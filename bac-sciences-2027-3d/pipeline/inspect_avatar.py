import os, sys, bpy, collections
sys.path.insert(0, ".")
import garment_lib as gl
m = gl.boot("MAN")
sc = bpy.context.scene
body = sc.cd.avatar
print("body", body.name, len(body.data.vertices), "faces", len(body.data.polygons), "uv", [u.name for u in body.data.uv_layers])
rig = gl.cd["avatar"].find_armature(body)
print("bones", [b.name for b in rig.data.bones])
print("vgroups", [vg.name for vg in body.vertex_groups][:60])
# dominant group counts
names = {vg.index: vg.name for vg in body.vertex_groups}
cnt = collections.Counter()
for v in body.data.vertices:
    if v.groups:
        g = max(v.groups, key=lambda x: x.weight); cnt[names[g.group]] += 1
print(cnt.most_common(50))
print("limbs", {k: [tuple(round(c, 3) for c in v["p0"]), tuple(round(c, 3) for c in v["p1"])] for k, v in m["limbs"].items()})
