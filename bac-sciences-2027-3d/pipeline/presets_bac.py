"""Custom BAC SCIENCES 2027 pattern drafts for opensew-2 (GPL-3.0-or-later; uses its drafting helpers).

Each preset returns (pieces, seams) in the format opensew-2's `library` uses and is passed to
garment_lib.draft().  All lengths in metres, measured on the fitted avatar.

Oversize language (streetwear):  chest ease 0.28-0.38, dropped shoulder (sh_ext / sh_drop),
longer body (extra_len), wide sleeves into a rib cuff, rib hem narrower than the body.
"""
import math
from mathutils import Vector
from clothing_design import library as L
from clothing_design import avatar, patterns

AUTO_FLIP_CAPS = False
_seg = L._seg
_bez = patterns.bezier
_curve_len = L._curve_len
_armhole_len = L._armhole_len


def _draft(m, fit, sh_ext=1.0, extra_drop=0.0, extra_sh_drop=0.0, sleeveless=False, ring_k=1.65):
    """library._draft_top for oversized cuts.  The stock armhole is sized from the BICEPS girth x 1.35, which
    is shorter than the shoulder (deltoid) girth - the sleeve ring then cannot encircle the shoulder, slides
    down the arm and leaves the top of the shoulder bare.  Here the armhole ring is at least ring_k x the
    biceps girth; the extra length is bought by a deeper armhole and a wider scye (sleeve cap is
    re-solved against it by L._sleeve)."""
    d = L._draft_top(m, fit, sleeveless=sleeveless, sh_ext=sh_ext)
    d["sh_drop"] += extra_sh_drop
    d["arm_d"] += extra_drop
    need = max(d["armhole"], d["biceps"] * ring_k)        # ring_k x biceps girth (stock uses 1.35)
    half, sh_x, sh_drop = d["half"], d["sh_x"], d["sh_drop"]
    lo = d["arm_d"]
    arm_d = L._solve(lambda t: 2.0 * _armhole_len(d["scye_x"], sh_x, t, sh_drop), need, lo, lo + 0.14)
    scye = L._solve(lambda e: 2.0 * _armhole_len(d["scye_x"] + e, sh_x, arm_d, sh_drop), need, 0.0, 0.10)
    d["arm_d"] = arm_d
    d["scye_x"] = d["scye_x"] + scye
    d["armhole"] = 2.0 * _armhole_len(d["scye_x"], sh_x, arm_d, sh_drop)
    d["ring_need"] = need
    return d


def _sleeve_h(cap_h, sl, arm_total, apex_t=-0.02):
    """Limb-anchor fraction that puts the sleeve's cap apex at the arm root (apex_t along the arm) so
    the cap starts next to the armhole instead of ~25 cm above it (opensew-2's stock placement)."""
    if arm_total <= 1e-6:
        return 0.22
    return apex_t + 0.5 * (sl + cap_h) / arm_total


def _wrist_radius(m):
    farm = m.get("limbs", {}).get("farm_l")
    return avatar.limb_radius_at(farm, 1.0) if farm else 0.03


def _body_len(m, length_to, extra_len):
    z, g, _ = L._measurements(m)
    f = L._fig(m)
    return max(z["shoulder"] + L.SHELF - z[length_to], 0.12) + 0.03 + f["top_extra"] + extra_len


def _side_poly(half, hem_half, Lb, arm_d, rib_h, taper_h=0.12):
    """Side seam (hem -> underarm): vertical over the rib band, then flares out to the chest width."""
    pts = [(hem_half, -Lb), (hem_half, -(Lb - rib_h)),
           (hem_half + (half - hem_half) * 0.75, -(Lb - rib_h - taper_h)), (half, -(Lb - rib_h - taper_h - 0.10))]
    pts = [p for p in pts if p[1] <= -arm_d - 0.02]          # never above the armpit
    pts.append((half, -arm_d))
    return [Vector(p) for p in pts]


def _mirror_rev(pts):
    return [Vector((-p.x, p.y)) for p in reversed(pts)]


def _sleeve_cuffed(d, m, length, cuff_h, cuff_ratio, sleeve_flare=1.0, width_ease=1.10):
    """Set-in sleeve that tapers into a straight rib-cuff section (cuff_h tall) at the wrist."""
    segs, cw, cap_h = L._sleeve(d, 0.0, length, width_ease=width_ease)
    cw *= sleeve_flare
    r_w = _wrist_radius(m)
    hw = max(2.0 * math.pi * (r_w + 0.012) * cuff_ratio, 0.10)
    hw = min(hw, cw * 0.9)
    knee = -(length - cuff_h)
    under_front = _seg("under_front", [(-cw * 0.5, 0.0), (-hw * 0.5 - (cw - hw) * 0.10, knee * 0.55), (-hw * 0.5, knee), (-hw * 0.5, -length)])
    hem = _seg("hem", [(-hw * 0.5, -length), (hw * 0.5, -length)])
    under_back = _seg("under_back", [(hw * 0.5, -length), (hw * 0.5, knee), (hw * 0.5 + (cw - hw) * 0.10, knee * 0.55), (cw * 0.5, 0.0)])
    rest = [s for s in segs if s[0] in ("cap_back", "cap_front")]
    return [under_front, hem, under_back] + rest, cw, cap_h, hw


def _hood_piece_h(m, hood_h_scale):
    ng = avatar.neck_girth(m)
    return max(0.14, ng * 0.62) * hood_h_scale


def preset_hoodie_zip(m, fit=0.32, extra_len=0.10, sh_ext=1.14, extra_drop=0.05, extra_sh_drop=0.03,
                      cuff_h=0.075, cuff_ratio=1.02, rib_h=0.085, hem_ease=0.06, hood_h_scale=1.25,
                      sleeve_flare=1.0, length_to="hip", sleeve_total=None, sleeve_k=0.90, ring_k=1.65):
    """Oversized zip hoodie: two front halves sewn on the centre-front (zip line), back, two wide
    dropped-shoulder sleeves into rib cuffs, rib hem, two-panel hood."""
    z, g, _ = L._measurements(m)
    d = _draft(m, fit, sh_ext=sh_ext, extra_drop=extra_drop, extra_sh_drop=extra_sh_drop, ring_k=ring_k)
    half, scye_x, sh_x, sh_drop, arm_d = d["half"], d["scye_x"], d["sh_x"], d["sh_drop"], d["arm_d"]
    Lb = _body_len(m, length_to, extra_len)
    hip_half = g["hip"] * 0.5 * 0.5
    hem_half = max(hip_half * (1.0 + hem_ease), half * 0.80)
    hem_half = min(hem_half, half)
    nh = d["neck_half"] * 1.12
    dfh, dbh = d["df"] * 1.15, d["db"] * 1.3
    side = _side_poly(scye_x, hem_half, Lb, arm_d, rib_h)
    arm_pts = _bez((scye_x, -arm_d), (scye_x, -arm_d * 0.45), (sh_x + 0.035, -sh_drop - 0.02), (sh_x, -sh_drop), 12)

    # --- back (single panel, neck split in two for the hood)
    neck_b = _bez((nh, 0.0), (nh * 0.55, -dbh), (-nh * 0.55, -dbh), (-nh, 0.0), 14)
    hb = len(neck_b) // 2
    back = [_seg("hem", [(-hem_half, -Lb), (hem_half, -Lb)]),
            ("side_L", side), ("arm_L", arm_pts),
            _seg("shoulder_L", [(sh_x, -sh_drop), (nh, 0.0)]),
            ("neck_L", neck_b[:hb + 1]), ("neck_R", neck_b[hb:]),
            _seg("shoulder_R", [(-nh, 0.0), (-sh_x, -sh_drop)]),
            ("arm_R", _mirror_rev(arm_pts)), ("side_R", _mirror_rev(side))]

    # --- front halves (zip line = cf)
    neck_f = _bez((nh, 0.0), (nh * 0.62, -dfh * 0.85), (nh * 0.22, -dfh), (0.0, -dfh), 10)
    left = [_seg("hem", [(0.0, -Lb), (hem_half, -Lb)]),
            ("side_L", side), ("arm_L", arm_pts),
            _seg("shoulder_L", [(sh_x, -sh_drop), (nh, 0.0)]),
            ("neck_L", neck_f),
            _seg("cf_L", [(0.0, -dfh), (0.0, -Lb)])]
    right = []
    for name, pts in reversed(left):
        right.append((name.replace("_L", "_R"), [Vector((-p.x, p.y)) for p in reversed(pts)]))
    # the hem of the right half runs (-hem_half..0) after mirroring; segment order follows outline

    # --- sleeves
    arm_total = sum(m.get("limbs", {}).get(k, {}).get("len", 0.0) for k in ("arm_l", "farm_l"))
    sl = sleeve_total if sleeve_total is not None else max(0.20, arm_total * sleeve_k)
    if cuff_h > 0.0:
        sleeve, cw, cap_h, hw = _sleeve_cuffed(d, m, sl, cuff_h, cuff_ratio, sleeve_flare)
    else:                                   # stock set-in sleeve (known to stitch reliably)
        sleeve, cw, cap_h = L._sleeve(d, fit, sl)
        hw = 0.0
    sh = _sleeve_h(cap_h, sl, arm_total)

    # --- hood
    nl_f = _curve_len(neck_f)
    nl_b = _curve_len(neck_b) * 0.5
    hood_f, hood_b = max(0.03, nl_f / 1.005), max(0.03, nl_b / 1.005)
    hood_h = _hood_piece_h(m, hood_h_scale)
    body_h = (z["shoulder"] + L.SHELF - Lb * 0.5 - m["zmin"]) / m["height"]
    xs = [p.x for _, pts in left for p in pts]
    from clothing_design import build as _build
    # each half is centred on its own bbox, so spin it to the side until its centre-front edge meets x=0
    off = _build.ArcMap(m, z["chest"], 0.0, 0.04).theta_of(0.5 * (max(xs) - min(xs)))
    head_h = (z["neck"] + avatar.neck_girth(m) * 0.30 - m["zmin"]) / m["height"]
    pieces = [
        dict(name="Front_L", segs=left, anchor='TORSO_FRONT', height=body_h, ease=0.040, spin=off),
        dict(name="Front_R", segs=right, anchor='TORSO_FRONT', height=body_h, ease=0.040, spin=-off),
        dict(name="Back", segs=back, anchor='TORSO_BACK', height=body_h, ease=0.040),
        dict(name="Sleeve_L", segs=sleeve, anchor='ARM_L', height=sh, ease=0.036, taper=0.5 if cuff_h > 0 else 0.0),
        dict(name="Sleeve_R", segs=sleeve, anchor='ARM_R', height=sh, ease=0.036, taper=0.5 if cuff_h > 0 else 0.0),
        dict(name="Hood_L", segs=L._hood(hood_f, hood_b, hood_h, False), anchor='TORSO_LEFT',
             height=head_h, ease=0.06, wrap=0.8, spin=0.62),
        dict(name="Hood_R", segs=L._hood(hood_f, hood_b, hood_h, True), anchor='TORSO_RIGHT',
             height=head_h, ease=0.06, wrap=0.8, spin=-0.62),
    ]
    seams = [
        ("Front_L", "cf_L", "Front_R", "cf_R"),
        ("Front_L", "side_L", "Back", "side_L", False),
        ("Front_R", "side_R", "Back", "side_R", False),
        ("Front_L", "shoulder_L", "Back", "shoulder_L", False),
        ("Front_R", "shoulder_R", "Back", "shoulder_R", False),
        ("Sleeve_L", "cap_front", "Front_L", "arm_L") if AUTO_FLIP_CAPS else ("Sleeve_L", "cap_front", "Front_L", "arm_L", True),
        ("Sleeve_L", "cap_back", "Back", "arm_L") if AUTO_FLIP_CAPS else ("Sleeve_L", "cap_back", "Back", "arm_L", False),
        ("Sleeve_L", "under_front", "Sleeve_L", "under_back", True),
        ("Sleeve_R", "cap_front", "Front_R", "arm_R") if AUTO_FLIP_CAPS else ("Sleeve_R", "cap_front", "Front_R", "arm_R", False),
        ("Sleeve_R", "cap_back", "Back", "arm_R") if AUTO_FLIP_CAPS else ("Sleeve_R", "cap_back", "Back", "arm_R", True),
        ("Sleeve_R", "under_front", "Sleeve_R", "under_back", True),
        ("Hood_L", "crown", "Hood_R", "crown"),
        ("Hood_L", "neck_front", "Front_L", "neck_L"),
        ("Hood_R", "neck_front", "Front_R", "neck_R"),
        ("Hood_L", "neck_back", "Back", "neck_L"),
        ("Hood_R", "neck_back", "Back", "neck_R"),
    ]
    info = dict(Lb=Lb, hem_half=hem_half, half=half, rib_h=rib_h, cuff_h=cuff_h, sleeve_len=sl, cuff_w=hw,
                cw=cw, arm_d=arm_d)
    return pieces, seams


# ====================================================================== other garments

def _neck_front_crew(nh, df):
    return _bez((nh, 0.0), (nh * 0.55, -df), (-nh * 0.55, -df), (-nh, 0.0), 14)


def preset_tee_boxy(m, fit=0.30, extra_len=0.06, sleeve_len=0.26, sh_ext=1.12, extra_drop=0.03, extra_sh_drop=0.02,
                    sleeve_flare=1.15, hem_ease=0.10, neck_scale=1.05):
    """Boxy, dropped-shoulder crew tee: straight sides, wide short sleeve with a clean hem."""
    z, g, _ = L._measurements(m)
    d = _draft(m, fit, sh_ext=sh_ext, extra_drop=extra_drop, extra_sh_drop=extra_sh_drop)
    half, scye_x, sh_x, sh_drop, arm_d = d["half"], d["scye_x"], d["sh_x"], d["sh_drop"], d["arm_d"]
    Lb = _body_len(m, "hip", extra_len)
    hem_half = max(half, g["hip"] * 0.25 * (1 + hem_ease))
    nh = d["neck_half"] * neck_scale
    side = [Vector((hem_half, -Lb)), Vector((scye_x, -arm_d))]
    arm_pts = _bez((scye_x, -arm_d), (scye_x, -arm_d * 0.45), (sh_x + 0.035, -sh_drop - 0.02), (sh_x, -sh_drop), 12)

    def panel(df):
        return [_seg("hem", [(-hem_half, -Lb), (hem_half, -Lb)]), ("side_L", side), ("arm_L", arm_pts),
                _seg("shoulder_L", [(sh_x, -sh_drop), (nh, 0.0)]), ("neck", _neck_front_crew(nh, df)),
                _seg("shoulder_R", [(-nh, 0.0), (-sh_x, -sh_drop)]), ("arm_R", _mirror_rev(arm_pts)),
                ("side_R", _mirror_rev(side))]
    front, back = panel(d["df"] * 1.1), panel(d["db"])
    sleeve, cw, cap_h = L._sleeve(d, fit, sleeve_len, width_ease=1.18)
    arm_total = sum(m.get("limbs", {}).get(k, {}).get("len", 0.0) for k in ("arm_l", "farm_l"))
    sh = _sleeve_h(cap_h, sleeve_len, arm_total)
    body_h = (z["shoulder"] + L.SHELF - Lb * 0.5 - m["zmin"]) / m["height"]
    pieces = [dict(name="Front", segs=front, anchor='TORSO_FRONT', height=body_h, ease=0.028),
              dict(name="Back", segs=back, anchor='TORSO_BACK', height=body_h, ease=0.028),
              dict(name="Sleeve_L", segs=sleeve, anchor='ARM_L', height=sh, ease=0.026),
              dict(name="Sleeve_R", segs=sleeve, anchor='ARM_R', height=sh, ease=0.026)]
    seams = [("Front", "side_L", "Back", "side_L", False), ("Front", "side_R", "Back", "side_R", False),
             ("Front", "shoulder_L", "Back", "shoulder_L", False), ("Front", "shoulder_R", "Back", "shoulder_R", False),
             ("Sleeve_L", "cap_front", "Front", "arm_L", True), ("Sleeve_L", "cap_back", "Back", "arm_L", False),
             ("Sleeve_L", "under_front", "Sleeve_L", "under_back", True),
             ("Sleeve_R", "cap_front", "Front", "arm_R", False), ("Sleeve_R", "cap_back", "Back", "arm_R", True),
             ("Sleeve_R", "under_front", "Sleeve_R", "under_back", True)]
    return pieces, seams


def preset_vest(m, fit=0.24, extra_len=0.02, collar=True, collar_h=0.06, length_to="hip", armhole_up=0.0, neck_scale=1.0,
                v_depth=0.0):
    """Sleeveless zip vest/gilet: two front halves on a centre-front zip line + back; optional stand collar."""
    z, g, _ = L._measurements(m)
    d = L._draft_top(m, fit, sleeveless=True, sh_ext=1.0)
    half, scye_x, sh_x, sh_drop, arm_d = d["half"], d["scye_x"], d["sh_x"], d["sh_drop"], d["arm_d"]
    sh_x = min(sh_x, d["neck_half"] + 0.075)           # narrow gilet shoulder
    Lb = _body_len(m, length_to, extra_len)
    hem_half = max(half, g["hip"] * 0.25 * 1.06)
    nh = d["neck_half"] * neck_scale
    dfh, dbh = d["df"] * 1.7 + v_depth, d["db"] * 1.2
    arm_pts = _bez((scye_x, -arm_d), (scye_x, -arm_d * 0.45), (sh_x + 0.02, -sh_drop - 0.02), (sh_x, -sh_drop), 12)
    side = [Vector((hem_half, -Lb)), Vector((scye_x, -arm_d))]
    neck_b = _bez((nh, 0.0), (nh * 0.55, -dbh), (-nh * 0.55, -dbh), (-nh, 0.0), 14)
    back = [_seg("hem", [(-hem_half, -Lb), (hem_half, -Lb)]), ("side_L", side), ("arm_L", arm_pts),
            _seg("shoulder_L", [(sh_x, -sh_drop), (nh, 0.0)]), ("neck", neck_b),
            _seg("shoulder_R", [(-nh, 0.0), (-sh_x, -sh_drop)]), ("arm_R", _mirror_rev(arm_pts)), ("side_R", _mirror_rev(side))]
    neck_f = _bez((nh, 0.0), (nh * 0.62, -dfh * 0.85), (nh * 0.22, -dfh), (0.0, -dfh), 10)
    left = [_seg("hem", [(0.0, -Lb), (hem_half, -Lb)]), ("side_L", side), ("arm_L", arm_pts),
            _seg("shoulder_L", [(sh_x, -sh_drop), (nh, 0.0)]), ("neck_L", neck_f), _seg("cf_L", [(0.0, -dfh), (0.0, -Lb)])]
    right = [(n.replace("_L", "_R"), [Vector((-p.x, p.y)) for p in reversed(pts)]) for n, pts in reversed(left)]
    xs = [p.x for _, pts in left for p in pts]
    from clothing_design import build as _build
    off = _build.ArcMap(m, z["chest"], 0.0, 0.04).theta_of(0.5 * (max(xs) - min(xs)))
    body_h = (z["shoulder"] + L.SHELF - Lb * 0.5 - m["zmin"]) / m["height"]
    pieces = [dict(name="Front_L", segs=left, anchor='TORSO_FRONT', height=body_h, ease=0.030, spin=off),
              dict(name="Front_R", segs=right, anchor='TORSO_FRONT', height=body_h, ease=0.030, spin=-off),
              dict(name="Back", segs=back, anchor='TORSO_BACK', height=body_h, ease=0.030)]
    seams = [("Front_L", "cf_L", "Front_R", "cf_R"),
             ("Front_L", "side_L", "Back", "side_L", False), ("Front_R", "side_R", "Back", "side_R", False),
             ("Front_L", "shoulder_L", "Back", "shoulder_L", False), ("Front_R", "shoulder_R", "Back", "shoulder_R", False)]
    return pieces, seams
