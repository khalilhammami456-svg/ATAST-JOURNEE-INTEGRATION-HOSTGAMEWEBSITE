from g_tee import *
from art import *

CW = {   # colourways: body fabric, rib, inner, ink (main print/embroidery), acc (accent)
    "Chaux":   dict(body=PAL["chaux"], rib=PAL["chaux_d"], body_in=PAL["chaux_d"], ink=PAL["tyr"], acc=PAL["tyr_l"], on_acc=PAL["encre"]),
    "Pourpre": dict(body=PAL["tyr"], rib=PAL["tyr_d"], body_in=PAL["tyr_d"], ink=PAL["chaux"], acc=PAL["citron"], on_acc=PAL["encre"]),
    "Encre":   dict(body="#1D1523", rib="#120C17", body_in="#120C17", ink=PAL["chaux"], acc=PAL["citron"], on_acc=PAL["encre"]),
    "Sable":   dict(body=PAL["sable"], rib="#B7A57F", body_in="#B7A57F", ink=PAL["tyr"], acc=PAL["tyr_l"], on_acc=PAL["encre"]),
    "Citron":  dict(body=PAL["citron"], rib="#B5CE22", body_in="#B5CE22", ink=PAL["tyr"], acc=PAL["encre"], on_acc=PAL["encre"]),
}

def woven_label_art(cw, cx=CX, y=96):
    w, h = 40, 17
    lab = (f'<rect x="{cx-w/2}" y="{y}" width="{w}" height="{h}" rx="1.5" fill="{PAL["chaux"]}" stroke="#00000033" stroke-width=".6"/>'
           + T("HΛNNIBΛL", "archivo", 4.2, cx, y + 8.2, PAL["tyr"], "middle", tracking=60, wght=800, wdth=115)
           + T("2027", "archivo", 3.2, cx, y + 13.4, PAL["tyr"], "middle", tracking=120, wght=700, wdth=110))
    return lab

# ----------------------------------------------------------------- T1  PIERRE  (minimal everyday)
def t1_art(view, cw):
    c = CW[cw]; pr, emb, over = {}, {}, ""
    if view == "front":
        m, nw, nh = mono_art(c["ink"], c["acc"] if cw != "Chaux" else PAL["tyr"], 100)
        # left chest, 6.5 cm
        frag, h = place(m, nw, nh, CX + 105, y_hps(10.5), 6.5)
        emb["torso"] = frag
        pr["inner"] = woven_label_art(c)
    else:
        mt, mw, mh = motto_line(c["ink"], 20)
        frag, h = place(mt, mw, mh, CX, y_hps(8.5), 17.0)
        ar, aw, ah = motto_line(c["ink"], 26, ar=True)
        frag2, h2 = place(ar, aw, ah, CX, y_hps(8.5) + (h + 1.3) * PXCM, 10.5)
        pr["torso"] = frag + frag2
    return dict(print=pr, emb=emb)

# ----------------------------------------------------------------- T2  SURUS  (bold statement)
def t2_art(view, cw):
    c = CW[cw]; pr, emb = {}, {}
    if view == "front":
        wm, ww, wh = wm_art(c["ink"], c["acc"], 100)
        frag, h = place(wm, ww, wh, CX + 105, y_hps(11.0), 8.0)
        pr["torso"] = frag
    else:
        s, sw_, sh_ = surus_art(c["ink"], c["acc"], construction=True, cons_col=c["ink"])
        frag, h = place(s, sw_, sh_, CX, y_hps(10), 33.0)
        pr["torso"] = frag
        cap_lines = ["FIG. 1 — SURUS, CONSTRUIT AU COMPAS"]
        t = T(cap_lines[0], "mono", 15, 0, 15, c["ink"], wght=600)
        tw = text_w(cap_lines[0], "mono", 15, wght=600)
        frag2, h2 = place(t, tw, 18, CX, y_hps(10 + h + 2.2), 21)
        pr["torso"] += frag2
    return dict(print=pr, emb=emb)

# ----------------------------------------------------------------- T3  CQFD  (typography)
def t3_art(view, cw):
    c = CW[cw]; pr, emb = {}, {}
    ink = c["ink"]
    if view == "front":
        x = T("x", "serifi", 120, 0, 90, ink)
        frag, h = place(x, 70, 100, CX + 105, y_hps(11.5), 3.6)
        emb["torso"] = frag
    else:
        L = 118
        out = ""
        y = 0
        out += T("Soit ", "serifi", L, 0, y + L * .78, ink); w1 = text_w("Soit ", "serifi", L)
        out += T("x", "serifi", L, w1, y + L * .78, ink); w2 = w1 + text_w("x", "serifi", L)
        out += T(" l’inconnue.", "serifi", L, w2, y + L * .78, ink)
        W = w2 + text_w(" l’inconnue.", "serifi", L)
        y2 = L * 1.12
        out += T("Posons ", "serifi", L, 0, y2 + L * .78, ink); wp = text_w("Posons ", "serifi", L)
        out += T("x = ", "serifi", L, wp, y2 + L * .78, ink); wq = wp + text_w("x = ", "serifi", L)
        out += T("NOUS", "archivo", L * .78, wq, y2 + L * .78, ink if cw != "Encre" else c["acc"], wght=900, wdth=125, tracking=10)
        wn = wq + text_w("NOUS", "archivo", L * .78, 10, wght=900, wdth=125)
        out += T(".", "serifi", L, wn + 4, y2 + L * .78, ink)
        W = max(W, wn + 40)
        y3 = L * 2.3
        out += T("CQFD", "mono", L * .36, 0, y3 + L * .5, ink, tracking=120, wght=700)
        sq = L * .20; qx = text_w("CQFD", "mono", L * .36, 120, wght=700) + L * .18
        out += f'<rect x="{qx}" y="{y3 + L*.5 - sq}" width="{sq}" height="{sq}" fill="{ink}"/>'
        frag, h = place(out, W, y3 + L * .6, CX, y_hps(9.5), 28.0)
        pr["torso"] = frag
    return dict(print=pr, emb=emb)

# ----------------------------------------------------------------- T4  PROMO 27  (special edition)
def t4_art(view, cw):
    c = CW[cw]; pr, emb = {}, {}
    ink, acc = c["ink"], c["acc"]
    if view == "front":
        m, nw, nh = mono_art(ink, acc, 100)
        frag, h = place(m, nw, nh, CX + 105, y_hps(10.5), 6.8)
        emb["torso"] = frag
        # small mono caption on the opposite chest
        cap = T("BAC SCIENCES", "mono", 12, 0, 12, ink, wght=600) + T("PROMO 2027", "mono", 12, 0, 28, ink, wght=600)
        f2, h2 = place(cap, 92, 34, CX - 105, y_hps(11.6), 3.6)
        pr["torso"] = f2
        pr["inner"] = woven_label_art(c)
    else:
        n, nw, nh = numerals(300, acc, 0, 300 * .74, tracking=40)
        frag, h = place(n, nw, 300 * .74, CX, y_hps(9), 29.0)
        pr["torso"] = frag
        # trajectory + coordinates under numerals
        tr = trajectory(520, 90, ink, acc)
        f3, h3 = place(tr, 520, 96, CX, y_hps(9 + h + 2.4), 29.0)
        pr["torso"] += f3
        lab = T("LYCÉE HANNIBAL · TÉBOURBA", "mono", 14, 0, 14, ink, wght=600)
        lab2 = T(COORD, "mono", 14, 520, 14, ink, "end", wght=600)
        f4, h4 = place(lab + lab2, 520, 20, CX, y_hps(9 + h + 2.4 + h3 + 1.3), 29.0)
        pr["torso"] += f4
    return dict(print=pr, emb=emb)

TEES = {
    "T1": dict(id="HN27-T01", name="PIERRE", role="Minimal premium everyday", style="relaxed", fabric="jersey", gsm="230 gsm ring-spun cotton jersey",
               art=t1_art, cws=["Chaux", "Pourpre", "Encre"], main="Chaux",
               deco=[("Left chest", "Embroidery (flat, 2 colours)", "6.5 cm Ø"), ("Back, below collar", "Screen print 1 colour (or DTF)", "17 × 4 cm"), ("Inside neck", "Woven label 40 × 17 mm", "—")]),
    "T2": dict(id="HN27-T02", name="SURUS", role="Bold graphic statement", style="oversize", fabric="jersey", gsm="260 gsm heavyweight cotton jersey",
               art=t2_art, cws=["Pourpre", "Chaux", "Citron"], main="Pourpre",
               deco=[("Left chest", "Screen print 2 colours", "8 cm wide"), ("Back, upper", "Screen print 2 colours (3 with construction lines)", "33 × 26 cm")]),
    "T3": dict(id="HN27-T03", name="CQFD", role="Typography-driven", style="regular", fabric="jersey", gsm="200 gsm combed cotton jersey",
               art=t3_art, cws=["Sable", "Chaux", "Encre"], main="Sable",
               deco=[("Left chest", "Embroidery 1 colour", "3.6 cm"), ("Back, upper", "Screen print 1 colour (2 on Encre)", "28 × 18 cm")]),
    "T4": dict(id="HN27-T04", name="PROMO 27", role="Special edition — Bac Sciences 2027", style="boxy", fabric="jersey", gsm="260 gsm heavyweight cotton jersey",
               art=t4_art, cws=["Encre", "Pourpre"], main="Encre",
               deco=[("Left chest", "Embroidery (2 colours)", "6.8 cm Ø"), ("Right chest", "Screen print 1 colour", "3.6 cm"), ("Back, upper", "Screen print 2 colours", "29 × 24 cm"), ("Inside neck", "Woven label, numbered", "—")]),
}

def render_tee(key, cw, view, scale=0.8, out_dir=None):
    d = TEES[key]; c = CW[cw]
    parts, geo = tee(view, d["style"], d["fabric"])
    art = d["art"](view, cw)
    cols = dict(body=c["body"], rib=c["rib"], body_in=c["body_in"])
    s = mock(parts, cols, art=art)
    return s, parts, geo, art

if __name__ == "__main__":
    from PIL import Image
    import sys
    for key in TEES:
        for view in ("front", "back"):
            s, *_ = render_tee(key, TEES[key]["main"], view)
            p = f"/tmp/{key}_{view}.svg"; write(p, s); render(p, png=p.replace(".svg", ".png"), scale=0.7)
    ims = [Image.open(f"/tmp/{k}_{v}.png").convert("RGB") for k in TEES for v in ("front", "back")]
    W = ims[0].width; H = ims[0].height
    sh = Image.new("RGB", (W * 4, H * 2))
    for i, im in enumerate(ims):
        sh.paste(im, ((i // 2) * W, (i % 2) * H))
    sh.save("/tmp/tee_collection.png"); print(sh.size)
