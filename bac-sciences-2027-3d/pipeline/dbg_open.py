import os, sys, bpy
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import garment_lib as gl
bpy.ops.wm.open_mainfile(filepath=os.environ["SRC"])
gl.attach()
g = gl.garment(); sc = bpy.context.scene
print("frame", sc.frame_current, "verts", len(g.data.vertices), "loose", len(gl.cd["build"].loose_edges(g.data)))
print("mods", [(m.type, getattr(getattr(m, "point_cache", None), "is_baked", None)) for m in g.modifiers])
for m in g.modifiers:
    if m.type == "CLOTH":
        pc = m.point_cache; print("cache start/end", pc.frame_start, pc.frame_end, "info", pc.info)
def bbox_eval():
    dg = bpy.context.evaluated_depsgraph_get(); ev = g.evaluated_get(dg); me = ev.to_mesh()
    zs = [v.co.z for v in me.vertices]; xs = [v.co.x for v in me.vertices]
    r = (round(min(xs), 2), round(max(xs), 2), round(min(zs), 2), round(max(zs), 2), len(me.vertices)); ev.to_mesh_clear(); return r
print("eval at current", bbox_eval())
sc.frame_set(76); print("eval at 76", bbox_eval())
sc.frame_set(1); print("eval at 1", bbox_eval())
