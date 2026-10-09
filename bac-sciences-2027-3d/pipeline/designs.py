"""Per-item designs: composes the PBR atlas (albedo / normal / ORM) for a sewn garment from the atlas manifest.

Coordinates are piece-local metres, origin = piece bounding-box centre, +x = wearer's left, +z = up.
helpers:  P(piece).top / .bot / .l / .r give the bbox edges;  from_top(piece, d) = z of a point d below the top edge.
"""
import sys, json, math
from pathlib import Path
import numpy as np
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE)); sys.path.insert(0, str(HERE / "art"))
import texlab
from texlab import Atlas, hex2rgb, srgb2lin
from collection import PAL
import art3d as ART
from lib import PAL as APAL

TEX = HERE.parent / "3d" / "textures"


class Pc:
    def __init__(self, man, name):
        full = [k for k in man["pieces"] if k.endswith("_" + name) or k == name]
        if not full:
            raise KeyError(name)
        self.name = full[0]
        p = man["pieces"][self.name]
        self.w, self.h = p["w"], p["h"]
        self.l, self.r = p["minx"], p["minx"] + p["w"]
        self.bot, self.top = p["minz"], p["minz"] + p["h"]

    def from_top(self, d):
        return self.top - d

    def from_bot(self, d):
        return self.bot + d

    def from_cf(self, d, left_half=True):
        """x at distance d from the centre-front edge (Front_L: cf at l, Front_R: cf at r)."""
        return self.l + d if left_half else self.r - d


def seg_pts(man, piece_full, seg):
    return [tuple(p) for p in man["segments"].get(piece_full, {}).get(seg, [])]


def inset_line(pts, d, side=+1):
    """Offset a polyline by d towards its left (+1) / right (-1) normal."""
    out = []
    n = len(pts)
    for i, (x, z) in enumerate(pts):
        a = pts[max(0, i - 1)]; b = pts[min(n - 1, i + 1)]
        tx, tz = b[0] - a[0], b[1] - a[1]
        L = math.hypot(tx, tz) or 1.0
        nx, nz = -tz / L, tx / L
        out.append((x + side * d * nx, z + side * d * nz))
    return out


def stitch_seams(A, man, rgb, pieces_segs, d=0.006, side=None, gauge=0.0028):
    """Topstitch parallel to named segments.  pieces_segs: {piece_suffix: [seg, ...]}.  The inward side is
    chosen so the stitch falls inside the piece mask."""
    for suffix, segs in pieces_segs.items():
        pc = Pc(man, suffix)
        for sg in segs:
            pts = seg_pts(man, pc.name, sg)
            if len(pts) < 2:
                continue
            best = None
            for s in (+1, -1):
                q = inset_line(pts, d, s)
                inside = sum(1 for (x, z) in q if A.piece_mask[pc.name][int(min(max(A.px(pc.name, x, z)[1], 0), A.size - 1)),
                                                                        int(min(max(A.px(pc.name, x, z)[0], 0), A.size - 1))])
                if best is None or inside > best[0]:
                    best = (inside, q)
            A.stitch_line(pc.name, best[1], rgb, gauge_m=gauge)


# ----------------------------------------------------------------------------------------------- H1  ROSE ORBITE
def h1_rose(man, colorway="rose", out="h1", rib_h=0.085, cuff_h=0.075, sc=1.0):
    P = dict(PAL)
    cw = {"rose": dict(fabric=P["rose"], rib=P["rose_d"] if "rose_d" in P else "#B87B83", thread=P["chalk"], accent=P["maroon"],
                       patch_bg=P["nuit"], patch_fg=P["chalk"], patch_acc=P["rose"]),
          "chalk": dict(fabric="#EFEBE2", rib="#D5CFC1", thread=P["nuit"], accent=P["rose"], patch_bg=P["nuit"], patch_fg=P["chalk"], patch_acc=P["rose"]),
          "nuit": dict(fabric="#0F1730", rib="#0A0F20", thread=P["rose"], accent=P["chalk"], patch_bg=P["rose"], patch_fg=P["nuit"], patch_acc=P["maroon"])}[colorway]
    A = Atlas(man)
    A.fabric(hex2rgb(cw["fabric"]), rough=0.94, grain=0.07, nap=0.6)
    # rib hem (all body pieces) and rib cuffs (sleeves)
    for nm in ("Front_L", "Front_R", "Back"):
        pc = Pc(man, nm)
        A.rib(A.zone(pc.name, pc.l - 0.01, pc.bot - 0.01, pc.r + 0.01, pc.bot + rib_h), hex2rgb(cw["rib"]), vertical=True)
    for nm in ("Sleeve_L", "Sleeve_R"):
        pc = Pc(man, nm)
        A.rib(A.zone(pc.name, pc.l - 0.01, pc.bot - 0.01, pc.r + 0.01, pc.bot + cuff_h), hex2rgb(cw["rib"]), vertical=True)
    thread = hex2rgb(cw["thread"])
    stitch_seams(A, man, hex2rgb(cw["fabric"]) * 0.82, {"Front_L": ["side_L", "shoulder_L", "arm_L"], "Front_R": ["side_R", "shoulder_R", "arm_R"],
                                                         "Back": ["side_L", "side_R", "shoulder_L", "shoulder_R", "arm_L", "arm_R"]})
    # yoke seam across the back and fronts (ref 1): a topstitched seam 0.19 m below the shoulder line
    for nm in ("Back", "Front_L", "Front_R"):
        pc = Pc(man, nm)
        z = pc.from_top(0.215)
        A.stitch_line(pc.name, [(pc.l + 0.004, z), (pc.r - 0.004, z)], hex2rgb(cw["fabric"]) * 0.78, gauge_m=0.0026)
        A.stitch_line(pc.name, [(pc.l + 0.004, z - 0.006), (pc.r - 0.004, z - 0.006)], hex2rgb(cw["fabric"]) * 0.78, gauge_m=0.0026)
    # hem + cuff topstitch
    for nm in ("Front_L", "Front_R", "Back"):
        pc = Pc(man, nm)
        for dz in (rib_h, rib_h + 0.007):
            A.stitch_line(pc.name, [(pc.l + 0.004, pc.bot + dz), (pc.r - 0.004, pc.bot + dz)], hex2rgb(cw["fabric"]) * 0.75, gauge_m=0.0026)

    # --- left-chest woven crest patch (7 cm), on Front_L (wearer's left)
    fl = Pc(man, "Front_L")
    crest = ART.crest_svg(APAL | {}, fg=cw["patch_bg"], bg=cw["patch_fg"], accent=cw["patch_acc"], R=300)
    layer = A.place(fl.name, crest, 0.072, fl.from_cf(0.105), fl.from_top(0.185))
    A.weave(layer, rough=0.62, relief_m=0.0010)
    # merrowed border: a ring of satin stitch around the patch
    ring = ART.svg(640, 640, f'<circle cx="320" cy="320" r="302" fill="none" stroke="{cw["patch_fg"]}" stroke-width="16"/>')
    A.emb(A.place(fl.name, ring, 0.072, fl.from_cf(0.105), fl.from_top(0.185)), thread_angle_deg=0, pitch_m=0.0007, relief_m=0.0016)

    # --- script on the left sleeve (embroidered, runs down the arm): "Bac Sciences" + 2027
    sl = Pc(man, "Sleeve_L")
    scr = ART.script_svg(APAL, "Bac Sciences", fill=cw["thread"], size=300)
    lay = A.place(sl.name, scr, 0.185, 0.0, sl.from_top(0.34), rot=90)
    A.emb(lay, thread_angle_deg=60, pitch_m=0.0007, relief_m=0.0011, pillow_m=0.0005, rough=0.38)
    yr = ART.numerals_svg(APAL, fill=cw["thread"], size=200)
    lay = A.place(sl.name, yr, 0.05, 0.0, sl.from_bot(cuff_h + 0.075), rot=90)
    A.emb(lay, thread_angle_deg=0, pitch_m=0.0007, relief_m=0.0013)

    # --- back yoke: periodic tiles B Ac Sc I (embroidered), caption under
    bk = Pc(man, "Back")
    tiles = ART.tiles_svg(APAL, scheme="category", s=200, gap=22)
    lay = A.place(bk.name, tiles, 0.33, 0.0, bk.from_top(0.125))
    A.emb(lay, thread_angle_deg=40, pitch_m=0.0007, relief_m=0.0012, pillow_m=0.0006)
    cap_txt = "TÉBOURBA · 36°50′N 9°50′E · BAC SCIENCES 2027"
    cw_ = ART.text_w(cap_txt, "mono", 44, 200, wght=500) + 40
    cap = ART.svg(cw_, 70, ART.T(cap_txt, "mono", 44, cw_ / 2, 52, cw["thread"], "middle", tracking=200, wght=500))
    A.emb(A.place(bk.name, cap, cw_ * 0.000125, 0.0, bk.from_top(0.255)), thread_angle_deg=0, pitch_m=0.0007, relief_m=0.0008, pillow_m=0.0003)

    # --- woven hem label on the left front hem
    lab = ART.woven_label_svg(APAL, bg=P["nuit"], ink=P["chalk"], accent=P["rose"])
    A.weave(A.place(fl.name, lab, 0.06, fl.from_cf(0.30), fl.from_bot(rib_h + 0.032)), rough=0.6)

    # --- motto on the hood (outer side of Hood_L)
    try:
        hd = Pc(man, "Hood_L")
        mo = ART.motto_svg(APAL, ink=cw["thread"], accent=P["chalk"], W=1500)
        A.emb(A.place(hd.name, mo, 0.17, 0.0, hd.from_top(0.12)), thread_angle_deg=20, pitch_m=0.0007, relief_m=0.0009, pillow_m=0.0004)
    except KeyError:
        pass
    outdir = TEX / out
    files = A.export(outdir, colorway)
    return dict(dir=str(outdir), files=files)


# ----------------------------------------------------------------------------------------------- H1 (shell)
def h1_shell(man, colorway="rose", out="h1s", rib_h=0.09, cuff_h=0.075, collar_h=0.05):
    P = dict(PAL)
    cwd = {"rose": dict(fabric=P["rose"], rib="#B07880", thread=P["chalk"], accent=P["maroon"], patch_bg=P["nuit"], patch_fg=P["chalk"], patch_acc=P["rose"]),
           "chalk": dict(fabric="#EFEBE2", rib="#D5CFC1", thread=P["nuit"], accent=P["rose"], patch_bg=P["nuit"], patch_fg=P["chalk"], patch_acc=P["rose"]),
           "nuit": dict(fabric="#0F1730", rib="#0A0F20", thread=P["rose"], accent=P["chalk"], patch_bg=P["rose"], patch_fg=P["nuit"], patch_acc=P["maroon"])}[colorway]
    meta = man["meta"]
    A = Atlas(man)
    A.fabric(hex2rgb(cwd["fabric"]), rough=0.94, grain=0.07, nap=0.6)
    fab = hex2rgb(cwd["fabric"]); rib = hex2rgb(cwd["rib"]); thread = hex2rgb(cwd["thread"])
    hz, nz = meta["hem_z"], meta["neck_z"]
    for nm in ("Front", "Back"):
        pc = Pc(man, nm)
        A.rib(A.zone(pc.name, pc.l - 0.01, hz - 0.02, pc.r + 0.01, hz + rib_h), rib)
        A.rib(A.zone(pc.name, -0.125, nz - collar_h, 0.125, pc.top + 0.02), rib)
        for dz in (rib_h, rib_h + 0.007):
            A.stitch_line(pc.name, [(pc.l + 0.004, hz + dz), (pc.r - 0.004, hz + dz)], fab * 0.75, gauge_m=0.0026)
        z = meta["shoulder_z"] - 0.19                                           # yoke seam
        for dz in (0, 0.006):
            A.stitch_line(pc.name, [(pc.l + 0.004, z - dz), (pc.r - 0.004, z - dz)], fab * 0.78, gauge_m=0.0026)
    L = meta["chain_len"]
    for nm in ("Sleeve_L", "Sleeve_R"):
        pc = Pc(man, nm)
        A.rib(A.zone(pc.name, pc.l - 0.01, pc.bot - 0.02, pc.r + 0.01, -(L * meta["cuff_t"] - cuff_h)), rib)
        for dz in (cuff_h, cuff_h + 0.007):
            zc = -(L * meta["cuff_t"] - dz)
            A.stitch_line(pc.name, [(pc.l + 0.004, zc), (pc.r - 0.004, zc)], fab * 0.75, gauge_m=0.0026)
    fl = Pc(man, "Front")
    # zip placket: two topstitched lines either side of the centre front
    for x in (-0.011, 0.011):
        A.stitch_line("Front", [(x, nz - collar_h * 0.6), (x, hz + rib_h)], fab * 0.76, gauge_m=0.0026)
    chest_z = meta["chest_z"] + 0.02
    crest = ART.crest_svg(APAL, fg=cwd["patch_bg"], bg=cwd["patch_fg"], accent=cwd["patch_acc"], R=300)
    sp = A.place("Front", crest, 0.075, 0.105, chest_z)
    A.weave(sp, rough=0.62, relief_m=0.0010)
    ring = ART.svg(640, 640, f'<circle cx="320" cy="320" r="302" fill="none" stroke="{cwd["patch_fg"]}" stroke-width="16"/>')
    A.emb(A.place("Front", ring, 0.075, 0.105, chest_z), thread_angle_deg=0, pitch_m=0.0007, relief_m=0.0016)
    scr = ART.script_svg(APAL, "Bac Sciences", fill=cwd["thread"], size=300)
    A.emb(A.place("Sleeve_L", scr, 0.19, 0.0, -0.30, rot=90), thread_angle_deg=60, pitch_m=0.0007, relief_m=0.0011, pillow_m=0.0005, rough=0.38)
    yr = ART.numerals_svg(APAL, fill=cwd["thread"], size=200)
    A.emb(A.place("Sleeve_L", yr, 0.05, 0.0, -(L * meta["cuff_t"] - cuff_h - 0.09), rot=90), thread_angle_deg=0, pitch_m=0.0007, relief_m=0.0013)
    tiles = ART.tiles_row_svg(APAL, fills=[cwd["thread"], P["violet"], P["blue"], P["nuit"]], inks=[P["nuit"], P["chalk"], P["chalk"], P["chalk"]])
    A.emb(A.place("Back", tiles, 0.27, 0.0, meta["shoulder_z"] - 0.17), thread_angle_deg=40, pitch_m=0.0007, relief_m=0.0012, pillow_m=0.0006)
    cap_txt = "TÉBOURBA · 36°50′N 9°50′E · BAC SCIENCES 2027"
    cw_ = ART.text_w(cap_txt, "mono", 44, 200, wght=500) + 40
    cap = ART.svg(cw_, 70, ART.T(cap_txt, "mono", 44, cw_ / 2, 52, cwd["thread"], "middle", tracking=200, wght=500))
    A.emb(A.place("Back", cap, cw_ * 0.000125, 0.0, meta["shoulder_z"] - 0.235), thread_angle_deg=0, pitch_m=0.0007, relief_m=0.0008, pillow_m=0.0003)
    lab = ART.woven_label_svg(APAL, bg=P["nuit"], ink=P["chalk"], accent=P["rose"])
    A.weave(A.place("Front", lab, 0.075, 0.215, hz + rib_h + 0.032), rough=0.6, relief_m=0.0006)
    outdir = TEX / out
    files = A.export(outdir, colorway)
    return dict(dir=str(outdir), files=files)


def hood_tex(man_hood, colorway="rose", out="h1s", motto=True, rib=False):
    """Texture set for the hood object (own atlas): fabric + lining-side motto embroidery."""
    P = dict(PAL)
    cwd = {"rose": dict(fabric=P["rose"], thread=P["chalk"]), "chalk": dict(fabric="#EFEBE2", thread=P["nuit"]),
           "nuit": dict(fabric="#0F1730", thread=P["rose"])}[colorway]
    A = Atlas(man_hood, size=2048)
    A.fabric(hex2rgb(cwd["fabric"]), rough=0.94, grain=0.07, nap=0.6)
    if motto:
        mo = ART.motto_svg(APAL, ink=cwd["thread"], accent=P["chalk"], W=1500)
        A.emb(A.place("Hood", mo, 0.20, 0.0, -0.17), thread_angle_deg=20, pitch_m=0.0007, relief_m=0.0009, pillow_m=0.0004)
    return A.export(TEX / out, colorway + "_hood")
