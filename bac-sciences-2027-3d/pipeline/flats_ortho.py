"""Orthographic front / back silhouettes of a produced garment (venv python with bpy).

usage: ITEM=H1 python flats_ortho.py     ->  technical-flats/_work/<ID>_{front,back}_mask.png + <ID>_ortho.json

Only the garment objects (shell, hood, trims) are rendered, flat white on transparent, with an orthographic camera.
The JSON stores the camera mapping (world x,z -> pixel) and projected key lines (collar ring, hem, cuffs, zip) so that
flat_sheet.py (system python) can trace a vector outline and dimension it with numbers taken from the 3D shell.
"""
import os, sys, json, math, bpy
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from mathutils import Vector
ROOT = os.path.abspath(os.path.join(HERE, ".."))
ITEM = os.environ.get("ITEM", "H1")
SIZE = int(os.environ.get("SIZE", 2400))
import garment_lib as gl, shell as shl
gl.boot("MAN"); gl.pose_arms(0.7); gl.cd["avatar"].measure(bpy.context, force=True)
_body = shl.Body()
ARMS = {sd: [list(map(float, v)) for v in _body.arm_axis(sd)] for sd in ("L", "R")}
ZB = {k: float(v) for k, v in _body.z.items()}
bpy.ops.wm.open_mainfile(filepath=os.path.join(ROOT, "3d", "models", ITEM, f"{ITEM}_scene.blend"))
sc = bpy.context.scene
keep = []
for o in sc.objects:
    show = o.type in ("MESH", "CURVE") and (o.name.startswith(("CD_Garment", "CD_Hood", "Zipper", "Snap", "Cord", "CD_Cap", "CD_Beanie", "CD_Scarf", "CD_Tote", "CD_Patch", "CD_Label")))
    o.hide_render = not show
    o.hide_viewport = not show
    if show:
        keep.append(o)
        for md in o.modifiers:
            if md.type == "DISPLACE":
                md.show_render = False; md.show_viewport = False     # flats: no fabric wrinkle noise
# bbox of what is shown (evaluated)
dg = bpy.context.evaluated_depsgraph_get()
mn = Vector((1e9,) * 3); mx = Vector((-1e9,) * 3)
for o in keep:
    ev = o.evaluated_get(dg)
    me = ev.to_mesh()
    for v in me.vertices:
        w = o.matrix_world @ v.co
        mn = Vector((min(mn[i], w[i]) for i in range(3))); mx = Vector((max(mx[i], w[i]) for i in range(3)))
    ev.to_mesh_clear()
cx, cz = (mn.x + mx.x) / 2, (mn.z + mx.z) / 2
span = max(mx.x - mn.x, mx.z - mn.z) * 1.12
sc.render.engine = "CYCLES"
sc.cycles.samples = 4; sc.cycles.use_denoising = False; sc.cycles.device = "CPU"
sc.render.film_transparent = True
em = bpy.data.materials.new("flat_em"); em.use_nodes = True
nt = em.node_tree
for n in list(nt.nodes):
    nt.nodes.remove(n)
e = nt.nodes.new("ShaderNodeEmission"); e.inputs["Color"].default_value = (1, 1, 1, 1); e.inputs["Strength"].default_value = 1.0
oo = nt.nodes.new("ShaderNodeOutputMaterial"); nt.links.new(e.outputs[0], oo.inputs["Surface"])
bpy.context.view_layer.material_override = em
sc.world = None
sc.render.resolution_x = sc.render.resolution_y = SIZE
sc.render.image_settings.file_format = "PNG"; sc.render.image_settings.color_mode = "RGBA"
sc.view_settings.view_transform = "Standard"; sc.view_settings.look = "None"
os.makedirs(os.path.join(ROOT, "technical-flats", "_work"), exist_ok=True)
cam_d = bpy.data.cameras.new("fc"); cam_d.type = "ORTHO"; cam_d.ortho_scale = span; cam_d.clip_start = 0.01; cam_d.clip_end = 50
cam = bpy.data.objects.new("fc", cam_d); sc.collection.objects.link(cam); sc.camera = cam
out = {}
for name, y, rot in (("front", -5.0, (math.pi / 2, 0, 0)), ("back", 5.0, (math.pi / 2, 0, math.pi))):
    cam.location = (cx, y, cz); cam.rotation_euler = rot
    sc.render.filepath = os.path.join(ROOT, "technical-flats", "_work", f"{ITEM}_{name}_mask.png")
    bpy.ops.render.render(write_still=True)
    out[name] = dict(cx=cx, cz=cz, span=span, size=SIZE, flip=(name == "back"))
# projected key lines: open-boundary loops of the shell base mesh (collar / hem / cuffs / armholes)
shell_ob = bpy.data.objects.get("CD_Garment_" + ITEM)
lines = []
if shell_ob is not None:
    import bmesh
    bm = bmesh.new(); bm.from_mesh(shell_ob.data); bm.verts.ensure_lookup_table(); bm.edges.index_update(); bm.verts.index_update()
    for lp in shl.boundary_loops(bm):
        pts = [shell_ob.matrix_world @ v.co for v in lp]
        lines.append([[round(p.x, 4), round(p.y, 4), round(p.z, 4)] for p in pts])
    bm.free()
out["loops"] = lines
out["arms"] = ARMS
out["z"] = ZB
meta = json.load(open(os.path.join(ROOT, "3d", "models", ITEM, f"{ITEM}_manifest.json")))["meta"] if os.path.exists(os.path.join(ROOT, "3d", "models", ITEM, f"{ITEM}_manifest.json")) else {}
out["meta"] = meta
json.dump(out, open(os.path.join(ROOT, "technical-flats", "_work", f"{ITEM}_ortho.json"), "w"))
print("ortho flats", ITEM, "span", round(span, 3))
