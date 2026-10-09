"""All garment designs: geometry + artwork + colourways + spec data.  Registry: DESIGNS."""
from g_other import *
from art import *
from c_tees import TEES, CW as TCW, t1_art, t2_art, t3_art, t4_art

TYR, TYRD, CHX, ENC, CIT, SAB, ARG = PAL["tyr"], PAL["tyr_d"], PAL["chaux"], PAL["encre"], PAL["citron"], PAL["sable"], PAL["argile"]
ENC_BODY, ENC_RIB = "#1D1523", "#120C17"
DESIGNS = {}

def place_rot(frag, nw, nh, cx, cy, w_cm, rot, name=None, meta=None):
    k = w_cm * PXCM / nw
    if name: REGISTRY[name] = dict(frag=frag, nw=nw, nh=nh, w_cm=w_cm, h_cm=nh * k / PXCM, meta=meta or {})
    return f'<g transform="translate({cx:.1f} {cy:.1f}) rotate({rot:.2f}) scale({k:.4f}) translate({-nw/2:.1f} {-nh/2:.1f})">{frag}</g>'

# ============================================================================ J1 VARSITY
J1_CW = {
    "Pourpre / Chaux": dict(body=TYR, sleeve=CHX, rib=TYRD, lining="#2A0A26", ink=CHX, acc=CIT, letter=CHX, letter_b=CIT, stripe_a=CHX, stripe_b=CIT),
    "Encre / Pourpre": dict(body=ENC_BODY, sleeve=TYR, rib=ENC_RIB, lining="#2A0A26", ink=CHX, acc=CIT, letter=CIT, letter_b=CHX, stripe_a=CIT, stripe_b=CHX),
    "Sable / Pourpre": dict(body=SAB, sleeve=TYR, rib="#B7A57F", lining=TYR, ink=TYR, acc=TYR, letter=TYR, letter_b=CHX, stripe_a=TYR, stripe_b=CHX),
}
def rib_stripes(geo, c, collar=True):
    hs = geo["hem_top"]; E1c, E1, E2c, E2 = geo["E1c"], geo["E1"], geo["E2c"], geo["E2"]
    out = {"hem": f'<path d="M{CX-320} {hs+24} H{CX+320}" stroke="{c["stripe_a"]}" stroke-width="8"/><path d="M{CX-320} {hs+42} H{CX+320}" stroke="{c["stripe_b"]}" stroke-width="5"/>'}
    for nm, s in (("cuffR", 1), ("cuffL", -1)):
        X = (lambda p: p) if s > 0 else M
        p1a, p1b = X(L(E1c, E1, .34)), X(L(E2c, E2, .34)); p2a, p2b = X(L(E1c, E1, .56)), X(L(E2c, E2, .56))
        out[nm] = (f'<path d="M{f(p1a[0])} {f(p1a[1])} L{f(p1b[0])} {f(p1b[1])}" stroke="{c["stripe_a"]}" stroke-width="8"/>'
                   f'<path d="M{f(p2a[0])} {f(p2a[1])} L{f(p2b[0])} {f(p2b[1])}" stroke="{c["stripe_b"]}" stroke-width="5"/>')
    return out

def j1_art(view, cw):
    c = J1_CW[cw]; parts, geo = varsity(view)
    pr, emb, lift, over = {}, {}, {}, ""
    st = rib_stripes(geo, c)
    pr.update(st)
    # collar stripes
    coll = ""
    for d, col, w in ((24, c["stripe_a"], 7), (38, c["stripe_b"], 4)):
        coll += (f'<path d="M{CX-118} {118+d*.2} C {CX-122} {66+d} {CX-76} {32+d} {CX} {32+d} C {CX+76} {32+d} {CX+122} {66+d} {CX+118} {118+d*.2}" '
                 f'fill="none" stroke="{col}" stroke-width="{w}"/>')
    pr["collar"] = coll
    if view == "front":
        # chenille Λ letter, left chest (viewer's right)
        Cc, W = 150, 128
        lx, ly = CX + 135 - W / 2, 300 + Cc / 2
        let = (f'<g filter="url(#f_chenille)">'
               + lam(lx - 0, ly, Cc, W, 46, 24, c["letter_b"]).replace('fill="%s"' % c["letter_b"], f'fill="{c["letter_b"]}" stroke="{c["letter_b"]}" stroke-width="16" stroke-linejoin="round"')
               + lam(lx, ly, Cc, W, 46, 24, c["letter"]) + '</g>')
        lift["torso"] = let
        REGISTRY[f"HN27-J01_{cw}_chest_chenille_L"] = dict(frag=let, nw=W + 20, nh=Cc + 20, w_cm=(W + 20) / PXCM, h_cm=(Cc + 20) / PXCM, meta=dict(method="Chenille patch (felt backing) with embroidered merrow-style border"))
        n, nw, nh = numerals(60, c["acc"], 0, 60 * .74, tracking=40)
        emb["torso"] = place(n, nw, 60 * .74, CX - 135, 282, 6.0, name=f"HN27-J01_{cw}_chest_2027", meta=dict(method="Embroidery 1 colour"))[0]
        # sleeve patches
        top, bot, ang = sleeve_axis(geo, 1)
        sealfrag = seal(60, 60, 60, TYR if cw != "Sable / Pourpre" else TYR, CHX, c["acc"] if cw != "Sable / Pourpre" else CHX)
        pc = L(geo["SP"], geo["E1c"], .30); pc = (mir(pc[0]) + 10, pc[1])
        emb["sleeveL"] = place_rot(sealfrag, 120, 120, pc[0], pc[1], 8.0, 0, name=f"HN27-J01_{cw}_sleeve_seal", meta=dict(method="Embroidered/woven patch, merrow border"))
        mt, mw, mh = motto_line(c["acc"] if cw != "Sable / Pourpre" else CHX, 20)
        pc2 = L(geo["SP"], geo["E1c"], .50); pc2 = (pc2[0] - 6, pc2[1])
        emb["sleeveR"] = place_rot(mt, mw, mh, pc2[0], pc2[1], 22, math.degrees(math.atan2(geo["E1c"][1] - geo["SP"][1], geo["E1c"][0] - geo["SP"][0])), name=f"HN27-J01_{cw}_sleeve_motto", meta=dict(method="Embroidery 1 colour"))
        over = snaps([200, 288, 376, 464, 552, 636], col="#CFC8B6" if cw != "Sable / Pourpre" else TYRD)
    else:
        ink, acc = c["ink"], c["acc"]
        sur = surus(ink, acc)
        k = 280 / 440
        e = f'<g transform="translate({CX-220*k:.1f} {400-160*k:.1f}) scale({k:.4f})">{sur[sur.index("<g mask") - 0:] if False else sur}</g>'
        arc_top = T_arc("LYCÉE HANNIBAL · TÉBOURBA", "archivo", 25, CX, 424, 212, -90, ink, tracking=170, wght=800, wdth=112)
        arc_bot = T_arc("BAC SCIENCES · 2027", "archivo", 25, CX, 424, 212 + 18, 90, ink, tracking=170, inside=True, wght=800, wdth=112)
        back_art = e + arc_top + arc_bot
        emb["torso"] = back_art
        REGISTRY[f"HN27-J01_{cw}_back_surus"] = dict(frag=back_art, nw=1000, nh=1000, w_cm=100, h_cm=100, meta=dict(method="Embroidery / twill appliqué, 3 colours (ink, accent, tonal)", bbox="approx 46 x 44 cm incl. arc text"))
    return dict(print=pr, emb=emb, lift=lift, over=over)

# ============================================================================ J2 COACH
J2_CW = {
    "Citron": dict(body=CIT, rib="#B5CE22", lining=TYR, ink=TYR, acc=TYR, snap=TYR),
    "Pourpre": dict(body=TYR, rib=TYRD, lining=CIT, ink=CHX, acc=CIT, snap="#CFC8B6"),
    "Encre": dict(body=ENC_BODY, rib=ENC_RIB, lining=TYR, ink=CIT, acc=CHX, snap="#CFC8B6"),
}
def j2_art(view, cw):
    c = J2_CW[cw]; parts, geo = coach(view); pr, emb, over = {}, {}, ""
    ink = c["ink"]
    if view == "front":
        m, nw, nh = mono_art(ink, c["acc"] if cw != "Citron" else ENC, 100)
        emb["torso"] = place(m, nw, nh, CX + 140, 262, 7.0, name=f"HN27-J02_{cw}_chest_mono", meta=dict(method="Embroidery 2 colours"))[0]
        top, bot, ang = sleeve_axis(geo, 1)
        wm, w, cc = wordmark(40, ink, 0, 40 * .74, lam_fill=c["acc"] if cw == "Pourpre" else None)
        txt = wm + T("27", "archivo", 40, w + 22, 40 * .74, ink, wght=900, wdth=125)
        tw = w + 22 + text_w("27", "archivo", 40, wght=900, wdth=125)
        mid = L(geo["SP"], geo["E1c"], .50); mid = (mid[0] - 4, mid[1])
        pr["sleeveR"] = place_rot(txt, tw, 40 * .8, mid[0], mid[1], 20, math.degrees(math.atan2(geo["E1c"][1] - geo["SP"][1], geo["E1c"][0] - geo["SP"][0])), name=f"HN27-J02_{cw}_sleeve_wordmark", meta=dict(method="Screen print 1 colour"))
        over = snaps([196, 286, 376, 466, 556, 646, 736], col=c["snap"])
    else:
        # stacked statement type
        W = 1000
        l1 = justify("FRANCHIR", "archivo", 150, W, ink, 0, 150 * .72, wght=900, wdth=125)
        l2 = justify("L’INCONNUE", "archivo", 150, W, ink, 0, 150 * .72 + 150 * .98, wght=900, wdth=125)
        pk = peaks(0, 150 * .72 + 150 * 1.98 + 44, W, 70, 9, c["acc"] if cw != "Citron" else ink, sw=9)
        co = T(COORD + "  —  LYCÉE HANNIBAL · TÉBOURBA", "mono", 30, 0, 150 * .72 + 150 * 1.98 + 44 + 70 + 52, ink, wght=600)
        frag = l1 + l2 + pk + co
        pr["torso"] = place(frag, W, 150 * 3.5, CX, 208, 38.0, name=f"HN27-J02_{cw}_back_type", meta=dict(method="Screen print 1 colour (2 on Pourpre/Encre)"))[0]
        ar, aw, ah = motto_line(ink, 26, ar=True)
        pr["torso"] += place(ar, aw, ah, CX, 208 + 38 * 3.5 * 0.99 * 1.0 + 40, 9.0)[0] if False else ""
    return dict(print=pr, emb=emb, over=over)

# ============================================================================ J3 CHORE (LABO)
J3_CW = {
    "Sable": dict(body=SAB, rib=SAB, lining=TYR, ink=TYR, acc=TYR, btn=TYRD),
    "Encre": dict(body=ENC_BODY, rib=ENC_BODY, lining=TYR, ink=CHX, acc=CIT, btn="#CFC8B6"),
    "Pourpre": dict(body=TYR, rib=TYR, lining=CIT, ink=CHX, acc=CIT, btn="#CFC8B6"),
}
def j3_art(view, cw):
    c = J3_CW[cw]; parts, geo = chore(view); pr, emb, lift, over = {}, {}, {}, ""
    if view == "front":
        wm, w, cc = wordmark(40, c["ink"], 0, 40 * .74, lam_fill=c["acc"] if cw != "Sable" else None)
        emb["pk_chest"] = place(wm, w, 40 * .74, CX + 146, 290, 9.0, name=f"HN27-J03_{cw}_pocket_wordmark", meta=dict(method="Embroidery 1-2 colours"))[0]
        rl = tick_ruler(150, c["ink"], 12, 1.04)
        pr["pk_lowL"] = place(rl, 156, 26, CX - 204, 534, 15.0, name=f"HN27-J03_{cw}_pocket_ruler", meta=dict(method="Screen print 1 colour (or printed twill tape)"))[0]
        lab, lw, lh = label_tag(["HΛNNIBΛL", "PROMO 2027"], c["ink"], None, 11)
        emb["pk_lowR"] = place(lab, lw, lh, CX + 204, 536, 7.0, name=f"HN27-J03_{cw}_pocket_tag", meta=dict(method="Woven label sewn on pocket edge"))[0]
        over = buttons([200, 290, 380, 470, 560, 650, 735], col=c["btn"])
    else:
        lab, lw, lh = label_tag(["LABORATOIRE", "BAC SCIENCES", "PROMO 2027", "N° ___ / 120"], c["ink"], None, 12)
        lift["torso"] = place(lab, lw, lh, CX, 218, 10.0, name=f"HN27-J03_{cw}_back_label", meta=dict(method="Woven patch / numbered leather-look label"))[0]
        s, sw_, sh_ = surus_art(c["ink"], c["acc"], construction=True, cons_col=c["ink"])
        pr["torso"] = place(s, sw_, sh_, CX, 390, 24.0, name=f"HN27-J03_{cw}_back_surus", meta=dict(method="Screen print 1-2 colours (tonal on Sable)"))[0]
    return dict(print=pr, emb=emb, lift=lift, over=over)

# ============================================================================ V1 KNIT VEST
V1_CW = {
    "Pourpre": dict(body=TYR, body_in=TYRD, rib=TYRD, stripe1=CIT, stripe2=CHX, ink=CHX, acc=CIT),
    "Chaux": dict(body=CHX, body_in=PAL["chaux_d"], rib=PAL["chaux_d"], stripe1=TYR, stripe2=ARG, ink=TYR, acc=TYR),
    "Sable": dict(body=SAB, body_in="#B7A57F", rib="#B7A57F", stripe1=TYR, stripe2=CHX, ink=TYR, acc=TYR),
}
def v1_art(view, cw):
    c = V1_CW[cw]; parts, geo = vest_knit(view); pr, emb = {}, {}
    hs = geo["hem_top"]
    pr["hem"] = f'<path d="M{CX-300} {hs+24} H{CX+300}" stroke="{c["stripe1"]}" stroke-width="8"/><path d="M{CX-300} {hs+42} H{CX+300}" stroke="{c["stripe2"]}" stroke-width="5"/>'
    if view == "front":
        m, nw, nh = mono_art(c["ink"], c["acc"], 100)
        emb["torso"] = place(m, nw, nh, CX + 150, 360, 6.5, name=f"HN27-V01_{cw}_chest_mono", meta=dict(method="Embroidery 2 colours (or intarsia knit)"))[0]
    else:
        n, nw, nh = numerals(60, c["ink"], 0, 60 * .74, tracking=40)
        emb["torso"] = place(n, nw, 60 * .74, CX, 170, 5.5, name=f"HN27-V01_{cw}_back_2027", meta=dict(method="Embroidery 1 colour"))[0]
    return dict(print=pr, emb=emb)

# ============================================================================ V2 QUILTED UTILITY VEST
V2_CW = {
    "Encre": dict(body=ENC_BODY, lining=TYR, bind=CIT, zip="#8A8794", ink=CIT, acc=CHX),
    "Pourpre": dict(body=TYR, lining=CIT, bind=CHX, zip="#8A8794", ink=CHX, acc=CIT),
    "Sable": dict(body=SAB, lining=TYR, bind=TYR, zip="#8A8794", ink=TYR, acc=TYR),
}
def v2_art(view, cw):
    c = V2_CW[cw]; parts, geo = vest_quilt(view); pr, emb, lift = {}, {}, {}
    if view == "front":
        m, nw, nh = mono_art(c["ink"], c["acc"], 100)
        emb["q1"] = place(m, nw, nh, CX + 108, 262, 5.0, name=f"HN27-V02_{cw}_chest_mono", meta=dict(method="Embroidery 2 colours"))[0]
        lab = (f'<rect width="40" height="17" rx="1.5" fill="{CHX}"/>' + T("HΛNNIBΛL", "archivo", 4.2, 20, 8.2, TYR, "middle", tracking=60, wght=800, wdth=115)
               + T("2027", "archivo", 3.2, 20, 13.4, TYR, "middle", tracking=120, wght=700, wdth=110))
        lift["q5"] = place(lab, 40, 17, CX - 150, 620, 4.6, name=f"HN27-V02_{cw}_hem_label", meta=dict(method="Woven label, loop-sewn"))[0]
    else:
        t = T("FRANCHIR L’INCONNUE", "archivo", 40, 0, 40 * .72, c["ink"], tracking=240, wght=800, wdth=112)
        tw = text_w("FRANCHIR L’INCONNUE", "archivo", 40, 240, wght=800, wdth=112)
        for qi in range(2, 6):
            pass
        frag = place_rot(t, tw, 40, CX, 420, 40.0, -90, name=f"HN27-V02_{cw}_back_spine", meta=dict(method="Screen print / reflective-ink 1 colour"))
        for qi in range(0, 7): pr[f"q{qi}"] = frag
    return dict(print=pr, emb=emb, lift=lift)

# ============================================================================ H1 HOODIE
H1_CW = {
    "Pourpre": dict(body=TYR, body_in=TYRD, rib=TYRD, cord=CHX, tip="#9a9a9a", ink=CHX, acc=CIT, tone=PAL["tyr_l"]),
    "Chaux": dict(body=CHX, body_in=PAL["chaux_d"], rib=PAL["chaux_d"], cord=TYR, tip="#9a9a9a", ink=TYR, acc=TYR, tone=PAL["chaux_d"]),
    "Encre": dict(body=ENC_BODY, body_in=ENC_RIB, rib=ENC_RIB, cord=CIT, tip="#9a9a9a", ink=CHX, acc=CIT, tone="#2B2133"),
}
def h1_art(view, cw):
    c = H1_CW[cw]; parts, geo = hoodie(view); pr, emb, over = {}, {}, ""
    if view == "front":
        m, nw, nh = mono_art(c["ink"], c["acc"] if cw != "Chaux" else TYR, 100)
        emb["torso"] = place(m, nw, nh, CX + 140, 340, 7.0, name=f"HN27-H01_{cw}_chest_mono", meta=dict(method="Embroidery 2 colours"))[0]
        n, nw, nh = numerals(60, c["ink"], 0, 60 * .74, tracking=40)
        mid = L(geo["SP"], geo["E1c"], .52); mid = (mid[0] - 6, mid[1])
        pr["sleeveR"] = place_rot(n, nw, 60 * .74, mid[0], mid[1], 12, math.degrees(math.atan2(geo["E1c"][1] - geo["SP"][1], geo["E1c"][0] - geo["SP"][0])), name=f"HN27-H01_{cw}_sleeve_2027", meta=dict(method="Screen print 1 colour (or embroidery)"))
    else:
        sur = surus(c["tone"], c["acc"] if cw != "Chaux" else TYR)
        k = 330 / 440
        emb["torso"] = f'<g transform="translate({CX-220*k:.1f} {400-160*k:.1f}) scale({k:.4f})">{sur}</g>'
        REGISTRY[f"HN27-H01_{cw}_back_surus"] = dict(frag=sur, nw=440, nh=320, w_cm=33, h_cm=24, meta=dict(method="Tone-on-tone embroidery (heavy), accent tusk"))
        t = T("FRANCHIR L’INCONNUE", "archivo", 22, 0, 18, c["tone"] if cw != "Chaux" else TYR, tracking=300, wght=800, wdth=112)
        tw = text_w("FRANCHIR L’INCONNUE", "archivo", 22, 300, wght=800, wdth=112)
        emb["torso"] += place(t, tw, 24, CX, 590, 22, name=f"HN27-H01_{cw}_back_motto", meta=dict(method="Embroidery tone-on-tone"))[0]
    return dict(print=pr, emb=emb, over=over)

# ============================================================================ C1 CAP
C1_CW = {
    "Pourpre": dict(body=TYR, brim=CHX, brim_u=PAL["chaux_d"], strap=TYRD, metal="#C9C3B4", eye=TYRD, ink=CHX, acc=CIT),
    "Chaux": dict(body=CHX, brim=TYR, brim_u=TYRD, strap=PAL["chaux_d"], metal="#C9C3B4", eye=PAL["chaux_d"], ink=TYR, acc=TYR),
    "Encre": dict(body=ENC_BODY, brim=CIT, brim_u="#9CB21F", strap=ENC_RIB, metal="#C9C3B4", eye=ENC_RIB, ink=CHX, acc=CIT),
}
def c1_art(view, cw):
    c = C1_CW[cw]; pr, emb = {}, {}
    if view == "front":
        m, nw, nh = mono_art(c["ink"], c["acc"], 100)
        emb["crown"] = place(m, nw, nh, CX, 250, 6.0, name=f"HN27-C01_{cw}_front_mono", meta=dict(method="Embroidery 2 colours, 3D puff optional"))[0]
    else:
        n, nw, nh = numerals(60, c["ink"], 0, 60 * .74, tracking=40)
        emb["crown"] = place(n, nw, 60 * .74, CX, 330, 4.2, name=f"HN27-C01_{cw}_back_2027", meta=dict(method="Embroidery 1 colour"))[0]
    return dict(print=pr, emb=emb)

# ============================================================================ registry
def R(**kw):
    DESIGNS[kw["key"]] = kw

# T1-T4 from c_tees  ------------------------------------------------------------
for k, d in TEES.items():
    R(key=k, id=d["id"], name=d["name"], cat="T-shirt", role=d["role"], geom=(lambda v, d=d: tee(v, d["style"], d["fabric"])), art=d["art"],
      cws={n: TCW[n] for n in d["cws"]}, main=d["main"], deco=d["deco"], fabric=d["gsm"], fit=d["style"])
R(key="J1", id="HN27-J01", name="SURUS 27 — Varsity", cat="Jacket", role="Premium varsity — flagship piece", geom=varsity, art=j1_art, cws=J1_CW, main="Pourpre / Chaux", fit="boxy, set-in sleeves",
  fabric="Body: wool-blend melton ~24 oz (~680 gsm) | Sleeves: PU leather-look on knit backing | Rib: acrylic/wool-blend rib knit",
  deco=[("Left chest", "Chenille Λ letter, embroidered border", "12.8 x 15 cm"), ("Right chest", "Embroidery 1 colour", "6 cm wide"), ("Sleeve R (viewer L)", "Seal patch, merrow border", "8 cm Ø"),
        ("Sleeve L (viewer R)", "Embroidery 1 colour", "22 cm"), ("Back", "Twill appliqué + embroidery, arc lettering", "approx 46 x 44 cm"), ("Collar / cuffs / hem", "Striped rib (knitted-in)", "—")])
R(key="J2", id="HN27-J02", name="FRANCHIR — Coach", cat="Jacket", role="Lightweight statement coach jacket (budget hero)", geom=coach, art=j2_art, cws=J2_CW, main="Citron", fit="boxy, drop shoulder",
  fabric="Shell: poly-cotton or nylon twill ~110-140 gsm, water-repellent finish | Lining: poly taffeta | Cuffs: rib",
  deco=[("Left chest", "Embroidery 2 colours", "7 cm Ø"), ("Sleeve R (viewer L)", "Screen print 1 colour", "20 cm"), ("Back", "Screen print 1 colour, large type", "38 x 40 cm"), ("Front", "7 snap buttons (tyr-coloured)", "—")])
R(key="J3", id="HN27-J03", name="LABO — Workwear chore", cat="Jacket", role="Workwear lab jacket with restrained scientific details", geom=chore, art=j3_art, cws=J3_CW, main="Sable", fit="boxy",
  fabric="Cotton canvas ~270-320 gsm, garment-washed | Corozo/resin buttons",
  deco=[("Chest pocket", "Embroidery 1 colour", "9 cm wide"), ("Lower-left pocket", "Printed ruler (1:1 cm scale)", "15 cm"), ("Back upper", "Numbered woven label", "10 cm"), ("Back", "Tonal screen print, construction Surus", "24 cm")])
R(key="V1", id="HN27-V01", name="COL V — Knit vest", cat="Vest", role="Collegiate knit vest", geom=vest_knit, art=v1_art, cws=V1_CW, main="Pourpre", fit="regular, hip length",
  fabric="Cotton-rich or wool-blend knit, 7-9 gauge | Rib trims, 2 stripes", deco=[("Left chest", "Embroidery 2 colours (or intarsia)", "6.5 cm"), ("Back neck", "Embroidery 1 colour", "5.5 cm"), ("Trims", "Knitted-in stripes (neck, arm, hem)", "—")])
R(key="V2", id="HN27-V02", name="GILET LABO — Quilted vest", cat="Vest", role="Contemporary layering vest", geom=vest_quilt, art=v2_art, cws=V2_CW, main="Encre", fit="regular, hip length",
  fabric="Nylon/poly shell 20-30D, light fill 60-80 gsm, horizontal quilting 8.8 cm channels | Zip YKK-type #5", deco=[("Left chest", "Embroidery 2 colours", "5 cm Ø"), ("Hem left", "Woven label", "4.6 cm"), ("Back spine", "Screen print 1 colour, vertical", "40 cm")])
R(key="H1", id="HN27-H01", name="TRAVERSÉE — Hoodie", cat="Hoodie", role="Heavyweight tone-on-tone hoodie", geom=hoodie, art=h1_art, cws=H1_CW, main="Pourpre", fit="boxy, drop shoulder",
  fabric="Brushed-back fleece 380-420 gsm cotton | Rib 2x2 cuffs & hem | Flat drawcord, metal tips", deco=[("Left chest", "Embroidery 2 colours", "7 cm Ø"), ("Sleeve L", "Print 1 colour", "12 cm"), ("Back", "Tone-on-tone heavy embroidery + accent tusk", "33 cm wide")])
R(key="C1", id="HN27-C01", name="BORNE — 6-panel cap", cat="Cap", role="Embroidered 6-panel cap", geom=cap, art=c1_art, cws=C1_CW, main="Pourpre", fit="unstructured/low profile",
  fabric="Cotton twill ~260 gsm | Self-fabric strap with metal slide | 2 eyelets / 4 each side", deco=[("Front", "Embroidery 2 colours", "6 cm Ø"), ("Back crown", "Embroidery 1 colour", "4.2 cm")])

def colours(did, cw):
    return DESIGNS[did]["cws"][cw]

def mock_design(did, cw, view, backdrop="studio", art_override=None):
    d = DESIGNS[did]; parts, geo = d["geom"](view)
    c = d["cws"][cw]
    art = d["art"](view, cw)
    return mock(parts, c, art=art, backdrop=backdrop), parts, art, geo

if __name__ == "__main__":
    from PIL import Image
    import sys
    ids = sys.argv[1:] or ["J1", "J2", "J3", "V1", "V2", "H1", "C1"]
    ims = []
    for did in ids:
        for view in ("front", "back"):
            s, *_ = mock_design(did, DESIGNS[did]["main"], view)
            p = f"/tmp/g_{did}_{view}.svg"; write(p, s); render(p, png=p.replace(".svg", ".png"), scale=.5)
            ims.append(Image.open(p.replace(".svg", ".png")).convert("RGB"))
    W, H = ims[0].size
    n = len(ids)
    sh = Image.new("RGB", (W * n, H * 2))
    for i, im in enumerate(ims): sh.paste(im, ((i // 2) * W, (i % 2) * H))
    sh.save("/tmp/garments.png"); print(sh.size)
