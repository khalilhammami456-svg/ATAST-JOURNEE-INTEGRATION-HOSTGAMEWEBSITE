"""Vector technical flats (front / back) from the 3D silhouettes.  System python (cv2, numpy, PIL).

usage: python flat_sheet.py ID [colourway]    -> technical-flats/<ID>_flat.svg  (+ returns legend / POM bubbles for the tech pack)
Requires flats_ortho.py output (technical-flats/_work/<ID>_{front,back}_mask.png + <ID>_ortho.json).
Outline  = traced silhouette of the 3D garment (front / back orthographic view), simplified to <0.5 mm error.
Lines    = projected collar / hem / cuff loops of the shell, rib-top lines, placket / snaps from the build config.
POM      = lettered measurement bubbles (A, B, C ...) whose values are in <ID>_measures.json and in the tech pack.
Decor    = dashed boxes at the true placements recorded by texlab (print / embroidery / woven).
"""
import sys, json, math
from pathlib import Path
import numpy as np
import cv2
from PIL import Image
HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(HERE))
from collection import ITEMS

INK = "#0B1226"; GRID = "#9AA3B2"; RED = "#C8102E"; ACC = "#6B4EF5"
KCOL = {"embroidery": "#6B4EF5", "print": "#2E7BFF", "woven": "#B87B83"}
KFR = {"embroidery": "broderie", "print": "impression", "woven": "tissé"}


def trace(mask_png):
    a = np.asarray(Image.open(mask_png))[..., 3]
    a = cv2.GaussianBlur(a, (0, 0), 2.0)
    m = (a > 127).astype(np.uint8) * 255
    cs, _ = cv2.findContours(m, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
    c = max(cs, key=cv2.contourArea)
    c = cv2.approxPolyDP(c, 1.6, True)[:, 0, :].astype(float)
    return c, m


def run_extent(m, py, px0):
    """x-extent (px) of the connected mask run on row py that contains column px0."""
    row = m[int(py)] > 0
    if not row[int(px0)]:
        return None
    l = int(px0); r = int(px0)
    while l > 0 and row[l - 1]:
        l -= 1
    while r < len(row) - 1 and row[r + 1]:
        r += 1
    return l, r


def arm_point(arm, d):
    sh, el, wr = [np.array(v) for v in arm]
    L1 = np.linalg.norm(el - sh); L2 = np.linalg.norm(wr - el)
    if d <= L1:
        return sh + (el - sh) * d / L1
    return el + (wr - el) * min(1.0, (d - L1) / L2)


def build(it, colorway=None, out=None):
    meta_it = ITEMS[it]
    W = ROOT / "technical-flats" / "_work"
    od = json.load(open(W / f"{it}_ortho.json"))
    meta = od["meta"]
    cws = list(meta_it["colorways"])
    cw = colorway or cws[0]
    pj = ROOT / "3d" / "textures" / it / f"{cw}_placements.json"
    pls = json.load(open(pj)) if pj.exists() else []
    hj = ROOT / "3d" / "textures" / it / f"{cw}_hood_placements.json"
    hood_pls = json.load(open(hj)) if hj.exists() else []
    M = {}
    mp = ROOT / "3d" / "models" / it / f"{it}_measures.json"
    if mp.exists():
        M = json.load(open(mp))
    sc = 1000.0                                      # metres -> svg units (mm)
    views = {}
    for v in ("front", "back"):
        info = od[v]
        c, m = trace(W / f"{it}_{v}_mask.png")
        S = info["size"]; span = info["span"]; cx, cz = info["cx"], info["cz"]
        # px -> (u, z) where u = rightwards in the image, in metres from the panel centre
        u = (c[:, 0] - S / 2) / S * span
        z = cz - (c[:, 1] - S / 2) / S * span
        views[v] = dict(u=u, z=z, m=m, S=S, span=span, cx=cx, cz=cz)
    span = od["front"]["span"]
    panel = span * sc
    gap = 120
    Wt = panel * 2 + gap + 160
    Ht = panel + 210
    g = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {Wt:.0f} {Ht:.0f}" width="{Wt * 0.9:.0f}" height="{Ht * 0.9:.0f}" font-family="JetBrains Mono, DejaVu Sans Mono, monospace">',
         f'<rect width="100%" height="100%" fill="#fff"/>']
    legend = []; pom = []
    off = {"front": 80, "back": 80 + panel + gap}
    def X(v, u_m):
        return off[v] + panel / 2 + u_m * sc
    def Z(v, z_m):
        return 120 + panel / 2 - (z_m - views[v]["cz"]) * sc
    neck_z = meta.get("neck_z", od["z"]["neck"]); hem_z = meta.get("hem_z", 0.9)
    for v in ("front", "back"):
        V = views[v]
        d = " ".join(("M" if i == 0 else "L") + f"{X(v, uu):.1f},{Z(v, zz):.1f}" for i, (uu, zz) in enumerate(zip(V["u"], V["z"]))) + " Z"
        g.append(f'<path d="{d}" fill="#F5F4F0" stroke="{INK}" stroke-width="3" stroke-linejoin="round"/>')
        g.append(f'<text x="{off[v] + 4:.0f}" y="100" font-size="30" font-weight="700" fill="{INK}">{"DEVANT" if v == "front" else "DOS"} · {it}</text>')
        sgn = 1 if v == "front" else -1
        # --- projected loops (collar, hem, cuffs): keep the half facing the camera
        for lp in od["loops"]:
            pts = np.array(lp)
            yc = pts[:, 1].mean()
            zc = pts[:, 2].mean()
            front_half = pts[:, 1] <= yc if v == "front" else pts[:, 1] >= yc
            # sleeves openings (arms) are drawn whole
            is_cuff = abs(pts[:, 0].mean()) > 0.15
            sel = pts if is_cuff else pts[front_half]
            if len(sel) < 3:
                continue
            ordr = np.argsort(sel[:, 0]) if not is_cuff else np.arange(len(sel))
            uu = (sel[:, 0] - od[v]["cx"]) * sgn
            pp = " ".join(("M" if i == 0 else "L") + f"{X(v, uu[j]):.1f},{Z(v, sel[j][2]):.1f}" for i, j in enumerate(ordr))
            col = INK
            g.append(f'<path d="{pp}" fill="none" stroke="{col}" stroke-width="1.8" stroke-linejoin="round" opacity="0.8"/>')
        # --- rib / band lines
        rh = meta.get("rib_h", 0.0)
        if rh and rh > 0:
            ext = run_extent(V["m"], V["S"] / 2 + (V["cz"] - (hem_z + rh)) / V["span"] * V["S"], V["S"] / 2 - sgn * V["cx"] / V["span"] * V["S"])
            if ext:
                l, r = ext
                uu0 = (l - V["S"] / 2) / V["S"] * V["span"]; uu1 = (r - V["S"] / 2) / V["S"] * V["span"]
                for dz in (0, 0.007):
                    g.append(f'<path d="M{X(v, uu0):.1f},{Z(v, hem_z + rh + dz):.1f} L{X(v, uu1):.1f},{Z(v, hem_z + rh + dz):.1f}" stroke="{INK}" stroke-width="1.2" stroke-dasharray="9 5"/>')
        if v == "front" and (meta.get("zip") or meta.get("snaps")):
            g.append(f'<path d="M{X(v, 0):.1f},{Z(v, neck_z - 0.01):.1f} L{X(v, 0):.1f},{Z(v, hem_z + 0.005):.1f}" stroke="{INK}" stroke-width="2.4"/>')
            if meta.get("snaps"):
                for k in range(6):
                    zq = neck_z - 0.045 + (hem_z + rh + 0.075 - (neck_z - 0.045)) * k / 5
                    g.append(f'<circle cx="{X(v, 0):.1f}" cy="{Z(v, zq):.1f}" r="7" fill="#fff" stroke="{INK}" stroke-width="2"/>')
        # --- POM bubbles with dimension lines
        def bub(letter, x, y):
            g.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="15" fill="{RED}"/><text x="{x:.1f}" y="{y + 6:.1f}" text-anchor="middle" font-size="17" font-weight="700" fill="#fff">{letter}</text>')
        if v == "front":
            ch = meta["chest_z"]; wz = meta["waist_z"]
            tor = []
            for letter, zq, key in (("A", ch, "chest_half_cm"), ("B", wz, "waist_half_cm"), ("C", hem_z + 0.025, "hem_half_cm")):
                py = V["S"] / 2 + (V["cz"] - zq) / V["span"] * V["S"]
                ext = run_extent(V["m"], py, V["S"] / 2 - sgn * V["cx"] / V["span"] * V["S"])
                if ext:
                    l, r = ext
                    u0 = (l - V["S"] / 2) / V["S"] * V["span"]; u1 = (r - V["S"] / 2) / V["S"] * V["span"]
                    y = Z(v, zq)
                    g.append(f'<path d="M{X(v, u0):.1f},{y:.1f} L{X(v, u1):.1f},{y:.1f}" stroke="{RED}" stroke-width="1.6"/><path d="M{X(v, u0):.1f},{y - 8:.1f} v16 M{X(v, u1):.1f},{y - 8:.1f} v16" stroke="{RED}" stroke-width="1.6"/>')
                    bub(letter, X(v, u0) - 26, y)
                    pom.append((letter, key))
            # D: body length (left of the garment at the hem)
            xl = X(v, -0.0) - (views[v]["span"] * sc) * 0.5 + 24
            g.append(f'<path d="M{xl:.1f},{Z(v, neck_z):.1f} L{xl:.1f},{Z(v, hem_z):.1f}" stroke="{RED}" stroke-width="1.6"/><path d="M{xl - 8:.1f},{Z(v, neck_z):.1f} h16 M{xl - 8:.1f},{Z(v, hem_z):.1f} h16" stroke="{RED}" stroke-width="1.6"/>')
            bub("D", xl, (Z(v, neck_z) + Z(v, hem_z)) / 2)
            pom.append(("D", "body_length_cm"))
            # E: sleeve length along the arm (left arm = +x = right in the front view)
            sh, el, wr = [np.array(q) for q in od["arms"]["L"]]
            if meta.get("sleeve") != "armhole":
                cut = meta["arm_cut"] * meta["upper_len"] if meta["sleeve"] == "short" else meta["chain_len"] * meta["cuff_t"]
                p0 = arm_point(od["arms"]["L"], 0.0); p1 = arm_point(od["arms"]["L"], cut)
                dx, dz = p1[0] - p0[0], p1[2] - p0[2]
                n = np.array([dz, -dx]); n = n / (np.linalg.norm(n) + 1e-9) * 0.045
                q0, q1 = (p0[0] + n[0], p0[2] + n[1]), (p1[0] + n[0], p1[2] + n[1])
                g.append(f'<path d="M{X(v, q0[0] - od[v]["cx"]):.1f},{Z(v, q0[1]):.1f} L{X(v, q1[0] - od[v]["cx"]):.1f},{Z(v, q1[1]):.1f}" stroke="{RED}" stroke-width="1.6"/>')
                bub("E", X(v, (q0[0] + q1[0]) / 2 - od[v]["cx"]) + 18, Z(v, (q0[1] + q1[1]) / 2))
                pom.append(("E", "sleeve_len_cm"))
            # F: shoulder width between the shoulder joints
            zs = od["z"]["shoulder"] + 0.035
            g.append(f'<path d="M{X(v, -sh[0] - od[v]["cx"]):.1f},{Z(v, zs):.1f} L{X(v, sh[0] - od[v]["cx"]):.1f},{Z(v, zs):.1f}" stroke="{RED}" stroke-width="1.6" stroke-dasharray="6 4"/>')
            bub("F", X(v, 0), Z(v, zs) - 26)
            pom.append(("F", "shoulder_cm"))
        # --- decor placements
        n_pl = 0
        allp = pls + [dict(p, _hood=True) for p in hood_pls]
        for pl in allp:
            if pl.get("_hood"):
                continue
            piece = pl["piece"]
            if piece == "Front" and v != "front" or piece == "Back" and v != "back":
                continue
            if piece.startswith("Sleeve") and v != "front":
                continue
            if pl["w"] < 0.012:
                continue
            if piece in ("Front", "Back"):
                uu = pl["x"] - od[v]["cx"] if v == "front" else pl["x"] + od[v]["cx"]
                zz = pl["z"]
            else:
                side = "L" if piece.endswith("L") else "R"
                P = arm_point(od["arms"][side], -pl["z"])
                uu = P[0]; zz = P[2]
            w, h = pl["w"] * sc, pl["h"] * sc
            xx, yy = X(v, uu - (od[v]["cx"] if piece.startswith("Sleeve") else 0)), Z(v, zz)
            col = KCOL.get(pl["kind"], ACC)
            rot = pl.get("rot", 0.0)
            key = (v, piece, round(pl["x"], 2), round(pl["z"], 2), round(pl["w"], 2), pl["kind"])
            if key in [k for k, *_ in legend]:
                continue
            idx = len(legend) + 1
            legend.append((key, idx, pl))
            g.append(f'<g transform="translate({xx:.1f},{yy:.1f}) rotate({rot:.1f})"><rect x="{-w / 2:.1f}" y="{-h / 2:.1f}" width="{w:.1f}" height="{h:.1f}" fill="{col}" fill-opacity="0.12" stroke="{col}" stroke-width="2" stroke-dasharray="8 5"/></g>')
            g.append(f'<circle cx="{xx:.1f}" cy="{yy:.1f}" r="14" fill="{col}"/><text x="{xx:.1f}" y="{yy + 6:.1f}" font-size="17" fill="#fff" text-anchor="middle" font-weight="700">{idx}</text>')
    g.append("</svg>")
    out = Path(out or ROOT / "technical-flats" / f"{it}_flat.svg")
    out.write_text("\n".join(g), encoding="utf-8")
    return dict(legend=[(i, pl["kind"], pl["piece"], pl["w"], pl["h"], pl["x"], pl["z"]) for _, i, pl in legend], pom=pom, svg=out)


if __name__ == "__main__":
    for it in sys.argv[1:]:
        r = build(it)
        print(it, "flat ->", r["svg"].name, len(r["legend"]), "placements", [p[0] for p in r["pom"]])
