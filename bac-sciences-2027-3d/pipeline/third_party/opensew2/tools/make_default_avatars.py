# Build the two bundled fitting avatars from CC0 data:
#
#   clothing_design/assets/default_character.blend  (Nora, the female figure)
#   clothing_design/assets/default_man.blend        (Theo, the male figure)
#
#   blender -b --python tools/make_default_avatars.py
#
# The bodies are generated with MPFB2 (the MakeHuman plugin for Blender,
# https://static.makehumancommunity.org/mpfb.html). MPFB2's code is GPL, but
# its mesh data - base mesh, targets, skeletons, weights - is CC0, and the
# characters it produces are CC0 as well, so the resulting .blend files can be
# redistributed with the add-on without any third-party license attached.
#
# Each avatar is a single mesh with a Mixamo-named rig (which the measuring
# code in avatar.py already understands): macro targets baked down, MakeHuman
# helper geometry deleted, only the rig's own weight groups kept, plain
# untextured materials, arms posed 60 degrees out from the body (garments
# drape noticeably cleaner that way) and the feet on the floor.
import bpy, bmesh, os, sys, math
from mathutils import Vector, Matrix

for mod in ("bl_ext.user_default.mpfb", "bl_ext.blender_org.mpfb", "mpfb"):
    try:
        bpy.ops.preferences.addon_enable(module=mod)
        HumanService = __import__(mod + ".services.humanservice",
                                  fromlist=["HumanService"]).HumanService
        TargetService = __import__(mod + ".services.targetservice",
                                   fromlist=["TargetService"]).TargetService
        LocationService = __import__(mod + ".services.locationservice",
                                     fromlist=["LocationService"]).LocationService
        break
    except Exception:
        HumanService = None
if HumanService is None:
    print("MPFB2 is not installed in this Blender. Install the 'MPFB' extension first:")
    print("  blender --command extension install-file -r user_default -e mpfb.zip")
    sys.exit(1)

ASSETS = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                      "clothing_design", "assets")
ARM_ANGLE = 60.0     # degrees out from straight down

FIGURES = {
    'WOMAN': {
        "file": "default_character.blend", "prefix": "CD_Woman",
        # Deliberately an ordinary figure, not an idealised mannequin: the
        # add-on has to dress any body, so the one it ships with should not
        # be the easiest possible case. Slimming it was tried as a way of
        # making garments sit better and rejected - it hid drafting faults
        # instead of fixing them.
        "macro": {"gender": 0.0, "age": 0.5, "muscle": 0.5, "weight": 0.5,
                  "proportions": 0.55, "height": 0.52, "cupsize": 0.55, "firmness": 0.6,
                  "race": {"asian": 0.33, "caucasian": 0.33, "african": 0.33}},
        # a fitting avatar is a dress form: square the shoulders a little, or
        # an open jacket has nothing to hang from and slides down the arms
        "details": [("torso/measure-shoulder-dist-incr.target.gz", 0.35),
                    ("arms/l-upperarm-shoulder-muscle-incr.target.gz", 0.25),
                    ("arms/r-upperarm-shoulder-muscle-incr.target.gz", 0.25)],
    },
    'MAN': {
        "file": "default_man.blend", "prefix": "CD_Man",
        "macro": {"gender": 1.0, "age": 0.5, "muscle": 0.5, "weight": 0.45,
                  "proportions": 0.55, "height": 0.6, "cupsize": 0.5, "firmness": 0.5,
                  "race": {"asian": 0.33, "caucasian": 0.33, "african": 0.33}},
    },
}


def plain(name, rgb, rough=0.55):
    mat = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    mat.use_nodes = True
    nt = mat.node_tree
    nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    bsdf = nt.nodes.new("ShaderNodeBsdfPrincipled")
    bsdf.inputs["Base Color"].default_value = (*rgb, 1.0)
    bsdf.inputs["Roughness"].default_value = rough
    nt.links.new(bsdf.outputs[0], out.inputs[0])
    return mat


def activate(ob):
    bpy.ops.object.select_all(action='DESELECT')
    ob.select_set(True)
    bpy.context.view_layer.objects.active = ob


def bake_shape_keys(body):
    activate(body)
    if body.data.shape_keys:
        bpy.ops.object.shape_key_remove(all=True, apply_mix=True)


def delete_helpers(body):
    """MakeHuman's helper and joint-cube geometry is only needed while fitting
    the rig; everything that is not in the 'body' group goes."""
    gi = body.vertex_groups["body"].index
    bm = bmesh.new()
    bm.from_mesh(body.data)
    dl = bm.verts.layers.deform.verify()
    kill = [v for v in bm.verts if v[dl].get(gi, 0.0) <= 0.0]
    bmesh.ops.delete(bm, geom=kill, context='VERTS')
    bm.to_mesh(body.data)
    bm.free()


def prune_groups(body):
    """Keep only the rig's weight groups. avatar.py masks arms and head by the
    dominant vertex group per vertex; a stray full-weight 'body' group would
    win everywhere and break that."""
    for g in list(body.vertex_groups):
        if not g.name.lower().startswith("mixamorig"):
            body.vertex_groups.remove(g)


def arm_out_angle(rig, side):
    a = rig.pose.bones["mixamorig:%sArm" % side]
    f = rig.pose.bones["mixamorig:%sForeArm" % side]
    d = (rig.matrix_world @ f.head - rig.matrix_world @ a.head).normalized()
    return math.degrees(math.acos(max(-1.0, min(1.0, -d.z))))


def rotate_pose_world(rig, pb, axis, angle):
    mw = rig.matrix_world
    pmw = mw @ pb.matrix
    t = Matrix.Translation(pmw.to_translation())
    pb.matrix = mw.inverted() @ (t @ Matrix.Rotation(angle, 4, axis) @ t.inverted() @ pmw)


def pose_arms_out(body, rig):
    """Abduct the upper arms to ARM_ANGLE from vertical and make that the rest
    pose. The rotation runs about the body's forward axis, so the arms travel
    in the frontal plane whichever way the character faces."""
    changed = False
    for side, sign in (("Left", 1.0), ("Right", -1.0)):
        cur = arm_out_angle(rig, side)
        delta = math.radians(ARM_ANGLE - cur)
        if abs(delta) < math.radians(2.0):
            continue
        pb = rig.pose.bones["mixamorig:%sArm" % side]
        rotate_pose_world(rig, pb, Vector((0, 1, 0)), sign * delta)
        bpy.context.view_layer.update()
        # sign flips if the character faces +Y instead of -Y: retry mirrored
        if abs(arm_out_angle(rig, side) - ARM_ANGLE) > 2.0:
            rotate_pose_world(rig, pb, Vector((0, 1, 0)), -2.0 * sign * delta)
            bpy.context.view_layer.update()
        changed = True
    if not changed:
        return
    activate(body)
    mod = next(m for m in body.modifiers if m.type == 'ARMATURE')
    bpy.ops.object.modifier_apply(modifier=mod.name)
    mod = body.modifiers.new("Armature", 'ARMATURE')
    mod.object = rig
    activate(rig)
    bpy.ops.object.mode_set(mode='POSE')
    bpy.ops.pose.armature_apply(selected=False)
    bpy.ops.object.mode_set(mode='OBJECT')


def feet_on_floor(body, rig):
    dg = bpy.context.evaluated_depsgraph_get()
    ev = body.evaluated_get(dg)
    zmin = min((ev.matrix_world @ v.co).z for v in ev.data.vertices)
    rig.location.z -= zmin
    print("  floor shift %.4f m" % -zmin)


def clean_scene(keep):
    scene = bpy.context.scene
    for ob in list(bpy.data.objects):
        if ob not in keep:
            bpy.data.objects.remove(ob, do_unlink=True)
    for c in list(bpy.data.collections):
        bpy.data.collections.remove(c)
    coll = bpy.data.collections.new("Collection")
    scene.collection.children.link(coll)
    for ob in bpy.data.objects:
        for c in ob.users_collection:
            c.objects.unlink(ob)
        coll.objects.link(ob)
    for block in (bpy.data.images, bpy.data.actions, bpy.data.cameras, bpy.data.lights,
                  bpy.data.node_groups, bpy.data.worlds, bpy.data.texts):
        for x in list(block):
            try:
                block.remove(x)
            except Exception:
                pass
    for _ in range(4):
        bpy.data.orphans_purge(do_recursive=True)


def build(figure, spec):
    print("== %s -> %s" % (figure, spec["file"]))
    bpy.ops.wm.read_homefile(use_empty=True)

    body = HumanService.create_human(mask_helpers=False, detailed_helpers=True,
                                     extra_vertex_groups=True, feet_on_ground=True,
                                     scale=0.1, macro_detail_dict=dict(spec["macro"]))
    targets_dir = LocationService.get_mpfb_data("targets")
    for rel, w in spec.get("details", []):
        TargetService.load_target(body, os.path.join(targets_dir, rel), weight=w, name=rel)
    rig = HumanService.add_builtin_rig(body, "mixamo", import_weights=True)

    bake_shape_keys(body)
    delete_helpers(body)
    prune_groups(body)
    pose_arms_out(body, rig)
    feet_on_floor(body, rig)

    body.data.materials.clear()
    body.data.materials.append(plain("CD_Avatar_Skin", (0.62, 0.47, 0.38)))

    prefix = spec["prefix"]
    body.name = body.data.name = prefix + "_Body"
    rig.name = rig.data.name = prefix + "_Rig"
    for holder in (body, body.data, rig, rig.data):
        for k in list(holder.keys()):
            del holder[k]
    body["cd_figure"] = figure
    # provenance travels inside the file
    body["license"] = "CC0-1.0"
    body["source"] = ("Generated with MPFB2 (MakeHuman) from the MakeHuman "
                      "community's CC0 base mesh and targets; "
                      "see tools/make_default_avatars.py")

    clean_scene({body, rig})

    out = os.path.join(ASSETS, spec["file"])
    bpy.ops.wm.save_as_mainfile(filepath=out, compress=True, copy=True)
    print("  wrote %s (%d KB, %d verts)" % (out, os.path.getsize(out) // 1024,
                                            len(body.data.vertices)))


for figure, spec in FIGURES.items():
    build(figure, spec)
print("done")
