"""Designs for the remaining garments (shell UV space).  Same conventions as designs.py:
Front/Back local x = arc length from the centre line (m), z = world height (m);  Sleeve_L/R: x = r*theta, z = -distance from the shoulder.
Every function: f(man, colorway, out) -> files dict.  Needs system python (fontTools, uharfbuzz, rdkit, scipy)."""
import sys, math
from pathlib import Path
import numpy as np
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE)); sys.path.insert(0, str(HERE / "art"))
import texlab
from texlab import Atlas, hex2rgb, srgb2lin
from collection import PAL
import art3d as ART
from lib import PAL as APAL, lum, svg as SVG, T as TXT, text_w as TXTW
import designs as D1
from designs import TEX, Pc

P = dict(PAL)


def ink_on(bg_hex):
    return P["nuit"] if lum(bg_hex) > 0.28 else P["chalk"]


def start(man, rgb, kind, **kw):
    A = Atlas(man)
    A.fabric(hex2rgb(rgb), kind=kind, **kw)
    return A


def sleeve_end(meta):
    """z (local, negative) of the sleeve end for tees (cut along the upper arm)."""
    return -meta["upper_len"] * meta["arm_cut"]


def stitch_edges(A, man, rgb, meta, hem=True, sleeve=True, d=0.018):
    fab = hex2rgb(rgb) * 0.78
    hz = meta["hem_z"]
    if hem:
        for nm in ("Front", "Back"):
            pc = Pc(man, nm)
            for dz in (d, d + 0.006):
                A.stitch_line(nm, [(pc.l + 0.005, hz + dz), (pc.r - 0.005, hz + dz)], fab, gauge_m=0.0026)
    if sleeve:
        for nm in ("Sleeve_L", "Sleeve_R"):
            pc = Pc(man, nm)
            ze = sleeve_end(meta)
            for dz in (0.016, 0.022):
                A.stitch_line(nm, [(pc.l + 0.005, ze + dz), (pc.r - 0.005, ze + dz)], fab, gauge_m=0.0026)


def collar_rib(A, man, meta, rgb):
    A.rib(A.tag_mask("collar"), hex2rgb(rgb), pitch_m=0.0030, depth_m=0.0005)


# ===================================================================================== T1 NUIT
def t1_nuit(man, colorway="nuit", out="T1"):
    cw = {"nuit": "#0F1730", "chalk": "#EFEBE2", "rose": "#D9A3A8"}[colorway]
    ink = ink_on(cw)
    meta = man["meta"]
    A = start(man, cw, "jersey")
    rib = {"nuit": "#0A1024", "chalk": "#DCD6C8", "rose": "#C48C92"}[colorway]
    collar_rib(A, man, meta, rib)
    stitch_edges(A, man, cw, meta)
    # left chest: tiny embroidered DNA (ref 4: small DNA at left chest)
    strand = ink
    rungs = {"A": P["violet"], "T": P["rose"] if colorway != "rose" else P["maroon"], "G": P["blue"], "C": ink}
    d1 = ART.dna_tall_svg(APAL, ink=strand, H=600)
    A.emb(A.place("Front", d1, 0.016, 0.095, meta["chest_z"] + 0.03), thread_angle_deg=60, pitch_m=0.0007, relief_m=0.0011, pillow_m=0.0004)
    # back: tall clean DNA + tagline (screen print)
    bases = "ATGCCGTAGCATTGCAGTCA"
    d2 = ART.dna_tall_svg(APAL, ink=ink, H=1000, strand=ink, letters=True, bases=bases, tagline="ON NAÎT UNIQUE", tag_col=ink)
    A.print_(A.place("Back", d2, 0.115, 0.0, meta["shoulder_z"] - 0.205), rough=0.58, relief_m=0.0003)
    return A.export(TEX / out, colorway)


# ===================================================================================== T2 TABLEAU
def t2_tableau(man, colorway="chalk", out="T2"):
    cw = {"chalk": "#EFEBE2", "lab": "#8E959E", "maroon": "#5C1526"}[colorway]
    ink = ink_on(cw)
    meta = man["meta"]
    A = start(man, cw, "jersey", grain=0.05)
    collar_rib(A, man, meta, {"chalk": "#DCD6C8", "lab": "#7C838C", "maroon": "#4B1020"}[colorway])
    stitch_edges(A, man, cw, meta)
    fills = {"chalk": [P["rose"], P["violet"], P["blue"], P["nuit"]],
             "lab": [P["chalk"], P["violet"], P["blue"], P["nuit"]],
             "maroon": [P["rose"], P["violet"], P["blue"], P["chalk"]]}[colorway]
    inks = [ink_on("#%02x%02x%02x" % tuple(int(c * 255) for c in hex2rgb(f))) for f in fills]
    tiles = ART.tiles_row_svg(APAL, fills=fills, inks=inks, s=200, gap=16)
    A.print_(A.place("Front", tiles, 0.40, 0.0, meta["chest_z"] - 0.02), rough=0.60, relief_m=0.0003)
    sub = SVG(900, 60, TXT("B  ·  AC  ·  SC  ·  I   =   BAC  SCI", "mono", 38, 450, 44, ink, "middle", tracking=300, wght=500))
    A.print_(A.place("Front", sub, 0.20, 0.0, meta["chest_z"] - 0.105), rough=0.6, relief_m=0.0002)
    n = ART.numerals_svg(APAL, fill=ink, size=300)
    A.print_(A.place("Back", n, 0.32, 0.0, meta["shoulder_z"] - 0.15), rough=0.58, relief_m=0.0003)
    cap = SVG(1000, 70, TXT("TÉBOURBA · BAC SCIENCES · LYCÉE HANNIBAL", "mono", 38, 500, 50, ink, "middle", tracking=240, wght=500))
    A.print_(A.place("Back", cap, 0.24, 0.0, meta["shoulder_z"] - 0.255), rough=0.6, relief_m=0.0002)
    sc = ART.tile_square_svg(APAL, "Sc", s=300, fill=fills[2], ink=inks[2], label=False)
    A.emb(A.place("Sleeve_R", sc, 0.040, 0.0, sleeve_end(meta) + 0.065), thread_angle_deg=45, pitch_m=0.0007, relief_m=0.0011)
    return A.export(TEX / out, colorway)


# ===================================================================================== T3 CAFEINE
def t3_cafeine(man, colorway="lab", out="T3"):
    cw = {"lab": "#A3A9B1", "rose": "#D9A3A8", "nuit": "#0F1730"}[colorway]
    ink = ink_on(cw)
    meta = man["meta"]
    A = start(man, cw, "jersey")
    collar_rib(A, man, meta, {"lab": "#8E959E", "rose": "#C48C92", "nuit": "#0A1024"}[colorway])
    stitch_edges(A, man, cw, meta)
    mol = ART.caffeine_svg(APAL, ink=ink, accent=P["violet"], size=900, line=3.4)
    A.print_(A.place("Front", mol, 0.30, 0.0, meta["chest_z"] - 0.012), rough=0.6, relief_m=0.0003)
    f = SVG(900, 150, TXT("C₈H₁₀N₄O₂", "mono", 74, 450, 80, ink, "middle", tracking=60, wght=600)
            + TXT("CAFÉINE · 1,3,7-TRIMÉTHYLXANTHINE · 194,19 g·mol⁻¹", "mono", 21, 450, 128, ink, "middle", tracking=100, wght=500))
    A.print_(A.place("Front", f, 0.26, 0.0, meta["chest_z"] - 0.145), rough=0.6, relief_m=0.0002)
    pun = ART.punnett_svg(APAL, ink=ink, accent=P["violet"] if colorway != "nuit" else P["blue"])
    A.print_(A.place("Back", pun, 0.25, 0.0, meta["shoulder_z"] - 0.20), rough=0.6, relief_m=0.0003)
    return A.export(TEX / out, colorway)


# ===================================================================================== H2 GRIS COLLEGE
def h2_gris(man, colorway="lab", out="H2", rib_h=0.09, cuff_h=0.075):
    cw = {"lab": "#8E959E", "chalk": "#EFEBE2", "maroon": "#5C1526"}[colorway]
    ink = ink_on(cw)
    rib = {"lab": "#7B828B", "chalk": "#D9D3C5", "maroon": "#4A0F1F"}[colorway]
    meta = man["meta"]
    A = start(man, cw, "fleece" if False else None, rough=0.94, grain=0.07, nap=0.6)
    A.rib(A.tag_mask("hem"), hex2rgb(rib)); A.rib(A.tag_mask("cuff"), hex2rgb(rib)); A.rib(A.tag_mask("collar"), hex2rgb(rib))
    fab = hex2rgb(cw)
    hz = meta["hem_z"]
    for nm in ("Front", "Back"):
        pc = Pc(man, nm)
        for dz in (rib_h, rib_h + 0.007):
            A.stitch_line(nm, [(pc.l + 0.004, hz + dz), (pc.r - 0.004, hz + dz)], fab * 0.75, gauge_m=0.0026)
    # kangaroo pocket: stitched outline + opening slits (front)
    zt, zb = hz + 0.30, hz + rib_h + 0.045
    xs = 0.185
    pocket = [(-xs, zt), (xs, zt), (xs * 0.92, zb), (-xs * 0.92, zb), (-xs, zt)]
    for off in (0.0, 0.006):
        A.stitch_line("Front", [(x, z - (off if i < 2 else 0)) for i, (x, z) in enumerate(pocket)], fab * 0.72, gauge_m=0.0026)
    for sgn in (-1, 1):                                 # hand openings: dark slit with edge stitching
        sx0, sx1, sz0, sz1 = sgn * xs * 0.97, sgn * xs * 0.62, zt - 0.045, zt - 0.115
        slit = [(sx0, sz0), (sx1, sz1)]
        A.stitch_line("Front", slit, fab * 0.55, gauge_m=0.0016, width_m=0.0022)
    # chest: embroidered wordmark (left chest) + year
    wm = ART.wordmark_svg(APAL, fill=ink, kicker=True, foot=False, size=100)
    A.emb(A.place("Front", wm, 0.115, 0.105, meta["chest_z"] + 0.035), thread_angle_deg=35, pitch_m=0.0007, relief_m=0.0011, pillow_m=0.0005)
    # back collage (print on fabric): ink / accent / background fill colours per colourway
    acc = P["rose"] if colorway != "maroon" else P["chalk"]
    col = ART.collage_svg(APAL, ink=ink, accent=(P["violet"] if colorway == "chalk" else acc), bg=cw)
    A.print_(A.place("Back", col, 0.40, 0.0, meta["shoulder_z"] - 0.19), rough=0.6, relief_m=0.0004)
    # sleeves: 2027 above the cuff on the left, HANNIBAL down the right
    yr = ART.numerals_svg(APAL, fill=ink, size=200)
    L = meta["chain_len"]
    A.emb(A.place("Sleeve_L", yr, 0.05, 0.0, -(L * meta["cuff_t"] - 0.075 - 0.09), rot=90), thread_angle_deg=0, pitch_m=0.0007, relief_m=0.0013)
    hw = ART.wordmark_svg(APAL, fill=ink, kicker=False, foot=False, size=100)
    A.emb(A.place("Sleeve_R", hw, 0.22, 0.0, -0.30, rot=-90), thread_angle_deg=30, pitch_m=0.0007, relief_m=0.0012, pillow_m=0.0005)
    lab = ART.woven_label_svg(APAL, bg=P["nuit"], ink=P["chalk"], accent=P["rose"])
    A.weave(A.place("Front", lab, 0.075, 0.215, hz + rib_h + 0.032), rough=0.6, relief_m=0.0006)
    return A.export(TEX / out, colorway)


# ===================================================================================== H3 NUIT COSMIQUE
def h3_cosmique(man, colorway="nuit", out="H3", rib_h=0.08, cuff_h=0.07):
    cw = {"nuit": "#0B1226", "violet": "#4B36B8", "lab": "#4B525C"}[colorway]
    ink = P["chalk"]
    rib = {"nuit": "#070C1C", "violet": "#3A2994", "lab": "#3A4048"}[colorway]
    meta = man["meta"]
    A = start(man, cw, "nylon" if False else None, rough=0.55, grain=0.05, nap=0.2)       # technical fleece face: slightly sleek
    A.rib(A.tag_mask("hem"), hex2rgb(rib)); A.rib(A.tag_mask("cuff"), hex2rgb(rib)); A.rib(A.tag_mask("collar"), hex2rgb(rib))
    fab = hex2rgb(cw)
    hz = meta["hem_z"]
    for nm in ("Front", "Back"):
        pc = Pc(man, nm)
        for dz in (rib_h, rib_h + 0.007):
            A.stitch_line(nm, [(pc.l + 0.004, hz + dz), (pc.r - 0.004, hz + dz)], fab * 1.9 + 0.02, gauge_m=0.0026)
    for x in (-0.011, 0.011):
        A.stitch_line("Front", [(x, meta["neck_z"] - 0.02), (x, hz + rib_h)], fab * 2.0 + 0.02, gauge_m=0.0026)
    crest = ART.crest_svg(APAL, fg=P["nuit"], bg=P["chalk"], ring=P["chalk"], accent=P["violet"], R=300)
    A.emb(A.place("Front", crest, 0.052, 0.105, meta["chest_z"] + 0.03), thread_angle_deg=40, pitch_m=0.0007, relief_m=0.0011)
    cos = ART.cosmic_svg(APAL, R=800, quote=True)
    A.print_(A.place("Back", cos, 0.40, 0.0, meta["shoulder_z"] - 0.22), rough=0.5, relief_m=0.0003)
    # orbit band down each sleeve (repeat cell), violet/chalk
    cell = ART.orbit_cell_svg(APAL, s=300, ink=P["chalk"], accent=P["violet"])
    L = meta["chain_len"]
    for nm in ("Sleeve_L", "Sleeve_R"):
        sp = A.tile_strip(nm, cell, -0.036, 0.036, -0.10, -(L * meta["cuff_t"] - 0.12), 0.072)
        A.print_(sp, rough=0.5, relief_m=0.0002, opacity=0.9)
    lab = ART.woven_label_svg(APAL, bg=P["violet"], ink=P["chalk"], accent=P["chalk"])
    A.weave(A.place("Front", lab, 0.075, 0.215, hz + rib_h + 0.032), rough=0.6, relief_m=0.0006)
    return A.export(TEX / out, colorway)


# ===================================================================================== J1 VARSITY
def _stripes_rib(A, man, meta, rib_rgb, stripe_rgb):
    if isinstance(stripe_rgb, str):
        stripe_rgb = hex2rgb(stripe_rgb)
    A.rib(A.tag_mask("hem"), hex2rgb(rib_rgb), pitch_m=0.0042); A.rib(A.tag_mask("cuff"), hex2rgb(rib_rgb), pitch_m=0.0042)
    A.rib(A.tag_mask("collar"), hex2rgb(rib_rgb), pitch_m=0.0042)
    hz = meta["hem_z"]
    hm = A.tag_mask("hem")
    for dz in (0.034, 0.048):
        A.band(hm, hz + dz, hz + dz + 0.0065, ["Front", "Back"], stripe_rgb)
    cm = A.tag_mask("cuff")
    L = meta["chain_len"]; zc = -(L * meta["cuff_t"])
    for dz in (0.028, 0.042):
        A.band(cm, zc + dz, zc + dz + 0.0065, ["Sleeve_L", "Sleeve_R"], stripe_rgb)
    nm = A.tag_mask("collar")
    nz = meta["neck_z"]
    for dz in (0.013, 0.026):
        A.band(nm, nz + dz, nz + dz + 0.0055, ["Front", "Back"], stripe_rgb)


def j1_varsity(man, colorway="nuit-rose", out="J1"):
    body, sleeve = {"nuit-rose": ("#0F1730", "#D9A3A8"), "maroon-chalk": ("#5C1526", "#EFEBE2")}[colorway]
    ink = ink_on(body); sink = ink_on(sleeve)
    meta = man["meta"]
    A = start(man, body, "melton")
    A.fabric(hex2rgb(sleeve), kind="leather", mask=A.piece_mask_of("Sleeve_L", "Sleeve_R"))
    rib = "#EFEBE2" if colorway == "nuit-rose" else "#EFEBE2"
    stripe = P["rose"] if colorway == "nuit-rose" else P["maroon"]
    _stripes_rib(A, man, meta, rib, stripe)
    hz = meta["hem_z"]
    fab = hex2rgb(body)
    # placket + snap line stitching, yoke / shoulder seams
    for x in (-0.012, 0.012):
        A.stitch_line("Front", [(x, meta["neck_z"] - 0.01), (x, hz + 0.085)], fab * 1.8 + 0.02, gauge_m=0.0030)
    # left chest: chenille H on felt
    h = ART.chenille_letter_svg(APAL, letter="H", fill=sleeve, border=P["chalk"], size=520)
    A.emb(A.place("Front", h, 0.105, 0.105, meta["chest_z"] + 0.02), thread_angle_deg=70, pitch_m=0.0011, relief_m=0.0028, pillow_m=0.0016, rough=0.85, shade=0.5)
    # sleeve patches
    L = meta["chain_len"]
    yr = SVG(520, 230, f'<rect width="520" height="230" rx="30" fill="{P["nuit"]}"/><rect x="10" y="10" width="500" height="210" rx="22" fill="none" stroke="{P["chalk"]}" stroke-width="8"/>'
                        + ART.ID.numerals(120, P["chalk"], 260, 160, tracking=40, anchor="middle")[0])
    A.weave(A.place("Sleeve_L", yr, 0.064, 0.0, -0.205, rot=90), rough=0.62, relief_m=0.0010)
    crest = ART.crest_svg(APAL, fg=P["nuit"], bg=P["chalk"], accent=P["rose"], R=300)
    A.weave(A.place("Sleeve_R", crest, 0.058, 0.0, -0.205), rough=0.62, relief_m=0.0010)
    # back: arched SCIENCES (embroidery), Surus crest, caption
    arch = ART.varsity_text_svg(APAL, "SCIENCES", fill=sleeve if colorway == "nuit-rose" else P["chalk"], outline=P["chalk"] if colorway == "nuit-rose" else P["rose"], arc=520, size=170)
    A.emb(A.place("Back", arch, 0.33, 0.0, meta["shoulder_z"] - 0.13), thread_angle_deg=50, pitch_m=0.0010, relief_m=0.0020, pillow_m=0.0012, rough=0.55)
    crest2 = ART.crest_svg(APAL, fg=P["nuit"], bg=P["chalk"], accent=P["rose"], R=300)
    A.emb(A.place("Back", crest2, 0.125, 0.0, meta["shoulder_z"] - 0.285), thread_angle_deg=40, pitch_m=0.0007, relief_m=0.0011)
    cap = SVG(900, 60, TXT("TÉBOURBA · 36°50′N 9°50′E · PROMO 2027", "mono", 38, 450, 44, ink, "middle", tracking=240, wght=500))
    A.emb(A.place("Back", cap, 0.20, 0.0, meta["shoulder_z"] - 0.395), thread_angle_deg=0, pitch_m=0.0007, relief_m=0.0008, pillow_m=0.0003)
    return A.export(TEX / out, colorway)


# ===================================================================================== J2 COACH
def j2_coach(man, colorway="lab", out="J2"):
    cw = {"lab": "#B7BCC3", "nuit": "#0F1730"}[colorway]
    ink = ink_on(cw)
    meta = man["meta"]
    A = start(man, cw, "nylon")
    fab = hex2rgb(cw)
    hz = meta["hem_z"]
    for nm in ("Front", "Back"):                                     # elastic hem channel
        pc = Pc(man, nm)
        for dz in (0.03, 0.036):
            A.stitch_line(nm, [(pc.l + 0.004, hz + dz), (pc.r - 0.004, hz + dz)], fab * 0.8, gauge_m=0.0026)
    for x in (-0.012, 0.012):
        A.stitch_line("Front", [(x, meta["neck_z"] - 0.01), (x, hz + 0.02)], fab * 0.8, gauge_m=0.0030)
    L = meta["chain_len"]
    for nm in ("Sleeve_L", "Sleeve_R"):                              # sleeve cuff channel
        pc = Pc(man, nm)
        zc = -(L * meta["cuff_t"])
        for dz in (0.04, 0.046):
            A.stitch_line(nm, [(pc.l + 0.004, zc + dz), (pc.r - 0.004, zc + dz)], fab * 0.8, gauge_m=0.0026)
    wm = ART.wordmark_svg(APAL, fill=ink, kicker=False, foot=False, size=100)
    A.emb(A.place("Front", wm, 0.075, 0.105, meta["chest_z"] + 0.035), thread_angle_deg=35, pitch_m=0.0007, relief_m=0.0010, pillow_m=0.0004)
    mol = ART.caffeine_svg(APAL, ink=ink, accent=P["violet"], size=900, line=3.4)
    A.print_(A.place("Back", mol, 0.31, 0.0, meta["shoulder_z"] - 0.20), rough=0.45, relief_m=0.0003)
    f = SVG(900, 130, TXT("C₈H₁₀N₄O₂", "mono", 64, 450, 70, ink, "middle", tracking=60, wght=600) + TXT("BAC SCIENCES 2027", "mono", 22, 450, 112, ink, "middle", tracking=300, wght=500))
    A.print_(A.place("Back", f, 0.22, 0.0, meta["shoulder_z"] - 0.375), rough=0.5, relief_m=0.0002)
    return A.export(TEX / out, colorway)


# ===================================================================================== V1 GILET VARSITY
def v1_gilet(man, colorway="nuit", out="V1"):
    body = {"nuit": "#0F1730", "maroon": "#5C1526"}[colorway]
    ink = ink_on(body)
    meta = man["meta"]
    A = start(man, body, "melton")
    rib = "#EFEBE2"; stripe = P["rose"] if colorway == "nuit" else P["rose"]
    A.rib(A.tag_mask("hem"), hex2rgb(rib), pitch_m=0.0042); A.rib(A.tag_mask("cuff"), hex2rgb(rib), pitch_m=0.0042); A.rib(A.tag_mask("collar"), hex2rgb(rib), pitch_m=0.0042)
    hz = meta["hem_z"]
    hm = A.tag_mask("hem")
    for dz in (0.028, 0.040):
        A.band(hm, hz + dz, hz + dz + 0.0058, ["Front", "Back"], stripe)
    nm = A.tag_mask("collar"); nz = meta["neck_z"]
    for dz in (0.012, 0.024):
        A.band(nm, nz + dz, nz + dz + 0.005, ["Front", "Back"], stripe)
    fab = hex2rgb(body)
    for x in (-0.012, 0.012):
        A.stitch_line("Front", [(x, meta["neck_z"] - 0.01), (x, hz + 0.07)], fab * 1.8 + 0.02, gauge_m=0.0030)
    crest = ART.crest_svg(APAL, fg=P["nuit"], bg=P["chalk"], accent=P["rose"], R=300)
    A.weave(A.place("Front", crest, 0.074, 0.105, meta["chest_z"] + 0.03), rough=0.62, relief_m=0.0010)
    arch = ART.varsity_text_svg(APAL, "SCIENCES", fill=P["chalk"], outline=P["rose"], arc=520, size=170)
    A.emb(A.place("Back", arch, 0.33, 0.0, meta["shoulder_z"] - 0.13), thread_angle_deg=50, pitch_m=0.0010, relief_m=0.0020, pillow_m=0.0012, rough=0.55)
    s = ART.surus_svg(APAL, fg=P["chalk"], accent=P["rose"])
    A.emb(A.place("Back", s, 0.17, 0.0, meta["shoulder_z"] - 0.285), thread_angle_deg=40, pitch_m=0.0007, relief_m=0.0011)
    yr = ART.numerals_svg(APAL, fill=P["rose"], size=200)
    A.emb(A.place("Back", yr, 0.13, 0.0, meta["shoulder_z"] - 0.375), thread_angle_deg=0, pitch_m=0.0007, relief_m=0.0012)
    return A.export(TEX / out, colorway)


# ===================================================================================== V2 COUCHE LABO (puffer)
def v2_couche(man, colorway="lab", out="V2"):
    cw = {"lab": "#8E959E", "rose": "#D9A3A8"}[colorway]
    ink = ink_on(cw)
    meta = man["meta"]
    A = start(man, cw, "nylon")
    body_mask = A.piece_mask_of("Front", "Back")
    A.quilt(body_mask & ~A.tag_mask("collar"), pitch_m=0.080, puff_m=0.008)
    # collar: funnel, smooth with 1 channel
    # tonal orbit repeat over the back, low contrast
    cell = ART.orbit_cell_svg(APAL, s=300, ink=ink, accent=ink, stars=True)
    bk = Pc(man, "Back")
    sp = A.tile_strip("Back", cell, -0.27, 0.27, meta["shoulder_z"] - 0.45, meta["shoulder_z"] - 0.06, 0.11)
    A.print_(sp, rough=0.42, relief_m=0.0002, opacity=0.34)
    sp = A.tile_strip("Front", cell, -0.27, 0.27, meta["hem_z"] + 0.04, meta["chest_z"] - 0.2, 0.11)
    A.print_(sp, rough=0.42, relief_m=0.0002, opacity=0.22)
    for x in (-0.011, 0.011):
        A.stitch_line("Front", [(x, meta["neck_z"] - 0.02), (x, meta["hem_z"] + 0.02)], hex2rgb(cw) * 0.75, gauge_m=0.0028)
    lab = ART.woven_label_svg(APAL, bg=P["nuit"], ink=P["chalk"], accent=P["violet"])
    A.weave(A.place("Front", lab, 0.075, 0.105, meta["chest_z"] + 0.04), rough=0.6, relief_m=0.0006)
    wm = ART.wordmark_svg(APAL, fill=ink, kicker=False, foot=False, size=100)
    A.emb(A.place("Back", wm, 0.16, 0.0, meta["shoulder_z"] - 0.055), thread_angle_deg=35, pitch_m=0.0007, relief_m=0.0010, pillow_m=0.0004)
    return A.export(TEX / out, colorway)
