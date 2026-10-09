"""Export the brand-identity kit (SVG logos, artwork, palette, typography sheet).  System python.

usage: python export_brand.py  ->  brand-identity/logos/*.svg (+PNG previews), brand-identity/color-palette/*, brand-identity/brand-sheet.{html,pdf,png}
All lettering is outlined (HarfBuzz + fontTools) so every SVG is font-independent.
"""
import sys, json
from pathlib import Path
HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(HERE)); sys.path.insert(0, str(HERE / "art"))
import art3d as ART
from lib import PAL, write, render, render_html, text_w

LOGO = ROOT / "brand-identity" / "logos"
ART_DIR = ROOT / "brand-identity" / "artwork"
PAL_DIR = ROOT / "brand-identity" / "color-palette"
for d in (LOGO, ART_DIR, PAL_DIR):
    d.mkdir(parents=True, exist_ok=True)


def out(path, s, png=True, bg="transparent", scale=1.0):
    p = write(path, s)
    if png:
        render(p, png=str(p).replace(".svg", ".png"), scale=scale, bg=bg)
    return p


def main():
    P = PAL
    # ---------- logos
    for nm, fill, bg in (("dark", P["nuit"], "transparent"), ("light", P["chalk"], P["nuit"])):
        out(LOGO / f"wordmark_{nm}.svg", ART.wordmark_svg(P, fill=fill, lam_fill=P["violet"] if nm == "dark" else P["rose"]), bg=bg)
    out(LOGO / "crest_surus.svg", ART.crest_svg(P, fg=P["nuit"], bg=P["chalk"], accent=P["violet"], R=300))
    out(LOGO / "crest_surus_rose.svg", ART.crest_svg(P, fg=P["nuit"], bg=P["rose"], accent=P["maroon"], R=300))
    out(LOGO / "surus_mark.svg", ART.surus_svg(P, fg=P["nuit"], accent=P["violet"]))
    out(LOGO / "monogram_orbit_lambda.svg", ART.orbit_lam_svg(P, fill=P["nuit"], accent=P["violet"], R=200))
    out(LOGO / "numerals_2027.svg", ART.numerals_svg(P, fill=P["nuit"], size=200))
    out(LOGO / "script_bac_sciences.svg", ART.script_svg(P, "Bac Sciences", fill=P["rose_d"], size=300))
    out(LOGO / "motto.svg", ART.motto_svg(P, ink=P["nuit"], accent=P["violet"]))
    # ---------- artwork used on garments
    out(ART_DIR / "tiles_BAcScI.svg", ART.tiles_row_svg(P, fills=[P["rose"], P["violet"], P["blue"], P["nuit"]], inks=[P["nuit"], P["chalk"], P["chalk"], P["chalk"]]))
    out(ART_DIR / "dna_back.svg", ART.dna_tall_svg(P, ink=P["nuit"]))
    out(ART_DIR / "caffeine.svg", ART.caffeine_svg(P, ink=P["nuit"], accent=P["violet"], size=900, line=3.6))
    out(ART_DIR / "punnett.svg", ART.punnett_svg(P, ink=P["nuit"], accent=P["violet"]))
    out(ART_DIR / "cosmic.svg", ART.cosmic_svg(P), bg=P["nuit"])
    out(ART_DIR / "orbit_cell.svg", ART.orbit_cell_svg(P, ink=P["chalk"], accent=P["violet"]), bg=P["nuit"])
    out(ART_DIR / "collage_back.svg", ART.collage_svg(P, ink=P["nuit"], accent=P["violet"], bg=P["lab"]), bg=P["lab"])
    out(ART_DIR / "woven_label.svg", ART.woven_label_svg(P, bg=P["nuit"], ink=P["chalk"], accent=P["violet"]), bg=P["nuit"])
    out(ART_DIR / "neck_label.svg", ART.neck_label_svg(P, bg=P["nuit"], ink=P["chalk"]), bg=P["nuit"])
    out(ART_DIR / "chenille_H.svg", ART.chenille_letter_svg(P, letter="H", fill=P["rose"], border=P["chalk"]))
    out(ART_DIR / "varsity_SCIENCES_arch.svg", ART.varsity_text_svg(P, "SCIENCES", fill=P["rose"], outline=P["chalk"], arc=520, size=170), bg=P["nuit"])
    for kind in ("phys", "chem", "svt"):
        try:
            out(ART_DIR / f"badge_{kind}.svg", ART.badge_svg(P, kind=kind, ring=P["nuit"], fill=P["chalk"], ink=P["nuit"]))
        except Exception as e:                                          # noqa: BLE001
            print("badge", kind, "skipped:", e)
    # ---------- palette
    pal = [("Nuit", "nuit", "navy / near-black: grounds, trousers, text on light"), ("Encre", "encre", "ink black: deepest shadows, line art"),
           ("Chalk", "chalk", "chalk white: text on dark, tiles, rib trim"), ("Lab gray", "lab", "pullover, coach jacket, puffer"),
           ("Dusty rose", "rose", "hero fleece, varsity sleeves"), ("Maroon", "maroon", "alternate grounds, borders"),
           ("Cosmic violet", "violet", "accent only"), ("Electric blue", "blue", "accent only"),
           ("Tunisian red", "red", "controlled accent — tiny details only")]
    json.dump({n: dict(hex=P[k], use=u) for n, k, u in pal}, open(PAL_DIR / "palette.json", "w"), indent=1, ensure_ascii=False)
    # ---------- brand sheet (HTML -> PDF / PNG)
    sw = "".join(f'<div class="sw"><i style="background:{P[k]}"></i><b>{n}</b><code>{P[k]}</code><span>{u}</span></div>' for n, k, u in pal)
    def img(rel, h): return f'<img src="{rel}" style="height:{h}px">'
    html = f"""<!doctype html><meta charset="utf-8"><title>Brand sheet - Bac Sciences 2027</title>
<style>
@page{{size:1600px 1360px;margin:0}} body{{margin:0;background:#F1EEE7;color:#0B1226;font:15px/1.45 'Archivo',sans-serif}}
.pg{{width:1600px;height:1360px;padding:56px 64px;box-sizing:border-box;position:relative}}
h1{{font:700 28px/1 sans-serif;letter-spacing:.14em;margin:0 0 6px}} h2{{font:600 13px/1 monospace;letter-spacing:.2em;color:#6B4EF5;margin:0 0 22px}}
.row{{display:flex;gap:40px;align-items:center;flex-wrap:wrap}} .dark{{background:#0B1226;padding:36px;border-radius:6px}}
.grid{{display:grid;grid-template-columns:repeat(3,1fr);gap:14px}} .sw{{display:grid;grid-template-columns:54px 1fr;gap:2px 12px;align-items:center}}
.sw i{{grid-row:span 3;width:54px;height:54px;border-radius:50%;border:1px solid #0B122622}} .sw code{{font:12px monospace}} .sw span{{font-size:12px;color:#4B525C}}
.cap{{font:11px monospace;letter-spacing:.12em;color:#4B525C;margin-top:8px}} .art{{display:grid;grid-template-columns:repeat(4,1fr);gap:22px;margin-top:26px}}
.art div{{background:#fff;border-radius:6px;padding:16px;display:flex;flex-direction:column;align-items:center;gap:8px}} .art img{{max-width:100%;max-height:200px}}
</style>
<div class="pg"><h1>LYCÉE HANNIBAL · TÉBOURBA</h1><h2>BAC SCIENCES 2027 — IDENTITÉ « ORBITE-Λ »</h2>
<div class="row"><div>{img('logos/wordmark_dark.png', 120)}<div class="cap">WORDMARK — A = Λ (Hannibal's Alps)</div></div>
<div class="dark">{img('logos/wordmark_light.png', 120)}</div>
<div>{img('logos/crest_surus.png', 230)}<div class="cap">SCEAU SURUS — atom-ring ear</div></div>
<div>{img('logos/monogram_orbit_lambda.png', 150)}<div class="cap">MONOGRAMME ORBITE-Λ</div></div>
<div>{img('logos/numerals_2027.png', 90)}<div class="cap">2027 — orbit zero</div></div></div>
<div class="art" style="margin-top:34px">
<div>{img('logos/script_bac_sciences.png', 90)}<span class="cap">SCRIPT — Great Vibes</span></div>
<div>{img('logos/motto.png', 80)}<span class="cap">DEVISE — TRAVERSER L'INCONNU / عبور المجهول</span></div>
<div>{img('logos/surus_mark.png', 150)}<span class="cap">SURUS</span></div>
<div>{img('artwork/tiles_BAcScI.png', 60)}<span class="cap">TUILES B·Ac·Sc·I = BAC SCI</span></div></div>
<h2 style="margin-top:42px">PALETTE</h2><div class="grid">{sw}</div>
<h2 style="margin-top:42px">TYPOGRAPHIE</h2>
<div class="row" style="gap:60px"><div><b style="font:800 34px sans-serif">Archivo</b><div class="cap">WORDMARK / TITRES (OFL)</div></div>
<div><b style="font:500 28px monospace">JetBrains Mono</b><div class="cap">ANNOTATIONS SCIENTIFIQUES (OFL)</div></div>
<div><b style="font:italic 400 36px serif">Great Vibes</b><div class="cap">SCRIPT ÉDITION LIMITÉE (OFL)</div></div>
<div><b style="font:400 30px sans-serif">Graduate</b><div class="cap">VARSITY (OFL)</div></div>
<div><b style="font:600 30px sans-serif">Noto Kufi / Aref Ruqaa</b><div class="cap">ARABE — À RELIRE PAR UN LOCUTEUR NATIF</div></div></div>
</div>"""
    hp = ROOT / "brand-identity" / "brand-sheet.html"
    hp.write_text(html, encoding="utf-8")
    render_html(hp, png=str(ROOT / "brand-identity" / "brand-sheet.png"), pdf=str(ROOT / "brand-identity" / "brand-sheet.pdf"), w=1600, h=1360)
    print("brand kit exported")


if __name__ == "__main__":
    main()
