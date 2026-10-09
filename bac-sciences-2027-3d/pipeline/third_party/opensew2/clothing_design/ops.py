# Clothing Design - operators.
import bpy, bmesh, math, json, os
from bpy.props import (StringProperty, BoolProperty, FloatProperty, IntProperty,
                       EnumProperty, FloatVectorProperty)
from bpy.types import Operator
from mathutils import Vector
from mathutils.geometry import intersect_line_plane

from . import avatar, patterns, library, build, sim, workspace, props

AVATAR_COLL = "CD_Avatar"

COUNTERPART = {
    'TORSO_FRONT': 'TORSO_BACK', 'TORSO_BACK': 'TORSO_FRONT',
    'TORSO_LEFT': 'TORSO_RIGHT', 'TORSO_RIGHT': 'TORSO_LEFT',
    'HIP_FRONT': 'HIP_BACK', 'HIP_BACK': 'HIP_FRONT',
    'ARM_L': 'ARM_R', 'ARM_R': 'ARM_L',
    'LEG_L': 'LEG_R', 'LEG_R': 'LEG_L',
}


def drop_seams_for(scn, garment):
    """Remove only this garment's seams. The seam list is shared by the whole
    scene, so clearing it wholesale wipes every other garment's stitching and
    leaves them impossible to re-sew."""
    for i in range(len(scn.cd.seams) - 1, -1, -1):
        s = scn.cd.seams[i]
        a, b = s.obj_a, s.obj_b
        if a is None or b is None:
            scn.cd.seams.remove(i)
        elif a.cd.garment == garment or b.cd.garment == garment:
            scn.cd.seams.remove(i)


def seams_for(scn, garment):
    return [s for s in scn.cd.seams
            if s.obj_a and s.obj_b and
            (s.obj_a.cd.garment == garment or s.obj_b.cd.garment == garment)]


def _patterns_selected(context):
    return [o for o in context.selected_objects if o.cd.is_pattern]


# ---------------------------------------------------------------- avatar

class CD_OT_set_avatar(Operator):
    bl_idname = "cd.set_avatar"
    bl_label = "Set Avatar"
    bl_description = "Use the active mesh as the body (auto-detects if nothing suitable is active)"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        ob = context.active_object
        if ob is None or ob.type != 'MESH' or ob.cd.is_pattern or ob.cd.is_garment:
            ob = avatar.auto_avatar(context)
        if ob is None:
            self.report({'ERROR'}, "No mesh found to use as the avatar")
            return {'CANCELLED'}
        context.scene.cd.avatar = ob
        context.scene.cd.facing = avatar.auto_facing(context, ob)
        m = avatar.measure(context, ob, force=True)
        if m is None:
            self.report({'ERROR'}, "Could not measure %s" % ob.name)
            return {'CANCELLED'}
        sim.ensure_collider(context, ob)
        self.report({'INFO'}, "Avatar %s: %.0f cm tall, facing %s, chest %.0f cm"
                    % (ob.name, m["height"] * 100, context.scene.cd.facing,
                       avatar.girth_at(m, avatar.z_of(m, "chest")) * 100))
        return {'FINISHED'}


def asset_path(name="default_character.blend"):
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets", name)


CHARACTERS = {
    'WOMAN': ("default_character.blend", "Nora"),
    'MAN':   ("default_man.blend", "Theo"),
}


class CD_OT_import_character(Operator):
    bl_idname = "cd.import_character"
    bl_label = "Import Default Character"
    bl_description = ("Append a built-in fitting avatar: a project character with no "
                      "clothing, a neutral face, arms held clear of the body and the "
                      "feet on the floor")
    bl_options = {'REGISTER', 'UNDO'}

    figure: EnumProperty(items=[(k, v[1], "The %s fitting avatar" % k.lower())
                                for k, v in CHARACTERS.items()],
                         name="Figure", default='WOMAN')
    reimport: BoolProperty(name="Import Another Copy", default=False,
                           description="Bring in a second copy even if this scene already has one")

    def execute(self, context):
        scn = context.scene
        coll = patterns.get_collection(context, AVATAR_COLL)

        if not self.reimport:
            found = [o for o in coll.objects if o.type == 'MESH' and len(o.data.vertices) > 2000
                     and o.get("cd_figure", 'WOMAN') == self.figure]
            if found:
                body = max(found, key=lambda o: len(o.data.vertices))
                self._activate(context, body)
                self.report({'INFO'}, "This scene already has the default %s; using %s"
                            % (self.figure.lower(), body.name))
                return {'FINISHED'}

        path = asset_path(CHARACTERS[self.figure][0])
        if not os.path.exists(path):
            self.report({'ERROR'}, "Character asset is missing: %s" % path)
            return {'CANCELLED'}
        try:
            with bpy.data.libraries.load(path, link=False) as (src, dst):
                dst.objects = list(src.objects)
        except Exception as e:
            self.report({'ERROR'}, "Could not read the character asset: %s" % e)
            return {'CANCELLED'}

        brought = [o for o in dst.objects if o is not None]
        if not brought:
            self.report({'ERROR'}, "The character asset contained no objects")
            return {'CANCELLED'}
        for ob in brought:
            if ob.name not in coll.objects:
                coll.objects.link(ob)

        meshes = [o for o in brought if o.type == 'MESH']
        if not meshes:
            self.report({'ERROR'}, "The character asset contained no mesh")
            return {'CANCELLED'}
        body = max(meshes, key=lambda o: len(o.data.vertices))
        body["cd_figure"] = self.figure
        self._activate(context, body)
        m = avatar.measure(context, body, force=True)
        h = ("%.0f cm tall" % (m["height"] * 100)) if m else "measured"
        self.report({'INFO'}, "Imported %d objects; avatar is %s (%s)"
                    % (len(brought), body.name, h))
        return {'FINISHED'}

    def _activate(self, context, body):
        scn = context.scene
        scn.cd.avatar = body
        try:
            scn.cd.facing = avatar.auto_facing(context, body)
        except Exception:
            pass
        avatar.measure(context, body, force=True)
        sim.ensure_collider(context, body)
        for o in context.selected_objects:
            o.select_set(False)
        try:
            body.select_set(True)
            context.view_layer.objects.active = body
        except Exception:
            pass
        try:
            workspace.refresh_views(context)
        except Exception:
            pass


class CD_OT_measure(Operator):
    bl_idname = "cd.measure"
    bl_label = "Re-measure"
    bl_description = "Measure the avatar again at the current frame and pose"
    bl_options = {'REGISTER'}

    def execute(self, context):
        if context.scene.cd.avatar is None:
            self.report({'ERROR'}, "Set an avatar first")
            return {'CANCELLED'}
        m = avatar.measure(context, force=True)
        if m is None:
            self.report({'ERROR'}, "Measuring failed")
            return {'CANCELLED'}
        self.report({'INFO'}, "Measured: height %.0f cm, chest %.0f, waist %.0f, hip %.0f cm"
                    % (m["height"] * 100,
                       avatar.girth_at(m, avatar.z_of(m, "chest")) * 100,
                       avatar.girth_at(m, avatar.z_of(m, "waist")) * 100,
                       avatar.girth_at(m, avatar.z_of(m, "hip")) * 100))
        return {'FINISHED'}


# ---------------------------------------------------------------- garments

class CD_OT_add_garment(Operator):
    bl_idname = "cd.add_garment"
    bl_label = "Add Garment"
    bl_description = "Create a full set of pattern pieces, already sewn and arranged on the body"
    bl_options = {'REGISTER', 'UNDO'}

    preset: EnumProperty(items=library.PRESET_ITEMS, name="Garment", default='TSHIRT')
    fit: FloatProperty(name="Ease", default=0.08, min=-0.1, max=1.0,
                       description="Extra width over the body measurement. Lower is a closer fit")
    name: StringProperty(name="Name", default="")

    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self, width=280)

    def execute(self, context):
        scn = context.scene
        if scn.cd.avatar is None:
            bpy.ops.cd.set_avatar()
        m = avatar.measure(context)
        if m is None:
            self.report({'ERROR'}, "Set an avatar first")
            return {'CANCELLED'}

        label, fn = library.PRESETS[self.preset]
        gname = self.name or label.replace(" ", "")
        base = gname
        i = 1
        while any(o.cd.is_pattern and o.cd.garment == gname for o in scn.objects):
            i += 1
            gname = "%s%d" % (base, i)
        scn.cd.garment_name = gname

        m = dict(m)
        m["figure"] = avatar.figure(context, m)
        try:
            pieces, seams = fn(m, fit=self.fit)
        except Exception as e:
            self.report({'ERROR'}, "Preset failed: %s" % e)
            return {'CANCELLED'}

        made = {}
        with props.muted():
          for spec in pieces:
            ob = patterns.create_panel(
                context, "%s_%s" % (gname, spec["name"]), spec["segs"],
                garment=gname, anchor=spec["anchor"], height=spec["height"],
                ease=spec.get("ease", 0.02), wrap=spec.get("wrap", 1.0),
                spin=spec.get("spin", 0.0), taper=spec.get("taper", 0.0))
            made[spec["name"]] = ob

        drop_seams_for(scn, gname)
        for entry in seams:
            a, sa, b, sb = entry[:4]
            flip = entry[4] if len(entry) > 4 else None
            if a not in made or b not in made:
                continue
            s = scn.cd.seams.add()
            s.name = "%s.%s - %s.%s" % (a, sa, b, sb)
            s.obj_a, s.seg_a, s.obj_b, s.seg_b = made[a], sa, made[b], sb
            if flip is not None:
                s.flip = flip
                s.auto_flip = False

        g = build.sync_garment(context, self.report, gname)
        if g:
            existing = [o for o in scn.objects
                        if o.cd.is_garment and o is not g and o.data and len(o.data.vertices)]
            g.cd.layer = max((o.cd.layer for o in existing), default=-1) + 1
            sim.setup_cloth(context, g)
            sim.ensure_collider(context, scn.cd.avatar)
            sim.setup_layers(context)
            for i, o in enumerate(bpy.data.objects):
                if o is g:
                    scn.cd.active_garment = i
                    break
        try:
            workspace.refresh_views(context)
        except Exception:
            pass
        self.report({'INFO'}, "%s (%s): %d pieces, %d seams"
                    % (label, m["figure"].lower(), len(made), len(seams)))
        return {'FINISHED'}


_OUTFIT_ITEMS = []   # Blender needs the item strings kept alive


def _outfit_items(self, context):
    global _OUTFIT_ITEMS
    fig = avatar.figure(context) if context and context.scene.cd.avatar else None
    _OUTFIT_ITEMS = library.outfit_items(fig) or library.outfit_items()
    return _OUTFIT_ITEMS


class CD_OT_add_outfit(Operator):
    bl_idname = "cd.add_outfit"
    bl_label = "Add Outfit"
    bl_description = ("Build a complete outfit: several garments drafted and stacked on "
                      "their own layers, in the order you would dress: bottoms "
                      "first, then tops untucked over them, outerwear last")
    bl_options = {'REGISTER', 'UNDO'}

    outfit: EnumProperty(items=_outfit_items, name="Outfit",
                         description="Outfits drafted for the avatar's figure")
    sew_now: BoolProperty(name="Sew Them", default=False,
                          description="Also stitch every layer once they are drafted. "
                                      "Off by default because it takes a minute per garment")

    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self, width=300)

    def execute(self, context):
        scn = context.scene
        if scn.cd.avatar is None:
            bpy.ops.cd.import_character()
        label, fig, parts = library.OUTFITS[self.outfit]
        made = []
        for preset, ease in parts:
            try:
                bpy.ops.cd.add_garment(preset=preset, fit=ease)
                made.append(scn.cd.garment_name)
            except Exception as e:
                self.report({'WARNING'}, "%s failed: %s" % (preset, e))
        sim.setup_layers(context)
        if self.sew_now and made:
            bpy.ops.cd.sew(all_garments=True)
            sim.relax_outfit(context)
        self.report({'INFO'}, "%s: %s" % (label, " over ".join(made)))
        return {'FINISHED'}


class CD_OT_sync(Operator):
    bl_idname = "cd.sync"
    bl_label = "Arrange on Body"
    bl_description = "Rebuild the 3D garment from the 2D pattern pieces"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        ob = build.sync_garment(context, self.report)
        return {'FINISHED'} if ob else {'CANCELLED'}


class CD_OT_counterpart(Operator):
    bl_idname = "cd.counterpart"
    bl_label = "Create Counterpart"
    bl_description = "Copy the selected piece to the opposite side of the body and sew the edges that meet"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        sel = _patterns_selected(context)
        if not sel:
            self.report({'ERROR'}, "Select a pattern piece")
            return {'CANCELLED'}
        scn = context.scene
        new = []
        for ob in sel:
            cp = ob.copy()
            cp.data = ob.data.copy()
            cp.name = ob.name + "_Back"
            patterns.move_to_collection(cp, patterns.get_collection(context, patterns.PATTERN_COLL))
            cp.cd.anchor = COUNTERPART.get(ob.cd.anchor, ob.cd.anchor)
            cp.scale = ob.scale.copy()
            bb = [Vector(c) for c in cp.bound_box]
            w = max(p.x for p in bb) - min(p.x for p in bb)
            cp.location = (patterns.layout_slot(context, w), 0.0, ob.location.z)
            new.append(cp)
        bpy.ops.cd.auto_seam()
        build.sync_garment(context, self.report)
        self.report({'INFO'}, "Created %d counterpart piece(s)" % len(new))
        return {'FINISHED'}


# ---------------------------------------------------------------- sewing

def _seg_polyline(ob, seg, f):
    idx = patterns.segment_verts(ob, seg)
    return [f(ob.data.vertices[i].co.copy()) for i in idx]


def _adjacent_segments(ob, sa, sb, tol):
    """True if two segments of the same piece meet at a corner of its outline.
    Neighbouring edges of one panel must never be sewn to each other."""
    try:
        ends = json.loads(ob.get("cd_seg_ends", "{}"))
    except Exception:
        return False
    ea, eb = ends.get(sa), ends.get(sb)
    if not ea or not eb:
        return False
    pa = [Vector((p[0], p[1])) for p in ea]
    pb = [Vector((p[0], p[1])) for p in eb]
    return min((x - y).length for x in pa for y in pb) < tol


def _blocked(A, B, bvh, n=5):
    """True if the body sits between the two edges. Panels are sewn around the
    body, never through it, and this is what separates a genuine side seam from
    a front hem lining up with a back hem."""
    if bvh is None:
        return False
    hits = 0
    for i in range(n):
        t = (i + 0.5) / n
        a = A[min(len(A) - 1, int(t * (len(A) - 1)))]
        b = B[min(len(B) - 1, int(t * (len(B) - 1)))]
        d = b - a
        L = d.length
        if L < 1e-5:
            continue
        hit = bvh.ray_cast(a + d.normalized() * 1e-3, d.normalized(), L - 2e-3)
        if hit and hit[0] is not None:
            hits += 1
    return hits > n // 2


def _pair_cost(A, B):
    """Mean distance between two 3D polylines, best of the two orientations."""
    if len(A) < 2 or len(B) < 2:
        return 1e9, False
    def cost(bb):
        n = 8
        tot = 0.0
        for i in range(n + 1):
            t = i / n
            a = A[min(len(A) - 1, int(round(t * (len(A) - 1))))]
            b = bb[min(len(bb) - 1, int(round(t * (len(bb) - 1))))]
            tot += (a - b).length
        return tot / (n + 1)
    c1 = cost(B)
    c2 = cost(list(reversed(B)))
    return (c1, False) if c1 <= c2 else (c2, True)


class CD_OT_auto_seam(Operator):
    bl_idname = "cd.auto_seam"
    bl_label = "Auto Sew"
    bl_description = "Sew together the panel edges that end up next to each other on the body"
    bl_options = {'REGISTER', 'UNDO'}

    max_dist: FloatProperty(name="Max Distance", default=0.25, min=0.001, unit='LENGTH',
                            description="How far apart two panel edges may be and still be sewn")
    replace: BoolProperty(name="Replace Existing", default=True)
    self_seams: BoolProperty(name="Allow Self Seams", default=False,
                             description="Also sew a piece to itself, as a sleeve tube does. "
                                         "Off by default, since two edges of one panel are "
                                         "rarely meant to join")

    def execute(self, context):
        scn = context.scene
        m = avatar.measure(context)
        fwd, side = avatar.basis(scn.cd.facing)
        pieces = _patterns_selected(context) or build.garment_pieces(context)
        if len(pieces) < 1:
            self.report({'ERROR'}, "No pattern pieces")
            return {'CANCELLED'}

        bvh = avatar.torso_bvh(context) or avatar.body_bvh(context)
        segs = []
        for ob in pieces:
            f = build.piece_transform(ob, m, fwd, side)
            for s in patterns.segment_names(ob):
                poly = _seg_polyline(ob, s, f)
                if len(poly) >= 2:
                    L = sum((poly[i + 1] - poly[i]).length for i in range(len(poly) - 1))
                    segs.append((ob, s, poly, L))

        cands = []
        for i in range(len(segs)):
            for j in range(i + 1, len(segs)):
                oa, sa, pa, la = segs[i]
                ob_, sb, pb, lb = segs[j]
                if oa is ob_:
                    if sa == sb or not self.self_seams:
                        continue
                    if _adjacent_segments(oa, sa, sb, scn.cd.resolution * 3.0):
                        continue
                if max(la, lb) > 1e-9 and min(la, lb) / max(la, lb) < 0.55:
                    continue
                c, rev = _pair_cost(pa, pb)
                if c >= self.max_dist:
                    continue
                pb2 = list(reversed(pb)) if rev else pb
                if _blocked(pa, pb2, bvh):
                    continue
                cands.append((c, i, j, rev))
        cands.sort(key=lambda x: x[0])

        if self.replace:
            for gname in {ob.cd.garment for ob in pieces}:
                drop_seams_for(scn, gname)
        used = set()
        for ob_ in pieces:
            pass
        existing = {(s.obj_a.name if s.obj_a else "", s.seg_a,
                     s.obj_b.name if s.obj_b else "", s.seg_b) for s in scn.cd.seams}
        n = 0
        for c, i, j, rev in cands:
            if i in used or j in used:
                continue
            oa, sa, _, _ = segs[i]
            ob_, sb, _, _ = segs[j]
            key = (oa.name, sa, ob_.name, sb)
            if key in existing or (ob_.name, sb, oa.name, sa) in existing:
                continue
            s = scn.cd.seams.add()
            s.name = "%s.%s - %s.%s" % (oa.name, sa, ob_.name, sb)
            s.obj_a, s.seg_a, s.obj_b, s.seg_b = oa, sa, ob_, sb
            s.flip = rev
            used.add(i); used.add(j)
            n += 1
        build.sync_garment(context, None)
        self.report({'INFO'}, "Sewed %d seam(s)" % n)
        return {'FINISHED'}


def _seg_items(self, context):
    ob = context.active_object
    if ob is None:
        return [('NONE', "None", "")]
    items = [(s, s, "") for s in patterns.segment_names(ob)]
    return items or [('NONE', "None", "")]


class CD_OT_add_seam(Operator):
    bl_idname = "cd.add_seam"
    bl_label = "Sew Selected Edges"
    bl_description = ("Sew the selected boundary edges of two pattern pieces. "
                      "Select the edges in Edit Mode, or two objects for Auto Sew")
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        scn = context.scene
        ob = context.active_object
        if ob is None or ob.mode != 'EDIT' or not ob.cd.is_pattern:
            self.report({'ERROR'}, "Enter Edit Mode on a pattern piece and select boundary verts")
            return {'CANCELLED'}
        bm = bmesh.from_edit_mesh(ob.data)
        sel = [v.index for v in bm.verts if v.select and v.is_boundary]
        if len(sel) < 2:
            self.report({'ERROR'}, "Select at least 2 boundary vertices")
            return {'CANCELLED'}
        name = "S%d" % len([s for s in patterns.segment_names(ob)])
        bpy.ops.object.mode_set(mode='OBJECT')
        vg = ob.vertex_groups.new(name=patterns.SEG_PREFIX + name)
        vg.add(sel, 1.0, 'REPLACE')
        bpy.ops.object.mode_set(mode='EDIT')
        self.report({'INFO'}, "Created segment '%s' - use Auto Sew or the seam list to pair it" % name)
        return {'FINISHED'}


class CD_OT_remove_seam(Operator):
    bl_idname = "cd.remove_seam"
    bl_label = "Remove Seam"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        scn = context.scene
        i = scn.cd.active_seam
        if 0 <= i < len(scn.cd.seams):
            scn.cd.seams.remove(i)
            scn.cd.active_seam = max(0, i - 1)
            build.sync_garment(context, None)
        return {'FINISHED'}


class CD_OT_clear_seams(Operator):
    bl_idname = "cd.clear_seams"
    bl_label = "Clear Seams"
    bl_description = "Remove every seam on the active garment"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        scn = context.scene
        drop_seams_for(scn, scn.cd.garment_name)
        build.sync_garment(context, None)
        return {'FINISHED'}


# ---------------------------------------------------------------- drawing

class CD_OT_draw_pattern(Operator):
    bl_idname = "cd.draw_pattern"
    bl_label = "Draw Pattern"
    bl_description = ("Click to place points in the 2D pattern view; click the first point "
                      "again (or press Enter) to close the shape. Points snap to the grid, "
                      "Ctrl inverts the snap. Backspace undoes a point, Esc cancels")
    bl_options = {'REGISTER', 'UNDO'}

    _handle = None
    CLOSE_PX = 14.0     # screen radius round the first point that closes the outline

    def _plane_point(self, context, event):
        region = context.region
        rv3d = context.region_data
        from bpy_extras import view3d_utils
        co = (event.mouse_region_x, event.mouse_region_y)
        origin = view3d_utils.region_2d_to_origin_3d(region, rv3d, co)
        vec = view3d_utils.region_2d_to_vector_3d(region, rv3d, co)
        p = intersect_line_plane(origin, origin + vec * 1e4, Vector((0, 0, 0)), Vector((0, 1, 0)))
        if p is None:
            return None
        step = context.scene.cd.draw_snap
        if (step > 0.0) != bool(event.ctrl):
            p.x = round(p.x / step) * step
            p.z = round(p.z / step) * step
        return p

    def _near_first(self, context, event):
        """Is the mouse on the first point, with enough points to make a shape?"""
        if len(self.points) < 3:
            return False
        from bpy_extras.view3d_utils import location_3d_to_region_2d
        s = location_3d_to_region_2d(context.region, context.region_data, self.points[0])
        if s is None:
            return False
        dx = s.x - event.mouse_region_x
        dy = s.y - event.mouse_region_y
        return (dx * dx + dy * dy) ** 0.5 <= self.CLOSE_PX

    def invoke(self, context, event):
        if context.area is None or context.area.type != 'VIEW_3D':
            self.report({'ERROR'}, "Run this in a 3D viewport (use the 2D Pattern view)")
            return {'CANCELLED'}
        self.points = []
        self.cursor = None
        self.closing = False
        args = (self, context)
        self._handle = bpy.types.SpaceView3D.draw_handler_add(
            _draw_callback, args, 'WINDOW', 'POST_PIXEL')
        context.window_manager.modal_handler_add(self)
        self._header(context)
        return {'RUNNING_MODAL'}

    def _header(self, context):
        step = context.scene.cd.draw_snap
        snap = ("snap %.0f mm (Ctrl: off)" % (step * 1000)) if step > 0 else "snap off (Ctrl: on)"
        context.area.header_text_set(
            "Draw Pattern   |   click to add points, click the first point or Enter to close"
            "   |   Backspace undo, Esc cancel   |   " + snap)

    def modal(self, context, event):
        if context.area:
            context.area.tag_redraw()
        if event.type == 'MOUSEMOVE':
            self.closing = self._near_first(context, event)
            self.cursor = self.points[0].copy() if self.closing else self._plane_point(context, event)
            return {'RUNNING_MODAL'}
        if event.type == 'LEFTMOUSE' and event.value == 'PRESS':
            if self._near_first(context, event):
                return self.finish(context)
            p = self._plane_point(context, event)
            if p:
                # landing exactly on the first point through the grid closes too
                if len(self.points) >= 3 and (p - self.points[0]).length < 1e-6:
                    return self.finish(context)
                if not self.points or (p - self.points[-1]).length > 1e-6:
                    self.points.append(p)
            return {'RUNNING_MODAL'}
        if event.type in {'BACK_SPACE', 'DEL'} and event.value == 'PRESS':
            if self.points:
                self.points.pop()
            return {'RUNNING_MODAL'}
        if event.type in {'RET', 'NUMPAD_ENTER'} and event.value == 'PRESS':
            return self.finish(context)
        if event.type in {'RIGHTMOUSE', 'ESC'} and event.value == 'PRESS':
            return self.cancel(context)
        if event.type in {'MIDDLEMOUSE', 'WHEELUPMOUSE', 'WHEELDOWNMOUSE'}:
            return {'PASS_THROUGH'}
        return {'RUNNING_MODAL'}

    def _cleanup(self, context):
        if self._handle:
            bpy.types.SpaceView3D.draw_handler_remove(self._handle, 'WINDOW')
            self._handle = None
        if context.area:
            context.area.header_text_set(None)

    def cancel(self, context):
        self._cleanup(context)
        return {'CANCELLED'}

    def finish(self, context):
        self._cleanup(context)
        if len(self.points) < 3:
            self.report({'ERROR'}, "Need at least 3 points")
            return {'CANCELLED'}
        scn = context.scene
        pts = [Vector((p.x, p.z)) for p in self.points]
        segs = []
        n = len(pts)
        for i in range(n):
            segs.append(("S%d" % i, [pts[i], pts[(i + 1) % n]]))
        m = avatar.measure(context)
        zc = sum(p.y for p in pts) / n
        height = 0.5
        if m:
            height = (zc - m["zmin"]) / m["height"]
        try:
            ob = patterns.create_panel(context, scn.cd.garment_name + "_Panel", segs,
                                       garment=scn.cd.garment_name, height=height)
        except Exception as e:
            self.report({'ERROR'}, str(e))
            return {'CANCELLED'}
        for o in context.selected_objects:
            o.select_set(False)
        ob.select_set(True)
        context.view_layer.objects.active = ob
        build.sync_garment(context, None)
        self.report({'INFO'}, "Panel created with %d edges" % n)
        return {'FINISHED'}


def _draw_callback(op, context):
    import gpu
    from gpu_extras.batch import batch_for_shader
    from bpy_extras.view3d_utils import location_3d_to_region_2d
    region, rv3d = context.region, context.region_data
    pts = [p for p in op.points if p is not None]
    if not pts:
        return
    scr = [location_3d_to_region_2d(region, rv3d, p) for p in pts]
    scr = [s for s in scr if s]
    if op.cursor is not None:
        c = location_3d_to_region_2d(region, rv3d, op.cursor)
        if c:
            scr = scr + [c]
    if len(scr) < 2:
        return
    shader = gpu.shader.from_builtin('UNIFORM_COLOR')
    gpu.state.blend_set('ALPHA')
    gpu.state.line_width_set(2.0)
    batch = batch_for_shader(shader, 'LINE_STRIP', {"pos": scr})
    shader.bind()
    shader.uniform_float("color", (1.0, 0.75, 0.2, 1.0))
    batch.draw(shader)
    closing = getattr(op, "closing", False)
    if len(scr) > 2:
        batch2 = batch_for_shader(shader, 'LINE_STRIP', {"pos": [scr[-1], scr[0]]})
        shader.uniform_float("color", (0.3, 1.0, 0.4, 1.0) if closing else (1.0, 0.75, 0.2, 0.35))
        batch2.draw(shader)
    batch3 = batch_for_shader(shader, 'POINTS', {"pos": scr[:len(pts)]})
    gpu.state.point_size_set(7.0)
    shader.uniform_float("color", (0.2, 0.9, 1.0, 1.0))
    batch3.draw(shader)
    if len(pts) >= 3:
        # the first point is the one that closes the shape: ring it, green when hot
        batch4 = batch_for_shader(shader, 'POINTS', {"pos": [scr[0]]})
        gpu.state.point_size_set(16.0 if closing else 11.0)
        shader.uniform_float("color", (0.3, 1.0, 0.4, 1.0) if closing else (1.0, 0.75, 0.2, 0.9))
        batch4.draw(shader)
    if op.cursor is not None and scr:
        batch5 = batch_for_shader(shader, 'POINTS', {"pos": [scr[-1]]})
        gpu.state.point_size_set(5.0)
        shader.uniform_float("color", (1.0, 1.0, 1.0, 0.9))
        batch5.draw(shader)
    gpu.state.blend_set('NONE')


# ---------------------------------------------------------------- simulation

GRAB_GROUP = "CD_GRAB"


class CD_OT_grab(Operator):
    bl_idname = "cd.grab"
    bl_label = "Grab Fabric"
    bl_description = ("Pull the cloth around with the mouse while it simulates. "
                      "Drag on the garment, release to let go, Esc to finish. "
                      "Scroll changes the grab radius")
    bl_options = {'REGISTER'}

    radius: FloatProperty(name="Radius", default=0.055, min=0.005, max=0.5, unit='LENGTH')

    _timer = None

    def _cloth(self):
        return next((m for m in self.ob.modifiers if m.type == 'CLOTH'), None)

    def _eval_coords(self, context):
        with sim.sim_cage_only(self.ob):
            context.view_layer.update()
            dg = context.evaluated_depsgraph_get()
            ev = self.ob.evaluated_get(dg)
            me = ev.to_mesh()
            co = [v.co.copy() for v in me.vertices]
            ev.to_mesh_clear()
        return co

    def _ray(self, context, event):
        from bpy_extras import view3d_utils
        region, rv3d = context.region, context.region_data
        mouse = (event.mouse_region_x, event.mouse_region_y)
        origin = view3d_utils.region_2d_to_origin_3d(region, rv3d, mouse)
        vec = view3d_utils.region_2d_to_vector_3d(region, rv3d, mouse)
        dg = context.evaluated_depsgraph_get()
        hit, loc, nor, idx, obj, mat = context.scene.ray_cast(dg, origin, vec)
        if hit and obj is not None and obj.original == self.ob:
            return loc
        return None

    def _plane_point(self, context, event, anchor):
        from bpy_extras import view3d_utils
        region, rv3d = context.region, context.region_data
        mouse = (event.mouse_region_x, event.mouse_region_y)
        return view3d_utils.region_2d_to_location_3d(region, rv3d, mouse, anchor)

    def _grab(self, context, event):
        """Pin a patch and drive it with a Hook.

        The hook deforms the cloth's *input* mesh, which the pin then targets.
        Writing the pin targets straight into the mesh data instead stalls the
        solver, because editing mesh data invalidates the point cache.
        """
        loc = self._ray(context, event)
        if loc is None:
            return False
        co = self._eval_coords(context)
        if len(co) != len(self.ob.data.vertices):
            self.report({'WARNING'}, "Garment topology has changed - re-arrange before grabbing")
            return False
        r = self.radius
        picked = [(i, (co[i] - loc).length) for i in range(len(co)) if (co[i] - loc).length < r]
        if len(picked) < 3:
            return False

        vg = self.ob.vertex_groups.get(GRAB_GROUP)
        if vg:
            self.ob.vertex_groups.remove(vg)
        vg = self.ob.vertex_groups.new(name=GRAB_GROUP)
        for i, d in picked:
            t = 1.0 - (d / r)
            vg.add([i], max(0.04, t * t * (3.0 - 2.0 * t)), 'REPLACE')
        idx = [i for i, _ in picked]

        emp = bpy.data.objects.new("CD_Hand", None)
        context.scene.collection.objects.link(emp)
        emp.empty_display_type = 'SPHERE'
        emp.empty_display_size = r
        # bind pulled back by the mean rest-to-draped offset so the patch starts
        # under the cursor rather than snapping toward the flat pattern
        off = Vector((0, 0, 0))
        for i in idx:
            off += co[i] - self.ob.data.vertices[i].co
        off /= len(idx)
        emp.location = loc - off
        context.view_layer.update()

        hk = self.ob.modifiers.new("CD_Hook", 'HOOK')
        hk.object = emp
        hk.vertex_group = GRAB_GROUP
        hk.matrix_inverse = emp.matrix_world.inverted()
        emp.location = loc
        try:
            with context.temp_override(object=self.ob, active_object=self.ob):
                bpy.ops.object.modifier_move_to_index(modifier=hk.name, index=0)
        except Exception:
            pass

        cl = self._cloth()
        cl.settings.vertex_group_mass = GRAB_GROUP
        cl.settings.pin_stiffness = 20.0
        self.emp, self.hook, self.anchor = emp, hk, loc.copy()
        self.dragging = True
        return True

    def _release(self, context):
        if not self.dragging:
            return
        cl = self._cloth()
        if cl:
            cl.settings.vertex_group_mass = ""
        if self.hook and self.hook.name in [m.name for m in self.ob.modifiers]:
            self.ob.modifiers.remove(self.hook)
        if self.emp:
            bpy.data.objects.remove(self.emp, do_unlink=True)
        vg = self.ob.vertex_groups.get(GRAB_GROUP)
        if vg:
            self.ob.vertex_groups.remove(vg)
        self.emp = self.hook = None
        self.dragging = False

    def invoke(self, context, event):
        if context.area is None or context.area.type != 'VIEW_3D':
            self.report({'ERROR'}, "Run this in a 3D viewport")
            return {'CANCELLED'}
        ob = build.garment_object(context, create=False)
        if ob is None or not len(ob.data.vertices):
            self.report({'ERROR'}, "No garment to grab - arrange one first")
            return {'CANCELLED'}
        self.ob = ob
        if self._cloth() is None:
            sim.setup_cloth(context, ob)
            sim.ensure_collider(context, context.scene.cd.avatar)
        self.emp = self.hook = None
        self.dragging = False
        wm = context.window_manager
        self._timer = wm.event_timer_add(0.02, window=context.window)
        wm.modal_handler_add(self)
        self._status(context)
        return {'RUNNING_MODAL'}

    def _status(self, context):
        context.workspace.status_text_set(
            "Grab Fabric   |   drag on the garment to pull it, release to let go   |   "
            "scroll: radius %.0f mm   |   Esc: finish" % (self.radius * 1000))

    def modal(self, context, event):
        scn = context.scene
        if event.type in {'ESC', 'RIGHTMOUSE'} and event.value == 'PRESS':
            return self._finish(context)

        if event.type in {'WHEELUPMOUSE', 'WHEELDOWNMOUSE'} and not self.dragging:
            self.radius *= 1.15 if event.type == 'WHEELUPMOUSE' else 1.0 / 1.15
            self.radius = max(0.005, min(0.5, self.radius))
            self._status(context)
            return {'RUNNING_MODAL'}

        if event.type == 'LEFTMOUSE':
            if event.value == 'PRESS':
                if not self._grab(context, event):
                    self.report({'INFO'}, "Nothing there - click on the garment itself")
                return {'RUNNING_MODAL'}
            if event.value == 'RELEASE':
                self._release(context)
                return {'RUNNING_MODAL'}

        if event.type == 'MOUSEMOVE' and self.dragging and self.emp:
            p = self._plane_point(context, event, self.anchor)
            if p is not None:
                self.emp.location = p
            return {'RUNNING_MODAL'}

        if event.type == 'TIMER':
            scn.frame_set(scn.frame_current + 1)
            return {'RUNNING_MODAL'}

        return {'RUNNING_MODAL'}

    def _finish(self, context):
        self._release(context)
        wm = context.window_manager
        if self._timer:
            wm.event_timer_remove(self._timer)
            self._timer = None
        context.workspace.status_text_set(None)
        self.report({'INFO'}, "Grab finished at frame %d" % context.scene.frame_current)
        return {'FINISHED'}


def _active_garment(context):
    return build.garment_object(context, create=False)


def _drop_finalize_mods(ob, arm):
    for m in list(ob.modifiers):
        if m.type in {'ARMATURE', 'SOLIDIFY'}:
            ob.modifiers.remove(m)
    if arm is not None:
        bones = {b.name for b in arm.data.bones}
        for vg in list(ob.vertex_groups):
            if vg.name in bones:
                ob.vertex_groups.remove(vg)


class CD_OT_unsew(Operator):
    bl_idname = "cd.unsew"
    bl_label = "Unsew"
    bl_description = ("Open the seams again: rebuild this garment from its flat pattern "
                      "pieces, drop the rig binding and thickness, and put the stitches back")
    bl_options = {'REGISTER', 'UNDO'}

    all_garments: BoolProperty(name="Every Garment", default=False)

    def execute(self, context):
        scn = context.scene
        targets = (sim.garment_layers(context) if self.all_garments
                   else [g for g in [_active_garment(context)] if g])
        if not targets:
            self.report({'ERROR'}, "No garment to unsew")
            return {'CANCELLED'}
        arm = avatar.find_armature(scn.cd.avatar) if scn.cd.avatar else None
        prev = scn.cd.garment_name
        done = 0
        for g in targets:
            scn.cd.garment_name = g.cd.garment
            if not build.garment_pieces(context, g.cd.garment):
                continue
            _drop_finalize_mods(g, arm)
            build.sync_garment(context, None, g.cd.garment)
            sim.setup_cloth(context, g)
            done += 1
        scn.cd.garment_name = prev
        sim.setup_layers(context)
        self.report({'INFO'}, "Unsewed %d garment%s - seams are open again"
                    % (done, "" if done == 1 else "s"))
        return {'FINISHED'}


class CD_OT_sew(Operator):
    bl_idname = "cd.sew"
    bl_label = "Sew"
    bl_description = ("Stitch the seams closed, weld them and let the garment settle. "
                      "With Every Garment on, works through the layers from the inside out")
    bl_options = {'REGISTER'}

    all_garments: BoolProperty(name="Every Garment", default=False)

    def execute(self, context):
        scn = context.scene
        targets = (sim.garment_layers(context) if self.all_garments
                   else [g for g in [_active_garment(context)] if g])
        if not targets:
            self.report({'ERROR'}, "No garment to sew")
            return {'CANCELLED'}
        sim.ensure_collider(context, scn.cd.avatar)
        sim.setup_layers(context)
        prev = scn.cd.garment_name
        start = scn.frame_current
        msgs = []
        # the garments this one is worn over collide as their cages, so a
        # finalized layer behaves the same as an unfinalized one
        others = [o for o in scn.objects if o.cd.is_garment and o not in targets]
        for g in targets:
            scn.cd.garment_name = g.cd.garment
            scn.frame_set(start)
            if len(targets) > 1:
                # re-arrange over the layers already sewn beneath this one -
                # when the outfit was drafted they were still flat panels
                build.sync_garment(context, garment=g.cd.garment)
            sim.setup_cloth(context, g)
            sim.kick_solver(context, g)
            # hold the collar on the shoulders while the seams close; from 60%
            # keep only the back collar - the part the garment hangs from - so
            # the front can draw in to the neck before it is welded
            pinned = sim.pin_shoulders(context, g)
            hold = int(scn.cd.stitch_frames * sim.PIN_HOLD) if pinned else -1
            sim.set_gravity(g, scn.cd.stitch_gravity)
            with sim.cages_only(others):
                for i in range(scn.cd.stitch_frames):
                    if i == hold:
                        sim.pin_shoulders(context, g, torso_anchors=('TORSO_BACK',))
                    scn.frame_set(scn.frame_current + 1)
            merged = 0
            if scn.cd.auto_close:
                merged, _ = sim.close_seams(context, g)
            sim.unpin_shoulders(g)
            sim.set_gravity(g, 1.0)
            with sim.cages_only(others):
                for _ in range(scn.cd.settle_frames):
                    scn.frame_set(scn.frame_current + 1)
            msgs.append("%s (%d welded)" % (g.cd.garment, merged))
        # (A relax pass here was tried and reverted: taking the fabric in
        # smooths a garment measured on its own, but on the body it drags an
        # open-front jacket back down off the shoulders. Relax stays an
        # outfit-level finish, where the layers underneath hold it up, and a
        # button users can press.)
        scn.cd.garment_name = prev
        self.report({'INFO'}, "Sewn: " + ", ".join(msgs))
        return {'FINISHED'}


class CD_OT_setup_layers(Operator):
    bl_idname = "cd.setup_layers"
    bl_label = "Rebuild Layers"
    bl_description = ("Wire up layered collision so each garment collides with the body "
                      "and with everything worn under it")
    bl_options = {'REGISTER'}

    def execute(self, context):
        n = sim.setup_layers(context)
        gs = sim.garment_layers(context)
        self.report({'INFO'}, "%d garment%s layered: %s"
                    % (len(gs), "" if len(gs) == 1 else "s",
                       ", ".join("%s(L%d)" % (g.cd.garment, g.cd.layer) for g in gs)) if gs
                    else "No garments to layer")
        return {'FINISHED'}


class CD_OT_garment_layer(Operator):
    bl_idname = "cd.garment_layer"
    bl_label = "Move Layer"
    bl_options = {'REGISTER', 'UNDO'}

    direction: EnumProperty(items=[('UP', "Out", ""), ('DOWN', "In", "")], default='UP')

    def execute(self, context):
        g = _active_garment(context)
        if g is None:
            return {'CANCELLED'}
        g.cd.layer = max(0, min(16, g.cd.layer + (1 if self.direction == 'UP' else -1)))
        sim.setup_layers(context)
        self.report({'INFO'}, "%s is now on layer %d" % (g.cd.garment, g.cd.layer))
        return {'FINISHED'}


class CD_OT_setup_sim(Operator):
    bl_idname = "cd.setup_sim"
    bl_label = "Setup Simulation"
    bl_description = "Add cloth to the garment and collision to the avatar"
    bl_options = {'REGISTER'}

    def execute(self, context):
        scn = context.scene
        ob = build.garment_object(context, create=False)
        if ob is None:
            self.report({'ERROR'}, "No garment - press Arrange on Body first")
            return {'CANCELLED'}
        sim.setup_cloth(context, ob)
        sim.ensure_collider(context, scn.cd.avatar)
        self.report({'INFO'}, "Cloth ready on %s (sewing springs on)" % ob.name)
        return {'FINISHED'}


class CD_OT_drape(Operator):
    bl_idname = "cd.drape"
    bl_label = "Sew & Drape"
    bl_description = ("Pull the seams closed, weld them into one continuous garment, "
                      "then let it settle on the body")
    bl_options = {'REGISTER'}

    _timer = None

    def _prepare(self, context):
        scn = context.scene
        ob = build.garment_object(context, create=False)
        if ob is None:
            self.report({'ERROR'}, "No garment - press Arrange on Body first")
            return None
        sim.setup_cloth(context, ob)
        sim.ensure_collider(context, scn.cd.avatar)
        sim.set_gravity(ob, scn.cd.stitch_gravity)
        self.ob = ob
        self.stitch_end = scn.frame_current + scn.cd.stitch_frames
        self.settle_end = self.stitch_end + scn.cd.settle_frames
        self.closed = False
        self.merged = 0
        return ob

    def _close(self, context):
        scn = context.scene
        self.closed = True
        if scn.cd.auto_close:
            self.merged, _ = sim.close_seams(context, self.ob)
        sim.set_gravity(self.ob, 1.0)

    def execute(self, context):
        scn = context.scene
        if self._prepare(context) is None:
            return {'CANCELLED'}
        while scn.frame_current < self.stitch_end:
            scn.frame_set(scn.frame_current + 1)
        self._close(context)
        while scn.frame_current < self.settle_end:
            scn.frame_set(scn.frame_current + 1)
        self.report({'INFO'}, "Sewn and draped (%d seam verts welded)" % self.merged)
        return {'FINISHED'}

    def invoke(self, context, event):
        if self._prepare(context) is None:
            return {'CANCELLED'}
        wm = context.window_manager
        self._timer = wm.event_timer_add(0.01, window=context.window)
        wm.modal_handler_add(self)
        context.workspace.status_text_set("Stitching... Esc to stop")
        return {'RUNNING_MODAL'}

    def modal(self, context, event):
        scn = context.scene
        if event.type in {'ESC', 'RIGHTMOUSE'}:
            return self._finish(context)
        if event.type == 'TIMER':
            if not self.closed and scn.frame_current >= self.stitch_end:
                self._close(context)
                context.workspace.status_text_set("Settling... Esc to stop")
                return {'RUNNING_MODAL'}
            if self.closed and scn.frame_current >= self.settle_end:
                return self._finish(context)
            scn.frame_set(scn.frame_current + 1)
        return {'RUNNING_MODAL'}

    def _finish(self, context):
        wm = context.window_manager
        if self._timer:
            wm.event_timer_remove(self._timer)
            self._timer = None
        context.workspace.status_text_set(None)
        self.report({'INFO'}, "Drape finished at frame %d (%d seam verts welded)"
                    % (context.scene.frame_current, self.merged))
        return {'FINISHED'}


class CD_OT_close_seams(Operator):
    bl_idname = "cd.close_seams"
    bl_label = "Weld Seams Now"
    bl_description = "Weld the stitched seams into one continuous surface and keep simulating"
    bl_options = {'REGISTER'}

    def execute(self, context):
        ob = build.garment_object(context, create=False)
        if ob is None:
            self.report({'ERROR'}, "No garment")
            return {'CANCELLED'}
        merged, skipped = sim.close_seams(context, ob)
        msg = "%d seam verts welded" % merged
        if skipped:
            msg += ", %d stitches still too wide to close" % skipped
        self.report({'INFO'}, msg)
        return {'FINISHED'}


class CD_OT_settle(Operator):
    bl_idname = "cd.settle"
    bl_label = "Settle"
    bl_description = "Keep simulating the garment where it is"
    bl_options = {'REGISTER'}

    def execute(self, context):
        scn = context.scene
        ob = build.garment_object(context, create=False)
        if ob is None:
            self.report({'ERROR'}, "No garment")
            return {'CANCELLED'}
        # Add Outfit leaves its garments frozen (baked, solver dropped) so the
        # layers stay where they settled; put a solver back if asked to run on
        if not any(m.type == 'CLOTH' for m in ob.modifiers):
            sim.ensure_collider(context, scn.cd.avatar)
            sim.setup_layers(context)
            sim.setup_cloth(context, ob)
        sim.set_gravity(ob, 1.0)
        end = scn.frame_current + scn.cd.settle_frames
        while scn.frame_current < end:
            scn.frame_set(scn.frame_current + 1)
        self.report({'INFO'}, "Settled to frame %d" % scn.frame_current)
        return {'FINISHED'}


class CD_OT_relax(Operator):
    bl_idname = "cd.relax"
    bl_label = "Relax"
    bl_description = ("Finishing pass: soften the fabric and take it in a little so "
                      "it wraps the body, freeze that shape, then let it rest. The "
                      "weld bakes a ballooned mid-drape shape as the cloth's rest "
                      "shape, and settling at fabric stiffness never lies it down")
    bl_options = {'REGISTER'}

    take_in: FloatProperty(name="Take In", default=0.06, min=0.0, max=0.3,
                           description="How much the fabric is taken in while it wraps")

    def execute(self, context):
        ob = build.garment_object(context, create=False)
        if ob is None:
            self.report({'ERROR'}, "No garment")
            return {'CANCELLED'}
        if not any(m.type == 'CLOTH' for m in ob.modifiers):
            sim.ensure_collider(context, context.scene.cd.avatar)
            sim.setup_layers(context)
            sim.setup_cloth(context, ob)
        if not sim.relax_garment(context, ob, take_in=self.take_in):
            self.report({'ERROR'}, "The garment has no cloth - sew it first")
            return {'CANCELLED'}
        self.report({'INFO'}, "Relaxed %s to frame %d" % (ob.cd.garment, context.scene.frame_current))
        return {'FINISHED'}


class CD_OT_reset_sim(Operator):
    bl_idname = "cd.reset_sim"
    bl_label = "Reset"
    bl_description = "Send the garment back to its arranged position and clear the cache"
    bl_options = {'REGISTER'}

    def execute(self, context):
        ob = build.sync_garment(context, None)
        if ob is None:
            return {'CANCELLED'}
        sim.setup_cloth(context, ob)
        self.report({'INFO'}, "Reset to the arranged shape")
        return {'FINISHED'}


class CD_OT_finalize(Operator):
    bl_idname = "cd.finalize"
    bl_label = "Finalize Garment"
    bl_description = ("Freeze the draped shape, weld the seams into one continuous "
                      "surface, add thickness and bind to the rig")
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        scn = context.scene
        ob = build.garment_object(context, create=False)
        if ob is None:
            self.report({'ERROR'}, "No garment")
            return {'CANCELLED'}
        msgs = []
        if not sim.bake_shape(context, ob):
            self.report({'WARNING'}, "Could not read the simulated shape; freezing skipped")
        else:
            msgs.append("shape frozen")
        for mod in list(ob.modifiers):
            if mod.type == 'CLOTH':
                ob.modifiers.remove(mod)
        if scn.cd.weld_seams and build.loose_edges(ob.data):
            merged, left = sim.weld_seams(ob, scn.cd.weld_dist)
            msgs.append("%d seam verts welded" % merged)
            if left:
                msgs.append("%d open stitches removed" % left)
        sim.add_subdivision(ob, scn.cd.subdiv_levels, scn.cd.subdiv_render)
        holes = sim.close_stray_holes(ob)
        if holes:
            msgs.append("%d stray hole%s closed" % (holes, "" if holes == 1 else "s"))
        if scn.cd.thickness > 0.0:
            sim.add_thickness(ob, scn.cd.thickness)
            msgs.append("thickness %.1f mm" % (scn.cd.thickness * 1000))
        if scn.cd.bind_armature and scn.cd.avatar:
            ok, msg = sim.bind_to_armature(context, ob, scn.cd.avatar)
            msgs.append(msg if ok else "bind skipped (%s)" % msg)
        self.report({'INFO'}, "; ".join(msgs))
        return {'FINISHED'}


class CD_OT_animate(Operator):
    bl_idname = "cd.animate"
    bl_label = "Animate"
    bl_description = ("Walk the avatar on the spot so you can watch a finalized "
                      "garment move with the body. Play with Space; press again "
                      "to re-key, or Rest Pose to clear it")
    bl_options = {'REGISTER', 'UNDO'}

    style: EnumProperty(
        name="Walk", default='WALK',
        items=[('WALK', "Walk", "An ordinary walk"),
               ('CATWALK', "Catwalk", "A runway walk: slower, with the hips "
                                      "and torso doing much more of the work "
                                      "and the feet landing on the centre line")],
        description="Which gait to key. Changing this resets the sliders below")
    period: IntProperty(name="Frames per Stride", default=32, min=8, max=120,
                        description="Length of one full stride")
    stride: FloatProperty(name="Stride", default=0.32, min=0.05, max=1.2,
                          subtype='ANGLE',
                          description="How far the legs swing")
    arm_swing: FloatProperty(name="Arm Swing", default=0.26, min=0.0, max=1.2,
                             subtype='ANGLE')
    arm_down: FloatProperty(name="Lower Arms", default=0.75, min=0.0, max=1.4,
                            subtype='ANGLE',
                            description="Bring the arms in from the avatar's "
                                        "drafting pose to a natural walking one")
    play: BoolProperty(name="Play", default=True,
                       description="Start playback once the walk is keyed")

    @classmethod
    def poll(cls, context):
        av = context.scene.cd.avatar
        return av is not None and avatar.find_armature(av) is not None

    def invoke(self, context, event):
        # The style sets the sliders, so picking Catwalk and pressing Enter
        # gives a catwalk without anyone having to know that a runway walk is
        # mostly pelvis roll.
        self._apply_style()
        return context.window_manager.invoke_props_dialog(self, width=300)

    def _apply_style(self):
        pre = sim.WALK_STYLES.get(self.style)
        if not pre:
            return
        self.period = pre["period"]
        self.stride = pre["stride"]
        self.arm_swing = pre["arm_swing"]

    def execute(self, context):
        scn = context.scene
        # The style supplies the cadence and swing; a slider only overrides it
        # if the user actually touched it. Overriding unconditionally meant the
        # operator's own defaults won whenever execute() ran without invoke() -
        # from a script, or from the redo panel - and Catwalk quietly keyed an
        # ordinary 32-frame walk.
        pre = dict(sim.WALK_STYLES.get(self.style, sim.WALK_STYLES['WALK']))
        for key in ("period", "stride", "arm_swing"):
            if self.properties.is_property_set(key):
                pre[key] = getattr(self, key)
        pre["arm_down"] = self.arm_down
        act, msg = sim.walk_cycle(context, scn.cd.avatar, **pre)
        if act is None:
            self.report({'ERROR'}, msg)
            return {'CANCELLED'}
        bound = [o for o in scn.objects if o.cd.is_garment
                 and any(m.type == 'ARMATURE' for m in o.modifiers)]
        if not bound:
            self.report({'WARNING'}, "%s - no garment is bound to the rig yet; "
                                     "run Finalize with Bind To Armature on" % msg)
        else:
            self.report({'INFO'}, "%s; %d garment(s) following" % (msg, len(bound)))
        if self.play and not context.screen.is_animation_playing:
            bpy.ops.screen.animation_play()
        return {'FINISHED'}


class CD_OT_rest_pose(Operator):
    bl_idname = "cd.rest_pose"
    bl_label = "Rest Pose"
    bl_description = "Stop the walk and put the avatar back in its rest pose"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        av = context.scene.cd.avatar
        return av is not None and avatar.find_armature(av) is not None

    def execute(self, context):
        if context.screen.is_animation_playing:
            bpy.ops.screen.animation_cancel(restore_frame=False)
        rig = avatar.find_armature(context.scene.cd.avatar)
        sim.clear_walk(rig)
        context.scene.frame_set(context.scene.frame_start)
        self.report({'INFO'}, "Rest pose restored")
        return {'FINISHED'}


# ---------------------------------------------------------------- workspace

class CD_OT_build_workspace(Operator):
    bl_idname = "cd.build_workspace"
    bl_label = "Create Clothing Design Workspace"
    bl_description = "Build the clothing design workspace: 2D pattern, side and 3D views"
    bl_options = {'REGISTER'}

    def execute(self, context):
        ok, msg = workspace.build(context)
        self.report({'INFO'} if ok else {'ERROR'}, msg)
        return {'FINISHED'} if ok else {'CANCELLED'}


class CD_OT_frame_view(Operator):
    bl_idname = "cd.frame_view"
    bl_label = "Frame"
    bl_options = {'REGISTER'}

    target: EnumProperty(items=[('2D', "2D Patterns", ""), ('3D', "Body", "")], default='2D')

    def execute(self, context):
        workspace.frame_region(context, context.area, self.target)
        return {'FINISHED'}


CLASSES = (
    CD_OT_import_character, CD_OT_set_avatar, CD_OT_measure, CD_OT_add_garment,
    CD_OT_add_outfit, CD_OT_sync, CD_OT_counterpart,
    CD_OT_auto_seam, CD_OT_add_seam, CD_OT_remove_seam, CD_OT_clear_seams,
    CD_OT_draw_pattern, CD_OT_grab, CD_OT_unsew, CD_OT_sew, CD_OT_setup_layers,
    CD_OT_garment_layer, CD_OT_setup_sim, CD_OT_drape, CD_OT_close_seams, CD_OT_settle,
    CD_OT_relax, CD_OT_reset_sim, CD_OT_finalize, CD_OT_animate, CD_OT_rest_pose,
    CD_OT_build_workspace, CD_OT_frame_view,
)


def register():
    for c in CLASSES:
        bpy.utils.register_class(c)


def unregister():
    for c in reversed(CLASSES):
        bpy.utils.unregister_class(c)
