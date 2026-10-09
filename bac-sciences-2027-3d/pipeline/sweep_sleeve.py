"""Sweep sleeve placement (cd.height / shift) and report cap-seam gaps on the arranged zip hoodie."""
import os, sys, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import garment_lib as gl
E = os.environ.get
gl.boot("MAN")
import presets_bac as pb
import bpy
kw = {}
for k in ("extra_len", "sh_ext", "extra_drop", "extra_sh_drop", "cuff_h", "cuff_ratio", "rib_h", "hem_ease", "hood_h_scale", "sleeve_flare", "sleeve_total"):
    if E(k.upper()): kw[k] = float(E(k.upper()))
g = gl.draft(pb.preset_hoodie_zip, "G", fit=float(E("FIT", "0.30")), **kw)
build = gl.cd["build"]
pcs = {p.name.split("_", 1)[-1]: p for p in build.garment_pieces(bpy.context, "G")}
print("sleeve height", pcs["Sleeve_L"].cd.height, "ease", pcs["Sleeve_L"].cd.ease)
base = pcs["Sleeve_L"].cd.height
from clothing_design import props
for dh in [float(x) for x in E("DH", "-0.06,-0.03,0,0.03,0.06,0.09").split(",")]:
    with props.muted():
        for s in ("Sleeve_L", "Sleeve_R"):
            pcs[s].cd.height = base + dh
    build.sync_garment(bpy.context, None, "G")
    g = build.garment_object(bpy.context, "G", create=False)
    rep = gl.stitch_report(g, verbose=False)
    cap = [(k, v) for k, v in rep.items() if any("Sleeve" in x for x in k) and any(x.startswith(("Front", "Back")) for x in k)]
    print("dh %+.2f " % dh + "  ".join("%s mean %.3f max %.3f" % ("/".join(k), v[1], v[2]) for k, v in cap))
