"""Reusable artwork pieces (vector, outlined text) for garments.  All coordinates local; use place() to size in cm."""
from identity import *
from engine import PXCM

REGISTRY = {}
def place(frag, nat_w, nat_h, cx, top, w_cm, anchor="top", name=None, meta=None):
    """Scale artwork of natural size (nat_w x nat_h, local origin top-left) to w_cm centimetres wide,
    centred on x=cx with its top (or centre) at y=top (garment space, 10px = 1cm)."""
    k = w_cm * PXCM / nat_w
    x = cx - nat_w * k / 2
    y = top if anchor == "top" else top - nat_h * k / 2
    if name: REGISTRY[name] = dict(frag=frag, nw=nat_w, nh=nat_h, w_cm=w_cm, h_cm=nat_h * k / PXCM, meta=meta or {})
    return f'<g transform="translate({x:.1f} {y:.1f}) scale({k:.4f})">{frag}</g>', nat_h * k / PXCM

def wm_art(fg, lam=None, size=100):
    b, w, c = wordmark(size, fg, 0, size * 0.74, lam_fill=lam)
    return b, w, size * 0.74

def motto_line(fg, size=20, width=None, ar=False):
    if ar:
        return T(MOTTO_AR, "reem", size, 0, size * .9, fg, wght=600), text_w(MOTTO_AR, "reem", size, wght=600), size * 1.2
    return T(MOTTO_FR, "archivo", size, 0, size * .72, fg, tracking=160, wght=700, wdth=112), text_w(MOTTO_FR, "archivo", size, 160, wght=700, wdth=112), size

def surus_art(fg, accent, construction=False, cons_col=None):
    return surus(fg, accent, construction=construction, cons_col=cons_col), 440, 320

def mono_art(fg, accent, R=100):
    return monogram(R, R, R, fg, accent), 2 * R, 2 * R

def mono_text_block(lines, fg, size=14, leading=1.5, key="mono", weight=500, w=None, align="start"):
    out = []; y = size
    for ln in lines:
        out.append(T(ln, key, size, 0 if align == "start" else (w or 0), y, fg, align if align != "start" else "start", wght=weight))
        y += size * leading
    return "".join(out), (w or max(text_w(l, key, size, wght=weight) for l in lines)), y - size * leading + size * .3

# --- scientific graphic pieces ------------------------------------------------
def trajectory(w, h, fg, acc, steps=7, sw=2.2):
    """Parabolic crossing (the 'traversée'): f(x) = -4h/w^2 (x)(x-w).  Sample points = elephants' steps."""
    pts = []
    d = f"M0 {h}"
    N = 40
    for i in range(1, N + 1):
        x = w * i / N; y = h - (4 * h / (w * w)) * x * (w - x) * 1.0
        d += f" L{x:.1f} {y:.1f}"
    out = [f'<path d="{d}" fill="none" stroke="{fg}" stroke-width="{sw}" stroke-dasharray="1 7" stroke-linecap="round"/>']
    for i in range(steps + 1):
        x = w * i / steps; y = h - (4 * h / (w * w)) * x * (w - x)
        r = 5 if i not in (0, steps) else 8
        out.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{r}" fill="{acc if i in (0, steps) else fg}"/>')
    out.append(f'<path d="M0 {h} H{w}" stroke="{fg}" stroke-width="{sw}"/>')
    return "".join(out)

def graph_axes(w, h, fg, ticks=8, sw=1.6, arrow=True):
    d = f'<path d="M0 {h} H{w} M0 {h} V0" stroke="{fg}" stroke-width="{sw}" fill="none"/>'
    for i in range(1, ticks + 1):
        x = w * i / ticks
        d += f'<path d="M{x} {h-5} V{h+5}" stroke="{fg}" stroke-width="{sw}"/>'
    return d

def peaks_fill(w, h, fg, n=3):
    """Solid Alpine skyline"""
    pw = w / n
    d = f"M0 {h} " + " ".join(f"L{pw*(i+.5):.1f} {h*(0 if i%2==0 else .38):.1f} L{pw*(i+1):.1f} {h}" for i in range(n)) + " Z"
    return f'<path d="{d}" fill="{fg}"/>'

def label_tag(lines, fg, bg=None, size=12, pad=10, key="mono", weight=600):
    """lab specimen label: boxed mono lines"""
    mw = max(text_w(l, key, size, wght=weight) for l in lines)
    w = mw + pad * 2; h = len(lines) * size * 1.5 + pad * 1.4
    out = (f'<rect x="0" y="0" width="{w}" height="{h}" fill="{bg or "none"}" stroke="{fg}" stroke-width="1.6"/>' )
    y = pad + size * .8
    for l in lines:
        out += T(l, key, size, pad, y, fg, wght=weight); y += size * 1.5
    return out, w, h

def tick_ruler(length_mm, fg, h=14, scale=4):
    """A cm/mm ruler strip (scale px per mm) - used as sleeve-hem detail."""
    out = f'<path d="M0 {h} H{length_mm*scale}" stroke="{fg}" stroke-width="1.4"/>'
    for i in range(length_mm + 1):
        hh = h if i % 10 == 0 else (h * .6 if i % 5 == 0 else h * .35)
        out += f'<path d="M{i*scale} {h} V{h-hh}" stroke="{fg}" stroke-width="1.2"/>'
    for i in range(0, length_mm + 1, 10):
        out += T(str(i // 10), "mono", 8, i * scale, h + 11, fg, "middle", wght=600)
    return out

# Coordinates (accurate): Tébourba (ancient Thuburbo Minus) ~36.83 N 9.83 E
COORD = "36°50′N · 9°50′E"
