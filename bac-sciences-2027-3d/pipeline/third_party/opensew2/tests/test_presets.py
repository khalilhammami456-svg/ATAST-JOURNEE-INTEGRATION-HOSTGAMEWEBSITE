# Headless check of the bundled avatars and every preset on both figures.
#
#   blender -b --python tests/test_presets.py [-- --drape]
#
# With --drape, also sews and drapes a T-shirt on each figure and reports the
# open-stitch count and the penetration after settling.
import bpy, sys, math, time
from mathutils import Vector

bpy.ops.preferences.addon_enable(module="clothing_design")
from clothing_design import avatar, library, build, sim, patterns


def seg_length(ob, seg):
    idx = patterns.segment_verts(ob, seg)
    co = [ob.matrix_world @ ob.data.vertices[i].co for i in idx]
    return sum((b - a).length for a, b in zip(co, co[1:]))


def penetration(ctx, g, tol=0.004):
    """Count garment verts sitting inside the body after the drape."""
    bvh = avatar.body_bvh(ctx)
    dg = ctx.evaluated_depsgraph_get()
    ev = g.evaluated_get(dg)
    mw = ev.matrix_world
    inside = 0
    for v in ev.data.vertices:
        p = mw @ v.co
        loc, nrm, _, _ = bvh.find_nearest(p)
        if loc is not None and (p - loc).dot(nrm) < -tol:
            inside += 1
    return inside, len(ev.data.vertices)

DRAPE = "--drape" in sys.argv
fails = []


def check(cond, msg):
    print(("  ok   " if cond else "  FAIL ") + msg)
    if not cond:
        fails.append(msg)


def fresh():
    bpy.ops.wm.read_homefile(use_empty=True)
    bpy.ops.preferences.addon_enable(module="clothing_design")


def arm_angle(m):
    lp = m["limbs"].get("arm_l")
    d = (Vector(lp["p1"]) - Vector(lp["p0"])).normalized()
    return math.degrees(math.acos(max(-1.0, min(1.0, -d.z))))


for fig in ('WOMAN', 'MAN'):
    fresh()
    ctx = bpy.context
    scn = ctx.scene
    print("== %s" % fig)
    bpy.ops.cd.import_character(figure=fig)
    body = scn.cd.avatar
    check(body is not None and body.get("cd_figure") == fig, "imported %s body tagged" % fig)
    m = avatar.measure(ctx, body, force=True)
    g = {k: avatar.girth_at(m, avatar.z_of(m, k)) for k in ("chest", "waist", "hip")}
    ng = avatar.neck_girth(m)
    print("  height %.2f  chest %.0f waist %.0f hip %.0f neck %.0f cm  arms %.0f deg  score %+.2f"
          % (m["height"], g["chest"] * 100, g["waist"] * 100, g["hip"] * 100, ng * 100,
             arm_angle(m), avatar.figure_score(m)))
    check(0.28 < ng < 0.45, "neck girth plausible (%.3f)" % ng)
    check(m["figure_auto"] == fig, "figure guessed %s" % m["figure_auto"])
    check(arm_angle(m) > 45, "arms held clear of the body")
    zmin = min((body.matrix_world @ v.co).z for v in body.data.vertices)
    check(abs(zmin) < 0.05, "feet on the floor (zmin %.3f)" % zmin)
    scn.cd.figure = 'AUTO'
    check(avatar.figure(ctx) == fig, "effective figure %s" % avatar.figure(ctx))

    items = [i[0] for i in library.outfit_items(fig)]
    check(all(k.startswith(fig[0]) for k in items) and items, "outfits for %s: %s" % (fig, items))

    for key, (label, fn) in library.PRESETS.items():
        t = time.time()
        try:
            bpy.ops.cd.add_garment(preset=key, fit=0.10)
        except Exception as e:
            check(False, "%s raised %s" % (label, e))
            continue
        gname = scn.cd.garment_name
        pieces = [o for o in scn.objects if o.cd.is_pattern and o.cd.garment == gname]
        gob = next((o for o in scn.objects if o.cd.is_garment and o.name == gname), None) \
            or build.garment_object(ctx, create=False)
        nv = len(gob.data.vertices) if gob and gob.data else 0
        seams = [s for s in scn.cd.seams if s.obj_a and s.obj_a.cd.garment == gname]
        check(pieces and nv > 0, "%-11s %d pieces, %d seams, %d verts  (%.1fs)"
              % (label, len(pieces), len(seams), nv, time.time() - t))
        # the two halves of every seam should measure within 4 % of each other,
        # plus half an edge: a segment's vert chain stops short of the shared
        # corner vertex at one end, so short edges read a little under length
        tol_abs = 0.5 * scn.cd.resolution
        for s in seams:
            try:
                la = seg_length(s.obj_a, s.seg_a)
                lb = seg_length(s.obj_b, s.seg_b)
            except Exception:
                la = lb = None
            if la and lb and max(la, lb) > 0.03:
                r = abs(la - lb) / max(la, lb)
                if abs(la - lb) > 0.04 * max(la, lb) + tol_abs:
                    check(False, "    seam %s lengths differ %.0f%% (%.3f vs %.3f)"
                          % (s.name, r * 100, la, lb))

    if DRAPE:
        for key in ('TSHIRT', 'TROUSERS'):
            fresh(); ctx = bpy.context; scn = ctx.scene
            bpy.ops.cd.import_character(figure=fig)
            bpy.ops.cd.add_garment(preset=key, fit=0.10)
            g = build.garment_object(ctx, create=False)
            t = time.time()
            bpy.ops.cd.sew()
            merged, _ = sim.close_seams(ctx, g)   # anything still open after the settle
            inside, n = penetration(ctx, g)
            print("  drape %-9s %3.0fs  %d verts, %d late welds, %d inside the body"
                  % (key.lower(), time.time() - t, n, merged, inside))
            check(inside < n * 0.02, "%s on %s: %.1f%% of verts inside the body"
                  % (key.lower(), fig.lower(), 100.0 * inside / max(1, n)))

print("\n%d failure(s)" % len(fails))
for f in fails:
    print("  -", f)
sys.exit(1 if fails else 0)
