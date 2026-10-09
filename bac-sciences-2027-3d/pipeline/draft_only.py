"""Draft a garment and save the ARRANGED (pre-sim) state for quick inspection.  env: PRESET=zip|hoodie|... plus preset kwargs (upper-case)."""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import garment_lib as gl
E = os.environ.get
gl.boot(E("FIG", "MAN"))
import presets_bac as pb
kw = {}
for k in ("extra_len", "sh_ext", "extra_drop", "extra_sh_drop", "cuff_h", "cuff_ratio", "rib_h", "hem_ease", "hood_h_scale", "sleeve_flare", "sleeve_total"):
    if E(k.upper()): kw[k] = float(E(k.upper()))
fn = {"zip": pb.preset_hoodie_zip}.get(E("PRESET", "zip"))
if fn is None:
    from clothing_design import library
    fn = library.PRESETS[E("PRESET").upper()][1]
g = gl.draft(fn, "G", fit=float(E("FIT", "0.32")), **kw)
import bpy
bpy.ops.wm.save_as_mainfile(filepath=E("OUT", "/home/user/work/exp/draft.blend"))
print("bbox x %.2f..%.2f y %.2f..%.2f z %.2f..%.2f" % gl.garment_bbox(g))
