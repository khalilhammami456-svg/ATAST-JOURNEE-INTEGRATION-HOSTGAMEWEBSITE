"""Apply the orientation diagnostic atlas to a sewn garment and render 4 views (checks UV orientation / flips)."""
import os, sys, json, bpy
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import garment_lib as gl, texlab, materials, studio
bpy.ops.wm.open_mainfile(filepath=os.environ["SRC"])
gl.attach()
g = gl.garment()
man = json.loads(g["gl_atlas"])
out = os.environ.get("OUT", "/home/user/work/prev/diag")
png = "/home/user/work/prev/diag_atlas.png"
texlab.diag_atlas(man, png, size=2048)
mat = materials.atlas_material("diag", png, micro=None, sheen=0.0)
materials.apply_all(g, mat)
body = bpy.data.objects.get("CD_Man_Body")
if body: body.hide_render = bool(os.environ.get("HIDE_BODY"))
for o in bpy.data.objects:
    if o.type == "MESH" and o is not g and o is not body and not o.name.startswith("cyclorama"):
        o.hide_render = True
sc = bpy.context.scene
studio.render_settings(int(os.environ.get("W", 700)), int(os.environ.get("H", 700)), samples=8, threads=4)
for name, yaw in (("front", 0), ("back", 180), ("left", -90), ("right", 90)):
    for o in [o for o in sc.objects if o.name.startswith(("StudioRig", "cyclorama", "key", "fill", "rim", "top", "cam"))]:
        bpy.data.objects.remove(o)
    studio.studio(focus_z=float(os.environ.get("FOCUS", "1.3")), cam_dist=float(os.environ.get("DIST", "3.4")), lens=85, yaw_deg=yaw)
    studio.render(f"{out}_{name}.png")
print("done")
