from identity import *
from pathlib import Path
OUT = ROOT / "brand-identity" / "logos"
P = PAL

def lockup_h(fg, lam=None, size=120, sub=None):
    """Horizontal lockup: wordmark + justified sub-line + motto. returns body,w,h"""
    wm, w, c = wordmark(size, fg, 0, c_top := size*0.74, lam_fill=lam)
    y0 = c_top
    body = wm
    sub = sub or fg
    gap = size * 0.16
    body += justify("LYCÉE HANNIBAL  ·  TÉBOURBA", "archivo", size*0.135, w, sub, 0, y0 + gap + size*0.135*0.72, wght=700, wdth=112)
    h = y0 + gap + size*0.135*0.72 + size*0.02
    return body, w, h

def save_logo(name, body, w, h, pad=20, bg=None):
    s = svg(w + 2*pad, h + 2*pad, f'<g transform="translate({pad} {pad})">{body}</g>', bg=bg)
    p = OUT / f"{name}.svg"; write(p, s); render(p, png=OUT / f"{name}.png", scale=2)
    return p

def stacked(fg, acc, ele_fg=None, size=100):
    """Surus above wordmark + subline + motto"""
    wm, w, c = wordmark(size, fg, 0, 0, lam_fill=acc if acc != fg else None)
    k = w * 0.34 / 440
    ele = surus(ele_fg or fg, acc, scale=k, x=(w - 440*k)/2, y=0)
    eh = 320 * k
    body = ele + f'<g transform="translate(0 {eh + size*0.30 + c})">{wm}</g>'
    y = eh + size*0.30 + c + size*0.16 + size*0.075
    body += justify("LYCÉE HANNIBAL  ·  TÉBOURBA", "archivo", size*0.135, w, fg, 0, y, wght=700, wdth=112)
    y2 = y + size*0.30
    body += T("BAC SCIENCES 2027", "archivo", size*0.135, w/2, y2, acc if acc != fg else fg, "middle", tracking=300, wght=700, wdth=112)
    return body, w, y2 + size*0.05

if __name__ == "__main__":
    # ---- individual files
    for nm, fg, lam, bg in [("wordmark_tyr", P["tyr"], None, None), ("wordmark_encre", P["encre"], None, None),
                            ("wordmark_chaux", P["chaux"], P["citron"], P["tyr"]), ("wordmark_1c_black", "#000", None, None)]:
        b, w, h = lockup_h(fg, lam)
        save_logo("lockup_h_" + nm.split("_",1)[1], b, w, h, bg=bg)
    for nm, fg, acc, bg in [("tyr", P["tyr"], P["tyr"], None), ("chaux", P["chaux"], P["citron"], P["tyr"]), ("1c_black", "#000", "#000", None)]:
        b, w, h = stacked(fg, acc); save_logo("lockup_stacked_" + nm, b, w, h, bg=bg)
    for nm, fg, acc, bg in [("tyr_citron", P["tyr"], P["citron"], None), ("chaux_citron", P["chaux"], P["citron"], P["tyr"]),
                            ("1c_black", "#000", None, None), ("1c_tyr", P["tyr"], None, None)]:
        save_logo("surus_" + nm, surus(fg, acc), 440, 320, bg=bg)
    save_logo("surus_construction", surus(P["chaux"], P["citron"], construction=True), 440, 320, bg=P["encre"])
    save_logo("monogram_tyr", monogram(100, 100, 100, P["tyr"], P["citron"]), 200, 200)
    save_logo("monogram_chaux", monogram(100, 100, 100, P["chaux"], P["citron"]), 200, 200, bg=P["tyr"])
    n, w, h = numerals(160, P["tyr"], 0, 160*0.74, tracking=40); save_logo("numerals_2027_tyr", n, w, h*1.0)
    n, w, h = numerals(160, P["citron"], 0, 160*0.74, tracking=40); save_logo("numerals_2027_citron", n, w, h*1.0, bg=P["tyr"])
    save_logo("seal_tyr", seal(200, 200, 200, P["tyr"], P["chaux"], P["citron"]), 400, 400)
    save_logo("seal_chaux", seal(200, 200, 200, P["chaux"], P["tyr"], P["tyr"], text_col=P["tyr"]), 400, 400)
    save_logo("seal_1c_black", seal(200, 200, 200, "#000", "#fff", "#fff"), 400, 400, bg="#fff")
    print("logos done")
