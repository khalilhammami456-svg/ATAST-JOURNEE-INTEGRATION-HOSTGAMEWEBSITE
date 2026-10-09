"""Parametric sew driver around opensew-2 (headless).
env: PRESET FIG FIT OUT  RES STITCH SETTLE FABRIC SEW_FORCE SHRINK SUBDIV
Prints weld diagnostics (merged/skipped stitch counts) and bbox, saves .blend."""
import bpy, sys, os, time, json
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "third_party", "opensew2"))
bpy.ops.wm.read_homefile(use_empty=True)
bpy.ops.preferences.addon_enable(module="clothing_design")
from clothing_design import avatar, library, build, sim
E = os.environ.get
ctx = bpy.context; scn = ctx.scene
bpy.ops.cd.import_character(figure=E("FIG", "MAN"))
avatar.measure(ctx, force=True)
if E("RES"): scn.cd.resolution = float(E("RES"))
if E("FABRIC"): scn.cd.fabric = E("FABRIC")
if E("STITCH"): scn.cd.stitch_frames = int(E("STITCH"))
if E("SETTLE"): scn.cd.settle_frames = int(E("SETTLE"))
if E("SEW_FORCE"): scn.cd.sew_force = float(E("SEW_FORCE"))
if E("SHRINK"): scn.cd.shrink = float(E("SHRINK"))
if E("WELD"): scn.cd.weld_dist = float(E("WELD"))
_w = sim.weld_seams
def wrapped(ob, gap):
    r = _w(ob, gap); print("WELD merged=%d skipped=%d gap=%.3f" % (r[0], r[1], gap)); return r
sim.weld_seams = wrapped
t = time.time()
bpy.ops.cd.add_garment(preset=E("PRESET", "HOODIE"), fit=float(E("FIT", "0.2")))
print("draft", round(time.time() - t, 1), "s")
t = time.time(); bpy.ops.cd.sew(); print("sew", round(time.time() - t, 1), "s")
g = build.garment_object(ctx, create=False)
import mathutils
bb = [g.matrix_world @ mathutils.Vector(c) for c in g.bound_box]
print("verts", len(g.data.vertices), "bbox z %.2f..%.2f x %.2f..%.2f" % (min(v.z for v in bb), max(v.z for v in bb), min(v.x for v in bb), max(v.x for v in bb)))
print("boundary edges", sum(1 for e in g.data.edges if sum(1 for p in g.data.polygons if e.key in [tuple(sorted(k)) for k in p.edge_keys]) == 1) if False else "")
bpy.ops.wm.save_as_mainfile(filepath=E("OUT", "/home/user/work/sew_out.blend"))
print("saved")
