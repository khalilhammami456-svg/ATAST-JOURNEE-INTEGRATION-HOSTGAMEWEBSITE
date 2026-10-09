import os, sys, json, bpy
import numpy as np
sys.path.insert(0, ".")
import garment_lib as gl
bpy.ops.wm.open_mainfile(filepath=os.environ["SRC"]); gl.attach()
g = gl.garment(); me = g.data
man = json.loads(g["gl_atlas"]); order = man["order"]; side = man["side_m"]
uvl = me.uv_layers["pattern"]
rows = {n: [] for n in order}
for poly in me.polygons:
    n = order[poly.material_index]
    for li in poly.loop_indices:
        v = me.vertices[me.loops[li].vertex_index].co
        u, vv = uvl.data[li].uv
        rows[n].append((u * side, vv * side, v.x, v.y, v.z))
for n, r in rows.items():
    a = np.array(r)
    cu = lambda col: np.corrcoef(a[:, 0], a[:, col])[0, 1]
    cv = lambda col: np.corrcoef(a[:, 1], a[:, col])[0, 1]
    print(n, "u~x %+.2f u~y %+.2f u~z %+.2f | v~x %+.2f v~y %+.2f v~z %+.2f" % (cu(2), cu(3), cu(4), cv(2), cv(3), cv(4)))
