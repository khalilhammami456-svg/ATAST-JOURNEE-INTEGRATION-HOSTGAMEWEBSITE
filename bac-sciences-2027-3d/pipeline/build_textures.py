"""Compose the texture atlases of one item / colourway (system python: fontTools, uharfbuzz, rdkit, scipy).
usage: python3 build_textures.py H1 rose"""
import sys, json
from pathlib import Path
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import designs, designs2, designs3
FN = {"H1": (designs, "h1_shell"), "T1": (designs2, "t1_nuit"), "T2": (designs2, "t2_tableau"), "T3": (designs2, "t3_cafeine"),
      "H2": (designs2, "h2_gris"), "H3": (designs2, "h3_cosmique"), "J1": (designs2, "j1_varsity"), "J2": (designs2, "j2_coach"),
      "V1": (designs2, "v1_gilet"), "V2": (designs2, "v2_couche"),
      "S1": (designs3, "s1_orbite"), "S2": (designs3, "s2_bord"), "A1": (designs3, "a1_cap"), "A2": (designs3, "a2_beanie"),
      "A3": (designs3, "a3_tote"), "A4": (designs3, "a4_patch"), "A5": (designs3, "a5_label")}
item, cw = sys.argv[1], sys.argv[2]
mdir = HERE.parent / "3d" / "models" / item
man = json.load(open(mdir / f"{item}_manifest.json"))
mod, fn = FN[item]
kw = {}
for suffix, arg in (("brim", "brim_man"), ("cuff", "cuff_man")):
    sp = mdir / f"{item}_manifest_{suffix}.json"
    if sp.exists() and item in ("A1", "A2"):
        kw[arg] = json.load(open(sp))
res = getattr(mod, fn)(man, colorway=cw, out=item, **kw)
print(item, cw, res if not isinstance(res, dict) or "files" not in res else res["files"])
hp = mdir / f"{item}_manifest_hood.json"
if hp.exists():
    hood = designs.hood_tex(json.load(open(hp)), colorway=cw, out=item)
    print("hood", hood)
