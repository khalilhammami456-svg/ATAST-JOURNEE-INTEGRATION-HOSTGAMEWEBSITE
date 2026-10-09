"""Technical flats generated from the 3D garment's own pattern pieces (system python).

The UV atlas of every garment is a *pattern layout*: Front / Back / Sleeve pieces in true metres (see shell.build_uv).
We take those pieces, trace their outline, add the print / embroidery placements recorded by texlab (`*_placements.json`)
and draw dimensioned vector flats (SVG).  Everything is derived from the model, nothing is hand-drawn.

usage: python tflat.py ITEM [colourway]  ->  technical-flats/<ITEM>_flat.svg
"""
import sys, json, math
from pathlib import Path
HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(HERE))
from collection import ITEMS, PAL, SPEC

INK = "#0B1226"; GRID = "#9AA3B2"; ACC = "#6B4EF5"; RED = "#C8102E"
KIND_COL = {"embroidery": "#6B4EF5", "print": "#2E7BFF", "woven": "#B87B83"}
KIND_FR = {"embroidery": "broderie", "print": "impression", "woven": "tissé"}


def _key(p):
    return (round(p[0] * 2000), round(p[1] * 2000))


def outline(polys):
    """Outer boundary of a set of quads (piece-local metres) -> list of loops (largest first)."""
    cnt, pts = {}, {}
    for q in polys:
        n = len(q)
        for i in range(n):
            a, b = _key(q[i]), _key(q[(i + 1) % n])
            pts[a] = q[i]; pts[b] = q[(i + 1) % n]
            e = (a, b) if a < b else (b, a)
            cnt[e] = cnt.get(e, 0) + 1
    adj = {}
    for (a, b), c in cnt.items():
        if c == 1:
            adj.setdefault(a, []).append(b); adj.setdefault(b, []).append(a)
    seen, loops = set(), []
    for start in list(adj):
        if start in seen:
            continue
        loop, cur, prev = [], start, None
        while cur not in seen:
            seen.add(cur); loop.append(pts[cur])
            nxt = [n for n in adj[cur] if n != prev and n not in seen]
            if not nxt:
                break
            prev, cur = cur, nxt[0]
        if len(loop) > 8:
            loops.append(loop)
    loops.sort(key=lambda l: -abs(_area(l)))
    return loops


def _area(l):
    return 0.5 * sum(l[i][0] * l[(i + 1) % len(l)][1] - l[(i + 1) % len(l)][0] * l[i][1] for i in range(len(l)))


def simplify(l, eps=0.0015):
    if len(l) < 4:
        return l
    def dp(a, b, pts):
        if len(pts) < 3:
            return pts
        (x1, y1), (x2, y2) = pts[0], pts[-1]
        dx, dy = x2 - x1, y2 - y1
        L = math.hypot(dx, dy) or 1e-9
        best, bi = -1, 0
        for i in range(1, len(pts) - 1):
            d = abs(dy * pts[i][0] - dx * pts[i][1] + x2 * y1 - y2 * x1) / L
            if d > best:
                best, bi = d, i
        if best > eps:
            left = dp(a, bi, pts[:bi + 1]); right = dp(bi, b, pts[bi:])
            return left[:-1] + right
        return [pts[0], pts[-1]]
    # split the closed loop at its two farthest-apart vertices so DP is stable
    n = len(l)
    i0 = 0
    j0 = max(range(n), key=lambda j: math.hypot(l[j][0] - l[0][0], l[j][1] - l[0][1]))
    a = l[i0:j0 + 1]; b = l[j0:] + l[:1]
    return dp(0, 0, a)[:-1] + dp(0, 0, b)[:-1]


def width_at(loop, z):
    xs = []
    n = len(loop)
    for i in range(n):
        (x1, z1), (x2, z2) = loop[i], loop[(i + 1) % n]
        if (z1 - z) * (z2 - z) <= 0 and z1 != z2:
            xs.append(x1 + (x2 - x1) * (z - z1) / (z2 - z1))
    return (min(xs), max(xs)) if len(xs) >= 2 else (0, 0)


def flat_svg(item, manifest, placements, out, mm_per_px=2.4, label=True):
    meta = manifest["meta"]
    pieces = [p for p in manifest["order"] if p in manifest["polys"]]
    show = []
    for p in pieces:
        loops = outline(manifest["polys"][p])
        if not loops:
            continue
        outer = simplify(loops[0])
        xs = [q[0] for q in outer]; zs = [q[1] for q in outer]
        show.append(dict(name=p, loop=outer, x0=min(xs), x1=max(xs), z0=min(zs), z1=max(zs)))
    # layout: Front | Back on row 1, sleeves on row 2 (all in mm)
    pad = 0.07
    rows = [[s for s in show if s["name"] in ("Front", "Back")], [s for s in show if s["name"] not in ("Front", "Back")]]
    cursor_y = pad
    W = 0
    place = {}
    for row in rows:
        if not row:
            continue
        cx = pad
        h = 0
        for s in row:
            place[s["name"]] = (cx - s["x0"], cursor_y - s["z0"] * -1 if False else cursor_y)   # filled below
            s["ox"] = cx - s["x0"]
            s["oy"] = cursor_y + s["z1"]                   # image y = oy - z
            cx += (s["x1"] - s["x0"]) + pad + 0.06
            h = max(h, s["z1"] - s["z0"])
        W = max(W, cx)
        cursor_y += h + pad + 0.05
    H = cursor_y
    sc = 1000.0                                           # metres -> SVG units (1 unit = 1 mm)
    g = []
    g.append(f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W * sc:.1f} {H * sc + 60:.1f}" width="{W * sc * 0.9:.0f}" height="{(H * sc + 60) * 0.9:.0f}" font-family="JetBrains Mono, monospace">')
    g.append('<rect width="100%" height="100%" fill="#FFFFFF"/>')
    for s in show:
        d = " ".join(("M" if i == 0 else "L") + f"{(s['ox'] + q[0]) * sc:.1f},{(s['oy'] - q[1]) * sc:.1f}" for i, q in enumerate(s["loop"])) + " Z"
        g.append(f'<path d="{d}" fill="#F4F5F8" stroke="{INK}" stroke-width="2.2" stroke-linejoin="round"/>')
        # grain line + notches
        cx = (s["ox"] + (s["x0"] + s["x1"]) / 2) * sc
        y0, y1 = (s["oy"] - s["z0"] - 0.05) * sc, (s["oy"] - s["z1"] + 0.05) * sc
        g.append(f'<path d="M{cx:.1f},{y0 - 40:.1f} L{cx:.1f},{y1 + 40:.1f}" stroke="{GRID}" stroke-width="1.2" stroke-dasharray="14 8"/>')
        g.append(f'<text x="{(s["ox"] + s["x0"]) * sc + 6:.1f}" y="{(s["oy"] - s["z1"]) * sc - 10:.1f}" font-size="19" fill="{INK}" font-weight="700">{s["name"].replace("_", " ").upper()}</text>')
        # horizontal dimension (width at chest / max)
        zc = meta["chest_z"] if s["name"] in ("Front", "Back") else (s["z0"] + s["z1"]) / 2
        a, b = width_at(s["loop"], zc)
        if b > a:
            yy = (s["oy"] - zc) * sc
            g.append(f'<path d="M{(s["ox"] + a) * sc:.1f},{yy:.1f} L{(s["ox"] + b) * sc:.1f},{yy:.1f}" stroke="{RED}" stroke-width="1.4"/>')
            g.append(f'<text x="{(s["ox"] + (a + b) / 2) * sc:.1f}" y="{yy - 8:.1f}" font-size="18" fill="{RED}" text-anchor="middle">{(b - a) * 100:.1f} cm</text>')
        # vertical dimension
        xv = (s["ox"] + s["x1"]) * sc + 22
        g.append(f'<path d="M{xv:.1f},{(s["oy"] - s["z1"]) * sc:.1f} L{xv:.1f},{(s["oy"] - s["z0"]) * sc:.1f}" stroke="{RED}" stroke-width="1.4"/>')
        g.append(f'<text transform="translate({xv + 20:.1f},{(s["oy"] - (s["z0"] + s["z1"]) / 2) * sc:.1f}) rotate(90)" font-size="18" fill="{RED}" text-anchor="middle">{(s["z1"] - s["z0"]) * 100:.1f} cm</text>')
    # placements
    num = 0
    legend = []
    seen = set()
    for pl in placements:
        s = next((q for q in show if q["name"] == pl["piece"]), None)
        if not s:
            continue
        key = (pl["piece"], round(pl["x"], 2), round(pl["z"], 2), round(pl["w"], 2))
        if key in seen or pl["w"] < 0.012 or pl["w"] > 1.5 * (s["x1"] - s["x0"]):
            continue
        seen.add(key)
        num += 1
        w, h = pl["w"] * sc, pl["h"] * sc
        cx, cy = (s["ox"] + pl["x"]) * sc, (s["oy"] - pl["z"]) * sc
        col = KIND_COL.get(pl["kind"], ACC)
        rot = pl.get("rot", 0.0)
        g.append(f'<g transform="translate({cx:.1f},{cy:.1f}) rotate({rot:.1f})"><rect x="{-w / 2:.1f}" y="{-h / 2:.1f}" width="{w:.1f}" height="{h:.1f}" fill="{col}" fill-opacity="0.10" stroke="{col}" stroke-width="1.6" stroke-dasharray="7 4"/></g>')
        g.append(f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="14" fill="{col}"/><text x="{cx:.1f}" y="{cy + 6:.1f}" font-size="17" fill="#fff" text-anchor="middle" font-weight="700">{num}</text>')
        legend.append((num, pl["kind"], pl["piece"], pl["w"], pl["h"], pl["x"], pl["z"]))
    g.append("</svg>")
    Path(out).parent.mkdir(parents=True, exist_ok=True)
    Path(out).write_text("\n".join(g), encoding="utf-8")
    return dict(legend=legend, size_m=(W, H))


if __name__ == "__main__":
    it = sys.argv[1]
    mp = ROOT / "3d" / "models" / it / f"{it}_manifest.json"
    man = json.load(open(mp))
    cw = sys.argv[2] if len(sys.argv) > 2 else list(ITEMS[it]["colorways"])[0]
    pj = ROOT / "3d" / "textures" / it / f"{cw}_placements.json"
    pls = json.load(open(pj)) if pj.exists() else []
    r = flat_svg(it, man, pls, ROOT / "technical-flats" / f"{it}_flat.svg")
    print(it, "flat ->", r["size_m"], len(r["legend"]), "placements")
