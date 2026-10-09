import os, sys, bpy
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import garment_lib as gl
m = gl.boot("MAN")
av = gl.cd["avatar"]
print("zmin", m["zmin"], "height", m["height"])
print({k: round(av.z_of(m, k), 3) for k in ("neck", "shoulder", "chest", "waist", "hip", "crotch")})
for k in ("arm_l", "farm_l"):
    lp = m["limbs"][k]; print(k, [round(c, 3) for c in lp["p0"]], [round(c, 3) for c in lp["p1"]], "len", round(lp["len"], 3), "rad_root", lp.get("rad_root"))
import presets_bac as pb
g = gl.draft(pb.preset_hoodie_zip, "G", fit=0.3, cuff_h=0.0)
build = gl.cd["build"]
for p in build.garment_pieces(bpy.context, "G"):
    ws = [p.matrix_world @ v.co for v in p.data.vertices]
    print(p.name, "anchor", p.cd.anchor, "height", round(p.cd.height, 3), "local z range", round(min(v.co.z for v in p.data.vertices), 3), round(max(v.co.z for v in p.data.vertices), 3))
me = g.data
names = {vg.index: vg.name for vg in g.vertex_groups}
import collections
rng = collections.defaultdict(lambda: [9, -9])
for v in me.vertices:
    for gr in v.groups:
        if gr.weight > .5:
            r = rng[names[gr.group]]; r[0] = min(r[0], v.co.z); r[1] = max(r[1], v.co.z)
for k, r in rng.items(): print("garment piece z-range", k, [round(x, 3) for x in r])
