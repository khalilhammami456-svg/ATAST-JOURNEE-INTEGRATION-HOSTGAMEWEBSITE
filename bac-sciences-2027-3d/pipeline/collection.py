"""Single source of truth for the BAC SCIENCES 2027 3D collection (items, colourways, art mapping).

Used by the build scripts, the viewer manifest, the tech packs and the presentation.
Colours are hex sRGB.  Palette roles: nuit (navy/near-black), chalk, lab gray, dusty rose, maroon,
cosmic violet / electric blue (accents), Tunisian red (controlled accent: tiny details only).
"""
from collections import OrderedDict

PAL = dict(
    nuit="#0B1226", encre="#06080F", chalk="#F1EEE7", lab="#8E959E", lab_d="#4B525C", lab_l="#C3C8CE",
    rose="#D9A3A8", rose_l="#EBC6C8", rose_d="#B87B83", maroon="#5C1526", violet="#6B4EF5", blue="#2E7BFF", red="#C8102E",
)

# reference mapping (user-supplied visual references -> original recreations)
REFS = OrderedDict([
    ("ref1", "pink zip hoodie: yoke seam, metal zip, embroidered script, woven crest -> H1 ROSE ORBITE"),
    ("ref2", "cosmic energy back print + scarf all-over -> H3 NUIT COSMIQUE, S1 ORBITE"),
    ("ref3", "gray collegiate hoodie, back collage -> H2 GRIS COLLÈGE"),
    ("ref4", "DNA 'born unique' minimal back print + small left-chest DNA -> T1 NUIT"),
    ("ref5", "molecule graphic -> T3 CAFÉINE, J2 COACH LABO back"),
    ("ref6", "periodic tiles spelling a word -> T2 TABLEAU (B·Ac·Sc·I = BAC SCI), patches, scarf"),
])

ITEMS = OrderedDict()


def item(id, name, kind, title, **kw):
    ITEMS[id] = dict(id=id, name=name, kind=kind, title=title, **kw)


# ----------------------------------------------------------------------------- tees
item("T1", "NUIT", "tee", "T-shirt minimal premium",
     preset="tee_boxy", fabric="Single jersey 240 gsm, 100 % organic combed cotton, garment washed",
     colorways=OrderedDict([("nuit", "#0F1730"), ("chalk", "#EFEBE2"), ("rose", "#D9A3A8")]),
     art=["dna_small_chest", "dna_back", "unique_line"], refs=["ref4"])
item("T2", "TABLEAU", "tee", "T-shirt graphique audacieux",
     preset="tee_boxy", fabric="Heavy jersey 260 gsm, 100 % cotton, boxy cut",
     colorways=OrderedDict([("chalk", "#EFEBE2"), ("lab", "#8E959E"), ("maroon", "#5C1526")]),
     art=["tiles_front", "year_back"], refs=["ref6"])
item("T3", "CAFÉINE", "tee", "T-shirt illustration scientifique",
     preset="tee_boxy", fabric="Single jersey 220 gsm, cotton / modal 90/10",
     colorways=OrderedDict([("lab", "#A3A9B1"), ("rose", "#D9A3A8"), ("nuit", "#0F1730")]),
     art=["caffeine_front", "punnett_back"], refs=["ref5"])
# ----------------------------------------------------------------------------- hoodies
item("H1", "ROSE ORBITE", "hoodie", "Hoodie zippé oversize",
     preset="hoodie_zip", fabric="Brushed-back fleece 380 gsm (80 % cotton / 20 % polyester), rib 1x1 with 2 % elastane, YKK-type metal zip",
     colorways=OrderedDict([("rose", "#D9A3A8"), ("chalk", "#EFEBE2"), ("nuit", "#0F1730")]),
     art=["crest_chest_patch", "script_sleeve", "tiles_back", "label_hem", "motto_hood"], refs=["ref1"])
item("H2", "GRIS COLLÈGE", "hoodie", "Hoodie pull collégial",
     preset="hoodie_pull", fabric="Loopback french terry 340 gsm, 100 % cotton, kangaroo pocket",
     colorways=OrderedDict([("lab", "#8E959E"), ("chalk", "#EFEBE2"), ("maroon", "#5C1526")]),
     art=["wordmark_chest", "collage_back", "year_sleeve", "motto_hood", "label_hem"], refs=["ref3"])
item("H3", "NUIT COSMIQUE", "hoodie", "Hoodie technique",
     preset="hoodie_zip", fabric="Bonded tech fleece 320 gsm (poly / elastane), water-repellent face, tape-seamed",
     colorways=OrderedDict([("nuit", "#0B1226"), ("violet", "#4B36B8"), ("lab", "#4B525C")]),
     art=["crest_chest_small", "cosmic_back", "orbit_sleeves", "label_hem"], refs=["ref2"])
# ----------------------------------------------------------------------------- jackets
item("J1", "VARSITY HANNIBAL", "jacket", "Varsity jacket",
     preset="jacket_varsity", fabric="Melton wool-blend body 500 gsm, faux-leather sleeves, rib collar/cuffs/hem, snap front",
     colorways=OrderedDict([("nuit-rose", ("#0F1730", "#D9A3A8")), ("maroon-chalk", ("#5C1526", "#EFEBE2"))]),
     art=["chenille_h", "patch_2027", "back_sciences_arch", "crest_sleeve"], refs=["ref3"])
item("J2", "COACH LABO", "jacket", "Veste coach légère",
     preset="jacket_coach", fabric="Nylon taffeta 70D, DWR, lightly padded none, snap front",
     colorways=OrderedDict([("lab", "#B7BCC3"), ("nuit", "#0F1730")]),
     art=["wordmark_small_chest", "caffeine_back"], refs=["ref5"])
# ----------------------------------------------------------------------------- vests
item("V1", "GILET VARSITY", "vest", "Gilet varsity",
     preset="vest", fabric="Melton wool-blend 500 gsm, quilted lining, rib trim",
     colorways=OrderedDict([("nuit", "#0F1730"), ("maroon", "#5C1526")]),
     art=["crest_chest_patch", "back_sciences_arch"], refs=["ref3"])
item("V2", "COUCHE LABO", "vest", "Gilet de superposition",
     preset="vest", fabric="Quilted ripstop 30D, recycled fill 80 g, funnel collar, zip",
     colorways=OrderedDict([("lab", "#8E959E"), ("rose", "#D9A3A8")]),
     art=["orbit_tile_repeat", "label_small"], refs=["ref2"])
# ----------------------------------------------------------------------------- scarves
item("S1", "ORBITE", "scarf", "Écharpe motif orbites",
     preset="scarf", fabric="Brushed wool-blend jacquard 180 x 32 cm, chalk contrast ends",
     colorways=OrderedDict([("nuit", "#0B1226"), ("maroon", "#5C1526")]), art=["orbit_allover", "ends_text"], refs=["ref2"])
item("S2", "BORD", "scarf", "Écharpe minimale bordée",
     preset="scarf", fabric="Merino-viscose knit 200 x 28 cm, jacquard border",
     colorways=OrderedDict([("rose", "#D9A3A8"), ("chalk", "#EFEBE2")]), art=["border_text"], refs=["ref6"])
# ----------------------------------------------------------------------------- accessories
item("A1", "CASQUETTE", "cap", "Casquette 6 panneaux",
     preset="cap", fabric="Cotton twill 8 oz, metal-eyelets, strap-back",
     colorways=OrderedDict([("nuit", "#0F1730"), ("rose", "#D9A3A8")]), art=["monogram_front", "year_back"], refs=["ref6"])
item("A2", "BONNET", "beanie", "Bonnet côtelé",
     preset="beanie", fabric="Rib-knit merino/acrylic, folded cuff, woven tab",
     colorways=OrderedDict([("nuit", "#0F1730"), ("chalk", "#EFEBE2")]), art=["woven_tab"], refs=[])
item("A3", "TOTE", "tote", "Tote bag",
     preset="tote", fabric="Canvas 12 oz cotton, 40 x 38 cm, 70 cm handles",
     colorways=OrderedDict([("chalk", "#EFEBE2"), ("nuit", "#0F1730")]), art=["molecule_center"], refs=["ref5"])
item("A4", "ÉCUSSON", "patch", "Écusson brodé / tissé",
     preset="patch", fabric="Merrowed-border twill, 80 mm, heat-seal backing", colorways=OrderedDict([("nuit", "#0B1226")]),
     art=["crest_patch"], refs=[])
item("A5", "ÉTIQUETTE", "label", "Étiquette tissée",
     preset="label", fabric="Damask woven polyester, 60 x 12 mm, end-fold", colorways=OrderedDict([("nuit", "#0B1226")]),
     art=["label_hem"], refs=[])


# ----------------------------------------------------------------------------- production specs (estimates are flagged "est.")
SPEC = {
    "T1": dict(gsm="240 g/m²", make="Jersey bio peigné · col rib 1x1 · piqûre double aiguille · broderie satin 4 cm (≈3 800 pts est.) · sérigraphie base eau 2 couleurs dos",
               hot=[("Broderie ADN poitrine", [0.095, -0.16, 1.42], 0.45, 0), ("ADN dos", [0, 0.13, 1.30], 0.9, 180), ("Col rib", [0, -0.1, 1.56], 0.55, 0)],
               note="Dos : double hélice avec appariement exact A–T (2 liaisons H) et G–C (3 liaisons H)."),
    "T2": dict(gsm="260 g/m²", make="Jersey épais coton · coupe boxy · sérigraphie plastisol 4 couleurs (tuiles) · « 2027 » dos 1 couleur",
               hot=[("Tuiles B·Ac·Sc·I", [0, -0.16, 1.38], 0.85, 0), ("2027 dos", [0, 0.13, 1.34], 0.8, 180), ("Tuile Sc manche", [-0.34, -0.03, 1.33], 0.45, -80)],
               note="B (Z=5) · Ac (Z=89) · Sc (Z=21) · I (Z=53) : les symboles se lisent « BAC SCI »."),
    "T3": dict(gsm="220 g/m²", make="Jersey coton/modal 90/10 · sérigraphie base eau 2 couleurs · formules en mono-espacé",
               hot=[("Caféine C₈H₁₀N₄O₂", [0, -0.16, 1.38], 0.9, 0), ("Carré de Punnett", [0, 0.13, 1.32], 0.9, 180)],
               note="Caféine = 1,3,7-triméthylxanthine, C₈H₁₀N₄O₂, M = 194,19 g·mol⁻¹. Punnett Aa×Aa → 1 AA : 2 Aa : 1 aa."),
    "H1": dict(gsm="380 g/m²", make="Molleton gratté 80/20 · côtes 1x1 + 2 % élasthanne · zip métal · broderie satin (écusson tissé ≈ 7 cm, script manche, tuiles dos) · étiquette tissée",
               hot=[("Écusson tissé", [0.105, -0.16, 1.41], 0.55, 0), ("Zip & cordons", [0, -0.15, 1.42], 0.7, 0), ("Tuiles dos", [0, 0.14, 1.32], 0.9, 180), ("Script manche", [0.40, -0.03, 1.28], 0.6, 90), ("Capuche", [0, 0.16, 1.55], 0.9, 180)],
               note="Référence 1 : hoodie rose zippé, pièce d’empiècement, zip métal, script brodé, écusson."),
    "H2": dict(gsm="340 g/m²", make="French terry bouclette 100 % coton · poche kangourou piquée · broderie wordmark · collage dos sérigraphié 3 couleurs",
               hot=[("Wordmark brodé", [0.115, -0.16, 1.43], 0.55, 0), ("Poche kangourou", [0, -0.17, 1.0], 0.9, 0), ("Collage dos", [0, 0.14, 1.28], 1.0, 180), ("Manche 2027", [0.44, -0.03, 1.27], 0.6, 90)],
               note="Référence 3 : collage dos (ADN, Surus, علوم, 2027, badges Physique/Chimie/SVT). Arabe à faire relire par un locuteur natif."),
    "H3": dict(gsm="320 g/m²", make="Polaire technique bonded déperlante · coutures recouvertes · zip nylon · impression pigmentaire dos · bandes orbite manches",
               hot=[("Cosmos dos", [0, 0.14, 1.30], 1.1, 180), ("Bande orbite manche", [0.40, -0.03, 1.28], 0.6, 90), ("Écusson poitrine", [0.105, -0.16, 1.43], 0.5, 0)],
               note="Référence 2 : énergie cosmique. Énoncé neutre : « L’énergie ne se crée ni ne se détruit : elle se transforme »."),
    "J1": dict(gsm="500 g/m² (feutre) · manches simili-cuir", make="Feutre mélange laine · manches simili-cuir grainé · côtes rayées · pressions métal · chenille « H » · écussons tissés · broderie dos",
               hot=[("Chenille H", [0.105, -0.16, 1.42], 0.6, 0), ("Écusson manche", [-0.40, -0.05, 1.27], 0.6, -90), ("SCIENCES brodé", [0, 0.14, 1.32], 1.0, 180), ("Pressions", [0, -0.16, 1.25], 0.7, 0)],
               note="Veste varsity : corps nuit, manches rose, côtes chalk à deux filets."),
    "J2": dict(gsm="70D taffetas", make="Taffetas nylon DWR · pressions · col montant · ourlet élastiqué · broderie wordmark · impression molécule dos",
               hot=[("Wordmark", [0.075, -0.16, 1.43], 0.5, 0), ("Molécule dos", [0, 0.14, 1.30], 1.0, 180), ("Pressions", [0, -0.16, 1.25], 0.7, 0)],
               note="Référence 5 : molécule. Caféine C₈H₁₀N₄O₂ (SMILES CN1C=NC2=C1C(=O)N(C(=O)N2C)C)."),
    "V1": dict(gsm="500 g/m²", make="Feutre mélange laine · côtes rayées · pressions · écusson tissé · broderie dos arquée",
               hot=[("Écusson", [0.105, -0.16, 1.42], 0.55, 0), ("SCIENCES dos", [0, 0.14, 1.28], 1.0, 180)], note="Gilet varsity sans manches."),
    "V2": dict(gsm="30D ripstop · garnissage 80 g", make="Ripstop matelassé horizontal (baffles 8 cm) · col cheminée · zip · motif orbite ton sur ton",
               hot=[("Matelassage", [0, -0.17, 1.2], 0.9, 0), ("Orbites dos", [0, 0.15, 1.28], 1.0, 180)], note="Gilet de superposition ton sur ton."),
    "S1": dict(gsm="≈ 420 g/m²", make="Jacquard laine/viscose brossé · bouts chalk contrastés · franges 6 cm", hot=[("Motif orbite", [0, -0.14, 1.3], 0.8, 0), ("Bout contrasté", [0.07, -0.14, 1.0], 0.7, 0)], note="Motif répété : atome à trois orbites et noyau."),
    "S2": dict(gsm="≈ 300 g/m²", make="Maille merinos/viscose · bordure typographique jacquard", hot=[("Bordure", [0, -0.14, 1.35], 0.8, 0)], note="Bordure : TÉBOURBA · BAC SCIENCES · 2027 · LYCÉE HANNIBAL."),
    "A1": dict(gsm="8 oz", make="Twill coton 6 panneaux · œillets · fermeture métal · monogramme brodé", hot=[("Monogramme", [0, -0.12, 1.78], 0.5, 0), ("2027", [0, 0.10, 1.75], 0.5, 180)], note=""),
    "A2": dict(gsm="—", make="Maille côtelée mérinos/acrylique · revers · étiquette tissée", hot=[("Étiquette", [0, -0.12, 1.72], 0.5, 0)], note=""),
    "A3": dict(gsm="12 oz", make="Toile coton 12 oz · anses sangle · impression centrale", hot=[("Molécule", [0, -0.06, 0.2], 0.9, 0)], note=""),
    "A4": dict(gsm="—", make="Écusson twill bordure merrow 80 mm · thermocollant", hot=[("Écusson", [0, -0.01, 0], 0.25, 0)], note=""),
    "A5": dict(gsm="—", make="Étiquette damas tissé 60 × 12 mm", hot=[("Étiquette", [0, -0.01, 0], 0.15, 0)], note=""),
}

PLACE = {
    "T1": ["Poitrine gauche : mini hélice d’ADN brodée (4 cm)", "Dos : double hélice sérigraphiée 30 cm, appariement A–T / G–C exact", "Dos, sous l’hélice : « ON NAÎT UNIQUE »", "Col : côtes 1x1, piqûre double aiguille"],
    "T2": ["Poitrine : tuiles B · Ac · Sc · I (« BAC SCI ») 40 cm, 4 couleurs", "Poitrine, sous les tuiles : légende mono", "Dos : « 2027 » (zéro-orbite) 32 cm + ligne TÉBOURBA · BAC SCIENCES", "Manche droite : tuile Sc brodée"],
    "T3": ["Poitrine : caféine C₈H₁₀N₄O₂ 30 cm + formule et M = 194,19 g·mol⁻¹", "Dos : carré de Punnett Aa × Aa (1 : 2 : 1 ; 3 : 1)"],
    "H1": ["Poitrine gauche : écusson tissé « Sceau Surus » 7 cm", "Empiècement et zip métal, cordons", "Manche gauche : script « Bac Sciences » + 2027 brodés", "Dos : tuiles B·Ac·Sc·I brodées + coordonnées 36°50′N 9°50′E", "Capuche : devise TRAVERSER L’INCONNU / عبور المجهول", "Ourlet : étiquette tissée BAC SCIENCES 2027"],
    "H2": ["Poitrine gauche : wordmark HΛNNIBΛL brodé", "Poche kangourou piquée", "Dos : collage sérigraphié (SCIENCES, ADN, Surus, علوم, 2027, badges)", "Manche gauche : 2027 · manche droite : HΛNNIBΛL", "Ourlet : étiquette tissée"],
    "H3": ["Poitrine gauche : mini écusson brodé", "Dos : impression cosmique 40 cm (spirale, orbites, E = mc²)", "Manches : bande d’orbites répétées", "Ourlet : étiquette tissée violette"],
    "J1": ["Poitrine gauche : « H » chenille sur feutre", "Manche gauche : patch « 2027 » · manche droite : écusson Surus", "Dos : SCIENCES brodé en arc + écusson + coordonnées", "Côtes à deux filets, pressions métal"],
    "J2": ["Poitrine gauche : wordmark brodé", "Dos : molécule de caféine imprimée + formule", "Pressions, col montant, ourlet élastiqué"],
    "V1": ["Poitrine gauche : écusson tissé", "Dos : SCIENCES en arc, Surus, 2027", "Côtes à deux filets, pressions"],
    "V2": ["Matelassage horizontal (baffles 8 cm)", "Dos : motif orbite ton sur ton + wordmark", "Poitrine gauche : étiquette tissée"],
    "S1": ["Motif orbite répété sur toute la longueur", "Bouts chalk : « BAC SCIENCES 2027 » + filets"],
    "S2": ["Bordure typographique : TÉBOURBA · BAC SCIENCES · 2027 · LYCÉE HANNIBAL", "Filets de bout + monogramme Orbite-Λ"],
    "A1": ["Devant : monogramme Orbite-Λ brodé", "Arrière : « 2027 » brodé", "6 panneaux, œillets"],
    "A2": ["Revers : étiquette tissée BAC 2027", "Maille côtelée"],
    "A3": ["Face : molécule de caféine + formule", "Dos : écusson Surus"],
    "A4": ["Écusson brodé 80 mm, bordure merrow"],
    "A5": ["Étiquette tissée BAC SCIENCES 2027, 60 × 12 mm"],
}
