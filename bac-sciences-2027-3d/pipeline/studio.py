"""Studio rig + render helpers (bpy).  import studio; studio.setup(...)"""
import bpy, math, os, mathutils
from mathutils import Vector

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
HDRI = os.path.join(ROOT, "3d", "textures", "hdri_studio_pmndrs_cc0.exr")

def clear_scene():
    bpy.ops.wm.read_factory_settings(use_empty=True)

def make_cyclorama(color=(0.82, 0.80, 0.77), width=14.0, depth=3.6, height=6.0, radius=1.4):
    """Seamless floor-to-wall sweep.  Floor at z=0, wall at y=+depth."""
    prof = []
    steps = 24
    prof.append((-8.0, 0.0))
    prof.append((depth - radius, 0.0))
    for i in range(1, steps + 1):
        a = math.pi / 2 * i / steps
        prof.append((depth - radius + radius * math.sin(a), radius - radius * math.cos(a)))
    prof.append((depth, height))
    verts, faces = [], []
    for (y, z) in prof:
        verts.append((-width / 2, y, z)); verts.append((width / 2, y, z))
    for i in range(len(prof) - 1):
        a = 2 * i; faces.append((a, a + 1, a + 3, a + 2))
    me = bpy.data.meshes.new("cyc"); me.from_pydata(verts, [], faces); me.update()
    ob = bpy.data.objects.new("cyclorama", me); bpy.context.scene.collection.objects.link(ob)
    for p in me.polygons: p.use_smooth = True
    mat = bpy.data.materials.new("cyc_mat"); mat.use_nodes = True
    b = mat.node_tree.nodes["Principled BSDF"]; b.inputs["Base Color"].default_value = (*color, 1); b.inputs["Roughness"].default_value = 0.9
    ob.data.materials.append(mat)
    return ob

def area_light(name, loc, target, size, energy, color=(1, 1, 1), shape="RECTANGLE", sy=None):
    l = bpy.data.lights.new(name, "AREA"); l.energy = energy; l.size = size; l.color = color
    if shape == "RECTANGLE": l.shape = "RECTANGLE"; l.size_y = sy or size
    ob = bpy.data.objects.new(name, l); ob.location = loc
    bpy.context.scene.collection.objects.link(ob)
    d = Vector(target) - Vector(loc); ob.rotation_euler = d.to_track_quat("-Z", "Y").to_euler()
    return ob

def set_world(hdri=HDRI, strength=0.35, bg=(0.82, 0.80, 0.77)):
    w = bpy.data.worlds.new("w"); w.use_nodes = True; bpy.context.scene.world = w
    nt = w.node_tree; nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputWorld"); bgn = nt.nodes.new("ShaderNodeBackground"); bgn.inputs["Strength"].default_value = strength
    if os.path.exists(hdri):
        env = nt.nodes.new("ShaderNodeTexEnvironment"); env.image = bpy.data.images.load(hdri)
        nt.links.new(env.outputs["Color"], bgn.inputs["Color"])
    nt.links.new(bgn.outputs["Background"], out.inputs["Surface"])

def camera(loc, target, lens=85, sensor=36):
    cam = bpy.data.cameras.new("cam"); cam.lens = lens; cam.sensor_width = sensor
    ob = bpy.data.objects.new("cam", cam); ob.location = loc
    bpy.context.scene.collection.objects.link(ob); bpy.context.scene.camera = ob
    d = Vector(target) - Vector(loc); ob.rotation_euler = d.to_track_quat("-Z", "Y").to_euler()
    return ob

def render_settings(w=1080, h=1620, samples=64, threads=0, engine="CYCLES", bg=None):
    sc = bpy.context.scene
    sc.render.engine = engine
    sc.cycles.device = "CPU"; sc.cycles.samples = samples; sc.cycles.use_denoising = True
    try: sc.cycles.denoiser = "OPENIMAGEDENOISE"
    except Exception: pass
    sc.cycles.max_bounces = 8; sc.cycles.diffuse_bounces = 3; sc.cycles.glossy_bounces = 4; sc.cycles.transmission_bounces = 2
    sc.cycles.sample_clamp_indirect = 10
    sc.render.resolution_x = w; sc.render.resolution_y = h; sc.render.resolution_percentage = 100
    if threads: sc.render.threads_mode = "FIXED"; sc.render.threads = threads
    sc.render.image_settings.file_format = "PNG"; sc.render.image_settings.color_depth = "8"
    try: sc.view_settings.view_transform = "Khronos PBR Neutral"
    except Exception: sc.view_settings.view_transform = "Standard"
    sc.view_settings.look = "None"

def studio(focus_z=1.0, cam_dist=5.2, lens=85, yaw_deg=0.0, key=1.0, bg=(0.42, 0.41, 0.40), world=0.25):
    """3-point softbox rig + cyclorama parented to one empty so the whole set orbits the
    subject. Subject stands at the origin facing -Y; yaw_deg=0 front, 180 back, 90 = side.
    `key` scales every light (exposure trim)."""
    rig = bpy.data.objects.new("StudioRig", None); bpy.context.scene.collection.objects.link(rig)
    cyc = make_cyclorama(color=bg)
    set_world(strength=world)
    cam = camera((0, -cam_dist, focus_z), (0, 0, focus_z), lens)
    L = [area_light("key", (-2.4, -2.6, 2.7), (0, 0, focus_z), 2.6, 260 * key, (1.0, 0.97, 0.93), sy=2.6),
         area_light("fill", (3.0, -2.4, 1.5), (0, 0, focus_z), 3.2, 90 * key, (0.92, 0.95, 1.0), sy=2.6),
         area_light("rim", (1.2, 2.2, 2.6), (0, 0, focus_z + 0.2), 1.6, 220 * key, (1, 1, 1), sy=1.6),
         area_light("top", (0, -0.2, 3.6), (0, 0, focus_z), 2.6, 110 * key, (1, 1, 1), sy=2.6)]
    for o in [cyc, cam] + L:
        o.parent = rig
    # camera/lights are in the rig's frame; the cyclorama must stay BEHIND the subject
    # relative to the camera: the sweep is defined at +Y, camera at -Y -> consistent.
    rig.rotation_euler = (0, 0, math.radians(yaw_deg))
    bpy.context.view_layer.update()
    return cam

def render(path):
    bpy.context.scene.render.filepath = path
    bpy.ops.render.render(write_still=True)
