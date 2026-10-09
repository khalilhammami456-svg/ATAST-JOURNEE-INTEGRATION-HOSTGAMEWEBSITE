# Clothing Design - 2D pattern pieces.
#
# A pattern piece is an ordinary mesh object living flat in the world XZ plane
# (Blender's Front view), which is the addon's "2D pattern space". Its boundary
# is split into named segments, stored as SEG_<name> vertex groups, and those
# segment names are what seams refer to.
import bpy, bmesh, math, json
from mathutils import Vector
from mathutils.kdtree import KDTree
from . import props as _props

SEG_PREFIX = "SEG_"
PATTERN_COLL = "CD_Patterns"
GARMENT_COLL = "CD_Garments"


# ---------------------------------------------------------------- collections

def get_collection(context, name):
    coll = bpy.data.collections.get(name)
    if coll is None:
        coll = bpy.data.collections.new(name)
    if name not in {c.name for c in context.scene.collection.children_recursive}:
        try:
            context.scene.collection.children.link(coll)
        except RuntimeError:
            pass
    return coll


def move_to_collection(ob, coll):
    for c in list(ob.users_collection):
        c.objects.unlink(ob)
    coll.objects.link(ob)


# ---------------------------------------------------------------- materials

def fabric_material(name="CD_Fabric", color=(0.72, 0.74, 0.78, 1.0)):
    mat = bpy.data.materials.get(name)
    if mat:
        return mat
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes.get("Principled BSDF")
    if bsdf:
        bsdf.inputs["Base Color"].default_value = color
        for slot, val in (("Roughness", 0.85), ("Metallic", 0.0)):
            if slot in bsdf.inputs:
                bsdf.inputs[slot].default_value = val
        if "Sheen Weight" in bsdf.inputs:
            bsdf.inputs["Sheen Weight"].default_value = 0.25
    mat.diffuse_color = color
    mat.use_backface_culling = False
    return mat


# ---------------------------------------------------------------- outlines

def resample_loop(segs, target):
    """segs: [(name, [Vector2 ...]) ...] sharing endpoints, forming a closed loop.
    Returns evenly spaced boundary points plus the segment name of each."""
    pts, labels = [], []
    for name, poly in segs:
        for i in range(len(poly) - 1):
            a, b = Vector(poly[i]), Vector(poly[i + 1])
            d = (b - a).length
            n = max(1, int(round(d / target)))
            for k in range(n):
                pts.append(a.lerp(b, k / n))
                labels.append(name)
    # drop points that landed on top of each other
    out_p, out_l = [], []
    for p, l in zip(pts, labels):
        if out_p and (p - out_p[-1]).length < target * 0.15:
            continue
        out_p.append(p); out_l.append(l)
    if len(out_p) > 2 and (out_p[0] - out_p[-1]).length < target * 0.15:
        out_p.pop(); out_l.pop()
    return out_p, out_l


def bezier(p0, p1, p2, p3, n=12):
    """Cubic bezier sample list, endpoints included."""
    p0, p1, p2, p3 = (Vector(p) for p in (p0, p1, p2, p3))
    out = []
    for i in range(n + 1):
        t = i / n
        s = 1.0 - t
        out.append(p0 * (s ** 3) + p1 * (3 * s * s * t) + p2 * (3 * s * t * t) + p3 * (t ** 3))
    return out


# ---------------------------------------------------------------- meshing

def _smooth_interior(bm, iters=2, factor=0.5):
    for _ in range(iters):
        moved = {}
        for v in bm.verts:
            if v.is_boundary or not v.link_edges:
                continue
            acc = Vector((0, 0, 0))
            for e in v.link_edges:
                acc += e.other_vert(v).co
            acc /= len(v.link_edges)
            moved[v] = v.co.lerp(acc, factor)
        for v, c in moved.items():
            c.y = 0.0
            v.co = c


def _point_in_poly(x, z, poly):
    inside = False
    n = len(poly)
    j = n - 1
    for i in range(n):
        xi, zi = poly[i]
        xj, zj = poly[j]
        if (zi > z) != (zj > z):
            xc = (xj - xi) * (z - zi) / (zj - zi) + xi
            if x < xc:
                inside = not inside
        j = i
    return inside


def _nearest_on_poly(px, pz, poly):
    best, bd = (px, pz), 1e18
    n = len(poly)
    for i in range(n):
        ax, az = poly[i]
        bx, bz = poly[(i + 1) % n]
        dx, dz = bx - ax, bz - az
        L2 = dx * dx + dz * dz
        if L2 < 1e-16:
            t = 0.0
        else:
            t = max(0.0, min(1.0, ((px - ax) * dx + (pz - az) * dz) / L2))
        qx, qz = ax + dx * t, az + dz * t
        d = (px - qx) ** 2 + (pz - qz) ** 2
        if d < bd:
            bd, best = d, (qx, qz)
    return best


def panel_bmesh(pts2d, target, labels=None):
    """Quad grid clipped to the outline.

    A structured grid beats a triangulation here twice over: it subdivides into
    a clean cage, and its edges run along the pattern's own axes, so the cloth
    stretches along the grain the way woven fabric does.
    """
    poly = [(p.x, p.y) for p in pts2d]
    minx = min(p[0] for p in poly); maxx = max(p[0] for p in poly)
    minz = min(p[1] for p in poly); maxz = max(p[1] for p in poly)
    w, h = maxx - minx, maxz - minz
    if w < 1e-6 or h < 1e-6:
        raise RuntimeError("pattern outline is degenerate")

    nx = max(2, int(math.ceil(w / target))) + 2
    nz = max(2, int(math.ceil(h / target))) + 2
    ox = (minx + maxx) * 0.5 - (nx - 1) * target * 0.5
    oz = (minz + maxz) * 0.5 - (nz - 1) * target * 0.5

    # keep the cells whose centre falls inside the outline
    keep = set()
    for i in range(nx - 1):
        for j in range(nz - 1):
            cx = ox + (i + 0.5) * target
            cz = oz + (j + 0.5) * target
            if _point_in_poly(cx, cz, poly):
                keep.add((i, j))
    if len(keep) < 4:
        raise RuntimeError("outline too small for the chosen resolution")

    # largest connected block, so stray cells across a notch are dropped
    seen, blocks = set(), []
    for c in keep:
        if c in seen:
            continue
        stack, comp = [c], []
        while stack:
            x = stack.pop()
            if x in seen or x not in keep:
                continue
            seen.add(x); comp.append(x)
            i, j = x
            stack += [(i + 1, j), (i - 1, j), (i, j + 1), (i, j - 1)]
        blocks.append(comp)
    keep = set(max(blocks, key=len))

    bm = bmesh.new()
    vmap = {}
    def vert(i, j):
        if (i, j) not in vmap:
            vmap[(i, j)] = bm.verts.new((ox + i * target, 0.0, oz + j * target))
        return vmap[(i, j)]
    for (i, j) in sorted(keep):
        try:
            bm.faces.new((vert(i, j), vert(i + 1, j), vert(i + 1, j + 1), vert(i, j + 1)))
        except ValueError:
            pass
    bm.verts.ensure_lookup_table()
    bm.faces.ensure_lookup_table()
    if not bm.faces:
        bm.free()
        raise RuntimeError("could not fill the pattern outline")

    # pull the stepped edge out onto the real outline
    for v in bm.verts:
        if v.is_boundary:
            qx, qz = _nearest_on_poly(v.co.x, v.co.z, poly)
            v.co.x, v.co.z = qx, qz
    bmesh.ops.remove_doubles(bm, verts=bm.verts[:], dist=target * 0.12)
    _respace_boundary(bm, poly, labels)
    _smooth_interior(bm, 6, 0.5)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    return bm


def _respace_boundary(bm, poly, labels):
    """Even out the boundary vertices along the outline, keeping the corners.

    Projecting a stepped grid edge leaves the boundary unevenly spaced. Sewing
    two such edges together pinches the seam and folds the fabric back on
    itself, which shows up as a fin down the garment.
    """
    ring = [v for v in bm.verts if v.is_boundary]
    if len(ring) < 6:
        return
    # order the boundary loop
    adj = {}
    for e in bm.edges:
        if len(e.link_faces) == 1:
            adj.setdefault(e.verts[0], []).append(e.verts[1])
            adj.setdefault(e.verts[1], []).append(e.verts[0])
    if len(adj) != len(ring):
        return
    start = ring[0]
    if len(adj.get(start, [])) != 2:
        return
    loop, prev, cur = [start], None, start
    while True:
        nxt = [n for n in adj[cur] if n is not prev]
        if not nxt:
            return
        prev, cur = cur, nxt[0]
        if cur is start:
            break
        if cur in loop:
            return
        loop.append(cur)
    if len(loop) != len(ring):
        return

    n = len(poly)
    cum = [0.0]
    for i in range(n):
        ax, az = poly[i]
        bx, bz = poly[(i + 1) % n]
        cum.append(cum[-1] + math.hypot(bx - ax, bz - az))
    total = cum[-1]
    if total < 1e-9:
        return

    def param(px, pz):
        best, bs = 1e18, 0.0
        for i in range(n):
            ax, az = poly[i]
            bx, bz = poly[(i + 1) % n]
            dx, dz = bx - ax, bz - az
            L2 = dx * dx + dz * dz
            t = 0.0 if L2 < 1e-16 else max(0.0, min(1.0, ((px - ax) * dx + (pz - az) * dz) / L2))
            qx, qz = ax + dx * t, az + dz * t
            d = (px - qx) ** 2 + (pz - qz) ** 2
            if d < best:
                best, bs = d, cum[i] + math.hypot(qx - ax, qz - az)
        return bs

    def at(s):
        s = s % total
        lo, hi = 0, n
        while lo < hi - 1:
            mid = (lo + hi) // 2
            if cum[mid] <= s:
                lo = mid
            else:
                hi = mid
        ax, az = poly[lo]
        bx, bz = poly[(lo + 1) % n]
        seg = cum[lo + 1] - cum[lo]
        t = 0.0 if seg < 1e-12 else (s - cum[lo]) / seg
        return ax + (bx - ax) * t, az + (bz - az) * t

    params = [param(v.co.x, v.co.z) for v in loop]
    # rotate the loop so it runs forward in arc length
    k = min(range(len(loop)), key=lambda i: params[i])
    loop = loop[k:] + loop[:k]
    params = params[k:] + params[:k]
    if len(params) > 2 and params[1] < params[-1]:
        pass
    else:
        loop = [loop[0]] + loop[1:][::-1]
        params = [params[0]] + params[1:][::-1]

    # anchor the corners, then space the runs between them evenly
    corners = []
    if labels:
        for i in range(n):
            if labels[i] != labels[i - 1]:
                corners.append(cum[i])
    anchors = {}
    for cs in corners:
        j = min(range(len(loop)), key=lambda i: min(abs(params[i] - cs), total - abs(params[i] - cs)))
        anchors[j] = cs
    if 0 not in anchors:
        anchors[0] = params[0]
    keys = sorted(anchors)
    m = len(loop)
    for a_i in range(len(keys)):
        i0 = keys[a_i]
        i1 = keys[(a_i + 1) % len(keys)]
        s0 = anchors[i0]
        s1 = anchors[i1]
        span = (s1 - s0) % total
        count = (i1 - i0) % m
        if count == 0:
            continue
        for step in range(count + 1):
            idx = (i0 + step) % m
            x, z = at(s0 + span * (step / count))
            loop[idx].co.x, loop[idx].co.z = x, z


def assign_segments(bm, pts2d, labels):
    """Tag every boundary vert with the nearest original outline point's segment."""
    kd = KDTree(len(pts2d))
    for i, p in enumerate(pts2d):
        kd.insert((p.x, 0.0, p.y), i)
    kd.balance()
    out = {}
    for v in bm.verts:
        if not v.is_boundary:
            continue
        _, idx, _ = kd.find(v.co)
        out.setdefault(labels[idx], []).append(v.index)
    return out


# ---------------------------------------------------------------- creation

def layout_slot(context, width):
    """Next free x position in the 2D pattern area, to the +X side of the avatar.

    Positions are worked out from object.location plus the local bounding box
    rather than matrix_world: a piece created moments ago still has a stale
    matrix_world until the depsgraph runs, which would stack every new piece on
    top of the last one.
    """
    scn = context.scene
    gap = scn.cd.pattern_gap
    x = 0.0
    av = scn.cd.avatar
    if av:
        bb = [av.matrix_world @ Vector(c) for c in av.bound_box]
        x = max(p.x for p in bb) + gap
    for ob in scn.objects:
        if not ob.cd.is_pattern:
            continue
        local_max = max(c[0] for c in ob.bound_box) * ob.scale.x
        x = max(x, ob.location.x + local_max + gap)
    return x + width * 0.5


def create_panel(context, name, segs, target=None, garment=None,
                 anchor='TORSO_FRONT', height=0.5, ease=0.02, wrap=1.0, spin=0.0,
                 taper=0.0):
    """Build a pattern piece from a list of (segment_name, [Vector2...])."""
    scn = context.scene
    target = target or scn.cd.resolution
    pts2d, labels = resample_loop(segs, target)
    if len(pts2d) < 3:
        raise RuntimeError("outline needs at least 3 points")

    # centre the piece on its own bounding box so local coords are the pattern
    cx = (min(p.x for p in pts2d) + max(p.x for p in pts2d)) * 0.5
    cz = (min(p.y for p in pts2d) + max(p.y for p in pts2d)) * 0.5
    pts2d = [Vector((p.x - cx, p.y - cz)) for p in pts2d]
    width = max(p.x for p in pts2d) - min(p.x for p in pts2d)

    bm = panel_bmesh(pts2d, target, labels)
    seg_verts = assign_segments(bm, pts2d, labels)

    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    me.materials.append(fabric_material())

    ob = bpy.data.objects.new(name, me)
    move_to_collection(ob, get_collection(context, PATTERN_COLL))

    seen = []
    for sname, _ in segs:
        if sname not in seen:
            seen.append(sname)
    for sname in seen:
        idx = seg_verts.get(sname, [])
        vg = ob.vertex_groups.new(name=SEG_PREFIX + sname)
        if idx:
            vg.add(idx, 1.0, 'REPLACE')

    with _props.muted():
        ob.cd.is_pattern = True
        ob.cd.garment = garment or scn.cd.garment_name
        ob.cd.anchor = anchor
        ob.cd.height = height
        ob.cd.ease = ease
        ob.cd.wrap = wrap
        ob.cd.spin = spin
        ob.cd.taper = taper
        ob.cd.seg_order = ",".join(seen)

    zc = 0.0
    av = scn.cd.avatar
    if av:
        bb = [av.matrix_world @ Vector(c) for c in av.bound_box]
        zc = (min(p.z for p in bb) + max(p.z for p in bb)) * 0.5
    # remember the direction each segment runs in the outline, so seam pairing is
    # reproducible instead of depending on vertex order
    ends = {}
    for sname in seen:
        pts = [p for p, l in zip(pts2d, labels) if l == sname]
        if len(pts) >= 2:
            ends[sname] = [[pts[0].x, pts[0].y], [pts[-1].x, pts[-1].y]]
    ob["cd_seg_ends"] = json.dumps(ends)

    ob.location = (layout_slot(context, width), 0.0, zc)
    return ob


def segment_names(ob):
    return [vg.name[len(SEG_PREFIX):] for vg in ob.vertex_groups
            if vg.name.startswith(SEG_PREFIX)]


def segment_verts(ob, seg):
    """Indices of the verts in a segment, ordered along the boundary."""
    vg = ob.vertex_groups.get(SEG_PREFIX + seg)
    if vg is None:
        return []
    gi = vg.index
    members = set()
    for v in ob.data.vertices:
        for g in v.groups:
            if g.group == gi and g.weight > 0.5:
                members.add(v.index)
                break
    if not members:
        return []
    chain = order_chain(ob.data, members)
    return orient_chain(ob, seg, chain)


def orient_chain(ob, seg, chain):
    """Point the chain the same way the segment runs in the original outline."""
    if len(chain) < 2:
        return chain
    try:
        ends = json.loads(ob.get("cd_seg_ends", "{}"))
    except Exception:
        return chain
    e = ends.get(seg)
    if not e:
        return chain
    start = Vector((e[0][0], 0.0, e[0][1]))
    a = ob.data.vertices[chain[0]].co
    b = ob.data.vertices[chain[-1]].co
    if (b - start).length < (a - start).length:
        chain.reverse()
    return chain


def order_chain(me, members):
    """Walk a set of boundary verts into a single ordered chain."""
    edge_count = {}
    for e in me.edges:
        edge_count[e.vertices[0]] = edge_count.get(e.vertices[0], 0)
        edge_count[e.vertices[1]] = edge_count.get(e.vertices[1], 0)
    face_edges = {}
    for p in me.polygons:
        vs = list(p.vertices)
        for i in range(len(vs)):
            k = (min(vs[i], vs[i - 1]), max(vs[i], vs[i - 1]))
            face_edges[k] = face_edges.get(k, 0) + 1
    adj = {i: [] for i in members}
    for e in me.edges:
        a, b = e.vertices
        if a in members and b in members:
            k = (min(a, b), max(a, b))
            if face_edges.get(k, 0) == 1:      # boundary edge only
                adj[a].append(b)
                adj[b].append(a)
    ends = [v for v in members if len(adj[v]) == 1]
    start = ends[0] if ends else (min(members) if members else None)
    if start is None:
        return []
    chain, prev, cur = [start], None, start
    while True:
        nxt = [n for n in adj[cur] if n != prev]
        if not nxt:
            break
        prev, cur = cur, nxt[0]
        if cur in chain:
            break
        chain.append(cur)
    return chain
