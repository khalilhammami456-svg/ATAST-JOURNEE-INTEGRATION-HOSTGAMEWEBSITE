"""Compose the texture atlases of one item / colourway (system python: needs fontTools, uharfbuzz, rdkit, scipy).
usage: python3 build_textures.py H1 rose"""
import sys, json
from pathlib import Path
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import designs
DESIGN_FN = {"H1": "h1_shell"}
item, cw = sys.argv[1], sys.argv[2]
mdir = HERE.parent / "3d" / "models" / item
man = json.load(open(mdir / f"{item}_manifest.json"))
res = getattr(designs, DESIGN_FN[item])(man, colorway=cw, out=item)
print(res["files"])
hp = mdir / f"{item}_manifest_hood.json"
if hp.exists():
    print(designs.hood_tex(json.load(open(hp)), colorway=cw, out=item))
