import os, sys, bpy, bmesh
sys.path.insert(0, ".")
import garment_lib as gl
from mathutils import Vector
gl.boot("MAN"); gl.pose_arms(0.45); gl.cd["avatar"].measure(bpy.context, force=True)
import shell
body = shell.Body()
bm = bmesh.new()
verts = [bm.verts.new(c) for c in body.co]
for f in body.faces:
    try: bm.faces.new([verts[i] for i in f])
    except ValueError: pass
print("all", len(bm.verts), len(bm.faces))
bm.verts.ensure_lookup_table()
bi = bm.verts.layers.int.new("bi")
for v in bm.verts: v[bi] = v.index
drop = [v for v in bm.verts if body.dom[v[bi]].endswith("Head") or "Hand" in body.dom[v[bi]] or "Toe" in body.dom[v[bi]] or body.dom[v[bi]].endswith("Foot") or v.co.z < body.z["crotch"]]
print("drop", len(drop))
bmesh.ops.delete(bm, geom=drop, context='VERTS'); print("after drop", len(bm.verts), len(bm.faces))
shell._cut(bm, Vector((0, 0, 1.535)), Vector((0, 0, 1)), -1); print("after neck cut", len(bm.verts), len(bm.faces))
shell._cut(bm, Vector((0, 0, 1.03)), Vector((0, 0, 1)), +1); print("after crotch cut", len(bm.verts), len(bm.faces))
for side in "LR":
    sh, el, wr = body.arm_axis(side); print(side, [tuple(round(c, 3) for c in p) for p in (sh, el, wr)])
    ax = (wr - el).normalized(); p = el + (wr - el) * 0.97
    shell._cut(bm, p, ax, -1); print("after wrist cut", side, len(bm.verts), len(bm.faces))
