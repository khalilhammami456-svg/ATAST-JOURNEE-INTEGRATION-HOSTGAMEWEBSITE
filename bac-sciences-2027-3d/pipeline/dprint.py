import os, sys, math
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import garment_lib as gl
m = gl.boot("MAN")
import presets_bac as pb
from clothing_design import library as L
for fit in (0.22, 0.32):
    for rk in (1.5, 1.65, 1.85):
        d = pb._draft(m, fit, sh_ext=1.14, extra_drop=0.0, extra_sh_drop=0.02, ring_k=rk)
        print("fit %.2f ring_k %.1f arm_d %.3f scye_x %.3f half %.3f sh_x %.3f armhole %.3f need %.3f" % (fit, rk, d["arm_d"], d["scye_x"], d["half"], d["sh_x"], d["armhole"], d["ring_need"]))
