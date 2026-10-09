"""Original artwork for the BAC SCIENCES 2027 3D collection (Lycée Hannibal, Tébourba).

All type is converted to outlines (HarfBuzz shaping + fontTools), so SVGs are font-independent and
French accents / Arabic joining are real glyphs, never raster text.  Every function returns an SVG
string with a transparent background; colours are parameters so each colourway can recolour art.

Scientific content (checked):
  * tiles   B  Z=5  Bore      10,81     (metalloid)
            Ac Z=89 Actinium  [227]     (actinide)
            Sc Z=21 Scandium  44,956    (transition metal)
            I  Z=53 Iode      126,90    (halogen)          ->  B·Ac·Sc·I  reads  BAC SCI
  * caffeine C8H10N4O2, SMILES CN1C=NC2=C1C(=O)N(C(=O)N2C)C, drawn from RDKit 2D coordinates
  * DNA base pairing A-T (2 H-bonds), G-C (3 H-bonds)
  * Punnett square Aa x Aa  ->  AA, Aa, Aa, aa  (genotype 1:2:1, phenotype 3:1)
  * conservation of energy stated without attribution
"""
import math, sys, os, random
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from lib import *          # noqa: F401,F403  (PAL, T, text_d, text_w, T_arc, svg, write, render, face ...)
import identity as ID

# --------------------------------------------------------------------------- helpers

def _rect_rounded(x, y, w, h, r, fill, stroke=None, sw=0):
    s = f' stroke="{stroke}" stroke-width="{sw}"' if stroke else ""
    return f'<rect x="{x:.2f}" y="{y:.2f}" width="{w:.2f}" height="{h:.2f}" rx="{r:.2f}" fill="{fill}"{s}/>'


def lines_centered(lines, cx, y0, size, lead, fill, key="archivo", tracking=0, **axes):
    out = []
    for i, ln in enumerate(lines):
        out.append(T(ln, key, size, cx, y0 + i * lead, fill, "middle", tracking=tracking, **axes))
    return "".join(out)


# --------------------------------------------------------------------------- periodic tiles

TILE_DATA = {
    "B":  dict(z=5,  name="Bore",     mass="10,81",   cat="metalloid"),
    "Ac": dict(z=89, name="Actinium", mass="[227]",   cat="actinide"),
    "Sc": dict(z=21, name="Scandium", mass="44,956",  cat="transition"),
    "I":  dict(z=53, name="Iode",     mass="126,90",  cat="halogen"),
}
CAT_COL = lambda P: {"metalloid": P["rose"], "actinide": P["violet"], "transition": P["blue"], "halogen": P["chalk"]}


def tile(sym, x, y, s, fill, ink, edge=None, label=True, sub=None):
    """One periodic-table tile of size s x s (viewBox units) with the IUPAC layout:
    atomic number top-left, symbol centre, name below, atomic mass at the foot."""
    d = TILE_DATA[sym]
    out = [_rect_rounded(x, y, s, s, s * 0.045, fill, edge, s * 0.012 if edge else 0)]
    out.append(T(str(d["z"]), "mono", s * 0.135, x + s * 0.09, y + s * 0.19, ink, wght=600))
    big = s * (0.50 if len(sym) == 1 else 0.44)
    out.append(T(sym, "archivo", big, x + s * 0.5, y + s * 0.64, ink, "middle", wdth=100, wght=700, tracking=-10))
    if label:
        out.append(T(d["name"], "archivo", s * 0.108, x + s * 0.5, y + s * 0.79, ink, "middle", wdth=100, wght=600, tracking=40))
        out.append(T(d["mass"], "mono", s * 0.094, x + s * 0.5, y + s * 0.915, ink, "middle", wght=500))
    return "".join(out)


def tiles_svg(P, syms=("B", "Ac", "Sc", "I"), s=200, gap=22, scheme="category", ink=None, label=True):
    """Row of tiles spelling B-Ac-Sc-I.  scheme: 'category' (colour by element family), 'mono' (one fill)."""
    cat = CAT_COL(P)
    W = len(syms) * s + (len(syms) - 1) * gap
    out = []
    for i, sym in enumerate(syms):
        c = cat[TILE_DATA[sym]["cat"]] if scheme == "category" else (scheme if scheme.startswith("#") else P["chalk"])
        k = ink or (P["nuit"] if lum(c) > 0.30 else P["chalk"])
        out.append(tile(sym, i * (s + gap), 0, s, c, k, label=label))
    return svg(W, s, "".join(out))


def tiles_row_svg(P, syms=("B", "Ac", "Sc", "I"), s=200, gap=22, fills=None, inks=None, label=True):
    """Tile row with explicit fills/inks (so a tile never vanishes into the fabric colour)."""
    W = len(syms) * s + (len(syms) - 1) * gap
    out = []
    for i, sym in enumerate(syms):
        out.append(tile(sym, i * (s + gap), 0, s, fills[i], inks[i], label=label))
    return svg(W, s, "".join(out))


def tile_square_svg(P, sym, s=400, fill=None, ink=None, label=True):
    c = fill or CAT_COL(P)[TILE_DATA[sym]["cat"]]
    k = ink or (P["nuit"] if lum(c) > 0.30 else P["chalk"])
    return svg(s, s, tile(sym, 0, 0, s, c, k, label=label))


# --------------------------------------------------------------------------- lettering

def script_svg(P, text="Bac Sciences", fill=None, size=300, key="great", extra_line=None):
    """Elegant script line (Great Vibes) for sleeve / hem embroidery.  Returns svg."""
    fill = fill or P["chalk"]
    w = text_w(text, "script", size)
    pad = size * 0.25
    body = T(text, "script", size, pad, size * 0.95, fill)
    H = size * 1.35
    if extra_line:
        body += T(extra_line, "mono", size * 0.11, pad + w * 0.5, size * 1.28, fill, "middle", tracking=300, wght=500)
        H = size * 1.45
    return svg(w + 2 * pad, H, body)


def wordmark_svg(P, fill=None, lam_fill=None, kicker=True, foot=True, size=120):
    fill = fill or P["chalk"]
    wm, w, c = ID.wordmark(size, fill, 0, 0, tracking=18, lam_fill=lam_fill or fill)
    pad = size * 0.2
    body = f'<g transform="translate({pad} {size*0.95})">{wm}</g>'
    H = size * 1.1
    if kicker:
        body += T("LYCÉE", "archivo", size * 0.17, pad + w / 2, size * 0.18, fill, "middle", tracking=900, wdth=100, wght=500)
    if foot:
        body += T("TÉBOURBA · BAC SCIENCES 2027", "archivo", size * 0.115, pad + w / 2, size * 1.32, fill, "middle", tracking=420, wdth=100, wght=500)
        H = size * 1.5
    return svg(w + 2 * pad, H, body)


def numerals_svg(P, fill=None, size=200, digits="2027", accent=None):
    fill = fill or P["chalk"]
    n, w, h = ID.numerals(size, fill, 0, 0, tracking=30, digits=digits)
    pad = size * 0.1
    return svg(w + 2 * pad, h + 2 * pad, f'<g transform="translate({pad} {h + pad})">{n}</g>')


def orbit_lam_svg(P, fill=None, accent=None, R=200):
    fill = fill or P["chalk"]
    return svg(2 * R + 20, 2 * R + 20, ID.monogram(R + 10, R + 10, R, fill, accent or P["violet"]))


# --------------------------------------------------------------------------- crest / seal

def crest_svg(P, fg=None, bg=None, ring=None, accent=None, R=300):
    """Circular crest 'Sceau Surus'.  Original mark: Surus (Hannibal's elephant) with an atom-ring ear."""
    fg = fg or P["nuit"]; bg = bg or P["chalk"]; accent = accent or P["violet"]
    body = ID.seal(R + 6, R + 6, R, fg, bg, accent, text_col=ring or bg)
    return svg(2 * R + 12, 2 * R + 12, body)


def surus_svg(P, fg=None, accent=None, W=600):
    fg = fg or P["chalk"]; accent = accent or P["violet"]
    return svg(ID.SURUS_W + 40, ID.SURUS_H + 40, ID.surus(fg, accent, x=20, y=20))


# --------------------------------------------------------------------------- DNA

def dna_svg(P, H=1000, turns=3.0, amp=110, strand=None, rung_cols=None, letters=True, stroke=18, tilt=0.0,
            back=None, bases=None):
    """Double helix with true base pairing (A-T 2 bonds, G-C 3 bonds) and depth-ordered strands."""
    strand = strand or P["chalk"]
    back = back or P["lab"]
    rung_cols = rung_cols or {"A": P["violet"], "T": P["rose"], "G": P["blue"], "C": P["chalk"]}
    pairs = bases or "ATGCCGTAGCATTGCAGTCA"
    N = len(pairs)
    W = amp * 2 + 140
    cx = W / 2
    pts = 400
    def pos(t, ph):                         # t 0..1 along height
        a = 2 * math.pi * turns * t + ph
        return cx + amp * math.sin(a), 40 + (H - 80) * t, math.cos(a)
    out = []
    # strands as depth-ordered short segments
    segs = []
    for ph, col in ((0.0, strand), (math.pi, strand)):
        for i in range(pts):
            t0, t1 = i / pts, (i + 1) / pts
            x0, y0, z0 = pos(t0, ph); x1, y1, z1 = pos(t1, ph)
            segs.append(((z0 + z1) / 2, x0, y0, x1, y1, col))
    rungs = []
    for i, p in enumerate(pairs):
        t = (i + 0.5) / N
        xa, ya, za = pos(t, 0.0); xb, yb, zb = pos(t, math.pi)
        rungs.append((min(za, zb), (xa, ya, xb, yb, p, i, za)))
    # back strands, then rungs, then front strands
    def strand_seg(z, x0, y0, x1, y1, col):
        sw = stroke * (0.7 + 0.3 * (z + 1) / 2)
        c = col if z > 0 else back
        return f'<path d="M{x0:.1f} {y0:.1f} L{x1:.1f} {y1:.1f}" stroke="{c}" stroke-width="{sw:.1f}" stroke-linecap="round" fill="none"/>'
    out += [strand_seg(z, x0, y0, x1, y1, c) for (z, x0, y0, x1, y1, c) in segs if z <= 0]
    comp = {"A": "T", "T": "A", "G": "C", "C": "G"}
    for _, (xa, ya, xb, yb, p, i, za) in sorted(rungs, key=lambda r: r[0]):
        q = comp[p]
        xm, ym = (xa + xb) / 2, (ya + yb) / 2
        # two half-rungs coloured by base
        out.append(f'<path d="M{xa:.1f} {ya:.1f} L{xm:.1f} {ym:.1f}" stroke="{rung_cols[p]}" stroke-width="{stroke*0.62:.1f}" stroke-linecap="round"/>')
        out.append(f'<path d="M{xb:.1f} {yb:.1f} L{xm:.1f} {ym:.1f}" stroke="{rung_cols[q]}" stroke-width="{stroke*0.62:.1f}" stroke-linecap="round"/>')
        # hydrogen bonds: 2 for A-T, 3 for G-C, as short ticks across the middle
        nb = 2 if {p, q} == {"A", "T"} else 3
        dx, dy = xb - xa, yb - ya
        L = math.hypot(dx, dy) or 1
        ux, uy = dx / L, dy / L
        for k in range(nb):
            o = (k - (nb - 1) / 2) * stroke * 0.5
            out.append(f'<circle cx="{xm + ux*o:.1f}" cy="{ym + uy*o:.1f}" r="{stroke*0.13:.1f}" fill="{P["nuit"]}"/>')
        if letters and abs(za) < 0.99:
            for (xx, yy, ch) in ((xa, ya, p), (xb, yb, q)):
                out.append(T(ch, "mono", stroke * 0.95, xx, yy + stroke * 0.33, P["nuit"], "middle", wght=700))
    out += [strand_seg(z, x0, y0, x1, y1, c) for (z, x0, y0, x1, y1, c) in segs if z > 0]
    return svg(W, H, "".join(out))


# --------------------------------------------------------------------------- caffeine molecule

def caffeine_svg(P, ink=None, accent=None, size=700, line=3.2, label=True):
    """Caffeine (1,3,7-triméthylxanthine) C8H10N4O2 drawn from RDKit 2D coordinates.
    Atom labels come out as outline paths, so no font is needed."""
    from rdkit import Chem
    from rdkit.Chem import rdDepictor, rdMolDescriptors
    from rdkit.Chem.Draw import rdMolDraw2D
    ink = ink or P["chalk"]; accent = accent or P["violet"]
    m = Chem.MolFromSmiles("CN1C=NC2=C1C(=O)N(C(=O)N2C)C")
    assert rdMolDescriptors.CalcMolFormula(m) == "C8H10N4O2"
    rdDepictor.SetPreferCoordGen(True)
    rdDepictor.Compute2DCoords(m)
    d = rdMolDraw2D.MolDraw2DSVG(size, int(size * 0.82))
    o = d.drawOptions()
    o.clearBackground = False
    o.bondLineWidth = line
    o.multipleBondOffset = 0.14
    o.padding = 0.12
    o.baseFontSize = 0.62
    o.useBWAtomPalette()
    def rgb(h):
        h = h.lstrip("#"); return tuple(int(h[i:i + 2], 16) / 255 for i in (0, 2, 4))
    o.setSymbolColour(rgb(ink)); o.setDefaultColour(rgb(ink)) if hasattr(o, "setDefaultColour") else None
    for a in m.GetAtoms():
        pass
    d.DrawMolecule(m)
    d.FinishDrawing()
    s = d.GetDrawingText()
    import re
    s = re.sub(r"<rect[^>]*style='opacity:1\.0;fill:#FFFFFF[^>]*>", "", s)       # drop the white background rect
    # recolour: RDKit emits black strokes/fills for B/W palette
    s = s.replace("#000000", ink)
    return s


# --------------------------------------------------------------------------- Punnett square

def punnett_svg(P, ink=None, accent=None, s=150):
    """Monohybrid cross Aa x Aa: gametes A,a on both axes; cells AA, Aa, Aa, aa; ratios 1:2:1 and 3:1."""
    ink = ink or P["chalk"]; accent = accent or P["violet"]
    W = s * 3.1 + 40; H = s * 3.4 + 40
    ox, oy = s * 0.9 + 20, s * 0.9 + 20
    out = []
    out.append(T("Aa × Aa", "mono", s * 0.2, ox + s, 36 + s * 0.12, ink, "middle", wght=600, tracking=60))
    for i, g in enumerate("Aa"):
        out.append(T(g, "archivo", s * 0.42, ox + s * (i + 0.5), oy - s * 0.18, accent, "middle", wght=700))
        out.append(T(g, "archivo", s * 0.42, ox - s * 0.28, oy + s * (i + 0.5) + s * 0.15, accent, "middle", wght=700))
    cells = ["AA", "Aa", "Aa", "aa"]
    for k, g in enumerate(cells):
        r, c = divmod(k, 2)
        x, y = ox + c * s, oy + r * s
        out.append(f'<rect x="{x}" y="{y}" width="{s}" height="{s}" fill="none" stroke="{ink}" stroke-width="{s*0.028}"/>')
        out.append(T(g, "archivo", s * 0.40, x + s / 2, y + s * 0.62, ink, "middle", wght=600))
    out.append(T("1 AA : 2 Aa : 1 aa", "mono", s * 0.145, ox + s, oy + 2 * s + s * 0.34, ink, "middle", wght=500))
    out.append(T("phénotype  3 : 1", "mono", s * 0.145, ox + s, oy + 2 * s + s * 0.58, accent, "middle", wght=500))
    return svg(W, H, "".join(out))


# --------------------------------------------------------------------------- cosmic energy print

def cosmic_svg(P, R=800, stars=1400, seed=11, quote=True, arms=3, text_col=None, glow=True):
    """Large circular 'énergie' print: log-spiral galaxy arms of stars, nested orbit rings and a
    three-ellipse atom/torus figure around a bright nucleus.  Colours: violet -> electric blue -> chalk."""
    rnd = random.Random(seed)
    text_col = text_col or P["chalk"]
    C = R + 60
    out = []
    defs = ""
    if glow:
        defs += (f'<radialGradient id="cg"><stop offset="0" stop-color="{P["chalk"]}" stop-opacity="1"/>'
                 f'<stop offset="0.25" stop-color="{P["blue"]}" stop-opacity=".85"/>'
                 f'<stop offset="0.6" stop-color="{P["violet"]}" stop-opacity=".35"/>'
                 f'<stop offset="1" stop-color="{P["violet"]}" stop-opacity="0"/></radialGradient>')
        out.append(f'<circle cx="{C}" cy="{C}" r="{R*0.62}" fill="url(#cg)"/>')
    # rings
    for i, (rr, op, sw) in enumerate(((0.98, 1, 4), (0.90, .6, 2), (0.74, .5, 2), (0.58, .6, 2.5))):
        out.append(f'<circle cx="{C}" cy="{C}" r="{R*rr}" fill="none" stroke="{P["lab_l"]}" stroke-opacity="{op}" stroke-width="{sw}"/>')
    # galaxy arms: stars on logarithmic spirals
    def lerp(a, b, t):
        a = a.lstrip("#"); b = b.lstrip("#")
        ca = [int(a[i:i + 2], 16) for i in (0, 2, 4)]; cb = [int(b[i:i + 2], 16) for i in (0, 2, 4)]
        return "#%02x%02x%02x" % tuple(int(ca[i] + (cb[i] - ca[i]) * t) for i in range(3))
    for k in range(arms):
        base = 2 * math.pi * k / arms
        for _ in range(stars // arms):
            t = rnd.random() ** 0.8
            r = R * (0.08 + 0.8 * t)
            th = base + 3.4 * math.log(1 + 6 * t) + rnd.gauss(0, 0.16 * (1 - 0.5 * t))
            rr_ = r * (1 + rnd.gauss(0, 0.025))
            x, y = C + rr_ * math.cos(th), C + rr_ * math.sin(th)
            col = lerp(P["chalk"], P["violet"], min(1, t * 1.15)) if t < 0.5 else lerp(P["blue"], P["violet"], (t - .5) * 2)
            rad = rnd.choice((1.6, 2.2, 2.8, 3.6)) * (1.15 - 0.6 * t)
            out.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{rad:.2f}" fill="{col}" fill-opacity="{0.55 + 0.45 * (1 - t):.2f}"/>')
    # atom / torus figure: three ellipses at 0/60/120 deg
    for a in (0, 60, 120):
        out.append(f'<ellipse cx="{C}" cy="{C}" rx="{R*0.50}" ry="{R*0.17}" transform="rotate({a} {C} {C})" fill="none" '
                   f'stroke="{P["chalk"]}" stroke-width="5"/>')
    for a, ph in ((0, .3), (60, 1.7), (120, 3.9)):
        t = ph
        ex, ey = R * 0.50 * math.cos(t), R * 0.17 * math.sin(t)
        ang = math.radians(a)
        px = C + ex * math.cos(ang) - ey * math.sin(ang); py = C + ex * math.sin(ang) + ey * math.cos(ang)
        out.append(f'<circle cx="{px:.1f}" cy="{py:.1f}" r="13" fill="{P["blue"]}"/><circle cx="{px:.1f}" cy="{py:.1f}" r="5" fill="{P["chalk"]}"/>')
    out.append(f'<circle cx="{C}" cy="{C}" r="34" fill="{P["chalk"]}"/><circle cx="{C}" cy="{C}" r="16" fill="{P["violet"]}"/>')
    if quote:
        # statement of conservation of energy, set on the outer ring
        out.append(T_arc("L’ÉNERGIE NE SE CRÉE NI NE SE DÉTRUIT", "archivo", R * 0.052, C, C, R * 1.045, -90, text_col, tracking=210, wdth=110, wght=600))
        out.append(T_arc("ELLE SE TRANSFORME", "archivo", R * 0.052, C, C, R * 1.045 + R * 0.04, 90, text_col, tracking=360, inside=True, wdth=110, wght=600))
        out.append(T("E = mc²", "mono", R * 0.07, C, C + R * 0.88, text_col, "middle", wght=600, tracking=100))
    return svg(2 * C, 2 * C, "".join(out), defs=defs)


def orbit_cell_svg(P, s=300, ink=None, accent=None, stars=True):
    """Seamless repeat cell: atom figure + orbit rings + stars.  Use as pattern tile (scarf, sleeve border)."""
    ink = ink or P["chalk"]; accent = accent or P["violet"]
    c = s / 2
    out = []
    for a in (0, 60, 120):
        out.append(f'<ellipse cx="{c}" cy="{c}" rx="{s*0.38}" ry="{s*0.13}" transform="rotate({a} {c} {c})" fill="none" stroke="{ink}" stroke-width="{s*0.012}"/>')
    out.append(f'<circle cx="{c}" cy="{c}" r="{s*0.045}" fill="{accent}"/>')
    out.append(f'<circle cx="{c}" cy="{c}" r="{s*0.46}" fill="none" stroke="{ink}" stroke-opacity=".35" stroke-width="{s*0.006}"/>')
    if stars:
        for (x, y, r) in ((0.06, 0.08, 3), (0.94, 0.14, 2.2), (0.1, 0.92, 2.4), (0.9, 0.86, 3), (0.5, 0.03, 1.8), (0.5, 0.97, 1.8), (0.03, 0.5, 1.8), (0.97, 0.5, 1.8)):
            out.append(f'<circle cx="{x*s}" cy="{y*s}" r="{r}" fill="{ink}"/>')
    return svg(s, s, "".join(out))


# --------------------------------------------------------------------------- labels

def woven_label_svg(P, bg=None, ink=None, lines=("BAC SCIENCES", "2027"), W=1000, H=190, accent=None):
    """Folded hem label: navy ground, chalk type, a violet peak line (Λ motif).  Type is fitted to the width."""
    bg = bg or P["nuit"]; ink = ink or P["chalk"]; accent = accent or P["violet"]
    out = [f'<rect width="{W}" height="{H}" rx="14" fill="{bg}"/>']
    out.append(f'<rect x="10" y="10" width="{W-20}" height="{H-20}" rx="8" fill="none" stroke="{ink}" stroke-opacity=".55" stroke-width="3"/>')
    size = H * 0.36
    for _ in range(3):                                  # fit the type into the free width (peaks mark takes the left 16 %)
        w1 = text_w(lines[0], "archivo", size, 200, wdth=110, wght=700)
        w2 = text_w(lines[1], "archivo", size, 120, wdth=110, wght=700)
        gap = size * 0.9
        tot = w1 + gap + w2
        if tot <= W * 0.78:
            break
        size *= W * 0.76 / tot
    x0 = W * 0.58 - tot / 2
    out.append(T(lines[0], "archivo", size, x0, H * 0.64, ink, "start", tracking=200, wdth=110, wght=700))
    out.append(T(lines[1], "archivo", size, x0 + w1 + gap, H * 0.64, accent, "start", tracking=120, wdth=110, wght=700))
    out.append(ID.peaks(W * 0.045, H * 0.78, W * 0.11, H * 0.40, n=3, fill=accent, sw=7))
    return svg(W, H, "".join(out))


def neck_label_svg(P, bg=None, ink=None, W=520, H=260):
    bg = bg or P["chalk"]; ink = ink or P["nuit"]
    out = [f'<rect width="{W}" height="{H}" rx="12" fill="{bg}"/>']
    wm, w, c = ID.wordmark(52, ink, W / 2, H * 0.42, tracking=18, anchor="middle")
    out.append(wm)
    out.append(T("LYCÉE · TÉBOURBA", "archivo", 21, W / 2, H * 0.62, ink, "middle", tracking=420, wdth=100, wght=500))
    out.append(T("36°50′N · 9°50′E", "mono", 19, W / 2, H * 0.80, ink, "middle", wght=500, tracking=120))
    return svg(W, H, "".join(out))


def motto_svg(P, ink=None, accent=None, W=1500):
    """Hood motto: French line + Arabic line (HarfBuzz-shaped)."""
    ink = ink or P["chalk"]; accent = accent or P["rose"]
    out = [T("TRAVERSER L’INCONNU", "archivo", 70, W / 2, 90, ink, "middle", tracking=300, wdth=105, wght=600)]
    out.append(T("عبور المجهول", "kufi", 92, W / 2, 230, accent, "middle", wght=600))
    return svg(W, 280, "".join(out))


def varsity_arc_svg(P, text="HANNIBAL", fill=None, stroke=None, R=600):
    """Collegiate arched block lettering (Graduate) with an outline stroke."""
    fill = fill or P["chalk"]; stroke = stroke or P["nuit"]
    W = 2 * R
    d_all = []
    # place letters on an arc via T_arc using the Graduate face
    return svg(W, R * 0.5, T_arc(text, "grad", R * 0.28, R, R * 1.05, R, -90, fill, tracking=60))


if __name__ == "__main__":
    # preview sheet
    P = PAL
    out = Path("/tmp/art_preview"); out.mkdir(exist_ok=True)
    tests = {
        "tiles": tiles_svg(P), "crest": crest_svg(P), "wordmark": wordmark_svg(P), "numerals": numerals_svg(P),
        "dna": dna_svg(P), "caffeine": caffeine_svg(P), "punnett": punnett_svg(P), "cosmic": cosmic_svg(P),
        "label": woven_label_svg(P), "neck": neck_label_svg(P), "script": script_svg(P), "motto": motto_svg(P),
    }
    for k, v in tests.items():
        write(out / f"{k}.svg", v)
        bg = P["nuit"]
        render(out / f"{k}.svg", png=out / f"{k}.png", scale=1.0, bg="transparent")
    print("ok")


# ============================================================================== additional pieces (3D phase 2)

def dna_frag(P, H=1000, turns=3.0, amp=110, strand=None, rung_cols=None, letters=False, stroke=18, bases=None, back=None):
    """DNA helix as an SVG fragment: returns (body, W, H)."""
    full = dna_svg(P, H=H, turns=turns, amp=amp, strand=strand, rung_cols=rung_cols, letters=letters, stroke=stroke, bases=bases, back=back)
    import re
    m = re.search(r'viewBox="0 0 ([\d.]+) ([\d.]+)"', full)
    body = full[full.index("</defs>") + 7:full.rindex("</svg>")]
    return body, float(m.group(1)), float(m.group(2))


def dna_tall_svg(P, ink=None, H=1000, strand=None, letters=True, bases=None, tagline=None, tag_col=None):
    """Clean back print: DNA helix with an optional tagline underneath (ref 4: 'born unique' minimal back print)."""
    body, W, Hh = dna_frag(P, H=H, strand=strand or (ink or P["chalk"]), letters=letters, bases=bases)
    out = body
    height = Hh
    if tagline:
        tw = text_w(tagline, "mono", Hh * 0.034, 380, wght=500) + 20
        Wn = max(W, tw)
        out = f'<g transform="translate({(Wn - W)/2:.1f} 0)">{out}</g>'
        out += T(tagline, "mono", Hh * 0.034, Wn / 2, Hh + Hh * 0.06, tag_col or (ink or P["chalk"]), "middle", tracking=380, wght=500)
        height = Hh + Hh * 0.10
        W = Wn
    return svg(W, height, out)


def varsity_text_svg(P, text="SCIENCES", fill=None, outline=None, size=170, arc=0, ow=12, key="grad"):
    """Collegiate block lettering (Graduate), flat or arched, with a contrasting outline (stroke under fill)."""
    fill = fill or P["chalk"]; outline = outline or P["nuit"]
    if arc:
        R = arc
        W = 2 * R + 2 * size * 0.8
        body = T_arc(text, key, size, R + size * 0.8, R + size * 0.8, R, -90, fill, tracking=40)
        # outline copy first
        body_o = body.replace(f'fill="{fill}"', f'fill="{outline}" stroke="{outline}" stroke-width="{ow*2}" stroke-linejoin="round"')
        return svg(W, R * 0.95, body_o + body)
    w = text_w(text, key, size, 40)
    pad = ow * 3
    d, _ = text_d(text, key, size, pad, size * 0.95, "start", 40)
    body = (f'<path d="{d}" fill="{outline}" stroke="{outline}" stroke-width="{ow*2}" stroke-linejoin="round"/>'
            f'<path d="{d}" fill="{fill}"/>')
    return svg(w + 2 * pad, size * 1.15 + pad, body)


def chenille_letter_svg(P, letter="H", fill=None, border=None, size=520):
    """Chenille-style varsity letter: thick fill with a contrasting felt border (one raised look when composited)."""
    fill = fill or P["rose"]; border = border or P["chalk"]
    d, w = text_d(letter, "grad", size, size * 0.1, size * 0.9, "start", 0)
    body = (f'<path d="{d}" fill="{border}" stroke="{border}" stroke-width="{size*0.085}" stroke-linejoin="round"/>'
            f'<path d="{d}" fill="{fill}" stroke="{fill}" stroke-width="{size*0.02}" stroke-linejoin="round"/>')
    return svg(w + size * 0.3, size * 1.05, body)


def badge_svg(P, kind="phys", ring=None, fill=None, ink=None, R=160):
    """Round varsity badge: ring + arc text + icon (orbit atom / benzene ring / DNA mini)."""
    ring = ring or P["chalk"]; fill = fill or P["nuit"]; ink = ink or P["chalk"]
    c = R + 8
    out = [f'<circle cx="{c}" cy="{c}" r="{R}" fill="{fill}" stroke="{ring}" stroke-width="{R*0.07}"/>']
    out.append(f'<circle cx="{c}" cy="{c}" r="{R*0.62}" fill="none" stroke="{ring}" stroke-width="{R*0.025}"/>')
    label = {"phys": "PHYSIQUE", "chem": "CHIMIE", "svt": "SVT"}[kind]
    out.append(T_arc(label, "archivo", R * 0.19, c, c, R * 0.80, -90, ink, tracking=220, wdth=110, wght=700))
    if kind == "phys":
        for a in (0, 60, 120):
            out.append(f'<ellipse cx="{c}" cy="{c}" rx="{R*0.46}" ry="{R*0.16}" transform="rotate({a} {c} {c})" fill="none" stroke="{ink}" stroke-width="{R*0.03}"/>')
        out.append(f'<circle cx="{c}" cy="{c}" r="{R*0.07}" fill="{ink}"/>')
    elif kind == "chem":
        pts = [(c + R * 0.36 * math.cos(math.radians(60 * i - 90)), c + R * 0.36 * math.sin(math.radians(60 * i - 90))) for i in range(6)]
        out.append('<path d="M' + " L".join(f"{x:.1f} {y:.1f}" for x, y in pts) + f' Z" fill="none" stroke="{ink}" stroke-width="{R*0.035}" stroke-linejoin="round"/>')
        for i in (0, 2, 4):                                  # alternating double bonds (Kekulé benzene)
            (x0, y0), (x1, y1) = pts[i], pts[i + 1]
            mx, my = (x0 + x1) / 2, (y0 + y1) / 2
            dx, dy = (c - mx) * 0.22, (c - my) * 0.22
            out.append(f'<path d="M{x0+dx+(x1-x0)*0.15:.1f} {y0+dy+(y1-y0)*0.15:.1f} L{x1+dx-(x1-x0)*0.15:.1f} {y1+dy-(y1-y0)*0.15:.1f}" stroke="{ink}" stroke-width="{R*0.03}" stroke-linecap="round"/>')
    else:
        body, W, Hh = dna_frag(P, H=400, turns=1.6, amp=48, strand=ink, rung_cols={"A": ink, "T": ink, "G": ink, "C": ink}, letters=False, stroke=9, bases="ATGCAT", back=ink)
        k = R * 1.05 / Hh
        out.append(f'<g transform="translate({c - W*k/2:.1f} {c - Hh*k/2 + R*0.04:.1f}) scale({k:.3f})">{body}</g>')
    return svg(2 * c, 2 * c, "".join(out))


def collage_svg(P, ink=None, accent=None, bg=None, W=1100):
    """Back collage (ref 3 inspiration, original): arched SCIENCES, DNA + Surus roundel + Arabic calligraphy, 2027, badges."""
    ink = ink or P["chalk"]; accent = accent or P["rose"]; bg = bg or P["nuit"]
    cx, cy = W / 2, 500
    out = []
    arc = T_arc("SCIENCES", "grad", 150, cx, cy, 395, -90, ink, tracking=60)
    out.append(arc.replace(f'fill="{ink}"', f'fill="{bg}" stroke="{bg}" stroke-width="20" stroke-linejoin="round"'))
    out.append(arc)
    out.append(f'<circle cx="{cx}" cy="{cy+20}" r="190" fill="none" stroke="{ink}" stroke-width="10"/>')
    out.append(f'<circle cx="{cx}" cy="{cy+20}" r="172" fill="none" stroke="{ink}" stroke-width="3" stroke-dasharray="2 9"/>')
    out.append(ID.surus(ink, accent, x=cx - 150, y=cy - 60, scale=0.68))
    body, dw, dh = dna_frag(P, H=560, turns=2.2, amp=62, strand=ink, rung_cols={"A": accent, "T": ink, "G": P["blue"], "C": P["violet"]}, letters=False, stroke=12, back=P["lab"])
    out.append(f'<g transform="translate({120 - dw/2:.1f} {270})">{body}</g>')
    out.append(T("علوم", "aref", 170, 935, cy + 70, accent, "middle"))
    out.append(f'<path d="M800 {cy+110} H1070" stroke="{accent}" stroke-width="6" stroke-linecap="round"/>')
    out.append(T("SCIENCES", "mono", 17, 935, cy + 142, ink, "middle", tracking=300, wght=500))
    n, nw, nh = ID.numerals(190, ink, cx, 900, tracking=40, anchor="middle")
    out.append(n)
    for i, kind in enumerate(("phys", "chem", "svt")):
        s = badge_svg(P, kind, ring=ink, fill=bg, ink=ink, R=78)
        body = s[s.index("</defs>") + 7:s.rindex("</svg>")]
        out.append(f'<g transform="translate({cx - 270 + i*190:.1f} 940)">{body}</g>')
    out.append(T("LYCÉE HANNIBAL · TÉBOURBA · PROMO 2027", "mono", 24, cx, 1135, ink, "middle", tracking=240, wght=500))
    return svg(W, 1160, "".join(out))


def pocket_svg(P):
    return svg(10, 10, "")
