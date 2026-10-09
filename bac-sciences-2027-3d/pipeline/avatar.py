"""Build MakeHuman-based avatars inside Blender (bpy).  CC0 inputs: base.obj, default.mhskel, default_weights.mhw, targets.npz.
Usage:  python avatar.py [--targets /path/targets.npz]
Outputs (../3d/models): avatar_f.blend/.npz, avatar_m.blend/.npz"""
import sys, os, json, math, argparse
import numpy as np
import bpy

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, "assets_src")
OUT = os.path.abspath(os.path.join(HERE, "..", "3d", "models"))
TARGETS = os.environ.get("MH_TARGETS", "/home/user/work/mh_x/makehuman/data/targets.npz")

def parse_obj(path):
    V, VT, F, groups = [], [], [], []   # F: list of (vidx list, vtidx list, group)
    cur = None
    for ln in open(path):
        if ln.startswith("v "): V.append([float(x) for x in ln.split()[1:4]])
        elif ln.startswith("vt "): VT.append([float(x) for x in ln.split()[1:3]])
        elif ln.startswith("g "): cur = ln[2:].strip()
        elif ln.startswith("f "):
            vi, ti = [], []
            for tok in ln.split()[1:]:
                p = tok.split("/")
                vi.append(int(p[0]) - 1); ti.append(int(p[1]) - 1 if len(p) > 1 and p[1] else -1)
            F.append((vi, ti, cur))
    return np.array(V, dtype=np.float64), np.array(VT, dtype=np.float64), F

def macro_weights(gender, age, muscle=.5, weight=.5, race=(1/3, 1/3, 1/3)):
    gw = {"female": 1 - gender, "male": gender}
    if age < .1875: aw = {"baby": 1 - age/.1875, "child": age/.1875, "young": 0, "old": 0}
    elif age < .5: c = 1 - (age - .1875)/(.5 - .1875); aw = {"baby": 0, "child": c, "young": 1 - c, "old": 0}
    else: y = 1 - (age - .5)/.5; aw = {"baby": 0, "child": 0, "young": y, "old": 1 - y}
    def tri(v, lo, mid, hi):
        return {lo: max(0, 1 - 2*v), hi: max(0, 2*v - 1), mid: 1 - max(0, 1 - 2*v) - max(0, 2*v - 1)}
    mw = tri(muscle, "minmuscle", "averagemuscle", "maxmuscle")
    ww = tri(weight, "minweight", "averageweight", "maxweight")
    rw = dict(zip(("asian", "african", "caucasian"), race))
    out = {}
    for g, gv in gw.items():
        for a, av in aw.items():
            for r, rv in rw.items():
                w = gv * av * rv
                if w > 1e-6: out[f"targets/macrodetails/{r}-{g}-{a}"] = w
            for m, mv in mw.items():
                for ww_k, wv in ww.items():
                    w = gv * av * mv * wv
                    if w > 1e-6: out[f"targets/macrodetails/universal-{g}-{a}-{m}-{ww_k}"] = w
    return out

def morph(V, T, weights):
    P = V.copy()
    for k, w in weights.items():
        if k + ".index" not in T:
            print("  (missing target)", k); continue
        idx = T[k + ".index"].astype(np.int64); vec = T[k + ".vector"].astype(np.float64)
        P[idx] += w * vec
    return P

def build(name, gender, height_m, age=.36, out_dir=OUT):
    V, VT, F, = parse_obj(os.path.join(SRC, "base.obj"))
    T = np.load(TARGETS, allow_pickle=True)
    W = macro_weights(gender, age)
    P = morph(V, T, W)
    # MakeHuman (x right/left, y up, z front) -> Blender (x, -z, y)
    B = np.stack([P[:, 0], -P[:, 2], P[:, 1]], axis=1)
    # joints: centroid of vertices of each joint-* group
    joints = {}
    for vi, ti, g in F:
        if g and g.startswith("joint-"):
            joints.setdefault(g, set()).update(vi)
    joints = {g: B[sorted(s)].mean(axis=0) for g, s in joints.items()}
    # body faces only
    body = [(vi, ti) for vi, ti, g in F if g == "body"]
    used = sorted({i for vi, _ in body for i in vi})
    remap = {v: i for i, v in enumerate(used)}
    verts = B[used]
    # scale/place: feet on z=0, to target height
    zmin = verts[:, 2].min(); hgt = verts[:, 2].max() - zmin
    s = height_m / hgt
    verts = (verts - np.array([0, 0, zmin])) * s
    joints = {k: (v - np.array([0, 0, zmin])) * s for k, v in joints.items()}
    faces = [[remap[i] for i in vi] for vi, _ in body]
    uvs = [[VT[t] if t >= 0 else (0, 0) for t in ti] for _, ti in body]
    # bone weights -> dominant bone per vertex
    wj = json.load(open(os.path.join(SRC, "default_weights.mhw")))["weights"]
    bones = sorted(wj.keys()); bw = np.zeros((len(V), len(bones)), dtype=np.float32)
    for j, b in enumerate(bones):
        for vi_, w_ in wj[b]: bw[int(vi_), j] = w_
    bw = bw[used]; dom = np.array(bones)[bw.argmax(axis=1)]
    # --- blender object
    bpy.ops.wm.read_factory_settings(use_empty=True)
    me = bpy.data.meshes.new(name); me.from_pydata(verts.tolist(), [], faces); me.update()
    uv = me.uv_layers.new(name="UVMap"); li = 0
    for f_uv in uvs:
        for u in f_uv: uv.data[li].uv = (float(u[0]), float(u[1])); li += 1
    ob = bpy.data.objects.new(name, me); bpy.context.scene.collection.objects.link(ob)
    for p in me.polygons: p.use_smooth = True
    for j, b in enumerate(bones):
        vg = ob.vertex_groups.new(name=b)
        idx = np.nonzero(bw[:, j] > 0.01)[0]
        for i in idx: vg.add([int(i)], float(bw[i, j]), "REPLACE")
    # clay mannequin material
    mat = bpy.data.materials.new("avatar_clay"); mat.use_nodes = True
    bsdf = mat.node_tree.nodes["Principled BSDF"]
    bsdf.inputs["Base Color"].default_value = (0.62, 0.55, 0.49, 1)
    bsdf.inputs["Roughness"].default_value = 0.55
    ob.data.materials.append(mat)
    os.makedirs(out_dir, exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(out_dir, f"{name}.blend"))
    np.savez_compressed(os.path.join(out_dir, f"{name}.npz"), verts=verts, faces=np.array(faces, dtype=object), joints_names=list(joints.keys()),
                        joints_xyz=np.array(list(joints.values())), dom=dom, bones=np.array(bones), allow_pickle=True)
    print(name, "verts", len(verts), "faces", len(faces), "height", round(float(verts[:, 2].max()), 3), "m")
    print(" joints:", len(joints), "sample:", {k: np.round(v, 3).tolist() for k, v in list(joints.items())[:0]})
    return ob

if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("--targets"); a = ap.parse_args()
    if a.targets: TARGETS = a.targets
    which = sys.argv[-1] if sys.argv[-1] in ("f", "m") else "both"
    if which in ("f", "both"): build("avatar_f", 0.0, 1.68)
    if which in ("m", "both"): build("avatar_m", 1.0, 1.79)
