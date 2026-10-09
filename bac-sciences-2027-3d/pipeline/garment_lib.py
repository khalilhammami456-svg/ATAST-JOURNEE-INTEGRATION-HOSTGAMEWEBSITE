"""Garment construction helpers on top of the opensew-2 Blender add-on (GPL-3.0-or-later).

Headless usage (bpy 5.2 wheel):
    import garment_lib as gl
    gl.boot("MAN")                                  # fresh scene + CC0 fitting avatar
    g = gl.draft(preset_fn, "Hoodie", fit=0.3)      # pattern pieces -> garment mesh
    gl.assign_pattern_uv(g)                         # pattern-space UVs + atlas manifest
    gl.sew(g)                                       # stitch, weld, settle (cloth sim)
    gl.finalize(g)                                  # freeze, thickness, subsurf, bind to rig
    gl.pose_arms(0.7)                               # lower the arms for display
"""
import bpy, bmesh, sys, os, math, json, time
from mathutils import Vector

HERE = os.path.dirname(os.path.abspath(__file__))
OS2 = os.path.join(HERE, "third_party", "opensew2")
if OS2 not in sys.path:
    sys.path.insert(0, OS2)

cd = {}      # modules, filled by boot()


def boot(figure="MAN", fresh=True):
    """Fresh empty scene, add-on enabled, default avatar imported and measured."""
    if fresh:
        bpy.ops.wm.read_homefile(use_empty=True)
    bpy.ops.preferences.addon_enable(module="clothing_design")
    from clothing_design import avatar, library, build, sim, patterns
    cd.update(avatar=avatar, library=library, build=build, sim=sim, patterns=patterns)
    bpy.context.scene.cd.live_sync = False       # property updates must never rebuild a simulated garment
    bpy.ops.cd.import_character(figure=figure)
    m = avatar.measure(bpy.context, force=True)
    return m


def cfg(**kw):
    """Set scene.cd simulation properties (fabric, resolution, stitch_frames, ...)."""
    scn = bpy.context.scene
    for k, v in kw.items():
        setattr(scn.cd, k, v)
    return scn.cd


def draft(preset_fn, name, fit=0.2, **kw):
    """Build pattern pieces + seams from a preset function and join them into the garment mesh.
    Mirrors the add-on's own Add Garment operator so custom presets work headless."""
    ctx = bpy.context
    scn = ctx.scene
    avatar, build, sim, patterns = cd["avatar"], cd["build"], cd["sim"], cd["patterns"]
    from clothing_design import props, ops
    m = avatar.measure(ctx)
    m = dict(m)
    m["figure"] = avatar.figure(ctx, m)
    gname = name
    scn.cd.garment_name = gname
    pieces, seams = preset_fn(m, fit=fit, **kw)
    made = {}
    with props.muted():
        for spec in pieces:
            ob = patterns.create_panel(
                ctx, "%s_%s" % (gname, spec["name"]), spec["segs"], garment=gname,
                anchor=spec["anchor"], height=spec["height"], ease=spec.get("ease", 0.02),
                wrap=spec.get("wrap", 1.0), spin=spec.get("spin", 0.0), taper=spec.get("taper", 0.0))
            made[spec["name"]] = ob
    ops.drop_seams_for(scn, gname)
    for entry in seams:
        a, sa, b, sb = entry[:4]
        flip = entry[4] if len(entry) > 4 else None
        if a not in made or b not in made:
            print("[garment_lib] seam skipped (missing piece):", entry)
            continue
        s = scn.cd.seams.add()
        s.name = "%s.%s - %s.%s" % (a, sa, b, sb)
        s.obj_a, s.seg_a, s.obj_b, s.seg_b = made[a], sa, made[b], sb
        if flip is not None:
            s.flip = flip
            s.auto_flip = False
    g = build.sync_garment(ctx, None, gname)
    existing = [o for o in scn.objects if o.cd.is_garment and o is not g and o.data and len(o.data.vertices)]
    g.cd.layer = max((o.cd.layer for o in existing), default=-1) + 1
    sim.setup_cloth(ctx, g)
    sim.ensure_collider(ctx, scn.cd.avatar)
    sim.setup_layers(ctx)
    g["gl_pieces"] = json.dumps([p["name"] for p in pieces])
    return g


# ------------------------------------------------------------------ UV

def assign_pattern_uv(g, px_per_m=2400, pad_m=0.02, atlas_max=4096, name="pattern", flipx=("Back", "Sleeve_R")):
    """Give the garment pattern-space UVs: each pattern piece keeps its real 2D size, the pieces
    are shelf-packed into one atlas, and a manifest (piece -> rect in metres, flip flags) is stored
    on the object as g['gl_atlas'].  Run right after draft(), before sew(): welding keeps loop UVs.

    Also sets polygon material_index = piece index so each piece can carry its own material."""
    ctx = bpy.context
    build = cd["build"]
    pieces = build.garment_pieces(ctx, g.cd.garment)
    order = [p.name for p in pieces]
    boxes = []
    for p in pieces:
        xs = [v.co.x for v in p.data.vertices]
        zs = [v.co.z for v in p.data.vertices]
        sx, sz = abs(p.scale.x), abs(p.scale.z)
        w = (max(xs) - min(xs)) * sx
        h = (max(zs) - min(zs)) * sz
        boxes.append(dict(name=p.name, w=w, h=h, minx=min(xs) * sx, minz=min(zs) * sz, sx=sx, sz=sz))
    # shelf packing, tallest first
    side_m = atlas_max / px_per_m
    srt = sorted(boxes, key=lambda b: -b["h"])
    x = y = rowh = 0.0
    for b in srt:
        if x + b["w"] + pad_m > side_m:
            x = 0.0
            y += rowh + pad_m
            rowh = 0.0
        b["ax"], b["ay"] = x + pad_m * 0.5, y + pad_m * 0.5
        x += b["w"] + pad_m
        rowh = max(rowh, b["h"])
    used_h = y + rowh + pad_m
    if used_h > side_m:
        # shrink density until it fits
        k = side_m / used_h
        return assign_pattern_uv(g, px_per_m=px_per_m * k * 0.98, pad_m=pad_m, atlas_max=atlas_max, name=name, flipx=flipx)
    by_name = {b["name"]: b for b in boxes}
    me = g.data
    uvl = me.uv_layers.get(name) or me.uv_layers.new(name=name)
    # vertex i of the garment <-> vertex j of piece k, in draft order
    vmap = []
    for p in pieces:
        for v in p.data.vertices:
            vmap.append((p.name, v.co.x * abs(p.scale.x), v.co.z * abs(p.scale.z)))
    if len(vmap) != len(me.vertices):
        raise RuntimeError("garment/piece vertex count mismatch %d vs %d (run before sew)" % (len(vmap), len(me.vertices)))
    atlas_h_m = side_m
    for poly in me.polygons:
        pn = vmap[poly.vertices[0]][0]
        poly.material_index = order.index(pn)
        b = by_name[pn]
        for li in poly.loop_indices:
            vi = me.loops[li].vertex_index
            _, lx, lz = vmap[vi]
            fx = any(pn.endswith(f) for f in flipx)
            u = (b["ax"] + ((b["minx"] + b["w"] - lx) if fx else (lx - b["minx"]))) / side_m
            v = 1.0 - (b["ay"] + (b["minz"] + b["h"] - lz)) / atlas_h_m     # image row 0 = top; pattern +z (up) = image up
            uvl.data[li].uv = (u, v)
    me.uv_layers.active = uvl
    manifest = dict(px_per_m=atlas_max / side_m, size_px=atlas_max, side_m=side_m, order=order,
                    pieces={b["name"]: dict(ax=b["ax"], ay=b["ay"], w=b["w"], h=b["h"], minx=b["minx"], minz=b["minz"],
                                            flipx=any(b["name"].endswith(f) for f in flipx)) for b in boxes})
    # outlines + named segments (piece-local metres) for stitch lines, zones and masks
    segs, outlines = {}, {}
    patterns = cd["patterns"]
    for p in pieces:
        sx, sz = abs(p.scale.x), abs(p.scale.z)
        segs[p.name] = {}
        for sn in patterns.segment_names(p):
            try:
                idx = patterns.segment_verts(p, sn)
            except Exception:
                continue
            segs[p.name][sn] = [(round(p.data.vertices[i].co.x * sx, 5), round(p.data.vertices[i].co.z * sz, 5)) for i in idx]
        bm = bmesh.new(); bm.from_mesh(p.data)
        bnd = [e for e in bm.edges if len(e.link_faces) == 1]
        adj = {}
        for e in bnd:
            for v in e.verts:
                adj.setdefault(v.index, []).append(e)
        seen, loops = set(), []
        for e in bnd:
            if e.index in seen:
                continue
            loop, cur, prev = [], e.verts[0], None
            stack_e = e
            while stack_e is not None and stack_e.index not in seen:
                seen.add(stack_e.index)
                a, b = stack_e.verts
                nxt = b if a.index == (cur.index) else a
                loop.append((round(cur.co.x * sx, 5), round(cur.co.z * sz, 5)))
                cur = nxt
                stack_e = next((x for x in adj.get(cur.index, []) if x.index not in seen), None)
            loops.append(loop)
        bm.free()
        outlines[p.name] = loops
    manifest["segments"] = segs
    manifest["outlines"] = outlines
    # store the manifest as a file next to the .blend too (used by texlab)
    g["gl_atlas"] = json.dumps(manifest)
    return manifest


# ------------------------------------------------------------------ sew / finalize

def sew(g, log=True):
    """Stitch, weld and settle (see opensew-2 CD_OT_sew), one garment."""
    ctx = bpy.context
    scn = ctx.scene
    sim, build = cd["sim"], cd["build"]
    t0 = time.time()
    scn.cd.garment_name = g.cd.garment
    start = scn.frame_current
    sim.ensure_collider(ctx, scn.cd.avatar)
    sim.setup_layers(ctx)
    others = [o for o in scn.objects if o.cd.is_garment and o is not g]
    scn.frame_set(start)
    sim.setup_cloth(ctx, g)
    sim.kick_solver(ctx, g)
    pinned = sim.pin_shoulders(ctx, g)
    hold = int(scn.cd.stitch_frames * sim.PIN_HOLD) if pinned else -1
    sim.set_gravity(g, scn.cd.stitch_gravity)
    with sim.cages_only(others):
        for i in range(scn.cd.stitch_frames):
            if i == hold:
                sim.pin_shoulders(ctx, g, torso_anchors=('TORSO_BACK',))
            scn.frame_set(scn.frame_current + 1)
    merged = skipped = 0
    if scn.cd.auto_close:
        merged, skipped = sim.close_seams(ctx, g)
    sim.unpin_shoulders(g)
    sim.set_gravity(g, 1.0)
    with sim.cages_only(others):
        for _ in range(scn.cd.settle_frames):
            scn.frame_set(scn.frame_current + 1)
    if log:
        print("[sew] %s: welded %d, skipped %d, %.0fs" % (g.name, merged, skipped, time.time() - t0))
    return merged, skipped


def relax(g, take_in=0.04, frames=40, relax_frames=60):
    """Steam the garment onto the body, freeze, re-settle softly (opensew-2 relax_garment)."""
    ctx = bpy.context
    cd["sim"].relax_garment(ctx, g, take_in=take_in, frames=frames, relax_frames=relax_frames)


def finalize(g, thickness=None, subdiv=None, render_subdiv=None):
    ctx = bpy.context
    scn = ctx.scene
    if thickness is not None:
        scn.cd.thickness = thickness
    if subdiv is not None:
        scn.cd.subdiv_levels = subdiv
    if render_subdiv is not None:
        scn.cd.subdiv_render = render_subdiv
    scn.cd.garment_name = g.cd.garment
    bpy.ops.cd.finalize()
    return g


# ------------------------------------------------------------------ pose / info

def pose_arms(rad=0.7):
    """Lower both arms by `rad` radians about the body's forward axis (avatar is drafted with arms
    held away from the ribs).  Garment follows via the armature modifier."""
    ctx = bpy.context
    avatar, sim = cd["avatar"], cd["sim"]
    scn = ctx.scene
    rig = avatar.find_armature(scn.cd.avatar)
    fwd, side = avatar.basis(scn.cd.facing)
    from mathutils import Quaternion
    for role, sgn in (("arm_l", -1.0), ("arm_r", 1.0)):
        pb = avatar._find_bone(rig, sim.WALK_BONES[role])
        if pb is None:
            print("[pose] bone not found", role)
            continue
        pb.rotation_mode = 'QUATERNION'
        axis = sim._local_axis(rig, pb, fwd)
        pb.rotation_quaternion = Quaternion(axis, sgn * rad)
    ctx.view_layer.update()
    return rig


def garment_bbox(g):
    bb = [g.matrix_world @ Vector(c) for c in g.bound_box]
    return (min(v.x for v in bb), max(v.x for v in bb), min(v.y for v in bb), max(v.y for v in bb),
            min(v.z for v in bb), max(v.z for v in bb))


def stitch_report(g, verbose=True):
    """Initial sewing-spring lengths per piece pair (metres): the gap each seam must close.
    Large cap-seam gaps are what make the sleeves / shoulders fail to stitch."""
    me = g.data
    used = set()
    for p in me.polygons:
        vs = list(p.vertices)
        for i in range(len(vs)):
            used.add((min(vs[i], vs[i - 1]), max(vs[i], vs[i - 1])))
    names = {vg.index: vg.name for vg in g.vertex_groups}
    def piece(v):
        for gr in me.vertices[v].groups:
            if gr.weight > 0.5:
                return names.get(gr.group, "?")
        return "?"
    pairs = {}
    for e in me.edges:
        k = (min(e.vertices), max(e.vertices))
        if k in used:
            continue
        a, b = e.vertices
        L = (me.vertices[a].co - me.vertices[b].co).length
        key = tuple(sorted((piece(a).split("_", 1)[-1], piece(b).split("_", 1)[-1])))
        pairs.setdefault(key, []).append(L)
    rep = {}
    for k, v in pairs.items():
        rep[k] = (len(v), sum(v) / len(v), max(v))
    if verbose:
        for k, (n, mean, mx) in sorted(rep.items()):
            print("  stitch %-22s n=%3d mean %.3f max %.3f" % ("/".join(k), n, mean, mx))
    return rep


# ------------------------------------------------------------------ seam groups (zip line, hems, cuffs ...)

def mark_segments(g, mapping):
    """Create vertex groups on the DRAFTED garment (call before sew): {group: [(piece_suffix, segment), ...]}.
    Piece vertices occupy consecutive index ranges in draft order, so a segment's vertex ids translate directly."""
    ctx = bpy.context
    build, patterns = cd["build"], cd["patterns"]
    pieces = build.garment_pieces(ctx, g.cd.garment)
    off, cur = {}, 0
    for p in pieces:
        off[p.name] = cur
        cur += len(p.data.vertices)
    for gname, items in mapping.items():
        vg = g.vertex_groups.get(gname) or g.vertex_groups.new(name=gname)
        idx = []
        for suffix, seg in items:
            for p in pieces:
                if p.name.endswith("_" + suffix) or p.name == suffix:
                    idx += [off[p.name] + i for i in patterns.segment_verts(p, seg)]
        if idx:
            vg.add(sorted(set(idx)), 1.0, 'REPLACE')


def group_path(g, name, descending_z=True):
    """World positions + outward normals of the vertices in a group, evaluated through the armature only
    (no subsurf/solidify), ordered top -> bottom.  Returns (points, normals)."""
    ctx = bpy.context
    sim = cd["sim"]
    vg = g.vertex_groups.get(name)
    if vg is None:
        return [], []
    ids = [v.index for v in g.data.vertices if any(gr.group == vg.index and gr.weight > 0.5 for gr in v.groups)]
    with sim.sim_cage_only(g):
        ctx.view_layer.update()
        ev = g.evaluated_get(ctx.evaluated_depsgraph_get())
        me = ev.to_mesh()
        mw = ev.matrix_world
        pts = [(mw @ me.vertices[i].co, (mw.to_3x3() @ me.vertices[i].normal).normalized()) for i in ids if i < len(me.vertices)]
        ev.to_mesh_clear()
    pts.sort(key=lambda t: -t[0].z if descending_z else t[0].z)
    return [p for p, _ in pts], [n for _, n in pts]


# ------------------------------------------------------------------ opening an existing .blend / repairs

def attach():
    """Use after bpy.ops.wm.open_mainfile on a scene built earlier: enable the add-on, fill `cd`."""
    bpy.ops.preferences.addon_enable(module="clothing_design")
    from clothing_design import avatar, library, build, sim, patterns
    cd.update(avatar=avatar, library=library, build=build, sim=sim, patterns=patterns)
    bpy.context.scene.cd.live_sync = False
    return bpy.context.scene.cd.avatar


def garment(name=None):
    for o in bpy.data.objects:
        if o.name.startswith("CD_Garment") and (name is None or name in o.name):
            return o


def fix_penetration(g, clearance=0.004, iters=6, smooth_passes=3, ring=3, verbose=True):
    """Push garment vertices that sit inside (or too close to) the avatar back out along the surface normal,
    then relax the neighbourhood of what moved and re-push, so the repair does not leave creases.
    Works on the base cage (frame-independent coordinates, object at identity)."""
    ctx = bpy.context
    avatar = cd["avatar"]
    me = g.data
    adj = [[] for _ in me.vertices]
    for e in me.edges:
        a, b = e.vertices
        adj[a].append(b); adj[b].append(a)
    inv = g.matrix_world.inverted()
    mw = g.matrix_world
    total_moved = 0
    for it in range(iters):
        bvh = avatar.body_bvh(ctx)
        moved = set()
        for v in me.vertices:
            p = mw @ v.co
            hit = bvh.find_nearest(p)
            if hit is None or hit[0] is None:
                continue
            loc, nrm = hit[0], hit[1]
            gap = (p - loc).dot(nrm)
            if gap < clearance:
                v.co = inv @ (loc + nrm * clearance)
                moved.add(v.index)
        if not moved:
            break
        total_moved += len(moved)
        # grow the moved set by `ring` rings and Laplacian-smooth it (keeps the push but removes the crease)
        band = set(moved)
        for _ in range(ring):
            band |= {n for i in list(band) for n in adj[i]}
        for _ in range(smooth_passes):
            new = {}
            for i in band:
                nb = adj[i]
                if not nb:
                    continue
                c = sum((me.vertices[n].co for n in nb), Vector()) / len(nb)
                new[i] = me.vertices[i].co.lerp(c, 0.5)
            for i, co in new.items():
                me.vertices[i].co = co
    # final hard pass (no smoothing) so nothing ends up below the clearance
    bvh = avatar.body_bvh(ctx)
    for v in me.vertices:
        p = mw @ v.co
        hit = bvh.find_nearest(p)
        if hit and hit[0] is not None and (p - hit[0]).dot(hit[1]) < clearance:
            v.co = inv @ (hit[0] + hit[1] * clearance)
    me.update()
    if verbose:
        print("[fix_penetration] pushed %d vertex-moves over %d iterations" % (total_moved, it + 1))
    return total_moved


def penetration_stats(g, tol=0.002):
    ctx = bpy.context
    avatar = cd["avatar"]
    bvh = avatar.body_bvh(ctx)
    mw = g.matrix_world
    n_in = 0
    worst = 0.0
    for v in g.data.vertices:
        p = mw @ v.co
        hit = bvh.find_nearest(p)
        if hit and hit[0] is not None:
            gap = (p - hit[0]).dot(hit[1])
            if gap < -tol:
                n_in += 1
                worst = min(worst, gap)
    return n_in, len(g.data.vertices), worst


def freeze(g, frame=None):
    """Bake the simulated shape at `frame` (default: last frame) into the base mesh and drop the cloth solver."""
    ctx = bpy.context
    scn = ctx.scene
    if frame is not None:
        scn.frame_set(frame)
    return cd["sim"].freeze_garment(ctx, g)


def finish(g, clearance=0.006, thickness=0.0022, subdiv=1, render_subdiv=2, bind=False, push=True):
    """Bake the sim, close leftover holes, keep the cloth clear of the body, add thickness + subdivision.
    bind=False leaves the garment static in the pose it was sewn in / posed to (used for stills and GLB)."""
    ctx = bpy.context
    scn = ctx.scene
    freeze(g)
    scn.cd.bind_armature = bool(bind)
    scn.cd.thickness = thickness
    scn.cd.subdiv_levels = subdiv
    scn.cd.subdiv_render = render_subdiv
    scn.cd.garment_name = g.cd.garment
    bpy.ops.cd.finalize()
    if push:
        fix_penetration(g, clearance=clearance, smooth_passes=2)
    return g


def uv_flip_pieces(g, suffixes=("Back", "Sleeve_R"), uvname="pattern"):
    """Mirror the U coordinate inside the atlas rect of the given pieces (face material_index = piece index).
    For garments drafted before flipx was a draft-time option.  Updates the stored manifest flags."""
    man = json.loads(g["gl_atlas"])
    side = man["side_m"]
    me = g.data
    uvl = me.uv_layers[uvname]
    order = man["order"]
    flip_idx = {i for i, n in enumerate(order) if any(n.endswith(s) for s in suffixes)}
    done = set()
    for poly in me.polygons:
        if poly.material_index in flip_idx:
            p = man["pieces"][order[poly.material_index]]
            cx = (p["ax"] + p["w"] / 2) / side
            for li in poly.loop_indices:
                u, v = uvl.data[li].uv
                uvl.data[li].uv = (2 * cx - u, v)
    for n in order:
        man["pieces"][n]["flipx"] = any(n.endswith(s) for s in suffixes)
    g["gl_atlas"] = json.dumps(man)
    return man
