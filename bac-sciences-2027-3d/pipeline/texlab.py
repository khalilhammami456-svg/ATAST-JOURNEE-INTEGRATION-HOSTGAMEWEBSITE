"""Texture lab: builds the PBR atlas for a garment (albedo / normal / ORM) from vector artwork.

Everything is authored in piece-local METRES (the same space as the pattern-space UVs written by
garment_lib.assign_pattern_uv), so a logo placed at (x=+0.09 m, z=-0.12 m) on 'Front_L' lands 9 cm
to the wearer's left and 12 cm below the shoulder line, at its true size.

Layers
  base fabric   : colour, brushed/knit micro-variation, roughness
  rib zones     : vertical rib relief (hem, cuffs)
  stitch lines  : topstitch along seams
  prints        : plastisol / DTF (flat, thin relief, optional crackle)
  embroidery    : satin-stitch relief (thread hatch + padded pillow), thread sheen
  woven patches : twill weave + merrowed border
Outputs float32 arrays in linear light for albedo? -> we keep sRGB uint8 for albedo, tangent-space
normal (OpenGL +Y), ORM (R=AO, G=roughness, B=metallic).
"""
import io, os, math, json, subprocess, tempfile, hashlib
from pathlib import Path
import numpy as np
from PIL import Image
from scipy import ndimage as ndi

ROOT = Path(__file__).resolve().parent.parent
CACHE = ROOT / "3d" / "textures" / "_cache"
CHROME = "/opt/pw-browsers/chromium_headless_shell-1194/chrome-linux/headless_shell"


from collections import namedtuple
Sprite = namedtuple('Sprite', 'rgba x0 y0 meta', defaults=(None,))


def hex2rgb(h):
    h = h.lstrip("#")
    return np.array([int(h[i:i + 2], 16) / 255.0 for i in (0, 2, 4)], dtype=np.float32)


def srgb2lin(c):
    c = np.asarray(c, dtype=np.float32)
    return np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)


def lin2srgb(c):
    c = np.clip(np.asarray(c, dtype=np.float32), 0, 1)
    return np.where(c <= 0.0031308, c * 12.92, 1.055 * c ** (1 / 2.4) - 0.055)


# ---------------------------------------------------------------- SVG -> RGBA raster

def rasterize_svg(svg_text, w_px, h_px, cache=True):
    """Rasterise an SVG string (viewBox given) to an RGBA float32 array [h,w,4] 0..1 (straight alpha)
    with headless Chromium.  Results are cached by content hash."""
    key = hashlib.sha1((svg_text + "|%d|%d" % (w_px, h_px)).encode()).hexdigest()[:16]
    CACHE.mkdir(parents=True, exist_ok=True)
    out = CACHE / (key + ".png")
    if not (cache and out.exists()):
        with tempfile.TemporaryDirectory() as td:
            sp = Path(td) / "a.svg"
            # force the requested pixel size, keep aspect through viewBox
            import re
            txt = re.sub(r"""(<svg[^>]*?)\swidth=["'][\d.]+(px)?["']""", r'\1 width="%d"' % w_px, svg_text, count=1)
            txt = re.sub(r"""(<svg[^>]*?)\sheight=["'][\d.]+(px)?["']""", r'\1 height="%d"' % h_px, txt, count=1)
            sp.write_text(txt, encoding="utf-8")
            html = Path(td) / "r.html"
            html.write_text('<!doctype html><meta charset="utf-8"><style>html,body{margin:0;background:transparent}'
                            'img{display:block;width:%dpx;height:%dpx}</style><img src="%s">' % (w_px, h_px, sp.as_uri()))
            tmp = Path(td) / "o.png"
            subprocess.run([CHROME, "--no-sandbox", "--disable-gpu", "--hide-scrollbars", "--allow-file-access-from-files",
                            "--default-background-color=00000000", "--screenshot=%s" % tmp,
                            "--window-size=%d,%d" % (w_px, h_px), "--force-device-scale-factor=1", html.as_uri()],
                           check=True, capture_output=True, timeout=240)
            Image.open(tmp).convert("RGBA").save(out)
    a = np.asarray(Image.open(out).convert("RGBA"), dtype=np.float32) / 255.0
    return a


# ---------------------------------------------------------------- noise helpers

def fbm(h, w, rng, scales=(64, 32, 16, 8, 4), weights=None):
    """Tileable-ish value noise (not strictly tileable) in 0..1."""
    weights = weights or [1.0 / (i + 1) for i in range(len(scales))]
    acc = np.zeros((h, w), np.float32)
    tot = 0.0
    for s, wt in zip(scales, weights):
        gh, gw = max(2, h // s + 2), max(2, w // s + 2)
        g = rng.random((gh, gw)).astype(np.float32)
        acc += wt * ndi.zoom(g, (h / (gh - 1) * 0.999 + 0.0, w / (gw - 1) * 0.999 + 0.0), order=3)[:h, :w] \
            if False else wt * np.asarray(Image.fromarray((g * 255).astype(np.uint8)).resize((w, h), Image.BICUBIC), np.float32) / 255.0
        tot += wt
    return acc / tot


def normal_from_height(hmap, strength, px_per_m):
    """Tangent-space normal (OpenGL: +Y up) from a height field in metres. strength scales slope."""
    gy, gx = np.gradient(hmap.astype(np.float32))
    k = px_per_m * strength
    nx, ny = -gx * k, gy * k            # image y runs down; flip for +Y-up convention
    nz = np.ones_like(nx)
    n = np.sqrt(nx * nx + ny * ny + nz * nz)
    return np.stack([nx / n, ny / n, nz / n], -1)


def pack_normal(n):
    return ((n * 0.5 + 0.5) * 255.0 + 0.5).clip(0, 255).astype(np.uint8)


# ---------------------------------------------------------------- Atlas

class Atlas:
    """Canvases for one garment: albedo (linear), height (m), roughness, ao, metal, covered by pieces."""

    def __init__(self, manifest, size=None, seed=7):
        self.man = manifest
        self.size = size or manifest["size_px"]
        self.ppm = manifest["px_per_m"]
        N = self.size
        self.alb = np.zeros((N, N, 3), np.float32)
        self.hgt = np.zeros((N, N), np.float32)       # metres
        self.rgh = np.full((N, N), 0.9, np.float32)
        self.ao = np.ones((N, N), np.float32)
        self.met = np.zeros((N, N), np.float32)
        self.mask = np.zeros((N, N), bool)            # inside any piece
        self.rng = np.random.default_rng(seed)
        self.log = []                                  # placement log (piece, kind, centre, size) for the technical flats
        self.piece_mask = {}
        self._build_piece_masks()

    # piece-local metres -> atlas pixel
    def px(self, piece, x, z):
        p = self.man["pieces"][piece]
        u = (p["ax"] + (x - p["minx"])) * self.ppm
        v = (p["ay"] + (p["minz"] + p["h"] - z)) * self.ppm      # pattern +z (up) = image up
        if p.get("flipx"):
            u = (p["ax"] + (p["minx"] + p["w"] - x)) * self.ppm
        return u, v

    def rect_px(self, piece):
        p = self.man["pieces"][piece]
        x0, y0 = int(math.floor(p["ax"] * self.ppm)), int(math.floor(p["ay"] * self.ppm))
        x1, y1 = int(math.ceil((p["ax"] + p["w"]) * self.ppm)), int(math.ceil((p["ay"] + p["h"]) * self.ppm))
        return x0, y0, x1, y1

    def _build_piece_masks(self):
        for name, p in self.man["pieces"].items():
            poly = self.man.get("outlines", {}).get(name)
            polys = self.man.get("polys", {}).get(name)
            x0, y0, x1, y1 = self.rect_px(name)
            m = np.zeros((self.size, self.size), bool)
            if polys:
                img = Image.new("L", (self.size, self.size), 0)
                from PIL import ImageDraw
                d = ImageDraw.Draw(img)
                for pl in polys:
                    d.polygon([self.px(name, x, z) for x, z in pl], fill=255)
                m = np.asarray(img) > 127
                m = ndi.binary_dilation(m, iterations=2)       # cover hairline gaps between faces
            elif poly:
                img = Image.new("L", (self.size, self.size), 0)
                from PIL import ImageDraw
                d = ImageDraw.Draw(img)
                for loop in poly:
                    pts = [self.px(name, x, z) for x, z in loop]
                    d.polygon(pts, fill=255)
                m = np.asarray(img) > 127
            else:
                m[y0:y1, x0:x1] = True
            self.piece_mask[name] = m
            self.mask |= m

    def tag_mask(self, tag, pieces=None):
        """Boolean atlas mask of the faces tagged `tag` ('hem', 'collar', 'cuff') in the manifest (exact UV polygons)."""
        from PIL import ImageDraw
        img = Image.new("L", (self.size, self.size), 0)
        d = ImageDraw.Draw(img)
        for name in (pieces or list(self.man["pieces"])):
            pl, tg = self.man.get("polys", {}).get(name, []), self.man.get("ptags", {}).get(name, [])
            for poly, t in zip(pl, tg):
                if t == tag:
                    d.polygon([self.px(name, x, z) for x, z in poly], fill=255)
        m = np.asarray(img) > 127
        return ndi.binary_dilation(m, iterations=2) & self.mask

    def piece_mask_of(self, *names):
        m = np.zeros((self.size, self.size), bool)
        for n in names:
            m |= self.piece_mask[n]
        return m

    # ---- base fabric
    def fabric(self, rgb, rough=0.92, grain=0.06, nap=0.35, tint_var=0.035, name_filter=None, kind=None, mask=None):
        N = self.size
        n1 = fbm(N, N, self.rng, scales=(96, 40, 16, 6, 3), weights=(0.5, 0.7, 0.8, 0.9, 1.0))
        n2 = self.rng.random((N, N)).astype(np.float32)
        lin = srgb2lin(rgb)
        if kind == "leather":                      # grain: small irregular cells
            c = fbm(N, N, self.rng, scales=(7, 4, 2), weights=(1, 1, 1))
            cells = np.abs(np.sin(c * 40.0))
            n2 = 0.5 + 0.5 * cells
            grain, nap, rough = 0.18, 0.5, 0.46
        elif kind == "nylon":                      # ripstop grid every 5 mm, very smooth
            yy, xx = np.mgrid[0:N, 0:N].astype(np.float32)
            g = ((xx % (self.ppm * 0.005) < 1.6) | (yy % (self.ppm * 0.005) < 1.6)).astype(np.float32)
            n2 = 0.5 + g * 0.5
            grain, nap, rough, tint_var = 0.05, 0.1, 0.34, 0.02
        elif kind == "melton":
            grain, nap, rough = 0.10, 0.8, 0.96
        elif kind == "jersey":
            grain, nap, rough = 0.05, 0.25, 0.86
        v = 1.0 + (n1 - 0.5) * 2 * tint_var + (n2 - 0.5) * grain
        col = lin[None, None, :] * v[..., None]
        h = ((n1 - 0.5) * 0.0004 + (n2 - 0.5) * 0.00025) * nap
        if mask is None:
            self.alb[:] = col; self.hgt[:] = h; self.rgh[:] = rough
        else:
            self.alb = np.where(mask[..., None], col, self.alb); self.hgt = np.where(mask, h, self.hgt); self.rgh = np.where(mask, rough, self.rgh)
        return self

    def zone(self, piece, x0, z0, x1, z1):
        """Boolean mask of a piece-local rectangle (metres)."""
        u0, v0 = self.px(piece, x0, z0)
        u1, v1 = self.px(piece, x1, z1)
        m = np.zeros((self.size, self.size), bool)
        a, b = int(min(u0, u1)), int(max(u0, u1))
        c, d = int(min(v0, v1)), int(max(v0, v1))
        m[max(c, 0):d, max(a, 0):b] = True
        return m & self.piece_mask[piece]

    def rib(self, mask, rgb, pitch_m=0.0036, depth_m=0.0006, vertical=True, rough=0.95):
        """Vertical 1x1 rib (knit) inside `mask` (windowed to the mask bounding box)."""
        rows = np.where(mask.any(axis=1))[0]; cols = np.where(mask.any(axis=0))[0]
        if len(rows) == 0:
            return
        sl = (slice(rows[0], rows[-1] + 1), slice(cols[0], cols[-1] + 1))
        m = mask[sl]
        yy, xx = np.mgrid[sl[0], sl[1]].astype(np.float32)
        coord = (xx if vertical else yy) / (self.ppm * pitch_m)
        ph = (0.5 + 0.5 * np.cos(2 * math.pi * coord)) ** 1.4
        lin = srgb2lin(rgb)
        shade = (0.78 + 0.22 * ph)[..., None]
        fine = (self.rng.random(m.shape).astype(np.float32) - 0.5) * 0.05
        self.alb[sl] = np.where(m[..., None], lin[None, None, :] * (shade + fine[..., None]), self.alb[sl])
        self.hgt[sl] = np.where(m, ph * depth_m, self.hgt[sl])
        self.rgh[sl] = np.where(m, rough, self.rgh[sl])
        self.ao[sl] = np.where(m, 0.88 + 0.12 * ph, self.ao[sl])

    # ---- generic layer compositing (sprites: cropped RGBA + atlas offset)
    def _sprite(self, rgba, cx_px, cy_px, rot_deg=0.0, mirror=False):
        im = Image.fromarray((rgba * 255 + 0.5).astype(np.uint8), "RGBA")
        if mirror:
            im = im.transpose(Image.FLIP_LEFT_RIGHT)
        if rot_deg:
            im = im.rotate(-rot_deg, resample=Image.BICUBIC, expand=True)
        w, h = im.size
        return np.asarray(im, dtype=np.float32) / 255.0, int(round(cx_px - w / 2)), int(round(cy_px - h / 2))

    def place(self, piece, svg_text, width_m, x, z, rot=0.0, mirror=False, supersample=1):
        """Rasterise art of true width `width_m`, centre at piece-local (x, z) metres.  Returns a Sprite
        (rgba, x0, y0) clipped to the piece outline."""
        import re
        m = re.search(r"""viewBox=["']0 0 ([\d.]+) ([\d.]+)["']""", svg_text)
        vw, vh = float(m.group(1)), float(m.group(2))
        wpx = max(8, int(round(width_m * self.ppm * supersample)))
        hpx = max(8, int(round(wpx * vh / vw)))
        art = rasterize_svg(svg_text, wpx, hpx)
        if supersample > 1:
            im = Image.fromarray((art * 255).astype(np.uint8), "RGBA").resize((wpx // supersample, hpx // supersample), Image.LANCZOS)
            art = np.asarray(im, dtype=np.float32) / 255.0
        cx, cy = self.px(piece, x, z)
        arr, x0, y0 = self._sprite(art, cx, cy, rot, mirror)
        N = self.size
        # clip to the atlas and to the piece mask
        ys0, xs0 = max(0, -y0), max(0, -x0)
        ye, xe = min(arr.shape[0], N - y0), min(arr.shape[1], N - x0)
        arr = arr[ys0:ye, xs0:xe].copy()
        x0, y0 = max(x0, 0), max(y0, 0)
        arr[..., 3] *= self.piece_mask[piece][y0:y0 + arr.shape[0], x0:x0 + arr.shape[1]]
        return Sprite(arr, x0, y0, dict(piece=piece, x=round(float(x), 4), z=round(float(z), 4), w=round(float(width_m), 4),
                                         h=round(float(width_m * vh / vw), 4), rot=float(rot), mirror=bool(mirror)))

    def _rec(self, sp, kind, **kw):
        if sp is not None and getattr(sp, "meta", None):
            self.log.append(dict(sp.meta, kind=kind, **kw))

    # ---- surfaces
    def _win(self, sp, pad=6):
        h, w = sp.rgba.shape[:2]
        y0, x0 = max(0, sp.y0 - pad), max(0, sp.x0 - pad)
        y1, x1 = min(self.size, sp.y0 + h + pad), min(self.size, sp.x0 + w + pad)
        sub = np.zeros((y1 - y0, x1 - x0, 4), np.float32)
        sub[sp.y0 - y0: sp.y0 - y0 + h, sp.x0 - x0: sp.x0 - x0 + w] = sp.rgba
        return (slice(y0, y1), slice(x0, x1)), sub

    def print_(self, sp, rough=0.62, relief_m=0.00025, crackle=0.0, opacity=1.0, tint=None):
        """Flat plastisol/DTF print: composite colour, thin relief, optional crackle."""
        self._rec(sp, "print")
        sl, L = self._win(sp)
        a = L[..., 3] * opacity
        if crackle > 0:
            nz = fbm(a.shape[0], a.shape[1], self.rng, scales=(10, 5, 2), weights=(1, 1, 1))
            a = a * (1.0 - crackle * np.clip((nz - 0.55) * 6, 0, 1))
        rgb = srgb2lin(L[..., :3])
        if tint is not None:
            rgb = rgb * srgb2lin(np.asarray(tint, np.float32))
        edge = ndi.gaussian_filter(a, 0.8)
        self.alb[sl] = self.alb[sl] * (1 - a[..., None]) + rgb * a[..., None]
        self.hgt[sl] = self.hgt[sl] + edge * relief_m * (a > 0.05)
        self.rgh[sl] = self.rgh[sl] * (1 - a) + rough * a

    def emb(self, sp, thread_angle_deg=35.0, pitch_m=0.0007, pillow_m=0.0007, relief_m=0.0012,
            rough=0.42, sheen=0.25, shade=0.35):
        """Satin-stitch embroidery relief: padded pillow + thread hatch (cropped to the sprite window)."""
        self._rec(sp, "embroidery", pitch_m=pitch_m)
        sl, L = self._win(sp, pad=12)
        a = L[..., 3]
        solid = a > 0.5
        if not solid.any():
            return
        d = ndi.distance_transform_edt(solid).astype(np.float32) / self.ppm
        pil = np.sin(np.clip(d / pillow_m, 0, 1) * math.pi / 2)
        yy, xx = np.mgrid[sl[0], sl[1]].astype(np.float32)
        th = math.radians(thread_angle_deg)
        s = (xx * math.cos(th) + yy * math.sin(th)) / (self.ppm * pitch_m)
        hatch = 0.5 + 0.5 * np.sin(2 * math.pi * s)
        h = (pil * relief_m + hatch * relief_m * 0.18) * solid
        light = 1.0 - shade * (1.0 - hatch) * 0.5 - 0.35 * (1.0 - pil) ** 2
        rgb = srgb2lin(L[..., :3]) * np.clip(light, 0.3, 1.2)[..., None]
        al = ndi.gaussian_filter(a, 0.6)
        self.alb[sl] = self.alb[sl] * (1 - al[..., None]) + rgb * al[..., None]
        self.hgt[sl] = np.where(solid, np.maximum(self.hgt[sl], h), self.hgt[sl] + ndi.gaussian_filter(h, 1.0) * 0.5)
        self.rgh[sl] = self.rgh[sl] * (1 - al) + (rough + 0.12 * (1 - hatch)) * al
        halo = ndi.gaussian_filter(solid.astype(np.float32), 2.5 * self.ppm / 2400.0 * 2)
        self.ao[sl] = self.ao[sl] * (1 - 0.35 * halo * (~solid))

    def weave(self, sp, pitch_m=0.00055, rough=0.7, relief_m=0.0007):
        """Woven (damask) patch / label: fine twill weave, flat colour from the sprite."""
        self._rec(sp, "woven")
        sl, L = self._win(sp, pad=8)
        a = L[..., 3]
        solid = a > 0.5
        yy, xx = np.mgrid[sl[0], sl[1]].astype(np.float32)
        t = ((xx + yy) / (self.ppm * pitch_m))
        tw = 0.5 + 0.5 * np.sin(2 * math.pi * t)
        weft = 0.5 + 0.5 * np.sin(2 * math.pi * yy / (self.ppm * pitch_m * 1.5))
        rgb = srgb2lin(L[..., :3]) * (0.86 + 0.14 * tw)[..., None] * (0.94 + 0.06 * weft)[..., None]
        al = ndi.gaussian_filter(a, 0.5)
        self.alb[sl] = self.alb[sl] * (1 - al[..., None]) + rgb * al[..., None]
        self.hgt[sl] = np.where(solid, np.maximum(self.hgt[sl], relief_m * (0.6 + 0.4 * tw)), self.hgt[sl])
        self.rgh[sl] = self.rgh[sl] * (1 - al) + rough * al

    def quilt(self, mask, pitch_m=0.078, seam_m=0.004, puff_m=0.006, vertical=False, rgb_seam=None):
        """Horizontal baffles: pillow height between stitched channels (puffer)."""
        rows = np.where(mask.any(axis=1))[0]; cols = np.where(mask.any(axis=0))[0]
        if len(rows) == 0:
            return
        sl = (slice(rows[0], rows[-1] + 1), slice(cols[0], cols[-1] + 1))
        m = mask[sl]
        yy, xx = np.mgrid[sl[0], sl[1]].astype(np.float32)
        coord = (xx if vertical else yy) / (self.ppm * pitch_m)
        ph = coord % 1.0
        pill = np.sin(np.clip(ph, 0, 1) * math.pi) ** 0.7              # 0 at the seam, 1 mid-baffle
        self.hgt[sl] = np.where(m, pill * puff_m, self.hgt[sl])
        shade = 0.82 + 0.18 * pill
        self.alb[sl] = np.where(m[..., None], self.alb[sl] * shade[..., None], self.alb[sl])
        self.ao[sl] = np.where(m, 0.78 + 0.22 * pill, self.ao[sl])

    def band(self, mask, z0, z1, piece_names, rgb, rough=None):
        """Flat colour band between world heights z0..z1 on the given pieces, restricted to `mask`."""
        m = np.zeros((self.size, self.size), bool)
        for n in piece_names:
            m |= self.zone(n, -9, z0, 9, z1)
        m &= mask
        if isinstance(rgb, str):
            rgb = hex2rgb(rgb)
        lin = srgb2lin(rgb)
        self.alb = np.where(m[..., None], lin[None, None, :] * (0.94 + 0.06 * self.rng.random((self.size, self.size, 1)).astype(np.float32)), self.alb)
        if rough is not None:
            self.rgh = np.where(m, rough, self.rgh)

    def tile_strip(self, piece, svg_text, x0, x1, z0, z1, cell_m, rot=0.0):
        """Tile an SVG cell over the rectangle (piece-local metres) [x0,x1] x [z0,z1] (seamless repeat); returns a Sprite."""
        import re
        m = re.search(r"""viewBox=["']0 0 ([\d.]+) ([\d.]+)["']""", svg_text)
        vw, vh = float(m.group(1)), float(m.group(2))
        cw = max(8, int(round(cell_m * self.ppm))); ch = max(8, int(round(cw * vh / vw)))
        cell = rasterize_svg(svg_text, cw, ch)
        ua, va = self.px(piece, min(x0, x1), max(z0, z1))
        ub, vb = self.px(piece, max(x0, x1), min(z0, z1))
        W, H = int(abs(ub - ua)), int(abs(vb - va))
        if W < 4 or H < 4:
            return Sprite(np.zeros((1, 1, 4), np.float32), 0, 0)
        reps = (H // ch + 1, W // cw + 1, 1)
        big = np.tile(cell, reps)[:H, :W].copy()
        x0p, y0p = int(min(ua, ub)), int(min(va, vb))
        N = self.size
        ye, xe = min(H, N - y0p), min(W, N - x0p)
        big = big[:ye, :xe]
        big[..., 3] *= self.piece_mask[piece][y0p:y0p + ye, x0p:x0p + xe]
        return Sprite(big, x0p, y0p, dict(piece=piece, x=round((x0 + x1) / 2, 4), z=round((z0 + z1) / 2, 4), w=round(abs(x1 - x0), 4), h=round(abs(z1 - z0), 4), rot=float(rot), mirror=False))

    def stitch_line(self, piece, pts, rgb, gauge_m=0.003, width_m=0.0006, offset_m=0.0, dash=True):
        """Topstitch along a polyline given in piece-local metres (cropped window)."""
        from PIL import ImageDraw
        P = [self.px(piece, x, z) for x, z in pts]
        xs = [p[0] for p in P]; ys = [p[1] for p in P]
        pad = 6
        x0, y0 = max(0, int(min(xs)) - pad), max(0, int(min(ys)) - pad)
        x1, y1 = min(self.size, int(max(xs)) + pad), min(self.size, int(max(ys)) + pad)
        if x1 <= x0 or y1 <= y0:
            return
        img = Image.new("L", (x1 - x0, y1 - y0), 0)
        d = ImageDraw.Draw(img)
        for (xa, ya), (xb, yb) in zip(P[:-1], P[1:]):
            xa -= x0; xb -= x0; ya -= y0; yb -= y0
            Ln = math.hypot(xb - xa, yb - ya)
            if Ln < 1e-6:
                continue
            n = max(1, int(Ln / (gauge_m * self.ppm)))
            for i in range(n):
                t0, t1 = i / n, min((i + 0.72) / n, 1)
                d.line([(xa + (xb - xa) * t0, ya + (yb - ya) * t0), (xa + (xb - xa) * t1, ya + (yb - ya) * t1)],
                       fill=255, width=max(1, int(width_m * self.ppm)))
        a = np.asarray(img, np.float32) / 255.0
        sl = (slice(y0, y1), slice(x0, x1))
        a = ndi.gaussian_filter(a, 0.5) * self.piece_mask[piece][sl]
        lin = srgb2lin(rgb)
        self.alb[sl] = self.alb[sl] * (1 - a[..., None]) + lin * a[..., None]
        self.hgt[sl] += a * 0.0004
        self.rgh[sl] = self.rgh[sl] * (1 - a) + 0.55 * a

    # ---- export
    def export(self, outdir, name, fill_bleed=8):
        """Write albedo/normal/orm PNGs (sRGB, tangent normal, ORM) with edge bleed to avoid seams."""
        outdir = Path(outdir)
        outdir.mkdir(parents=True, exist_ok=True)
        m = self.mask
        # bleed: extend piece colours outward so bilinear filtering never samples black
        idx = ndi.distance_transform_edt(~m, return_distances=False, return_indices=True)
        alb = self.alb[idx[0], idx[1]]
        hgt = self.hgt[idx[0], idx[1]]
        rgh = self.rgh[idx[0], idx[1]]
        ao = self.ao[idx[0], idx[1]]
        n = normal_from_height(ndi.gaussian_filter(hgt, 0.35), 1.0, self.ppm)
        Image.fromarray((lin2srgb(alb) * 255 + 0.5).astype(np.uint8)).save(outdir / (name + "_albedo.png"))
        Image.fromarray(pack_normal(n)).save(outdir / (name + "_normal.png"))
        json.dump(self.log, open(outdir / (name + "_placements.json"), "w"), indent=1)
        orm = np.stack([ao, rgh, self.met[idx[0], idx[1]]], -1)
        Image.fromarray((orm.clip(0, 1) * 255 + 0.5).astype(np.uint8)).save(outdir / (name + "_orm.png"))
        return dict(albedo=name + "_albedo.png", normal=name + "_normal.png", orm=name + "_orm.png")


def diag_atlas(man, out_png, size=None):
    """Orientation/scale diagnostic: coloured pieces, 5 cm grid with labels, piece name, arrow and an
    asymmetric 'F' so mirroring and rotation are obvious on the 3D garment."""
    from PIL import ImageDraw, ImageFont
    N = size or man["size_px"]
    ppm = man["px_per_m"] * N / man["size_px"]
    img = Image.new("RGB", (N, N), (30, 30, 34))
    d = ImageDraw.Draw(img)
    f_big = ImageFont.truetype(str(ROOT / "brand-identity" / "typography" / "JetBrainsMono-VF.ttf"), int(0.07 * ppm))
    f_sm = ImageFont.truetype(str(ROOT / "brand-identity" / "typography" / "JetBrainsMono-VF.ttf"), int(0.02 * ppm))
    cols = [(236, 120, 120), (120, 190, 236), (140, 220, 140), (236, 200, 110), (190, 140, 236), (110, 220, 210), (240, 150, 200), (200, 200, 120)]
    for i, (name, p) in enumerate(man["pieces"].items()):
        x0, y0 = p["ax"] * ppm, p["ay"] * ppm
        w, h = p["w"] * ppm, p["h"] * ppm
        col = cols[i % len(cols)]
        poly = man.get("outlines", {}).get(name)
        polys = man.get("polys", {}).get(name)
        def P(x, z):
            u = (p["ax"] + ((p["minx"] + p["w"] - x) if p.get("flipx") else (x - p["minx"]))) * ppm
            v = (p["ay"] + (p["minz"] + p["h"] - z)) * ppm
            return (u, v)
        if polys:
            for pl in polys:
                d.polygon([P(x, z) for x, z in pl], fill=tuple(int(c * 0.55) for c in col))
        elif poly:
            for loop in poly:
                d.polygon([P(x, z) for x, z in loop], fill=tuple(int(c * 0.55) for c in col))
        else:
            d.rectangle([x0, y0, x0 + w, y0 + h], fill=tuple(int(c * 0.55) for c in col))
        # grid every 5 cm in piece-local metres, origin = piece bbox centre
        for gx in range(-40, 41):
            xm = gx * 0.05
            a, b = P(xm, p["minz"]), P(xm, p["minz"] + p["h"])
            d.line([a, b], fill=(255, 255, 255) if gx == 0 else (200, 200, 200), width=3 if gx == 0 else 1)
            if abs(xm) <= (p["w"] / 2 + 0.2):
                d.text((a[0] + 3, b[1] + 3), "%+d" % (gx * 5), font=f_sm, fill=(255, 255, 255))
        for gz in range(-40, 41):
            zm = gz * 0.05
            a, b = P(p["minx"], zm), P(p["minx"] + p["w"], zm)
            d.line([a, b], fill=(255, 255, 255) if gz == 0 else (200, 200, 200), width=3 if gz == 0 else 1)
            d.text((b[0] - 90, a[1] + 3), "%+d" % (gz * 5), font=f_sm, fill=(255, 255, 255))
        cx, cz = (p["minx"] + p["w"] / 2) * 0, 0
        c = P(0, 0)
        d.text((c[0] + 6, c[1] + 6), name.split("_", 1)[-1], font=f_big, fill=(255, 255, 255), stroke_width=3, stroke_fill=(0, 0, 0))
        d.text((c[0] + 6, c[1] + 6 + int(0.09 * ppm)), "F  ->x  ^up", font=f_big, fill=(255, 255, 0), stroke_width=3, stroke_fill=(0, 0, 0))
    img.save(out_png)
    return out_png
