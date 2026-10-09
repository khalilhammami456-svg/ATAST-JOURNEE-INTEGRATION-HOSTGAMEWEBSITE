"""Tech-pack generator (HTML -> PDF via headless Chromium).  System python.

usage: python techpack.py [ID ...]          -> tech-packs/<ID>_techpack.html / .pdf   (default: all items that have a scene)

Inputs  (everything is derived from the model, nothing is typed by hand per item except the construction tables below):
  collection.py            item spec, fabrics, colourways, placements text
  3d/models/<ID>/*_manifest.json , <ID>_measures.json   pattern pieces + measurements from the 3D shell
  3d/textures/<ID>/<cw>_placements.json                  print / embroidery / woven placements (texlab log)
  mockups/<ID>_<cw>_front|back.png                        3D renders (final)
  production/cost_model.json                             cost ranges (estimates)
Numbers that are *estimates* are tagged EST.  Nothing here is a supplier-confirmed value.
"""
import sys, json, html, re, datetime
from pathlib import Path
HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(HERE)); sys.path.insert(0, str(HERE / "art"))
from collection import ITEMS, SPEC, PLACE, PAL
from lib import render_html
import tflat
from PIL import Image

DATE = "2026-10-09"
VERSION = "v1.0 (prototype)"
BASE_SIZE = "L"
SIZES = ["S", "M", "L", "XL", "XXL"]
CW_NAME = {"nuit": "Nuit", "chalk": "Chalk", "rose": "Rose poudré", "lab": "Gris labo", "maroon": "Bordeaux", "violet": "Violet cosmique",
           "nuit-rose": "Nuit / Rose", "maroon-chalk": "Bordeaux / Chalk"}

# ---------------------------------------------------------------------------- construction tables (standard apparel practice, ISO 4915 stitch classes)
CONSTR = {
    "tee": [("Épaules", "504 surjet 3 fils + ruban d'épaule", "SPI 12–14", "1 cm"), ("Côtés / manches (montage)", "504 surjet 4 fils", "SPI 12–14", "1 cm"),
            ("Ourlet bas", "406 couture de recouvrement (2 aiguilles)", "SPI 10–12", "2 cm"), ("Ourlet manches", "406 couture de recouvrement", "SPI 10–12", "1,5 cm"),
            ("Col côtes 1x1", "504 surjet + 406 recouvrement, ruban de renfort dos", "SPI 10–12", "—")],
    "hoodie": [("Épaules / empiècement dos", "516 (401 + 504) ou 504 + surpiqûre 301", "SPI 10–12", "1 cm"), ("Montage manches (tombantes)", "516 / 504 + surpiqûre", "SPI 10–12", "1 cm"),
               ("Côtés + manches", "504 surjet 4 fils", "SPI 10–12", "1 cm"), ("Côtes bas / poignets 1x1 + 2 % élasthanne", "504 + piqûre de recouvrement 406", "SPI 10–12", "—"),
               ("Capuche doublée (2 pièces) + oeillets", "301 piqûre droite + 504 ; oeillets métal Ø 8 mm", "SPI 11–12", "1 cm"), ("Fermeture / zip métal (H1, H3)", "301 double piqûre + ruban de renfort", "SPI 11–12", "—"),
               ("Poche kangourou (H2)", "301 piqûre droite + bride d'arrêt 304", "SPI 10–12", "1 cm")],
    "jacket": [("Corps / dos", "401 point de chaînette + 504 surjet des valeurs de couture", "SPI 10–12", "1,5 cm"), ("Manches", "401 / 504", "SPI 10–12", "1,5 cm"),
               ("Côtes (col, poignets, bas)", "504 + 301 surpiqûre", "SPI 10–12", "—"), ("Pressions métal", "Pressions 4 parties, Ø 15 mm, renfort thermocollé", "—", "—"),
               ("Doublure", "301 piqûre droite, ourlet flottant", "SPI 12", "1 cm")],
    "vest": [("Épaules / côtés", "401 + 504", "SPI 10–12", "1,5 cm"), ("Emmanchures", "biais / côtes 504 + 301", "SPI 10–12", "—"),
             ("Matelassage horizontal (V2)", "301 baffles 8 cm, remplissage 80 g recyclé", "SPI 8–10", "—"), ("Fermeture (zip V2 / pressions V1)", "301 double piqûre", "SPI 11–12", "—")],
    "scarf": [("Franges / bouts", "Franges torsadées 6 cm", "—", "—"), ("Lisières", "Jacquard sans couture (tissé) ou 504 + 301 si tricot coupé", "—", "—")],
    "cap": [("Panneaux 6 (couture à plat)", "301 + surpiqûre 301 (2 rangs)", "SPI 10–12", "0,8 cm"), ("Visière", "301, 5 rangs de surpiqûre, renfort rigide", "SPI 12", "—"),
            ("Bandeau intérieur", "301", "—", "—"), ("Oeillets métal ×6, boucle réglable arrière", "—", "—", "—")],
    "beanie": [("Tricot côtes 2x2", "Tricoté en forme (jauge 12) + fermeture sommet", "—", "—"), ("Revers", "Doublé, étiquette tissée cousue 301", "SPI 12", "—")],
    "tote": [("Corps (2 panneaux)", "401 + 504 surjet", "SPI 8–10", "1,5 cm"), ("Anses sangle 25 mm", "Piqûre 301 en carré croisé (box-x)", "SPI 8", "—")],
    "patch": [("Bordure merrow 80 mm", "Surjet merrow 504 haute densité", "—", "—"), ("Dos", "Thermocollant + point d'arrêt à la couture 301", "—", "—")],
    "label": [("Étiquette damas 60 × 12 mm", "Tissée, bords coupés à chaud, pli de bout", "—", "—")],
}
KIND_FR = {"tee": "T-shirt", "hoodie": "Hoodie", "jacket": "Veste", "vest": "Gilet", "scarf": "Écharpe", "cap": "Casquette", "beanie": "Bonnet",
           "tote": "Tote bag", "patch": "Écusson", "label": "Étiquette"}
CARE = {
    "cotton": "Lavage 30 °C à l'envers, séchage à plat ou à basse température, ne pas utiliser d'eau de Javel, repassage à l'envers (broderies).",
    "synthetic": "Lavage 30 °C cycle délicat, ne pas essorer à haute vitesse, pas de sèche-linge, pas de repassage direct.",
    "wool": "Lavage à la main 30 °C ou nettoyage à sec, séchage à plat, ne pas tordre.",
}


def care_for(it):
    f = ITEMS[it]["fabric"].lower()
    if any(k in f for k in ("wool", "merino", "melton")):
        return CARE["wool"]
    if any(k in f for k in ("nylon", "ripstop", "poly", "bonded")) and "cotton" not in f:
        return CARE["synthetic"]
    return CARE["cotton"]


def esc(s):
    return html.escape(str(s))


def jpg(src, dst, w=1100):
    src = Path(src)
    if not src.exists():
        return None
    dst = Path(dst); dst.parent.mkdir(parents=True, exist_ok=True)
    if not dst.exists() or dst.stat().st_mtime < src.stat().st_mtime:
        im = Image.open(src).convert("RGB")
        im.thumbnail((w, int(w * 1.8)))
        im.save(dst, quality=88)
    return dst


def grading(M):
    """Half-girth / length grading (cm), proposed rule: chest +2.5, hem +2.5, length +1.5, sleeve +1, shoulder +1.2 per size step."""
    rule = {"chest_half_cm": 2.5, "waist_half_cm": 2.5, "hem_half_cm": 2.5, "body_length_cm": 1.5, "sleeve_len_cm": 1.0, "shoulder_cm": 1.2,
            "neck_opening_cm": 0.4, "sleeve_opening_half_cm": 0.5}
    out = []
    labels = {"chest_half_cm": "Poitrine (1/2 tour, à 2,5 cm sous l'emmanchure)", "waist_half_cm": "Taille (1/2 tour)", "hem_half_cm": "Bas (1/2 tour)",
              "body_length_cm": "Longueur dos (base col → bas)", "sleeve_len_cm": "Longueur manche (épaule → bord)", "shoulder_cm": "Largeur d'épaules (couture à couture)",
              "neck_opening_cm": "Ouverture d'encolure", "sleeve_opening_half_cm": "Ouverture de manche (1/2 tour)"}
    for k, step in rule.items():
        if k in M and M[k]:
            vals = [round(M[k] + step * (i - 2), 1) for i in range(5)]
            out.append((labels[k], vals, "± 1,0"))
    return out


def page(inner, num, total, it, title):
    meta = ITEMS[it]
    return f"""<section class="pg"><header><span class="brand">LYCÉE HANNIBAL · TÉBOURBA · BAC SCIENCES 2027</span><span>TECH PACK {esc(it)} — {esc(meta['name'])}</span><span>{VERSION} · {DATE}</span></header>
<h2>{esc(title)}</h2>{inner}<footer><span>Dérivé du modèle 3D (avatar d'essayage 186 cm, taille de base {BASE_SIZE}). Valeurs EST = estimations, à confirmer par échantillon.</span><span>{num} / {total}</span></footer></section>"""


CSS = """
@page{size:297mm 210mm;margin:0}
*{box-sizing:border-box} body{margin:0;font:11.5px/1.4 'Archivo','Helvetica Neue',Arial,sans-serif;color:#0B1226;background:#fff}
.pg{width:297mm;height:210mm;padding:11mm 13mm 9mm;position:relative;page-break-after:always;overflow:hidden}
header{display:flex;justify-content:space-between;font:600 9.5px/1 monospace;letter-spacing:.08em;border-bottom:2px solid #0B1226;padding-bottom:6px;margin-bottom:9px;color:#4B525C}
header .brand{color:#0B1226;font-weight:800}
footer{position:absolute;left:13mm;right:13mm;bottom:6mm;display:flex;justify-content:space-between;font:9px monospace;color:#8E959E}
h1{font:800 34px/1 'Archivo',sans-serif;letter-spacing:.03em;margin:4px 0 2px} h2{font:800 17px/1 'Archivo',sans-serif;letter-spacing:.08em;text-transform:uppercase;margin:2px 0 10px;color:#0B1226}
h3{font:700 11px/1 monospace;letter-spacing:.14em;text-transform:uppercase;color:#6B4EF5;margin:12px 0 5px}
table{border-collapse:collapse;width:100%} th{background:#0B1226;color:#F1EEE7;font:600 9.5px monospace;letter-spacing:.07em;text-align:left;padding:4px 6px;text-transform:uppercase}
td{border-bottom:1px solid #D9D4C8;padding:3.5px 6px;vertical-align:top} tr:nth-child(even) td{background:#F6F4EE}
.two{display:grid;grid-template-columns:1fr 1fr;gap:14px} .three{display:grid;grid-template-columns:1fr 1fr 1fr;gap:12px}
.sw{display:inline-flex;align-items:center;gap:6px;margin:2px 12px 2px 0}.sw i{display:inline-block;width:18px;height:18px;border-radius:50%;border:1px solid #0B122633}
.hero{display:flex;gap:10px;justify-content:center;align-items:flex-end;background:linear-gradient(#E9E6DF,#D8D4CC);border-radius:6px;padding:8px;height:150mm}
.hero img{height:100%;object-fit:contain} .note{background:#F1EEE7;border-left:4px solid #6B4EF5;padding:6px 9px;margin:8px 0;font-size:10.5px}
.est{color:#B87B83;font:600 9px monospace} .flag{background:#FFF3F0;border-left:4px solid #C8102E;padding:6px 9px;margin:8px 0;font-size:10.5px}
svg.flat{max-width:100%;height:auto} .small{font-size:10px;color:#4B525C} code{font:10px monospace}
"""


def build(it):
    meta = ITEMS[it]; spec = SPEC.get(it, {})
    mdir = ROOT / "3d" / "models" / it
    M = {}
    if (mdir / f"{it}_measures.json").exists():
        M = json.load(open(mdir / f"{it}_measures.json"))
    cws = list(meta["colorways"])
    cw0 = cws[0]
    pjson = ROOT / "3d" / "textures" / it / f"{cw0}_placements.json"
    placements = json.load(open(pjson)) if pjson.exists() else []
    tmp = ROOT / "tech-packs" / "_img"
    imgs = {}
    for cw in cws:
        for v in ("front", "back"):
            j = jpg(ROOT / "mockups" / f"{it}_{cw}_{v}.png", tmp / f"{it}_{cw}_{v}.jpg")
            if j:
                imgs[(cw, v)] = j.name
    # flat
    flat_svg, legend = "", []
    mp = mdir / f"{it}_manifest.json"
    if mp.exists() and meta["kind"] in ("tee", "hoodie", "jacket", "vest"):
        man = json.load(open(mp))
        fp = ROOT / "technical-flats" / f"{it}_flat.svg"
        r = tflat.flat_svg(it, man, placements, fp)
        legend = r["legend"]
        flat_svg = fp.read_text(encoding="utf-8").replace('<svg ', '<svg class="flat" ', 1)
    cost = {}
    cp = ROOT / "production" / "cost_model.json"
    if cp.exists():
        cost = json.load(open(cp)).get(it, {})
    pages = []
    # ----------------------------------------------------------- 1 cover
    sw = "".join(f'<span class="sw"><i style="background:{(c if isinstance(c, str) else c[0])}"></i>{esc(CW_NAME.get(k, k))} <code>{esc(c if isinstance(c, str) else " + ".join(c))}</code></span>'
                 for k, c in meta["colorways"].items())
    heroimgs = "".join(f'<img src="_img/{imgs[(cw0, v)]}">' for v in ("front", "back") if (cw0, v) in imgs)
    cover = f"""<div style="display:grid;grid-template-columns:1.25fr 1fr;gap:16px"><div><div class="hero">{heroimgs or '<span class="small">rendu 3D à venir</span>'}</div></div>
<div><h1>{esc(meta['name'])}</h1><div style="font:600 14px monospace;letter-spacing:.1em;color:#6B4EF5">{esc(it)} · {esc(KIND_FR[meta['kind']])} · {esc(meta['title'])}</div>
<h3>Coloris</h3><div>{sw}</div>
<h3>Matière principale</h3><p>{esc(meta['fabric'])}</p>
<h3>Grammage</h3><p>{esc(spec.get('gsm', '—'))}</p>
<h3>Fabrication / décor</h3><p>{esc(spec.get('make', ''))}</p>
<h3>Concept</h3><p>{esc(spec.get('note', ''))}</p>
<h3>Références (visuels fournis)</h3><p>{esc(', '.join(meta.get('refs', [])) or '—')}</p>
<h3>Tailles</h3><p>{' · '.join(SIZES)} — taille de base du modèle 3D : <b>{BASE_SIZE}</b></p>
<div class="flag"><b>Statut :</b> prototype numérique. Aucune pièce n'est validée pour la production avant approbation d'un échantillon physique. Aucun fournisseur n'a été contacté.</div></div></div>"""
    pages.append(("Couverture", cover))
    # ----------------------------------------------------------- 2 flats + placements
    rows = "".join(f"<tr><td>{n}</td><td>{esc(tflat.KIND_FR.get(k, k))}</td><td>{esc(p.replace('_', ' '))}</td><td>{w * 100:.1f} × {h * 100:.1f}</td><td>{x * 100:+.1f} / {z * 100:+.1f}</td></tr>"
                   for n, k, p, w, h, x, z in legend)
    lt = PLACE.get(it, [])
    ptxt = "".join(f"<li>{esc(t)}</li>" for t in lt)
    if flat_svg:
        inner = f"""<div style="display:grid;grid-template-columns:1.6fr 1fr;gap:14px"><div style="border:1px solid #D9D4C8;border-radius:4px;padding:4px">{flat_svg}</div>
<div><h3>Emplacements (numéros du plan)</h3><table><tr><th>#</th><th>Technique</th><th>Pièce</th><th>L × H cm</th><th>x / z cm*</th></tr>{rows}</table>
<p class="small">* x : écart latéral par rapport à l'axe de la pièce ; z : hauteur dans le repère du patron (0 = ligne d'épaule/épaule, valeurs absolues du modèle 3D). Position à valider sur l'échantillon.</p>
<h3>Description</h3><ul style="margin:0;padding-left:16px">{ptxt}</ul></div></div>
<div class="note">Le plan est tracé automatiquement à partir des pièces de patron du modèle 3D (devant, dos, manches) ; cotes en cm au milieu de la poitrine et en hauteur. Les rectangles pointillés sont les emplacements de décor réels utilisés pour les textures.</div>"""
    else:
        inner = f"<h3>Description</h3><ul>{ptxt}</ul><div class=\"note\">Accessoire : plan de patron détaillé dans la fiche matière ci-après.</div>"
    pages.append(("Plan technique et emplacements", inner))
    # ----------------------------------------------------------- 3 materials & construction
    cons = "".join(f"<tr><td>{esc(a)}</td><td>{esc(b)}</td><td>{esc(c)}</td><td>{esc(d)}</td></tr>" for a, b, c, d in CONSTR.get(meta["kind"], []))
    trims = {
        "tee": ["Ruban d'épaule coton", "Étiquette de col imprimée (taille / composition)", "Étiquette tissée Orbite-Λ (ourlet, A5)"],
        "hoodie": ["Cordons ronds Ø 4 mm, embouts métal (aglets)", "Oeillets métal Ø 8 mm ×2", "Zip métal nickel n°5 ruban sombre (H1, H3)", "Étiquette tissée A5 + étiquette de soin",
                   "Côtes 1x1 + 2 % élasthanne (col, poignets, bas)"],
        "jacket": ["Pressions métal Ø 15 mm ×6", "Doublure taffetas", "Côtes à deux filets (col, poignets, bas)", "Étiquette tissée A5 + étiquette de soin"],
        "vest": ["Pressions métal Ø 15 mm ×6 (V1) / zip (V2)", "Garnissage recyclé 80 g (V2)", "Côtes (V1)", "Étiquette tissée A5 + soin"],
        "scarf": ["Franges 6 cm", "Étiquette tissée A5 cousue au bout"], "cap": ["Oeillets métal ×6", "Boucle réglable", "Bandeau sudation"],
        "beanie": ["Étiquette tissée sur revers"], "tote": ["Sangle coton 25 mm", "Renfort d'anse"], "patch": ["Thermocollant au dos"], "label": ["—"],
    }[meta["kind"]]
    tr = "".join(f"<li>{esc(t)}</li>" for t in trims)
    bom = f"""<div class="two"><div><h3>Matières</h3><table><tr><th>Poste</th><th>Spécification</th></tr>
<tr><td>Tissu principal</td><td>{esc(meta['fabric'])}</td></tr><tr><td>Grammage</td><td>{esc(spec.get('gsm', '—'))}</td></tr>
<tr><td>Besoin tissu (modèle 3D)</td><td>{(M.get('surface_m2', 0) + M.get('hood_surface_m2', 0)):.2f} m² net (surface de la coque 3D) — marge de coupe EST 18–25 %</td></tr>
<tr><td>Fil</td><td>Polyester 40/2 ton sur ton (couleurs : voir fiche coloris)</td></tr>
<tr><td>Entretien (EST, à valider par essais)</td><td>{esc(care_for(it))}</td></tr></table>
<h3>Mercerie / finitions</h3><ul style="margin:0;padding-left:16px">{tr}</ul></div>
<div><h3>Construction (classes de points ISO 4915)</h3><table><tr><th>Opération</th><th>Point / méthode</th><th>Densité</th><th>Valeur de couture</th></tr>{cons}</table>
<div class="note">Les classes de points et densités sont des valeurs usuelles de l'habillement ; elles sont à confirmer avec l'atelier choisi. Aucun fournisseur n'a validé ces valeurs.</div></div></div>"""
    pages.append(("Matières, mercerie et construction", bom))
    # ----------------------------------------------------------- 4 measurements
    gr = grading(M)
    if gr:
        grows = "".join(f"<tr><td>{esc(lab)}</td>" + "".join(f"<td{' style=\"font-weight:800;background:#EEEAF9\"' if i == 2 else ''}>{v:.1f}</td>" for i, v in enumerate(vals)) + f"<td>{tol}</td></tr>" for lab, vals, tol in gr)
        meas = f"""<table><tr><th>Point de mesure (cm)</th>{''.join(f'<th>{s}</th>' for s in SIZES)}<th>Tolérance</th></tr>{grows}</table>
<div class="note"><b>Base {BASE_SIZE}</b> mesurée sur la coque 3D (surface moyenne du tissu, avatar d'essayage 186 cm, bras en A). Gradation proposée : poitrine / bas +2,5 cm par taille (demi-tour), longueur +1,5, manche +1,0, épaules +1,2 — <b>EST</b>, à valider par un modéliste.
La coupe est volontairement oversize (aisance poitrine ≈ {M.get('chest_half_cm', 0) * 2 - 108:.0f} cm sur un tour de poitrine de 108 cm EST pour le mannequin).</div>
<h3>Détails dimensionnels</h3><table><tr><th>Élément</th><th>Valeur</th></tr>
<tr><td>Hauteur totale de la pièce</td><td>{M.get('total_height_cm', '—')} cm</td></tr><tr><td>Périmètre bas</td><td>{M.get('hem_girth_cm', '—')} cm</td></tr>
{'<tr><td>Capuche : hauteur × largeur</td><td>%s × %s cm</td></tr>' % (M.get('hood_height_cm'), M.get('hood_width_cm')) if 'hood_height_cm' in M else ''}
<tr><td>Hauteur côtes bas / poignets</td><td>{(ITEMS[it].get('rib_h') or '—')}</td></tr></table>"""
    else:
        meas = f"<div class='note'>Dimensions nominales : {esc(meta['fabric'])}.</div>"
    pages.append(("Mesures et gradation", meas))
    # ----------------------------------------------------------- 5 decoration specs
    DECO_SPEC = """<table><tr><th>Technique</th><th>Spécification (valeurs usuelles, EST)</th></tr>
<tr><td>Broderie satin</td><td>Densité 0,40 mm, sous-couche en zigzag + bord, fil polyester 40 wt ton sur ton ; arrêt de fil à chaque changement de couleur ; entoilage tear-away 2 couches sur jersey, cut-away sur molleton ; fichier .DST à numériser à partir des SVG vectoriels fournis (<code>brand-identity/</code>).</td></tr>
<tr><td>Sérigraphie</td><td>Plastisol (T2, J2) ou base eau (T1, T3) ; tamis 77–120 fils/cm ; sous-couche blanche sur couleurs foncées ; polymérisation 160 °C ; pantones à faire correspondre aux références sRGB du dossier (aucune valeur Pantone n'est garantie ici).</td></tr>
<tr><td>DTF</td><td>Film A3, poudre adhésive, presse 150 °C / 15 s / pression moyenne ; recommandé pour les dégradés (impression cosmique H3) ; lavabilité à tester.</td></tr>
<tr><td>Tissé / écusson</td><td>Damas polyester, bordure merrow 80 mm pour les écussons ; étiquettes 60 × 12 mm pli de bout ; fichier vectoriel fourni.</td></tr>
<tr><td>Chenille</td><td>Lettre « H » découpée au laser, bordure brodée en satin, fond feutre.</td></tr></table>"""
    art = "".join(f"<li>{esc(a.replace('_', ' '))}</li>" for a in meta.get("art", []))
    pages.append(("Décors : broderie, impression, étiquettes", f"""<div class="two"><div>{DECO_SPEC}</div><div><h3>Éléments graphiques (fichiers dans <code>brand-identity/</code>)</h3><ul style="margin:0;padding-left:16px">{art}</ul>
<div class="note">Tout le lettrage est vectorisé (HarfBuzz + fontTools) ; accents français et arabe = vrais glyphes. <b>Texte arabe à faire relire par un locuteur natif avant production.</b></div>
<h3>Faits scientifiques vérifiés</h3><p class="small">{esc(spec.get('note', '—'))}</p></div></div>"""))
    # ----------------------------------------------------------- 6 colourways + cost + QC
    cwimgs = []
    for cw in cws:
        for v in ("front", "back"):
            if (cw, v) in imgs:
                cwimgs.append(f'<figure style="margin:0;text-align:center"><img src="_img/{imgs[(cw, v)]}" style="height:62mm"><figcaption class="small">{esc(CW_NAME.get(cw, cw))} · {v}</figcaption></figure>')
    cwrow = f'<div style="display:flex;gap:6px;justify-content:center;flex-wrap:wrap;background:#EFEBE2;padding:6px;border-radius:6px">{"".join(cwimgs)}</div>' if cwimgs else ""
    cost_row = ""
    if cost:
        u = cost["unit_dt"]
        cost_row = f"""<h3>Budget indicatif (DT / pièce, EST)</h3><table><tr><th>N = 50</th><th>N = 100</th><th>N = 200</th></tr><tr><td>{u['50'][0]:.0f}–{u['50'][1]:.0f}</td><td>{u['100'][0]:.0f}–{u['100'][1]:.0f}</td><td>{u['200'][0]:.0f}–{u['200'][1]:.0f}</td></tr></table>
<p class="small">Voir <code>production/cost-assessment.md</code> : ancrages vérifiés vs hypothèses. Aucun devis fournisseur.</p>"""
    qc = """<ul style="margin:0;padding-left:16px"><li>Échantillon prototype : conformité aux mesures ± 1 cm, symétrie des décors ± 3 mm</li><li>Tenue des couleurs (sRGB de référence) sur tissu réel</li><li>Test de lavage 30 °C × 5 : retrait ≤ 5 %, solidité des teintes ≥ 4</li><li>Broderie : pas de fronçage, fils coupés, contrôle de la densité</li><li>Zip / pressions : 500 cycles, aucun accrochage</li><li>Étiquettes : composition, taille, pays d'origine</li></ul>"""
    pages.append(("Coloris, budget et contrôle qualité", f"{cwrow}<div class='two'><div>{cost_row}</div><div><h3>Contrôle qualité (points de contrôle)</h3>{qc}</div></div>"))
    total = len(pages)
    body = "".join(page(inner, i + 1, total, it, t) for i, (t, inner) in enumerate(pages))
    doc = f"<!doctype html><meta charset='utf-8'><title>Tech pack {it}</title><style>{CSS}</style>{body}"
    out = ROOT / "tech-packs" / f"{it}_techpack.html"
    out.parent.mkdir(exist_ok=True)
    out.write_text(doc, encoding="utf-8")
    render_html(out, pdf=str(out.with_suffix(".pdf")))
    print("tech pack", it, "->", out.with_suffix(".pdf").name, len(pages), "pages")


if __name__ == "__main__":
    ids = sys.argv[1:] or [k for k in ITEMS if (ROOT / "3d" / "models" / k / f"{k}_scene.blend").exists()]
    for k in ids:
        build(k)
