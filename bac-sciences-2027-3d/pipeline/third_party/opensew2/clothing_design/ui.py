# Clothing Design - sidebar UI.
import bpy
from bpy.types import Panel, UIList, Menu
from . import avatar, library, build, patterns

CAT = "Clothing"


class CD_UL_seams(UIList):
    def draw_item(self, context, layout, data, item, icon, active_data, active_prop, index):
        row = layout.row(align=True)
        row.prop(item, "enabled", text="", emboss=False,
                 icon='CHECKBOX_HLT' if item.enabled else 'CHECKBOX_DEHLT')
        a = item.obj_a.name.split("_")[-1] if item.obj_a else "?"
        b = item.obj_b.name.split("_")[-1] if item.obj_b else "?"
        row.label(text="%s.%s" % (a, item.seg_a), icon='OUTLINER_DATA_SURFACE')
        row.label(text="", icon='FORWARD')
        row.label(text="%s.%s" % (b, item.seg_b))
        row.prop(item, "flip", text="", icon='ARROW_LEFTRIGHT', emboss=item.flip)

    def filter_items(self, context, data, propname):
        """Show only the active garment's seams."""
        items = getattr(data, propname)
        g = context.scene.cd.garment_name
        flt = []
        for s in items:
            keep = (s.obj_a and s.obj_b and
                    (s.obj_a.cd.garment == g or s.obj_b.cd.garment == g))
            flt.append(self.bitflag_filter_item if keep else 0)
        return flt, []


class CD_UL_garments(UIList):
    """All garments in the scene, innermost layer first."""

    def draw_item(self, context, layout, data, item, icon, active_data, active_prop, index):
        row = layout.row(align=True)
        row.label(text="L%d" % item.cd.layer)
        row.prop(item.cd, "garment", text="", emboss=False)
        from . import build
        n = len(build.loose_edges(item.data)) if item.data else 0
        if n:
            row.label(text="%d open" % n, icon='UNLINKED')
        else:
            row.label(text="sewn", icon='LINKED')

    def filter_items(self, context, data, propname):
        items = getattr(data, propname)
        flt = [0] * len(items)
        keys = []
        for i, ob in enumerate(items):
            if ob.cd.is_garment and ob.data and len(ob.data.vertices):
                flt[i] = self.bitflag_filter_item
            keys.append((ob.cd.layer, ob.name))
        order = [i for i, _ in sorted(enumerate(keys), key=lambda t: t[1])]
        rank = [0] * len(items)
        for pos, i in enumerate(order):
            rank[i] = pos
        return flt, rank


class _Base:
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = CAT


class CD_PT_avatar(_Base, Panel):
    bl_label = "Avatar"
    bl_idname = "CD_PT_avatar"

    def draw(self, context):
        scn = context.scene
        L = self.layout
        row = L.row(align=True)
        row.label(text="Default", icon='OUTLINER_OB_ARMATURE')
        row.operator("cd.import_character", text="Woman").figure = 'WOMAN'
        row.operator("cd.import_character", text="Man").figure = 'MAN'
        col = L.column(align=True)
        col.prop(scn.cd, "avatar", text="")
        row = col.row(align=True)
        row.operator("cd.set_avatar", icon='USER')
        row.operator("cd.measure", text="", icon='FILE_REFRESH')
        L.prop(scn.cd, "facing")
        row = L.row(align=True)
        row.prop(scn.cd, "figure")
        if scn.cd.avatar and scn.cd.figure == 'AUTO':
            row.label(text=avatar.figure(context).title())

        m = None
        if scn.cd.avatar and "cd_measure" in scn:
            try:
                import json
                m = json.loads(scn["cd_measure"])
            except Exception:
                m = None
        if m:
            box = L.box().column(align=True)
            box.label(text="Height  %.0f cm" % (m["height"] * 100))
            for k, lab in (("chest", "Chest"), ("waist", "Waist"), ("hip", "Hip")):
                z = avatar.z_of(m, k)
                box.label(text="%-6s  %.0f cm" % (lab, avatar.girth_at(m, z) * 100))
            if m.get("armature"):
                box.label(text="Rig: %s" % m["armature"], icon='ARMATURE_DATA')


class CD_PT_patterns(_Base, Panel):
    bl_label = "Patterns"
    bl_idname = "CD_PT_patterns"

    def draw(self, context):
        scn = context.scene
        L = self.layout
        row = L.row(align=True)
        row.operator("cd.add_garment", icon='MOD_CLOTH')
        row.operator("cd.add_outfit", text="Outfit", icon='OUTLINER_OB_GROUP_INSTANCE')
        row = L.row(align=True)
        row.operator("cd.draw_pattern", icon='GREASEPENCIL')
        row.operator("cd.counterpart", text="Counterpart", icon='MOD_MIRROR')
        row.prop(scn.cd, "draw_snap", text="")
        L.prop(scn.cd, "garment_name", text="Garment")
        col = L.column(align=True)
        col.prop(scn.cd, "resolution")
        col.prop(scn.cd, "pattern_gap")
        row = L.row(align=True)
        row.prop(scn.cd, "subdiv_levels")
        row.prop(scn.cd, "subdiv_render", text="Render")
        L.operator("cd.sync", icon='SHADERFX')
        row = L.row(align=True)
        row.prop(scn.cd, "live_sync")
        row.prop(scn.cd, "keep_off_body")

        n = len(build.garment_pieces(context))
        g = build.garment_object(context, create=False)
        if n:
            info = "%d piece%s" % (n, "" if n == 1 else "s")
            if g:
                info += "  -  %d sewing springs" % g.get("cd_sewing_edges", 0)
            L.label(text=info, icon='INFO')


class CD_PT_garments(_Base, Panel):
    bl_label = "Garments"
    bl_idname = "CD_PT_garments"

    def draw(self, context):
        import bpy as _bpy
        scn = context.scene
        L = self.layout
        row = L.row()
        row.template_list("CD_UL_garments", "", _bpy.data, "objects",
                          scn.cd, "active_garment", rows=4)
        col = row.column(align=True)
        col.operator("cd.garment_layer", text="", icon='TRIA_UP').direction = 'UP'
        col.operator("cd.garment_layer", text="", icon='TRIA_DOWN').direction = 'DOWN'
        col.separator()
        col.operator("cd.setup_layers", text="", icon='FILE_REFRESH')

        gs = [o for o in scn.objects if o.cd.is_garment and o.data and len(o.data.vertices)]
        if len(gs) > 1:
            L.label(text="Layer 0 is worn innermost", icon='INFO')
        g = build.garment_object(context, create=False)
        if g is not None:
            L.prop(g.cd, "size", text="Size  (%s)" % g.cd.garment)

        col = L.column(align=True)
        row = col.row(align=True)
        row.scale_y = 1.25
        row.operator("cd.sew", text="Sew", icon='LINKED').all_garments = False
        row.operator("cd.unsew", text="Unsew", icon='UNLINKED').all_garments = False
        row = col.row(align=True)
        row.operator("cd.sew", text="Sew All", icon='LINKED').all_garments = True
        row.operator("cd.unsew", text="Unsew All", icon='UNLINKED').all_garments = True


class CD_PT_piece(_Base, Panel):
    bl_label = "Arrangement"
    bl_idname = "CD_PT_piece"

    @classmethod
    def poll(cls, context):
        ob = context.active_object
        return ob is not None and ob.cd.is_pattern

    def draw(self, context):
        ob = context.active_object
        L = self.layout
        L.label(text=ob.name, icon='OUTLINER_OB_SURFACE')
        col = L.column(align=True)
        col.prop(ob.cd, "anchor")
        col.prop(ob.cd, "height", slider=True)
        col.prop(ob.cd, "spin")
        col.prop(ob.cd, "wrap", slider=True)
        if ob.cd.anchor in {'ARM_L', 'ARM_R', 'LEG_L', 'LEG_R'}:
            col.prop(ob.cd, "taper", slider=True)
        col.prop(ob.cd, "ease")
        row = L.row(align=True)
        row.prop(ob.cd, "scale_w")
        row.prop(ob.cd, "scale_l")
        L.prop(ob.cd, "shift")
        segs = patterns.segment_names(ob)
        if segs:
            box = L.box()
            box.label(text="Edges: " + ", ".join(segs), icon='EDGESEL')


class CD_PT_seams(_Base, Panel):
    bl_label = "Seams"
    bl_idname = "CD_PT_seams"

    def draw(self, context):
        scn = context.scene
        L = self.layout
        row = L.row()
        row.template_list("CD_UL_seams", "", scn.cd, "seams", scn.cd, "active_seam", rows=4)
        col = row.column(align=True)
        col.operator("cd.remove_seam", text="", icon='X')
        col.separator()
        col.operator("cd.clear_seams", text="", icon='TRASH')
        row = L.row(align=True)
        row.operator("cd.auto_seam", icon='AUTOMERGE_ON')
        if context.mode == 'EDIT_MESH':
            L.operator("cd.add_seam", icon='EDGESEL')


class CD_PT_sim(_Base, Panel):
    bl_label = "Simulate"
    bl_idname = "CD_PT_sim"

    def draw(self, context):
        scn = context.scene
        L = self.layout
        row = L.row(align=True)
        row.scale_y = 1.4
        row.operator("cd.drape", icon='PLAY')
        row.operator("cd.reset_sim", text="", icon='LOOP_BACK')
        col = L.column(align=True)
        col.prop(scn.cd, "stitch_frames")
        col.prop(scn.cd, "settle_frames")
        col.prop(scn.cd, "stitch_gravity", slider=True)
        col.prop(scn.cd, "auto_close")
        row = L.row(align=True)
        row.operator("cd.close_seams", icon='AUTOMERGE_ON')
        row.operator("cd.settle", icon='FRAME_NEXT')
        row.operator("cd.relax", icon='MOD_CLOTH')
        row = L.row(align=True)
        row.scale_y = 1.2
        row.operator("cd.grab", icon='VIEW_PAN')
        L.operator("cd.setup_sim", icon='PHYSICS')

        box = L.box().column(align=True)
        box.prop(scn.cd, "fabric", text="")
        box.prop(scn.cd, "shrink", slider=True)
        sub = box.column(align=True)
        sub.prop(scn.cd, "stiff_bend")
        sub.prop(scn.cd, "stiff_compress")
        sub.prop(scn.cd, "stiff_tension")
        sub.prop(scn.cd, "stiff_shear")
        sub.prop(scn.cd, "air_damping")
        col = L.column(align=True)
        col.prop(scn.cd, "sew_force")
        col.prop(scn.cd, "quality")
        col.prop(scn.cd, "mass")
        box = L.box().column(align=True)
        box.prop(scn.cd, "self_collision")
        box.prop(scn.cd, "coll_distance")


class CD_PT_finalize(_Base, Panel):
    bl_label = "Finalize"
    bl_idname = "CD_PT_finalize"

    def draw(self, context):
        scn = context.scene
        L = self.layout
        col = L.column(align=True)
        col.prop(scn.cd, "weld_seams")
        sub = col.row()
        sub.enabled = scn.cd.weld_seams
        sub.prop(scn.cd, "weld_dist")
        col.prop(scn.cd, "thickness")
        col.prop(scn.cd, "bind_armature")
        L.operator("cd.finalize", icon='CHECKMARK')

        # Walking the avatar is the last step: a garment that looks right on a
        # still figure can still slide, gape at the armhole or clip through a
        # thigh once the body moves.
        bound = [o for o in scn.objects if o.cd.is_garment
                 and any(m.type == 'ARMATURE' for m in o.modifiers)]
        box = L.box()
        box.label(text="Test On The Move", icon='ARMATURE_DATA')
        row = box.row(align=True)
        row.scale_y = 1.2
        row.operator("cd.animate", icon='PLAY')
        row.operator("cd.rest_pose", text="", icon='LOOP_BACK')
        if not bound:
            box.label(text="Finalize with Bind To Armature first", icon='INFO')


class CD_PT_workspace(_Base, Panel):
    bl_label = "Workspace"
    bl_idname = "CD_PT_workspace"
    bl_options = {'DEFAULT_CLOSED'}

    def draw(self, context):
        L = self.layout
        if bpy.data.workspaces.get("Clothing Design"):
            L.label(text="Workspace tab is present", icon='CHECKMARK')
        L.operator("cd.build_workspace", icon='WORKSPACE')
        try:
            prefs = context.preferences.addons[__package__].preferences
            L.prop(prefs, "auto_workspace")
        except Exception:
            pass
        row = L.row(align=True)
        row.operator("cd.frame_view", text="Frame 2D").target = '2D'
        row.operator("cd.frame_view", text="Frame Body").target = '3D'


def _add_menu(self, context):
    self.layout.separator()
    self.layout.operator("cd.add_garment", text="Garment Pattern", icon='MOD_CLOTH')


CLASSES = (CD_UL_seams, CD_UL_garments, CD_PT_avatar, CD_PT_patterns, CD_PT_garments, CD_PT_piece, CD_PT_seams,
           CD_PT_sim, CD_PT_finalize, CD_PT_workspace)


def register():
    for c in CLASSES:
        bpy.utils.register_class(c)
    bpy.types.VIEW3D_MT_add.append(_add_menu)


def unregister():
    bpy.types.VIEW3D_MT_add.remove(_add_menu)
    for c in reversed(CLASSES):
        bpy.utils.unregister_class(c)
