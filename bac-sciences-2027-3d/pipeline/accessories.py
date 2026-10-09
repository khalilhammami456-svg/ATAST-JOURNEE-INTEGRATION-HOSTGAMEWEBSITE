"""Accessory builders: scarf (path-guided + cloth settle), 6-panel cap, beanie, tote, patch, woven label.
All return (objects..., manifest).  Units: metres; avatar faces -Y."""
import bpy, bmesh, math, json
from mathutils import Vector, Matrix
import shell, materials

SQ = lambda x: x * x


def _obj(bm, name, smooth=True):
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me); bm.free()
    ob = bpy.data.objects.new(name, me)
    bpy.context.scene.collection.objects.link(ob)
    if smooth:
        for p in me.polygons:
            p.use_smooth = True
    return ob


# ------------------------------------------------------------------------------------------------ scarf
def scarf_path(c, ring_r, z_ring, length, hang_y=-0.128, twist_len=0.12, n=190, ring_deg=(-58.0, 238.0), lift=0.0):
    """Centreline + width direction for a scarf worn round the neck with both ends hanging down the front."""
    a0, a1 = math.radians(ring_deg[0]), math.radians(ring_deg[1])
    ring_len = ring_r * (a1 - a0)
    hang = (length - ring_len) / 2.0
    pts = []
    # left hanging end (from bottom up to the ring start)
    p_ring0 = Vector((c.x + ring_r * math.cos(a0), c.y + ring_r * math.sin(a0), z_ring))
    p_ring1 = Vector((c.x + ring_r * math.cos(a1), c.y + ring_r * math.sin(a1), z_ring))
    def hang_points(p_ring, side):
        out = []
        m = int(n * hang / length)
        for i in range(m + 1):
            t = i / m                       # 0 at ring end, 1 at free end
            d = hang * t
            y = hang_y - 0.0 * t
            # blend from the ring tangent (leaving the ring) down to the chest line
            k = min(1.0, d / 0.10)
            x = p_ring.x * (1 - k) + side * 0.075 * k
            yy = p_ring.y * (1 - k) + hang_y * k
            out.append(Vector((x, yy - 0.012 * math.sin(min(1, d / 0.3) * math.pi) , z_ring - d * (0.2 + 0.8 * k))))
        return out
    left = hang_points(p_ring0, +1)
    right = hang_points(p_ring1, -1)
    ring = []
    m = int(n * ring_len / length)
    for i in range(1, m):
        a = a0 + (a1 - a0) * i / m
        ring.append(Vector((c.x + ring_r * math.cos(a), c.y + ring_r * math.sin(a), z_ring + lift * math.sin(i / m * math.pi))))
    path = list(reversed(left)) + ring + right        # from the free end of the left tail to the free end of the right tail
    # arclength
    s = [0.0]
    for a, b in zip(path[:-1], path[1:]):
        s.append(s[-1] + (b - a).length)
    # width direction: horizontal across on the hanging parts, vertical on the ring
    frames = []
    nl, nr = len(left), len(right)
    for i, p in enumerate(path):
        if i < nl:
            k = i / max(1, nl - 1)                       # 0 free end -> 1 at ring
        elif i >= len(path) - nr:
            k = (len(path) - 1 - i) / max(1, nr - 1)
        else:
            k = 1.0
        # twist weight: 0 = horizontal (hanging), 1 = vertical (on the ring)
        dist_to_ring = hang * (1 - k) if (i < nl or i >= len(path) - nr) else 0.0
        tw = 1.0 if dist_to_ring <= 0 else max(0.0, 1.0 - max(0.0, dist_to_ring - 0.05) / twist_len)
        tw = tw * tw * (3 - 2 * tw)
        frames.append(tw)
    return path, s, frames


def make_scarf(body, mannequin_head, length=1.7, width=0.17, thickness=0.006, name="CD_Scarf", frames=70, collide=()):
    hc = json.loads(mannequin_head["gl_head"])
    z_neck = body.z["neck"]
    c = Vector((0.0, body.m["height"] and 0.0, 0.0))
    cn = body.m and None
    from clothing_design import avatar as _av
    cc = _av.center_at(body.m, z_neck)
    c = Vector((0.0, cc.y, 0.0))
    z_ring = z_neck - 0.045
    path, s, tw = scarf_path(c, 0.108, z_ring, length)
    n = len(path)
    M = 10
    bm = bmesh.new()
    cols = []
    for i, p in enumerate(path):
        if 0 < i < n - 1:
            t = (path[i + 1] - path[i - 1]).normalized()
        else:
            t = (path[min(i + 1, n - 1)] - path[max(i - 1, 0)]).normalized()
        w_v = Vector((0, 0, 1)); w_h = Vector((1, 0, 0))
        w = (w_h * (1 - tw[i]) + w_v * tw[i]).normalized()
        w = (w - t * w.dot(t)).normalized()
        row = []
        for j in range(M + 1):
            off = (j / M - 0.5) * width
            row.append(bm.verts.new(p + w * off))
        cols.append(row)
    for i in range(n - 1):
        for j in range(M):
            bm.faces.new((cols[i][j], cols[i][j + 1], cols[i + 1][j + 1], cols[i + 1][j]))
    ob = _obj(bm, name)
    # UV: u = arclength (m), v = across (m)
    def piece(p):
        return "Scarf"
    me = ob.data
    def uv_of(vi, pn):
        i, j = divmod(vi, M + 1)
        return (s[i] - s[-1] / 2, (j / M - 0.5) * width)
    man = shell.generic_uv(ob, piece, uv_of, ["Scarf"], ppm=2000, atlas=4096, pad=0.01)
    # settle on the body
    return ob, man, dict(length=s[-1], width=width)


def make_scarf2(body, mannequin_head, top, length=1.7, width=0.17, name="CD_Scarf", n_ring=64, n_tail=70, thick_gap=0.016,
                fold=0.62, tail_delta=0.09, fringe=0.0, ring_r=0.122):
    """Conformal scarf: a cowl-like loop resting on the collar / shoulders of `top` (ray-cast from above) and two tails hanging on
    the chest (ray-cast from the front).  No cloth simulation: the path hugs the dressed model so it can never collapse.
    Returns (scarf_obj, manifest, info, fringe_obj_or_None)."""
    ctx = bpy.context
    from clothing_design import avatar as _av
    cc = _av.center_at(body.m, body.z["neck"])
    c = Vector((0.0, cc.y, 0.0))
    dg = ctx.evaluated_depsgraph_get()
    def cast(o, d):
        ok, loc, nrm, idx, hit, mw = ctx.scene.ray_cast(dg, o, d)
        return (loc, nrm) if ok and hit.name == top.name else (None, None)
    # ---- ring (cowl): angles from the right-front, round the back, to the left-front (the avatar faces -Y)
    a0, a1 = math.radians(-62.0), math.radians(242.0)
    ring = []
    ring_dirs = []
    for i in range(n_ring + 1):
        a = a0 + (a1 - a0) * i / n_ring
        d = Vector((math.cos(a), math.sin(a), 0.0))
        R = ring_r
        pos = nrm = None
        for _ in range(8):                      # step outwards until the ray lands on the garment (not on the head)
            o = c + d * R + Vector((0, 0, 2.2))
            pos, nrm = cast(o, Vector((0, 0, -1)))
            if pos is not None and pos.z < body.z["neck"] + 0.07:
                break
            R += 0.012
        if pos is None:
            pos = c + d * ring_r + Vector((0, 0, body.z["neck"] - 0.02)); nrm = Vector((0, 0, 1))
        ring.append(pos + nrm * (thick_gap * 0.8) + d * 0.004)
        ring_dirs.append(d)
    # ---- tails
    ring_len = sum((ring[i + 1] - ring[i]).length for i in range(n_ring))
    hang = (length - ring_len) / 2.0
    def tail(p_ring, side, h):
        pts = []
        m = n_tail
        x_end = side * 0.075
        for i in range(1, m + 1):
            t = i / m
            dd = h * t
            k = min(1.0, dd / 0.11)
            x = p_ring.x * (1 - k) + (x_end + side * 0.012 * math.sin(t * math.pi * 1.5)) * k
            z = p_ring.z - dd * (0.15 + 0.85 * min(1.0, dd / 0.13)) if False else p_ring.z - dd * (0.2 + 0.8 * k)
            pos, nrm = cast(Vector((x, -1.5, z)), Vector((0, 1, 0)))
            if pos is None:
                pos = Vector((x, p_ring.y - 0.02, z)); nrm = Vector((0, -1, 0))
            pts.append(pos + nrm * (thick_gap * (1.0 if k > 0.5 else 0.9)))
        return pts
    # right tail starts at the first ring point, left tail at the last one
    tail_r = tail(ring[0], +1, hang + tail_delta)
    tail_l = tail(ring[-1], -1, hang - tail_delta)
    path = list(reversed(tail_r)) + ring + tail_l
    nr_, nl_ = len(tail_r), len(tail_l)
    n = len(path)
    s = [0.0]
    for a, b in zip(path[:-1], path[1:]):
        s.append(s[-1] + (b - a).length)
    # ---- frames: ring -> cowl direction (tilted band), tails -> horizontal
    bm = bmesh.new()
    M = 10
    cols = []
    up = Vector((0, 0, 1))
    for i, p in enumerate(path):
        t = ((path[min(i + 1, n - 1)] - path[max(i - 1, 0)])).normalized()
        if nr_ <= i < nr_ + len(ring):
            d = ring_dirs[i - nr_]
            wv = (up * 0.92 + d * 0.22).normalized()                  # nearly vertical band, slightly flaring over the shoulders
            ring_w = fold
            fs = 1.0
        else:
            dist = (nr_ - 1 - i) if i < nr_ else (i - (nr_ + len(ring)))
            frac = max(0.0, 1.0 - dist * (hang / n_tail) / 0.12)      # 1 near the ring -> 0 away from it
            fs = frac * frac * (3 - 2 * frac)
            d = ring_dirs[0] if i < nr_ else ring_dirs[-1]
            wv_ring = (up * 0.92 + d * 0.22).normalized()
            wv = (Vector((1, 0, 0)) * (1 - fs) + wv_ring * fs).normalized()
            ring_w = fold + (1 - fold) * (1 - fs)
        wv = (wv - t * wv.dot(t)).normalized()
        row = []
        half = width * ring_w / 2
        bulge_dir = (d * 1.0 + up * 0.0)
        for j in range(M + 1):
            off = (j / M - 0.5) * width * ring_w
            arch = 0.034 * fs * max(0.0, 1.0 - (off / half) ** 2) if half > 1e-6 else 0.0
            row.append(bm.verts.new(p + wv * off + bulge_dir * arch))
        cols.append(row)
    for i in range(n - 1):
        for j in range(M):
            bm.faces.new((cols[i][j], cols[i][j + 1], cols[i + 1][j + 1], cols[i + 1][j]))
    end_rows = {e: (cols[e][0].co.copy(), cols[e][-1].co.copy()) for e in (0, n - 1)}
    ob = _obj(bm, name)
    def piece(p):
        return "Scarf"
    def uv_of(vi, pn):
        i, j = divmod(vi, M + 1)
        return (s[i] - s[-1] / 2, (j / M - 0.5) * width)
    man = shell.generic_uv(ob, piece, uv_of, ["Scarf"], ppm=2000, atlas=4096, pad=0.01)
    fr_ob = None
    if fringe > 0:
        fb = bmesh.new()
        import random
        rnd = random.Random(5)
        for end in (0, n - 1):
            p_end = path[end]
            tdir = (path[1] - path[0]).normalized() if end == 0 else (path[-1] - path[-2]).normalized()
            wv = (end_rows[end][1] - end_rows[end][0]).normalized()
            wlen = (end_rows[end][1] - end_rows[end][0]).length
            nstr = 22
            for q in range(nstr):
                f = (q + 0.5) / nstr - 0.5
                base = (end_rows[end][0] + end_rows[end][1]) * 0.5 + wv * f * wlen
                outward = tdir if end == n - 1 else -tdir
                L = fringe * (0.9 + 0.2 * rnd.random())
                sw = wlen / nstr * 0.42
                prev = None
                segs = 5
                for k in range(segs + 1):
                    tt = k / segs
                    pos = base + outward * (L * tt * 0.25) + Vector((0, 0, -L * tt * 0.95)) + wv * (f * 0.05 * tt) + Vector((0, 0, 0))
                    a_ = fb.verts.new(pos - wv * sw * (1 - 0.4 * tt)); b_ = fb.verts.new(pos + wv * sw * (1 - 0.4 * tt))
                    if prev:
                        fb.faces.new((prev[0], prev[1], b_, a_))
                    prev = (a_, b_)
        fr_ob = _obj(fb, name + "_Fringe")
    return ob, man, dict(length=s[-1], width=width), fr_ob


def settle_free(ob, colliders, frames=60, mass=0.35, bending=2.0, thickness=0.004, pin=None, gravity=1.0, tension=15.0, compression=15.0, shear=5.0):
    ctx = bpy.context; scn = ctx.scene
    for c in colliders:
        if not any(m.type == 'COLLISION' for m in c.modifiers):
            c.modifiers.new("Collision", 'COLLISION')
        c.collision.thickness_outer = 0.002; c.collision.cloth_friction = 12.0
    if pin:
        vg = ob.vertex_groups.new(name="pin")
        for i, w in pin.items():
            vg.add([i], w, 'REPLACE')
    cl = ob.modifiers.new("Cloth", 'CLOTH')
    st = cl.settings
    st.quality = 8; st.mass = mass
    st.tension_stiffness = tension; st.compression_stiffness = compression; st.shear_stiffness = shear; st.bending_stiffness = bending
    st.tension_damping = 10; st.compression_damping = 10; st.shear_damping = 4; st.bending_damping = 0.5; st.air_damping = 1.2
    if pin:
        st.vertex_group_mass = "pin"; st.pin_stiffness = 1.0
    st.effector_weights.gravity = gravity
    cs = cl.collision_settings
    cs.use_collision = True; cs.distance_min = thickness; cs.collision_quality = 5; cs.friction = 8.0
    cs.use_self_collision = True; cs.self_distance_min = thickness * 0.8
    cl.point_cache.frame_start = 1; cl.point_cache.frame_end = frames + 2
    scn.frame_set(1)
    for f in range(2, frames + 1):
        scn.frame_set(f)
    ctx.view_layer.update()
    ev = ob.evaluated_get(ctx.evaluated_depsgraph_get())
    me = ev.to_mesh(); coords = [v.co.copy() for v in me.vertices]; ev.to_mesh_clear()
    ob.modifiers.remove(cl)
    for v, p in zip(ob.data.vertices, coords):
        v.co = p
    ob.data.update(); scn.frame_set(1)


# ------------------------------------------------------------------------------------------------ cap
def make_cap(head, name="CD_Cap", ease=0.012, brim_len=0.092, brim_w=0.205, crown_lift=0.0):
    hc = json.loads(head["gl_head"]); cx, cy, cz = hc["c"]; rx, ry, rz = hc["r"]
    rx += ease; ry += ease; rzz = rz + ease * 0.8
    zb = cz - 0.28 * rz                                    # rim height (just above the brow)
    bm = bmesh.new()
    seg, rings = 48, 16
    verts = []
    for r in range(rings + 1):
        phi = (math.pi / 2) * r / rings                    # 0 at the rim, 90deg at the crown
        row = []
        for k in range(seg):
            th = 2 * math.pi * k / seg
            # slightly squared crown profile
            sphi = math.sin(phi) ** 0.9
            R = math.cos(phi)
            x = cx + rx * R * math.cos(th)
            y = cy + ry * R * math.sin(th) * (1.04 if math.sin(th) < 0 else 1.0)
            z = zb + (cz + rzz - zb) * sphi
            row.append(bm.verts.new((x, y, z)))
        verts.append(row)
    for r in range(rings):
        for k in range(seg):
            bm.faces.new((verts[r][k], verts[r][(k + 1) % seg], verts[r + 1][(k + 1) % seg], verts[r + 1][k]))
    # close the crown tip
    tip = bm.verts.new((cx, cy, cz + rzz))
    for k in range(seg):
        bm.faces.new((verts[rings][k], verts[rings][(k + 1) % seg], tip))
    crown = _obj(bm, name + "_Crown")
    # brim
    bm = bmesh.new()
    rows_b, cols_b = 10, 24
    grid = []
    ymin = cy - ry * 1.02
    for i in range(rows_b + 1):
        v = i / rows_b
        row = []
        for j in range(cols_b + 1):
            u = (j / cols_b - 0.5) * 2.0
            half_w = brim_w * 0.5 * math.sqrt(max(0.0, 1 - (v * 0.95) ** 2 * 0.0)) * (1 - 0.12 * v * v)
            x = cx + u * half_w * (1 - 0.18 * v)
            # outline: elliptical front edge
            edge = brim_len * math.sqrt(max(0.0, 1 - u * u * 0.78))
            y = ymin - edge * v
            z = zb - 0.004 - 0.020 * v * v - 0.010 * (u * u) * v
            row.append(bm.verts.new((x, y, z)))
        grid.append(row)
    for i in range(rows_b):
        for j in range(cols_b):
            bm.faces.new((grid[i][j], grid[i][j + 1], grid[i + 1][j + 1], grid[i + 1][j]))
    brim = _obj(bm, name + "_Brim")
    return crown, brim, dict(c=hc["c"], r=hc["r"], zb=zb, ymin=ymin)


def cap_uv(crown, brim, info):
    cx, cy, cz = info["c"]
    def piece(p):
        return "Front" if p.normal.y < 0 else "Back"
    def uv_of(vi, pn):
        v = crown.data.vertices[vi].co
        if pn == "Front":
            return (v.x - cx, v.z)
        return (-(v.x - cx), v.z)
    man = shell.generic_uv(crown, piece, uv_of, ["Front", "Back"], ppm=2400, atlas=2048)
    def bpiece(p): return "Brim"
    def buv(vi, pn):
        v = brim.data.vertices[vi].co
        return (v.x - cx, -(v.y - info["ymin"]))
    manb = shell.generic_uv(brim, bpiece, buv, ["Brim"], ppm=2400, atlas=1024)
    return man, manb


# ------------------------------------------------------------------------------------------------ beanie
def make_beanie(head, name="CD_Beanie", ease=0.014, cuff_h=0.060, height_k=0.62):
    hc = json.loads(head["gl_head"]); cx, cy, cz = hc["c"]; rx, ry, rz = hc["r"]
    rx += ease; ry += ease; rzz = rz + ease + 0.012
    zb = cz - 0.32 * rz
    bm = bmesh.new()
    seg, rings = 56, 22
    verts = []
    for r in range(rings + 1):
        phi = (math.pi / 2) * r / rings
        row = []
        for k in range(seg):
            th = 2 * math.pi * k / seg
            R = math.cos(phi) ** 0.85
            x = cx + rx * R * math.cos(th)
            y = cy + ry * R * math.sin(th)
            z = zb + (cz + rzz - zb) * math.sin(phi) ** 1.05
            row.append(bm.verts.new((x, y, z)))
        verts.append(row)
    for r in range(rings):
        for k in range(seg):
            bm.faces.new((verts[r][k], verts[r][(k + 1) % seg], verts[r + 1][(k + 1) % seg], verts[r + 1][k]))
    tip = bm.verts.new((cx, cy, cz + rzz))
    for k in range(seg):
        bm.faces.new((verts[rings][k], verts[rings][(k + 1) % seg], tip))
    # folded cuff: a thicker band (outward) rolled over the lower edge
    bm2 = bmesh.new()
    rows = 8
    cuff = []
    for j in range(rows + 1):
        v = j / rows
        row = []
        for k in range(seg):
            th = 2 * math.pi * k / seg
            roll = 0.012 * math.sin(v * math.pi)
            x = cx + (rx + 0.004 + roll) * math.cos(th)
            y = cy + (ry + 0.004 + roll) * math.sin(th)
            z = zb - 0.012 + cuff_h * v
            row.append(bm2.verts.new((x, y, z)))
        cuff.append(row)
    for j in range(rows):
        for k in range(seg):
            bm2.faces.new((cuff[j][k], cuff[j][(k + 1) % seg], cuff[j + 1][(k + 1) % seg], cuff[j + 1][k]))
    crown = _obj(bm, name + "_Crown")
    cuffo = _obj(bm2, name + "_Cuff")
    return crown, cuffo, dict(c=hc["c"], r=hc["r"], zb=zb, cuff_h=cuff_h)


def beanie_uv(crown, cuff, info, r_ref=0.10):
    """Cylindrical (arc-length) UVs so the knitted ribs keep their pitch on the dome and the folded cuff."""
    cx, cy, cz = info["c"]
    def theta(v, pn):
        return math.atan2(v.x - cx, -(v.y - cy)) if pn in ("Front", "CuffF") else math.atan2(-(v.x - cx), (v.y - cy))
    def piece(p): return "Front" if p.normal.y < 0 else "Back"
    def uv_of(vi, pn):
        v = crown.data.vertices[vi].co
        return (r_ref * theta(v, pn), v.z)
    m1 = shell.generic_uv(crown, piece, uv_of, ["Front", "Back"], ppm=2400, atlas=2048)
    def cpiece(p): return "CuffF" if p.normal.y < 0 else "CuffB"
    def cuv(vi, pn):
        v = cuff.data.vertices[vi].co
        return (r_ref * theta(v, pn), v.z)
    m2 = shell.generic_uv(cuff, cpiece, cuv, ["CuffF", "CuffB"], ppm=2400, atlas=2048)
    return m1, m2


# ------------------------------------------------------------------------------------------------ tote
def make_tote(w=0.40, h=0.38, d=0.11, handle=0.68, name="CD_Tote"):
    """Canvas tote standing on the floor: rounded box shell (open top) + two flat handle loops."""
    bm = bmesh.new()
    nx, nz, ny = 22, 24, 6
    # five-sided box built by projecting a subdivided cube: walls only (no top)
    def rounded(x, y, z):
        # soften the vertical edges
        return x, y, z
    verts = {}
    def V(i, j, k):
        key = (i, j, k)
        if key not in verts:
            x = (i / nx - 0.5) * w; z = (k / nz) * h; y = (j / ny - 0.5) * d
            verts[key] = bm.verts.new((x, y, z))
        return verts[key]
    # front (j=0) and back (j=ny) walls
    for jj in (0, ny):
        for i in range(nx):
            for k in range(nz):
                f = (V(i, jj, k), V(i + 1, jj, k), V(i + 1, jj, k + 1), V(i, jj, k + 1))
                bm.faces.new(f if jj == ny else tuple(reversed(f)))
    # side walls (i=0, nx)
    for ii in (0, nx):
        for j in range(ny):
            for k in range(nz):
                f = (V(ii, j, k), V(ii, j + 1, k), V(ii, j + 1, k + 1), V(ii, j, k + 1))
                bm.faces.new(tuple(reversed(f)) if ii == 0 else f)
    # bottom
    for i in range(nx):
        for j in range(ny):
            bm.faces.new((V(i, j, 0), V(i, j + 1, 0), V(i + 1, j + 1, 0), V(i + 1, j, 0)))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    bm.verts.index_update()
    # belly: pillow the big faces slightly, round the edges
    for v in bm.verts:
        x, y, z = v.co
        bulge = 0.018 * (1 - (2 * x / w) ** 2) * (1 - (2 * (z - h / 2) / h) ** 2)
        v.co.y = y + (bulge if y > 0 else -bulge) * (abs(y) / (d / 2) > 0.5)
        v.co.x = x * (1 - 0.04 * (abs(y) / (d / 2)) ** 2)
    shell.smooth_verts(bm, iters=2, factor=0.25)
    body = _obj(bm, name)
    # handles: flat bands on front/back, joined over the top (two loops)
    objs = []
    for side in (-1, 1):
        bm = bmesh.new()
        bw = 0.032
        pts = []
        for i in range(0, 41):
            t = i / 40
            # arch from the left anchor to the right anchor, slightly leaning outward
            x = (-0.13 + 0.26 * t)
            z = h + handle * 0.62 * math.sin(t * math.pi) ** 0.8
            y = side * (d / 2 + 0.002) * (1 - math.sin(t * math.pi) * 0.25) + side * 0.06 * math.sin(t * math.pi) ** 2
            pts.append(Vector((x, y, z)))
        # extend anchor tails down the wall
        tail = [Vector((-0.13, side * (d / 2 + 0.002), h - 0.09 * k / 5)) for k in range(5, 0, -1)]
        tailr = [Vector((0.13, side * (d / 2 + 0.002), h - 0.09 * k / 5)) for k in range(1, 6)]
        path = tail + pts + tailr
        rows = []
        for i, p in enumerate(path):
            a = path[max(i - 1, 0)]; b = path[min(i + 1, len(path) - 1)]
            t = (b - a).normalized()
            n = Vector((0, side, 0))
            wv = t.cross(n).normalized()
            rows.append((bm.verts.new(p - wv * bw / 2), bm.verts.new(p + wv * bw / 2)))
        for r0, r1 in zip(rows[:-1], rows[1:]):
            bm.faces.new((r0[0], r0[1], r1[1], r1[0]))
        ho = _obj(bm, name + "_Handle" + ("F" if side < 0 else "B"))
        sol = ho.modifiers.new("th", "SOLIDIFY"); sol.thickness = 0.004; sol.offset = 0
        objs.append(ho)
    return body, objs, dict(w=w, h=h, d=d)


def tote_uv(body, info):
    w, h, d = info["w"], info["h"], info["d"]
    def piece(p):
        n = p.normal
        if abs(n.y) > 0.6:
            return "Front" if n.y < 0 else "Back"
        return "Side"
    def uv_of(vi, pn):
        v = body.data.vertices[vi].co
        if pn == "Front": return (v.x, v.z)
        if pn == "Back": return (-v.x, v.z)
        return (v.y if v.x > 0 else -v.y, v.z)
    return shell.generic_uv(body, piece, uv_of, ["Front", "Back", "Side"], ppm=2400, atlas=2048)


# ------------------------------------------------------------------------------------------------ patch + label
def make_patch(r=0.040, t=0.0035, name="CD_Patch"):
    """Embroidered/woven patch: disc with a raised merrowed rim."""
    bm = bmesh.new()
    seg = 64
    ring = lambda rad, z: [bm.verts.new((rad * math.cos(2 * math.pi * k / seg), 0, z + rad * math.sin(2 * math.pi * k / seg))) for k in range(seg)]
    # profile in (rad, y) with the disc facing -Y
    prof = [(0.0, -t), (r * 0.80, -t), (r * 0.93, -t * 1.9), (r * 1.0, -t * 1.3), (r * 1.02, -t * 0.2), (r * 1.0, 0.0), (r * 0.5, 0.0), (0.0, 0.0)]
    rings = []
    for rad, y in prof:
        if rad == 0.0:
            rings.append([bm.verts.new((0, y, 0))])
        else:
            rings.append([bm.verts.new((rad * math.cos(2 * math.pi * k / seg), y, rad * math.sin(2 * math.pi * k / seg))) for k in range(seg)])
    for a, b in zip(rings[:-1], rings[1:]):
        if len(a) == 1:
            for k in range(seg):
                bm.faces.new((a[0], b[(k + 1) % seg], b[k]))
        elif len(b) == 1:
            for k in range(seg):
                bm.faces.new((a[k], a[(k + 1) % seg], b[0]))
        else:
            for k in range(seg):
                bm.faces.new((a[k], a[(k + 1) % seg], b[(k + 1) % seg], b[k]))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    ob = _obj(bm, name)
    def piece(p): return "Face" if p.normal.y < -0.3 else "Back"
    def uv_of(vi, pn):
        v = ob.data.vertices[vi].co
        return (v.x, v.z)
    man = shell.generic_uv(ob, piece, uv_of, ["Face", "Back"], ppm=9000, atlas=2048)
    return ob, man


def make_label(w=0.060, h=0.0125, t=0.0012, name="CD_Label"):
    """Woven end-fold label: flat strip with slightly lifted rolled edges."""
    bm = bmesh.new()
    nx, nz = 40, 6
    g = []
    for i in range(nx + 1):
        row = []
        for k in range(nz + 1):
            x = (i / nx - 0.5) * w
            z = (k / nz - 0.5) * h
            y = -t * (1.0 + 0.9 * (abs(2 * k / nz - 1)) ** 4) + 0.0004 * math.sin(i / nx * math.pi * 6)
            row.append(bm.verts.new((x, y, z)))
        g.append(row)
    for i in range(nx):
        for k in range(nz):
            bm.faces.new((g[i][k], g[i + 1][k], g[i + 1][k + 1], g[i][k + 1]))
    ob = _obj(bm, name)
    sol = ob.modifiers.new("th", "SOLIDIFY"); sol.thickness = t; sol.offset = 1.0
    def piece(p): return "Face"
    def uv_of(vi, pn):
        v = ob.data.vertices[vi].co
        return (v.x, v.z)
    man = shell.generic_uv(ob, piece, uv_of, ["Face"], ppm=24000, atlas=2048)
    return ob, man
