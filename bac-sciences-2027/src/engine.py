"""Garment render engine.  A garment = list of Part dicts (geometry in a 1000x1000 space, 10 px = 1 cm).
Same parts -> shaded mockup (fabric texture, lighting, folds, stitching, print / embroidery effects)
              or technical flat (outline, seam lines, dimension callouts)."""
import re, math, itertools
from lib import *
from identity import uid

PXCM = 10.0   # 1 cm = 10 px in garment space
CX = 500

# ---------------------------------------------------------------- geometry helpers
def nums(d):
    return [float(x) for x in re.findall(r"-?\d+\.?\d*", d)]
def bbox(d, pad=0):
    n = nums(re.sub(r"[A-Za-z]", " ", d)); xs, ys = n[0::2], n[1::2]
    return min(xs) - pad, min(ys) - pad, max(xs) + pad, max(ys) + pad

def mir(x): return 2 * CX - x

def sym(points_right, closed_top=None):
    """Build a closed outline from right-side segments (list of tuples starting with command)
    given from the top-centre going down the right side to the bottom-centre; mirrors for left."""
    pass

def f(v): return f"{v:.1f}".rstrip("0").rstrip(".")

def P(*pts):  # "x y x y" helper
    return " ".join(f(v) for v in pts)

def mirror_path_cmds(cmds):
    """cmds: list of ('L',x,y) | ('C',x1,y1,x2,y2,x,y) | ('Q',x1,y1,x,y) beginning with ('M',x,y).
    Returns path for the LEFT side traversed from the end of the right side back to start."""
    # collect absolute nodes
    segs = []; cur = None
    for c in cmds:
        if c[0] == "M": cur = (c[1], c[2]); continue
        if c[0] == "L": segs.append(("L", cur, None, None, (c[1], c[2])))
        elif c[0] == "C": segs.append(("C", cur, (c[1], c[2]), (c[3], c[4]), (c[5], c[6])))
        elif c[0] == "Q": segs.append(("Q", cur, (c[1], c[2]), None, (c[3], c[4])))
        cur = segs[-1][4]
    out = []
    for kind, p0, c1, c2, p3 in reversed(segs):
        m = lambda p: (mir(p[0]), p[1])
        if kind == "L": out.append(("L",) + m(p0))
        elif kind == "C": out.append(("C",) + m(c2) + m(c1) + m(p0))
        else: out.append(("Q",) + m(c1) + m(p0))
    return out

def cmds_to_d(cmds):
    s = []
    for c in cmds:
        s.append(c[0] + " ".join(f(v) for v in c[1:]))
    return " ".join(s)

def outline(right_cmds, bottom_join="L", top_join=None, close=True):
    """Full symmetric outline from right-side cmds (starting at top-centre M ... ending at bottom-centre)."""
    left = mirror_path_cmds(right_cmds)
    cmds = list(right_cmds) + left
    d = cmds_to_d(cmds)
    return d + (" Z" if close else "")

def offset_stroke_d(d, dx=0, dy=0):
    return f'<path d="{d}" transform="translate({dx} {dy})"/>'

# ---------------------------------------------------------------- shared defs (filters / patterns)
def fabric_defs():
    def tex(id_, freq, octv, slope, off, seed=3, blur=0):
        b = f'<feGaussianBlur stdDeviation="{blur}"/>' if blur else ""
        return (f'<filter id="{id_}" x="0" y="0" width="100%" height="100%" color-interpolation-filters="sRGB">'
                f'<feTurbulence type="fractalNoise" baseFrequency="{freq}" numOctaves="{octv}" seed="{seed}"/>{b}'
                f'<feColorMatrix type="matrix" values="0 0 0 0 0  0 0 0 0 0  0 0 0 0 0  {slope} 0 0 0 {off}"/></filter>')
    d = ""
    d += tex("t_jersey", "0.9 0.6", 2, -1.0, 0.62, 3)
    d += tex("t_fleece", "0.55", 3, -1.4, 0.8, 5)
    d += tex("t_wool", "0.38", 4, -1.3, 0.8, 8, 0.5)
    d += tex("t_leather", "0.7", 3, -1.5, 0.85, 2, 0.3)
    d += tex("t_nylon", "0.05 0.35", 2, -0.8, 0.45, 4)
    d += tex("t_canvas", "1.0 0.8", 2, -1.2, 0.75, 6)
    d += tex("t_knit", "0.8 0.4", 2, -1.2, 0.7, 9)
    d += tex("t_twill", "0.6 0.06", 2, -1.3, 0.75, 12)
    d += tex("t_satin", "0.01", 1, -0.5, 0.35, 2)
    d += ('<filter id="b2" x="-20%" y="-20%" width="140%" height="140%"><feGaussianBlur stdDeviation="2"/></filter>'
          '<filter id="b4" x="-30%" y="-30%" width="160%" height="160%"><feGaussianBlur stdDeviation="4"/></filter>'
          '<filter id="b8" x="-40%" y="-40%" width="180%" height="180%"><feGaussianBlur stdDeviation="8"/></filter>'
          '<filter id="b16" x="-60%" y="-60%" width="220%" height="220%"><feGaussianBlur stdDeviation="16"/></filter>'
          '<filter id="b30" x="-80%" y="-80%" width="260%" height="260%"><feGaussianBlur stdDeviation="30"/></filter>')
    # ink print (speckle & slight bleed) -- prints sit *under* the shading
    d += ('<filter id="f_print" x="-2%" y="-2%" width="104%" height="104%" color-interpolation-filters="sRGB">'
          '<feTurbulence type="fractalNoise" baseFrequency="1.3" numOctaves="2" seed="11" result="n"/>'
          '<feColorMatrix in="n" type="matrix" values="0 0 0 0 0  0 0 0 0 0  0 0 0 0 0  4 0 0 0 -0.35" result="a"/>'
          '<feGaussianBlur in="SourceGraphic" stdDeviation="0.35" result="s"/>'
          '<feComposite in="s" in2="a" operator="in"/></filter>')
    # embroidery : raised thread, sheen, shadow
    d += ('<filter id="f_emb" x="-8%" y="-8%" width="116%" height="116%" color-interpolation-filters="sRGB">'
          '<feGaussianBlur in="SourceAlpha" stdDeviation="1.5" result="bl"/>'
          '<feSpecularLighting in="bl" surfaceScale="5" specularConstant="1.0" specularExponent="26" lighting-color="#ffffff" result="sp">'
          '<feDistantLight azimuth="225" elevation="52"/></feSpecularLighting>'
          '<feComposite in="sp" in2="SourceAlpha" operator="in" result="sp2"/>'
          '<feTurbulence type="fractalNoise" baseFrequency="1.4 0.09" numOctaves="2" seed="7" result="th"/>'
          '<feColorMatrix in="th" type="matrix" values="0 0 0 0 0  0 0 0 0 0  0 0 0 0 0  -2.2 0 0 0 1.0" result="th2"/>'
          '<feComposite in="th2" in2="SourceAlpha" operator="in" result="th3"/>'
          '<feOffset in="SourceAlpha" dx="1.6" dy="2.8" result="of"/><feGaussianBlur in="of" stdDeviation="2.2" result="sh0"/>'
          '<feFlood flood-color="#000" flood-opacity=".5"/><feComposite in2="sh0" operator="in" result="sh"/>'
          '<feMerge><feMergeNode in="sh"/><feMergeNode in="SourceGraphic"/><feMergeNode in="th3"/><feMergeNode in="sp2"/></feMerge></filter>')
    # appliqué / patch : thick lift
    d += ('<filter id="f_lift" x="-10%" y="-10%" width="125%" height="125%" color-interpolation-filters="sRGB">'
          '<feOffset in="SourceAlpha" dx="2" dy="5" result="o"/><feGaussianBlur in="o" stdDeviation="4" result="b"/>'
          '<feFlood flood-color="#000" flood-opacity=".42"/><feComposite in2="b" operator="in" result="s"/>'
          '<feMerge><feMergeNode in="s"/><feMergeNode in="SourceGraphic"/></feMerge></filter>')
    d += '<filter id="f_gray"><feColorMatrix type="saturate" values="0"/></filter>'
    d += ('<filter id="f_shadow" x="-30%" y="-30%" width="160%" height="170%"><feGaussianBlur stdDeviation="14"/></filter>')
    # chenille-ish fuzz
    d += ('<filter id="f_chenille" x="-8%" y="-8%" width="116%" height="116%" color-interpolation-filters="sRGB">'
          '<feTurbulence type="fractalNoise" baseFrequency="0.9" numOctaves="2" seed="4" result="n"/>'
          '<feDisplacementMap in="SourceGraphic" in2="n" scale="5" xChannelSelector="R" yChannelSelector="G" result="d"/>'
          '<feGaussianBlur in="SourceAlpha" stdDeviation="2" result="bl"/>'
          '<feSpecularLighting in="bl" surfaceScale="6" specularConstant=".7" specularExponent="12" lighting-color="#fff" result="sp"><feDistantLight azimuth="225" elevation="55"/></feSpecularLighting>'
          '<feComposite in="sp" in2="d" operator="in" result="sp2"/>'
          '<feOffset in="d" dx="2" dy="4" result="o"/><feColorMatrix in="o" type="matrix" values="0 0 0 0 0  0 0 0 0 0  0 0 0 0 0  0 0 0 .5 0" result="sh"/>'
          '<feGaussianBlur in="sh" stdDeviation="3" result="sh2"/>'
          '<feMerge><feMergeNode in="sh2"/><feMergeNode in="d"/><feMergeNode in="sp2"/></feMerge></filter>')
    # rib & twill patterns
    d += ('<pattern id="p_rib" width="5" height="5" patternUnits="userSpaceOnUse"><rect width="5" height="5" fill="#fff" opacity="0"/>'
          '<rect width="2.2" height="5" fill="#000" opacity=".22"/><rect x="2.2" width="1" height="5" fill="#fff" opacity=".14"/></pattern>')
    d += ('<pattern id="p_ribh" width="5" height="5" patternUnits="userSpaceOnUse"><rect width="5" height="2.2" fill="#000" opacity=".22"/>'
          '<rect y="2.2" width="5" height="1" fill="#fff" opacity=".14"/></pattern>')
    d += ('<pattern id="p_knit" width="7" height="9" patternUnits="userSpaceOnUse"><path d="M0 0 L3.5 7 L7 0" fill="none" stroke="#000" stroke-opacity=".20" stroke-width="1.6"/>'
          '<path d="M0 1.6 L3.5 8.6 L7 1.6" fill="none" stroke="#fff" stroke-opacity=".15" stroke-width="1"/></pattern>')
    d += ('<pattern id="p_quilt" width="1000" height="1000" patternUnits="userSpaceOnUse"></pattern>')
    return d

TEX = {"jersey": "t_jersey", "fleece": "t_fleece", "wool": "t_wool", "leather": "t_leather", "nylon": "t_nylon",
       "canvas": "t_canvas", "knit": "t_knit", "twill": "t_twill", "satin": "t_satin", "none": None}
TEX_OP = {"jersey": .40, "fleece": .50, "wool": .55, "leather": .50, "nylon": .14, "canvas": .50, "knit": .35, "twill": .45, "satin": .2}

def shade_color(c, k):
    """k>0 lighten toward white, k<0 darken toward black."""
    h = c.lstrip("#"); r, g, b = [int(h[i:i+2], 16) for i in (0, 2, 4)]
    if k >= 0: r, g, b = [round(v + (255 - v) * k) for v in (r, g, b)]
    else: r, g, b = [round(v * (1 + k)) for v in (r, g, b)]
    return f"#{r:02x}{g:02x}{b:02x}"

# ---------------------------------------------------------------- Part model
def part(id, d, color="body", tex="jersey", shade="tube", ang=0, kind="fill", sw=0, folds=(), seams=(), rib=None,
         gloss=0.0, lift=False, z=0, edge=.42, clip_to=None):
    """color: key into the garment's colourway dict (or '#hex').  rib: None|'v'|'h'|'knit'."""
    return dict(id=id, d=d, color=color, tex=tex, shade=shade, ang=ang, kind=kind, sw=sw, folds=list(folds),
                seams=list(seams), rib=rib, gloss=gloss, lift=lift, z=z, edge=edge, clip_to=clip_to)

def paint_part(p, colours, art_print="", art_emb="", art_lift=""):
    col = colours.get(p["color"], p["color"])
    mid = uid("pm")
    d = p["d"]
    x0, y0, x1, y1 = bbox(d, pad=p["sw"] / 2 + 4 if p["kind"] == "stroke" else 4)
    w, h = x1 - x0, y1 - y0
    if p["kind"] == "stroke":
        shape = f'<path d="{d}" fill="none" stroke="#fff" stroke-width="{p["sw"]}" stroke-linecap="butt" stroke-linejoin="round"/>'
        edge_shape = f'<path d="{d}" fill="none" stroke="#000" stroke-width="{p["sw"]}" stroke-linecap="butt"/>'
    else:
        shape = f'<path d="{d}" fill="#fff"/>'
        edge_shape = f'<path d="{d}" fill="none" stroke="#000" stroke-width="22"/>'
    out = [f'<mask id="{mid}" maskUnits="userSpaceOnUse" x="{x0-20}" y="{y0-20}" width="{w+40}" height="{h+40}">{shape}</mask>']
    g = [f'<g mask="url(#{mid})">', f'<rect x="{x0}" y="{y0}" width="{w}" height="{h}" fill="{col}"/>']
    # print layer (below texture/shade so it takes fabric detail)
    if art_print: g.append(f'<g filter="url(#f_print)">{art_print}</g>')
    tid = TEX.get(p["tex"])
    if tid:
        lf = 0.45 if lum(col) > 0.45 else 1.0
        g.append(f'<rect x="{x0}" y="{y0}" width="{w}" height="{h}" filter="url(#{tid})" opacity="{TEX_OP[p["tex"]]*lf:.2f}"/>')
    if p["rib"]:
        pat = {"v": "p_rib", "h": "p_ribh", "knit": "p_knit"}[p["rib"]]
        g.append(f'<rect x="{x0}" y="{y0}" width="{w}" height="{h}" fill="url(#{pat})"/>')
    # volume shading
    gid = uid("gr")
    cxm, cym = (x0 + x1) / 2, (y0 + y1) / 2
    if p["shade"] == "tube":
        R = max(w, h) / 2
        a = math.radians(p["ang"]); dx, dy = math.cos(a) * w / 2, math.sin(a) * w / 2
        out.append(f'<linearGradient id="{gid}" gradientUnits="userSpaceOnUse" x1="{f(cxm-dx)}" y1="{f(cym-dy)}" x2="{f(cxm+dx)}" y2="{f(cym+dy)}">'
                   '<stop offset="0" stop-color="#000" stop-opacity=".20"/><stop offset=".18" stop-color="#000" stop-opacity=".03"/>'
                   '<stop offset=".40" stop-color="#fff" stop-opacity=".07"/><stop offset=".62" stop-color="#fff" stop-opacity=".0"/>'
                   '<stop offset="1" stop-color="#000" stop-opacity=".24"/></linearGradient>')
        g.append(f'<rect x="{x0}" y="{y0}" width="{w}" height="{h}" fill="url(#{gid})"/>')
    elif p["shade"] == "diag":
        out.append(f'<linearGradient id="{gid}" gradientUnits="userSpaceOnUse" x1="{x0}" y1="{y0}" x2="{x1}" y2="{y1}">'
                   '<stop offset="0" stop-color="#fff" stop-opacity=".16"/><stop offset=".5" stop-color="#fff" stop-opacity="0"/>'
                   '<stop offset="1" stop-color="#000" stop-opacity=".26"/></linearGradient>')
        g.append(f'<rect x="{x0}" y="{y0}" width="{w}" height="{h}" fill="url(#{gid})"/>')
    elif p["shade"] == "vert":
        out.append(f'<linearGradient id="{gid}" gradientUnits="userSpaceOnUse" x1="0" y1="{y0}" x2="0" y2="{y1}">'
                   '<stop offset="0" stop-color="#fff" stop-opacity=".12"/><stop offset=".7" stop-color="#000" stop-opacity=".02"/>'
                   '<stop offset="1" stop-color="#000" stop-opacity=".22"/></linearGradient>')
        g.append(f'<rect x="{x0}" y="{y0}" width="{w}" height="{h}" fill="url(#{gid})"/>')
    if p["gloss"]:
        gg = uid("gl")
        out.append(f'<linearGradient id="{gg}" gradientUnits="userSpaceOnUse" x1="{x0}" y1="{y0}" x2="{x1}" y2="{y0 + h*0.8}">'
                   f'<stop offset="0" stop-color="#fff" stop-opacity="0"/><stop offset=".35" stop-color="#fff" stop-opacity="{p["gloss"]}"/>'
                   '<stop offset=".5" stop-color="#fff" stop-opacity="0"/><stop offset=".72" stop-color="#fff" stop-opacity="' + str(p["gloss"]*.6) + '"/><stop offset="1" stop-color="#fff" stop-opacity="0"/></linearGradient>')
        g.append(f'<rect x="{x0}" y="{y0}" width="{w}" height="{h}" fill="url(#{gg})"/>')
    # inner edge shadow (ambient occlusion)
    if p["edge"]:
        g.append(f'<g filter="url(#b8)" opacity="{p["edge"]}">{edge_shape}</g>')
    # folds
    for fd in p["folds"]:
        dd, k = fd if isinstance(fd, tuple) else (fd, 1.0)
        g.append(f'<path d="{dd}" fill="none" stroke="#000" stroke-opacity="{.13*k:.2f}" stroke-width="{34*abs(k)}" stroke-linecap="round" filter="url(#b16)"/>')
        g.append(f'<path d="{dd}" fill="none" stroke="#fff" stroke-opacity="{.10*k:.2f}" stroke-width="{18*abs(k)}" stroke-linecap="round" filter="url(#b8)" transform="translate(16 -4)"/>')
    # seams (stitch lines) - drawn on top of shading
    for sd in p["seams"]:
        dd, kind = sd if isinstance(sd, tuple) else (sd, "stitch")
        if kind == "stitch":
            g.append(f'<path d="{dd}" fill="none" stroke="#000" stroke-opacity=".28" stroke-width="1.5" transform="translate(0.8 1.3)"/>')
            g.append(f'<path d="{dd}" fill="none" stroke="{shade_color(col, .35)}" stroke-width="1.6" stroke-dasharray="6 4.5" stroke-opacity=".95"/>')
        elif kind == "seam":
            g.append(f'<path d="{dd}" fill="none" stroke="#000" stroke-opacity=".30" stroke-width="2.2" filter="url(#b2)"/>')
            g.append(f'<path d="{dd}" fill="none" stroke="#fff" stroke-opacity=".18" stroke-width="1.6" transform="translate(1.6 1.6)"/>')
        elif kind == "dark":
            g.append(f'<path d="{dd}" fill="none" stroke="#000" stroke-opacity=".5" stroke-width="3"  filter="url(#b2)"/>')
    # embroidery & lifted layers (above the shading)
    if art_emb: g.append(f'<g filter="url(#f_emb)">{art_emb}</g>')
    if art_lift: g.append(art_lift)
    g.append("</g>")
    return "".join(out) + "".join(g)

def mock(parts, colours, w=1000, h=1000, art=None, bg=None, backdrop="studio", shadow=True, extra_under="", extra_over="",
         floor=None, scale_art=1):
    """parts: list of part dicts.  art: {'print': {partid: svg}, 'emb': {...}, 'lift': {...}, 'over': svg (free layer on top)}."""
    art = art or {}
    ordered = sorted(parts, key=lambda p: p["z"])
    body = []
    if backdrop == "studio":
        defs_bg = ('<radialGradient id="bgrad" cx="50%" cy="42%" r="75%"><stop offset="0" stop-color="#F6F2E9"/><stop offset=".65" stop-color="#E8E1D2"/>'
                   '<stop offset="1" stop-color="#D3CAB6"/></radialGradient>')
        body.append(f'<rect width="{w}" height="{h}" fill="url(#bgrad)"/>')
    elif backdrop:
        defs_bg = ""
        body.append(f'<rect width="{w}" height="{h}" fill="{backdrop}"/>')
    else:
        defs_bg = ""
    body.append(extra_under)
    # ground shadow = union of all part silhouettes, blurred
    if shadow:
        sh = "".join((f'<path d="{p["d"]}" fill="#1a1020"/>' if p["kind"] == "fill" else
                      f'<path d="{p["d"]}" fill="none" stroke="#1a1020" stroke-width="{p["sw"]}" stroke-linecap="round"/>') for p in ordered)
        body.append(f'<g filter="url(#f_shadow)" opacity=".38" transform="translate(10 26)">{sh}</g>')
        body.append(f'<g filter="url(#b8)" opacity=".30" transform="translate(3 8)">{sh}</g>')
    defs = fabric_defs() + defs_bg
    for p in ordered:
        ap = art.get("print", {}).get(p["id"], ""); ae = art.get("emb", {}).get(p["id"], ""); al = art.get("lift", {}).get(p["id"], "")
        body.append(paint_part(p, colours, ap, ae, al))
    body.append(art.get("over", ""))
    body.append(extra_over)
    # the paint_part returns defs-like elements (mask, gradients) inline: valid in SVG (masks may live anywhere)
    return svg(w, h, "".join(body), defs=defs)

# ---------------------------------------------------------------- technical flat renderer
def flat(parts, w=1000, h=1000, art=None, dims=(), callouts=(), title=None, stroke="#111", fill="#fff", zebra=True,
         art_override=None, lw=1.6):
    """Technical drawing: line art + seam dashes + (optional) simplified artwork outline."""
    ordered = sorted(parts, key=lambda p: p["z"])
    body = ['<rect width="%d" height="%d" fill="#fff"/>' % (w, h)]
    for p in ordered:
        fillc = "#fff"
        if p["kind"] == "fill":
            body.append(f'<path d="{p["d"]}" fill="{fillc}" stroke="{stroke}" stroke-width="{lw}" stroke-linejoin="round"/>')
        else:
            # stroke parts (e.g. rib collar) -> draw as double line
            body.append(f'<path d="{p["d"]}" fill="none" stroke="{stroke}" stroke-width="{p["sw"]+lw*2}" stroke-linecap="round" stroke-linejoin="round"/>')
            body.append(f'<path d="{p["d"]}" fill="none" stroke="#fff" stroke-width="{p["sw"]}" stroke-linecap="round" stroke-linejoin="round"/>')
        for sd in p["seams"]:
            dd, kind = sd if isinstance(sd, tuple) else (sd, "stitch")
            if kind == "stitch":
                body.append(f'<path d="{dd}" fill="none" stroke="{stroke}" stroke-width="1" stroke-dasharray="5 3.5"/>')
            else:
                body.append(f'<path d="{dd}" fill="none" stroke="{stroke}" stroke-width="{lw*.8}"/>')
        if p["rib"] and p["kind"] == "fill":
            pat = {"v": "p_rib", "h": "p_ribh", "knit": "p_knit"}[p["rib"]]
            body.append(f'<path d="{p["d"]}" fill="url(#{pat})" opacity=".55"/>')
    if art:
        for k in ("print", "emb", "lift"):
            for pid, a in art.get(k, {}).items():
                body.append(f'<g opacity=".9">{a}</g>' if not art_override else art_override(a))
        body.append(art.get("over", ""))
    for dm in dims: body.append(dm)
    for c in callouts: body.append(c)
    defs = fabric_defs()
    return svg(w, h, "".join(body), defs=defs)
