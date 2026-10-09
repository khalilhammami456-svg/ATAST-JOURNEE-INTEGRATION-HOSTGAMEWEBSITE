import os, sys, json, bpy
sys.path.insert(0, ".")
import garment_lib as gl
bpy.ops.wm.open_mainfile(filepath=os.environ["SRC"]); gl.attach()
g = gl.garment(); man = json.loads(g["gl_atlas"])
polys = man["polys"]["Front"]
big = [(max(abs(p[0]) for p in pl), pl) for pl in polys]
big.sort(key=lambda t: -t[0])
print("front polys", len(polys), "max |u|", [round(b[0], 3) for b in big[:8]])
# where are those faces in world space?
me = g.data; order = man["order"]
fi = order.index("Front")
rows = []
uvl = me.uv_layers["pattern"]; side = man["side_m"]
cnt = 0
for poly in me.polygons:
    if poly.material_index != fi: continue
    c = poly.center
    pl = polys[cnt]; cnt += 1
    m = max(abs(p[0]) for p in pl)
    if m > 0.33: rows.append((round(m, 3), round(c.x, 3), round(c.y, 3), round(c.z, 3)))
print(rows[:12], len(rows))
