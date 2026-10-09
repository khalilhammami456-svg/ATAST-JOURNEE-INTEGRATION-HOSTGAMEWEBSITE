"""Hardware and trims modelled as real geometry (bpy/bmesh): zipper (tape, interlocking teeth, slider, pull),
snap buttons, draw-cords with aglets, eyelets, rib-cuff seam piping.  All dimensions in metres."""
import bpy, bmesh, math
from mathutils import Vector, Matrix, Quaternion
import materials as M


def _new(name, bm_or_none=None):
    me = bpy.data.meshes.new(name)
    ob = bpy.data.objects.new(name, me)
    bpy.context.scene.collection.objects.link(ob)
    return ob, me


def _box(bm, c, ex, ey, ez, ax, ay, az):
    """Axis-aligned-in-local-frame box centred c with half sizes (ex,ey,ez) along unit vectors ax, ay, az."""
    vs = []
    for sx in (-1, 1):
        for sy in (-1, 1):
            for sz in (-1, 1):
                vs.append(bm.verts.new(c + ax * (sx * ex) + ay * (sy * ey) + az * (sz * ez)))
    f = lambda a, b, c_, d: bm.faces.new((vs[a], vs[b], vs[c_], vs[d]))
    f(0, 1, 3, 2); f(4, 6, 7, 5); f(0, 4, 5, 1); f(2, 3, 7, 6); f(0, 2, 6, 4); f(1, 5, 7, 3)
    return vs


def _resample(points, step):
    """Resample a polyline at constant arc length."""
    out = [points[0]]
    acc = 0.0
    for a, b in zip(points[:-1], points[1:]):
        seg = (b - a).length
        if seg < 1e-9:
            continue
        d = step - acc
        while d <= seg:
            out.append(a + (b - a) * (d / seg))
            d += step
        acc = seg - (d - step)
    return out


def zipper(path, normals, name="Zipper", tape_w=0.011, tooth_pitch=0.0042, tooth_w=0.0034, offset=0.0024,
           tape_rgb=(0.05, 0.05, 0.07), metal="brass", slider_at=0.0, pull_len=0.034, open_frac=0.0):
    """path: list of Vector (top -> bottom) centre-front line on the garment surface; normals: outward unit
    vectors at those points.  Returns the zipper object group (tape, teeth, slider, pull) parented to one empty."""
    # smooth + resample the path
    pts = [Vector(p) for p in path]
    # arc-length param along the polyline
    res = _resample(pts, tooth_pitch)
    # outward normal for each resampled point from the nearest original
    def nrm(p):
        best, bi = 1e9, 0
        for i, q in enumerate(pts):
            d = (q - p).length_squared
            if d < best:
                best, bi = d, i
        return Vector(normals[bi]).normalized()
    ns = [nrm(p) for p in res]
    # tangent
    tans = []
    for i in range(len(res)):
        a = res[max(0, i - 1)]; b = res[min(len(res) - 1, i + 1)]
        tans.append((b - a).normalized())
    # light smoothing of the frames
    frames = []
    for p, n, t in zip(res, ns, tans):
        side = t.cross(n).normalized()
        n2 = side.cross(t).normalized()
        frames.append((p + n2 * offset, t, side, n2))

    # --- teeth: alternate left/right, interlocking
    bm = bmesh.new()
    n_closed = int(len(frames) * (1.0 - open_frac))
    for i, (p, t, s, n) in enumerate(frames[:max(2, n_closed)]):
        side = 1 if i % 2 == 0 else -1
        _box(bm, p + s * (side * 0.00062), tooth_w * 0.5 + 0.0003, 0.00095, 0.00135, s, n, t)
        # tooth head (rounded look: small cap box)
        _box(bm, p + s * (side * 0.0013) + n * 0.0003, 0.00055, 0.0011, 0.0012, s, n, t)
    teeth_ob, teeth_me = _new(name + "_teeth")
    bm.to_mesh(teeth_me); bm.free()
    for poly in teeth_me.polygons:
        poly.use_smooth = False
    if metal == "brass":
        mt = M.flat_material(name + "_brass", (0.72, 0.52, 0.22), rough=0.30, metal=1.0)
    elif metal == "nickel":
        mt = M.flat_material(name + "_nickel", (0.80, 0.80, 0.82), rough=0.26, metal=1.0)
    else:
        mt = M.flat_material(name + "_gun", (0.20, 0.21, 0.23), rough=0.32, metal=1.0)
    teeth_ob.data.materials.append(mt)

    # --- tape: two ribbons either side of the teeth
    bm = bmesh.new()
    for sgn in (-1, 1):
        rows = []
        for (p, t, s, n) in frames:
            a = p + s * (sgn * 0.0021) - n * 0.0004
            b = p + s * (sgn * (0.0021 + tape_w)) - n * 0.0010
            rows.append((bm.verts.new(a), bm.verts.new(b)))
        for r0, r1 in zip(rows[:-1], rows[1:]):
            bm.faces.new((r0[0], r0[1], r1[1], r1[0]) if sgn > 0 else (r0[1], r0[0], r1[0], r1[1]))
    tape_ob, tape_me = _new(name + "_tape")
    bm.to_mesh(tape_me); bm.free()
    for poly in tape_me.polygons:
        poly.use_smooth = True
    sol = tape_ob.modifiers.new("th", "SOLIDIFY"); sol.thickness = 0.0009; sol.offset = 0
    tape_ob.data.materials.append(M.flat_material(name + "_tape_mat", tape_rgb, rough=0.85))

    # --- slider body + pull tab at the top (slider_at in 0..1 along the path, 0 = top)
    k = int(slider_at * (len(frames) - 1))
    p, t, s, n = frames[k]
    bm = bmesh.new()
    _box(bm, p + n * 0.0022, 0.0075, 0.0022, 0.0105, s, n, t)         # slider body
    _box(bm, p + n * 0.0044 + t * 0.0, 0.0044, 0.0010, 0.0060, s, n, t)  # cap
    sl_ob, sl_me = _new(name + "_slider")
    bm.to_mesh(sl_me); bm.free()
    bev = sl_ob.modifiers.new("bev", "BEVEL"); bev.width = 0.0008; bev.segments = 2
    sl_ob.data.materials.append(mt)
    # pull tab: flat rounded plate with a hole hanging downwards
    bm = bmesh.new()
    tab_c = p + n * 0.0055 - t * (pull_len * 0.55)
    _box(bm, tab_c, 0.0058, 0.0009, pull_len * 0.5, s, n, t)
    pl_ob, pl_me = _new(name + "_pull")
    bm.to_mesh(pl_me); bm.free()
    bev = pl_ob.modifiers.new("bev", "BEVEL"); bev.width = 0.0012; bev.segments = 3
    pl_ob.data.materials.append(mt)
    root = bpy.data.objects.new(name, None)
    bpy.context.scene.collection.objects.link(root)
    for o in (teeth_ob, tape_ob, sl_ob, pl_ob):
        o.parent = root
    return root


def snap_button(center, normal, tangent, r=0.0065, name="Snap", rgb=(0.72, 0.74, 0.76), ring_rgb=None):
    """Four-part metal snap button: domed cap with a raised rim."""
    bm = bmesh.new()
    n = Vector(normal).normalized(); t = Vector(tangent).normalized()
    s = n.cross(t).normalized()
    seg = 28
    rings = [(r, 0.0), (r * 0.98, 0.0008), (r * 0.84, 0.0016), (r * 0.55, 0.0021), (0.0, 0.0023)]
    rv = []
    for rad, h in rings:
        if rad == 0.0:
            rv.append([bm.verts.new(Vector(center) + n * h)])
        else:
            rv.append([bm.verts.new(Vector(center) + n * h + (t * math.cos(2 * math.pi * i / seg) + s * math.sin(2 * math.pi * i / seg)) * rad)
                       for i in range(seg)])
    for a, b in zip(rv[:-1], rv[1:]):
        if len(b) == 1:
            for i in range(seg):
                bm.faces.new((a[i], a[(i + 1) % seg], b[0]))
        else:
            for i in range(seg):
                bm.faces.new((a[i], a[(i + 1) % seg], b[(i + 1) % seg], b[i]))
    ob, me = _new(name)
    bm.to_mesh(me); bm.free()
    for p in me.polygons:
        p.use_smooth = True
    ob.data.materials.append(M.flat_material(name + "_m", rgb, rough=0.25, metal=1.0))
    return ob


def tube_along(points, radius, name="Cord", rgb=(0.9, 0.9, 0.9), rough=0.8, aglet=True, aglet_len=0.022):
    """Draw-cord: bevelled curve through points, with metal/plastic aglets at both ends."""
    cu = bpy.data.curves.new(name, "CURVE")
    cu.dimensions = "3D"
    cu.bevel_depth = radius
    cu.bevel_resolution = 4
    sp = cu.splines.new("NURBS")
    sp.points.add(len(points) - 1)
    for i, p in enumerate(points):
        sp.points[i].co = (p.x, p.y, p.z, 1.0)
    sp.order_u = min(4, len(points)); sp.use_endpoint_u = True
    ob = bpy.data.objects.new(name, cu)
    bpy.context.scene.collection.objects.link(ob)
    cu.materials.append(M.flat_material(name + "_m", rgb, rough=rough))
    objs = [ob]
    if aglet:
        for end, dirn in ((points[0], (points[1] - points[0])), (points[-1], (points[-2] - points[-1]))):
            d = Vector(dirn).normalized()
            bm = bmesh.new()
            bmesh.ops.create_cone(bm, cap_ends=True, segments=14, radius1=radius * 1.35, radius2=radius * 1.35, depth=aglet_len)
            q = Vector((0, 0, 1)).rotation_difference(d)
            bmesh.ops.rotate(bm, verts=bm.verts[:], matrix=q.to_matrix(), cent=(0, 0, 0))
            bmesh.ops.translate(bm, verts=bm.verts[:], vec=Vector(end) + d * (aglet_len * 0.5 - 0.002) * -1)
            ag, me = _new(name + "_aglet")
            bm.to_mesh(me); bm.free()
            ag.data.materials.append(M.flat_material(name + "_ag", (0.75, 0.76, 0.78), rough=0.25, metal=1.0))
            objs.append(ag)
    return objs
