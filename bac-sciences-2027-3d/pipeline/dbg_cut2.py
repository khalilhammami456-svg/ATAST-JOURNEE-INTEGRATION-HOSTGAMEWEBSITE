import os, sys, bpy, collections
sys.path.insert(0, ".")
import garment_lib as gl
gl.boot("MAN"); gl.pose_arms(0.45); gl.cd["avatar"].measure(bpy.context, force=True)
import shell
body = shell.Body()
zs = [c.z for c in body.co]
print("z range", min(zs), max(zs), "n", len(zs))
print(collections.Counter(body.dom).most_common(6))
print("crotch", body.z["crotch"], "less than crotch:", sum(1 for z in zs if z < body.z["crotch"]))
import bmesh
bm = bmesh.new()
verts = [bm.verts.new(c) for c in body.co]
bm.verts.ensure_lookup_table()
bi = bm.verts.layers.int.new("bi")
for v in bm.verts: v[bi] = v.index
print("bi sample", [bm.verts[i][bi] for i in (0, 1, 5000, 13379)])
c = collections.Counter()
for v in bm.verts:
    d = body.dom[v[bi]]
    c["head"] += d.endswith("Head"); c["hand"] += "Hand" in d; c["toe"] += "Toe" in d; c["foot"] += d.endswith("Foot"); c["z"] += v.co.z < body.z["crotch"]
print(c)
