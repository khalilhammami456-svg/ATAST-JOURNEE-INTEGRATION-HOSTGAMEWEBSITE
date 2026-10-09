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
    "H3": dict(kind="hoodie", sleeve="long", hem_z=0.88, hood=True, zip=True, cords=True, pocket=False, collar=0.04,
               e_torso=(0.035, 0.04, 0.048, 0.052, 0.025), e_arm=(0.03, 0.04, 0.042, 0.03, 0.012), rib_h=0.08, cuff_h=0.07),
    "T1": dict(kind="tee", sleeve="short", arm_cut=0.42, hem_z=0.90, hood=False, zip=False, cords=False, collar=0.022,
               e_torso=(0.035, 0.04, 0.046, 0.05, 0.025), e_arm=(0.04, 0.05, 0.05, 0.05, 0.05), rib_h=0.0, cuff_h=0.0),
    "T2": dict(kind="tee", sleeve="short", arm_cut=0.42, hem_z=0.90, hood=False, zip=False, cords=False, collar=0.022,
               e_torso=(0.04, 0.045, 0.05, 0.055, 0.025), e_arm=(0.045, 0.055, 0.055, 0.055, 0.055), rib_h=0.0, cuff_h=0.0),
    "T3": dict(kind="tee", sleeve="short", arm_cut=0.42, hem_z=0.90, hood=False, zip=False, cords=False, collar=0.022,
               e_torso=(0.03, 0.035, 0.04, 0.045, 0.022), e_arm=(0.035, 0.045, 0.045, 0.045, 0.045), rib_h=0.0, cuff_h=0.0),
    "J1": dict(kind="jacket", sleeve="long", hem_z=0.90, hood=False, zip=False, snaps=True, collar=0.045,
               e_torso=(0.04, 0.045, 0.052, 0.055, 0.028), e_arm=(0.035, 0.045, 0.045, 0.032, 0.013), rib_h=0.085, cuff_h=0.08),
    "J2": dict(kind="jacket", sleeve="long", hem_z=0.90, hood=False, zip=False, snaps=True, collar=0.05,
               e_torso=(0.04, 0.046, 0.055, 0.058, 0.03), e_arm=(0.035, 0.045, 0.045, 0.035, 0.02), rib_h=0.0, cuff_h=0.0),
    "V1": dict(kind="vest", sleeve="armhole", hem_z=0.92, hood=False, zip=False, snaps=True, collar=0.04,
               e_torso=(0.04, 0.045, 0.052, 0.055, 0.028), e_arm=(0.03, 0.03, 0.03, 0.03, 0.03), rib_h=0.07, cuff_h=0.0),
    "V2": dict(kind="vest", sleeve="armhole", hem_z=0.93, hood=False, zip=True, snaps=False, collar=0.06,
               e_torso=(0.05, 0.058, 0.066, 0.07, 0.03), e_arm=(0.04, 0.04, 0.04, 0.04, 0.04), rib_h=0.0, cuff_h=0.0),
}


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
    rings = shell.extrude_hem(bm, hip, hem_z, steps=8, flare=cfg.get("flare", 0.0))
    shell.regularize_ring(rings[-1], planar_z=hem_z, iters=14)
    tags = {"hem": set(), "collar": set(), "cuff": set()}
    rib_h = cfg.get("rib_h", 0.0)
    if rib_h > 0:
        for k, rg in enumerate(rings):
            if (k / (len(rings) - 1)) >= (1 - rib_h / (rings[0][0].co.z - hem_z + 1e-9)):
                tags["hem"].update(rg)
    shell.regularize_ring(neck, iters=4)
    crings = shell.extrude_loop(bm, neck, Vector((0, 0, 1)), cfg.get("collar", 0.03), steps=3, scale=lambda t: 1.0 - 0.06 * t)
    shell.regularize_ring(crings[-1], planar_z=sum(v.co.z for v in crings[-1]) / len(crings[-1]), iters=10)
    for rg in crings:
        tags["collar"].update(rg)
    pin_objs = set(crings[-1]) | set(crings[-2]) | set(neck)
    for cl in cuffs:
        shell.regularize_ring(cl, iters=4)
    sh_, el_, wr_ = body.arm_axis("L")
    Lchain = (el_ - sh_).length + (wr_ - el_).length
    z = body.z
    et = cfg["e_torso"]
    ease_torso = [(hem_z, et[0]), (z["hip"], et[1]), (z["waist"], et[2]), (z["chest"], et[3]), (z["shoulder"], et[4])]
    ea = cfg["e_arm"]
    ease_arm = [(0.0, ea[0]), (0.35, ea[1]), (0.7, ea[2]), (0.88, ea[3]), (1.0, ea[4])]
    shell.smooth_verts(bm, iters=10, factor=0.5)
    shell.ease_offset(bm, body, ease_torso, ease_arm)
    cuff_h = cfg.get("cuff_h", 0.0)
    if cuff_h > 0 and cfg["sleeve"] == "long":
        for v in bm.verts:
            side_, s_, d_, t_, q_, ax_ = shell.arm_params(body, v.co)
            if d_ < 0.12 and s_ >= Lchain * float(cfg.get("cuff_t", 0.97)) - cuff_h:
                tags["cuff"].add(v)
    bm.verts.index_update()
    tags = {k: {v.index for v in s} for k, s in tags.items()}
    pin_ids = {v.index for v in pin_objs}
    ob = shell.make_object(bm, "CD_Garment_" + ITEM)
    man = shell.build_uv(ob, body, vtags=tags)
    man["meta"] = dict(item=ITEM, kind=cfg["kind"], sleeve=cfg["sleeve"], hem_z=hem_z, neck_z=sum(v.co.z for v in neck) / len(neck),
                       shoulder_z=z["shoulder"], chest_z=z["chest"], waist_z=z["waist"], chain_len=Lchain,
                       cuff_t=float(cfg.get("cuff_t", 0.97)), rib_h=rib_h, cuff_h=cuff_h, collar_h=cfg.get("collar", 0.03))
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
    shell.settle(ob, body.ob, pinw, frames=int(cfg.get("settle", 70)), bending=float(cfg.get("bend", 12)),
                 compression=25, tension=30, thickness=0.004)
    hood = None
    if cfg.get("hood"):
        ring_world = [ob.data.vertices[v.index].co.copy() for v in crings[-1]]
        hood = shell.make_hood_down(ob, ring_world, body.ob, frames=36)
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


def add_modifiers(ob, thick=0.005, subdiv=(1, 2), offset=1.0):
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
    tr.data.materials.append(materials.flat_material("trousers", (0.035, 0.045, 0.085), rough=0.85))
    add_modifiers(tr, thick=0.003, subdiv=(0, 1), offset=1.0)
    return man, head, tr


def main():
    cfg = CFG[ITEM]
    body, ob, hood, man, crings = build_shell(cfg)
    outdir = os.path.join(ROOT, "3d", "models", ITEM)
    os.makedirs(outdir, exist_ok=True)
    add_modifiers(ob, thick=float(cfg.get("thick", 0.005)))
    if hood is not None:
        add_modifiers(hood, thick=0.004)
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
    mann, head, tr = dress(body, cfg)
    path = os.path.join(outdir, f"{ITEM}_scene.blend")
    bpy.ops.wm.save_as_mainfile(filepath=path)
    json.dump(man, open(os.path.join(outdir, f"{ITEM}_manifest.json"), "w"))
    if hood is not None:
        json.dump(json.loads(hood["gl_atlas"]), open(os.path.join(outdir, f"{ITEM}_manifest_hood.json"), "w"))
    print("saved", path)


main()
