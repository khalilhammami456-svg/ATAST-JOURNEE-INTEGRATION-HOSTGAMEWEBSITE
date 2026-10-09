# Headless fit audit: sew and drape every preset on both bundled avatars and
# check the result against the body's own landmarks - hems where they belong,
# sleeves ending at the wrist and not the fingertips, nothing dragging on the
# floor, nothing inside the body.
#
#   blender -b --python tests/test_fit.py [-- --figure WOMAN]
import bpy, sys, math
from mathutils import Vector

bpy.ops.preferences.addon_enable(module="clothing_design")
from clothing_design import avatar, library, build, sim

fails = []


def check(cond, msg):
    print(("  ok   " if cond else "  FAIL ") + msg)
    if not cond:
        fails.append(msg)


def fresh():
    bpy.ops.wm.read_homefile(use_empty=True)
    bpy.ops.preferences.addon_enable(module="clothing_design")


def garment_verts(ctx, g):
    dg = ctx.evaluated_depsgraph_get()
    ev = g.evaluated_get(dg)
    mw = ev.matrix_world
    return [mw @ v.co for v in ev.data.vertices]


def penetration(ctx, g, tol=0.004):
    bvh = avatar.body_bvh(ctx)
    inside = 0
    vs = garment_verts(ctx, g)
    for p in vs:
        loc, nrm, _, _ = bvh.find_nearest(p)
        if loc is not None and (p - loc).dot(nrm) < -tol:
            inside += 1
    return inside, len(vs)


def sleeve_reach(m, verts):
    """How far down the arm the garment reaches: 0 at the shoulder joint,
    1 at the wrist. Only verts within 9 cm of the arm axis count."""
    arm, farm = m["limbs"].get("arm_l"), m["limbs"].get("farm_l")
    if not arm or not farm:
        return None
    p0, p1 = Vector(arm["p0"]), Vector(farm["p1"])
    axis = p1 - p0
    L = axis.length
    u = axis / L
    ts = []
    for v in verts:
        d = v - p0
        t = d.dot(u) / L
        if -0.2 < t < 1.6 and (d - u * (t * L)).length < 0.09:
            ts.append(t)
    if len(ts) < 10:
        return None
    ts.sort()
    return ts[int(0.98 * (len(ts) - 1))]


def z_of(m, k):
    return avatar.z_of(m, k)


FIGS = ['WOMAN', 'MAN']
if "--figure" in sys.argv:
    FIGS = [sys.argv[sys.argv.index("--figure") + 1]]

# per-preset expectations: (hem z range as landmarks+offsets, sleeve t range)
def expectations(m):
    hip, waist, knee, ankle = z_of(m, "hip"), z_of(m, "waist"), z_of(m, "knee"), z_of(m, "ankle")
    shoulder = z_of(m, "shoulder")
    return {
        'TSHIRT':   dict(hem=(hip - 0.15, hip + 0.10), sleeve=(0.25, 0.80)),
        'TANK':     dict(hem=(hip - 0.15, hip + 0.12), sleeve=None),
        'SKIRT':    dict(hem=(knee - 0.08, waist - 0.10), top=(waist - 0.08, waist + 0.06)),
        'TROUSERS': dict(hem=(ankle - 0.04, ankle + 0.16), top=(hip - 0.05, waist + 0.06)),
        'JUMPSUIT': dict(hem=(ankle - 0.04, ankle + 0.18), sleeve=(0.20, 0.85)),
        'DRESS':    dict(hem=(knee - 0.18, knee + 0.18), sleeve=(0.10, 0.85)),
        'JACKET':   dict(hem=(hip - 0.16, hip + 0.12), sleeve=(0.80, 1.18)),
        'HOODIE':   dict(hem=(hip - 0.18, hip + 0.12), sleeve=(0.80, 1.18)),
    }


for fig in FIGS:
    fresh()
    ctx = bpy.context
    scn = ctx.scene
    print("== %s" % fig)
    bpy.ops.cd.import_character(figure=fig)
    m = avatar.measure(ctx, force=True)
    exp = expectations(m)
    wrist_z = Vector(m["limbs"]["farm_l"]["p1"]).z if "farm_l" in m["limbs"] else None

    for key, want in exp.items():
        fresh()
        ctx = bpy.context
        scn = ctx.scene
        bpy.ops.cd.import_character(figure=fig)
        m = avatar.measure(ctx, force=True)
        try:
            bpy.ops.cd.add_garment(preset=key, fit=0.10)
            bpy.ops.cd.sew()
        except Exception as e:
            check(False, "%s %s raised %s" % (fig, key, e))
            continue
        g = build.garment_object(ctx, create=False)
        vs = garment_verts(ctx, g)
        zmin = min(p.z for p in vs)
        zmax = max(p.z for p in vs)

        label = "%s %-9s" % (fig, key.lower())
        hem = want.get("hem")
        if hem:
            check(hem[0] <= zmin <= hem[1],
                  "%s hem at %.2f m (want %.2f..%.2f)" % (label, zmin, hem[0], hem[1]))
        top = want.get("top")
        if top:
            check(top[0] <= zmax <= top[1],
                  "%s top edge at %.2f m (want %.2f..%.2f)" % (label, zmax, top[0], top[1]))
        sl = want.get("sleeve")
        if sl:
            t = sleeve_reach(m, vs)
            check(t is not None and sl[0] <= t <= sl[1],
                  "%s sleeve reaches %.2f of the arm (want %.2f..%.2f)"
                  % (label, -1 if t is None else t, sl[0], sl[1]))
        if key not in ('TROUSERS', 'JUMPSUIT'):
            check(zmin > 0.15, "%s clear of the floor (zmin %.2f)" % (label, zmin))
        inside, n = penetration(ctx, g)
        check(inside < n * 0.02, "%s %d/%d verts inside the body" % (label, inside, n))

print("\n%d failure(s)" % len(fails))
for f in fails:
    print("  -", f)
sys.exit(1 if fails else 0)
