"""Drive: oversized zip hoodie draft -> pattern UV -> sew -> save.   env knobs below."""
import os, sys, time, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import garment_lib as gl
E = os.environ.get
gl.boot(E("FIG", "MAN"))
if E("ARMS"):
    gl.pose_arms(float(E("ARMS")))
    gl.cd["avatar"].measure(gl.bpy.context, force=True)
import presets_bac as pb
kw = {}
for k in ("extra_len", "sh_ext", "extra_drop", "extra_sh_drop", "cuff_h", "cuff_ratio", "rib_h", "hem_ease", "hood_h_scale", "sleeve_flare", "ring_k", "sleeve_k"):
    if E(k.upper()): kw[k] = float(E(k.upper()))
cfgkw = dict(fabric=E("FABRIC", "CRISP"))
for k, t in (("RES", float), ("STITCH", int), ("SETTLE", int), ("SEW_FORCE", float), ("SHRINK", float), ("QUALITY", int), ("WELD", float)):
    if E(k): cfgkw[{"RES": "resolution", "STITCH": "stitch_frames", "SETTLE": "settle_frames", "SEW_FORCE": "sew_force", "SHRINK": "shrink", "QUALITY": "quality", "WELD": "weld_dist"}[k]] = t(E(k))
gl.cfg(**cfgkw)
for k, attr in (("BEND", "stiff_bend"), ("COMPRESS", "stiff_compress"), ("TENSION", "stiff_tension"), ("MASS", "mass")):
    if E(k): gl.cfg(**{attr: float(E(k))})
t = time.time()
g = gl.draft(pb.preset_hoodie_zip, "ZipHoodie", fit=float(E("FIT", "0.32")), **kw)
print("draft %.1fs verts %d" % (time.time() - t, len(g.data.vertices)))
man = gl.assign_pattern_uv(g)
print("atlas px/m %.0f size %d pieces %s" % (man["px_per_m"], man["size_px"], {k: (round(v["w"], 3), round(v["h"], 3)) for k, v in man["pieces"].items()}))
gl.sew(g)
b = gl.garment_bbox(g)
print("bbox x %.2f..%.2f y %.2f..%.2f z %.2f..%.2f" % b)
import bpy
bpy.ops.wm.save_as_mainfile(filepath=E("OUT", "/home/user/work/exp/zip.blend"))
print("saved")
