"""Write viewer/items.json from collection.py (items, colourways, specs, hotspots, default camera views)."""
import json
from pathlib import Path
from collection import ITEMS, SPEC, PLACE
ROOT = Path(__file__).resolve().parent.parent
LABEL = {"nuit": "Nuit", "chalk": "Chalk", "rose": "Rose poudré", "lab": "Gris labo", "maroon": "Bordeaux", "violet": "Violet cosmique",
         "nuit-rose": "Nuit / Rose", "maroon-chalk": "Bordeaux / Chalk"}
VIEWS = {  # target (blender coords), yaw, distance
    "garment": dict(front=dict(target=[0, -0.02, 1.08], yaw=0, dist=4.3), back=dict(target=[0, -0.02, 1.08], yaw=180, dist=4.3), q=dict(target=[0, -0.02, 1.08], yaw=36, dist=4.0)),
    "head": dict(front=dict(target=[0, -0.05, 1.70], yaw=0, dist=1.5), back=dict(target=[0, -0.05, 1.70], yaw=180, dist=1.5), q=dict(target=[0, -0.05, 1.70], yaw=40, dist=1.4)),
    "scarf": dict(front=dict(target=[0, -0.05, 1.35], yaw=0, dist=2.6), back=dict(target=[0, -0.05, 1.35], yaw=180, dist=2.6), q=dict(target=[0, -0.05, 1.35], yaw=36, dist=2.4)),
    "tote": dict(front=dict(target=[0, 0, 0.35], yaw=0, dist=2.0), back=dict(target=[0, 0, 0.35], yaw=180, dist=2.0), q=dict(target=[0, 0, 0.35], yaw=35, dist=1.9)),
    "tiny": dict(front=dict(target=[0, 0, 0], yaw=0, dist=0.35), back=dict(target=[0, 0, 0], yaw=180, dist=0.35), q=dict(target=[0, 0, 0], yaw=30, dist=0.32)),
}
KIND_VIEW = {"tee": "garment", "hoodie": "garment", "jacket": "garment", "vest": "garment", "scarf": "scarf", "cap": "head", "beanie": "head", "tote": "tote", "patch": "tiny", "label": "tiny"}
items = []
for iid, it in ITEMS.items():
    cws = []
    for k, v in it["colorways"].items():
        hexv = v[0] if isinstance(v, (tuple, list)) else v
        cws.append(dict(key=k, label=LABEL.get(k, k), hex=hexv))
    sp = SPEC.get(iid, {})
    items.append(dict(id=iid, name=it["name"], kind=it["kind"], title=it["title"], fabric=it["fabric"], gsm=sp.get("gsm"), make=sp.get("make"),
                      colorways=cws, refs=it.get("refs", []), art=PLACE.get(iid, []), note=sp.get("note", ""),
                      views=VIEWS[KIND_VIEW[it["kind"]]], glb=f"assets/{iid}/{iid}.glb", assets=f"assets/{iid}",
                      hotspots=[dict(label=a, pos=p, dist=d, yaw=y) for a, p, d, y in sp.get("hot", [])]))
(ROOT / "viewer").mkdir(exist_ok=True)
json.dump(dict(items=items), open(ROOT / "viewer" / "items.json", "w"), ensure_ascii=False, indent=1)
print(len(items), "items")
