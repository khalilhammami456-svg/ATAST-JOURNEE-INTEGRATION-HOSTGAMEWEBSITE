"""Fast multi-angle low-res Cycles preview of a .blend (debugging aid).
env: SRC=blend  OUT=prefix  SAMPLES=8  W=420 H=600"""
import bpy, sys, os, math
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import studio
from mathutils import Vector
src = os.environ["SRC"]; out = os.environ.get("OUT", "/home/user/work/prev/v")
bpy.ops.wm.open_mainfile(filepath=src)
sc = bpy.context.scene
for o in list(sc.objects):
    if o.type == "MESH" and (o.name.startswith("CD_Garment") or o.name.startswith("CD_Hood")):
        mat = bpy.data.materials.new("g"); mat.use_nodes = True
        b = mat.node_tree.nodes["Principled BSDF"]; b.inputs["Base Color"].default_value = (0.55, 0.30, 0.34, 1); b.inputs["Roughness"].default_value = 0.9
        o.data.materials.clear(); o.data.materials.append(mat)
        for p in o.data.polygons: p.use_smooth = True
    if o.type == "MESH" and o.name.startswith("CD_Man_Body") or o.name.startswith("CD_Woman_Body"):
        mat = bpy.data.materials.new("skin"); mat.use_nodes = True
        b = mat.node_tree.nodes["Principled BSDF"]; b.inputs["Base Color"].default_value = (0.6, 0.55, 0.5, 1); b.inputs["Roughness"].default_value = 0.8
        o.data.materials.clear(); o.data.materials.append(mat)
    if o.name.startswith(("Hoodie_","Jacket_","Tshirt_","T-Shirt_","Front","Back")) and o.type == "MESH":
        o.hide_render = True
if os.environ.get("HIDE_BODY"):
    for o in sc.objects:
        if o.name.startswith(("CD_Man_Body", "CD_Woman_Body")): o.hide_render = True
if os.environ.get("FRAME") != "keep": sc.frame_set(sc.frame_end)
focus = float(os.environ.get("FOCUS", "1.25"))
studio.render_settings(int(os.environ.get("W", 420)), int(os.environ.get("H", 600)), samples=int(os.environ.get("SAMPLES", 8)), threads=4)
rigs = []
for name, yaw in (("front", 0), ("q", 45), ("side", 90), ("back", 180)):
    for o in [o for o in sc.objects if o.name.startswith(("StudioRig", "cyclorama", "key", "fill", "rim", "top", "cam"))]:
        bpy.data.objects.remove(o)
    studio.studio(focus_z=focus, cam_dist=float(os.environ.get("DIST", "4.2")), lens=85, yaw_deg=yaw, key=float(os.environ.get("KEY", "1")))
    studio.render(f"{out}_{name}.png")
print("done")
