"""Identity components for LYCÉE HANNIBAL · TÉBOURBA · BAC SCIENCES 2027.
Every function returns an SVG fragment (string).  `uid()` keeps mask ids unique."""
import itertools, math
from lib import *

_uid = itertools.count(1)
def uid(p="u"): return f"{p}{next(_uid)}"

# -------------------------------------------------------------------------- SURUS
# Elephant is constructed on a 440 x 320 grid from circles and capsules (compass geometry).
SURUS_W, SURUS_H = 440, 320
def surus(fg=PAL["tyr"], accent=None, eye=True, gap=5, construction=False, cons_col=None, scale=1.0, x=0, y=0,
          detail=True, bg_gap=None):
    """Surus - Hannibal's one-tusked elephant, facing right, trunk raised.
    Knock-outs are real transparency (mask) so the mark works in 1 colour, 2 colours, or embroidery."""
    m = uid("sm")
    acc = accent or fg
    body = ('<rect x="46" y="72" width="240" height="132" rx="66" />'          # torso capsule
            '<circle cx="288" cy="130" r="68" />'                               # head
            '<rect x="62" y="168" width="44" height="112" rx="16" />'          # rear leg A
            '<rect x="114" y="174" width="42" height="106" rx="16" />'         # rear leg B
            '<rect x="196" y="174" width="42" height="106" rx="16" />'         # front leg B
            '<rect x="246" y="168" width="44" height="112" rx="16" />')        # front leg A
    trunk = ('<path d="M334 146 C 388 156, 424 122, 410 82 C 402 58, 372 50, 360 70" '
             'fill="none" stroke="#fff" stroke-width="30" stroke-linecap="round" stroke-linejoin="round"/>')
    tail = ('<path d="M52 118 C 22 126, 16 168, 30 196" fill="none" stroke="#fff" stroke-width="10" stroke-linecap="round"/>'
            '<ellipse cx="30" cy="206" rx="11" ry="16" transform="rotate(10 30 206)" fill="#fff"/>')
    ko = (f'<circle cx="250" cy="130" r="54" fill="none" stroke="#000" stroke-width="{gap}"/>'          # ear edge
          f'<circle cx="250" cy="130" r="34" fill="none" stroke="#000" stroke-width="{gap}"/>'          # orbit ring
          '<circle cx="250" cy="130" r="8" fill="#000"/>'                                              # nucleus
          + ('<circle cx="318" cy="112" r="7" fill="#000"/>' if eye else ''))
    if detail:
        ko += "".join(f'<path d="M{cx-9} 270 a9 9 0 0 1 18 0" stroke="#000" stroke-width="3.4" fill="none" stroke-linecap="round"/>'
                      for cx in (84, 135, 217, 268))
    tusk_d = "M336 178 C 366 200, 408 190, 424 150"
    tusk = f'<path d="{tusk_d}" fill="none" stroke="{acc}" stroke-width="12" stroke-linecap="round"/>'
    ko_tusk = f'<path d="{tusk_d}" fill="none" stroke="#000" stroke-width="23" stroke-linecap="round"/>'
    mask = (f'<mask id="{m}" maskUnits="userSpaceOnUse" x="-20" y="-20" width="500" height="360">'
            f'<g fill="#fff">{body}</g>{trunk}<g>{tail}</g>{ko}{ko_tusk}</mask>')
    cons = ""
    if construction:
        c = cons_col or fg
        cons = (f'<g fill="none" stroke="{c}" stroke-width="1.2" opacity=".95">'
                '<circle cx="288" cy="130" r="68" stroke-dasharray="3 5"/>'
                '<circle cx="250" cy="130" r="54" stroke-dasharray="3 5"/>'
                '<circle cx="250" cy="130" r="34" stroke-dasharray="3 5"/>'
                '<circle cx="107" cy="143" r="61" stroke-dasharray="3 5"/>'
                '<path d="M0 280 H 440" stroke-dasharray="8 4"/>'
                '<path d="M288 40 V 220 M 200 130 H 360" stroke-dasharray="1 4"/>'
                '<path d="M250 130 L 296 90" />'
                '</g>'
                f'<g fill="{c}"><circle cx="288" cy="130" r="3"/><circle cx="107" cy="143" r="3"/><circle cx="296" cy="90" r="2.6"/></g>')
    g = (f'<g transform="translate({x} {y}) scale({scale})">'
         f'<defs>{mask}</defs>'
         f'<g mask="url(#{m})"><rect x="-20" y="-20" width="500" height="360" fill="{fg}"/></g>'
         + tusk + cons + '</g>')
    return g


# -------------------------------------------------------------------------- glyph metrics
from fontTools.pens.boundsPen import BoundsPen
def gbounds(key, ch, **axes):
    fc = face(key, **axes)
    gname = fc.tt.getBestCmap()[ord(ch)]
    bp = BoundsPen(fc.gs); fc.gs[gname].draw(bp)
    return bp.bounds, fc.gs[gname].width * 1.0 / fc.upem   # (xmin,ymin,xmax,ymax) in font units, advance in em

def cap_h(key, size, **axes):
    fc = face(key, **axes); return fc.tt["OS/2"].sCapHeight * size / fc.upem

AX_WM = dict(wdth=125, wght=900)

def lam(x, y, C, W, h, t, fill):
    """Λ: flat-topped peak, baseline y, cap height C, width W, leg thickness h (horizontal), apex half-flat t."""
    yi = C * (W / 2 - h) / (W / 2 - t)
    pts = [(x, y), (x + W / 2 - t, y - C), (x + W / 2 + t, y - C), (x + W, y), (x + W - h, y), (x + W / 2, y - yi), (x + h, y)]
    return '<path d="M' + " L".join(f"{a:.2f} {b:.2f}" for a, b in pts) + f' Z" fill="{fill}"/>'

# -------------------------------------------------------------------------- WORDMARK  HΛNNIBΛL
def wordmark(size=100, fill=PAL["tyr"], x=0, y=0, tracking=18, anchor="start", lam_fill=None):
    """Primary wordmark. Both A's become Λ (Alpine peaks). Returns (svg, width, capheight)."""
    C = cap_h("archivo", size, **AX_WM)
    (ax0, ay0, ax1, ay1), adv_a = gbounds("archivo", "A", **AX_WM)
    (ix0, _, ix1, _), _ = gbounds("archivo", "I", **AX_WM)
    fc = face("archivo", **AX_WM); s = size / fc.upem
    stem = (ix1 - ix0) * s
    Wl = (ax1 - ax0) * s
    adv_l = adv_a * size
    trk = tracking * size / 1000
    # measure
    parts = []; cur = 0
    for ch in "HANNIBAL":
        if ch == "A":
            parts.append(("A", cur)); cur += adv_l + trk
        else:
            w = text_w(ch, "archivo", size, 0, **AX_WM)
            parts.append((ch, cur)); cur += w + trk
    total = cur - trk
    ox = x - (total / 2 if anchor == "middle" else total if anchor == "end" else 0)
    out = []
    for ch, cx in parts:
        if ch == "A":
            lsb = ax0 * s
            out.append(lam(ox + cx + lsb, y, C, Wl, stem * 1.18, stem * 0.52, lam_fill or fill))
        else:
            out.append(T(ch, "archivo", size, ox + cx, y, fill, **AX_WM))
    return "".join(out), total, C

# -------------------------------------------------------------------------- ORBIT motif (ring + nucleus)
def orbit(cx, cy, R, fill=PAL["tyr"], ring=0.2, nucleus=0.2, rings=1, bg=None):
    """ring width = ring*R, nucleus radius = nucleus*R. rings>1 adds a second concentric orbit."""
    out = []
    w = ring * R
    out.append(f'<circle cx="{cx}" cy="{cy}" r="{R - w/2}" fill="none" stroke="{fill}" stroke-width="{w}"/>')
    if rings > 1:
        r2 = (R - w) * 0.62
        out.append(f'<circle cx="{cx}" cy="{cy}" r="{r2}" fill="none" stroke="{fill}" stroke-width="{w*0.6}"/>')
    out.append(f'<circle cx="{cx}" cy="{cy}" r="{nucleus * R}" fill="{fill}"/>')
    return "".join(out)

# -------------------------------------------------------------------------- 2027 numerals
def numerals(size=100, fill=PAL["tyr"], x=0, y=0, tracking=30, anchor="start", digits="2027"):
    """2027 - the zero is an Orbit (ring + nucleus), echoing Surus' ear. Returns (svg, width, height)."""
    C = cap_h("archivo", size, **AX_WM)
    fc = face("archivo", **AX_WM)
    parts = []; cur = 0; trk = tracking * size / 1000
    for ch in digits:
        if ch == "0":
            D = C * 1.0
            parts.append(("0", cur, D)); cur += D + trk
        else:
            (b0, _, b1, _), adv = gbounds("archivo", ch, **AX_WM)
            parts.append((ch, cur, adv * size)); cur += adv * size + trk
    total = cur - trk
    ox = x - (total / 2 if anchor == "middle" else total if anchor == "end" else 0)
    out = []
    for ch, cx, w in parts:
        if ch == "0":
            D = w; R = D / 2
            out.append(orbit(ox + cx + R, y - R, R * 1.0, fill, ring=0.36, nucleus=0.22))
        else:
            out.append(T(ch, "archivo", size, ox + cx, y, fill, **AX_WM))
    return "".join(out), total, C

# -------------------------------------------------------------------------- Monogram (Orbit-Λ)
def monogram(cx, cy, R, fill=PAL["tyr"], accent=None, nucleus_col=None):
    """Compact emblem: ring, Λ peak, sun (nucleus) above apex.  Stitch-safe: min feature = 0.09*R."""
    acc = nucleus_col or accent or fill
    w = R * 0.17
    out = [f'<circle cx="{cx}" cy="{cy}" r="{R - w/2}" fill="none" stroke="{fill}" stroke-width="{w}"/>']
    C = R * 0.80; W = R * 1.00
    out.append(lam(cx - W / 2, cy + C * 0.50, C, W, R * 0.27, R * 0.13, fill))
    out.append(f'<circle cx="{cx}" cy="{cy - R*0.50}" r="{R*0.115}" fill="{acc}"/>')
    return "".join(out)

# -------------------------------------------------------------------------- Seal / badge
MOTTO_FR = "FRANCHIR L’INCONNUE"
MOTTO_AR = "عبور المجهول"
def seal(cx, cy, R, fg=PAL["tyr"], bg=PAL["chaux"], accent=PAL["citron"], text_col=None, surus_construction=False):
    """Round patch 'Sceau Surus' - ring text + Surus.  Works as 80 mm embroidered/woven patch."""
    tc = text_col or bg
    out = []
    out.append(f'<circle cx="{cx}" cy="{cy}" r="{R}" fill="{fg}"/>')
    out.append(f'<circle cx="{cx}" cy="{cy}" r="{R*0.965}" fill="none" stroke="{bg}" stroke-width="{R*0.022}"/>')
    ring_inner = R * 0.64
    out.append(f'<circle cx="{cx}" cy="{cy}" r="{ring_inner}" fill="none" stroke="{bg}" stroke-width="{R*0.016}"/>')
    ts = R * 0.135
    out.append(T_arc("LYCÉE HANNIBAL", "archivo", ts, cx, cy, R * 0.775, -90, tc, tracking=150, wght=800, wdth=115))
    out.append(T_arc("BAC SCIENCES", "archivo", ts, cx, cy, R * 0.775 + ts*0.72, 90, tc, tracking=150, inside=True, wght=800, wdth=115))
    # stars/dots separators
    for a in (180, 0):
        px, py = cx + R*0.80*math.cos(math.radians(a)), cy + R*0.80*math.sin(math.radians(a))
        out.append(f'<circle cx="{px:.1f}" cy="{py:.1f}" r="{R*0.028}" fill="{accent}"/>')
    k = R * 1.12 / 440
    out.append(surus(bg, accent, scale=k, x=cx - 220*k, y=cy - 160*k - R*0.13, gap=6))
    # year on base
    n, w, h = numerals(R * 0.21, accent, cx, cy + R*0.50, tracking=40, anchor="middle")
    out.append(n)
    return "".join(out)

def justify(txt, key, size, width, fill, x, y, **axes):
    """Letter-space `txt` so its ink runs exactly `width` wide (starting at x)."""
    base = text_w(txt, key, size, 0, **axes)
    n = len(txt) - 1
    trk = (width - base) / (n * size / 1000.0)
    return T(txt, key, size, x, y, fill, tracking=trk, **axes)

# -------------------------------------------------------------------------- Λ peaks motif line
def peaks(x, y, w, h, n=3, fill=PAL["tyr"], sw=None):
    """Row of n Alpine peaks (Λ outlines), total width w, height h."""
    sw = sw or h * 0.12
    pw = w / n
    d = f"M{x} {y} " + " ".join(f"L{x + pw*(i+0.5):.1f} {y - h*(1 if i%2==0 else 0.62):.1f} L{x + pw*(i+1):.1f} {y}" for i in range(n))
    return f'<path d="{d}" fill="none" stroke="{fill}" stroke-width="{sw}" stroke-linejoin="miter" stroke-linecap="butt"/>'

# -------------------------------------------------------------------------- tech annotation helpers
def crosshair(x, y, r=6, col="#000", sw=1):
    return (f'<g stroke="{col}" stroke-width="{sw}" fill="none"><path d="M{x-r} {y} H{x+r} M{x} {y-r} V{y+r}"/>'
            f'<circle cx="{x}" cy="{y}" r="{r*0.45}"/></g>')

def dim_h(x1, x2, y, label, col="#000", size=11, tick=5, key="mono", weight=500):
    mid = (x1 + x2) / 2
    lw = text_w(label, key, size, wght=weight) + 8
    return (f'<g stroke="{col}" stroke-width="1" fill="none"><path d="M{x1} {y-tick} V{y+tick} M{x2} {y-tick} V{y+tick} '
            f'M{x1} {y} H{mid-lw/2} M{mid+lw/2} {y} H{x2}"/></g>' + T(label, key, size, mid, y + size*0.35, col, "middle", wght=weight))

def dim_v(x, y1, y2, label, col="#000", size=11, tick=5, key="mono", weight=500):
    mid = (y1 + y2) / 2
    lw = text_w(label, key, size, wght=weight) + 8
    t = T(label, key, size, 0, 0, col, "middle", wght=weight)
    return (f'<g stroke="{col}" stroke-width="1" fill="none"><path d="M{x-tick} {y1} H{x+tick} M{x-tick} {y2} H{x+tick} '
            f'M{x} {y1} V{mid-lw/2} M{x} {mid+lw/2} V{y2}"/></g>'
            f'<g transform="translate({x} {mid}) rotate(-90) translate(0 {size*0.35})">{t}</g>')

if __name__ == "__main__":
    body = ""
    wm, w, c = wordmark(130, PAL["tyr"], 40, 170)
    body += wm
    n, nw, nh = numerals(130, PAL["tyr"], 40, 340, tracking=40)
    body += n
    body += monogram(660, 130, 90, PAL["tyr"], PAL["citron"])
    body += seal(780, 330, 150, PAL["tyr"], PAL["chaux"], PAL["citron"])
    s = svg(1000, 520, body, bg=PAL["chaux"])
    write("/tmp/id.svg", s); render("/tmp/id.svg", png="/tmp/id.png", scale=1.4)
