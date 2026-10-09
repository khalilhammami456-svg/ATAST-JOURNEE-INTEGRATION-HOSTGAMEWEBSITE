"""Studio library: palette, outlined text (HarfBuzz + fontTools), SVG helpers, Chromium renderer.

All typography in the collection artwork is converted to vector outlines so that the
SVG/PDF files are font-independent (Arabic is shaped by HarfBuzz => correct joining).
"""
import io, math, os, subprocess, tempfile, hashlib
from pathlib import Path
from fontTools.ttLib import TTFont
from fontTools.varLib import instancer
from fontTools.pens.svgPathPen import SVGPathPen
from fontTools.pens.transformPen import TransformPen
import uharfbuzz as hb

ROOT = Path(__file__).resolve().parent.parent.parent
FONTDIR = ROOT / "brand-identity" / "typography"
CHROME = "/opt/pw-browsers/chromium_headless_shell-1194/chrome-linux/headless_shell"

# ------------------------------------------------------------------ palette
PAL = dict(
    nuit="#0B1226",      # deep navy, near-black (core)
    encre="#06080F",     # ink black
    chalk="#F1EEE7",     # chalk white
    chalk_d="#D9D4C8",
    lab="#8E959E",       # lab gray
    lab_d="#4B525C",
    lab_l="#C3C8CE",
    rose="#D9A3A8",      # dusty rose
    rose_l="#EBC6C8",
    rose_d="#B87B83",
    maroon="#5C1526",    # deep maroon
    violet="#6B4EF5",    # cosmic violet (accent)
    blue="#2E7BFF",      # electric blue (accent)
    red="#C8102E",       # Tunisian red (controlled accent only)
)

FONTFILES = {
    "archivo": ("Archivo-VF.ttf", {"wdth": 100, "wght": 400}),
    "bricolage": ("BricolageGrotesque-VF.ttf", {"opsz": 48, "wdth": 100, "wght": 600}),
    "grotesk": ("SpaceGrotesk-VF.ttf", {"wght": 500}),
    "mono": ("JetBrainsMono-VF.ttf", {"wght": 500}),
    "serif": ("InstrumentSerif-Regular.ttf", {}),
    "serifi": ("InstrumentSerif-Italic.ttf", {}),
    "reem": ("ReemKufi-VF.ttf", {"wght": 600}),
    "kufi": ("NotoKufiArabic-VF.ttf", {"wght": 600}),
    "script": ("GreatVibes-Regular.ttf", {}),
    "pinyon": ("PinyonScript-Regular.ttf", {}),
    "grad": ("Graduate-Regular.ttf", {}),
    "aref": ("ArefRuqaa-Bold.ttf", {}),
    "lalezar": ("Lalezar-Regular.ttf", {}),
}
_faces = {}

class Face:
    def __init__(self, key, axes):
        fn, defaults = FONTFILES[key]
        ax = dict(defaults); ax.update(axes)
        f = TTFont(str(FONTDIR / fn))
        if "fvar" in f:
            have = {a.axisTag for a in f["fvar"].axes}
            f = instancer.instantiateVariableFont(f, {k: v for k, v in ax.items() if k in have}, inplace=False)
        buf = io.BytesIO(); f.save(buf); data = buf.getvalue()
        self.tt = TTFont(io.BytesIO(data))
        self.order = self.tt.getGlyphOrder()
        self.gs = self.tt.getGlyphSet()
        self.upem = self.tt["head"].unitsPerEm
        self.hbfont = hb.Font(hb.Face(data))

def face(key, **axes):
    k = (key, tuple(sorted(axes.items())))
    if k not in _faces:
        _faces[k] = Face(key, axes)
    return _faces[k]

def shape(txt, key, size, tracking=0, features=None, **axes):
    """-> list of (glyphname, x, y) in px for baseline at 0, plus total advance (px)."""
    fc = face(key, **axes)
    buf = hb.Buffer(); buf.add_str(txt); buf.guess_segment_properties()
    hb.shape(fc.hbfont, buf, features or {"kern": True, "liga": True})
    s = size / fc.upem
    cur = 0.0; out = []
    rtl = buf.direction == "rtl"
    for info, pos in zip(buf.glyph_infos, buf.glyph_positions):
        out.append((fc.order[info.codepoint], (cur + pos.x_offset) * s, pos.y_offset * s))
        cur += pos.x_advance + (0 if rtl else tracking * fc.upem / 1000.0)
    return fc, out, cur * s

def text_d(txt, key, size, x=0, y=0, anchor="start", tracking=0, features=None, **axes):
    fc, glyphs, w = shape(txt, key, size, tracking, features, **axes)
    if anchor == "middle": x -= w / 2
    elif anchor == "end": x -= w
    s = size / fc.upem
    parts = []
    for name, gx, gy in glyphs:
        pen = SVGPathPen(fc.gs, ntos=lambda v: f"{v:.2f}".rstrip("0").rstrip("."))
        tp = TransformPen(pen, (s, 0, 0, -s, x + gx, y - gy))
        fc.gs[name].draw(tp)
        parts.append(pen.getCommands())
    return " ".join(p for p in parts if p), w

def T(txt, key, size, x=0, y=0, fill="#000", anchor="start", tracking=0, extra="", **axes):
    d, w = text_d(txt, key, size, x, y, anchor, tracking, **axes)
    return f'<path d="{d}" fill="{fill}" {extra}/>'

def text_w(txt, key, size, tracking=0, **axes):
    return shape(txt, key, size, tracking, None, **axes)[2]

def T_arc(txt, key, size, cx, cy, r, mid_deg=-90, fill="#000", tracking=0, inside=False, **axes):
    """Set caps text on a circle, centred at mid_deg (-90 = top). inside=True reads along bottom (upright)."""
    widths = [text_w(c, key, size, 0, **axes) for c in txt]
    trk = tracking * size / 1000.0
    total = sum(widths) + trk * (len(txt) - 1)
    out = []
    cur = -total / 2
    for c, w in zip(txt, widths):
        mid = cur + w / 2
        cur += w + trk
        if c == " ": continue
        ang = mid / r  # radians along arc
        if not inside:
            a = math.radians(mid_deg) + ang
            px, py = cx + r * math.cos(a), cy + r * math.sin(a)
            rot = math.degrees(a) + 90
        else:
            a = math.radians(mid_deg) - ang
            px, py = cx + r * math.cos(a), cy + r * math.sin(a)
            rot = math.degrees(a) - 90
        d, _ = text_d(c, key, size, -w / 2, 0, **axes)
        out.append(f'<path transform="translate({px:.2f} {py:.2f}) rotate({rot:.2f})" d="{d}" fill="{fill}"/>')
    return "".join(out)

# ------------------------------------------------------------------ svg helpers
def svg(w, h, body, defs="", bg=None, extra=""):
    b = f'<rect width="{w}" height="{h}" fill="{bg}"/>' if bg else ""
    return (f'<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" '
            f'viewBox="0 0 {w} {h}" width="{w}" height="{h}" {extra}><defs>{defs}</defs>{b}{body}</svg>')

def write(path, content):
    path = Path(path); path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8"); return path

def render(svg_path, png=None, pdf=None, scale=1.0, bg="transparent"):
    """Rasterise / print an SVG file with headless Chromium."""
    svg_path = Path(svg_path).resolve()
    txt = svg_path.read_text(encoding="utf-8")
    import re
    m = re.search(r"""viewBox=["']0 0 ([\d.]+) ([\d.]+)["']""", txt)
    w, h = float(m.group(1)), float(m.group(2))
    html = (f'<!doctype html><meta charset="utf-8"><style>@page{{size:{w}px {h}px;margin:0}}'
            f'html,body{{margin:0;padding:0;background:{bg}}}img{{display:block;width:{w}px;height:{h}px}}</style>'
            f'<img src="{svg_path.as_uri()}">')
    tmp = Path(tempfile.mkdtemp()) / "r.html"; tmp.write_text(html)
    base = [CHROME, "--no-sandbox", "--disable-gpu", "--hide-scrollbars",
            "--allow-file-access-from-files", "--disable-web-security"]
    if png:
        subprocess.run(base + [f"--screenshot={Path(png).resolve()}", f"--window-size={int(w)},{int(h)}",
                               f"--force-device-scale-factor={scale}",
                               "--default-background-color=" + ("00000000" if bg == "transparent" else "FFFFFFFF"),
                               tmp.as_uri()], check=True, capture_output=True, timeout=180)
    if pdf:
        subprocess.run(base + [f"--print-to-pdf={Path(pdf).resolve()}", "--no-pdf-header-footer", tmp.as_uri()],
                       check=True, capture_output=True, timeout=180)

def render_html(html_path, png=None, pdf=None, w=1920, h=1080, scale=1.0):
    html_path = Path(html_path).resolve()
    base = [CHROME, "--no-sandbox", "--disable-gpu", "--hide-scrollbars",
            "--allow-file-access-from-files", "--virtual-time-budget=4000"]
    if png:
        subprocess.run(base + [f"--screenshot={Path(png).resolve()}", f"--window-size={w},{h}",
                               f"--force-device-scale-factor={scale}", html_path.as_uri()], check=True, capture_output=True, timeout=240)
    if pdf:
        subprocess.run(base + [f"--print-to-pdf={Path(pdf).resolve()}", "--no-pdf-header-footer", html_path.as_uri()],
                       check=True, capture_output=True, timeout=300)

def lum(hexc):
    h = hexc.lstrip("#"); r, g, b = [int(h[i:i+2], 16) / 255 for i in (0, 2, 4)]
    f = lambda c: c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4
    return 0.2126 * f(r) + 0.7152 * f(g) + 0.0722 * f(b)

def contrast(a, b):
    la, lb = sorted([lum(a), lum(b)], reverse=True)
    return (la + 0.05) / (lb + 0.05)
