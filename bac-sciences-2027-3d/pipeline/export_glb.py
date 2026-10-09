"""Export a produced scene to GLB with a given colourway's textures (downscaled to <=2048 for the web).
env: SRC scene blend, TEX dir, CW colourway, OUT .glb, TEXSIZE=2048"""
import os, sys, bpy
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import garment_lib as gl, materials
from PIL import Image
E = os.environ.get
bpy.ops.wm.open_mainfile(filepath=E("SRC"))
gl.attach()
tex, cw, size = E("TEX"), E("CW", "rose"), int(E("TEXSIZE", 2048))
tmp = os.path.join(os.path.dirname(E("OUT")), "_tex_" + cw)
os.makedirs(tmp, exist_ok=True)
def small(prefix, kind):
    src = f"{tex}/{prefix}_{kind}.png"
    if not os.path.exists(src):
        return None
    im = Image.open(src).convert("RGB")
    if im.width > size:
        im = im.resize((size, size), Image.LANCZOS)
    dst = f"{tmp}/{prefix}_{kind}." + ("jpg" if kind == "albedo" else "png")
    im.save(dst, quality=90) if dst.endswith("jpg") else im.save(dst)
    return dst
g = gl.garment()
materials.apply_all(g, materials.export_material("fabric_" + cw, small(cw, "albedo"), small(cw, "normal"), small(cw, "orm")))
hood = bpy.data.objects.get("CD_Hood")
if hood:
    materials.apply_all(hood, materials.export_material("hood_" + cw, small(cw + "_hood", "albedo"), small(cw + "_hood", "normal"), small(cw + "_hood", "orm")))
for o in bpy.data.objects:
    if o.name == "CD_Man_Body":
        o.hide_set(True); o.hide_render = True
    for m in o.modifiers:
        if m.type == "COLLISION":
            o.modifiers.remove(m)
bpy.ops.object.select_all(action='DESELECT')
for o in bpy.data.objects:
    if o.type in ("MESH", "CURVE") and not o.name.startswith(("CD_Man_Body", "cyclorama")) and o.visible_get():
        o.select_set(True)
bpy.ops.export_scene.gltf(filepath=E("OUT"), export_format='GLB', use_selection=True, export_apply=True, export_image_format='AUTO',
                          export_yup=True, export_texcoords=True, export_normals=True, export_materials='EXPORT')
print("glb", os.path.getsize(E("OUT")) / 1e6, "MB")
