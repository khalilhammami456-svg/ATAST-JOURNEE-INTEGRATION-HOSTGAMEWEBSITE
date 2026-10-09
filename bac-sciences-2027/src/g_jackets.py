from engine import *
from g_tee import circle_inter

def L(a, b, t): return (a[0] + (b[0]-a[0])*t, a[1] + (b[1]-a[1])*t)
def M(p): return (mir(p[0]), p[1])
def poly(*pts): return "M" + " L".join(f"{f(x)} {f(y)}" for x, y in pts) + " Z"
def pl(*pts): return "M" + " L".join(f"{f(x)} {f(y)}" for x, y in pts)

def snaps(ys, x=CX, r=9, col="#cfc8b6"):
    out = ""
    for y in ys:
        out += (f'<circle cx="{x}" cy="{y}" r="{r+1.5}" fill="#000" fill-opacity=".35" transform="translate(1.5 2.5)"/>'
                f'<circle cx="{x}" cy="{y}" r="{r}" fill="{col}"/><circle cx="{x}" cy="{y}" r="{r*.62}" fill="none" stroke="#000" stroke-opacity=".28" stroke-width="1.3"/>'
                f'<circle cx="{x-r*.28}" cy="{y-r*.3}" r="{r*.22}" fill="#fff" fill-opacity=".7"/>')
    return out

# =================================================================================== VARSITY
def varsity(view="front"):
    y_sh = 128; SP = (CX + 246, y_sh); A = (CX + 300, 392)
    E1 = (CX + 424, 712); E2 = (CX + 320, 716)
    t = .885
    E1c, E2c = L(SP, E1, t), L(A, E2, t)
    hem_top, hem_bot = 648, 742
    torso_r = [("M", CX + 104, 98), ("L", SP[0], SP[1]), ("C", SP[0] - 8, SP[1] + 80, A[0] - 26, A[1] - 90, A[0], A[1]),
               ("L", CX + 292, hem_top), ("L", CX, hem_top)]
    left = mirror_path_cmds(torso_r)
    nd = 162 if view == "front" else 70
    d_t = cmds_to_d(torso_r) + " " + cmds_to_d(left)
    d_t += f" L{f(CX-104)} 98 " + (f"L{f(CX)} {nd} " if view == "front" else f"C {f(CX-60)} {nd+20} {f(CX+60)} {nd+20} {f(CX+104)} 98 ") + "Z"
    parts = []
    # lining visible through opening
    parts.append(part("lining", f"M{f(CX-90)} 96 L{f(CX+90)} 96 L{f(CX+6)} {nd} L{f(CX-6)} {nd} Z", "lining", "satin", "none", z=-1, edge=.6))
    # body (wool melton)
    seams = []
    folds = [(f"M{f(CX-190)} 420 Q {f(CX-150)} 540 {f(CX-176)} 630", .8), (f"M{f(CX+170)} 410 Q {f(CX+140)} 520 {f(CX+176)} 620", .7)]
    if view == "front":
        seams += [(f"M{f(CX)} {nd} V{hem_top}", "seam"), (f"M{f(CX-5)} {nd} V{hem_top}", "stitch"), (f"M{f(CX+5)} {nd} V{hem_top}", "stitch")]
        # welt pockets (slanted)
        for s in (1, -1):
            p1 = (CX + s*168, 470); p2 = (CX + s*200, 592)
            seams += [(pl(p1, p2), "dark"), (pl((p1[0]+s*-4, p1[1]-8), (p2[0]+s*-4, p2[1]+8)), "stitch")]
    else:
        seams += [(f"M{f(CX)} 100 V{hem_top}", "seam"),
                  (f"M{f(CX-246)} 138 C {f(CX-120)} 200 {f(CX+120)} 200 {f(CX+246)} 138", "seam")]
    seams += [(f"M{f(A[0]-4)} {A[1]} L{f(CX+292-4)} {hem_top}", "seam"), (f"M{f(mir(A[0])+4)} {A[1]} L{f(mir(CX+292)+4)} {hem_top}", "seam")]
    parts.append(part("torso", d_t, "body", "wool", "tube", folds=folds, seams=seams, z=0, gloss=0.0))
    # hem rib
    hem_d = poly((CX + 292, hem_top), (CX + 276, hem_bot), (CX - 276, hem_bot), (CX - 292, hem_top))
    stripe_y = [hem_top + 22, hem_top + 34]
    hs = [(f"M{f(CX-290+ (y-hem_top)*.17)} {y} L{f(CX+290-(y-hem_top)*.17)} {y}", "dark") for y in ()]
    parts.append(part("hem", hem_d, "rib", "knit", "vert", rib="v", z=1, edge=.5))
    # sleeves (PU leather) + cuffs
    for s, nm in ((1, "R"), (-1, "L")):
        X = (lambda p: p) if s > 0 else M
        sp, a_, e1c, e2c, e1, e2 = map(X, (SP, A, E1c, E2c, E1, E2))
        d = (f"M{f(sp[0])} {f(sp[1])} L{f(e1c[0])} {f(e1c[1])} L{f(e2c[0])} {f(e2c[1])} L{f(a_[0])} {f(a_[1])} "
             f"C {f(X((A[0]-26, 0))[0])} {f(A[1]-90)} {f(X((SP[0]-8, 0))[0])} {f(SP[1]+80)} {f(sp[0])} {f(sp[1])} Z")
        mid = L(L(SP, E1c, .5), L(A, E2c, .5), .5)
        ang = 12 if s > 0 else 168
        parts.append(part("sleeve" + nm, d, "sleeve", "leather", "tube", ang=ang, z=1, gloss=.20,
                          folds=[(pl(X(L(SP, E1c, .35)), X(L(A, E2c, .5))), .9), (pl(X(L(SP, E1c, .72)), X(L(A, E2c, .85))), .7)],
                          seams=[(pl(X(L(SP, E1c, .5)), X(L(SP, E1c, .5))), "dark")]))
        cd = poly(e1c, e1, e2, e2c)
        parts.append(part("cuff" + nm, cd, "rib", "knit", "vert", rib="v", z=2, edge=.55))
    # collar (rib): outer trapezoid and inner opening
    if view == "front":
        outer = (f"M{f(CX-108)} 120 C {f(CX-112)} 66 {f(CX-72)} 36 {f(CX)} 36 C {f(CX+72)} 36 {f(CX+112)} 66 {f(CX+108)} 120 L{f(CX+8)} {nd+8} L{f(CX-8)} {nd+8} Z")
        parts.append(part("collar", outer, "rib", "knit", "vert", rib="v", z=3, edge=.5,
                          seams=[(f"M{f(CX-100)} 112 C {f(CX-102)} 70 {f(CX-68)} 46 {f(CX)} 46 C {f(CX+68)} 46 {f(CX+102)} 70 {f(CX+100)} 112", "stitch")]))
        inner = (f"M{f(CX-84)} 110 C {f(CX-86)} 80 {f(CX-54)} 62 {f(CX)} 62 C {f(CX+54)} 62 {f(CX+86)} 80 {f(CX+84)} 110 L{f(CX+4)} {nd-8} L{f(CX-4)} {nd-8} Z")
        parts.append(part("collar_in", inner, "lining", "satin", "none", z=4, edge=.8))
    else:
        outer = f"M{f(CX-110)} 112 C {f(CX-112)} 64 {f(CX-70)} 36 {f(CX)} 36 C {f(CX+70)} 36 {f(CX+112)} 64 {f(CX+110)} 112 C {f(CX+60)} {nd+22} {f(CX-60)} {nd+22} {f(CX-110)} 112 Z"
        parts.append(part("collar", outer, "rib", "knit", "vert", rib="v", z=3, edge=.5))
    geo = dict(SP=SP, A=A, E1=E1, E2=E2, E1c=E1c, E2c=E2c, hem_top=hem_top, hem_bot=hem_bot, nd=nd)
    return parts, geo

def sleeve_axis(geo, side=1):
    """centre point and rotation (deg) of a sleeve for placing sleeve art. side=+1 viewer's right."""
    SP, A, E1c, E2c = geo["SP"], geo["A"], geo["E1c"], geo["E2c"]
    top = L(SP, A, .5); bot = L(E1c, E2c, .5)
    ang = math.degrees(math.atan2(bot[1]-top[1], bot[0]-top[0]))
    return top, bot, ang

# =================================================================================== COACH
def coach(view="front"):
    y_sh = 134; SP = (CX + 258, y_sh); A = (CX + 304, 388)
    E1 = (CX + 414, 706); E2 = (CX + 332, 712)
    t = .90
    E1c, E2c = L(SP, E1, t), L(A, E2, t)
    hem_y = 756
    rc = [("M", CX + 104, 98), ("L", SP[0], SP[1]), ("C", SP[0] - 8, SP[1] + 80, A[0] - 26, A[1] - 90, A[0], A[1]),
          ("L", CX + 306, hem_y), ("Q", CX + 150, hem_y + 6, CX, hem_y + 4)]
    nd = 150 if view == "front" else 78
    left = mirror_path_cmds(rc)
    d_t = cmds_to_d(rc) + " " + cmds_to_d(left) + f" L{f(CX-104)} 98 " + (f"L{f(CX)} {nd} L{f(CX+104)} 98 Z" if view == "front" else f"C {f(CX-60)} {nd+18} {f(CX+60)} {nd+18} {f(CX+104)} 98 Z")
    parts = []
    parts.append(part("lining", f"M{f(CX-96)} 96 L{f(CX+96)} 96 L{f(CX)} {nd} Z", "lining", "satin", "none", z=-1, edge=.7))
    seams = [(f"M{f(CX-300)} {hem_y-34} Q {f(CX)} {hem_y-28} {f(CX+300)} {hem_y-34}", "stitch")]
    folds = [(f"M{f(CX-200)} 400 Q {f(CX-150)} 560 {f(CX-190)} 720", .9), (f"M{f(CX+190)} 410 Q {f(CX+150)} 560 {f(CX+176)} 700", .7),
             (f"M{f(CX-60)} 470 Q {f(CX-30)} 580 {f(CX-70)} 700", .5)]
    if view == "front":
        seams += [(f"M{f(CX)} {nd} V{hem_y}", "seam"), (f"M{f(CX+9)} {nd+6} V{hem_y-3}", "stitch")]
        for s in (1, -1):   # slanted side-entry pockets with flap-less welt
            p1 = (CX + s*196, 470); p2 = (CX + s*218, 585)
            seams += [(pl(p1, p2), "dark"), (pl((p1[0]-s*7, p1[1]-4), (p2[0]-s*7, p2[1]+6)), "stitch")]
    else:
        seams += [(f"M{f(CX-258)} 142 C {f(CX-120)} 196 {f(CX+120)} 196 {f(CX+258)} 142", "seam"), (f"M{f(CX-258)} 152 C {f(CX-120)} 206 {f(CX+120)} 206 {f(CX+258)} 152", "stitch")]
    seams += [(f"M{f(A[0]-4)} {A[1]} L{f(CX+306-4)} {hem_y}", "seam"), (f"M{f(mir(A[0])+4)} {A[1]} L{f(mir(CX+306)+4)} {hem_y}", "seam")]
    parts.append(part("torso", d_t, "body", "nylon", "tube", folds=folds, seams=seams, gloss=.18, z=0))
    for s, nm in ((1, "R"), (-1, "L")):
        X = (lambda p: p) if s > 0 else M
        sp, a_, e1c, e2c, e1, e2 = map(X, (SP, A, E1c, E2c, E1, E2))
        d = (f"M{f(sp[0])} {f(sp[1])} L{f(e1c[0])} {f(e1c[1])} L{f(e2c[0])} {f(e2c[1])} L{f(a_[0])} {f(a_[1])} "
             f"C {f(X((A[0]-26, 0))[0])} {f(A[1]-90)} {f(X((SP[0]-8, 0))[0])} {f(SP[1]+80)} {f(sp[0])} {f(sp[1])} Z")
        parts.append(part("sleeve" + nm, d, "body", "nylon", "tube", ang=(12 if s > 0 else 168), gloss=.18, z=1,
                          folds=[(pl(X(L(SP, E1c, .3)), X(L(A, E2c, .45))), .9), (pl(X(L(SP, E1c, .7)), X(L(A, E2c, .85))), .8)]))
        parts.append(part("cuff" + nm, poly(e1c, e1, e2, e2c), "rib", "knit", "vert", rib="v", z=2, edge=.5))
    # flat collar
    if view == "front":
        back = f"M{f(CX-96)} 98 C {f(CX-84)} 50 {f(CX+84)} 50 {f(CX+96)} 98 L{f(CX+58)} 108 C {f(CX+40)} 86 {f(CX-40)} 86 {f(CX-58)} 108 Z"
        parts.append(part("collar_back", back, "body", "nylon", "none", z=3, edge=.6, gloss=.1))
        for s, nm in ((1, "R"), (-1, "L")):
            X = (lambda p: p) if s > 0 else M
            pts = [X(p) for p in [(CX + 4, nd + 24), (CX + 126, 84), (CX + 98, 44), (CX + 58, 92)]]
            d = (f"M{f(pts[0][0])} {f(pts[0][1])} L{f(pts[1][0])} {f(pts[1][1])} L{f(pts[2][0])} {f(pts[2][1])} L{f(pts[3][0])} {f(pts[3][1])} Z")
            parts.append(part("collar" + nm, d, "body", "nylon", "diag", z=4, edge=.55, gloss=.2,
                              seams=[(pl(*[X(p) for p in [(CX + 12, nd + 12), (CX + 112, 82)]]), "stitch")]))
    else:
        band = f"M{f(CX-104)} 98 C {f(CX-90)} 40 {f(CX+90)} 40 {f(CX+104)} 98 C {f(CX+60)} {nd+10} {f(CX-60)} {nd+10} {f(CX-104)} 98 Z"
        parts.append(part("collar", band, "body", "nylon", "none", z=3, edge=.5, gloss=.12, seams=[(f"M{f(CX-96)} 96 C {f(CX-50)} {nd+4} {f(CX+50)} {nd+4} {f(CX+96)} 96", "stitch")]))
    geo = dict(SP=SP, A=A, E1=E1, E2=E2, E1c=E1c, E2c=E2c, hem_y=hem_y, nd=nd)
    return parts, geo
