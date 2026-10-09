from g_jackets import *

# =================================================================================== CHORE / LAB JACKET
def chore(view="front"):
    parts, geo = coach(view)
    out = []
    for p in parts:
        q = dict(p)
        if p["id"].startswith("cuff"): q.update(color="body", tex="canvas", rib=None, shade="tube")
        elif q["tex"] == "nylon": q.update(tex="canvas", gloss=0.0)
        if q["id"] == "lining": q["color"] = "lining"
        out.append(q)
    parts = out
    hem_y = geo["hem_y"]
    nd = geo["nd"]
    extra = []
    if view == "front":
        # patch pockets: chest (wearer's left = viewer's right) + two lower
        def pocket(id_, x0, y0, w, h, flap=0):
            d = f"M{f(x0)} {f(y0)} L{f(x0+w)} {f(y0)} L{f(x0+w)} {f(y0+h)} L{f(x0)} {f(y0+h)} Z"
            seams = [(f"M{f(x0+5)} {f(y0+5)} L{f(x0+w-5)} {f(y0+5)} L{f(x0+w-5)} {f(y0+h-5)} L{f(x0+5)} {f(y0+h-5)} Z", "stitch")]
            return part(id_, d, "body", "canvas", "none", z=6, edge=.4, seams=seams)
        extra.append(pocket("pk_chest", CX + 82, 262, 128, 150))
        extra.append(pocket("pk_lowR", CX + 120, 520, 168, 190))
        extra.append(pocket("pk_lowL", CX - 288, 520, 168, 190))
        # pen slot on chest pocket
        extra.append(part("pen_slot", f"M{f(CX+170)} 262 L{f(CX+170)} 326", "body", "none", "none", kind="stroke", sw=2.2, z=7, edge=0))
        # buttons
        # (drawn as art 'over')
    else:
        # back box pleat + yoke
        extra.append(part("pleat", f"M{f(CX-34)} 200 V{hem_y-40} M{f(CX+34)} 200 V{hem_y-40}", "body", "none", "none", kind="stroke", sw=1.6, z=6, edge=0))
    parts = parts + extra
    geo["buttons"] = [200, 290, 380, 470, 560, 650, 735] if view == "front" else []
    return parts, geo

def buttons(ys, x=CX, r=11, col="#2b2030", ring=True):
    out = ""
    for y in ys:
        out += (f'<circle cx="{x}" cy="{y}" r="{r+1.5}" fill="#000" fill-opacity=".3" transform="translate(1.5 2.5)"/>'
                f'<circle cx="{x}" cy="{y}" r="{r}" fill="{col}"/><circle cx="{x}" cy="{y}" r="{r*.64}" fill="none" stroke="#fff" stroke-opacity=".22" stroke-width="1.4"/>'
                f'<circle cx="{x-3}" cy="{y-3}" r="1.6" fill="#fff" fill-opacity=".55"/><circle cx="{x+3}" cy="{y+3}" r="1.6" fill="#fff" fill-opacity=".55"/>')
    return out

# =================================================================================== KNIT VEST (collegiate)
def vest_knit(view="front"):
    N = (CX + 84, 96); S = (CX + 158, 112); A = (CX + 252, 336)
    hem_top, hem_bot = 690, 762
    arm_c1 = (CX + 176, 190); arm_c2 = (CX + 236, 250)
    rc = [("M", CX + 84, 96), ("L", S[0], S[1]), ("C", arm_c1[0], arm_c1[1], arm_c2[0], arm_c2[1], A[0], A[1]),
          ("L", CX + 248, hem_top), ("L", CX, hem_top)]
    left = mirror_path_cmds(rc)
    vd = 304 if view == "front" else 64
    d = cmds_to_d(rc) + " " + cmds_to_d(left)
    if view == "front":
        d += f" L{f(CX-84)} 96 L{f(CX)} {vd} L{f(CX+84)} 96 Z"
    else:
        d += f" L{f(CX-84)} 96 C {f(CX-60)} {vd+16} {f(CX+60)} {vd+16} {f(CX+84)} 96 Z"
    parts = []
    if view == "front":
        parts.append(part("inner", f"M{f(CX-84)} 96 C {f(CX-50)} 56 {f(CX+50)} 56 {f(CX+84)} 96 L{f(CX)} {vd} Z", "body_in", "knit", "none", z=-1, edge=.8))
    parts.append(part("torso", d, "body", "knit", "tube", rib="knit", z=0, edge=.35,
                      folds=[(f"M{f(CX-170)} 360 Q {f(CX-150)} 540 {f(CX-176)} 680", .6)],
                      seams=[(f"M{f(CX-250+2)} {A[1]} L{f(CX-248+2)} {hem_top}", "seam"), (f"M{f(CX+250-2)} {A[1]} L{f(CX+248-2)} {hem_top}", "seam")]))
    parts.append(part("hem", poly((CX + 248, hem_top), (CX + 244, hem_bot), (CX - 244, hem_bot), (CX - 248, hem_top)), "rib", "knit", "vert", rib="v", z=1, edge=.5))
    # trims: neck band(s) and armhole bands
    if view == "front":
        v1 = f"M{f(CX-84)} 96 L{f(CX)} {vd} L{f(CX+84)} 96"
        parts.append(part("neck_band", v1, "rib", "knit", "none", kind="stroke", sw=24, z=3, rib=None, edge=.5))
        v2 = f"M{f(CX-98)} 110 L{f(CX)} {vd+34} L{f(CX+98)} 110"
        parts.append(part("neck_stripe1", v2, "stripe1", "none", "none", kind="stroke", sw=7, z=3, edge=0))
        v3 = f"M{f(CX-108)} 124 L{f(CX)} {vd+58} L{f(CX+108)} 124"
        parts.append(part("neck_stripe2", v3, "stripe2", "none", "none", kind="stroke", sw=7, z=3, edge=0))
    else:
        nb = f"M{f(CX-84)} 96 C {f(CX-60)} {vd+16} {f(CX+60)} {vd+16} {f(CX+84)} 96"
        parts.append(part("neck_band", nb, "rib", "knit", "none", kind="stroke", sw=24, z=3, edge=.5))
        parts.append(part("neck_stripe1", f"M{f(CX-96)} 108 C {f(CX-70)} {vd+36} {f(CX+70)} {vd+36} {f(CX+96)} 108", "stripe1", "none", "none", kind="stroke", sw=7, z=3, edge=0))
    for s in (1, -1):
        X = (lambda p: p) if s > 0 else M
        ad = f"M{f(X(S)[0])} {f(S[1])} C {f(X(arm_c1)[0])} {f(arm_c1[1])} {f(X(arm_c2)[0])} {f(arm_c2[1])} {f(X(A)[0])} {f(A[1])}"
        parts.append(part("arm_band" + ("R" if s > 0 else "L"), ad, "rib", "knit", "none", kind="stroke", sw=22, z=3, edge=.5))
        ad2 = f"M{f(X((S[0]-10, 0))[0])} {f(S[1]+14)} C {f(X((arm_c1[0]-12, 0))[0])} {f(arm_c1[1]+10)} {f(X((arm_c2[0]-18, 0))[0])} {f(arm_c2[1]+6)} {f(X((A[0]-20, 0))[0])} {f(A[1]+4)}"
        parts.append(part("arm_stripe" + ("R" if s > 0 else "L"), ad2, "stripe1", "none", "none", kind="stroke", sw=6, z=3, edge=0))
    geo = dict(A=A, S=S, vd=vd, hem_top=hem_top, hem_bot=hem_bot)
    return parts, geo

# =================================================================================== QUILTED UTILITY VEST
def vest_quilt(view="front"):
    N = (CX + 92, 74); S = (CX + 178, 120); A = (CX + 248, 360); hem = 745
    rc = [("M", CX + 92, 74), ("L", S[0], S[1]), ("C", S[0] + 24, S[1] + 70, A[0] + 8, A[1] - 120, A[0], A[1]), ("L", CX + 244, hem), ("L", CX, hem + 4)]
    left = mirror_path_cmds(rc)
    d = cmds_to_d(rc) + " " + cmds_to_d(left) + " Z"
    parts = []
    # puffy quilting channels: strips with own shading
    ys = [150, 238, 326, 414, 502, 590, 678, hem + 4]
    parts.append(part("base", d, "body", "nylon", "tube", z=0, gloss=.12, edge=.45))
    def x_half(y):
        if y <= S[1]: return 178
        if y < A[1]: 
            t = (y - S[1]) / (A[1] - S[1]); return 178 + (A[0] - CX - 178) * (t ** .55)
        return 246
    for i in range(len(ys) - 1):
        y0, y1 = ys[i], ys[i + 1]
        xh0, xh1 = x_half(y0), x_half(y1)
        strip = poly((CX - xh0, y0), (CX + xh0, y0), (CX + xh1, y1), (CX - xh1, y1))
        parts.append(part(f"q{i}", strip, "body", "nylon", "vert", z=1, gloss=.28, edge=.5,
                          seams=[(pl((CX - xh0, y0), (CX + xh0, y0)), "seam")]))
    # arm bands (binding)
    for s in (1, -1):
        X = (lambda p: p) if s > 0 else M
        ad = f"M{f(X(S)[0])} {f(S[1])} C {f(X((S[0]+24,0))[0])} {f(S[1]+70)} {f(X((A[0]+8,0))[0])} {f(A[1]-120)} {f(X(A)[0])} {f(A[1])}"
        parts.append(part("bind" + ("R" if s > 0 else "L"), ad, "bind", "none", "none", kind="stroke", sw=12, z=3, edge=.3))
    # stand collar
    if view == "front":
        col = f"M{f(CX-96)} 76 C {f(CX-96)} 40 {f(CX-60)} 22 {f(CX)} 22 C {f(CX+60)} 22 {f(CX+96)} 40 {f(CX+96)} 76 L{f(CX+96)} 120 L{f(CX-96)} 120 Z"
        parts.append(part("collar", col, "body", "nylon", "tube", z=4, gloss=.2, edge=.55, seams=[(f"M{f(CX)} 22 V122", "seam")]))
        parts.append(part("collar_in", f"M{f(CX-82)} 78 C {f(CX-80)} 56 {f(CX-50)} 44 {f(CX)} 44 C {f(CX+50)} 44 {f(CX+80)} 56 {f(CX+82)} 78 Z", "lining", "satin", "none", z=3, edge=.7))
        # centre zip + pockets
        parts.append(part("zip", f"M{f(CX)} 120 V{hem}", "zip", "none", "none", kind="stroke", sw=9, z=5, edge=0))
        for s in (1, -1):
            parts.append(part("pk_hand" + ("R" if s > 0 else "L"),
                              f"M{f(CX+s*180)} 470 L{f(CX+s*212)} 600", "zip", "none", "none", kind="stroke", sw=7, z=5, edge=0))
            parts.append(part("pk_chest" + ("R" if s > 0 else "L"),
                              f"M{f(CX+s*60)} 230 L{f(CX+s*150)} 228", "zip", "none", "none", kind="stroke", sw=7, z=5, edge=0))
    else:
        col = f"M{f(CX-96)} 76 C {f(CX-96)} 40 {f(CX-60)} 26 {f(CX)} 26 C {f(CX+60)} 26 {f(CX+96)} 40 {f(CX+96)} 76 C {f(CX+60)} 110 {f(CX-60)} 110 {f(CX-96)} 76 Z"
        parts.append(part("collar", col, "body", "nylon", "tube", z=4, gloss=.2, edge=.55))
    geo = dict(S=S, A=A, hem=hem, ys=ys)
    return parts, geo

# =================================================================================== HOODIE
def hoodie(view="front"):
    SP = (CX + 262, 176); A = (CX + 300, 420); hem_top, hem_bot = 700, 784
    E1 = (CX + 418, 700); E2 = (CX + 332, 712); t = .90
    E1c, E2c = L(SP, E1, t), L(A, E2, t)
    parts = []
    # hood behind
    hood = (f"M{f(CX-176)} 190 C {f(CX-190)} 70 {f(CX-100)} 6 {f(CX)} 6 C {f(CX+100)} 6 {f(CX+190)} 70 {f(CX+176)} 190 Z")
    parts.append(part("hood", hood, "body", "fleece", "tube", z=-2, edge=.5, folds=[(f"M{f(CX-120)} 80 Q {f(CX)} 40 {f(CX+120)} 80", .5)]))
    rc = [("M", CX + 112, 150), ("L", SP[0], SP[1]), ("C", SP[0] - 6, SP[1] + 90, A[0] - 20, A[1] - 90, A[0], A[1]),
          ("L", CX + 292, hem_top), ("L", CX, hem_top)]
    left = mirror_path_cmds(rc)
    nd = 262 if view == "front" else 160
    d = cmds_to_d(rc) + " " + cmds_to_d(left) + f" L{f(CX-112)} 150 C {f(CX-70)} {nd} {f(CX+70)} {nd} {f(CX+112)} 150 Z"
    seams = [(f"M{f(A[0]-4)} {A[1]} L{f(CX+292-4)} {hem_top}", "seam"), (f"M{f(mir(A[0])+4)} {A[1]} L{f(mir(CX+292)+4)} {hem_top}", "seam")]
    folds = [(f"M{f(CX-190)} 440 Q {f(CX-150)} 570 {f(CX-176)} 690", .9), (f"M{f(CX+180)} 440 Q {f(CX+140)} 570 {f(CX+170)} 690", .8)]
    parts.append(part("torso", d, "body", "fleece", "tube", z=0, folds=folds, seams=seams))
    parts.append(part("hem", poly((CX + 292, hem_top), (CX + 280, hem_bot), (CX - 280, hem_bot), (CX - 292, hem_top)), "rib", "knit", "vert", rib="v", z=1, edge=.5))
    for s, nm in ((1, "R"), (-1, "L")):
        X = (lambda p: p) if s > 0 else M
        sp, a_, e1c, e2c, e1, e2 = map(X, (SP, A, E1c, E2c, E1, E2))
        dd = (f"M{f(sp[0])} {f(sp[1])} L{f(e1c[0])} {f(e1c[1])} L{f(e2c[0])} {f(e2c[1])} L{f(a_[0])} {f(a_[1])} "
              f"C {f(X((A[0]-20, 0))[0])} {f(A[1]-90)} {f(X((SP[0]-6, 0))[0])} {f(SP[1]+90)} {f(sp[0])} {f(sp[1])} Z")
        parts.append(part("sleeve" + nm, dd, "body", "fleece", "tube", ang=(12 if s > 0 else 168), z=1,
                          folds=[(pl(X(L(SP, E1c, .35)), X(L(A, E2c, .5))), .9), (pl(X(L(SP, E1c, .7)), X(L(A, E2c, .85))), .8)]))
        parts.append(part("cuff" + nm, poly(e1c, e1, e2, e2c), "rib", "knit", "vert", rib="v", z=2, edge=.5))
    if view == "front":
        # hood opening (lining) + hood rim
        op = f"M{f(CX-100)} 150 C {f(CX-96)} 60 {f(CX+96)} 60 {f(CX+100)} 150 C {f(CX+70)} {nd-6} {f(CX-70)} {nd-6} {f(CX-100)} 150 Z"
        parts.append(part("hood_in", op, "body_in", "fleece", "none", z=3, edge=.8))
        rim = f"M{f(CX-108)} 156 C {f(CX-108)} 56 {f(CX+108)} 56 {f(CX+108)} 156"
        parts.append(part("hood_rim", rim, "body", "fleece", "none", kind="stroke", sw=26, z=3, edge=.5))
        # kangaroo pocket
        pk = poly((CX - 196, 520), (CX + 196, 520), (CX + 226, 706), (CX - 226, 706))
        parts.append(part("pocket", pk, "body", "fleece", "vert", z=4, edge=.55,
                          seams=[(pl((CX - 190, 528), (CX + 190, 528)), "stitch"), (pl((CX - 196, 520), (CX - 226, 706)), "seam"), (pl((CX + 196, 520), (CX + 226, 706)), "seam")]))
        # drawcords
        for s in (1, -1):
            parts.append(part("cord" + ("R" if s > 0 else "L"), f"M{f(CX+s*38)} {nd-8} C {f(CX+s*44)} {nd+50} {f(CX+s*30)} {nd+90} {f(CX+s*40)} {nd+150}", "cord", "none", "none", kind="stroke", sw=7, z=5, edge=0))
            parts.append(part("tip" + ("R" if s > 0 else "L"), f"M{f(CX+s*40)} {nd+150} L{f(CX+s*40)} {nd+176}", "tip", "none", "none", kind="stroke", sw=10, z=5, edge=0))
    else:
        parts.append(part("hood_back", f"M{f(CX-108)} 156 C {f(CX-100)} 90 {f(CX-40)} 60 {f(CX)} 60 C {f(CX+40)} 60 {f(CX+100)} 90 {f(CX+108)} 156 C {f(CX+60)} {nd+20} {f(CX-60)} {nd+20} {f(CX-108)} 156 Z",
                          "body", "fleece", "tube", z=3, edge=.5, seams=[(f"M{f(CX)} 60 V{nd+14}", "seam")]))
    geo = dict(SP=SP, A=A, E1c=E1c, E2c=E2c, hem_top=hem_top, nd=nd)
    return parts, geo

# =================================================================================== CAP
def cap(view="front"):
    parts = []
    if view == "front":
        crown = (f"M{f(CX-206)} 500 C {f(CX-214)} 280 {f(CX-120)} 140 {f(CX)} 140 C {f(CX+120)} 140 {f(CX+214)} 280 {f(CX+206)} 500 "
                 f"C {f(CX+120)} 548 {f(CX-120)} 548 {f(CX-206)} 500 Z")
        panels = [(f"M{f(CX)} 140 V546", "seam"), (f"M{f(CX-84)} 150 C {f(CX-116)} 280 {f(CX-124)} 400 {f(CX-120)} 538", "seam"),
                  (f"M{f(CX+84)} 150 C {f(CX+116)} 280 {f(CX+124)} 400 {f(CX+120)} 538", "seam"),
                  (f"M{f(CX-90)} 152 C {f(CX-121)} 280 {f(CX-129)} 400 {f(CX-125)} 536", "stitch"),
                  (f"M{f(CX+90)} 152 C {f(CX+121)} 280 {f(CX+129)} 400 {f(CX+125)} 536", "stitch")]
        parts.append(part("crown", crown, "body", "twill", "tube", z=1, seams=panels, folds=[(f"M{f(CX-160)} 300 Q {f(CX-140)} 400 {f(CX-170)} 470", .5)]))
        brim = (f"M{f(CX-222)} 494 C {f(CX-300)} 596 {f(CX-176)} 676 {f(CX)} 676 C {f(CX+176)} 676 {f(CX+300)} 596 {f(CX+222)} 494 "
                f"C {f(CX+120)} 556 {f(CX-120)} 556 {f(CX-222)} 494 Z")
        under = (f"M{f(CX-300)} 596 C {f(CX-176)} 676 {f(CX+176)} 676 {f(CX+300)} 596 L{f(CX+300)} 616 C {f(CX+176)} 700 {f(CX-176)} 700 {f(CX-300)} 616 Z")
        rows = [(f"M{f(CX-262)} 566 C {f(CX-210)} {664-i*15} {f(CX+210)} {664-i*15} {f(CX+262)} 566", "stitch") for i in (0, 2, 4, 6)]
        parts.append(part("brim_u", under, "brim_u", "twill", "none", z=-1, edge=.6))
        parts.append(part("brim", brim, "brim", "twill", "vert", z=0, edge=.5, seams=rows, gloss=.10,
                          folds=[(f"M{f(CX-120)} 600 Q {f(CX)} 650 {f(CX+120)} 600", .5)]))
        parts.append(part("button", f"M{f(CX)} 142 L{f(CX)} 142", "body", "none", "none", kind="stroke", sw=24, z=2, edge=.4))
        for dx in (-34, 34):
            parts.append(part("eyelet%d" % dx, f"M{f(CX+dx)} 214 L{f(CX+dx)} 214", "eye", "none", "none", kind="stroke", sw=9, z=2, edge=0))
    else:
        crown = (f"M{f(CX-206)} 500 C {f(CX-214)} 280 {f(CX-120)} 140 {f(CX)} 140 C {f(CX+120)} 140 {f(CX+214)} 280 {f(CX+206)} 500 "
                 f"C {f(CX+120)} 512 {f(CX-120)} 512 {f(CX-206)} 500 Z")
        parts.append(part("crown", crown, "body", "twill", "tube", z=0, seams=[(f"M{f(CX)} 140 V510", "seam"), (f"M{f(CX-84)} 150 C {f(CX-116)} 280 {f(CX-124)} 400 {f(CX-120)} 506", "seam"), (f"M{f(CX+84)} 150 C {f(CX+116)} 280 {f(CX+124)} 400 {f(CX+120)} 506", "seam")]))
        parts.append(part("strap", f"M{f(CX-200)} 462 C {f(CX-100)} 486 {f(CX+100)} 486 {f(CX+200)} 462", "strap", "twill", "none", kind="stroke", sw=40, z=1, edge=.4,
                          seams=[(f"M{f(CX-200)} 450 C {f(CX-100)} 474 {f(CX+100)} 474 {f(CX+200)} 450", "stitch"), (f"M{f(CX-200)} 474 C {f(CX-100)} 498 {f(CX+100)} 498 {f(CX+200)} 474", "stitch")]))
        parts.append(part("slide", f"M{f(CX-30)} 476 L{f(CX+30)} 476", "metal", "none", "none", kind="stroke", sw=34, z=2, edge=.2))
        parts.append(part("button", f"M{f(CX)} 142 L{f(CX)} 142", "body", "none", "none", kind="stroke", sw=24, z=2, edge=.4))
    return parts, dict()

# =================================================================================== SCARVES (flat, long)
SC = 4.4   # px per cm for scarves (so a 170 cm scarf fits)
def scarf_rect(w_cm, l_cm, fringe_cm, cx=CX, top=60):
    w, l, fr = w_cm * SC, l_cm * SC, fringe_cm * SC
    x0 = cx - w / 2
    body = f"M{f(x0)} {f(top)} H{f(x0+w)} V{f(top+l)} H{f(x0)} Z"
    # fringe lines
    fr_d = ""
    n = int(w_cm * 1.0)
    for i in range(n + 1):
        x = x0 + w * (i + .5) / (n + 1)
        fr_d += f"M{f(x)} {f(top)} V{f(top-fr)} M{f(x)} {f(top+l)} V{f(top+l+fr)} "
    return body, fr_d, dict(x0=x0, w=w, l=l, top=top, fr=fr)
