"""Designs for scarves and accessories (own UV atlases).  System python."""
import sys, math, json
from pathlib import Path
import numpy as np
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE)); sys.path.insert(0, str(HERE / "art"))
from texlab import Atlas, hex2rgb
from collection import PAL
import art3d as ART
from lib import PAL as APAL, lum, svg as SVG, T as TXT, text_w as TXTW
from designs import TEX, Pc
from designs2 import ink_on

P = dict(PAL)


def _border_text(text, ink, width_units=2400, size=44):
    w = TXTW(text, "mono", size, 260, wght=600) + 40
    return SVG(w, size * 1.6, TXT(text, "mono", size, w / 2, size * 1.15, ink, "middle", tracking=260, wght=600))


# ===================================================================================== S1 ORBITE
def s1_orbite(man, colorway="nuit", out="S1"):
    base, accent, end = {"nuit": ("#0B1226", P["violet"], "#EFEBE2"), "maroon": ("#5C1526", P["rose"], "#EFEBE2")}[colorway]
    meta = man["pieces"]["Scarf"]
    L, W = meta["w"], meta["h"]
    A = Atlas(man)
    A.fabric(hex2rgb(base), rough=0.95, grain=0.09, nap=0.9, tint_var=0.03)
    x0, x1, z0, z1 = -L / 2, L / 2, -W / 2, W / 2
    cell = ART.orbit_cell_svg(APAL, s=300, ink=P["chalk"], accent=accent, stars=True)
    pat = A.tile_strip("Scarf", cell, x0 + 0.27, x1 - 0.27, z0 + 0.012, z1 - 0.012, 0.075)
    A.weave(pat, rough=0.9, relief_m=0.0008)
    # contrast ends (chalk jacquard) with type
    endcol = hex2rgb(end)
    for sgn, x_a, x_b in ((-1, x0, x0 + 0.26), (1, x1 - 0.26, x1)):
        A.band(A.piece_mask["Scarf"], z0 + 0.0, z1, ["Scarf"], endcol) if False else None
        m = A.zone("Scarf", x_a, z0, x_b, z1)
        A.alb = np.where(m[..., None], endcol[None, None, :] * (0.94 + 0.06 * A.rng.random((A.size, A.size, 1)).astype(np.float32)), A.alb)
        txt = _border_text("BAC SCIENCES 2027", base, size=40)
        sp = A.place("Scarf", txt, 0.20, (x_a + x_b) / 2, 0.0, rot=(90 if sgn < 0 else -90))
        A.weave(sp, rough=0.9, relief_m=0.0008)
        # stripes at the cut edge
        for k, col in enumerate((base, accent, base)):
            xs = (x_a + 0.012 * (k + 1)) if sgn < 0 else (x_b - 0.012 * (k + 1))
            A.stitch_line("Scarf", [(xs, z0 + 0.004), (xs, z1 - 0.004)], hex2rgb(col), gauge_m=0.0015, width_m=0.0045)
    return A.export(TEX / out, colorway)


# ===================================================================================== S2 BORD
def s2_bord(man, colorway="rose", out="S2"):
    base, border = {"rose": ("#D9A3A8", P["chalk"]), "chalk": ("#EFEBE2", P["maroon"])}[colorway]
    meta = man["pieces"]["Scarf"]
    L, W = meta["w"], meta["h"]
    A = Atlas(man)
    A.fabric(hex2rgb(base), rough=0.96, grain=0.10, nap=1.0, tint_var=0.03)
    x0, x1, z0, z1 = -L / 2, L / 2, -W / 2, W / 2
    for sgn in (-1, 1):
        zc = sgn * (W / 2 - 0.022)
        for dz in (-0.014, 0.014):
            A.stitch_line("Scarf", [(x0 + 0.01, zc + dz), (x1 - 0.01, zc + dz)], hex2rgb(border), gauge_m=0.0016, width_m=0.0030)
        txt = _border_text("TÉBOURBA · BAC SCIENCES · 2027 · LYCÉE HANNIBAL ·", border, size=36)
        reps = int(L / 0.52) + 1
        for r in range(reps):
            xc = x0 + 0.26 + r * 0.52
            if xc + 0.26 > x1:
                break
            A.weave(A.place("Scarf", txt, 0.50, xc, zc, rot=0 if sgn > 0 else 180), rough=0.92, relief_m=0.0007)
    for sgn in (-1, 1):                                       # end stripes
        for k in range(4):
            xs = (x0 + 0.03 + 0.016 * k) if sgn < 0 else (x1 - 0.03 - 0.016 * k)
            A.stitch_line("Scarf", [(xs, z0 + 0.004), (xs, z1 - 0.004)], hex2rgb(border if k % 2 == 0 else P["maroon"]), gauge_m=0.0015, width_m=0.0055)
    ten = ART.orbit_lam_svg(APAL, fill=border, accent=border, R=200)
    A.emb(A.place("Scarf", ten, 0.07, x1 - 0.12, 0.0), thread_angle_deg=40, pitch_m=0.0008, relief_m=0.0010)
    return A.export(TEX / out, colorway)


# ===================================================================================== A1 CASQUETTE
def _cap_seams(A, piece, man, info, rgb, side):
    cx = info["c"][0]; rx = info["r"][0] + 0.012; cz = info["c"][2]; rz = info["r"][2] + 0.0096; zb = info["zb"]
    lum_ = float(rgb.mean())
    thread = np.clip(rgb * 0.62 + 0.0, 0, 1) if lum_ > 0.35 else np.clip(rgb * 1.0 + 0.20, 0, 1)
    for az in (0, 60, 120, 180, 240, 300):
        a = math.radians(az)
        front = az in (0, 60, 300)
        if (piece == "Front") != front:
            continue
        for dxs in (-0.0032, 0.0032):                         # double topstitch either side of the seam
            pts = []
            for i in range(0, 41):
                phi = (math.pi / 2) * i / 40 * 0.985
                x = (rx * math.cos(phi) * math.sin(a) + dxs * math.cos(a)) * (1 if piece == "Front" else -1)
                z = zb + (cz + rz - zb) * math.sin(phi) ** 0.9
                pts.append((x, z))
            A.stitch_line(piece, pts, thread, gauge_m=0.0021, width_m=0.0009)
        pts = []                                              # the seam itself (slightly darker, recessed)
        for i in range(0, 41):
            phi = (math.pi / 2) * i / 40 * 0.985
            x = rx * math.cos(phi) * math.sin(a) * (1 if piece == "Front" else -1)
            z = zb + (cz + rz - zb) * math.sin(phi) ** 0.9
            pts.append((x, z))
        A.stitch_line(piece, pts, rgb * 0.7, gauge_m=0.0012, width_m=0.0016, dash=False)


def a1_cap(man, colorway="nuit", out="A1", brim_man=None):
    base = {"nuit": "#0F1730", "rose": "#D9A3A8"}[colorway]
    ink = ink_on(base)
    info = man["info"]
    A = Atlas(man)
    A.fabric(hex2rgb(base), rough=0.9, grain=0.08, nap=0.5)
    for pc in ("Front", "Back"):
        _cap_seams(A, pc, man, info, hex2rgb(base), pc)
    cx, cy, cz = info["c"]
    mono = ART.orbit_lam_svg(APAL, fill=ink, accent=P["violet"] if colorway == "nuit" else P["maroon"], R=200)
    A.emb(A.place("Front", mono, 0.058, 0.0, info["zb"] + 0.052), thread_angle_deg=40, pitch_m=0.0007, relief_m=0.0012)
    yr = ART.numerals_svg(APAL, fill=ink, size=200)
    A.emb(A.place("Back", yr, 0.050, 0.0, info["zb"] + 0.032), thread_angle_deg=0, pitch_m=0.0007, relief_m=0.0011)
    res = A.export(TEX / out, colorway)
    if brim_man:
        B = Atlas(brim_man, size=1024)
        B.fabric(hex2rgb(base), rough=0.8, grain=0.05, nap=0.3)
        bp = brim_man["pieces"]["Brim"]
        half = 0.5 * 0.205 * 0.82
        thr = np.clip(hex2rgb(base) * 0.62, 0, 1) if hex2rgb(base).mean() > 0.35 else np.clip(hex2rgb(base) + 0.20, 0, 1)
        for k in range(1, 6):                                  # five rows of stitching parallel to the edge
            d = 0.0065 * k
            pts = []
            for i in range(-20, 21):
                u = i / 20.0
                edge = 0.092 * math.sqrt(max(0.0, 1 - u * u * 0.78))
                pts.append((u * half * (1 - 0.0), -edge + d))
            B.stitch_line("Brim", pts, thr, gauge_m=0.0022, width_m=0.0009)
        B.export(TEX / out, colorway + "_brim")
    return res


# ===================================================================================== A2 BONNET
def a2_beanie(man, colorway="nuit", out="A2", cuff_man=None):
    base = {"nuit": "#0F1730", "chalk": "#EFEBE2"}[colorway]
    ink = ink_on(base)
    A = Atlas(man)
    A.fabric(hex2rgb(base), rough=0.97, grain=0.10, nap=1.0)
    for pc in ("Front", "Back"):
        A.rib(A.piece_mask[pc], hex2rgb(base) * 0.9, pitch_m=0.0042, depth_m=0.0011)
    res = A.export(TEX / out, colorway)
    if cuff_man:
        C = Atlas(cuff_man, size=2048)
        C.fabric(hex2rgb(base), rough=0.97, grain=0.10, nap=1.0)
        for pc in ("CuffF", "CuffB"):
            C.rib(C.piece_mask[pc], hex2rgb(base) * 0.88, pitch_m=0.0052, depth_m=0.0014)
        lab = ART.woven_label_svg(APAL, bg=P["nuit"] if colorway != "nuit" else P["violet"], ink=P["chalk"], accent=P["chalk"], W=700, H=300, lines=("BAC", "2027"))
        C.weave(C.place("CuffF", lab, 0.045, -0.02, cuff_man["pieces"]["CuffF"]["minz"] + 0.030), rough=0.6, relief_m=0.0008)
        C.export(TEX / out, colorway + "_cuff")
    return res


# ===================================================================================== A3 TOTE
def a3_tote(man, colorway="chalk", out="A3"):
    base = {"chalk": "#EFEBE2", "nuit": "#0F1730"}[colorway]
    ink = ink_on(base)
    A = Atlas(man)
    A.fabric(hex2rgb(base), rough=0.96, grain=0.12, nap=0.9)
    mol = ART.caffeine_svg(APAL, ink=ink, accent=P["violet"], size=900, line=3.6)
    A.print_(A.place("Front", mol, 0.27, 0.0, 0.215), rough=0.7, relief_m=0.0003)
    f = SVG(900, 150, TXT("C₈H₁₀N₄O₂", "mono", 74, 450, 80, ink, "middle", tracking=60, wght=600)
            + TXT("BAC SCIENCES 2027 · LYCÉE HANNIBAL", "mono", 22, 450, 128, ink, "middle", tracking=120, wght=500))
    A.print_(A.place("Front", f, 0.25, 0.0, 0.075), rough=0.7, relief_m=0.0002)
    crest = ART.crest_svg(APAL, fg=P["nuit"], bg=P["chalk"], accent=P["violet"] if colorway == "chalk" else P["rose"], R=300)
    A.print_(A.place("Back", crest, 0.10, 0.0, 0.28), rough=0.7, relief_m=0.0003)
    for pc in ("Front", "Back"):
        z = A.man["pieces"][pc]["minz"] + 0.035
        w = A.man["pieces"][pc]["w"]
        A.stitch_line(pc, [(-w / 2 + 0.01, z + 0.01), (w / 2 - 0.01, z + 0.01)], hex2rgb(base) * 0.8, gauge_m=0.0030)
    return A.export(TEX / out, colorway)


# ===================================================================================== A4 PATCH / A5 LABEL
def a4_patch(man, colorway="nuit", out="A4"):
    A = Atlas(man, size=2048)
    A.fabric(hex2rgb(P["nuit"]), rough=0.7, grain=0.08, nap=0.4)
    crest = ART.crest_svg(APAL, fg=P["nuit"], bg=P["chalk"], accent=P["violet"], R=300)
    A.emb(A.place("Face", crest, 0.074, 0.0, 0.0), thread_angle_deg=30, pitch_m=0.00055, relief_m=0.0013, pillow_m=0.0005, rough=0.38)
    return A.export(TEX / out, colorway)


def a5_label(man, colorway="nuit", out="A5"):
    A = Atlas(man, size=2048)
    A.fabric(hex2rgb(P["nuit"]), rough=0.7, grain=0.05, nap=0.2)
    lab = ART.woven_label_svg(APAL, bg=P["nuit"], ink=P["chalk"], accent=P["violet"], W=1200, H=240)
    A.weave(A.place("Face", lab, 0.057, 0.0, 0.0), rough=0.6, relief_m=0.0003, pitch_m=0.00016)
    return A.export(TEX / out, colorway)
