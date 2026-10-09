# Clothing Design - cloth simulation, draping and finalising.
import bpy, bmesh, math
from contextlib import contextmanager
from mathutils import Vector, Quaternion
from . import patterns, build

COLLIDER_COLL = "CD_Colliders"


def collider_collection(context):
    """Collection holding the avatar. Must stay linked to the scene or Blender
    purges it on save and the cloth silently reverts to colliding with the
    whole scene."""
    coll = patterns.get_collection(context, COLLIDER_COLL)
    try:
        coll.hide_render = True
    except Exception:
        pass
    return coll


def garment_layers(context):
    """Every garment in the scene, innermost first."""
    gs = [o for o in context.scene.objects
          if o.cd.is_garment and o.data and len(o.data.vertices)]
    gs.sort(key=lambda o: (o.cd.layer, o.name))
    return gs


def make_collidable(ob):
    """Let other cloth collide with this garment."""
    mod = next((m for m in ob.modifiers if m.type == 'COLLISION'), None)
    if mod is None:
        mod = ob.modifiers.new("CD_Collision", 'COLLISION')
    cs = ob.collision
    if cs:
        cs.thickness_outer = 0.002
        cs.thickness_inner = 0.006
        cs.damping_factor = 0.5
        # fabric on fabric is not slick: with the default 5 an open jacket
        # slides off the shoulders of a layered outfit while its sleeve seams
        # pull it towards the arms
        cs.cloth_friction = 60.0
    return mod


def setup_layers(context):
    """Point each garment's cloth at the body plus everything worn under it.

    The collision is deliberately one-directional: an outer layer sees the
    inner ones, never the reverse. Letting two cloth objects collide with each
    other makes the depsgraph cyclic and Blender drops the relationship.
    """
    scn = context.scene
    av = scn.cd.avatar
    gs = garment_layers(context)
    if not gs:
        return 0
    for g in gs:
        make_collidable(g)
    n = 0
    for g in gs:
        coll = patterns.get_collection(context, "CD_Colliders_L%d" % g.cd.layer)
        try:
            coll.hide_render = True
        except Exception:
            pass
        for o in list(coll.objects):
            coll.objects.unlink(o)
        if av is not None:
            coll.objects.link(av)
        for other in gs:
            if other is not g and other.cd.layer < g.cd.layer:
                coll.objects.link(other)
        for mod in g.modifiers:
            if mod.type == 'CLOTH':
                mod.collision_settings.collection = coll
                n += 1
    return n


def ensure_collider(context, av):
    if av is None:
        return None
    coll = collider_collection(context)
    if av.name not in coll.objects:
        coll.objects.link(av)
    mod = next((m for m in av.modifiers if m.type == 'COLLISION'), None)
    if mod is None:
        mod = av.modifiers.new("CD_Collision", 'COLLISION')
    cs = av.collision
    if cs:
        cs.thickness_outer = 0.002
        cs.thickness_inner = 0.02
        cs.damping_factor = 0.3
        cs.cloth_friction = 60.0
    return mod


def setup_cloth(context, ob):
    scn = context.scene
    cd = scn.cd
    mod = next((m for m in ob.modifiers if m.type == 'CLOTH'), None)
    if mod is None:
        mod = ob.modifiers.new("CD_Cloth", 'CLOTH')
    s = mod.settings
    s.quality = cd.quality
    s.mass = cd.mass
    s.air_damping = cd.air_damping
    s.bending_model = 'ANGULAR'
    s.tension_stiffness = cd.stiff_tension
    s.compression_stiffness = cd.stiff_compress
    s.shear_stiffness = cd.stiff_shear
    s.bending_stiffness = cd.stiff_bend
    s.tension_damping = 15.0
    s.compression_damping = 15.0
    s.shear_damping = 5.0
    s.bending_damping = 0.5
    s.use_sewing_springs = True
    s.sewing_force_max = cd.sew_force
    # Taking the fabric in while the seams are still open fights the stitching,
    # so it is applied at the weld instead (see close_seams).
    s.shrink_min = 0.0

    cs = mod.collision_settings
    # 4 lets a collar tunnel into the neck when the shoulder pin releases
    # and the neckline snaps in; 6 catches it
    cs.collision_quality = 6
    cs.distance_min = cd.coll_distance
    cs.damping = 0.3
    cs.friction = 15.0
    cs.use_self_collision = cd.self_collision
    cs.self_distance_min = max(0.001, cd.coll_distance * 0.5)
    cs.self_friction = 2.0
    layered = [o for o in scn.objects if o.cd.is_garment and o.data and len(o.data.vertices)]
    if len(layered) > 1:
        cs.collection = patterns.get_collection(context, "CD_Colliders_L%d" % ob.cd.layer)
    else:
        cs.collection = collider_collection(context)

    order_modifiers(ob)
    pc = mod.point_cache
    pc.frame_start = scn.frame_current
    pc.frame_end = scn.frame_current + max(cd.stitch_frames + cd.settle_frames, 250)
    return mod


def reset_cache(ob):
    for mod in ob.modifiers:
        if mod.type == 'CLOTH':
            try:
                mod.point_cache.frame_start = bpy.context.scene.frame_current
            except Exception:
                pass


DISPLAY_MODS = {'SUBSURF', 'SOLIDIFY'}


@contextmanager
def sim_cage_only(ob):
    """Temporarily switch off the modifiers that change the vertex count.

    Freezing the shape and the grab tool both map evaluated vertices back onto
    the base mesh one-for-one, which a subdivision surface would break.
    """
    off = []
    for m in ob.modifiers:
        if m.type in DISPLAY_MODS and m.show_viewport:
            m.show_viewport = False
            off.append(m)
    try:
        yield
    finally:
        for m in off:
            m.show_viewport = True


@contextmanager
def cages_only(obs):
    """Drop the display modifiers on a set of objects for the duration.

    A garment used as a collider should present the surface it was simulated
    as, not the one it is displayed as. A finalized garment carries
    subdivision and solidify, and cloth simulated against that - a dense,
    double-walled shell - behaves quite differently: a t-shirt sewn over
    finalized trousers ended up 13 cm lower than the same t-shirt sewn over
    the same trousers before they were finalized.
    """
    off = []
    for ob in obs:
        if ob is None:
            continue
        for m in ob.modifiers:
            if m.type in DISPLAY_MODS and m.show_viewport:
                m.show_viewport = False
                off.append(m)
    try:
        yield
    finally:
        for m in off:
            m.show_viewport = True


MOD_ORDER = ('ARMATURE', 'CLOTH', 'SUBSURF', 'SOLIDIFY')


def order_modifiers(ob):
    """Deform, then solve, then smooth, then thicken.

    The subdivision has to sit after the cloth or the solver runs on the
    subdivided mesh instead of the cage - same result, many times the cost.
    """
    desired = []
    for t in MOD_ORDER:
        desired += [m for m in ob.modifiers if m.type == t]
    desired += [m for m in ob.modifiers if m.type not in MOD_ORDER]
    try:
        with bpy.context.temp_override(object=ob, active_object=ob):
            for i, m in enumerate(desired):
                if ob.modifiers.find(m.name) != i:
                    bpy.ops.object.modifier_move_to_index(modifier=m.name, index=i)
    except Exception as e:
        print("[clothing_design] modifier ordering failed:", e)


def add_subdivision(ob, levels, render_levels):
    mod = next((m for m in ob.modifiers if m.type == 'SUBSURF'), None)
    if levels <= 0 and render_levels <= 0:
        if mod:
            ob.modifiers.remove(mod)
        return None
    if mod is None:
        mod = ob.modifiers.new("CD_Subdivision", 'SUBSURF')
    mod.subdivision_type = 'CATMULL_CLARK'
    mod.levels = levels
    mod.render_levels = max(levels, render_levels)
    mod.use_creases = True
    try:
        mod.boundary_smooth = 'PRESERVE_CORNERS'
    except Exception:
        pass
    order_modifiers(ob)
    return mod


def bake_shape(context, ob):
    """Copy the simulated shape into the base mesh."""
    with sim_cage_only(ob):
        context.view_layer.update()
        dg = context.evaluated_depsgraph_get()
        ev = ob.evaluated_get(dg)
        try:
            me = ev.to_mesh()
        except Exception:
            return False
        if len(me.vertices) != len(ob.data.vertices):
            ev.to_mesh_clear()
            return False
        coords = [v.co.copy() for v in me.vertices]
        ev.to_mesh_clear()
    for v, c in zip(ob.data.vertices, coords):
        v.co = c
    ob.data.update()
    return True


def weld_seams(ob, max_gap):
    """Close every stitch: each sewing edge's two ends are merged at their
    midpoint. Distance-based merging alone leaves stitches wider than the
    threshold open, so the seam has to be followed explicitly."""
    me = ob.data
    bm = bmesh.new()
    bm.from_mesh(me)
    bm.verts.ensure_lookup_table()
    bm.edges.ensure_lookup_table()

    sew = [e for e in bm.edges if not e.link_faces]
    parent = {}

    def find(v):
        root = v
        while parent.get(root, root) is not root:
            root = parent[root]
        while parent.get(v, v) is not v:          # path compression
            parent[v], v = root, parent[v]
        return root

    skipped = 0
    for e in sew:
        a, b = e.verts
        if (a.co - b.co).length > max_gap:
            skipped += 1
            continue
        ra, rb = find(a), find(b)
        if ra is not rb:
            parent[rb] = ra

    groups = {}
    for e in sew:
        for v in e.verts:
            groups.setdefault(find(v), set()).add(v)

    targetmap = {}
    merged = 0
    for root, members in groups.items():
        if len(members) < 2:
            continue
        mid = Vector((0, 0, 0))
        for v in members:
            mid += v.co
        mid /= len(members)
        root.co = mid
        for v in members:
            if v is not root:
                targetmap[v] = root
                merged += 1
    if targetmap:
        bmesh.ops.weld_verts(bm, targetmap=targetmap)

    leftovers = [e for e in bm.edges if not e.link_faces]
    if leftovers:
        bmesh.ops.delete(bm, geom=leftovers, context='EDGES')
    stray = [v for v in bm.verts if not v.link_edges]
    if stray:
        bmesh.ops.delete(bm, geom=stray, context='VERTS')
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    bm.to_mesh(me)
    bm.free()
    me.update()
    return merged, skipped


def close_stray_holes(ob, stretch=2.5, tiny=12):
    """Fill boundary loops left behind by the weld.

    A real opening - neck, cuff, hem - has edges at the mesh resolution. A slit
    left by a stitch that had to span a long gap has edges several times that,
    and corner junctions leave holes of only a few edges. Both get filled; the
    genuine openings are left alone.
    """
    me = ob.data
    bm = bmesh.new()
    bm.from_mesh(me)
    bm.edges.ensure_lookup_table()

    lengths = sorted(e.calc_length() for e in bm.edges)
    if not lengths:
        bm.free()
        return 0
    median = lengths[len(lengths) // 2]

    bnd = [e for e in bm.edges if len(e.link_faces) == 1]
    adj = {}
    for e in bnd:
        for v in e.verts:
            adj.setdefault(v, []).append(e)
    seen, loops = set(), []
    for e in bnd:
        if e in seen:
            continue
        stack, comp = [e], []
        while stack:
            x = stack.pop()
            if x in seen:
                continue
            seen.add(x)
            comp.append(x)
            for v in x.verts:
                for y in adj[v]:
                    if y not in seen:
                        stack.append(y)
        loops.append(comp)

    filled = 0
    for comp in loops:
        mean_len = sum(e.calc_length() for e in comp) / len(comp)
        if mean_len > median * stretch or len(comp) <= tiny:
            try:
                bmesh.ops.holes_fill(bm, edges=comp, sides=0)
                filled += 1
            except Exception:
                pass
    if filled:
        tris = [f for f in bm.faces if len(f.verts) > 4]
        if tris:
            bmesh.ops.triangulate(bm, faces=tris)
        bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
        bm.to_mesh(me)
        me.update()
    bm.free()
    return filled


def add_thickness(ob, thickness):
    mod = next((m for m in ob.modifiers if m.type == 'SOLIDIFY'), None)
    if thickness <= 0.0:
        if mod:
            ob.modifiers.remove(mod)
        return None
    if mod is None:
        mod = ob.modifiers.new("CD_Thickness", 'SOLIDIFY')
    mod.thickness = thickness
    mod.offset = 0.0
    mod.use_even_offset = False      # blows up on tight folds
    mod.use_rim = True
    mod.use_quality_normals = True
    order_modifiers(ob)
    return mod


def smooth_skin_weights(ob, arm, iterations=20, factor=0.5, min_weight=1e-4):
    """Blend bone influences across neighbouring vertices.

    The weight transfer maps each vertex to the nearest body polygon, so at the
    crotch - where the two thighs nearly touch - neighbouring vertices land on
    opposite legs. As the legs separate those neighbours fly apart and tear the
    garment open. Blender's vertex_group_smooth operator does nothing when
    driven headlessly, so the smoothing is done here directly.
    """
    bones = {b.name for b in arm.data.bones}
    names = {vg.index: vg.name for vg in ob.vertex_groups}
    bone_groups = {i for i, n in names.items() if n in bones}
    if not bone_groups:
        return 0

    me = ob.data
    adj = [[] for _ in me.vertices]
    for e in me.edges:
        a, b = e.vertices
        adj[a].append(b)
        adj[b].append(a)

    W = [{g.group: g.weight for g in v.groups if g.group in bone_groups}
         for v in me.vertices]

    for _ in range(iterations):
        nxt = []
        for i, w in enumerate(W):
            neigh = adj[i]
            if not neigh:
                nxt.append(w)
                continue
            acc = {}
            for j in neigh:
                for k, val in W[j].items():
                    acc[k] = acc.get(k, 0.0) + val
            inv = 1.0 / len(neigh)
            new = {}
            for k in set(w) | set(acc):
                v = (1.0 - factor) * w.get(k, 0.0) + factor * acc.get(k, 0.0) * inv
                if v > min_weight:
                    new[k] = v
            nxt.append(new)
        W = nxt

    groups = {i: ob.vertex_groups[i] for i in bone_groups}
    changed = 0
    for i, w in enumerate(W):
        total = sum(w.values())
        if total <= 1e-9:
            continue
        had = {g.group for g in me.vertices[i].groups if g.group in bone_groups}
        for k, val in w.items():
            groups[k].add([i], val / total, 'REPLACE')
        for k in had - set(w):
            groups[k].remove([i])
        changed += 1
    return changed


def bind_to_armature(context, ob, av):
    """Transfer skin weights from the avatar so the garment follows the rig."""
    from . import avatar as av_mod
    arm = av_mod.find_armature(av)
    if arm is None:
        return False, "avatar has no armature"

    for vg in list(ob.vertex_groups):
        if vg.name in {b.name for b in arm.data.bones}:
            ob.vertex_groups.remove(vg)

    prev_active = context.view_layer.objects.active
    prev_sel = [o for o in context.selected_objects]
    try:
        for o in prev_sel:
            o.select_set(False)
        av.select_set(True)
        ob.select_set(True)
        context.view_layer.objects.active = av
        with context.temp_override(object=av, active_object=av,
                                   selected_objects=[av, ob],
                                   selected_editable_objects=[av, ob]):
            bpy.ops.object.data_transfer(
                data_type='VGROUP_WEIGHTS',
                use_create=True,
                vert_mapping='POLYINTERP_NEAREST',
                layers_select_src='ALL',
                layers_select_dst='NAME',
                mix_mode='REPLACE')
    except Exception as e:
        return False, "weight transfer failed: %s" % e
    finally:
        for o in context.selected_objects:
            o.select_set(False)
        for o in prev_sel:
            try:
                o.select_set(True)
            except Exception:
                pass
        context.view_layer.objects.active = prev_active

    mod = next((m for m in ob.modifiers if m.type == 'ARMATURE'), None)
    if mod is None:
        mod = ob.modifiers.new("CD_Armature", 'ARMATURE')
    mod.object = arm
    order_modifiers(ob)

    smooth_skin_weights(ob, arm)
    return True, "bound to %s" % arm.name


def close_seams(context, ob):
    """Freeze the stitched shape, weld the seams into real shared edges and put a
    fresh cloth solver on the result. Without this the sewing springs keep pulling
    for the rest of the simulation and crush the garment into wrinkles."""
    scn = context.scene
    bake_shape(context, ob)
    for mod in list(ob.modifiers):
        if mod.type == 'CLOTH':
            ob.modifiers.remove(mod)
    merged, skipped = weld_seams(ob, scn.cd.weld_dist)
    # A weld merges each seam pair to its midpoint. Where the two edges sit
    # either side of a body ridge - the collar ends astride the trapezius -
    # that midpoint lands inside the body, and a cloth vert that starts a
    # solve inside a collider is trapped there for good. Push them back out
    # while the mesh is being edited anyway.
    from . import avatar as _av
    bvh = _av.body_bvh(context)
    if bvh is not None:
        for v in ob.data.vertices:
            hit = bvh.find_nearest(v.co)
            if hit is not None and hit[0] is not None:
                gap = (v.co - hit[0]).dot(hit[1])
                if gap < 0.002:
                    v.co = hit[0] + hit[1] * 0.003
    setup_cloth(context, ob)
    for mod in ob.modifiers:
        if mod.type == 'CLOTH':
            mod.settings.shrink_min = scn.cd.shrink
    # Force the fresh solver to initialise at this frame. Stepping straight on to
    # the next frame leaves the new cache uninitialised and the garment drops off
    # the body in a single step.
    scn.frame_set(scn.frame_current)
    try:
        dg = context.evaluated_depsgraph_get()
        ev = ob.evaluated_get(dg)
        ev.to_mesh()
        ev.to_mesh_clear()
    except Exception:
        pass
    return merged, skipped


def set_gravity(ob, factor):
    for mod in ob.modifiers:
        if mod.type == 'CLOTH':
            try:
                mod.settings.effector_weights.gravity = factor
            except Exception:
                pass


PIN_GROUP = "CD_PIN_SHOULDER"
# fraction of the stitch phase that holds the full collar; after it only the
# back collar stays held (1.0 = held to the weld)
PIN_HOLD = 0.6


def pin_shoulders(context, ob, torso_anchors=('TORSO_FRONT', 'TORSO_BACK')):
    """Hold the torso panels' collar line still while the seams stitch closed.

    A sleeved top is sewn to sleeves already wrapped around arms held out and
    down, and those cap seams pull the whole garment down the body while it
    has nothing to hang from yet. Alone on the body, friction wins; over a
    layered outfit it does not, and the jacket ends up around the waist.
    Pinning the collar band during the stitch is the tailor's hand holding
    the shoulders on the dress form; the weld then takes over and the settle
    runs unpinned. Calling it again with only TORSO_BACK re-pins just the
    back collar - the part a jacket actually hangs from - so the front can
    draw in to the neck before it is welded."""
    from . import build, avatar as _av
    m = _av.measure(context)
    if m is None:
        return False
    pieces = build.garment_pieces(context, ob.cd.garment)
    anchors = {p.name: p.cd.anchor for p in pieces}
    if not any(a in ('ARM_L', 'ARM_R') for a in anchors.values()):
        return False                      # nothing pulls a sleeveless top down
    torso = {n for n, a in anchors.items() if a in torso_anchors}
    if not torso:
        return False
    z_lo = _av.z_of(m, "shoulder") - 0.01
    gname = {g.index: g.name for g in ob.vertex_groups}
    vg = ob.vertex_groups.get(PIN_GROUP)
    if vg:
        ob.vertex_groups.remove(vg)
    vg = ob.vertex_groups.new(name=PIN_GROUP)
    mw = ob.matrix_world
    idx = [v.index for v in ob.data.vertices
           if (mw @ v.co).z >= z_lo
           and any(gname.get(g.group) in torso for g in v.groups if g.weight > 0.5)]
    if len(idx) < 6:
        ob.vertex_groups.remove(vg)
        return False
    vg.add(idx, 1.0, 'REPLACE')
    for mod in ob.modifiers:
        if mod.type == 'CLOTH':
            mod.settings.vertex_group_mass = PIN_GROUP
            mod.settings.pin_stiffness = 25.0
    return True


def unpin_shoulders(ob):
    for mod in ob.modifiers:
        if mod.type == 'CLOTH' and mod.settings.vertex_group_mass == PIN_GROUP:
            mod.settings.vertex_group_mass = ""
    vg = ob.vertex_groups.get(PIN_GROUP)
    if vg:
        ob.vertex_groups.remove(vg)


def kick_solver(context, ob):
    """Initialise a freshly built cloth solver at the current frame.

    Blender keys a modifier's point cache by name, so a rebuilt "CD_Cloth"
    inherits the cache left by the pre-weld mesh - a different vertex count,
    which evaluates to garbage and drops the garment into free fall. Stepping
    onto the cache's own start frame is what makes the solver re-initialise
    from the mesh instead of reading that cache.
    """
    scn = context.scene
    scn.frame_set(scn.frame_current)
    try:
        dg = context.evaluated_depsgraph_get()
        ev = ob.evaluated_get(dg)
        ev.to_mesh()
        ev.to_mesh_clear()
    except Exception:
        pass


def relax_garment(context, ob, take_in=0.06, phase_bend=2.0, relax_bend=8.0,
                  frames=60, relax_frames=90):
    """Finishing pass: steam the garment onto the body, then let it rest.

    The weld bakes the mid-drape shape as the cloth's new rest shape, and at
    fabric stiffness the bending springs then *hold* that ballooned memory -
    a settle can run forever without the garment ever lying down (measured:
    150 extra frames moved the chest standoff by 1 mm). This pass drops the
    bending to near-zero and takes the fabric in a little so it wraps the
    body (the take-in is also what keeps a soft garment from sliding off the
    shoulders - relaxing without any pull lost the jacket to the ribcage),
    freezes that as the new rest shape, and re-settles at a soft but held
    stiffness so the result reads as resting cloth, not shrink wrap. The
    re-settle is long because here it actually does something: settling at
    fabric stiffness never lies a garment down (the rest shape holds it),
    but at bending 8 a standing collar has time to fall onto the shoulders.
    """
    scn = context.scene
    cloth = next((m for m in ob.modifiers if m.type == 'CLOTH'), None)
    if cloth is None:
        ensure_collider(context, scn.cd.avatar)
        setup_layers(context)
        cloth = setup_cloth(context, ob)
        kick_solver(context, ob)
    if cloth is None:
        return False
    st = cloth.settings
    st.bending_stiffness = phase_bend
    if take_in > 0.0:
        st.shrink_min = take_in
    cloth.point_cache.frame_end = max(cloth.point_cache.frame_end,
                                      scn.frame_current + frames + relax_frames + 10)
    for g2 in [o for o in scn.objects if o.cd.is_garment]:
        for m2 in g2.modifiers:
            if m2.type == 'CLOTH':
                m2.point_cache.frame_end = max(m2.point_cache.frame_end,
                                               scn.frame_current + frames + relax_frames + 10)
    for _ in range(frames):
        scn.frame_set(scn.frame_current + 1)
    bake_shape(context, ob)
    for m in list(ob.modifiers):
        if m.type == 'CLOTH':
            ob.modifiers.remove(m)
    lift_off_layers(context, ob)
    setup_cloth(context, ob)
    cloth = next(m for m in ob.modifiers if m.type == 'CLOTH')
    cloth.settings.bending_stiffness = relax_bend
    cloth.settings.shrink_min = 0.0
    kick_solver(context, ob)
    for _ in range(relax_frames):
        scn.frame_set(scn.frame_current + 1)
    return True


# The finishing pass relaxes the OUTERMOST garment only - the one actually
# on show. Taking an inner top in rolls its collar up the neck and it stands
# proud of whatever is worn over it, and softening trousers slides their
# waistband down the hips (the crisp yoke is what keeps them up). Inner
# layers still get lifted clear of each other, which is what stopped a tank
# poking through the jacket; they just do not get shrunk.
RELAX_SKIP = ("trouser", "skirt", "jumpsuit")


def worn_over_bvh(context, ob):
    """BVH of everything this garment is worn over: the body plus every
    inner layer, at their current shapes."""
    from mathutils.bvhtree import BVHTree
    verts, tris = [], []
    under = [context.scene.cd.avatar] + [g for g in garment_layers(context)
                                         if g is not ob and g.cd.layer < ob.cd.layer]
    for src in under:
        if src is None or src.type != 'MESH':
            continue
        with sim_cage_only(src):
            context.view_layer.update()
            e = src.evaluated_get(context.evaluated_depsgraph_get())
            try:
                me = e.to_mesh()
                me.calc_loop_triangles()
            except Exception:
                continue
            mw = e.matrix_world
            base = len(verts)
            verts += [mw @ v.co for v in me.vertices]
            tris += [tuple(base + i for i in t.vertices) for t in me.loop_triangles]
            e.to_mesh_clear()
    if not tris:
        return None
    return BVHTree.FromPolygons(verts, tris)


def lift_off_layers(context, ob, clearance=0.007, max_move=0.03):
    """Push the garment's base mesh clear of everything worn under it.

    Taking a garment in pulls it hard against the inner layers, and the
    solver's collision cannot always hold a thin shirt against that pull:
    the jacket ends up drawn through the tank, which then pokes out of it
    in patches. This runs on the baked shape, before the solver restarts,
    so the relaxed garment starts outside everything it is worn over."""
    bvh = worn_over_bvh(context, ob)
    if bvh is None:
        return 0
    mw = ob.matrix_world
    inv = mw.inverted()
    moved = 0
    for v in ob.data.vertices:
        p = mw @ v.co
        hit = bvh.find_nearest(p)
        if hit is None or hit[0] is None:
            continue
        loc, nor = hit[0], hit[1]
        gap = (p - loc).dot(nor)
        if gap >= clearance:
            continue
        v.co = inv @ (p + nor * min(clearance - gap, max_move))
        moved += 1
    if moved:
        ob.data.update()
    return moved


def garment_hover(context, ob):
    """Median standoff between the garment's torso band and whatever it is
    worn over - the body plus every inner layer - in metres. Measuring to
    the body alone reads a jacket sitting snugly on a t-shirt as ballooned,
    because the shirt itself is a centimetre thick."""
    from . import avatar as _av
    m = _av.measure(context)
    bvh = worn_over_bvh(context, ob)
    if m is None or bvh is None:
        return 0.0
    z_lo = _av.z_of(m, "waist")
    z_hi = _av.z_of(m, "shoulder") - 0.03
    dg = context.evaluated_depsgraph_get()
    ev = ob.evaluated_get(dg)
    mw = ev.matrix_world
    gaps = []
    for v in ev.data.vertices:
        p = mw @ v.co
        if z_lo < p.z < z_hi and abs(p.x) < 0.16:
            hit = bvh.find_nearest(p)
            if hit is not None and hit[0] is not None:
                gaps.append((p - hit[0]).length)
    gaps.sort()
    return gaps[len(gaps) // 2] if gaps else 0.0


def freeze_garment(context, ob):
    """Bake the simulated shape and drop the solver, keeping the collision
    modifier: the garment becomes finished, static clothing that outer
    layers still drape against."""
    if not any(m.type == 'CLOTH' for m in ob.modifiers):
        return False
    bake_shape(context, ob)
    for m in list(ob.modifiers):
        if m.type == 'CLOTH':
            ob.modifiers.remove(m)
    return True


def relax_outfit(context):
    """Finish the outfit: freeze the under-layers where they settled, then
    run the relax pass over the outerwear. Freezing matters - the relax
    advances the simulation, and a low-rise waistband that held for the
    normal settle window will creep down the hips given another hundred
    frames of sim it was never meant to run."""
    scn = context.scene
    prev = scn.cd.garment_name
    layers = garment_layers(context)
    outermost = layers[-1] if layers else None
    plan = [(g, g is outermost and not any(k in g.cd.garment.lower() for k in RELAX_SKIP))
            for g in layers]
    # Freeze the whole outfit first, then relax exactly one garment at a
    # time. Relaxing advances the scene by a hundred frames, and any other
    # garment still carrying a solver would drift through them unwatched -
    # which is precisely how an inner tank ends up poking out of the jacket
    # worn over it. A frozen garment holds its shape and still collides.
    for g, _ in plan:
        freeze_garment(context, g)
    n = 0
    # innermost first: an outer layer is lifted, measured and relaxed against
    # inner layers already in their final shape - what it is really worn over
    for g, relaxes in plan:
        # De-interleave first, always. A jacket sleeve is arranged around the
        # arm, not around the arm plus the shirt already on it, so outerwear
        # can come out of the sew stage threaded through the layer beneath -
        # and a garment already tangled measures as snug, so leaving this to
        # the relax test would let exactly the worst case slip through.
        moved = lift_off_layers(context, g)
        if not relaxes:
            continue
        # a garment already lying down is left alone; 1 cm of take-in per
        # centimetre of standoff beyond the collision gap layered cloth needs
        # capped at 6%: taking a garment in shortens it as well as narrowing
        # it, and past this the hem climbs far enough to read as cropped
        take = min(0.06, max(0.0, (garment_hover(context, g) - 0.012) * 10.0))
        # anything that had to be lifted is re-seated even if it now measures
        # snug: the lift leaves it standing off the layer it was pulled out of
        if moved > max(20, len(g.data.vertices) // 100):
            take = max(take, 0.03)
        if take >= 0.02:
            scn.cd.garment_name = g.cd.garment
            if relax_garment(context, g, take_in=take):
                n += 1
            freeze_garment(context, g)
    scn.cd.garment_name = prev
    return n


# ---------------------------------------------------------------- walk test

# Bone roles for the walk cycle, in the same lowercase-substring style the
# measuring code uses, so a CC4, Mixamo or Rigify character all resolve.
WALK_BONES = {
    "hips":    ["mixamorig:hips", "cc_base_pelvis", "pelvis", "hips"],
    "spine":   ["mixamorig:spine1", "cc_base_spine01", "spine.002", "spine01", "spine"],
    "thigh_l": ["mixamorig:leftupleg", "cc_base_l_thigh", "thigh.l"],
    "thigh_r": ["mixamorig:rightupleg", "cc_base_r_thigh", "thigh.r"],
    "calf_l":  ["mixamorig:leftleg", "cc_base_l_calf", "shin.l"],
    "calf_r":  ["mixamorig:rightleg", "cc_base_r_calf", "shin.r"],
    "foot_l":  ["mixamorig:leftfoot", "cc_base_l_foot", "foot.l"],
    "foot_r":  ["mixamorig:rightfoot", "cc_base_r_foot", "foot.r"],
    "arm_l":   ["mixamorig:leftarm", "cc_base_l_upperarm", "upper_arm.l"],
    "arm_r":   ["mixamorig:rightarm", "cc_base_r_upperarm", "upper_arm.r"],
    "farm_l":  ["mixamorig:leftforearm", "cc_base_l_forearm", "forearm.l"],
    "farm_r":  ["mixamorig:rightforearm", "cc_base_r_forearm", "forearm.r"],
}

WALK_ACTION = "CD_Walk"


def _local_axis(rig, pb, world_axis):
    """The bone-local axis that points along a world axis in the rest pose.

    Rigs disagree about which way a bone's own X, Y and Z point, so keying a
    named local axis swings one character's leg forward and another's
    sideways. Converting the world axis into each bone's rest frame keeps the
    same walk working on any of them.
    """
    m = (rig.matrix_world @ pb.bone.matrix_local).to_3x3()
    try:
        v = m.inverted() @ world_axis
    except ValueError:
        return Vector((1.0, 0.0, 0.0))
    return v.normalized() if v.length > 1e-9 else Vector((1.0, 0.0, 0.0))


def action_fcurves(act):
    """Every F-curve in an action, on old and new Blender alike.

    Blender 5 replaced the flat Action.fcurves list with layers, strips and
    channelbags; 4.x and earlier only have the flat list. The walk keys the
    same way either way, so this is the only place that has to care.
    """
    if act is None:
        return []
    flat = getattr(act, "fcurves", None)
    if flat is not None:
        return list(flat)
    out = []
    for layer in getattr(act, "layers", []):
        for strip in getattr(layer, "strips", []):
            for bag in getattr(strip, "channelbags", []):
                out += list(bag.fcurves)
    return out


def clear_walk(rig):
    """Drop the walk action and put the rig back in its rest pose."""
    if rig is None:
        return False
    ad = rig.animation_data
    if ad and ad.action and ad.action.name.startswith(WALK_ACTION):
        act = ad.action
        rig.animation_data_clear()
        if act.users == 0:
            bpy.data.actions.remove(act)
    for pb in rig.pose.bones:
        pb.matrix_basis.identity()
    return True


# Two gaits. The catwalk numbers are measured off reference footage - cadence,
# stride, hip sway, pelvis roll and shoulder counter-rotation - because what
# separates a runway walk from a plain one is not the legs, which do much the
# same thing, but how much the pelvis and torso move over them. Measurements
# of how a person walks, not anybody's animation data.
#
#                     ordinary   catwalk   (catwalk measured from reference)
#   frames per stride    32         70     35 frames a step, deliberate
#   hip sway            1.3 cm    6.4 cm   12.8 cm peak to peak
#   pelvis roll          3.4 deg  11.5 deg 22.9 deg peak to peak
#   torso counter-rot    5.7 deg  16.4 deg 32.7 deg peak to peak
#   cross-over           none      9 deg   feet land on the centre line
WALK_STYLES = {
    'WALK':    dict(period=32, stride=0.32, arm_swing=0.26, bob=0.022,
                    sway=0.6, roll=0.06, torso=0.10, cross=0.0),
    'CATWALK': dict(period=70, stride=0.34, arm_swing=0.20, bob=0.022,
                    sway=2.9, roll=0.16, torso=0.29, cross=0.055),
}


def walk_cycle(context, av, period=32, stride=0.32, arm_swing=0.26, bob=0.022,
               arm_down=0.75, sway=0.6, roll=0.06, torso=0.10, cross=0.0):
    """Key a walk-in-place cycle on the avatar's rig.

    Walk in place rather than travelling: the point is to watch the garment
    move, and a character that walks out of frame has to be chased with the
    camera. Everything is driven off the body's own side axis, and the action
    is given a cycle modifier so it loops for as long as you play it.
    """
    from . import avatar as _av
    if av is None:
        return None, "no avatar"
    rig = _av.find_armature(av)
    if rig is None:
        return None, "the avatar has no armature to animate"

    fwd, side = _av.basis(context.scene.cd.facing)
    bones = {}
    for role, keys in WALK_BONES.items():
        pb = _av._find_bone(rig, keys)
        if pb is not None:
            bones[role] = pb
    if not any(k in bones for k in ("thigh_l", "thigh_r")):
        return None, "could not find leg bones on %s" % rig.name

    clear_walk(rig)
    rig.animation_data_create()
    act = bpy.data.actions.new(WALK_ACTION)
    rig.animation_data.action = act
    for pb in rig.pose.bones:
        pb.rotation_mode = 'QUATERNION'

    P = max(8, int(period))
    step = max(1, P // 16)

    # Sign convention. Turning a hanging limb by a POSITIVE angle about the
    # body's side axis carries it BACKWARDS - rotate (0,0,-1) about the
    # character's left and it swings behind. So every amplitude below is
    # written as the forward swing a reader expects, and the sign is applied
    # here, once. Getting this backwards makes the whole cycle read as
    # walking in reverse, which is exactly how it first came out.
    FWD = -1.0

    def swing(role, amp_fwd, phase, fold=None, drop=0.0, tuck=0.0):
        """Key one bone. amp_fwd is a forward swing; fold='back' or 'fwd'
        makes the joint hinge one way only, as a knee or an elbow does.

        drop brings a limb in towards the body about the forward axis. The
        avatar stands with its arms held out so garments drape clear of the
        ribs, and a walk that only swings them fore and aft leaves the
        character marching with its arms still out sideways.
        """
        pb = bones.get(role)
        if pb is None:
            return
        axis = _local_axis(rig, pb, side)
        # `tuck` pulls the limb in towards the body's midline as it swings
        # forward. It is what puts one foot in front of the other instead of
        # on two parallel tracks, and it is the single thing that reads as a
        # runway walk rather than a walk.
        ax_in = _local_axis(rig, pb, fwd) if tuck else None
        # Sign: rotating the left thigh positively about the forward axis
        # carries it *outwards*, so the inward tuck is negative on the left.
        # Backwards, and a runway walk comes out as a series of side splits.
        tuck_sgn = -1.0 if role.endswith("_l") else 1.0
        q_drop = None
        if drop:
            # +drop lowers the character's right arm, -drop the left
            sgn = -1.0 if role.endswith("_l") else 1.0
            q_drop = Quaternion(_local_axis(rig, pb, fwd), sgn * drop)
        for f in range(0, P + 1, step):
            t = 2.0 * math.pi * f / P + phase
            a = math.sin(t)
            if fold == 'back':
                ang = amp_fwd * max(0.0, a)          # knee: heel toward the seat
            elif fold == 'fwd':
                ang = FWD * amp_fwd * max(0.0, a)    # elbow: hand toward the chest
            else:
                ang = FWD * amp_fwd * a
            q = Quaternion(axis, ang)
            if ax_in is not None:
                q = q @ Quaternion(ax_in, tuck_sgn * tuck * max(0.0, a))
            pb.rotation_quaternion = (q @ q_drop) if q_drop else q
            pb.keyframe_insert("rotation_quaternion", frame=f + 1)

    swing("thigh_l", stride, 0.0, tuck=cross)
    swing("thigh_r", stride, math.pi, tuck=cross)
    # the knee folds through the back half of that leg's stride
    swing("calf_l", stride * 1.25, math.pi * 1.15, fold='back')
    swing("calf_r", stride * 1.25, math.pi * 0.15, fold='back')
    swing("foot_l", stride * 0.30, math.pi * 0.30)
    swing("foot_r", stride * 0.30, math.pi * 1.30)
    # arms counter-swing against the same-side leg
    swing("arm_l", arm_swing, math.pi, drop=arm_down)
    swing("arm_r", arm_swing, 0.0, drop=arm_down)
    swing("farm_l", arm_swing * 0.50, math.pi * 0.9, fold='fwd')
    swing("farm_r", arm_swing * 0.50, math.pi * 1.9, fold='fwd')

    # the torso counter-rotates a little about the vertical
    # The spine does two things at once and they have to be keyed together.
    # It counter-rotates against the pelvis about the vertical, and it takes
    # the pelvis roll back out - the hips are the root of the skeleton, so
    # rolling them 9 degrees rolls the head with them and the figure lists
    # like a ship. Done as a second pass this read rotation_quaternion without
    # a frame_set, so it compounded whatever the first pass happened to leave
    # behind rather than that frame's value, and bent her double.
    spine = bones.get("spine")
    if spine is not None:
        up = _local_axis(rig, spine, Vector((0.0, 0.0, 1.0)))
        ax_s = _local_axis(rig, spine, fwd)
        for f in range(0, P + 1, step):
            t = 2.0 * math.pi * f / P
            q = Quaternion(up, torso * math.sin(t))
            if roll:
                q = q @ Quaternion(ax_s, -roll * 0.85 * math.sin(t))
            spine.rotation_quaternion = q
            spine.keyframe_insert("rotation_quaternion", frame=f + 1)

    # hips bob twice per stride and sway once, which is what makes a walk
    # read as weight shifting rather than legs waving
    hips = bones.get("hips")
    if hips is not None:
        rest = hips.location.copy()
        for f in range(0, P + 1, step):
            t = 2.0 * math.pi * f / P
            hips.location = rest + Vector((0.0, 0.0, -bob * abs(math.sin(t)))) \
                + side * (bob * sway * math.sin(t))
            hips.keyframe_insert("location", frame=f + 1)
        axis = _local_axis(rig, hips, fwd)
        for f in range(0, P + 1, step):
            t = 2.0 * math.pi * f / P
            hips.rotation_quaternion = Quaternion(axis, roll * math.sin(t))
            hips.keyframe_insert("rotation_quaternion", frame=f + 1)


    for fc in action_fcurves(act):
        for kp in fc.keyframe_points:
            kp.interpolation = 'BEZIER'
        if not any(mo.type == 'CYCLES' for mo in fc.modifiers):
            fc.modifiers.new('CYCLES')

    scn = context.scene
    scn.frame_start = 1
    scn.frame_end = P
    scn.frame_set(1)
    return act, "%d-frame walk on %s" % (P, rig.name)
