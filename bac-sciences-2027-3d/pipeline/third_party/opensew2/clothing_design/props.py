# Clothing Design - property definitions
import bpy
from bpy.props import (StringProperty, BoolProperty, FloatProperty, IntProperty,
                       EnumProperty, PointerProperty, CollectionProperty,
                       FloatVectorProperty)
from bpy.types import PropertyGroup, AddonPreferences

ANCHORS = [
    ('TORSO_FRONT', "Torso Front",  "Wrap on the front of the torso"),
    ('TORSO_BACK',  "Torso Back",   "Wrap on the back of the torso"),
    ('TORSO_LEFT',  "Torso Left",   "Wrap on the character's left side"),
    ('TORSO_RIGHT', "Torso Right",  "Wrap on the character's right side"),
    ('HIP_FRONT',   "Hip Front",    "Wrap on the front of the hips"),
    ('HIP_BACK',    "Hip Back",     "Wrap on the back of the hips"),
    ('ARM_L',       "Arm Left",     "Wrap around the left upper arm"),
    ('ARM_R',       "Arm Right",    "Wrap around the right upper arm"),
    ('LEG_L',       "Leg Left",     "Wrap around the left leg"),
    ('LEG_R',       "Leg Right",    "Wrap around the right leg"),
    ('FREE',        "Free",         "Use the object's own transform"),
]

FACING = [
    ('-Y', "-Y (default)", "Character faces -Y"),
    ('+Y', "+Y", "Character faces +Y"),
    ('-X', "-X", "Character faces -X"),
    ('+X', "+X", "Character faces +X"),
]

FIGURES = [
    ('AUTO',  "Auto",  "Tell man from woman by the measured proportions"),
    ('WOMAN', "Woman", "Draft women's blocks: shaped side seams, hem from the hip, "
                       "deeper neckline, sloped shoulder"),
    ('MAN',   "Man",   "Draft men's blocks: straight side seams, wider shoulder, "
                       "longer body, lower trouser rise"),
]


_MUTE = 0


class muted:
    """Suppress live re-sync while a batch of properties is being set."""
    def __enter__(self):
        global _MUTE
        _MUTE += 1
        return self

    def __exit__(self, *a):
        global _MUTE
        _MUTE -= 1
        return False


FABRICS = [
    ('CRISP', "Crisp / Tailored", "Holds its shape: fewer, larger folds"),
    ('SOFT',  "Soft / Jersey",    "Clings closely with fine folds"),
    ('STIFF', "Stiff / Denim",    "Very firm, broad folds"),
    ('LIGHT', "Light / Silk",     "Fluid, lots of fine folds"),
]

FABRIC_VALUES = {
    'CRISP': dict(tension=20.0, compress=120.0, shear=8.0,  bend=25.0,
                  quality=12, damping=1.6, mass=0.28, shrink=0.05),
    'SOFT':  dict(tension=15.0, compress=15.0,  shear=5.0,  bend=0.5,
                  quality=7,  damping=1.0, mass=0.30, shrink=0.0),
    'STIFF': dict(tension=25.0, compress=200.0, shear=15.0, bend=60.0,
                  quality=14, damping=1.8, mass=0.45, shrink=0.03),
    'LIGHT': dict(tension=12.0, compress=8.0,   shear=3.0,  bend=0.15,
                  quality=8,  damping=1.0, mass=0.15, shrink=0.0),
}


def _apply_fabric(self, context):
    v = FABRIC_VALUES.get(self.fabric)
    if not v:
        return
    global _MUTE
    _MUTE += 1
    try:
        self.stiff_tension = v["tension"]
        self.stiff_compress = v["compress"]
        self.stiff_shear = v["shear"]
        self.stiff_bend = v["bend"]
        self.quality = v["quality"]
        self.air_damping = v["damping"]
        self.mass = v["mass"]
        self.shrink = v["shrink"]
    finally:
        _MUTE -= 1


def _pick_garment(self, context):
    """Follow the garment list selection: everything else works on this one."""
    try:
        ob = bpy.data.objects[self.active_garment]
    except Exception:
        return
    if ob and ob.cd.is_garment:
        self.garment_name = ob.cd.garment


def _resync(self, context):
    """Live-update the 3D garment when an arrangement value changes."""
    if _MUTE or context.scene is None or not context.scene.cd.live_sync:
        return
    try:
        from . import build
        build.sync_garment(context, report=None)
    except Exception as e:
        print("[clothing_design] live sync failed:", e)


class CDSeam(PropertyGroup):
    """One sewing relationship between a segment of piece A and a segment of piece B."""
    name:   StringProperty(default="Seam")
    obj_a:  PointerProperty(type=bpy.types.Object)
    seg_a:  StringProperty(default="")
    obj_b:  PointerProperty(type=bpy.types.Object)
    seg_b:  StringProperty(default="")
    flip:   BoolProperty(default=False, description="Reverse the pairing direction",
                         update=_resync)
    auto_flip: BoolProperty(default=True, name="Auto Direction",
                            description="Work the stitch direction out from the arrangement. "
                                        "Turn off to use the Flip setting as given")
    enabled: BoolProperty(default=True, update=_resync)


def apply_piece_scale(ob):
    """Mirror a piece's Width/Length and its garment's Size into the object
    scale, so the 2D view shows the size the 3D garment is built at. The
    builder reads the object scale, so scaling a piece with S in the 2D view
    and pressing Sync does the same thing by hand."""
    import bpy as _bpy
    size = 1.0
    g = _bpy.data.objects.get("CD_Garment_" + ob.cd.garment)
    if g is not None and g.cd.is_garment:
        size = g.cd.size
    ob.scale = (ob.cd.scale_w * size, 1.0, ob.cd.scale_l * size)


def _rescale_piece(self, context):
    apply_piece_scale(self.id_data)
    _resync(self, context)


def _rescale_garment(self, context):
    g = self.id_data
    for ob in context.scene.objects:
        if ob.cd.is_pattern and ob.cd.garment == g.cd.garment:
            apply_piece_scale(ob)
    if _MUTE or not context.scene.cd.live_sync:
        return
    try:
        from . import build
        build.sync_garment(context, report=None, garment=g.cd.garment)
    except Exception as e:
        print("[clothing_design] live sync failed:", e)


class CDObject(PropertyGroup):
    """Lives on every Object. Marks pattern pieces and the generated garment."""
    is_pattern: BoolProperty(default=False)
    is_garment: BoolProperty(default=False)
    layer:      IntProperty(name="Layer", default=0, min=0, max=16,
                            description="Layering order. A garment collides with the body and "
                                        "with every garment on a lower layer, so 0 is worn "
                                        "innermost")
    garment:    StringProperty(default="Garment")
    anchor:     EnumProperty(items=ANCHORS, default='TORSO_FRONT', update=_resync)
    height:     FloatProperty(name="Height", default=0.5, min=-0.5, max=1.5,
                              description="Placement of the piece's centre. On the torso: "
                                          "0 = floor, 1 = top of head. On an arm or leg: "
                                          "fraction of the way down the limb",
                              update=_resync)
    taper:      FloatProperty(name="Taper", default=0.0, min=0.0, max=1.0,
                              description="On a limb: 0 wraps at a constant angle (right for a "
                                          "sleeve), 1 follows the local radius (right for a "
                                          "trouser leg, whose pattern already tapers)",
                              update=_resync)
    wrap:       FloatProperty(name="Wrap", default=1.0, min=0.0, max=2.0,
                              description="0 = flat plate, 1 = wrapped around the body",
                              update=_resync)
    ease:       FloatProperty(name="Ease", default=0.02, min=0.0, max=0.5, unit='LENGTH',
                              description="Distance held off the body surface",
                              update=_resync)
    scale_w:    FloatProperty(name="Width", default=1.0, min=0.2, max=4.0, precision=3,
                              description="Scale the piece across the pattern (its X). "
                                          "1 = as drafted or drawn",
                              update=_rescale_piece)
    scale_l:    FloatProperty(name="Length", default=1.0, min=0.2, max=4.0, precision=3,
                              description="Scale the piece along the pattern (its Y). "
                                          "1 = as drafted or drawn",
                              update=_rescale_piece)
    size:       FloatProperty(name="Size", default=1.0, min=0.2, max=4.0, precision=3,
                              description="Scale every piece of this garment together, so "
                                          "seams keep matching. 1 = as drafted",
                              update=_rescale_garment)
    spin:       FloatProperty(name="Spin", default=0.0, min=-3.15, max=3.15, unit='ROTATION',
                              description="Rotate the piece around the body axis",
                              update=_resync)
    shift:      FloatVectorProperty(name="Shift", size=3, default=(0, 0, 0), subtype='TRANSLATION',
                                    description="Extra world-space offset", update=_resync)
    seg_order:  StringProperty(default="")   # comma separated segment names, creation order


class CDScene(PropertyGroup):
    avatar: PointerProperty(
        type=bpy.types.Object, name="Avatar",
        description="Body mesh the garment is fitted to and collides with",
        poll=lambda self, ob: ob.type == 'MESH')
    facing: EnumProperty(items=FACING, name="Facing", default='-Y',
                         description="Which way the character looks")
    figure: EnumProperty(items=FIGURES, name="Figure", default='AUTO',
                         description="Whose blocks to draft. Auto reads it off the "
                                     "measured proportions; override it if the guess is wrong")
    garment_name: StringProperty(name="Garment", default="Garment")
    resolution: FloatProperty(name="Resolution", default=0.018, min=0.004, max=0.20,
                              unit='LENGTH', description="Target edge length of new pattern pieces")
    pattern_gap: FloatProperty(name="2D Gap", default=0.35, min=0.0, unit='LENGTH',
                               description="Spacing between pieces in the 2D pattern area")
    draw_snap:   FloatProperty(name="Snap", default=0.01, min=0.0, max=0.5, unit='LENGTH',
                               description="Grid the Draw Pattern tool snaps to. 0 = off; "
                                           "holding Ctrl while drawing inverts it")
    keep_off_body: BoolProperty(name="Keep Off Body", default=True,
                                description="Push arranged panels out of the body before "
                                            "simulating, so nothing starts inside the mesh")
    live_sync: BoolProperty(name="Live Sync", default=True,
                            description="Rebuild the 3D garment whenever an arrangement value changes")

    seams: CollectionProperty(type=CDSeam)
    active_seam: IntProperty(default=0)
    active_garment: IntProperty(default=0, update=_pick_garment)

    # --- simulation ---
    quality:     IntProperty(name="Quality", default=12, min=1, max=80)
    mass:        FloatProperty(name="Mass", default=0.28, min=0.001)
    sew_force:   FloatProperty(name="Sew Force", default=0.0, min=0.0,
                               description="Max sewing force. 0 = unlimited (pulls seams fully "
                                           "closed; a heavy garment like the dress needs it to "
                                           "seat its shoulders). A cap of 2-5 reduces how far a "
                                           "light top rides up, at the cost of weaker stitching")
    fabric:      EnumProperty(items=FABRICS, name="Fabric", default='CRISP',
                              update=_apply_fabric,
                              description="Sets the stiffness values below")
    shrink:      FloatProperty(name="Take In", default=0.05, min=-0.5, max=0.5,
                               description="Shrinks the fabric onto the body once the seams are "
                                           "welded. Higher is a closer fit; negative eases it out")
    stiff_tension:  FloatProperty(name="Tension", default=20.0, min=0.0)
    stiff_compress: FloatProperty(name="Compression", default=120.0, min=0.0,
                                  description="Resistance to buckling. Low values wrinkle heavily")
    stiff_shear:    FloatProperty(name="Shear", default=8.0, min=0.0)
    stiff_bend:     FloatProperty(name="Bending", default=25.0, min=0.0,
                                  description="Resistance to folding. The strongest control over "
                                              "how many folds appear")
    air_damping:    FloatProperty(name="Damping", default=1.6, min=0.0)
    self_collision: BoolProperty(name="Self Collision", default=True)
    coll_distance:  FloatProperty(name="Collision Dist", default=0.004, min=0.0001, unit='LENGTH')
    stitch_frames:  IntProperty(name="Stitch Frames", default=25, min=1, max=1000,
                                description="Frames spent pulling the seams closed")
    settle_frames:  IntProperty(name="Settle Frames", default=50, min=0, max=2000,
                                description="Frames spent settling after the seams are welded shut")
    stitch_gravity: FloatProperty(name="Stitch Gravity", default=0.15, min=0.0, max=1.0,
                                  description="Gravity while stitching. Low keeps the garment "
                                              "in place while the seams close")
    auto_close:     BoolProperty(name="Weld When Sewn", default=True,
                                 description="Weld the seams once they are closed and carry on "
                                             "simulating as one piece. Sewing springs never stop "
                                             "pulling, so leaving them on wrinkles the fabric")

    # --- finalize ---
    subdiv_levels: IntProperty(name="Subdivision", default=1, min=0, max=4,
                               description="Subdivision surface shown in the viewport. The cloth "
                                           "still solves on the quad cage underneath",
                               update=_resync)
    subdiv_render: IntProperty(name="Render Subdiv", default=2, min=0, max=6,
                               description="Subdivision surface used at render time")
    weld_seams:  BoolProperty(name="Weld Seams", default=True,
                              description="Merge the sewn edges into a single continuous surface")
    weld_dist:   FloatProperty(name="Max Stitch Gap", default=0.045, min=0.0001, unit='LENGTH',
                              description="Stitches still open by more than this are left unwelded and removed")
    thickness:   FloatProperty(name="Thickness", default=0.0015, min=0.0, unit='LENGTH')
    bind_armature: BoolProperty(name="Bind to Armature", default=True,
                                description="Transfer skin weights from the avatar so the garment follows the animation")


class CDPreferences(AddonPreferences):
    bl_idname = __package__

    auto_workspace: BoolProperty(
        name="Add the Clothing Design workspace automatically",
        default=True,
        description="Put the Clothing Design tab in the workspace bar of every file "
                    "you open. Turn this off to add it by hand instead")

    def draw(self, context):
        L = self.layout
        L.prop(self, "auto_workspace")
        row = L.row()
        row.operator("cd.build_workspace", icon='WORKSPACE')
        L.label(text="Workspaces are saved inside each .blend file.", icon='INFO')


CLASSES = (CDSeam, CDObject, CDScene, CDPreferences)


def register():
    for c in CLASSES:
        bpy.utils.register_class(c)
    bpy.types.Scene.cd = PointerProperty(type=CDScene)
    bpy.types.Object.cd = PointerProperty(type=CDObject)


def unregister():
    del bpy.types.Object.cd
    del bpy.types.Scene.cd
    for c in reversed(CLASSES):
        bpy.utils.unregister_class(c)
