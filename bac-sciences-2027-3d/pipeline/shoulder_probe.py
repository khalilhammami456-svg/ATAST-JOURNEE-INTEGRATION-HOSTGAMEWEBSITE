import bpy, sys, os, collections
from mathutils import Vector
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import garment_lib as gl
bpy.ops.wm.open_mainfile(filepath=os.environ["SRC"])
gl.attach()
g = gl.garment()
me = g.data
names = {vg.index: vg.name for vg in g.vertex_groups}
# per piece: how many verts have x>0.2 and z in 1.44..1.62 (the shoulder cap zone), and their x/z/y ranges
zone = collections.defaultdict(list)
for v in me.vertices:
    p = v.co
    if 0.15 < p.x and 1.40 < p.z < 1.65:
        for gr in v.groups:
            if gr.weight > .5: zone[names[gr.group]].append(p.copy())
for k, ps in zone.items():
    xs = [p.x for p in ps]; ys = [p.y for p in ps]; zs = [p.z for p in ps]
    print(k, len(ps), "x %.2f..%.2f y %.2f..%.2f z %.2f..%.2f" % (min(xs), max(xs), min(ys), max(ys), min(zs), max(zs)))
# body top surface z at several x (y=0 plane slice): max z of body verts with |y|<0.04
body = bpy.data.objects["CD_Man_Body"]
dg = bpy.context.evaluated_depsgraph_get(); ev = body.evaluated_get(dg); bme = ev.to_mesh()
for x0 in (0.10, 0.16, 0.20, 0.24, 0.28, 0.32):
    zs = [v.co.z for v in bme.vertices if abs(v.co.x - x0) < 0.01 and abs(v.co.y) < 0.07]
    print("body shoulder top at x=%.2f: z max %.3f" % (x0, max(zs) if zs else -1))
# garment top at same x
for x0 in (0.10, 0.16, 0.20, 0.24, 0.28, 0.32):
    zs = [v.co.z for v in me.vertices if abs(v.co.x - x0) < 0.01 and abs(v.co.y) < 0.12]
    print("garment top at x=%.2f: z max %.3f" % (x0, max(zs) if zs else -1))
