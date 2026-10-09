# Clothing Design - avatar measuring: body cross-sections, landmarks, limb axes.
#
# The body is described by a stack of horizontal cross-sections. Each section
# stores a centre and a radius per angular sector, so the torso reads as the
# ellipse it really is instead of a circle. Arms and head are masked out using
# the rig's own skin weights, otherwise a relaxed pose puts the arms inside the
# chest measurement and every garment comes out several sizes too big.
import bpy, json, math
from mathutils import Vector
from mathutils.bvhtree import BVHTree

NBINS = 96      # vertical cross-sections
NSEC = 16       # angular sectors per cross-section
SPACING = 0.007 # target spacing of surface samples (m)

PROPORTIONS = {
    "ankle": 0.039, "knee": 0.285, "crotch": 0.485, "hip": 0.530,
    "waist": 0.620, "chest": 0.720, "shoulder": 0.818, "neck": 0.870,
}

# Bone name candidates (lowercased substrings, first match wins).
BONE_TABLE = {
    "neck":   ["cc_base_necktwist01", "mixamorig:neck", "neck", "spine.004"],
    "chest":  ["cc_base_spine02", "mixamorig:spine2", "spine.003", "chest", "spine02"],
    "waist":  ["cc_base_waist", "mixamorig:spine", "spine.001", "waist", "spine01"],
    "hip":    ["cc_base_pelvis", "mixamorig:hips", "pelvis", "hips", "spine"],
}
# Limb chains: (start bone, end bone). The axis runs start.head -> end.head,
# because CC4 bone tails stop at twist bones and badly understate limb length.
LIMB_CHAINS = {
    "arm_l":   (["cc_base_l_upperarm", "mixamorig:leftarm", "upper_arm.l"],
                ["cc_base_l_forearm", "mixamorig:leftforearm", "forearm.l"]),
    "arm_r":   (["cc_base_r_upperarm", "mixamorig:rightarm", "upper_arm.r"],
                ["cc_base_r_forearm", "mixamorig:rightforearm", "forearm.r"]),
    "farm_l":  (["cc_base_l_forearm", "mixamorig:leftforearm", "forearm.l"],
                ["cc_base_l_hand", "mixamorig:lefthand", "hand.l"]),
    "farm_r":  (["cc_base_r_forearm", "mixamorig:rightforearm", "forearm.r"],
                ["cc_base_r_hand", "mixamorig:righthand", "hand.r"]),
    "thigh_l": (["cc_base_l_thigh", "mixamorig:leftupleg", "thigh.l"],
                ["cc_base_l_calf", "mixamorig:leftleg", "shin.l"]),
    "thigh_r": (["cc_base_r_thigh", "mixamorig:rightupleg", "thigh.r"],
                ["cc_base_r_calf", "mixamorig:rightleg", "shin.r"]),
    "calf_l":  (["cc_base_l_calf", "mixamorig:leftleg", "shin.l"],
                ["cc_base_l_foot", "mixamorig:leftfoot", "foot.l"]),
    "calf_r":  (["cc_base_r_calf", "mixamorig:rightleg", "shin.r"],
                ["cc_base_r_foot", "mixamorig:rightfoot", "foot.r"]),
}
# Vertex groups whose verts must not contribute to the torso cross-sections.
# Finger bones are named Index1/Mid1/Ring1/Pinky1 in CC4, not "indexfinger" -
# missing them puts the hands inside the torso cross-section, which reads as a
# 164 cm waist on a figure standing in an A-pose.
EXCLUDE_TORSO = ("upperarm", "forearm", "elbow", "wrist", "hand", "palm", "thumb",
                 "index", "mid", "ring", "pinky", "head", "eye", "teeth", "tongue",
                 "jaw", "facial", "brow", "nose", "lip", "cheek", "ear",
                 "leftarm", "rightarm")   # Mixamo upper arms have no "upperarm" in the name
# Keywords identifying the verts belonging to each limb.
LIMB_GROUPS = {
    "arm_l":   ("l_upperarm", "leftarm", "upper_arm.l"),
    "arm_r":   ("r_upperarm", "rightarm", "upper_arm.r"),
    "farm_l":  ("l_forearm", "leftforearm", "forearm.l"),
    "farm_r":  ("r_forearm", "rightforearm", "forearm.r"),
    "thigh_l": ("l_thigh", "leftupleg", "thigh.l"),
    "thigh_r": ("r_thigh", "rightupleg", "thigh.r"),
    "calf_l":  ("l_calf", "leftleg", "shin.l"),
    "calf_r":  ("r_calf", "rightleg", "shin.r"),
}


# ---------------------------------------------------------------- basics

def basis(facing):
    """(forward, side). side = forward rotated +90 deg CCW about Z (character's left)."""
    fwd = {'-Y': Vector((0, -1, 0)), '+Y': Vector((0, 1, 0)),
           '-X': Vector((-1, 0, 0)), '+X': Vector((1, 0, 0))}[facing]
    return fwd, Vector((-fwd.y, fwd.x, 0.0))


def _pct(sorted_vals, q):
    if not sorted_vals:
        return 0.0
    i = min(len(sorted_vals) - 1, max(0, int(q * (len(sorted_vals) - 1))))
    return sorted_vals[i]


def _median(vals):
    return sorted(vals)[len(vals) // 2] if vals else 0.0


def _smooth(vals, passes=2):
    out = list(vals)
    for _ in range(passes):
        nxt = list(out)
        for i in range(1, len(out) - 1):
            nxt[i] = (out[i - 1] + 2.0 * out[i] + out[i + 1]) * 0.25
        out = nxt
    return out


def _smooth_ring(vals, passes=1):
    out = list(vals)
    n = len(out)
    for _ in range(passes):
        out = [(out[(i - 1) % n] + 2.0 * out[i] + out[(i + 1) % n]) * 0.25 for i in range(n)]
    return out


def find_armature(ob):
    for mod in ob.modifiers:
        if mod.type == 'ARMATURE' and mod.object:
            return mod.object
    if ob.parent and ob.parent.type == 'ARMATURE':
        return ob.parent
    return None


def _find_bone(arm, keys):
    names = {b.name.lower(): b for b in arm.pose.bones}
    for k in keys:
        if k in names:
            return names[k]
    for k in keys:
        for n, b in names.items():
            if k in n:
                return b
    return None


# ------------------------------------------------- geometry extraction

def _bary_grid(k):
    out = []
    for i in range(k + 1):
        for j in range(k + 1 - i):
            out.append((i / k, j / k))
    return out


_BARY = {k: _bary_grid(k) for k in range(1, 6)}


def sample_body(ob, depsgraph, spacing=SPACING):
    """Area-weighted samples over the body surface, each tagged with the dominant
    vertex group of its triangle. Sampling the surface instead of the vertices
    matters: a 14k-vert base mesh leaves the cross-section bins far too sparse."""
    ev = ob.evaluated_get(depsgraph)
    try:
        me = ev.to_mesh()
    except Exception:
        return [], []
    try:
        me.calc_loop_triangles()
    except Exception:
        pass
    mw = ev.matrix_world.copy()
    gname = {g.index: g.name.lower() for g in ob.vertex_groups}

    co = [mw @ v.co for v in me.vertices]
    dom_v = []
    for v in me.vertices:
        if v.groups:
            top = max(v.groups, key=lambda g: g.weight)
            dom_v.append(gname.get(top.group, ""))
        else:
            dom_v.append("")

    pts, dom = [], []
    tris = me.loop_triangles
    if not len(tris):
        ev.to_mesh_clear()
        return co, dom_v
    for t in tris:
        i0, i1, i2 = t.vertices
        a, b, c = co[i0], co[i1], co[i2]
        ab, ac = b - a, c - a
        area = ab.cross(ac).length * 0.5
        k = int(math.sqrt(max(area, 0.0) * 2.0) / spacing) + 1
        k = min(5, max(1, k))
        lab = dom_v[i0] or dom_v[i1] or dom_v[i2]
        for u, v in _BARY[k]:
            pts.append(a + ab * u + ac * v)
            dom.append(lab)
    ev.to_mesh_clear()
    return pts, dom


def guess_facing(arm, pts, dom):
    """Toe bones are the most reliable forward cue on a standing character."""
    if arm is not None:
        acc = Vector((0, 0, 0))
        mw = arm.matrix_world
        for b in arm.pose.bones:
            if "toe" in b.name.lower():
                d = (mw @ b.tail) - (mw @ b.head)
                d.z = 0.0
                if d.length > 1e-9:
                    acc += d.normalized()
        if acc.length > 0.5:
            acc.normalize()
            if abs(acc.y) >= abs(acc.x):
                return '-Y' if acc.y < 0 else '+Y'
            return '-X' if acc.x < 0 else '+X'
    if not pts:
        return '-Y'
    zs = [p.z for p in pts]
    zmin, h = min(zs), max(1e-6, max(zs) - min(zs))
    feet = [p for p in pts if p.z < zmin + 0.06 * h]
    core = [p for p in pts if zmin + 0.40 * h < p.z < zmin + 0.70 * h]
    if not feet or not core:
        return '-Y'
    cx, cy = _median([p.x for p in core]), _median([p.y for p in core])
    dx = sum(p.x for p in feet) / len(feet) - cx
    dy = sum(p.y for p in feet) / len(feet) - cy
    if abs(dy) >= abs(dx):
        return '-Y' if dy < 0 else '+Y'
    return '-X' if dx < 0 else '+X'


def build_profile(pts, dom, fwd, side, nbins=NBINS, nsec=NSEC):
    zs = [p.z for p in pts]
    zmin, zmax = min(zs), max(zs)
    height = max(1e-6, zmax - zmin)

    keep = [i for i, d in enumerate(dom)
            if not any(k in d for k in EXCLUDE_TORSO)]
    if len(keep) < 200:            # unrigged mesh: fall back to everything
        keep = list(range(len(pts)))

    bins = [[] for _ in range(nbins)]
    for i in keep:
        p = pts[i]
        b = int((p.z - zmin) / height * nbins)
        bins[min(nbins - 1, max(0, b))].append(p)

    cx, cy, sect, count, cover = [], [], [], [], []
    last_c = (0.0, 0.0)
    last_r = [0.05] * nsec
    for b in bins:
        count.append(len(b))
        if len(b) < 12:
            cx.append(last_c[0]); cy.append(last_c[1]); sect.append(list(last_r))
            cover.append(0.0)
            continue
        xs, ys = sorted(p.x for p in b), sorted(p.y for p in b)
        mx = (_pct(xs, 0.02) + _pct(xs, 0.98)) * 0.5
        my = (_pct(ys, 0.02) + _pct(ys, 0.98)) * 0.5
        buckets = [[] for _ in range(nsec)]
        for p in b:
            d = Vector((p.x - mx, p.y - my, 0.0))
            r = d.length
            if r < 1e-6:
                continue
            ang = math.atan2(d.dot(side), d.dot(fwd)) % (2.0 * math.pi)
            buckets[min(nsec - 1, int(ang / (2.0 * math.pi) * nsec))].append(r)
        rr = []
        for k in range(nsec):
            rr.append(_pct(sorted(buckets[k]), 0.90) if len(buckets[k]) >= 3 else 0.0)
        # fill empty sectors from their neighbours
        known = [k for k in range(nsec) if rr[k] > 0.0]
        cover.append(len(known) / float(nsec))
        if not known:
            rr = list(last_r)
        else:
            for k in range(nsec):
                if rr[k] <= 0.0:
                    near = min(known, key=lambda j: min(abs(j - k), nsec - abs(j - k)))
                    rr[k] = rr[near]
        rr = _smooth_ring(rr, 1)
        cx.append(mx); cy.append(my); sect.append(rr)
        last_c, last_r = (mx, my), rr

    cols = [_smooth([sect[i][k] for i in range(nbins)], 2) for k in range(nsec)]
    sect = [[cols[k][i] for k in range(nsec)] for i in range(nbins)]

    return {"zmin": zmin, "zmax": zmax, "height": height, "nbins": nbins, "nsec": nsec,
            "cx": _smooth(cx), "cy": _smooth(cy), "sect": sect,
            # per-bin sample count and the fraction of sectors that had samples:
            # a slice is only a real circumference where the ring is complete
            "count": count, "cover": cover}


# ------------------------------------------------- profile queries

def _bin_t(m, z):
    return (z - m["zmin"]) / max(1e-9, m["height"]) * m["nbins"] - 0.5


def _lerp1(arr, t):
    n = len(arr)
    i = int(math.floor(t)); f = t - i
    return arr[min(n - 1, max(0, i))] * (1.0 - f) + arr[min(n - 1, max(0, i + 1))] * f


def center_at(m, z):
    t = _bin_t(m, z)
    return Vector((_lerp1(m["cx"], t), _lerp1(m["cy"], t), z))


def radius_at(m, z, theta=0.0):
    """Body radius at height z in direction theta (0 = forward, +CCW)."""
    t = _bin_t(m, z)
    n, nsec = m["nbins"], m["nsec"]
    i0 = min(n - 1, max(0, int(math.floor(t)))); f = t - math.floor(t)
    i1 = min(n - 1, max(0, i0 + 1))
    a = (theta % (2.0 * math.pi)) / (2.0 * math.pi) * nsec - 0.5
    k0 = int(math.floor(a)); g = a - k0
    k0 %= nsec; k1 = (k0 + 1) % nsec
    r0 = m["sect"][i0][k0] * (1 - g) + m["sect"][i0][k1] * g
    r1 = m["sect"][i1][k0] * (1 - g) + m["sect"][i1][k1] * g
    return r0 * (1 - f) + r1 * f


def girth_at(m, z, steps=48):
    """Circumference of the cross-section at height z."""
    prev = None; total = 0.0
    for i in range(steps + 1):
        th = 2.0 * math.pi * i / steps
        p = Vector((math.cos(th), math.sin(th), 0.0)) * radius_at(m, z, th)
        if prev is not None:
            total += (p - prev).length
        prev = p
    return total


def arc_width(m, z, th0, th1, steps=32):
    """Surface distance across the body from angle th0 to th1 at height z."""
    prev = None; total = 0.0
    for i in range(steps + 1):
        th = th0 + (th1 - th0) * i / steps
        p = Vector((math.cos(th), math.sin(th), 0.0)) * radius_at(m, z, th)
        if prev is not None:
            total += (p - prev).length
        prev = p
    return total


def slice_ok(m, z, min_cover=0.95, min_count=40):
    """Whether the cross-section at z is a complete ring of samples. Above the
    point where the head's skin weights take over, the masked profile thins
    to a partial ring and then to nothing, and the smoothed radii there are
    meaningless."""
    count, cover = m.get("count"), m.get("cover")
    if not count or not cover:
        return True
    i = int(round(_bin_t(m, z)))
    i = min(len(count) - 1, max(0, i))
    return count[i] >= min_count and cover[i] >= min_cover


def neck_girth(m):
    """True neck circumference: the narrowest slice above the shoulders. The
    'neck' landmark sits at the neck base and includes the trapezius, which is
    far too big to size a neckline from. Only near-complete rings are
    considered, and the scan stops once the head mask has eaten into the ring:
    past that the profile decays towards zero and would give a doll's neck.
    One missing sector is tolerated - on Mixamo-weighted rigs the head group
    dominates far down the neck, and demanding a perfect ring would end the
    scan at the trapezius and report the neck base as the neck."""
    z0 = z_of(m, "neck")
    best = girth_at(m, z0)
    z = z0
    while z < z0 + 0.13 and z < m["zmax"]:
        if not slice_ok(m, z, min_cover=0.90):
            break
        best = min(best, girth_at(m, z))
        z += 0.01
    return best


# ------------------------------------------------- figure

def figure_score(m):
    """Positive for a male figure, negative for a female one. Three ratios that
    differ reliably between adult bodies regardless of size: hip to chest girth,
    waist to hip girth, and shoulder width to hip width. Each term is scaled so
    that a typical figure scores about +-2 and a borderline one near 0."""
    zc, zw, zh, zs = (z_of(m, k) for k in ("chest", "waist", "hip", "shoulder"))
    chest, waist, hip = girth_at(m, zc), girth_at(m, zw), girth_at(m, zh)
    if min(chest, waist, hip) < 1e-6:
        return 0.0
    sh_w = radius_at(m, zs, math.pi * 0.5)
    hip_w = max(1e-6, radius_at(m, zh, math.pi * 0.5))
    s = (1.09 - hip / chest) * 10.0
    s += (waist / hip - 0.815) * 10.0
    s += (sh_w / hip_w - 1.045) * 10.0
    return s


def figure_guess(m):
    return 'MAN' if figure_score(m) >= 0.0 else 'WOMAN'


def figure(context, m=None):
    """The figure the blocks are drafted for: the scene override, or the guess."""
    choice = context.scene.cd.figure
    if choice != 'AUTO':
        return choice
    ob = context.scene.cd.avatar
    tag = ob.get("cd_figure") if ob is not None else None
    if tag in ('MAN', 'WOMAN'):
        return tag
    m = m or measure(context)
    if m is None:
        return 'WOMAN'
    return m.get("figure_auto") or figure_guess(m)


def z_of(m, name):
    lm = m.get("landmarks", {})
    if name in lm:
        return lm[name]
    return m["zmin"] + PROPORTIONS.get(name, 0.5) * m["height"]


# ------------------------------------------------- limbs

def limb_profile(pts, dom, keys, p0, p1, nbins=10):
    p0, p1 = Vector(p0), Vector(p1)
    axis = p1 - p0
    L = axis.length
    if L < 1e-6:
        return None
    u = axis / L
    sel = [i for i, d in enumerate(dom) if any(k in d for k in keys)]
    if len(sel) < 20:
        sel = range(len(pts))
    bins = [[] for _ in range(nbins)]
    for i in sel:
        d = pts[i] - p0
        t = d.dot(u)
        if t < 0.0 or t > L:
            continue
        bins[min(nbins - 1, int(t / L * nbins))].append((d - u * t).length)
    rads, last = [], 0.05
    ok = False
    for b in bins:
        if len(b) < 4:
            rads.append(last)
        else:
            last = max(_pct(sorted(b), 0.85), 1e-4)
            rads.append(last); ok = True
    if not ok:
        return None
    # Near its root a limb merges into the torso, and how far the torso flesh
    # leaks into the limb's vertex groups is a weight-painting style: Mixamo
    # weights hand the whole deltoid (or half the glute) to the upper arm or
    # thigh, and the root bins then read a 50 cm biceps on a 161 cm figure.
    # Cap the root bins by the interior profile - a real limb never doubles
    # its girth in its top fifth. The uncapped root is kept separately: it is
    # wrong as a tube girth but right as the deltoid, which is what the
    # shoulder point of a bodice is drafted from.
    rad_root = rads[0]
    if len(rads) >= 7:
        cap = max(rads[3:7]) * 1.10
        for i in range(3):
            rads[i] = min(rads[i], cap)
    return {"p0": list(p0), "p1": list(p1), "len": L,
            "rad": _smooth(rads, 1), "rad_root": rad_root}


def limb_radius_at(lp, t):
    return _lerp1(lp["rad"], t * len(lp["rad"]) - 0.5)


def limb_frame(lp):
    """(origin, axis, u, v) orthonormal frame for a limb."""
    p0, p1 = Vector(lp["p0"]), Vector(lp["p1"])
    ax = (p1 - p0).normalized()
    ref = Vector((0, 0, 1)) if abs(ax.z) < 0.9 else Vector((1, 0, 0))
    u = (ref - ax * ref.dot(ax)).normalized()
    v = ax.cross(u)
    return p0, ax, u, v


# ------------------------------------------------- top level

_CACHE = {}


def measure(context, ob=None, force=False):
    scn = context.scene
    ob = ob or scn.cd.avatar
    if ob is None or ob.type != 'MESH':
        return None
    key = [ob.name, scn.frame_current, scn.cd.facing]
    if not force and _CACHE.get("key") == key:
        return _CACHE.get("data")
    if not force and "cd_measure" in scn:
        try:
            data = json.loads(scn["cd_measure"])
            if data.get("key") == key:
                _CACHE["key"] = key; _CACHE["data"] = data
                return data
        except Exception:
            pass

    depsgraph = context.evaluated_depsgraph_get()
    pts, dom = sample_body(ob, depsgraph)
    if not pts:
        return None
    arm = find_armature(ob)
    fwd, side = basis(scn.cd.facing)

    m = build_profile(pts, dom, fwd, side)

    lm = {}
    if arm is not None:
        mw = arm.matrix_world
        for name, cands in BONE_TABLE.items():
            b = _find_bone(arm, cands)
            if b is not None:
                lm[name] = (mw @ b.head).z
    m["landmarks"] = lm

    m["limbs"] = {}
    if arm is not None:
        mw = arm.matrix_world
        for name, (ka, kb) in LIMB_CHAINS.items():
            ba, bb = _find_bone(arm, ka), _find_bone(arm, kb)
            if ba is None or bb is None:
                continue
            lp = limb_profile(pts, dom, LIMB_GROUPS.get(name, ()),
                              mw @ ba.head, mw @ bb.head)
            if lp:
                m["limbs"][name] = lp
        if "arm_l" in m["limbs"]:
            lm["shoulder"] = Vector(m["limbs"]["arm_l"]["p0"]).z
        if "thigh_l" in m["limbs"]:
            lm["crotch"] = Vector(m["limbs"]["thigh_l"]["p0"]).z
        if "calf_l" in m["limbs"]:
            lm["knee"] = Vector(m["limbs"]["calf_l"]["p0"]).z

    # The rig's waist bone sits low, near the navel. The anatomical waist - and
    # where a skirt or trouser waistband belongs - is the narrowest section
    # between hip and chest, so use that when the profile shows one.
    try:
        zh, zc = lm.get("hip"), lm.get("chest")
        if zh is not None and zc is not None and zc > zh + 0.08:
            best_z, best_g = None, 1e9
            z = zh + 0.03
            while z < zc - 0.02:
                g = girth_at(m, z)
                if g < best_g:
                    best_g, best_z = g, z
                z += 0.01
            if best_z is not None:
                lm["waist"] = best_z
    except Exception:
        pass
    # and the chest: the fullest section between waist and shoulder, not the
    # rig's chest bone. Where that bone sits is a rigging convention, not
    # anatomy - CC4 puts it at 71 % of stature and Mixamo at 76 %, which is
    # 8 cm on the same body and changes every armhole drafted from it. The
    # widest cross-section is the bust line whatever rig is underneath.
    try:
        zw, zs = lm.get("waist"), lm.get("shoulder")
        if zw is not None and zs is not None and zs > zw + 0.12:
            best_z, best_g = None, -1.0
            z = zw + 0.04
            while z < zs - 0.04:
                if slice_ok(m, z, min_cover=0.90):
                    g = girth_at(m, z)
                    if g > best_g:
                        best_g, best_z = g, z
                z += 0.01
            if best_z is not None:
                lm["chest"] = best_z
    except Exception:
        pass
    # likewise the hip: the widest section over the seat, not the pelvis bone
    try:
        zcr, zw = lm.get("crotch"), lm.get("waist")
        if zcr is not None and zw is not None and zw > zcr + 0.10:
            best_z, best_g = None, -1.0
            z = zcr + 0.02
            while z < zw - 0.05:
                g = girth_at(m, z)
                if g > best_g:
                    best_g, best_z = g, z
                z += 0.01
            if best_z is not None:
                lm["hip"] = best_z
    except Exception:
        pass
    m["landmarks"] = lm

    m["armature"] = arm.name if arm else ""
    m["facing"] = scn.cd.facing
    m["figure_auto"] = figure_guess(m)
    m["key"] = key
    scn["cd_measure"] = json.dumps(m)
    _CACHE["key"] = key; _CACHE["data"] = m
    return m


def auto_avatar(context):
    best, best_score = None, 0.0
    for ob in context.scene.objects:
        if ob.type != 'MESH' or ob.cd.is_pattern or ob.cd.is_garment:
            continue
        if not ob.visible_get() or len(ob.data.vertices) < 200:
            continue
        bb = [ob.matrix_world @ Vector(c) for c in ob.bound_box]
        h = max(p.z for p in bb) - min(p.z for p in bb)
        skinned = any(mod.type == 'ARMATURE' for mod in ob.modifiers)
        score = h * (2.0 if skinned else 1.0)
        if score > best_score:
            best_score, best = score, ob
    return best


def auto_facing(context, ob):
    depsgraph = context.evaluated_depsgraph_get()
    pts, dom = sample_body(ob, depsgraph)
    return guess_facing(find_armature(ob), pts, dom)


# ---------------------------------------------------------------- collision proxy

_BVH = {}


def body_bvh(context, ob=None):
    """World-space BVH of the avatar, for keeping arranged panels out of the body."""
    ob = ob or context.scene.cd.avatar
    if ob is None or ob.type != 'MESH':
        return None
    key = (ob.name, context.scene.frame_current)
    if _BVH.get("key") == key:
        return _BVH.get("tree")
    dg = context.evaluated_depsgraph_get()
    ev = ob.evaluated_get(dg)
    try:
        me = ev.to_mesh()
    except Exception:
        return None
    try:
        me.calc_loop_triangles()
    except Exception:
        pass
    mw = ev.matrix_world.copy()
    verts = [mw @ v.co for v in me.vertices]
    tris = [tuple(t.vertices) for t in me.loop_triangles]
    ev.to_mesh_clear()
    if not tris:
        return None
    tree = BVHTree.FromPolygons(verts, tris)
    _BVH["key"] = key
    _BVH["tree"] = tree
    return tree


def torso_bvh(context, ob=None):
    """BVH of the torso only. Seam detection tests whether the body sits between
    two panel edges; including the arms would block legitimate side seams on a
    figure standing with its arms down."""
    ob = ob or context.scene.cd.avatar
    if ob is None or ob.type != 'MESH':
        return None
    key = (ob.name, context.scene.frame_current, "torso")
    if _BVH.get("tkey") == key:
        return _BVH.get("ttree")
    dg = context.evaluated_depsgraph_get()
    ev = ob.evaluated_get(dg)
    try:
        me = ev.to_mesh()
        me.calc_loop_triangles()
    except Exception:
        return None
    mw = ev.matrix_world.copy()
    gname = {g.index: g.name.lower() for g in ob.vertex_groups}
    excl = []
    for v in me.vertices:
        d = ""
        if v.groups:
            d = gname.get(max(v.groups, key=lambda g: g.weight).group, "")
        excl.append(any(k in d for k in EXCLUDE_TORSO))
    verts = [mw @ v.co for v in me.vertices]
    tris = [tuple(t.vertices) for t in me.loop_triangles
            if not (excl[t.vertices[0]] and excl[t.vertices[1]] and excl[t.vertices[2]])]
    ev.to_mesh_clear()
    if not tris:
        return None
    tree = BVHTree.FromPolygons(verts, tris)
    _BVH["tkey"] = key
    _BVH["ttree"] = tree
    return tree


def push_out(co, bvh, clearance, max_move=0.06):
    """Lift a point clear of the body along the surface normal.

    Only the shortfall is added; snapping the point onto nearest-surface +
    clearance instead would collapse whole rings of verts onto the same spot
    wherever geometry crowds the surface, such as a sleeve at the armpit.
    """
    hit = bvh.find_nearest(co)
    if hit is None or hit[0] is None:
        return co
    loc, nor = hit[0], hit[1]
    gap = (co - loc).dot(nor)
    if gap >= clearance:
        return co
    return co + nor * min(clearance - gap, max_move)
