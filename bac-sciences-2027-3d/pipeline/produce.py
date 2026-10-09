"""Produce one collection item as a render-ready Blender scene.

usage (venv python with bpy):  ITEM=H1 [COLORWAY=rose] python produce.py
steps: pose avatar -> garment shell (+UV, cloth settle) -> hood -> trims (zip / cords / snaps) -> mannequin + trousers
       -> materials from the texture atlas -> save  3d/models/<ITEM>/<ITEM>_<colorway>.blend  (+ manifests)
Textures are composed separately (designs.py, system python) by build_textures.py.
"""
import os, sys, json, math, bpy
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import garment_lib as gl, shell, materials, trims
from mathutils import Vector

E = os.environ.get
ROOT = os.path.abspath(os.path.join(HERE, ".."))
ITEM = E("ITEM", "H1")

# ---------------------------------------------------------------- per-item shell configs
CFG = {
    "H1": dict(kind="hoodie", sleeve="long", hem_z=0.86, hood=True, zip=True, cords=True, pocket=False, collar=0.035,
               e_torso=(0.045, 0.05, 0.06, 0.065, 0.03), e_arm=(0.04, 0.05, 0.05, 0.035, 0.014), rib_h=0.09, cuff_h=0.075),
    "H2": dict(kind="hoodie", sleeve="long", hem_z=0.86, hood=True, zip=False, cords=True, pocket=True, collar=0.035,
               e_torso=(0.045, 0.05, 0.06, 0.065, 0.03), e_arm=(0.04, 0.05, 0.05, 0.035, 0.014), rib_h=0.09, cuff_h=0.075),
    "H3": dict(trousers=(0.34, 0.31, 0.27), kind="hoodie", sleeve="long", hem_z=0.88, hood=True, zip=True, cords=True, pocket=False, collar=0.04,
               e_torso=(0.035, 0.04, 0.048, 0.052, 0.025), e_arm=(0.03, 0.04, 0.042, 0.03, 0.012), rib_h=0.08, cuff_h=0.07),
    "T1": dict(trousers=(0.34, 0.31, 0.27), settle=0, kind="tee", sleeve="short", arm_cut=0.62, hem_z=0.90, hood=False, zip=False, cords=False, collar=0.022,
               smooth=18, e_torso=(0.05, 0.055, 0.06, 0.07, 0.03), e_arm=(0.04, 0.05, 0.05, 0.05, 0.05), rib_h=0.0, cuff_h=0.0),
    "T2": dict(settle=0, kind="tee", sleeve="short", arm_cut=0.62, hem_z=0.90, hood=False, zip=False, cords=False, collar=0.022,
               smooth=18, e_torso=(0.055, 0.06, 0.065, 0.075, 0.03), e_arm=(0.045, 0.055, 0.055, 0.055, 0.055), rib_h=0.0, cuff_h=0.0),
    "T3": dict(settle=0, kind="tee", sleeve="short", arm_cut=0.62, hem_z=0.90, hood=False, zip=False, cords=False, collar=0.022,
               smooth=18, e_torso=(0.045, 0.05, 0.055, 0.065, 0.028), e_arm=(0.035, 0.045, 0.045, 0.045, 0.045), rib_h=0.0, cuff_h=0.0),
    "J1": dict(trousers=(0.34, 0.31, 0.27), kind="jacket", sleeve="long", hem_z=0.90, hood=False, zip=False, snaps=True, collar=0.045,
               e_torso=(0.04, 0.045, 0.052, 0.055, 0.028), e_arm=(0.035, 0.045, 0.045, 0.032, 0.013), rib_h=0.085, cuff_h=0.08),
    "J2": dict(settle=0, kind="jacket", sleeve="long", hem_z=0.90, hood=False, zip=False, snaps=True, collar=0.05,
               e_torso=(0.04, 0.046, 0.055, 0.058, 0.03), e_arm=(0.035, 0.045, 0.045, 0.035, 0.02), rib_h=0.0, cuff_h=0.0),
    "V1": dict(binding=(0.93, 0.91, 0.86), trousers=(0.34, 0.31, 0.27), kind="vest", sleeve="armhole", hem_z=0.92, hood=False, zip=False, snaps=True, collar=0.04,
               e_torso=(0.04, 0.045, 0.052, 0.055, 0.028), e_arm=(0.03, 0.03, 0.03, 0.03, 0.03), rib_h=0.07, cuff_h=0.0),
    "V2": dict(binding=(0.06, 0.08, 0.14), settle=0, kind="vest", sleeve="armhole", hem_z=0.93, hood=False, zip=True, snaps=False, collar=0.06,
               e_torso=(0.05, 0.058, 0.066, 0.07, 0.03), e_arm=(0.04, 0.04, 0.04, 0.04, 0.04), rib_h=0.0, cuff_h=0.0),
}


MICRO = {"tee": "jersey", "hoodie": "fleece", "jacket": "twill", "vest": "twill"}
MICRO_ITEM = {"J2": None, "V2": None, "H3": "fleece"}
WRINKLE = {"tee": (0.085, 0.0085), "hoodie": (0.11, 0.005), "jacket": (0.10, 0.0055), "vest": (0.10, 0.0055)}


def build_shell(cfg):
    ctx = bpy.context
    gl.boot(E("FIG", "MAN"))
    gl.pose_arms(float(E("ARMS", "0.7")))
    gl.cd["avatar"].measure(ctx, force=True)
    body = shell.Body()
    bm = shell.extract(body, kind=cfg["kind"], sleeve=cfg["sleeve"], cuff_t=float(cfg.get("cuff_t", 0.97)),
                       arm_cut_t=float(cfg.get("arm_cut", 0.5)), neck_r=0.0, armhole_d=float(cfg.get("armhole_d", 0.03)))
    loops = shell.boundary_loops(bm)
    hip = min(loops, key=lambda l: sum(v.co.z for v in l) / len(l))
    neck = max(loops, key=lambda l: sum(v.co.z for v in l) / len(l))
    cuffs = [l for l in loops if l is not hip and l is not neck]
    hem_z = cfg["hem_z"]
    shell.regularize_ring(hip, iters=6)
    rings = shell.extrude_hem(bm, hip, hem_z, steps=8, flare=cfg.get("flare", 0.0), keep_outside=bool(cfg.get("hem_keep", cfg["kind"] != "hoodie")))
    shell.regularize_ring(rings[-1], planar_z=hem_z, iters=14)
    tags = {"hem": set(), "collar": set(), "cuff": set()}
    rib_h = cfg.get("rib_h", 0.0)
    if rib_h > 0:
        for k, rg in enumerate(rings):
            if (k / (len(rings) - 1)) >= (1 - rib_h / (rings[0][0].co.z - hem_z + 1e-9)):
                tags["hem"].update(rg)
    if cfg.get("neck_fit", cfg["kind"] != "hoodie"):
        shell.regularize_ring(neck, iters=2)
        shell.fit_ring3(neck, harm_r=int(cfg.get("neck_hr", 4)), harm_z=int(cfg.get("neck_hz", 2)))
    else:
        shell.regularize_ring(neck, iters=4)
    crings = shell.extrude_loop(bm, neck, Vector((0, 0, 1)), cfg.get("collar", 0.03), steps=3, scale=lambda t: 1.0 - 0.06 * t)
    shell.regularize_ring(crings[-1], planar_z=sum(v.co.z for v in crings[-1]) / len(crings[-1]), iters=10)
    for rg in crings:
        tags["collar"].update(rg)
    pin_objs = set(crings[-1]) | set(crings[-2]) | set(neck)
    for cl in cuffs:
        shell.regularize_ring(cl, iters=2 if cfg["sleeve"] == "armhole" else 4)
        if cfg["sleeve"] == "armhole":
            shell.fit_ring_pca(cl, harm_r=int(cfg.get("arm_hr", 4)), harm_n=2)
    sh_, el_, wr_ = body.arm_axis("L")
    Lchain = (el_ - sh_).length + (wr_ - el_).length
    Lupper = (el_ - sh_).length
    z = body.z
    et = cfg["e_torso"]
    ease_torso = [(hem_z, et[0]), (z["hip"], et[1]), (z["waist"], et[2]), (z["chest"], et[3]), (z["shoulder"], et[4])]
    ea = cfg["e_arm"]
    ease_arm = [(0.0, ea[0]), (0.35, ea[1]), (0.7, ea[2]), (0.88, ea[3]), (1.0, ea[4])]
    shell.smooth_verts(bm, iters=int(cfg.get("smooth", 10)), factor=0.5)
    shell.ease_offset(bm, body, ease_torso, ease_arm)
    cuff_h = cfg.get("cuff_h", 0.0)
    if cuff_h > 0 and cfg["sleeve"] == "long":
        for v in bm.verts:
            side_, s_, d_, t_, q_, ax_ = shell.arm_params(body, v.co)
            if d_ < 0.12 and s_ >= Lchain * float(cfg.get("cuff_t", 0.97)) - cuff_h:
                tags["cuff"].add(v)
    if cfg["sleeve"] == "armhole" and cfg.get("rib_arm", True) and not cfg.get("binding"):
        for cl in cuffs:
            for v in cl:
                tags["cuff"].add(v)
                for e in v.link_edges:
                    tags["cuff"].add(e.other_vert(v))
    bm.verts.index_update()
    tags = {k: {v.index for v in s} for k, s in tags.items()}
    pin_ids = {v.index for v in pin_objs}
    cuff_ring_ids = [[v.index for v in cl] for cl in cuffs]
    ob = shell.make_object(bm, "CD_Garment_" + ITEM)
    man = shell.build_uv(ob, body, vtags=tags)
    man["meta"] = dict(item=ITEM, kind=cfg["kind"], sleeve=cfg["sleeve"], hem_z=hem_z, neck_z=sum(v.co.z for v in neck) / len(neck),
                       shoulder_z=z["shoulder"], chest_z=z["chest"], waist_z=z["waist"], chain_len=Lchain,
                       cuff_t=float(cfg.get("cuff_t", 0.97)), rib_h=rib_h, cuff_h=cuff_h, collar_h=cfg.get("collar", 0.03),
                       upper_len=Lupper, arm_cut=float(cfg.get("arm_cut", 0.5)), snaps=bool(cfg.get("snaps")), zip=bool(cfg.get("zip")))
    ob["gl_atlas"] = json.dumps(man)
    # cloth settle (soft pin ramps keep the oversized volume)
    pinw = {}
    def ss(x):
        x = max(0.0, min(1.0, x)); return x * x * (3 - 2 * x)
    zc, zw = float(cfg.get("pin_z1", 1.30)), float(cfg.get("pin_z0", 1.12))
    for v in ob.data.vertices:
        side_, s_, d_, t_, q_, ax_ = shell.arm_params(body, v.co)
        if d_ < 0.12 and t_ > 0.04:
            w = 1.0 - ss((t_ - 0.22) / (0.62 - 0.22))
        else:
            w = ss((v.co.z - zw) / (zc - zw))
        pinw[v.index] = w
    for i in pin_ids:
        pinw[i] = 1.0
    if int(cfg.get("settle", 70)) > 0:
        shell.settle(ob, body.ob, pinw, frames=int(cfg.get("settle", 70)), bending=float(cfg.get("bend", 12)),
                     compression=25, tension=30, thickness=0.004)
    hood = None
    if cfg.get("hood"):
        ring_world = [ob.data.vertices[v.index].co.copy() for v in crings[-1]]
        hood = shell.make_hood_down(ob, ring_world, body.ob, frames=36)
    ob["_cuff_rings"] = json.dumps(cuff_ring_ids)
    return body, ob, hood, man, crings


def ray_path(ob, zs, x=0.0, y0=-1.0, offset=0.0):
    """Cast rays along +Y at (x, z) onto object `ob` (evaluated, with modifiers); return (points, normals)."""
    ctx = bpy.context
    dg = ctx.evaluated_depsgraph_get()
    pts, nrm = [], []
    for z in zs:
        ok, loc, n, idx, hit, mat = ctx.scene.ray_cast(dg, Vector((x, y0, z)), Vector((0, 1, 0)))
        if ok and hit.name == ob.name:
            pts.append(loc + n * offset)
            nrm.append(n)
    return pts, nrm


def add_modifiers(ob, thick=0.005, subdiv=(1, 2), offset=1.0, wrinkle=None):
    """Displace (soft fabric undulation) -> solidify -> subsurf.  wrinkle=(noise size m, strength m)."""
    if wrinkle and not any(m.type == "DISPLACE" for m in ob.modifiers):
        tx = bpy.data.textures.new("wr_" + ob.name, 'CLOUDS')
        tx.noise_scale = wrinkle[0]; tx.noise_depth = 2; tx.intensity = 1.0; tx.contrast = 1.4
        dm = ob.modifiers.new("wrinkle", 'DISPLACE')
        dm.texture = tx; dm.direction = 'NORMAL'; dm.strength = wrinkle[1]; dm.mid_level = 0.5; dm.texture_coords = 'LOCAL'
    if not any(m.type == "SOLIDIFY" for m in ob.modifiers):
        sol = ob.modifiers.new("th", "SOLIDIFY"); sol.thickness = thick; sol.offset = offset
    if not any(m.type == "SUBSURF" for m in ob.modifiers):
        ss = ob.modifiers.new("ss", "SUBSURF"); ss.levels = subdiv[0]; ss.render_levels = subdiv[1]
    for p in ob.data.polygons:
        p.use_smooth = True


def dress(body, cfg):
    ctx = bpy.context
    man, head = shell.make_mannequin(body)
    body.ob.hide_render = True
    mm = materials.flat_material("mannequin", (0.80, 0.77, 0.73), rough=0.48)
    man.data.materials.append(mm); head.data.materials.append(mm)
    tr = shell.make_trousers(body)
    tr.data.materials.append(materials.flat_material("trousers", tuple(cfg.get("trousers", (0.035, 0.045, 0.085))), rough=0.85))
    add_modifiers(tr, thick=0.003, subdiv=(0, 1), offset=1.0)
    return man, head, tr


def main():
    cfg = CFG[ITEM]
    body, ob, hood, man, crings = build_shell(cfg)
    outdir = os.path.join(ROOT, "3d", "models", ITEM)
    os.makedirs(outdir, exist_ok=True)
    add_modifiers(ob, thick=float(cfg.get("thick", 0.005)), wrinkle=cfg.get("wrinkle", WRINKLE.get(cfg["kind"])))
    ob["gl_texkey"] = ""; ob["gl_micro"] = cfg.get("micro", MICRO.get(cfg["kind"], "fleece"))
    if hood is not None:
        add_modifiers(hood, thick=0.004)
        hood["gl_texkey"] = "_hood"; hood["gl_micro"] = ob["gl_micro"]
    bpy.context.view_layer.update()
    trim_objs = []
    meta = man["meta"]
    if cfg.get("zip"):
        z0, z1 = meta["neck_z"] + cfg["collar"] * 0.7, meta["hem_z"] + 0.012
        zs = [z0 - (z0 - z1) * i / 90.0 for i in range(91)]
        pts, nrm = ray_path(ob, zs, offset=0.0006)
        if len(pts) > 20:
            zp = trims.zipper(pts, nrm, name="Zipper", metal=cfg.get("zip_metal", "nickel"), tape_rgb=cfg.get("zip_tape", (0.05, 0.05, 0.07)))
            trim_objs.append(zp)
            print("zipper path points", len(pts))
    if cfg.get("snaps"):
        n_sn = int(cfg.get("n_snaps", 6))
        z_a = meta["neck_z"] - 0.045
        z_b = meta["hem_z"] + float(cfg.get("rib_h", 0.0)) + 0.075
        for i in range(n_sn):
            zq = z_a + (z_b - z_a) * i / (n_sn - 1)
            pp, nn = ray_path(ob, [zq], offset=0.0007)
            if pp:
                nv = nn[0].normalized()
                tg = (Vector((1, 0, 0)) - nv * nv.x).normalized()
                trim_objs.append(trims.snap_button(pp[0], nv, tg, r=0.0072, name="Snap%d" % i, rgb=cfg.get("snap_rgb", (0.74, 0.75, 0.78))))
        print("snaps", len(trim_objs))
    if cfg.get("cords"):
        for sgn in (1, -1):
            zs = [meta["neck_z"] - 0.012 - 0.20 * i / 14.0 for i in range(15)]
            pts = []
            for i, z in enumerate(zs):
                x = sgn * (0.055 + 0.012 * math.sin(i / 14.0 * math.pi * 1.2))
                p, n = ray_path(ob, [z], x=x, offset=0.0035)
                if p:
                    pts.append(p[0])
            if len(pts) > 6:
                trim_objs += trims.tube_along(pts, 0.0021, name="Cord%s" % ("L" if sgn > 0 else "R"), rgb=cfg.get("cord_rgb", (0.92, 0.9, 0.88)))
    if cfg.get("binding") and cfg["sleeve"] == "armhole":
        rings = json.loads(ob["_cuff_rings"])
        rgb = cfg["binding"]
        for k, ids in enumerate(rings):
            pts = [ob.matrix_world @ ob.data.vertices[i].co for i in ids]
            nrm = [ob.matrix_world.to_3x3() @ ob.data.vertices[i].normal for i in ids]
            cu = bpy.data.curves.new("Binding%d" % k, "CURVE"); cu.dimensions = "3D"; cu.bevel_depth = float(cfg.get("binding_r", 0.0085)); cu.bevel_resolution = 5
            sp = cu.splines.new("NURBS"); sp.points.add(len(pts) - 1)
            for i, (p_, n_) in enumerate(zip(pts, nrm)):
                q = p_ + n_ * float(cfg.get("binding_out", 0.002))
                sp.points[i].co = (q.x, q.y, q.z, 1.0)
            sp.use_cyclic_u = True; sp.order_u = 4
            cb = bpy.data.objects.new("Binding%d" % k, cu); bpy.context.scene.collection.objects.link(cb)
            cu.materials.append(materials.flat_material("binding_m", rgb, rough=0.9))
            trim_objs.append(cb)
    mann, head, tr = dress(body, cfg)
    path = os.path.join(outdir, f"{ITEM}_scene.blend")
    bpy.ops.wm.save_as_mainfile(filepath=path)
    json.dump(man, open(os.path.join(outdir, f"{ITEM}_manifest.json"), "w"))
    if hood is not None:
        json.dump(json.loads(hood["gl_atlas"]), open(os.path.join(outdir, f"{ITEM}_manifest_hood.json"), "w"))
    print("saved", path)


if __name__ == "__main__":
    main()
