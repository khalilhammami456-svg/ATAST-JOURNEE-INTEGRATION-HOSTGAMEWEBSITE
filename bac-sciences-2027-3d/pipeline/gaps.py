import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import garment_lib as gl
E = os.environ.get
gl.boot("MAN")
import presets_bac as pb
pb.AUTO_FLIP_CAPS = E('AUTO') == '1'
from clothing_design import library
fn = {"zip": pb.preset_hoodie_zip, "tee": pb.preset_tee_boxy, "vest": pb.preset_vest}.get(E("PRESET", "zip")) or library.PRESETS[E("PRESET").upper()][1]
kw = {}
for k in ("extra_len", "sh_ext", "extra_drop", "extra_sh_drop", "cuff_h", "cuff_ratio", "rib_h", "hem_ease", "hood_h_scale", "sleeve_flare"):
    if E(k.upper()): kw[k] = float(E(k.upper()))
g = gl.draft(fn, "G", fit=float(E("FIT", "0.3")), **kw)
gl.stitch_report(g)
