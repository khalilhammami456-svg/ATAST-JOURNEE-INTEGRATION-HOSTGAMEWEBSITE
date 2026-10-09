"""Body-offset garment shells (deterministic; no seam stitching).

Pipeline for a top (tee / hoodie / jacket / vest):
  1. take the posed avatar mesh, drop head / hands / legs by bone weights, cut with planes
     (neck, crotch, wrist or upper-arm, armhole) and keep the connected trunk+arms
  2. extrude the cut hip loop down to the hem (closed tube, rib band at the end)
  3. smooth the anatomy out of the surface and push it out by a height / arm-length ease profile
  4. assign pattern-space UVs (front & back = cylindrical panels, sleeves = cylindrical about the arm axis)
  5. (optional) cloth settle: neck ring pinned, gravity + body collision -> natural sag and folds
Everything is in world metres, avatar facing -Y, +X = wearer's left.
"""
import bpy, bmesh, math, json
from mathutils import Vector, Matrix
from mathutils.bvhtree import BVHTree
import garment_lib as gl

ARMS = {"L": dict(shoulder="mixamorig:LeftShoulder", arm="mixamorig:LeftArm", fore="mixamorig:LeftForeArm", hand="mixamorig:LeftHand", sgn=+1),
        "R": dict(shoulder="mixamorig:RightShoulder", arm="mixamorig:RightArm", fore="mixamorig:RightForeArm", hand="mixamorig:RightHand", sgn=-1)}


def _lerp_table(table, x):
    """Piecewise-linear lookup in [(x0,y0),(x1,y1),...] sorted by x."""
    if x <= table[0][0]:
        return table[0][1]
    for (xa, ya), (xb, yb) in zip(table[:-1], table[1:]):
        if x <= xb:
            t = (x - xa) / max(1e-9, xb - xa)
            t = t * t * (3 - 2 * t)
            return ya + (yb - ya) * t
    return table[-1][1]


class Body:
    """Posed avatar snapshot: world verts, faces, dominant bone per vertex, limb axes."""

    def __init__(self):
        ctx = bpy.context
        self.scn = ctx.scene
        self.ob = self.scn.cd.avatar
        dg = ctx.evaluated_depsgraph_get()
        ev = self.ob.evaluated_get(dg)
        me = ev.to_mesh()
        mw = ev.matrix_world
        self.co = [mw @ v.co for v in me.vertices]
        self.faces = [tuple(p.vertices) for p in me.polygons]
        names = {vg.index: vg.name for vg in self.ob.vertex_groups}
        dom = []
        for v in self.ob.data.vertices:
            dom.append(names[max(v.groups, key=lambda g: g.weight).group] if v.groups else "")
        self.dom = dom
        ev.to_mesh_clear()
        rig = self.ob.find_armature() if hasattr(self.ob, "find_armature") else None
        rig = gl.cd["avatar"].find_armature(self.ob)
        self.rig = rig
        self.bone = {}
        for b in rig.pose.bones:
            head = rig.matrix_world @ b.head
            tail = rig.matrix_world @ b.tail
            self.bone[b.name] = (head, tail)
        m = gl.cd["avatar"].measure(ctx)
        self.m = m
        self.z = {k: gl.cd["avatar"].z_of(m, k) for k in ("neck", "shoulder", "chest", "waist", "hip", "crotch", "knee", "ankle")}
        self.height = m["height"]
        self.bvh = BVHTree.FromPolygons(self.co, [tuple(f) for f in self.faces])

    def arm_axis(self, side):
        a = ARMS[side]
        sh = self.bone[a["arm"]][0]
        el = self.bone[a["fore"]][0]
        wr = self.bone[a["hand"]][0]
        return sh, el, wr


def _largest_component(bm, seed_co):
    seen, comps = set(), []
    for v in bm.verts:
        if v in seen:
            continue
        stack, comp = [v], []
        while stack:
            x = stack.pop()
            if x in seen:
                continue
            seen.add(x); comp.append(x)
            for e in x.link_edges:
                y = e.other_vert(x)
                if y not in seen:
                    stack.append(y)
        comps.append(comp)
    best = max(comps, key=len)
    keep = set(best)
    gone = [v for v in bm.verts if v not in keep]
    if gone:
        bmesh.ops.delete(bm, geom=gone, context='VERTS')


def _cut(bm, co, no, keep_side):
    """Bisect with a plane and delete the side not kept. keep_side: +1 keeps where (p-co).dot(no) > 0."""
    geom = list(bm.verts) + list(bm.edges) + list(bm.faces)
    r = bmesh.ops.bisect_plane(bm, geom=geom, plane_co=co, plane_no=no, dist=1e-5, use_snap_center=False,
                               clear_inner=(keep_side > 0), clear_outer=(keep_side < 0))
    return r


def extract(body, kind="hoodie", sleeve="long", neck_cut=None, hem_z=None, cuff_t=0.97, arm_cut_t=0.5, armhole_d=0.045,
            drop_neck=0.0, neck_r=0.095, neck_flare=0.45):
    """Return a bmesh of the garment base region (before extrusion/offset)."""
    bm = bmesh.new()
    # --- build bmesh of the entire body, then delete unwanted verts by bone / plane
    verts = [bm.verts.new(c) for c in body.co]
    bm.verts.index_update()
    for f in body.faces:
        try:
            bm.faces.new([verts[i] for i in f])
        except ValueError:
            pass
    bm.verts.ensure_lookup_table()
    bi = bm.verts.layers.int.new("bi")
    for i, v in enumerate(bm.verts):
        v[bi] = i
    z = body.z
    z_crotch = z["crotch"]
    drop = []
    for v in bm.verts:
        d = body.dom[v[bi]]
        if d.endswith("Head") or d.endswith("Neck") or "Hand" in d or "Toe" in d or d.endswith("Foot") or v.co.z < z_crotch:
            drop.append(v)
    # neck opening: remove a vertical cylinder around the neck axis so the collar hugs the neck instead of the trapezius
    if neck_r:
        cn = gl.cd["avatar"].center_at(body.m, z["neck"])
        for v in bm.verts:
            if v.co.z > z["shoulder"] - 0.06 and math.hypot(v.co.x - cn.x, v.co.y - cn.y) < neck_r + neck_flare * max(0.0, z["neck"] - v.co.z):
                drop.append(v)
    bmesh.ops.delete(bm, geom=list(set(drop)), context='VERTS')
    # --- planes: neck, crotch loop, sleeves
    nz = neck_cut if neck_cut is not None else z["neck"] + 0.06
    _cut(bm, Vector((0, 0, nz)), Vector((0, 0, 1)), -1)
    _cut(bm, Vector((0, 0, z_crotch + 0.03)), Vector((0, 0, 1)), +1)
    for side in ("L", "R"):
        sh, el, wr = body.arm_axis(side)
        if sleeve == "long":
            ax = (wr - el).normalized()
            p = el + (wr - el) * cuff_t
            _cut(bm, p, ax, -1)
        elif sleeve == "short":
            ax = (el - sh).normalized()
            p = sh + (el - sh) * arm_cut_t
            _cut(bm, p, ax, -1)
        else:   # armhole only: cut across the arm root
            ax = (el - sh).normalized()
            p = sh + ax * armhole_d
            _cut(bm, p, ax, -1)
    bm.verts.ensure_lookup_table()
    _largest_component(bm, Vector((0, 0, 1.3)))
    return bm


def boundary_loops(bm):
    """Ordered vertex loops of the open boundary."""
    bnd = [e for e in bm.edges if len(e.link_faces) == 1]
    adj = {}
    for e in bnd:
        for v in e.verts:
            adj.setdefault(v.index, []).append(e)
    seen, loops = set(), []
    for e in bnd:
        if e.index in seen:
            continue
        loop = []
        cur = e.verts[0]
        edge = e
        while edge is not None and edge.index not in seen:
            seen.add(edge.index)
            loop.append(cur)
            cur = edge.other_vert(cur)
            edge = next((x for x in adj.get(cur.index, []) if x.index not in seen), None)
        loops.append(loop)
    return loops


def fourier_ring(pos_xy, harmonics=3):
    """Low-pass the polar radius of a closed ring about its centroid (keeps the first `harmonics` harmonics)."""
    n = len(pos_xy)
    cx = sum(p[0] for p in pos_xy) / n; cy = sum(p[1] for p in pos_xy) / n
    ang = [math.atan2(p[1] - cy, p[0] - cx) for p in pos_xy]
    rad = [math.hypot(p[0] - cx, p[1] - cy) for p in pos_xy]
    # sort by angle to fit; evaluate back at each vertex's own angle
    order = sorted(range(n), key=lambda i: ang[i])
    a = [ang[i] for i in order]; r = [rad[i] for i in order]
    coef = [(sum(r[i] * math.cos(k * a[i]) for i in range(n)) * 2 / n, sum(r[i] * math.sin(k * a[i]) for i in range(n)) * 2 / n) for k in range(harmonics + 1)]
    out = []
    for i in range(n):
        rr = coef[0][0] / 2
        for k in range(1, harmonics + 1):
            rr += coef[k][0] * math.cos(k * ang[i]) + coef[k][1] * math.sin(k * ang[i])
        out.append((cx + rr * math.cos(ang[i]), cy + rr * math.sin(ang[i])))
    return out


def extrude_hem(bm, loop, z_hem, steps=7, flare=0.0, neck_in=0.0, roundness=0.6, rib_start=None, rib_shrink=0.0):
    """Extrude a hip loop straight down to z_hem in `steps` rings; rings are progressively rounded
    (Laplacian along the ring) so the peanut-shaped hip becomes a clean tube; last rings may narrow (rib)."""
    ring = loop
    z0 = sum(v.co.z for v in ring) / len(ring)
    rings = [ring]
    cx = sum(v.co.x for v in ring) / len(ring); cy = sum(v.co.y for v in ring) / len(ring)
    n = len(ring)
    for k in range(1, steps + 1):
        t = k / steps
        zk = z0 + (z_hem - z0) * t
        new = []
        prev = rings[-1]
        orig = [(v.co.x, v.co.y) for v in rings[0]]
        sm = fourier_ring(orig, harmonics=3)
        w = min(1.0, t * 1.6)                    # reach the clean smooth ring by ~60 % of the way down
        pos = [Vector((o[0] + (q[0] - o[0]) * w, o[1] + (q[1] - o[1]) * w, zk)) for o, q in zip(orig, sm)]
        # radial flare / rib
        c = Vector((sum(p.x for p in pos) / n, sum(p.y for p in pos) / n, zk))
        sc = 1.0 + flare * t
        if rib_start is not None and t >= rib_start:
            sc *= 1.0 - rib_shrink * (t - rib_start) / max(1e-6, 1 - rib_start)
        pos = [c + (p - c) * sc for p in pos]
        nv = [bm.verts.new(p) for p in pos]
        for i in range(n):
            j = (i + 1) % n
            try:
                bm.faces.new((prev[i], prev[j], nv[j], nv[i]))
            except ValueError:
                pass
        rings.append(nv)
    return rings


def smooth_verts(bm, iters=6, factor=0.5, keep=()):
    keep = set(keep)
    for _ in range(iters):
        bmesh.ops.smooth_vert(bm, verts=[v for v in bm.verts if v not in keep], factor=factor,
                              use_axis_x=True, use_axis_y=True, use_axis_z=True)


def ease_offset(bm, body, ease_torso, ease_arm, taper_sleeve=True, normals_smooth=2):
    """Push every vertex out along its (smoothed) normal by the ease profile.
    ease_torso: [(z, e)] ; ease_arm: [(t, e)] with t = 0 at shoulder .. 1 at wrist (cuff)."""
    bm.verts.index_update()
    bm.normal_update()
    # smooth the normals field a little: average with neighbours
    nrm = {v.index: v.normal.copy() for v in bm.verts}
    for _ in range(normals_smooth):
        new = {}
        for v in bm.verts:
            s = nrm[v.index].copy()
            for e in v.link_edges:
                s += nrm[e.other_vert(v).index]
            new[v.index] = s.normalized()
        nrm = new
    arms = {s: body.arm_axis(s) for s in ("L", "R")}
    # open-boundary vertices have a lopsided normal (one adjacent face): use the in-plane direction instead
    for v in bm.verts:
        if v.is_boundary:
            side, s_, d_, t_, q_, ax_ = arm_params(body, v.co)
            n = nrm[v.index]
            if d_ < 0.12 and t_ > 0.5:                       # cuff: remove the axial component
                n = (n - ax_ * n.dot(ax_))
            else:                                              # hem / neck: horizontal
                n = Vector((n.x, n.y, 0.0))
            if n.length > 1e-6:
                nrm[v.index] = n.normalized()
    for v in bm.verts:
        p = v.co
        # which limb is closest?  (distance from the arm axis polyline)
        e_t = _lerp_table(ease_torso, p.z)
        best = None
        for s, (sh, el, wr) in arms.items():
            for a, b, t0, t1 in ((sh, el, 0.0, 0.5), (el, wr, 0.5, 1.0)):
                ab = b - a
                u = max(0.0, min(1.0, (p - a).dot(ab) / max(1e-9, ab.length_squared)))
                q = a + ab * u
                d = (p - q).length
                if best is None or d < best[0]:
                    best = (d, t0 + (t1 - t0) * u, s)
        d, t, s = best
        # blend between torso ease and arm ease with a falloff on the distance to the arm axis
        w = max(0.0, min(1.0, (0.115 - d) / 0.05)) if t > 0.04 else 0.0
        e_a = _lerp_table(ease_arm, t)
        e = e_t * (1 - w) + e_a * w
        v.co = p + nrm[v.index] * e
    bm.normal_update()


def make_object(bm, name):
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    ob = bpy.data.objects.new(name, me)
    bpy.context.scene.collection.objects.link(ob)
    for p in me.polygons:
        p.use_smooth = True
    return ob


def loop_center(loop):
    n = len(loop)
    return Vector((sum(v.co.x for v in loop) / n, sum(v.co.y for v in loop) / n, sum(v.co.z for v in loop) / n))


def extrude_loop(bm, loop, direction, length, steps=4, scale=lambda t: 1.0, roundness=0.0, bulge=lambda t: 0.0):
    """Generic closed-loop extrusion along `direction` (unit vector) by `length`; each ring is scaled about
    the loop centre (in the plane perpendicular to `direction`)."""
    n = len(loop)
    c0 = loop_center(loop)
    d = direction.normalized()
    prev = loop
    rings = [loop]
    base = [Vector(v.co) for v in loop]
    for k in range(1, steps + 1):
        t = k / steps
        pos = []
        for p in base:
            r = p - c0
            r_par = d * r.dot(d)
            r_perp = r - r_par
            pos.append(c0 + r_par + r_perp * (scale(t) + bulge(t)) + d * (length * t))
        for _ in range(int(2 * roundness)):
            pos = [q.lerp((pos[i - 1] + pos[(i + 1) % n]) * 0.5, roundness * 0.5) for i, q in enumerate(pos)]
        nv = [bm.verts.new(p) for p in pos]
        for i in range(n):
            j = (i + 1) % n
            try:
                bm.faces.new((prev[i], prev[j], nv[j], nv[i]))
            except ValueError:
                pass
        rings.append(nv)
        prev = nv
    return rings


def regularize_ring(ring, planar_z=None, iters=12, factor=0.5):
    """Make a ring a clean smooth loop: periodic Laplacian smoothing (optionally flattened to a plane)."""
    n = len(ring)
    pos = [Vector(v.co) for v in ring]
    for _ in range(iters):
        pos = [p.lerp((pos[i - 1] + pos[(i + 1) % n]) * 0.5, factor) for i, p in enumerate(pos)]
    for v, p in zip(ring, pos):
        v.co = Vector((p.x, p.y, planar_z if planar_z is not None else p.z))


# ====================================================================== UV (pattern space)

def arm_params(body, p):
    """(side, s_chain, dist, t) for the nearest arm segment: s_chain = distance along the shoulder->elbow->wrist
    chain (metres), dist = distance to the axis, t = s_chain / chain length."""
    best = None
    for side in ("L", "R"):
        sh, el, wr = body.arm_axis(side)
        L1, L2 = (el - sh).length, (wr - el).length
        for a, b, s0, Lseg in ((sh, el, 0.0, L1), (el, wr, L1, L2)):
            ab = b - a
            u = max(0.0, min(1.0, (p - a).dot(ab) / max(1e-9, ab.length_squared)))
            q = a + ab * u
            d = (p - q).length
            if best is None or d < best[0]:
                best = (d, side, s0 + u * Lseg, (s0 + u * Lseg) / (L1 + L2), q, (b - a).normalized(), a)
    d, side, s, t, q, ax, a = best
    return side, s, d, t, q, ax


def torso_sections(verts_xyz, body, dz=0.015):
    """Per-height ellipse fit (cx, cy, a, b) of the trunk only (arm-free vertices)."""
    zs = {}
    for p in verts_xyz:
        side, s, d, t, q, ax = arm_params(body, p)
        if d < 0.16 and t > 0.03:
            continue
        zs.setdefault(round(p.z / dz), []).append(p)
    sec = {}
    for k, ps in zs.items():
        xs = [p.x for p in ps]; ys = [p.y for p in ps]
        sec[k] = ((max(xs) + min(xs)) / 2, (max(ys) + min(ys)) / 2, max(0.05, (max(xs) - min(xs)) / 2), max(0.04, (max(ys) - min(ys)) / 2))
    ks = sorted(sec)
    # moving-average smoothing across height so one odd slab (crotch loop, hem rings) cannot skew the fit
    sm = {}
    for k in ks:
        nb = [sec[j] for j in ks if abs(j - k) <= 3]
        sm[k] = tuple(sum(c[i] for c in nb) / len(nb) for i in range(4))
    return sm, ks, dz


def _section(sec, ks, dz, z):
    k = round(z / dz)
    if k in sec:
        return sec[k]
    nearest = min(ks, key=lambda x: abs(x - k))
    return sec[nearest]


def _ellipse_arc(a, b, theta):
    """Signed arc length of an ellipse (semi-axes a along x, b along y) from theta=0 (front) to theta, where
    theta is the polar angle measured by atan2(x/a, y/b) -> use the parametric angle."""
    n = 24
    s, prev = 0.0, 0.0
    sgn = 1.0 if theta >= 0 else -1.0
    th = abs(theta)
    for i in range(1, n + 1):
        t = th * i / n
        mid = th * (i - 0.5) / n
        s += math.sqrt((a * math.cos(mid)) ** 2 + (b * math.sin(mid)) ** 2) * (th / n)
    return sgn * s


def build_uv(ob, body, r_ref=0.07, name="pattern", ppm=2400, atlas=4096, pad=0.02, sleeve_t0=0.10, vtags=None):
    """Pattern-space UVs on the shell object. Pieces: Front, Back (arc length from centre-front/back x height),
    Sleeve_L, Sleeve_R (r*theta around the arm axis x -distance from the shoulder). Returns the atlas manifest;
    face material_index = piece index."""
    me = ob.data
    co = [v.co.copy() for v in me.vertices]
    # per-vertex limb info
    info = [arm_params(body, p) for p in co]
    sec, ks, dz = torso_sections(co, body)
    def vert_uv(i, piece):
        p = co[i]
        if piece in ("Front", "Back"):
            cx, cy, a, b = _section(sec, ks, dz, p.z)
            xi, eta = (p.x - cx) / a, (p.y - cy) / b
            if piece == "Front":
                th = math.atan2(xi, -eta)
            else:
                th = math.atan2(-xi, eta)
            return (_ellipse_arc(a, b, th), p.z)
        side, s, d, t, q, ax = info[i]
        sh, el, wr = body.arm_axis(side)
        lateral = Vector((1.0 if side == "L" else -1.0, 0, 0))
        u0 = (lateral - ax * lateral.dot(ax)).normalized()
        w = ax.cross(u0)
        if w.y < 0:          # make theta grow towards the back of the body (+Y)
            w = -w
        rv = p - q
        th = math.atan2(rv.dot(w), rv.dot(u0))
        return (r_ref * th * (1.0 if side == "L" else -1.0), -s)
    # classify faces
    names = ["Front", "Back", "Sleeve_L", "Sleeve_R"]
    face_piece = []
    for poly in me.polygons:
        vs = poly.vertices
        votes = {"L": 0, "R": 0, "T": 0}
        for i in vs:
            side, s, d, t, q, ax = info[i]
            if d < 0.115 and t > sleeve_t0:
                votes[side] += 1
            else:
                votes["T"] += 1
        if votes["L"] * 2 > len(vs):
            face_piece.append("Sleeve_L")
        elif votes["R"] * 2 > len(vs):
            face_piece.append("Sleeve_R")
        else:
            c = Vector((0, 0, 0))
            for i in vs:
                c += co[i]
            c /= len(vs)
            face_piece.append("Front" if poly.normal.y < 0 else "Back")
    uvl = me.uv_layers.get(name) or me.uv_layers.new(name=name)
    loc = {n: [] for n in names}
    uv_local = {}
    for pi, poly in enumerate(me.polygons):
        pn = face_piece[pi]
        poly.material_index = names.index(pn)
        for li in poly.loop_indices:
            vi = me.loops[li].vertex_index
            uv_local[li] = vert_uv(vi, pn)
            loc[pn].append(uv_local[li])
    boxes = {}
    for n in names:
        if not loc[n]:
            continue
        xs = [u for u, _ in loc[n]]; zs = [z for _, z in loc[n]]
        boxes[n] = dict(minx=min(xs), minz=min(zs), w=max(xs) - min(xs), h=max(zs) - min(zs))
    side_m = atlas / ppm
    x = y = rowh = 0.0
    placed = {}
    for n in sorted(boxes, key=lambda k: -boxes[k]["h"]):
        b = boxes[n]
        if x + b["w"] + pad > side_m:
            x = 0.0; y += rowh + pad; rowh = 0.0
        placed[n] = (x + pad * 0.5, y + pad * 0.5)
        x += b["w"] + pad
        rowh = max(rowh, b["h"])
    if y + rowh + pad > side_m:
        return build_uv(ob, body, r_ref, name, ppm * 0.9, atlas, pad, sleeve_t0, vtags)
    for pi, poly in enumerate(me.polygons):
        pn = face_piece[pi]
        b = boxes[pn]; ax_, ay_ = placed[pn]
        for li in poly.loop_indices:
            u, z = uv_local[li]
            uvl.data[li].uv = ((ax_ + (u - b["minx"])) / side_m, 1.0 - (ay_ + (b["minz"] + b["h"] - z)) / side_m)
    me.uv_layers.active = uvl
    manifest = dict(px_per_m=atlas / side_m, size_px=atlas, side_m=side_m, order=[n for n in names if n in boxes],
                    pieces={n: dict(ax=placed[n][0], ay=placed[n][1], w=boxes[n]["w"], h=boxes[n]["h"], minx=boxes[n]["minx"],
                                    minz=boxes[n]["minz"], flipx=False) for n in boxes})
    # polygons in piece-local metres for exact masks
    polys = {n: [] for n in boxes}
    ptags = {n: [] for n in boxes}
    for pi, poly in enumerate(me.polygons):
        polys[face_piece[pi]].append([[round(uv_local[li][0], 4), round(uv_local[li][1], 4)] for li in poly.loop_indices])
        tg = ""
        if vtags:
            cnt = {}
            for vi in poly.vertices:
                for k, sset in vtags.items():
                    if vi in sset:
                        cnt[k] = cnt.get(k, 0) + 1
            if cnt:
                k, c = max(cnt.items(), key=lambda kv: kv[1])
                if c * 2 >= len(poly.vertices):
                    tg = k
        ptags[face_piece[pi]].append(tg)
    manifest["polys"] = polys
    manifest["ptags"] = ptags
    # re-index material slots to manifest order
    order = manifest["order"]
    for pi, poly in enumerate(me.polygons):
        poly.material_index = order.index(face_piece[pi])
    ob["gl_atlas"] = json.dumps(manifest)
    return manifest


# ====================================================================== cloth settle

def settle(ob, body_ob, pin_verts, frames=60, quality=7, mass=0.30, tension=18.0, compression=18.0, shear=8.0,
           bending=6.0, damping=1.0, thickness=0.004, self_collision=True, gravity=1.0, shrink=0.0, progress=True):
    """Short cloth sim: pinned collar, gravity, body collision.  Bakes the result into the mesh (cage) and
    returns the number of frames simulated.  `pin_verts`: set of vertex indices with weight 1."""
    ctx = bpy.context
    scn = ctx.scene
    if "pin" in ob.vertex_groups:
        ob.vertex_groups.remove(ob.vertex_groups["pin"])
    vg = ob.vertex_groups.new(name="pin")
    if isinstance(pin_verts, dict):
        for i, w in pin_verts.items():
            if w > 0.001:
                vg.add([i], min(1.0, w), 'REPLACE')
    else:
        vg.add(sorted(pin_verts), 1.0, 'REPLACE')
    for m in list(ob.modifiers):
        if m.type == 'CLOTH':
            ob.modifiers.remove(m)
    cl = ob.modifiers.new("Cloth", 'CLOTH')
    st = cl.settings
    st.quality = quality; st.mass = mass
    st.tension_stiffness = tension; st.compression_stiffness = compression; st.shear_stiffness = shear
    st.bending_stiffness = bending
    st.tension_damping = 12.0; st.compression_damping = 12.0; st.shear_damping = 5.0; st.bending_damping = 0.5
    st.air_damping = damping
    st.vertex_group_mass = "pin"
    st.pin_stiffness = 1.0
    st.shrink_min = shrink
    st.effector_weights.gravity = gravity
    cs = cl.collision_settings
    cs.use_collision = True
    cs.distance_min = thickness
    cs.collision_quality = 4
    cs.friction = 8.0
    cs.use_self_collision = self_collision
    cs.self_distance_min = thickness * 0.8
    cs.self_friction = 3.0
    cs.damping = 0.4
    pc = cl.point_cache
    pc.frame_start = 1; pc.frame_end = frames + 2
    # body collision modifier (the avatar's own, configured by opensew2 ensure_collider)
    if not any(m.type == 'COLLISION' for m in body_ob.modifiers):
        body_ob.modifiers.new("Collision", 'COLLISION')
    body_ob.collision.thickness_outer = 0.002
    body_ob.collision.cloth_friction = 12.0
    scn.frame_set(1)
    for f in range(2, frames + 1):
        scn.frame_set(f)
    # bake: evaluated cage -> base mesh
    ctx.view_layer.update()
    dg = ctx.evaluated_depsgraph_get()
    ev = ob.evaluated_get(dg)
    me = ev.to_mesh()
    ok = len(me.vertices) == len(ob.data.vertices)
    if ok:
        coords = [v.co.copy() for v in me.vertices]
        ev.to_mesh_clear()
        for m in list(ob.modifiers):
            if m.type == 'CLOTH':
                ob.modifiers.remove(m)
        for v, c in zip(ob.data.vertices, coords):
            v.co = c
        ob.data.update()
    else:
        ev.to_mesh_clear()
    scn.frame_set(1)
    return frames if ok else 0


# ====================================================================== hood (worn down)

def make_hood(shell_ob, ring_world, body_ob, arc_deg=230, H=0.42, rows=22, flare=0.8, name="CD_Hood", frames=140,
              back_bias=0.55, mass=0.32, bending=14.0, thickness=0.005):
    """Hood hanging down the back: a funnel sheet rising from the back arc of the collar ring (pinned there),
    biased backwards, dropped under gravity onto the shell (collision) -> natural hood-down drape.
    ring_world: ordered list of Vector (the collar's top ring).  Returns the baked hood object."""
    ctx = bpy.context
    scn = ctx.scene
    n = len(ring_world)
    c = sum(ring_world, Vector()) / n
    ang = [math.atan2(p.y - c.y, p.x - c.x) for p in ring_world]
    half = math.radians(arc_deg / 2)
    back = math.pi / 2
    sel = []
    for i, a in enumerate(ang):
        d = (a - back + math.pi) % (2 * math.pi) - math.pi
        if abs(d) <= half:
            sel.append((d, i))
    sel.sort()                                     # from the wearer's right side (-d) round the back to the left (+d)
    idx = [i for _, i in sel]
    cols = len(idx)
    bm = bmesh.new()
    grid = []
    up = Vector((0, 0, 1))
    for j in range(rows + 1):
        v = j / rows
        row = []
        for k, i in enumerate(idx):
            base = ring_world[i]
            o = Vector((base.x - c.x, base.y - c.y, 0)).normalized()
            d = (o * 0.28 + up * 0.80 + Vector((0, 1, 0)) * back_bias * max(0.0, o.y)).normalized()
            # funnel widens with height (the hood is wider than the neck)
            lateral = Vector((-o.y, o.x, 0))
            spread = (k / max(1, cols - 1) - 0.5) * 2.0
            P = base + d * (H * v) + o * (flare * 0.12 * v) + lateral * (spread * 0.05 * v)
            row.append(bm.verts.new(P))
        grid.append(row)
    for j in range(rows):
        for k in range(cols - 1):
            bm.faces.new((grid[j][k], grid[j][k + 1], grid[j + 1][k + 1], grid[j + 1][k]))
    bm.verts.index_update()
    pin = {grid[0][k].index for k in range(cols)}
    pin_w = {i: 1.0 for i in pin}
    # second row gets a little help so the hood leaves the collar cleanly
    for k in range(cols):
        pin_w[grid[1][k].index] = 0.35
    hood = make_object(bm, name)
    # thicker, smoother
    for m in list(hood.modifiers):
        hood.modifiers.remove(m)
    # collider setup
    for ob in (shell_ob, body_ob):
        if not any(m.type == 'COLLISION' for m in ob.modifiers):
            ob.modifiers.new("Collision", 'COLLISION')
        ob.collision.thickness_outer = 0.002
        ob.collision.cloth_friction = 10.0
    ctx.view_layer.update()
    # cloth
    vg = hood.vertex_groups.new(name="pin")
    for i, w in pin_w.items():
        vg.add([i], w, 'REPLACE')
    cl = hood.modifiers.new("Cloth", 'CLOTH')
    st = cl.settings
    st.quality = 8; st.mass = mass
    st.tension_stiffness = 25; st.compression_stiffness = 25; st.shear_stiffness = 10
    st.bending_stiffness = bending
    st.tension_damping = 12; st.compression_damping = 12; st.shear_damping = 5; st.bending_damping = 0.8
    st.air_damping = 1.2
    st.vertex_group_mass = "pin"; st.pin_stiffness = 1.0
    cs = cl.collision_settings
    cs.use_collision = True; cs.distance_min = thickness; cs.collision_quality = 5; cs.friction = 10.0
    cs.use_self_collision = True; cs.self_distance_min = thickness * 0.8; cs.self_friction = 4.0
    cl.point_cache.frame_start = 1; cl.point_cache.frame_end = frames + 2
    scn.frame_set(1)
    for f in range(2, frames + 1):
        scn.frame_set(f)
    ctx.view_layer.update()
    ev = hood.evaluated_get(ctx.evaluated_depsgraph_get())
    me = ev.to_mesh()
    coords = [v.co.copy() for v in me.vertices]
    ev.to_mesh_clear()
    hood.modifiers.remove(cl)
    for v, p in zip(hood.data.vertices, coords):
        v.co = p
    hood.data.update()
    scn.frame_set(1)
    return hood


def make_hood_down(shell_ob, ring_world, body_ob, arc_deg=215, L=0.34, rows=20, bulge=0.062, taper=0.22, round_bottom=0.32,
                   name="CD_Hood", frames=36, mass=0.30, bending=18.0, thickness=0.004, settle=True):
    """Symmetric hood-down: a bag hanging from the back arc of the collar ring.  Built analytically
    (bulge profile + rounded bottom) so it is clean and symmetric, then relaxed by a short pinned cloth sim."""
    ctx = bpy.context
    scn = ctx.scene
    n = len(ring_world)
    c = sum(ring_world, Vector()) / n
    ang = [math.atan2(p.y - c.y, p.x - c.x) for p in ring_world]
    half = math.radians(arc_deg / 2)
    sel = []
    for i, a in enumerate(ang):
        d = (a - math.pi / 2 + math.pi) % (2 * math.pi) - math.pi
        if abs(d) <= half:
            sel.append((d, i))
    sel.sort()
    idx = [i for _, i in sel]
    cols = len(idx)
    bm = bmesh.new()
    grid = []
    for j in range(rows + 1):
        v = j / rows
        row = []
        env = max(0.0, math.sin(min(1.0, v * 1.12) * math.pi)) ** 0.8 * (0.35 + 0.65 * (1 - v)) + 0.03
        for k, i in enumerate(idx):
            base = ring_world[i]
            o = Vector((base.x - c.x, base.y - c.y, 0)).normalized()
            spread = (k / max(1, cols - 1) - 0.5) * 2.0
            drop = L * v * (1.0 - round_bottom * spread * spread * v)
            squeeze = 1.0 - taper * v
            P = Vector((c.x + (base.x - c.x) * squeeze, c.y + (base.y - c.y) * squeeze + 0.0, base.z)) + o * (bulge * env) + Vector((0, 0, -drop))
            # keep the hood behind the shoulders: push it back as it drops
            P.y += 0.035 * v
            row.append(bm.verts.new(P))
        grid.append(row)
    for j in range(rows):
        for k in range(cols - 1):
            bm.faces.new((grid[j][k], grid[j][k + 1], grid[j + 1][k + 1], grid[j + 1][k]))
    bm.verts.index_update()
    pin_w = {grid[0][k].index: 1.0 for k in range(cols)}
    for k in range(cols):
        pin_w[grid[1][k].index] = 0.30
    hood = make_object(bm, name)
    # pattern-space UV (analytic: u = arc length along the collar, v = -drop) + its own tiny atlas manifest
    me = hood.data
    uvl = me.uv_layers.new(name="pattern")
    xs_arc = [0.0]
    for k in range(1, cols):
        xs_arc.append(xs_arc[-1] + (ring_world[idx[k]] - ring_world[idx[k - 1]]).length)
    arc_total = xs_arc[-1]
    ppm, atlas = 2400, 2048
    w_m = arc_total; h_m = L
    side_m = atlas / ppm
    grid_uv = {}
    for j in range(rows + 1):
        for k in range(cols):
            grid_uv[grid[j][k].index] = (xs_arc[k] - arc_total / 2, -L * j / rows)
    polys = []
    for poly in me.polygons:
        loc = [grid_uv[vi] for vi in poly.vertices]
        polys.append([[round(a, 4), round(b, 4)] for a, b in loc])
    minx, minz = -arc_total / 2, -L
    for poly in me.polygons:
        for li in poly.loop_indices:
            vi = me.loops[li].vertex_index
            u, z = grid_uv[vi]
            uvl.data[li].uv = ((0.01 + (u - minx)) / side_m, 1.0 - (0.01 + (0.0 - z)) / side_m)
    hood["gl_atlas"] = json.dumps(dict(px_per_m=atlas / side_m, size_px=atlas, side_m=side_m, order=["Hood"],
                                       pieces={"Hood": dict(ax=0.01, ay=0.01, w=w_m, h=h_m, minx=minx, minz=minz, flipx=False)},
                                       polys={"Hood": polys}, ptags={"Hood": [""] * len(polys)}))
    if not settle:
        return hood
    for ob in (shell_ob, body_ob):
        if not any(m.type == 'COLLISION' for m in ob.modifiers):
            ob.modifiers.new("Collision", 'COLLISION')
        ob.collision.thickness_outer = 0.002
        ob.collision.cloth_friction = 10.0
    vg = hood.vertex_groups.new(name="pin")
    for i, w in pin_w.items():
        vg.add([i], w, 'REPLACE')
    cl = hood.modifiers.new("Cloth", 'CLOTH')
    st = cl.settings
    st.quality = 8; st.mass = mass
    st.tension_stiffness = 30; st.compression_stiffness = 30; st.shear_stiffness = 12
    st.bending_stiffness = bending
    st.tension_damping = 12; st.compression_damping = 12; st.shear_damping = 5; st.bending_damping = 0.8
    st.air_damping = 1.5
    st.vertex_group_mass = "pin"; st.pin_stiffness = 1.0
    cs = cl.collision_settings
    cs.use_collision = True; cs.distance_min = thickness; cs.collision_quality = 5; cs.friction = 10.0
    cs.use_self_collision = True; cs.self_distance_min = thickness * 0.8
    cl.point_cache.frame_start = 1; cl.point_cache.frame_end = frames + 2
    scn.frame_set(1)
    for f in range(2, frames + 1):
        scn.frame_set(f)
    ctx.view_layer.update()
    ev = hood.evaluated_get(ctx.evaluated_depsgraph_get())
    me = ev.to_mesh()
    coords = [v.co.copy() for v in me.vertices]
    ev.to_mesh_clear()
    hood.modifiers.remove(cl)
    for v, p in zip(hood.data.vertices, coords):
        v.co = p
    hood.data.update()
    scn.frame_set(1)
    return hood


# ====================================================================== mannequin + bottoms + shoes (styling)

def make_mannequin(body, name="Mannequin"):
    """Display body: avatar mesh without the face (eyes / mouth), capped by a smooth ovoid head, so renders read as a
    clean fashion mannequin instead of an uncanny bald face.  Collision still uses the original avatar mesh."""
    bm = bmesh.new()
    verts = [bm.verts.new(c) for c in body.co]
    bm.verts.index_update()
    for f in body.faces:
        try:
            bm.faces.new([verts[i] for i in f])
        except ValueError:
            pass
    head = [v for v in bm.verts if body.dom[v.index].endswith("Head")]
    hc = sum((v.co for v in head), Vector()) / max(1, len(head))
    zs = [v.co.z for v in head]
    ys = [v.co.y for v in head]; xs = [v.co.x for v in head]
    bmesh.ops.delete(bm, geom=head, context='VERTS')
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me); bm.free()
    ob = bpy.data.objects.new(name, me)
    bpy.context.scene.collection.objects.link(ob)
    # ovoid head
    hb = bmesh.new()
    bmesh.ops.create_uvsphere(hb, u_segments=48, v_segments=32, radius=1.0)
    rz = (max(zs) - min(zs)) * 0.5
    rx = (max(xs) - min(xs)) * 0.5
    ry = (max(ys) - min(ys)) * 0.5
    cz = (max(zs) + min(zs)) * 0.5
    for v in hb.verts:
        x, y, z = v.co
        # egg: slightly narrower at the chin
        k = 1.0 - 0.10 * max(0.0, -z)
        v.co = Vector((hc.x + x * rx * k, (max(ys) + min(ys)) * 0.5 + y * ry * k, cz - 0.018 + z * rz * (1.04 if z > 0 else 1.14)))
    hm = bpy.data.meshes.new(name + "_head")
    hb.to_mesh(hm); hb.free()
    ho = bpy.data.objects.new(name + "_head", hm)
    bpy.context.scene.collection.objects.link(ho)
    for p in hm.polygons:
        p.use_smooth = True
    for p in me.polygons:
        p.use_smooth = True
    ho.parent = None
    return ob, ho


def _body_bmesh(body):
    bm = bmesh.new()
    verts = [bm.verts.new(c) for c in body.co]
    bm.verts.index_update()
    for f in body.faces:
        try:
            bm.faces.new([verts[i] for i in f])
        except ValueError:
            pass
    bi = bm.verts.layers.int.new("bi")
    for i, v in enumerate(bm.verts):
        v[bi] = i
    return bm, bi


def _offset_normals(bm, dist, smooth=6):
    smooth_verts(bm, iters=smooth, factor=0.5)
    bm.verts.index_update()
    bm.normal_update()
    nrm = {v.index: v.normal.copy() for v in bm.verts}
    for v in bm.verts:
        n = nrm[v.index]
        if v.is_boundary:
            n = Vector((n.x, n.y, 0.0)) if n.length > 1e-6 else n
        d = dist(v.co) if callable(dist) else dist
        if n.length > 1e-6:
            v.co = v.co + n.normalized() * d
    bm.normal_update()


def make_trousers(body, name="Trousers", ankle_z=0.095, waist_z=None, ease=0.012, loose=0.0):
    """Slim trousers from the legs: hips down to the ankle, slim ease, waistband at waist_z."""
    bm, bi = _body_bmesh(body)
    z = body.z
    wz = waist_z if waist_z is not None else z["waist"] - 0.045
    drop = []
    for v in bm.verts:
        d = body.dom[v[bi]]
        keep_dom = ("Hips" in d) or ("UpLeg" in d) or (d.endswith("Leg")) or ("Spine" in d and v.co.z < wz)
        if not keep_dom or v.co.z > wz or v.co.z < ankle_z or "Foot" in d or "Toe" in d:
            drop.append(v)
    bmesh.ops.delete(bm, geom=drop, context='VERTS')
    _largest_component(bm, Vector((0, 0, 0.8)))
    for lp in boundary_loops(bm):
        zm = sum(v.co.z for v in lp) / len(lp)
        regularize_ring(lp, planar_z=(ankle_z if zm < 0.3 else wz), iters=10)
    _offset_normals(bm, lambda p: ease + loose * max(0.0, (p.z - ankle_z) / max(1e-6, wz - ankle_z)) * 0.0, smooth=4)
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me); bm.free()
    ob = bpy.data.objects.new(name, me)
    bpy.context.scene.collection.objects.link(ob)
    for p in me.polygons:
        p.use_smooth = True
    return ob


def make_shoes(body, name="Shoes", ease=0.020, sole=0.026, top=0.112, toe_lift=0.018):
    """Low sneakers: convex hull of each foot (everything below `top`), pushed out by `ease`, flat sole band
    (material index 1), toe spring.  Hull -> clean rounded shoe without toe serration."""
    out = bmesh.new()
    for side in (1, -1):
        pts = [Vector(c) for c in body.co if c.z < top and (c.x * side) > 0.0]
        cen = sum(pts, Vector()) / len(pts)
        # inflate points outward from the foot centre line (xy) to get shoe volume, keep sole at z=0
        P = []
        for p in pts:
            r = Vector((p.x - cen.x, p.y - cen.y, 0))
            q = Vector((p.x, p.y, p.z)) + (r.normalized() * ease if r.length > 1e-6 else Vector())
            q.z = p.z + (ease * 0.9 if p.z > 0.04 else 0.0)
            P.append(q)
        hb = bmesh.new()
        vs = [hb.verts.new(p) for p in P]
        res = bmesh.ops.convex_hull(hb, input=vs, use_existing_faces=False)
        interior = {g for g in (res.get("geom_interior", []) + res.get("geom_unused", [])) if isinstance(g, bmesh.types.BMVert)}
        if interior:
            bmesh.ops.delete(hb, geom=list(interior), context='VERTS')
        hb.verts.ensure_lookup_table()
        # toe spring + flat sole
        ymin = min(v.co.y for v in hb.verts)
        for v in hb.verts:
            if v.co.z < sole:
                v.co.z = 0.0
            if v.co.y < ymin + 0.07 and v.co.z > 0.0:
                v.co.z += toe_lift * (1 - (v.co.y - ymin) / 0.07) * 0.5
        # join into output
        vm = {}
        for v in hb.verts:
            vm[v] = out.verts.new(v.co)
        for f in hb.faces:
            try:
                out.faces.new([vm[v] for v in f.verts])
            except ValueError:
                pass
        hb.free()
    bmesh.ops.recalc_face_normals(out, faces=out.faces[:])
    me = bpy.data.meshes.new(name)
    out.to_mesh(me); out.free()
    ob = bpy.data.objects.new(name, me)
    bpy.context.scene.collection.objects.link(ob)
    for p in me.polygons:
        p.use_smooth = True
        zc = sum(me.vertices[i].co.z for i in p.vertices) / len(p.vertices)
        p.material_index = 1 if zc < sole * 0.8 else 0
    sub = ob.modifiers.new("ss", "SUBSURF"); sub.levels = 2; sub.render_levels = 2
    return ob
