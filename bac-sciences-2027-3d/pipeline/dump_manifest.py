import os, sys, json, bpy
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import garment_lib as gl
bpy.ops.wm.open_mainfile(filepath=os.environ["SRC"])
gl.attach()
g = gl.garment()
man = json.loads(g["gl_atlas"])
json.dump(man, open(os.environ["OUT"], "w"))
print({k: (round(v["w"], 3), round(v["h"], 3), v.get("flipx")) for k, v in man["pieces"].items()})
print("segments", {k: list(v) for k, v in man["segments"].items()})
