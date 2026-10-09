"""Render a produced scene (.blend from produce.py) with the texture set of one colourway.
env: SRC scene blend; TEX texture dir; CW colourway; VIEWS=front,back,q,side,...; W,H,SAMPLES; OUTP prefix;
     FOCUS DIST LENS KEY BG  ;  CAMX/CAMZ pan for close-ups; SLEEVE_TEX etc via tex naming <cw>_<piece>_*.png"""
import os, sys, json, bpy, math
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import garment_lib as gl, materials, studio
E = os.environ.get
bpy.ops.wm.open_mainfile(filepath=E("SRC"))
gl.attach()
sc = bpy.context.scene
tex, cw = E("TEX"), E("CW", "rose")
def mats_for(name, prefix, micro):
    return materials.atlas_material(name, f"{tex}/{prefix}_albedo.png", f"{tex}/{prefix}_normal.png", f"{tex}/{prefix}_orm.png",
                                    micro=micro, normal_strength=float(E("NSTR", "1.0")), sheen=float(E("SHEEN", "0.45")))
import os
for o in bpy.data.objects:
    if "gl_texkey" in o.keys():
        key = cw + o["gl_texkey"]
        if os.path.exists(f"{tex}/{key}_albedo.png"):
            micro = o.get("gl_micro", "fleece")
            if o.get("gl_micro") == "none" or micro == "":
                micro = None
            materials.apply_all(o, mats_for("m_" + o.name, key, micro))
for o in bpy.data.objects:
    if o.name in ("CD_Man_Body",):
        o.hide_render = True
for o in bpy.data.objects:
    if E("HIDE") and o.name.startswith(tuple(E("HIDE").split(","))):
        o.hide_render = True
W, H = int(E("W", 1080)), int(E("H", 1620))
studio.render_settings(W, H, samples=int(E("SAMPLES", 48)), threads=4)
views = {"front": 0, "q": 38, "side": 90, "back": 180, "q2": -38, "backq": 142}
for name in E("VIEWS", "front,back").split(","):
    for o in [o for o in sc.objects if o.name.startswith(("StudioRig", "cyclorama", "key", "fill", "rim", "top", "cam"))]:
        bpy.data.objects.remove(o)
    bg = tuple(float(x) for x in E("BG", "0.50,0.49,0.48").split(","))
    studio.studio(focus_z=float(E("FOCUS", "1.12")), cam_dist=float(E("DIST", "4.4")), lens=float(E("LENS", "85")), yaw_deg=views.get(name, 0),
                  key=float(E("KEY", "0.55")), bg=bg)
    studio.render(f"{E('OUTP', '/home/user/work/prev/item')}_{name}.png")
print("done")
