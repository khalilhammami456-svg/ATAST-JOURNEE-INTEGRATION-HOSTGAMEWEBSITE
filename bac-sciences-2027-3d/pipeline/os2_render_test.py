import bpy, sys, os, time, math
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "third_party", "opensew2")); sys.path.insert(0, HERE)
src = os.environ.get("SRC", "/home/user/work/os2_hoodie.blend")
bpy.ops.wm.open_mainfile(filepath=src)
bpy.ops.preferences.addon_enable(module="clothing_design")
from clothing_design import build
ctx = bpy.context; scn = ctx.scene
g = build.garment_object(ctx, create=False)
print("garment", g.name, "mods", [m.type for m in g.modifiers], "uv", [u.name for u in g.data.uv_layers], "verts", len(g.data.vertices))
t = time.time()
try:
    r = bpy.ops.cd.finalize(); print("finalize", r, round(time.time() - t, 1), "s")
except Exception as e: print("finalize failed", e)
print("mods after", [m.type for m in g.modifiers], "uv", [(u.name) for u in g.data.uv_layers])
print("objects:", [(o.name, o.type) for o in scn.objects])
# bounding box
import mathutils
bb = [g.matrix_world @ mathutils.Vector(c) for c in g.bound_box]
print("bbox z", round(min(v.z for v in bb), 2), round(max(v.z for v in bb), 2), "x", round(min(v.x for v in bb), 2), round(max(v.x for v in bb), 2))
bpy.ops.wm.save_as_mainfile(filepath="/home/user/work/os2_hoodie_final.blend")
import studio
# materials
mat = bpy.data.materials.new("fleece"); mat.use_nodes = True
b = mat.node_tree.nodes["Principled BSDF"]; b.inputs["Base Color"].default_value = (0.78, 0.55, 0.57, 1); b.inputs["Roughness"].default_value = 0.92
try: b.inputs["Sheen Weight"].default_value = 0.6; b.inputs["Sheen Roughness"].default_value = 0.5
except Exception as e: print("sheen", e)
g.data.materials.clear(); g.data.materials.append(mat)
for p in g.data.polygons: p.use_smooth = True
# studio (keep existing objects)
studio.studio(focus_z=1.05, cam_dist=6.0, lens=85)
body = [o for o in scn.objects if o.name.startswith("CD_") and o.type == "MESH" and o != g]
print("body objs", [o.name for o in body])
studio.render_settings(800, 1100, samples=int(os.environ.get("SAMPLES", "32")), threads=4)
t = time.time(); studio.render(os.environ.get("PNG", "/home/user/work/hoodie_test.png")); print("render s", round(time.time() - t, 1))
