"""Measure each produced garment (points of measure) straight from the 3D shell.  venv python with bpy.

usage: python measure_items.py [ID ...]   ->  3d/models/<ID>/<ID>_measures.json  +  production/measures.json
All numbers are taken on the fit avatar (186 cm male, size L equivalent) in the pose the shell was built on, half-girths
are the flat width = circumference / 2 of the shell mid-surface (so they exclude the 4-5 mm fabric thickness).
"""
import os, sys, json, math, bpy
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from mathutils import Vector
import garment_lib as gl, shell
from collection import ITEMS

ROOT = os.path.abspath(os.path.join(HERE, ".."))
ids = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else [a for a in sys.argv[1:]]
ids = ids or [k for k, v in ITEMS.items() if v["kind"] in ("tee", "hoodie", "jacket", "vest")]


def ring_len(pts):
    n = len(pts)
    return sum((pts[i] - pts[(i + 1) % n]).length for i in range(n))


def slice_girth(verts, z, tol=0.006):
    pts = [v for v in verts if abs(v.z - z) < tol]
    if len(pts) < 8:
        return 0.0
    cx = sum(p.x for p in pts) / len(pts); cy = sum(p.y for p in pts) / len(pts)
    pts.sort(key=lambda p: math.atan2(p.y - cy, p.x - cx))
    # simplified by angular bins to the outermost radius (kills inner folds)
    bins = {}
    for p in pts:
        k = int((math.atan2(p.y - cy, p.x - cx) + math.pi) / (2 * math.pi) * 180)
        r = math.hypot(p.x - cx, p.y - cy)
        if k not in bins or r > bins[k][0]:
            bins[k] = (r, p)
    ring = [bins[k][1] for k in sorted(bins)]
    return ring_len([Vector((p.x, p.y, 0)) for p in ring])


def main():
    gl.boot("MAN"); gl.pose_arms(0.7)
    gl.cd["avatar"].measure(bpy.context, force=True)
    body = shell.Body()
    out_all = {}
    for it in ids:
        mp = os.path.join(ROOT, "3d", "models", it, f"{it}_scene.blend")
        man_p = os.path.join(ROOT, "3d", "models", it, f"{it}_manifest.json")
        if not os.path.exists(mp):
            continue
        meta = json.load(open(man_p))["meta"]
        bpy.ops.wm.open_mainfile(filepath=mp)
        ob = bpy.data.objects["CD_Garment_" + it]
        mw = ob.matrix_world
        vs = [mw @ v.co for v in ob.data.vertices]
        # torso verts only (exclude arm-owned vertices)
        torso = []
        for p in vs:
            side_, s_, d_, t_, q_, ax_ = shell.arm_params(body, p)
            if not (d_ < 0.13 and t_ > 0.04):
                torso.append(p)
        z = body.z
        M = {}
        M["chest_half_cm"] = slice_girth(torso, meta["chest_z"]) / 2 * 100
        M["waist_half_cm"] = slice_girth(torso, meta["waist_z"]) / 2 * 100
        M["hem_half_cm"] = slice_girth(torso, meta["hem_z"] + 0.025) / 2 * 100
        M["body_length_cm"] = (meta["neck_z"] - meta["hem_z"]) * 100
        zs = [p.z for p in vs]
        M["total_height_cm"] = (max(zs) - min(zs)) * 100
        shL, _, _ = body.arm_axis("L"); shR, _, _ = body.arm_axis("R")
        M["shoulder_cm"] = (abs(shL.x - shR.x) + 0.03) * 100
        if meta["sleeve"] == "short":
            M["sleeve_len_cm"] = meta["upper_len"] * meta["arm_cut"] * 100
        elif meta["sleeve"] == "long":
            M["sleeve_len_cm"] = meta["chain_len"] * meta["cuff_t"] * 100
        else:
            M["sleeve_len_cm"] = 0.0
        # open boundary loops of the shell = neck, hem, sleeve openings
        import bmesh
        bm = bmesh.new(); bm.from_mesh(ob.data); bm.verts.ensure_lookup_table(); bm.edges.ensure_lookup_table()
        bm.verts.index_update()
        bm.edges.index_update()
        loops = shell.boundary_loops(bm)
        info = []
        for lp in loops:
            pts = [mw @ v.co for v in lp]
            zc = sum(p.z for p in pts) / len(pts)
            info.append((zc, ring_len(pts), pts))
        info.sort(key=lambda t: -t[0])
        if info:
            neck = info[0]
            xs = [p.x for p in neck[2]]
            M["neck_opening_cm"] = (max(xs) - min(xs)) * 100
            M["neck_girth_cm"] = neck[1] * 100
            ys = [p.y for p in neck[2]]
            M["front_drop_cm"] = (max(p.z for p in neck[2]) - min(p.z for p in neck[2])) * 100
        sl = [i for i in info[1:] if i[0] > meta["hem_z"] + 0.1]
        if sl and meta["sleeve"] != "armhole":
            M["sleeve_opening_half_cm"] = sum(i[1] for i in sl) / len(sl) / 2 * 100
        elif sl:
            M["armhole_cm"] = sum(i[1] for i in sl) / len(sl) * 100
        M["hem_girth_cm"] = info[-1][1] * 100 if info else 0.0
        M["surface_m2"] = sum(f.calc_area() for f in bm.faces) * (mw.to_scale()[0] ** 2)
        hood = bpy.data.objects.get("CD_Hood")
        if hood is not None:
            hb = bmesh.new(); hb.from_mesh(hood.data)
            M["hood_surface_m2"] = sum(f.calc_area() for f in hb.faces)
            hz = [(hood.matrix_world @ v.co) for v in hood.data.vertices]
            M["hood_height_cm"] = (max(p.z for p in hz) - min(p.z for p in hz)) * 100
            M["hood_width_cm"] = (max(p.x for p in hz) - min(p.x for p in hz)) * 100
            hb.free()
        bm.free()
        M = {k: round(v, 2) for k, v in M.items()}
        M["_basis"] = "fit avatar 186 cm male, mid-surface of the 3D shell, pose A (arms 0.7 rad); half-girth = circumference / 2"
        out_all[it] = M
        json.dump(M, open(os.path.join(ROOT, "3d", "models", it, f"{it}_measures.json"), "w"), indent=1)
        print(it, {k: v for k, v in M.items() if not k.startswith("_")})
    os.makedirs(os.path.join(ROOT, "production"), exist_ok=True)
    prev = {}
    pth = os.path.join(ROOT, "production", "measures.json")
    if os.path.exists(pth):
        prev = json.load(open(pth))
    prev.update(out_all)
    json.dump(prev, open(pth, "w"), indent=1)


main()
