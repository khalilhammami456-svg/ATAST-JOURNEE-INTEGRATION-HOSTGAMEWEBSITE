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
