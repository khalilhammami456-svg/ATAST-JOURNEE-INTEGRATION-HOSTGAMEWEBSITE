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
for o in bpy.data.objects:
    if "gl_texkey" in o.keys():
        key = cw + o["gl_texkey"]
        if small(key, "albedo"):
            materials.apply_all(o, materials.export_material("m_" + o.name + "_" + cw, small(key, "albedo"), small(key, "normal"), small(key, "orm")))
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
                          export_yup=True, export_texcoords=True, export_normals=True, export_materials='EXPORT', export_extras=True)
print("glb", os.path.getsize(E("OUT")) / 1e6, "MB")
