import bpy, sys, os
from mathutils import Vector
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import garment_lib as gl
bpy.ops.wm.open_mainfile(filepath=os.environ["SRC"])
gl.attach()
sc = bpy.context.scene
dg = bpy.context.evaluated_depsgraph_get()
for (x, z) in ((0.24, 1.52), (0.20, 1.52), (0.30, 1.44), (0.10, 1.50), (-0.24, 1.52)):
    o = Vector((x, -3.0, z)); d = Vector((0, 1, 0))
    hits = []
    cur = o.copy()
    for _ in range(6):
        ok, loc, nrm, idx, ob, mat = sc.ray_cast(dg, cur, d)
        if not ok: break
        hits.append((ob.name[:14], round(loc.y, 4)))
        cur = loc + d * 0.0005
    print("ray x=%.2f z=%.2f ->" % (x, z), hits)
