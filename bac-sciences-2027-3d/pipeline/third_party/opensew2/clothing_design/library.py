# Clothing Design - parametric garment presets.
#
# Each preset returns pattern pieces sized from the measured avatar plus the
# seams joining them, so adding a garment gives a complete sewn set rather than
# loose panels. Panel local +X is always the character's LEFT; build.py mirrors
# that axis for back-facing panels so side seams meet correctly.
import math
from mathutils import Vector
from . import avatar, patterns



def _ellipse_circ(a, b):
    """Ramanujan's approximation."""
    return math.pi * (3.0 * (a + b) - math.sqrt(max(0.0, (3 * a + b) * (a + 3 * b))))


def _curve_len(pts):
    return sum((pts[i + 1] - pts[i]).length for i in range(len(pts) - 1))


def _solve(fn, target, lo, hi, iters=40):
    """Bisection on a monotonically increasing fn."""
    if fn(lo) >= target:
        return lo
    if fn(hi) <= target:
        return hi
    for _ in range(iters):
        mid = (lo + hi) * 0.5
        if fn(mid) < target:
            lo = mid
        else:
            hi = mid
    return (lo + hi) * 0.5


def _neck_half(girth, df, db, fac=1.12):
    """Half-width of a neckline whose opening measures fac x the neck girth."""
    return _solve(lambda w: 0.5 * _ellipse_circ(w, df) + 0.5 * _ellipse_circ(w, db),
                  girth * fac, 0.02, 0.30)


def _cap_pts(cw, cap_h):
    """A set-in sleeve cap: back half then front half, apex at x = 0.

    A real cap is an S-curve - hollowed just above the underarm, full and
    rounded over the head of the arm - and the front half is scooped a
    little deeper than the back, because the front armhole is. Drawn as a
    plain arc it comes out a tent, and a tent-shaped cap sewn into a curved
    armhole is what puts those diagonal creases across the shoulder.
    """
    back = patterns.bezier((cw * 0.5, 0.0), (cw * 0.44, cap_h * 0.30),
                           (cw * 0.28, cap_h * 0.95), (0.0, cap_h), 18)
    front = patterns.bezier((0.0, cap_h), (-cw * 0.24, cap_h * 0.95),
                            (-cw * 0.46, cap_h * 0.26), (-cw * 0.5, 0.0), 18)
    return front, back


def _cap_len(cw, cap_h):
    f, b = _cap_pts(cw, cap_h)
    return _curve_len(f) + _curve_len(b)


def _armhole_len(half, sh_x, arm_d, sh_drop):
    """Length of one armhole curve (front or back)."""
    c = patterns.bezier((half, -arm_d), (half, -arm_d * 0.45),
                        (sh_x + 0.035, -sh_drop - 0.02), (sh_x, -sh_drop), 24)
    return _curve_len(c)


def _seg(name, pts):
    return (name, [Vector(p) for p in pts])


def _measurements(m):
    z = {k: avatar.z_of(m, k) for k in ("neck", "shoulder", "chest", "waist", "hip", "knee", "crotch", "ankle")}
    g = {k: avatar.girth_at(m, z[k]) for k in ("neck", "chest", "waist", "hip")}
    c = avatar.center_at(m, z["shoulder"])
    shoulder_half = 0.5 * m["height"] * 0.17
    lp = m.get("limbs", {}).get("arm_l")
    if lp:
        p0 = Vector(lp["p0"])
        # the deltoid: the uncapped limb root, not the biceps-safe tube radius
        r0 = lp.get("rad_root", avatar.limb_radius_at(lp, 0.0))
        shoulder_half = abs((p0 - avatar.center_at(m, p0.z)).length) + r0 * 0.6
    return z, g, shoulder_half


# ---------------------------------------------------------------- figure

# Drafting proportions that differ between men's and women's blocks. Girths
# always come from the avatar; these are the rules a cutter applies on top of
# them (Aldrich-style metric drafting, rounded to what the simulator resolves).
FIGURE = {
    'WOMAN': dict(
        neck_front=0.075, neck_back=0.022,      # scooped front, shallow back
        tank_front=0.095, tank_back=0.030,
        sh_drop=0.055, sh_x=0.93,               # sloped, narrower shoulder point
        top_extra=0.03,                         # cut past the hip: the stitch
                                                # phase hoists a top a few cm
        shape_waist=True,                       # side seams follow the waist in
        hem_hip=1.0,                            # hem cut to the hip girth
        tee_sleeve=0.15, sleeve_hem=0.82,       # short sleeve, narrow cuff
        rise=1.0,                               # trousers sit at the natural waist
    ),
    'MAN': dict(
        neck_front=0.060, neck_back=0.022,      # crew neck
        tank_front=0.085, tank_back=0.030,
        sh_drop=0.045, sh_x=1.0,                # squarer, full-width shoulder
        top_extra=0.065,                        # tops cover the hip, plus the
                                                # few cm the stitch hoists them
        shape_waist=False,                      # straight side seams
        hem_hip=0.98,                           # hem skims the hip
        tee_sleeve=0.20, sleeve_hem=0.88,       # longer sleeve, open cuff
        rise=0.78,                              # waistband below the natural waist
    ),
}


def _fig(m):
    return FIGURE.get(m.get("figure") or m.get("figure_auto") or 'WOMAN', FIGURE['WOMAN'])


def _sleeve_height(cap_h, length, arm_total):
    """Where the sleeve's UNDERARM line sits, as a fraction along the arm.

    A limb piece is anchored at its local y = 0, and on a sleeve that line
    is the underarm, not the middle of the piece: the cap rises above it and
    the sleeve hangs below. Anchoring the piece's centre instead - which is
    what this did - hung every sleeve about a third of the way down the arm,
    left the shoulder bare between the armhole and the cap, and is why
    sleeves read as loose tubes pinned to the elbows.
    """
    if arm_total <= 1e-6:
        return 0.0
    # Measured on both figures: the shoulder holds equally well anywhere in
    # 0.02-0.22, but the sleeve only reaches the wrist near the top of that
    # range - below it the cap is compressed into the armhole and the sleeve
    # concertinas up the arm. (The old formula put this at 0.59, which is
    # why sleeves used to hang off the elbows.)
    return 0.22


def _side_curve(hem, waist, top, n=7):
    """A side seam from the hem up through the waist to the underarm, with a
    vertical tangent at each end and at the waist so the seam reads as one
    smooth line rather than a kink at the waist."""
    dy1 = (waist[1] - hem[1]) * 0.5
    dy2 = (top[1] - waist[1]) * 0.5
    a = patterns.bezier(hem, (hem[0], hem[1] + dy1), (waist[0], waist[1] - dy1), waist, n)
    b = patterns.bezier(waist, (waist[0], waist[1] + dy2), (top[0], top[1] - dy2), top, n)
    return a + b[1:]


def _sides(m, fit, half, hem_half, L, arm_d):
    """Left side seam (hem -> underarm) and its mirror (underarm -> hem). For a
    shaped figure the seam goes in at the waist when the panel reaches below
    it; the amount is the side seam's share of the chest-to-waist difference,
    capped so an unusually small waist never pinches the cloth."""
    z, g, _ = _measurements(m)
    f = _fig(m)
    L_w = z["shoulder"] + SHELF - z["waist"]
    if f["shape_waist"] and L > L_w + 0.05 and L_w > arm_d + 0.04:
        waist_half = g["waist"] * 0.5 * (1.0 + fit) * 0.5 + 0.010
        waist_half = max(waist_half, min(half, hem_half) - 0.022)
        waist_half = min(waist_half, half, hem_half)
        left = _side_curve((hem_half, -L), (waist_half, -L_w), (half, -arm_d))
    else:
        left = [Vector((hem_half, -L)), Vector((half, -arm_d))]
    right = [Vector((-p[0], p[1])) for p in reversed(left)]
    return ("side_L", [Vector(p) for p in left]), ("side_R", right)


def _hem_half(m, fit, half, length_to):
    """Hem width of a top: chest-based, but never narrower than the hips it
    has to pass when the hem reaches them."""
    z, g, _ = _measurements(m)
    f = _fig(m)
    if z[length_to] <= z["hip"] + 0.03:
        return max(half, g["hip"] * 0.5 * (1.0 + fit) * 0.5 * f["hem_hip"])
    return half


# ---------------------------------------------------------------- tops

SHELF = 0.040   # how far the top of the shoulder sits above the arm joint


def _bodice(m, fit, length_to, neck_depth, neck_half, arm_d, sh_x, sh_drop=0.050,
            hem_half=None, split_hem=False, hem_dip=0.0, split_neck=False,
            scye_x=None):
    z, g, _ = _measurements(m)
    f = _fig(m)
    w = g["chest"] * 0.5 * (1.0 + fit)
    half = w * 0.5
    scye_x = half if scye_x is None else scye_x
    hem_half = _hem_half(m, fit, half, length_to) if hem_half is None else hem_half
    L = max(z["shoulder"] + SHELF - z[length_to], 0.12) + 0.03 + f["top_extra"]

    armhole_L = patterns.bezier((scye_x, -arm_d), (scye_x, -arm_d * 0.45),
                                (sh_x + 0.035, -sh_drop - 0.02), (sh_x, -sh_drop), 12)
    armhole_R = [Vector((-p.x, p.y)) for p in reversed(armhole_L)]
    neck = patterns.bezier((neck_half, 0.0), (neck_half * 0.55, -neck_depth),
                           (-neck_half * 0.55, -neck_depth), (-neck_half, 0.0), 14)
    if split_neck:
        half_n = len(neck) // 2
        neck_l, neck_r = neck[:half_n + 1], neck[half_n:]
    # a crotch curve: the hem dips between the legs so it reaches the leg tops
    hem = ([_seg("leg_R", [(-hem_half, -L), (-hem_half * 0.35, -L - hem_dip * 0.45),
                           (0.0, -L - hem_dip)]),
            _seg("leg_L", [(0.0, -L - hem_dip), (hem_half * 0.35, -L - hem_dip * 0.45),
                           (hem_half, -L)])]
           if split_hem else
           [_seg("hem", [(-hem_half, -L), (hem_half, -L)])])
    side_L, side_R = _sides(m, fit, scye_x, hem_half, L, arm_d)
    segs = hem + [
        side_L,
        ("arm_L",          armhole_L),
        _seg("shoulder_L", [(sh_x, -sh_drop), (neck_half, 0.0)]),
    ] + ([("neck_L", neck_l), ("neck_R", neck_r)] if split_neck else [("neck", neck)]) + [
        _seg("shoulder_R", [(-neck_half, 0.0), (-sh_x, -sh_drop)]),
        ("arm_R",          armhole_R),
        side_R,
    ]
    return segs, dict(z=z, g=g, half=half, hem_half=hem_half, L=L, arm_d=arm_d,
                      sh_x=sh_x, sh_drop=sh_drop)


def _draft_top(m, fit, sleeveless=False, sh_ext=1.0):
    """Work out neckline, armhole and sleeve so the cap actually fits the armhole."""
    z, g, sh_half = _measurements(m)
    f = _fig(m)
    half = g["chest"] * 0.5 * (1.0 + fit) * 0.5
    sh_drop = f["sh_drop"]
    # Outerwear is cut to the shoulder tip or a little past it (sh_ext): a
    # shoulder seam that stops short leaves the deltoid outside the panel,
    # and the armhole curve then starts inboard of the shoulder, so the top
    # of the arm is bare between the body and the sleeve head.
    sh_x = min(sh_half * f["sh_x"] * sh_ext, half * 0.98)
    df = f["neck_front"] if not sleeveless else f["tank_front"]
    db = f["neck_back"] if not sleeveless else f["tank_back"]
    ng = avatar.neck_girth(m)
    neck_half = _neck_half(ng, df, db, 1.12 if not sleeveless else 1.35)
    if sleeveless:
        sh_x = min(sh_x, neck_half + 0.050)

    lp = m.get("limbs", {}).get("arm_l")
    biceps_r = avatar.limb_radius_at(lp, 0.12) if lp else 0.05
    biceps = 2.0 * math.pi * biceps_r

    # The armhole DEPTH is anatomy: the shoulder line down to the armpit,
    # plus a little drop for comfort. Solving the depth from a required
    # length instead - which is what this used to do - drives the underarm
    # down to the waist on a figure with a full arm, and the sleeve, sewn at
    # the armpit where it belongs, then cannot reach it: the armhole seam
    # never closes and the shoulder is left bare through the gap.
    if lp:
        z_armpit = Vector(lp["p0"]).z - lp.get("rad_root", biceps_r)
    else:
        z_armpit = z["chest"]
    anat = (z["shoulder"] + SHELF) - z_armpit + 0.03

    # The armhole has to measure the arm root it is sewn around, and it is
    # allowed to drop below the armpit to get there - but only so far. Left
    # to solve freely it reached the waist on a full arm; held to anatomy it
    # was too short for any sleeve to fit. So: solve the depth, but never
    # more than 10 cm below the armpit, and buy any remaining length
    # sideways at the scye rather than going deeper still.
    need = biceps * (1.35 if not sleeveless else 1.05)
    arm_d = _solve(lambda t: 2.0 * _armhole_len(half, sh_x, t, sh_drop),
                   need, max(0.10, anat), anat + 0.10)
    scye = _solve(lambda e: 2.0 * _armhole_len(half + e, sh_x, arm_d, sh_drop),
                  need, 0.0, 0.05)
    scye_x = half + scye
    ah = 2.0 * _armhole_len(scye_x, sh_x, arm_d, sh_drop)
    return dict(neck_half=neck_half, df=df, db=db, arm_d=arm_d, sh_x=sh_x,
                sh_drop=sh_drop, half=half, scye_x=scye_x, armhole=ah,
                biceps=biceps, biceps_r=biceps_r,
                sleeve_hem=f["sleeve_hem"], tee_sleeve=f["tee_sleeve"])


def _sleeve(d, fit, length, width_ease=1.06):
    """A set-in sleeve, drafted the way one actually is: the sleeve is as
    wide as the arm needs, and the cap *height* is then solved so the cap
    measures the armhole it is sewn into.

    Doing it the other way round - fixing a shallow cap and widening the
    sleeve until it measured - is what produced a wide, droopy tube with a
    flat head: the only way a short cap reaches the length of an armhole is
    by getting very wide. Height first, width from the arm.
    """
    target = d["armhole"] * 1.02          # a little ease, eased in over the head
    # The sleeve has to be narrower than the armhole is long, or there is no
    # length left for the cap to rise in and it flattens into a tube sewn on
    # sideways. Width just clears the arm; the cap takes the rest.
    cw = max(d["biceps"] * width_ease, 0.05)
    cw = min(cw, target * 0.82)
    ceiling = d["arm_d"] * 0.95
    cap_h = _solve(lambda h: _cap_len(cw, h), target, 0.02, ceiling)
    if _cap_len(cw, cap_h) < target * 0.995:
        # even a full-height cap is too short for this armhole: the arm is
        # slim relative to the scye, so widen the sleeve to make up the rest
        cap_h = ceiling
        cw = _solve(lambda w: _cap_len(w, cap_h), target, cw, cw * 2.5)
    hw = cw * d.get("sleeve_hem", 0.90)
    front, back = _cap_pts(cw, cap_h)
    segs = [
        _seg("under_front", [(-cw * 0.5, 0.0), (-hw * 0.5, -length)]),
        _seg("hem",         [(-hw * 0.5, -length), (hw * 0.5, -length)]),
        _seg("under_back",  [(hw * 0.5, -length), (cw * 0.5, 0.0)]),
        ("cap_back",        back),
        ("cap_front",       front),
    ]
    return segs, cw, cap_h


def preset_tshirt(m, fit=0.14, sleeve_len=None):
    z, g, _ = _measurements(m)
    d = _draft_top(m, fit)
    front, info = _bodice(m, fit, "hip", d["df"], d["neck_half"], d["arm_d"], d["sh_x"], scye_x=d.get("scye_x"),
                          sh_drop=d["sh_drop"])
    back, _ = _bodice(m, fit, "hip", d["db"], d["neck_half"], d["arm_d"], d["sh_x"], scye_x=d.get("scye_x"),
                      sh_drop=d["sh_drop"])
    sl = sleeve_len if sleeve_len is not None else d["tee_sleeve"]
    sleeve, cw, cap_h = _sleeve(d, fit, sl)
    body_h = (z["shoulder"] + SHELF - info["L"] * 0.5 - m["zmin"]) / m["height"]
    # limb pieces are placed by their centre, so drop the sleeve until its cap
    # apex meets the shoulder joint
    arm_total = sum(m.get("limbs", {}).get(k, {}).get("len", 0.0) for k in ("arm_l", "farm_l"))
    sleeve_h = _sleeve_height(cap_h, sl, arm_total)

    pieces = [
        dict(name="Front", segs=front, anchor='TORSO_FRONT', height=body_h, ease=0.018),
        dict(name="Back",  segs=back,  anchor='TORSO_BACK',  height=body_h, ease=0.018),
        dict(name="Sleeve_L", segs=sleeve, anchor='ARM_L', height=sleeve_h, ease=0.014),
        dict(name="Sleeve_R", segs=sleeve, anchor='ARM_R', height=sleeve_h, ease=0.014),
    ]
    # flip says whether the two edges run in opposite directions along the outline
    seams = [
        ("Front", "side_L", "Back", "side_L", False),
        ("Front", "side_R", "Back", "side_R", False),
        ("Front", "shoulder_L", "Back", "shoulder_L", False),
        ("Front", "shoulder_R", "Back", "shoulder_R", False),
        ("Sleeve_L", "cap_front", "Front", "arm_L", True),
        ("Sleeve_L", "cap_back", "Back", "arm_L", False),
        ("Sleeve_L", "under_front", "Sleeve_L", "under_back", True),
        ("Sleeve_R", "cap_front", "Front", "arm_R", False),
        ("Sleeve_R", "cap_back", "Back", "arm_R", True),
        ("Sleeve_R", "under_front", "Sleeve_R", "under_back", True),
    ]
    return pieces, seams


def preset_tank(m, fit=0.10):
    z, g, _ = _measurements(m)
    d = _draft_top(m, fit, sleeveless=True)
    front, info = _bodice(m, fit, "hip", d["df"], d["neck_half"], d["arm_d"], d["sh_x"], scye_x=d.get("scye_x"),
                          sh_drop=d["sh_drop"])
    back, _ = _bodice(m, fit, "hip", d["db"], d["neck_half"], d["arm_d"], d["sh_x"], scye_x=d.get("scye_x"),
                      sh_drop=d["sh_drop"])
    body_h = (z["shoulder"] + SHELF - info["L"] * 0.5 - m["zmin"]) / m["height"]
    pieces = [
        dict(name="Front", segs=front, anchor='TORSO_FRONT', height=body_h, ease=0.014),
        dict(name="Back",  segs=back,  anchor='TORSO_BACK',  height=body_h, ease=0.014),
    ]
    seams = [
        ("Front", "side_L", "Back", "side_L", False),
        ("Front", "side_R", "Back", "side_R", False),
        ("Front", "shoulder_L", "Back", "shoulder_L", False),
        ("Front", "shoulder_R", "Back", "shoulder_R", False),
    ]
    return pieces, seams


# ---------------------------------------------------------------- bottoms

def preset_skirt(m, fit=0.10, length=0.45, flare=1.35):
    z, g, _ = _measurements(m)
    top = g["waist"] * 0.5 * (1.0 + fit)
    bot = top * flare
    L = length
    def half_panel():
        return [
            _seg("hem",    [(-bot * 0.5, -L), (bot * 0.5, -L)]),
            _seg("side_L", [(bot * 0.5, -L), (top * 0.5, 0.0)]),
            _seg("waist",  [(top * 0.5, 0.0), (-top * 0.5, 0.0)]),
            _seg("side_R", [(-top * 0.5, 0.0), (-bot * 0.5, -L)]),
        ]
    h = m["height"]
    hgt = (z["waist"] - L * 0.5 - m["zmin"]) / h
    pieces = [
        dict(name="Front", segs=half_panel(), anchor='TORSO_FRONT', height=hgt, ease=0.016),
        dict(name="Back",  segs=half_panel(), anchor='TORSO_BACK',  height=hgt, ease=0.016),
    ]
    seams = [("Front", "side_L", "Back", "side_L", False),
             ("Front", "side_R", "Back", "side_R", False)]
    return pieces, seams


def preset_trousers(m, fit=0.14, length_to="ankle"):
    """Hip yoke plus four leg panels. Leg tubes on their own slide straight off a
    tapering thigh; trousers are held up at the waist, so the yoke is what makes
    the garment stay where it belongs."""
    z, g, _ = _measurements(m)
    lp = m.get("limbs", {}).get("thigh_l")
    thigh_r = avatar.limb_radius_at(lp, 0.1) if lp else 0.09
    calf = m.get("limbs", {}).get("calf_l")
    ankle_r = avatar.limb_radius_at(calf, 0.95) if calf else 0.045

    f = _fig(m)
    # where the waistband sits: at the natural waist, or a way down towards
    # the hip for a man's low rise; the band is cut to the girth at that height
    rise = max(0.10, (z["waist"] - z["crotch"]) * f["rise"])
    z_top = z["crotch"] + rise
    hip_w = g["hip"] * 0.5 * (1.0 + fit)
    waist_w = avatar.girth_at(m, z_top) * 0.5 * (1.0 + fit * 0.5)
    L = max(0.15, z["crotch"] - z[length_to])
    top_w = math.pi * thigh_r * (1.0 + fit)
    bot_w = math.pi * ankle_r * (1.0 + fit) * 1.15

    def yoke():
        return [
            _seg("leg_R",  [(-hip_w * 0.5, -rise), (0.0, -rise)]),
            _seg("leg_L",  [(0.0, -rise), (hip_w * 0.5, -rise)]),
            _seg("side_L", [(hip_w * 0.5, -rise), (waist_w * 0.5, 0.0)]),
            _seg("waist",  [(waist_w * 0.5, 0.0), (-waist_w * 0.5, 0.0)]),
            _seg("side_R", [(-waist_w * 0.5, 0.0), (-hip_w * 0.5, -rise)]),
        ]

    # Only the outer part of a leg top joins the yoke; the inner part is the
    # crotch seam that joins the two legs. Sewing the whole leg top to the yoke
    # forces the surplus into a gather at the hip.
    out_len = min(hip_w * 0.5, top_w * 0.92)
    in_len = max(0.0, top_w - out_len)

    def leg(front=True):
        segs = [
            _seg("hem",    [(-bot_w * 0.5, -L), (bot_w * 0.5, -L)]),
            _seg("seam_a", [(bot_w * 0.5, -L), (top_w * 0.5, 0.0)]),
        ]
        x0 = top_w * 0.5
        if front:      # top edge runs outer -> inner
            segs.append(_seg("top_out", [(x0, 0.0), (x0 - out_len, 0.0)]))
            segs.append(_seg("top_in",  [(x0 - out_len, 0.0), (-x0, 0.0)]))
        else:          # back panel is mirrored: inner -> outer
            segs.append(_seg("top_in",  [(x0, 0.0), (x0 - in_len, 0.0)]))
            segs.append(_seg("top_out", [(x0 - in_len, 0.0), (-x0, 0.0)]))
        segs.append(_seg("seam_b", [(-top_w * 0.5, 0.0), (-bot_w * 0.5, -L)]))
        return segs

    leg_total = sum(m.get("limbs", {}).get(k, {}).get("len", 0.0)
                    for k in ("thigh_l", "calf_l"))
    leg_h = (L * 0.5) / leg_total if leg_total > 1e-6 else 0.25
    yoke_h = (z_top - rise * 0.5 - m["zmin"]) / m["height"]
    fs, bs = -math.pi * 0.5, math.pi * 0.5

    pieces = [
        dict(name="Hip_Front", segs=yoke(), anchor='HIP_FRONT', height=yoke_h, ease=0.016),
        dict(name="Hip_Back",  segs=yoke(), anchor='HIP_BACK',  height=yoke_h, ease=0.016),
        dict(name="Leg_L_Front", segs=leg(True),  anchor='LEG_L', height=leg_h, ease=0.016, spin=fs, taper=1.0),
        dict(name="Leg_L_Back",  segs=leg(False), anchor='LEG_L', height=leg_h, ease=0.016, spin=bs, taper=1.0),
        dict(name="Leg_R_Front", segs=leg(True),  anchor='LEG_R', height=leg_h, ease=0.016, spin=fs, taper=1.0),
        dict(name="Leg_R_Back",  segs=leg(False), anchor='LEG_R', height=leg_h, ease=0.016, spin=bs, taper=1.0),
    ]
    seams = [
        ("Hip_Front", "side_L", "Hip_Back", "side_L", False),
        ("Hip_Front", "side_R", "Hip_Back", "side_R", False),
        ("Leg_L_Front", "seam_a", "Leg_L_Back", "seam_b", True),
        ("Leg_L_Front", "seam_b", "Leg_L_Back", "seam_a", True),
        ("Leg_R_Front", "seam_a", "Leg_R_Back", "seam_b", True),
        ("Leg_R_Front", "seam_b", "Leg_R_Back", "seam_a", True),
        # yoke to leg tops, then the crotch seams joining the two legs
        ("Hip_Front", "leg_L", "Leg_L_Front", "top_out"),
        ("Hip_Front", "leg_R", "Leg_R_Front", "top_out"),
        ("Hip_Back", "leg_L", "Leg_L_Back", "top_out"),
        ("Hip_Back", "leg_R", "Leg_R_Back", "top_out"),
        ("Leg_L_Front", "top_in", "Leg_R_Front", "top_in"),
        ("Leg_L_Back", "top_in", "Leg_R_Back", "top_in"),
    ]
    return pieces, seams


def preset_jumpsuit(m, fit=0.10, sleeve_len=0.17, length_to="ankle"):
    """One piece: a bodice running shoulder to crotch, with four leg panels sewn
    to its split hem and to each other at the crotch."""
    z, g, _ = _measurements(m)
    d = _draft_top(m, fit)
    lp0 = m.get("limbs", {}).get("thigh_l")
    _thigh_r = avatar.limb_radius_at(lp0, 0.1) if lp0 else 0.09
    _top_w = math.pi * _thigh_r * (1.0 + fit)
    _in_len = max(0.09, _top_w * 0.28)
    # The bodice hem is sewn to the leg tops, so take its length from them, then
    # trade width for a crotch dip so the V-half still measures out_len.
    _out_len = _top_w - _in_len
    _dip = min(0.055, _out_len * 0.30)

    def _v_half(dip):
        # half-width whose three-point V (hem corner, mid dip, centre) measures out_len
        return _solve(lambda hh: _curve_len([Vector((hh, 0.0)), Vector((hh * 0.35, -dip * 0.45)),
                                             Vector((0.0, -dip))]), _out_len, 0.02, 0.60)
    hem_half = _v_half(_dip)
    front, info = _bodice(m, fit, "crotch", d["df"], d["neck_half"], d["arm_d"], d["sh_x"], scye_x=d.get("scye_x"),
                          sh_drop=d["sh_drop"], hem_half=hem_half, split_hem=True, hem_dip=_dip)
    back, _ = _bodice(m, fit, "crotch", d["db"], d["neck_half"], d["arm_d"], d["sh_x"], scye_x=d.get("scye_x"),
                      sh_drop=d["sh_drop"], hem_half=_v_half(_dip * 1.25), split_hem=True,
                      hem_dip=_dip * 1.25)
    sleeve, cw, cap_h = _sleeve(d, fit, sleeve_len)

    lp = m.get("limbs", {}).get("thigh_l")
    thigh_r = avatar.limb_radius_at(lp, 0.1) if lp else 0.09
    calf = m.get("limbs", {}).get("calf_l")
    ankle_r = avatar.limb_radius_at(calf, 0.95) if calf else 0.045
    L = max(0.15, z["crotch"] - z[length_to])
    top_w = math.pi * thigh_r * (1.0 + fit)
    bot_w = math.pi * ankle_r * (1.0 + fit) * 1.15
    in_len = _in_len
    out_len = max(0.02, top_w - in_len)

    def leg(front_panel=True):
        segs = [
            _seg("hem",    [(-bot_w * 0.5, -L), (bot_w * 0.5, -L)]),
            _seg("seam_a", [(bot_w * 0.5, -L), (top_w * 0.5, 0.0)]),
        ]
        x0 = top_w * 0.5
        if front_panel:
            segs.append(_seg("top_out", [(x0, 0.0), (x0 - out_len, 0.0)]))
            segs.append(_seg("top_in",  [(x0 - out_len, 0.0), (-x0, 0.0)]))
        else:
            segs.append(_seg("top_in",  [(x0, 0.0), (x0 - in_len, 0.0)]))
            segs.append(_seg("top_out", [(x0 - in_len, 0.0), (-x0, 0.0)]))
        segs.append(_seg("seam_b", [(-top_w * 0.5, 0.0), (-bot_w * 0.5, -L)]))
        return segs

    arm_total = sum(m.get("limbs", {}).get(k, {}).get("len", 0.0) for k in ("arm_l", "farm_l"))
    sleeve_h = _sleeve_height(cap_h, sleeve_len, arm_total)
    leg_total = sum(m.get("limbs", {}).get(k, {}).get("len", 0.0) for k in ("thigh_l", "calf_l"))
    leg_h = (L * 0.5) / leg_total if leg_total > 1e-6 else 0.25
    body_h = (z["shoulder"] + SHELF - info["L"] * 0.5 - m["zmin"]) / m["height"]
    fs, bs = -math.pi * 0.5, math.pi * 0.5

    pieces = [
        dict(name="Front", segs=front, anchor='TORSO_FRONT', height=body_h, ease=0.018),
        dict(name="Back",  segs=back,  anchor='TORSO_BACK',  height=body_h, ease=0.018),
        dict(name="Sleeve_L", segs=sleeve, anchor='ARM_L', height=sleeve_h, ease=0.014),
        dict(name="Sleeve_R", segs=sleeve, anchor='ARM_R', height=sleeve_h, ease=0.014),
        dict(name="Leg_L_Front", segs=leg(True),  anchor='LEG_L', height=leg_h, ease=0.016, spin=fs, taper=1.0),
        dict(name="Leg_L_Back",  segs=leg(False), anchor='LEG_L', height=leg_h, ease=0.016, spin=bs, taper=1.0),
        dict(name="Leg_R_Front", segs=leg(True),  anchor='LEG_R', height=leg_h, ease=0.016, spin=fs, taper=1.0),
        dict(name="Leg_R_Back",  segs=leg(False), anchor='LEG_R', height=leg_h, ease=0.016, spin=bs, taper=1.0),
    ]
    seams = [
        ("Front", "side_L", "Back", "side_L", False),
        ("Front", "side_R", "Back", "side_R", False),
        ("Front", "shoulder_L", "Back", "shoulder_L", False),
        ("Front", "shoulder_R", "Back", "shoulder_R", False),
        ("Sleeve_L", "cap_front", "Front", "arm_L", True),
        ("Sleeve_L", "cap_back", "Back", "arm_L", False),
        ("Sleeve_L", "under_front", "Sleeve_L", "under_back", True),
        ("Sleeve_R", "cap_front", "Front", "arm_R", False),
        ("Sleeve_R", "cap_back", "Back", "arm_R", True),
        ("Sleeve_R", "under_front", "Sleeve_R", "under_back", True),
        ("Leg_L_Front", "seam_a", "Leg_L_Back", "seam_b", True),
        ("Leg_L_Front", "seam_b", "Leg_L_Back", "seam_a", True),
        ("Leg_R_Front", "seam_a", "Leg_R_Back", "seam_b", True),
        ("Leg_R_Front", "seam_b", "Leg_R_Back", "seam_a", True),
        ("Front", "leg_L", "Leg_L_Front", "top_out"),
        ("Front", "leg_R", "Leg_R_Front", "top_out"),
        ("Back", "leg_L", "Leg_L_Back", "top_out"),
        ("Back", "leg_R", "Leg_R_Back", "top_out"),
        ("Leg_L_Front", "top_in", "Leg_R_Front", "top_in"),
        ("Leg_L_Back", "top_in", "Leg_R_Back", "top_in"),
    ]
    return pieces, seams


def preset_rectangle(m, fit=0.0):
    w = m["height"] * 0.28
    h = m["height"] * 0.35
    segs = [
        _seg("bottom", [(-w * 0.5, -h * 0.5), (w * 0.5, -h * 0.5)]),
        _seg("right",  [(w * 0.5, -h * 0.5), (w * 0.5, h * 0.5)]),
        _seg("top",    [(w * 0.5, h * 0.5), (-w * 0.5, h * 0.5)]),
        _seg("left",   [(-w * 0.5, h * 0.5), (-w * 0.5, -h * 0.5)]),
    ]
    z = avatar.z_of(m, "chest")
    return [dict(name="Panel", segs=segs, anchor='TORSO_FRONT',
                 height=(z - m["zmin"]) / m["height"], ease=0.02)], []


def _arc_angle(m, z, s):
    """Rough arc-length to angle at one height, for placing half panels."""
    r = max(0.02, avatar.radius_at(m, z, 0.0))
    return s / r


def preset_dress(m, fit=0.10, length_to="knee", flare=1.45, sleeve_len=0.0):
    """A-line shift dress: one panel front and back, flared from the underarm down."""
    z, g, _ = _measurements(m)
    d = _draft_top(m, fit, sleeveless=(sleeve_len <= 0.0))
    hem_half = g["hip"] * 0.5 * (1.0 + fit) * 0.5 * flare
    front, info = _bodice(m, fit, length_to, d["df"], d["neck_half"], d["arm_d"], d["sh_x"], scye_x=d.get("scye_x"), sh_drop=d["sh_drop"],
                          hem_half=hem_half)
    back, _ = _bodice(m, fit, length_to, d["db"], d["neck_half"], d["arm_d"], d["sh_x"], scye_x=d.get("scye_x"), sh_drop=d["sh_drop"],
                      hem_half=hem_half)
    body_h = (z["shoulder"] + SHELF - info["L"] * 0.5 - m["zmin"]) / m["height"]
    pieces = [
        dict(name="Front", segs=front, anchor='TORSO_FRONT', height=body_h, ease=0.020),
        dict(name="Back",  segs=back,  anchor='TORSO_BACK',  height=body_h, ease=0.020),
    ]
    seams = [
        ("Front", "side_L", "Back", "side_L", False),
        ("Front", "side_R", "Back", "side_R", False),
        ("Front", "shoulder_L", "Back", "shoulder_L", False),
        ("Front", "shoulder_R", "Back", "shoulder_R", False),
    ]
    if sleeve_len > 0.0:
        sleeve, cw, cap_h = _sleeve(d, fit, sleeve_len)
        arm_total = sum(m.get("limbs", {}).get(k, {}).get("len", 0.0) for k in ("arm_l", "farm_l"))
        sh = _sleeve_height(cap_h, sleeve_len, arm_total)
        pieces += [dict(name="Sleeve_L", segs=sleeve, anchor='ARM_L', height=sh, ease=0.014),
                   dict(name="Sleeve_R", segs=sleeve, anchor='ARM_R', height=sh, ease=0.014)]
        seams += [("Sleeve_L", "cap_front", "Front", "arm_L", True),
                  ("Sleeve_L", "cap_back", "Back", "arm_L", False),
                  ("Sleeve_L", "under_front", "Sleeve_L", "under_back", True),
                  ("Sleeve_R", "cap_front", "Front", "arm_R", False),
                  ("Sleeve_R", "cap_back", "Back", "arm_R", True),
                  ("Sleeve_R", "under_front", "Sleeve_R", "under_back", True)]
    return pieces, seams


def _open_front(m, fit, d, length_to, overlap=0.02):
    """Two front halves with a centre opening, for a jacket or hoodie."""
    z, g, _ = _measurements(m)
    f = _fig(m)
    half = g["chest"] * 0.5 * (1.0 + fit) * 0.5
    hem_half = _hem_half(m, fit, half, length_to)
    L = max(z["shoulder"] + SHELF - z[length_to], 0.12) + 0.03 + f["top_extra"]
    arm_d, sh_x, sh_drop = d["arm_d"], d["sh_x"], d["sh_drop"]
    scye_x = d.get("scye_x", half)
    nh = d["neck_half"]
    side_L, _ = _sides(m, fit, scye_x, hem_half, L, arm_d)
    # one HALF of the front: centre front (with a little overlap) out to the side
    armhole = patterns.bezier((scye_x, -arm_d), (scye_x, -arm_d * 0.45),
                              (sh_x + 0.035, -sh_drop - 0.02), (sh_x, -sh_drop), 12)
    # The front neck is cut to the same depth as any other top. It was
    # deepened by 4.5 cm at one point to keep lapels off an inner collar,
    # and that is what made the jacket slide: a 12 cm V has nothing to catch
    # on, so the garment runs down the body until the armholes stop it, and
    # the shoulders end up bare. Measured against a t-shirt on the same
    # avatar, this is the whole difference.
    df = d["df"]
    neck = patterns.bezier((nh, 0.0), (nh * 0.62, -df * 0.85),
                           (nh * 0.22, -df), (0.0, -df), 10)
    # The front edge is cut in three: open above the button, closed at it,
    # open below. A jacket that is stitched shut from throat to hem is a
    # pullover; one button holds it on the body and still shows lapels above
    # and a vent below, which is how a jacket is actually worn.
    L_w = z["shoulder"] + SHELF - z["waist"]
    btn_top = min(max(L_w - 0.05, df + 0.06), L - 0.10)
    btn_bot = btn_top + 0.09
    left = [
        _seg("hem",      [(-overlap, -L), (hem_half, -L)]),
        side_L,
        ("arm_L",        armhole),
        _seg("shoulder_L", [(sh_x, -sh_drop), (nh, 0.0)]),
        ("neck_L",       neck),
        _seg("lapel_L",  [(0.0, -df), (0.0, -btn_top)]),
        _seg("button_L", [(0.0, -btn_top), (0.0, -btn_bot)]),
        _seg("vent_L",   [(0.0, -btn_bot), (-overlap, -L)]),
    ]
    right = [(n.replace("_L", "_R"), [Vector((-p[0], p[1])) for p in reversed(pts)])
             for n, pts in left]
    right = list(reversed(right))
    return left, right, L, half, overlap


def preset_jacket(m, fit=0.12, length_to="hip", sleeve_len=None, closed_front=True):
    """Jacket: two front halves, a back and long sleeves. The fronts are sewn
    together below the lapel V - a buttoned jacket. An unfastened open front
    is marginal physics on any dress form (nothing anchors it against the
    sleeves' weight, and it slides off one run in three); pass
    closed_front=False if you want one anyway and style it by hand."""
    z, g, _ = _measurements(m)
    d = _draft_top(m, fit)
    # a sewn-shut front is butted edge to edge; only an open one gets the
    # button-stand overlap, or the seam crosses the panels into a knot
    left, right, L, half, overlap = _open_front(m, fit, d, length_to,
                                                overlap=0.0 if closed_front else 0.02)
    back, info = _bodice(m, fit, length_to, d["db"], d["neck_half"], d["arm_d"], d["sh_x"], scye_x=d.get("scye_x"),
                         sh_drop=d["sh_drop"])
    arm_total = sum(m.get("limbs", {}).get(k, {}).get("len", 0.0) for k in ("arm_l", "farm_l"))
    # cut past the wrist: a long sleeve takes up several centimetres bunching
    # over the elbow, so one drafted to the arm's length settles short of it
    sl = sleeve_len if sleeve_len is not None else max(0.20, arm_total * 1.08)
    sleeve, cw, cap_h = _sleeve(d, fit, sl)
    sh = _sleeve_height(cap_h, sl, arm_total)
    body_h = (z["shoulder"] + SHELF - L * 0.5 - m["zmin"]) / m["height"]
    # closed: both halves arranged meeting at centre front, where they are
    # sewn. Open: spun apart so the lapels hang loose to either side.
    off = 0.0 if closed_front else _arc_angle(m, z["chest"], (half - overlap) * 0.5)
    pieces = [
        dict(name="Front_L", segs=left,  anchor='TORSO_FRONT', height=body_h, ease=0.034, spin=off),
        dict(name="Front_R", segs=right, anchor='TORSO_FRONT', height=body_h, ease=0.034, spin=-off),
        dict(name="Back",    segs=back,  anchor='TORSO_BACK',  height=body_h, ease=0.034),
        dict(name="Sleeve_L", segs=sleeve, anchor='ARM_L', height=sh, ease=0.032),
        dict(name="Sleeve_R", segs=sleeve, anchor='ARM_R', height=sh, ease=0.032),
    ]
    seams = [
        ("Front_L", "side_L", "Back", "side_L", False),
        ("Front_R", "side_R", "Back", "side_R", False),
        ("Front_L", "shoulder_L", "Back", "shoulder_L", False),
        ("Front_R", "shoulder_R", "Back", "shoulder_R", False),
        ("Sleeve_L", "cap_front", "Front_L", "arm_L", True),
        ("Sleeve_L", "cap_back", "Back", "arm_L", False),
        ("Sleeve_L", "under_front", "Sleeve_L", "under_back", True),
        ("Sleeve_R", "cap_front", "Front_R", "arm_R", False),
        ("Sleeve_R", "cap_back", "Back", "arm_R", True),
        ("Sleeve_R", "under_front", "Sleeve_R", "under_back", True),
    ]
    if closed_front:
        # just the button: the lapels above it and the vent below stay open
        seams.append(("Front_L", "button_L", "Front_R", "button_R", True))
    return pieces, seams


def _hood(neck_f, neck_b, height, face_first):
    """One side of a hood. face_first puts the face opening at +X.

    The neck edge is cut to the necklines it will be sewn to, front and back
    separately, not from the neck girth: a hood cut larger than its neckline
    drags the front neck up into a crease, and one cut to the average of a
    deep front and a shallow back gathers at one and stretches at the other.
    """
    depth = (neck_f + neck_b) * 0.5
    dip = depth * 0.10
    depth_f = math.sqrt(max(1e-6, neck_f ** 2 - dip ** 2))
    depth_b = math.sqrt(max(1e-6, neck_b ** 2 - dip ** 2))
    face = _seg("face", [(depth_f, 0.0), (depth_f * 0.86, height)])
    crown = ("crown", patterns.bezier((depth_f * 0.86, height), (depth * 0.15, height * 1.12),
                                      (-depth * 0.95, height * 0.72), (-depth_b, 0.0), 14))
    segs = [
        _seg("neck_back",  [(-depth_b, 0.0), (0.0, -dip)]),
        _seg("neck_front", [(0.0, -dip), (depth_f, 0.0)]),
        face, crown,
    ]
    if face_first:
        return segs
    return [(n, [Vector((-p[0], p[1])) for p in pts]) for n, pts in segs]


def preset_hoodie(m, fit=0.20, length_to="hip", sleeve_len=None):
    """Sweater body with long sleeves and a two-panel hood."""
    z, g, _ = _measurements(m)
    d = _draft_top(m, fit)
    ng = avatar.neck_girth(m)
    nh = d["neck_half"] * 1.12
    dfh, dbh = d["df"] * 1.15, d["db"] * 1.3
    front, info = _bodice(m, fit, length_to, dfh, nh, d["arm_d"], d["sh_x"], scye_x=d.get("scye_x"),
                          sh_drop=d["sh_drop"], split_neck=True)
    back, _ = _bodice(m, fit, length_to, dbh, nh, d["arm_d"], d["sh_x"], scye_x=d.get("scye_x"),
                      sh_drop=d["sh_drop"], split_neck=True)
    # the hood's neck edge has to measure the same as the neckline it joins
    nl_f = _curve_len(patterns.bezier((nh, 0.0), (nh * 0.55, -dfh),
                                      (-nh * 0.55, -dfh), (-nh, 0.0), 14)) * 0.5
    nl_b = _curve_len(patterns.bezier((nh, 0.0), (nh * 0.55, -dbh),
                                      (-nh * 0.55, -dbh), (-nh, 0.0), 14)) * 0.5
    hood_f, hood_b = max(0.03, nl_f / 1.005), max(0.03, nl_b / 1.005)
    hood_h = max(0.12, ng * 0.62)
    arm_total = sum(m.get("limbs", {}).get(k, {}).get("len", 0.0) for k in ("arm_l", "farm_l"))
    # cut past the wrist: a long sleeve takes up several centimetres bunching
    # over the elbow, so one drafted to the arm's length settles short of it
    sl = sleeve_len if sleeve_len is not None else max(0.20, arm_total * 1.08)
    sleeve, cw, cap_h = _sleeve(d, fit, sl)
    sh = _sleeve_height(cap_h, sl, arm_total)
    body_h = (z["shoulder"] + SHELF - info["L"] * 0.5 - m["zmin"]) / m["height"]
    head_h = (z["neck"] + ng * 0.30 - m["zmin"]) / m["height"]
    pieces = [
        dict(name="Front", segs=front, anchor='TORSO_FRONT', height=body_h, ease=0.036),
        dict(name="Back",  segs=back,  anchor='TORSO_BACK',  height=body_h, ease=0.036),
        dict(name="Sleeve_L", segs=sleeve, anchor='ARM_L', height=sh, ease=0.034),
        dict(name="Sleeve_R", segs=sleeve, anchor='ARM_R', height=sh, ease=0.034),
        # spun towards the back so the hood lies behind the head rather than
        # collapsing over the face, which is where an unworn hood belongs
        dict(name="Hood_L", segs=_hood(hood_f, hood_b, hood_h, False),
             anchor='TORSO_LEFT', height=head_h, ease=0.06, wrap=0.8, spin=0.62),
        dict(name="Hood_R", segs=_hood(hood_f, hood_b, hood_h, True),
             anchor='TORSO_RIGHT', height=head_h, ease=0.06, wrap=0.8, spin=-0.62),
    ]
    seams = [
        ("Front", "side_L", "Back", "side_L", False),
        ("Front", "side_R", "Back", "side_R", False),
        ("Front", "shoulder_L", "Back", "shoulder_L", False),
        ("Front", "shoulder_R", "Back", "shoulder_R", False),
        ("Sleeve_L", "cap_front", "Front", "arm_L", True),
        ("Sleeve_L", "cap_back", "Back", "arm_L", False),
        ("Sleeve_L", "under_front", "Sleeve_L", "under_back", True),
        ("Sleeve_R", "cap_front", "Front", "arm_R", False),
        ("Sleeve_R", "cap_back", "Back", "arm_R", True),
        ("Sleeve_R", "under_front", "Sleeve_R", "under_back", True),
        ("Hood_L", "crown", "Hood_R", "crown"),
        ("Hood_L", "neck_front", "Front", "neck_L"),
        ("Hood_R", "neck_front", "Front", "neck_R"),
        ("Hood_L", "neck_back", "Back", "neck_L"),
        ("Hood_R", "neck_back", "Back", "neck_R"),
    ]
    return pieces, seams


PRESETS = {
    'TSHIRT':    ("T-Shirt",   preset_tshirt),
    'TANK':      ("Tank Top",  preset_tank),
    'SKIRT':     ("Skirt",     preset_skirt),
    'TROUSERS':  ("Trousers",  preset_trousers),
    'JUMPSUIT':  ("Jumpsuit",  preset_jumpsuit),
    'DRESS':     ("Dress",     preset_dress),
    'JACKET':    ("Jacket",    preset_jacket),
    'HOODIE':    ("Hoodie",    preset_hoodie),
    'RECTANGLE': ("Flat Panel", preset_rectangle),
}

# Complete outfits: (label, figure, [(preset, ease), ...]) worn from the inside out.
# Trousers and skirts are worn FIRST, tops untucked over the waistband -
# the order people actually dress in. A top sewn under the trousers leaves
# its hem beneath the waistband, and trousers closing over a slippery shirt
# instead of skin slide down a low-rise hip exactly like beltless trousers
# over an untucked shirt do in life.
OUTFITS = {
    'M_CASUAL':  ("Casual",         'MAN',   [('TROUSERS', 0.12), ('TSHIRT', 0.10), ('JACKET', 0.13)]),
    'M_STREET':  ("Streetwear",     'MAN',   [('TROUSERS', 0.14), ('TSHIRT', 0.10), ('HOODIE', 0.22)]),
    'M_WORK':    ("Workwear",       'MAN',   [('TSHIRT', 0.10), ('JUMPSUIT', 0.14)]),
    'M_LAYERED': ("Full Layers",    'MAN',   [('TROUSERS', 0.13), ('TANK', 0.07), ('TSHIRT', 0.12),
                                              ('JACKET', 0.15)]),
    'W_CASUAL':  ("Casual",         'WOMAN', [('TROUSERS', 0.10), ('TANK', 0.08), ('JACKET', 0.12)]),
    'W_SUMMER':  ("Summer",         'WOMAN', [('SKIRT', 0.10), ('TANK', 0.08)]),
    'W_DRESSED': ("Dress & Jacket", 'WOMAN', [('DRESS', 0.09), ('JACKET', 0.13)]),
    'W_STREET':  ("Streetwear",     'WOMAN', [('TROUSERS', 0.12), ('TSHIRT', 0.10), ('HOODIE', 0.20)]),
    'W_WORK':    ("Workwear",       'WOMAN', [('TSHIRT', 0.10), ('JUMPSUIT', 0.12)]),
}

FIGURE_LABEL = {'MAN': "Man", 'WOMAN': "Woman"}


def outfit_items(figure=None):
    """Enum items for the outfits of one figure (or all of them)."""
    return [(k, "%s (%s)" % (v[0], FIGURE_LABEL[v[1]]),
             "Build %s for a %s: %s" % (v[0], FIGURE_LABEL[v[1]].lower(),
                                        ", ".join(p for p, _ in v[2])))
            for k, v in OUTFITS.items() if figure in (None, v[1])]


OUTFIT_ITEMS = outfit_items()

PRESET_ITEMS = [(k, v[0], "Add a %s pattern set" % v[0]) for k, v in PRESETS.items()]
