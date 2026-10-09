from engine import *

def circle_inter(p0, r0, p1, r1, prefer="low_out"):
    (x0, y0), (x1, y1) = p0, p1
    dx, dy = x1 - x0, y1 - y0; d = math.hypot(dx, dy)
    a = (r0*r0 - r1*r1 + d*d) / (2*d); h2 = r0*r0 - a*a
    h = math.sqrt(max(h2, 0))
    xm, ym = x0 + a*dx/d, y0 + a*dy/d
    c = [(xm + h*dy/d, ym - h*dx/d), (xm - h*dy/d, ym + h*dx/d)]
    return max(c, key=lambda p: p[0] + p[1])   # lower / outward

def neck_d(half, depth, y0, rev=False):
    a = f"M{f(CX-half)} {f(y0)} C {f(CX-half+2)} {f(y0+depth*.78)} {f(CX-half*.52)} {f(y0+depth)} {f(CX)} {f(y0+depth)} " \
        f"C {f(CX+half*.52)} {f(y0+depth)} {f(CX+half-2)} {f(y0+depth*.78)} {f(CX+half)} {f(y0)}"
    return a

STYLES = {
    #            hps  spx  spy  chest hem  hem_y len  sl_len ang  open under  neck_depth_front
    "regular":  dict(hps=92,  spx=218, spy=112, chest=252, hem=252, hemlen=700, e1=(150,118), e2=(126,58), nf=78, nb=22),
    "relaxed":  dict(hps=96,  spx=236, spy=122, chest=278, hem=278, hemlen=700, e1=(150,108), e2=(122,54), nf=80, nb=22),
    "oversize": dict(hps=102, spx=268, spy=146, chest=308, hem=308, hemlen=715, e1=(152,92), e2=(118,50), nf=86, nb=24),
    "boxy":     dict(hps=100, spx=256, spy=130, chest=300, hem=300, hemlen=640, e1=(150,100), e2=(120,52), nf=84, nb=24),
}
Y0 = 80

def tee(view="front", style="regular", fabric="jersey", sleeve_mult=1.0, hem_curve=6):
    s = STYLES[style]; y0 = Y0
    spx, spy, hps = s["spx"], s["spy"], s["hps"]
    SP = (CX + spx, spy)
    E1 = (SP[0] + s["e1"][0]*sleeve_mult, SP[1] + s["e1"][1]*(1 if sleeve_mult<=1 else sleeve_mult))
    arm_y = spy + 232
    A = (CX + s["chest"], arm_y)
    E2 = (A[0] + s["e2"][0]*sleeve_mult, A[1] + s["e2"][1]*sleeve_mult)
    hemy = y0 + s["hemlen"]
    HEM = (CX + s["hem"], hemy)
    # torso right-side commands
    arm_c1 = (SP[0] - 6, spy + 70); arm_c2 = (A[0] - 22, arm_y - 70)
    rc = [("M", CX + hps, y0), ("L", SP[0], SP[1]), ("C", arm_c1[0], arm_c1[1], arm_c2[0], arm_c2[1], A[0], A[1]),
          ("L", HEM[0], HEM[1]), ("Q", CX + s["hem"]/2, hemy + hem_curve*1.2, CX, hemy + hem_curve)]
    nd = s["nf"] if view == "front" else s["nb"]
    left = mirror_path_cmds(rc)
    d_torso = cmds_to_d(rc) + " " + cmds_to_d(left)
    d_torso += f" C {f(CX-hps+2)} {f(y0+nd*.78)} {f(CX-hps*.52)} {f(y0+nd)} {f(CX)} {f(y0+nd)} C {f(CX+hps*.52)} {f(y0+nd)} {f(CX+hps-2)} {f(y0+nd*.78)} {f(CX+hps)} {f(y0)} Z"
    # sleeves
    def sleeve_d(sign):
        X = (lambda x: x) if sign > 0 else mir
        return (f"M{f(X(SP[0]))} {f(SP[1])} L{f(X(E1[0]))} {f(E1[1])} L{f(X(E2[0]))} {f(E2[1])} L{f(X(A[0]))} {f(A[1])} "
                f"C {f(X(arm_c2[0]))} {f(arm_c2[1])} {f(X(arm_c1[0]))} {f(arm_c1[1])} {f(X(SP[0]))} {f(SP[1])} Z")
    ax = unit = None
    ux, uy = (E1[0]-SP[0]), (E1[1]-SP[1]); L = math.hypot(ux, uy); ux, uy = ux/L, uy/L
    sl_in = 20   # sleeve hem fold depth px
    H1 = (E1[0]-ux*sl_in, E1[1]-uy*sl_in); H2 = (E2[0]-ux*sl_in, E2[1]-uy*sl_in)
    def hemstitch(sign):
        X = (lambda x: x) if sign > 0 else mir
        return f"M{f(X(H1[0]))} {f(H1[1])} L{f(X(H2[0]))} {f(H2[1])}"
    torso_seams = []
    # armhole seams (both sides), side seams, hem stitch
    torso_seams.append((f"M{f(SP[0])} {f(SP[1])} C {f(arm_c1[0])} {f(arm_c1[1])} {f(arm_c2[0])} {f(arm_c2[1])} {f(A[0])} {f(A[1])}", "seam"))
    torso_seams.append((f"M{f(mir(SP[0]))} {f(SP[1])} C {f(mir(arm_c1[0]))} {f(arm_c1[1])} {f(mir(arm_c2[0]))} {f(arm_c2[1])} {f(mir(A[0]))} {f(A[1])}", "seam"))
    torso_seams.append((f"M{f(A[0]-2)} {f(A[1])} L{f(HEM[0]-2)} {f(HEM[1])}", "seam"))
    torso_seams.append((f"M{f(mir(A[0])+2)} {f(A[1])} L{f(mir(HEM[0])+2)} {f(HEM[1])}", "seam"))
    hy = hemy - 24
    torso_seams.append((f"M{f(CX-s['hem']+2)} {f(hy)} Q {f(CX)} {f(hy+hem_curve*2)} {f(CX+s['hem']-2)} {f(hy)}", "stitch"))
    # folds : soft vertical drape + armpit pull
    folds = [(f"M{f(CX-s['chest']*.78)} {f(arm_y+10)} Q {f(CX-s['chest']*.55)} {f(arm_y+260)} {f(CX-s['chest']*.7)} {f(hemy-40)}", .8),
             (f"M{f(CX+s['chest']*.72)} {f(arm_y+20)} Q {f(CX+s['chest']*.52)} {f(arm_y+250)} {f(CX+s['chest']*.66)} {f(hemy-40)}", .7)]
    parts = []
    # inner back (visible through neck hole) for front view
    if view == "front":
        back_d = (f"M{f(CX-hps)} {f(y0)} C {f(CX-hps*.5)} {f(y0+26)} {f(CX+hps*.5)} {f(y0+26)} {f(CX+hps)} {f(y0)} "
                  f"C {f(CX+hps-2)} {f(y0+nd*.78)} {f(CX+hps*.52)} {f(y0+nd)} {f(CX)} {f(y0+nd)} C {f(CX-hps*.52)} {f(y0+nd)} {f(CX-hps+2)} {f(y0+nd*.78)} {f(CX-hps)} {f(y0)} Z")
        parts.append(part("inner", back_d, "body_in", fabric, "none", z=-1, edge=.7))
    parts.append(part("torso", d_torso, "body", fabric, "tube", folds=folds, seams=torso_seams, z=0))
    for sign, nm in ((1, "sleeveR"), (-1, "sleeveL")):
        sd = sleeve_d(sign)
        parts.append(part(nm, sd, "body", fabric, "tube", ang=(35 if sign > 0 else 145), seams=[(hemstitch(sign), "stitch")],
                          folds=[(f"M{f((SP[0]+E2[0])/2 if sign>0 else mir((SP[0]+E2[0])/2))} {f(SP[1]+40)} L{f((E1[0]+A[0])/2 if sign>0 else mir((E1[0]+A[0])/2))} {f((E1[1]+A[1])/2)}", .7)], z=1))
    # collar rib
    cw = 22
    parts.append(part("collar", neck_d(hps, nd, y0), "rib", "knit", "none", kind="stroke", sw=cw, z=3, rib=None, edge=.35,
                      seams=[(neck_d(hps+7, nd+7, y0), "stitch"), (neck_d(hps-7, nd-7, y0), "stitch")]))
    geo = dict(style=s, y0=y0, hemy=hemy, arm_y=arm_y, SP=SP, E1=E1, E2=E2, A=A, hps=hps, nd=nd, chest=s["chest"],
               sleeve_hem_mid=((E1[0]+E2[0])/2, (E1[1]+E2[1])/2), neck_bottom=y0+nd, view=view)
    return parts, geo

def y_hps(cm): return Y0 + cm * PXCM

if __name__ == "__main__":
    cols = dict(body=PAL["tyr"], rib=PAL["tyr_d"], body_in=PAL["tyr_d"])
    sheet = ""
    for i, (st, fab) in enumerate([("regular", "jersey"), ("oversize", "jersey"), ("boxy", "jersey")]):
        parts, geo = tee("front", st, fab)
        m = mock(parts, cols, backdrop=None)
        sheet += f'<g transform="translate({i*1000} 0)">{m}</g>'
    s = svg(3000, 1000, sheet.replace('<svg ', '<svg ').replace("</svg>", ""), bg=PAL["chaux"])
    # simple: render each separately
    for i, st in enumerate(["regular", "oversize", "boxy"]):
        parts, geo = tee("front", st)
        write(f"/tmp/tee_{st}.svg", mock(parts, cols))
        render(f"/tmp/tee_{st}.svg", png=f"/tmp/tee_{st}.png", scale=0.6)
    parts, geo = tee("back", "regular")
    write("/tmp/tee_back.svg", mock(parts, cols)); render("/tmp/tee_back.svg", png="/tmp/tee_back.png", scale=0.6)
    from PIL import Image
    ims = [Image.open(f"/tmp/tee_{n}.png") for n in ("regular", "oversize", "boxy", "back")]
    W = sum(i.width for i in ims); H = ims[0].height
    sh = Image.new("RGB", (W, H)); x = 0
    for im in ims: sh.paste(im.convert("RGB"), (x, 0)); x += im.width
    sh.save("/tmp/tees.png"); print(sh.size)
