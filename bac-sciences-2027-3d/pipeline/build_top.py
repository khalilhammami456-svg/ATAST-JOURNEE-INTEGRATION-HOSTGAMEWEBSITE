"""Build a body-offset shell top and save a .blend for preview.  env knobs: KIND, SLEEVE, ARMS, HEM_Z, ..."""
import os, sys, math, bpy, bmesh
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import garment_lib as gl
E = os.environ.get
gl.boot(E("FIG", "MAN"))
gl.pose_arms(float(E("ARMS", "0.45")))
gl.cd["avatar"].measure(bpy.context, force=True)
import shell
body = shell.Body()
print("z landmarks", {k: round(v, 3) for k, v in body.z.items()})
kind = E("KIND", "hoodie"); sleeve = E("SLEEVE", "long")
bm = shell.extract(body, kind=kind, sleeve=sleeve, cuff_t=float(E("CUFF_T", "0.97")), arm_cut_t=float(E("ARM_CUT", "0.5")), neck_r=float(E("NECK_R", "0")), neck_flare=float(E("NECK_FLARE", "0")))
loops = shell.boundary_loops(bm)
info = [(round(sum(v.co.z for v in l) / len(l), 3), round(sum(v.co.x for v in l) / len(l), 3), len(l)) for l in loops]
print("loops (zmean, xmean, n):", info)
hip = min(loops, key=lambda l: sum(v.co.z for v in l) / len(l))
neck = max(loops, key=lambda l: sum(v.co.z for v in l) / len(l))
from mathutils import Vector
cuffs = [l for l in loops if l is not hip and l is not neck]
hem_z = float(E("HEM_Z", "0.86"))
shell.regularize_ring(hip, iters=6)
rings = shell.extrude_hem(bm, hip, hem_z, steps=8, flare=float(E("FLARE", "0.0")))
shell.regularize_ring(rings[-1], planar_z=hem_z, iters=14)
tags = {"hem": set(), "collar": set(), "cuff": set()}
for k, rg in enumerate(rings):
    if (k / (len(rings) - 1)) >= (1 - float(E("RIB_H", "0.09")) / (rings[0][0].co.z - hem_z + 1e-9)):
        tags["hem"].update(rg)
# collar: stand collar extruded up the neck, slightly narrowing
col = float(E("COLLAR", "0.035"))
shell.regularize_ring(neck, iters=4)
crings = shell.extrude_loop(bm, neck, Vector((0, 0, 1)), col, steps=3, scale=lambda t: 1.0 - 0.06 * t)
shell.regularize_ring(crings[-1], planar_z=sum(v.co.z for v in crings[-1]) / len(crings[-1]), iters=10)
for rg in crings:
    tags["collar"].update(rg)
pin_objs = set(crings[-1]) | set(crings[-2]) | set(neck)
# cuffs: short straight extension (rib) beyond the cut, narrowing
for cl in cuffs:
    ax = (shell.loop_center(cl) - Vector((0, 0, 0)))
    side = 1 if shell.loop_center(cl).x > 0 else -1
    sh, el, wr = body.arm_axis("L" if side > 0 else "R")
    shell.regularize_ring(cl, iters=4)
    shell.extrude_loop(bm, cl, (wr - el).normalized(), float(E("CUFF_EXT", "0.0")), steps=2, scale=lambda t: 1.0) if float(E("CUFF_EXT", "0.0")) > 0 else None
print("rings", len(rings))
shell.smooth_verts(bm, iters=int(E("SMOOTH", "10")), factor=0.5)
z = body.z
ease_torso = [(hem_z, float(E("E_HEM", "0.045"))), (z["hip"], float(E("E_HIP", "0.05"))), (z["waist"], float(E("E_WAIST", "0.06"))),
              (z["chest"], float(E("E_CHEST", "0.065"))), (z["shoulder"], float(E("E_SH", "0.03")))]
ease_arm = [(0.0, float(E("E_ARM0", "0.04"))), (0.35, float(E("E_ARM1", "0.05"))), (0.7, float(E("E_ARM2", "0.05"))), (0.88, float(E("E_ARM3", "0.035"))), (1.0, float(E("E_CUFF", "0.014")))]
shell.ease_offset(bm, body, ease_torso, ease_arm)
# cuff tag: verts within cuff_h of the sleeve end
Lchain = (body.arm_axis("L")[1] - body.arm_axis("L")[0]).length + (body.arm_axis("L")[2] - body.arm_axis("L")[1]).length
for v in bm.verts:
    side_, s_, d_, t_, q_, ax_ = shell.arm_params(body, v.co)
    if d_ < 0.12 and s_ >= Lchain * float(E("CUFF_T", "0.97")) - float(E("CUFF_H", "0.075")):
        tags["cuff"].add(v)
bm.verts.index_update()
tags = {k: {v.index for v in s} for k, s in tags.items()}
pin_ids = {v.index for v in pin_objs}
ob = shell.make_object(bm, "CD_Garment_ShellTop")
man = shell.build_uv(ob, body, vtags=tags)
sh_, el_, wr_ = body.arm_axis("L")
man["meta"] = dict(hem_z=hem_z, neck_z=sum(v.co.z for v in neck) / len(neck), shoulder_z=body.z["shoulder"], chest_z=body.z["chest"],
                   waist_z=body.z["waist"], chain_len=(el_ - sh_).length + (wr_ - el_).length, cuff_t=float(E("CUFF_T", "0.97")), kind=kind, sleeve=sleeve)
ob["gl_atlas"] = __import__("json").dumps(man)
import json as _j
_j.dump(man, open(E("MAN_OUT", "/home/user/work/exp/shell1_manifest.json"), "w"))
print("atlas", {k: (round(v["w"], 3), round(v["h"], 3)) for k, v in man["pieces"].items()}, "px/m", round(man["px_per_m"]))
if E("SETTLE_F"):
    zc, zw = float(E("PIN_Z1", "1.30")), float(E("PIN_Z0", "1.12"))
    ta1, ta0 = float(E("PIN_T1", "0.22")), float(E("PIN_T0", "0.62"))
    def ss(x):
        x = max(0.0, min(1.0, x)); return x * x * (3 - 2 * x)
    pinw = {}
    for v in ob.data.vertices:
        side_, s_, d_, t_, q_, ax_ = shell.arm_params(body, v.co)
        if d_ < 0.12 and t_ > 0.04:
            w = 1.0 - ss((t_ - ta1) / (ta0 - ta1))
        else:
            w = ss((v.co.z - zw) / (zc - zw))
        pinw[v.index] = w
    for i in pin_ids:
        pinw[i] = 1.0
    n = shell.settle(ob, body.ob, pinw, frames=int(E("SETTLE_F")), bending=float(E("BEND", "12")), compression=float(E("COMP", "25")), tension=float(E("TENS", "30")), thickness=float(E("THICK", "0.004")))
    print("settled frames", n)
if E("HOOD"):
    ring_ids = [v.index for v in crings[-1]]
    ring_world = [ob.data.vertices[i].co.copy() for i in ring_ids]
    hood = shell.make_hood_down(ob, ring_world, body.ob, arc_deg=float(E("HOOD_ARC", "215")), L=float(E("HOOD_L", "0.34")), frames=int(E("HOOD_F", "36")), bulge=float(E("HOOD_B", "0.062")))
    print("hood verts", len(hood.data.vertices))
    __import__("json").dump(__import__("json").loads(hood["gl_atlas"]), open(E("MAN_OUT", "/home/user/work/exp/shell1_manifest.json").replace(".json", "_hood.json"), "w"))
print("shell verts", len(ob.data.vertices), "faces", len(ob.data.polygons), "bbox", gl.garment_bbox(ob))
bpy.ops.wm.save_as_mainfile(filepath=E("OUT", "/home/user/work/exp/shell1.blend"))
