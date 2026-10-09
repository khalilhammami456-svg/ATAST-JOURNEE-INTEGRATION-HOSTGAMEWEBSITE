# Clothing Design - the workspace layout.
#
# Built by duplicating the stock Layout workspace and splitting its 3D viewport,
# which keeps the timeline and outliner (both wanted while simulating) and avoids
# having to tear a screen down to a single area first.
import bpy, math
from mathutils import Vector, Euler
from bpy.app.handlers import persistent

NAME = "Clothing Design"

FRONT_ROT = Euler((math.pi * 0.5, 0.0, 0.0)).to_quaternion()
SIDE_ROT = Euler((math.pi * 0.5, 0.0, math.pi * 0.5)).to_quaternion()
PERSP_ROT = Euler((math.radians(72.0), 0.0, math.radians(28.0))).to_quaternion()


def _areas_sorted(screen):
    return sorted(screen.areas, key=lambda a: (-a.width * a.height))


def _split(context, win, screen, area, direction, factor):
    before = {a.as_pointer() for a in screen.areas}
    try:
        with context.temp_override(window=win, screen=screen, area=area):
            bpy.ops.screen.area_split(direction=direction, factor=factor)
    except Exception as e:
        print("[clothing_design] split failed:", e)
        return None
    new = [a for a in screen.areas if a.as_pointer() not in before]
    return new[0] if new else None


def _region(area, rtype='WINDOW'):
    for r in area.regions:
        if r.type == rtype:
            return r
    return None


def bounds(objs):
    lo = Vector((1e18, 1e18, 1e18))
    hi = -lo
    found = False
    for ob in objs:
        for c in ob.bound_box:
            p = ob.matrix_world @ Vector(c)
            lo = Vector((min(lo.x, p.x), min(lo.y, p.y), min(lo.z, p.z)))
            hi = Vector((max(hi.x, p.x), max(hi.y, p.y), max(hi.z, p.z)))
            found = True
    if not found:
        return None, None
    return lo, hi


def _view_axes(area):
    """Which world axes map to the viewport's horizontal and vertical."""
    rv3d = area.spaces.active.region_3d
    m = rv3d.view_matrix.to_3x3()
    right = Vector((m[0][0], m[0][1], m[0][2]))
    up = Vector((m[1][0], m[1][1], m[1][2]))
    return right, up


def frame_region(context, area, target='2D'):
    """Point one viewport at either the 2D pattern area or the body."""
    if area is None or area.type != 'VIEW_3D':
        return False
    scn = context.scene
    if target == '2D':
        objs = [o for o in scn.objects if o.cd.is_pattern]
        if not objs and scn.cd.avatar:
            objs = [scn.cd.avatar]
    else:
        objs = [o for o in scn.objects if o.cd.is_garment and len(o.data.vertices)]
        if scn.cd.avatar:
            objs.append(scn.cd.avatar)
        if not objs:
            objs = [o for o in scn.objects if o.type == 'MESH'][:1]
    lo, hi = bounds(objs)
    if lo is None:
        return False
    space = area.spaces.active
    rv3d = space.region_3d
    rv3d.view_location = (lo + hi) * 0.5

    # fit the bounds to the region, allowing for its aspect ratio
    half = (hi - lo) * 0.5
    right, up = _view_axes(area)
    ext_h = abs(half.x * right.x) + abs(half.y * right.y) + abs(half.z * right.z)
    ext_v = abs(half.x * up.x) + abs(half.y * up.y) + abs(half.z * up.z)
    region = _region(area)
    aspect = (region.width / region.height) if region and region.height else 1.0
    need = max(ext_v, ext_h / max(aspect, 1e-3))
    rv3d.view_distance = max(need * 3.1, 0.05)
    return True


def _setup_view(context, area, kind):
    space = area.spaces.active
    rv3d = space.region_3d
    ov = space.overlay
    sh = space.shading
    if kind == 'PATTERN':
        rv3d.view_perspective = 'ORTHO'
        rv3d.view_rotation = FRONT_ROT
        sh.type = 'SOLID'
        sh.light = 'FLAT'
        sh.color_type = 'MATERIAL'
        sh.show_xray = False
        ov.show_floor = False
        ov.show_axis_x = True
        ov.show_axis_y = False
        ov.show_axis_z = True
        ov.show_ortho_grid = True
        ov.show_cursor = False
        ov.show_relationship_lines = False
        space.show_region_toolbar = True
        space.show_region_ui = False
        space.show_gizmo_navigate = False
        frame_region(context, area, '2D')
    elif kind == 'SIDE':
        rv3d.view_perspective = 'ORTHO'
        rv3d.view_rotation = SIDE_ROT
        sh.type = 'SOLID'
        ov.show_floor = False
        ov.show_cursor = False
        ov.show_relationship_lines = False
        space.show_region_toolbar = False
        space.show_region_ui = False
        space.show_gizmo_navigate = False
        frame_region(context, area, '3D')
    else:  # MAIN
        rv3d.view_perspective = 'PERSP'
        rv3d.view_rotation = PERSP_ROT
        sh.type = 'SOLID'
        sh.color_type = 'MATERIAL'
        sh.show_backface_culling = False
        ov.show_relationship_lines = False
        space.show_region_ui = True
        frame_region(context, area, '3D')
        _defer_category(area)


def _defer_category(area):
    """Select the Clothing tab in the sidebar. It only takes once the region has
    been drawn, so it is applied from a timer rather than during the build."""
    def apply():
        try:
            r = _region(area, 'UI')
            if r:
                r.active_panel_category = "Clothing"
                area.tag_redraw()
        except Exception:
            pass
        return None
    try:
        bpy.app.timers.register(apply, first_interval=0.35)
    except Exception:
        pass


def _defer_properties_tab(screen):
    """Physics tab, applied late: setting it needs an active object that
    actually has physics, which may not be true while the workspace is built."""
    def apply():
        for a in screen.areas:
            if a.type == 'PROPERTIES':
                try:
                    a.spaces.active.context = 'PHYSICS'
                    a.tag_redraw()
                except Exception:
                    pass
        return None
    try:
        bpy.app.timers.register(apply, first_interval=0.5)
    except Exception:
        pass


def _defer_restore(prev_name, tries=8):
    """Keep putting the previously active workspace back until it sticks."""
    state = {"n": 0}

    def apply():
        state["n"] += 1
        try:
            win = bpy.context.window
            ws = bpy.data.workspaces.get(prev_name)
            if win is not None and ws is not None and win.workspace is not ws:
                win.workspace = ws
        except Exception:
            return None
        return 0.15 if state["n"] < tries else None

    try:
        bpy.app.timers.register(apply, first_interval=0.15)
    except Exception:
        pass


def build(context, activate=True):
    win = context.window
    if win is None:
        return False, "The workspace can only be built in the Blender UI, not in background mode"

    ws = bpy.data.workspaces.get(NAME)
    if ws is not None:
        if activate:
            win.workspace = ws
            return True, "Switched to the '%s' workspace" % NAME
        return True, "The '%s' workspace is already in this file" % NAME

    base = bpy.data.workspaces.get("Layout") or win.workspace
    prev = win.workspace
    try:
        win.workspace = base
        with context.temp_override(window=win):
            bpy.ops.workspace.duplicate()
    except Exception as e:
        win.workspace = prev
        return False, "Could not create the workspace: %s" % e

    ws = win.workspace
    if ws is base:
        cand = [w for w in bpy.data.workspaces if w.name.startswith(base.name) and w is not base]
        if cand:
            ws = cand[-1]
            win.workspace = ws
    ws.name = NAME
    screen = ws.screens[0]

    v3ds = [a for a in _areas_sorted(screen) if a.type == 'VIEW_3D']
    if not v3ds:
        return False, "No 3D viewport in the base workspace to split"
    main = v3ds[0]

    left = _split(context, win, screen, main, 'VERTICAL', 0.32)
    if left is None:
        _setup_view(context, main, 'MAIN')
        return True, "Workspace created (viewport split unavailable - single view)"
    # the split gives two areas; the left-hand one is the pattern column
    a, b = (left, main)
    if a.x > b.x:
        a, b = b, a
    pattern_col, main = a, b

    side = _split(context, win, screen, pattern_col, 'HORIZONTAL', 0.5)
    if side is not None:
        top, bottom = (pattern_col, side)
        if top.y < bottom.y:
            top, bottom = bottom, top
        _setup_view(context, top, 'PATTERN')
        _setup_view(context, bottom, 'SIDE')
    else:
        _setup_view(context, pattern_col, 'PATTERN')
    _setup_view(context, main, 'MAIN')

    _defer_properties_tab(screen)
    # put the tab at the end so the standard tab order is left as the user knows it
    try:
        with context.temp_override(window=win, workspace=ws, screen=screen):
            bpy.ops.workspace.reorder_to_back()
    except Exception:
        pass
    if not activate and prev is not None:
        # workspace.duplicate() activates the new workspace through a deferred
        # window update that lands after this function returns, so a direct
        # assignment here is overwritten. Re-assert it from a timer instead.
        win.workspace = prev
        _defer_restore(prev.name)
    return True, "Created the '%s' workspace" % NAME


def refresh_views(context):
    """Re-frame the pattern and body views of the current screen."""
    if context.screen is None:
        return
    for a in context.screen.areas:
        if a.type != 'VIEW_3D':
            continue
        rv3d = a.spaces.active.region_3d
        if rv3d.view_perspective == 'ORTHO' and (rv3d.view_rotation - FRONT_ROT).magnitude < 1e-3:
            frame_region(context, a, '2D')
        else:
            frame_region(context, a, '3D')


# ---------------------------------------------------------------- auto-create

_RETRY = [0]


def auto_enabled():
    try:
        prefs = bpy.context.preferences.addons[__package__].preferences
        return bool(prefs.auto_workspace)
    except Exception:
        return True


def ensure(context=None, activate=False):
    """Create the workspace in this file if it is not there yet."""
    if bpy.app.background:
        return False, "background mode"
    context = context or bpy.context
    if bpy.data.workspaces.get(NAME) is not None and not activate:
        return True, "already present"
    return build(context, activate=activate)


def _deferred_ensure():
    if bpy.app.background:
        return None
    win = getattr(bpy.context, "window", None)
    if win is None:                       # UI not up yet, try again shortly
        _RETRY[0] += 1
        return 0.5 if _RETRY[0] < 12 else None
    _RETRY[0] = 0
    try:
        if auto_enabled():
            ensure(bpy.context, activate=False)
    except Exception as e:
        print("[clothing_design] workspace auto-create failed:", e)
    return None


def schedule_ensure(delay=0.6):
    if bpy.app.background:
        return
    try:
        if bpy.app.timers.is_registered(_deferred_ensure):
            return
        bpy.app.timers.register(_deferred_ensure, first_interval=delay)
    except Exception:
        pass


@persistent
def _on_load(_dummy):
    _RETRY[0] = 0
    schedule_ensure(0.6)


def _workspace_menu(self, context):
    if bpy.data.workspaces.get(NAME) is None:
        self.layout.separator()
        self.layout.operator("cd.build_workspace", text=NAME, icon='MOD_CLOTH')


def register():
    if _on_load not in bpy.app.handlers.load_post:
        bpy.app.handlers.load_post.append(_on_load)
    try:
        bpy.types.TOPBAR_MT_workspace_menu.append(_workspace_menu)
    except Exception:
        pass
    schedule_ensure(0.8)


def unregister():
    if _on_load in bpy.app.handlers.load_post:
        bpy.app.handlers.load_post.remove(_on_load)
    try:
        bpy.types.TOPBAR_MT_workspace_menu.remove(_workspace_menu)
    except Exception:
        pass
    try:
        if bpy.app.timers.is_registered(_deferred_ensure):
            bpy.app.timers.unregister(_deferred_ensure)
    except Exception:
        pass
