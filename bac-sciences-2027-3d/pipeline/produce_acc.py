"""Produce an accessory scene: S1,S2 (scarves) A1 cap, A2 beanie, A3 tote, A4 patch, A5 label.
usage: ITEM=S1 python produce_acc.py"""
import os, sys, json, math, bpy
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import garment_lib as gl, shell, materials, produce, accessories as AC
from mathutils import Vector
E = os.environ.get
ITEM = E("ITEM", "S1")
ROOT = os.path.abspath(os.path.join(HERE, ".."))
outdir = os.path.join(ROOT, "3d", "models", ITEM)
os.makedirs(outdir, exist_ok=True)


BASE_RGB = {"S1": (0.62, 0.62, 0.60), "S2": (0.05, 0.065, 0.12)}


def dressed_base(cfg_name="T1", rgb=(0.055, 0.060, 0.075)):
    produce.ITEM = "BASE"
    cfg = dict(produce.CFG[cfg_name]); cfg["settle"] = 0
    body, top, hood, man, crings = produce.build_shell(cfg)
    produce.add_modifiers(top, thick=0.004)
    top.data.materials.clear()
    top.data.materials.append(materials.flat_material("base_top", rgb, rough=0.9))
    mann, head, tr = produce.dress(body, cfg)
    for k in list(top.keys()):
        if k in ("gl_atlas",):
            del top[k]
    top.name = "BaseTop"
    return body, top, mann, head, tr


def save(man_dict=None, extra=None):
    path = os.path.join(outdir, f"{ITEM}_scene.blend")
    bpy.ops.wm.save_as_mainfile(filepath=path)
    if man_dict:
        json.dump(man_dict, open(os.path.join(outdir, f"{ITEM}_manifest.json"), "w"))
    for k, v in (extra or {}).items():
        json.dump(v, open(os.path.join(outdir, f"{ITEM}_manifest_{k}.json"), "w"))
    print("saved", path)


def tag(ob, key, micro):
    ob["gl_texkey"] = key; ob["gl_micro"] = micro


if ITEM in ("S1", "S2"):
    body, top, mann, head, tr = dressed_base(rgb=BASE_RGB[ITEM])
    produce.bpy.context.view_layer.update()
    length, width = (1.72, 0.17) if ITEM == "S1" else (1.80, 0.15)
    scarf, man, info, fringe = AC.make_scarf2(body, head, top, length=length, width=width, name="CD_Scarf_" + ITEM, fringe=0.06 if ITEM == "S1" else 0.045)
    produce.add_modifiers(scarf, thick=0.008, subdiv=(1, 2), offset=0.0, wrinkle=(0.10, 0.005))
    tag(scarf, "", "fleece")
    if fringe is not None:
        produce.add_modifiers(fringe, thick=0.002, subdiv=(0, 1), offset=0.0)
        fringe.data.materials.append(materials.flat_material("fringe_m", (0.90, 0.88, 0.83), rough=0.95))
    save(man)
elif ITEM in ("A1", "A2"):
    body, top, mann, head, tr = dressed_base()
    if ITEM == "A1":
        crown, brim, info = AC.make_cap(head)
        man, manb = AC.cap_uv(crown, brim, info)
        man["info"] = info
        crown["gl_atlas"] = json.dumps(man)
        for o, thick in ((crown, 0.004), (brim, 0.004)):
            produce.add_modifiers(o, thick=thick, subdiv=(1, 2), offset=1.0)
        tag(crown, "", "twill"); tag(brim, "_brim", "twill")
        # fabric-covered top button
        bm_ = produce.bpy.data.meshes.new("Button"); import bmesh as _bm
        bb = _bm.new(); _bm.ops.create_uvsphere(bb, u_segments=20, v_segments=12, radius=0.0095)
        bb.to_mesh(bm_); bb.free()
        btn = produce.bpy.data.objects.new("CapButton", bm_); produce.bpy.context.scene.collection.objects.link(btn)
        btn.location = (info["c"][0], info["c"][1], info["c"][2] + info["r"][2] * 1.0 + 0.0125)
        for p_ in bm_.polygons: p_.use_smooth = True
        bm_.materials.append(materials.flat_material("btn_m", (0.045, 0.06, 0.12), rough=0.9))
        save(man, {"brim": manb})
    else:
        crown, cuff, info = AC.make_beanie(head)
        man, manc = AC.beanie_uv(crown, cuff, info)
        for o in (crown, cuff):
            produce.add_modifiers(o, thick=0.006, subdiv=(1, 2), offset=1.0)
        tag(crown, "", "none"); tag(cuff, "_cuff", "none")
        save(man, {"cuff": manc})
elif ITEM == "A3":
    gl.boot("MAN")
    body, hs, info = AC.make_tote()
    man = AC.tote_uv(body, info)
    produce.add_modifiers(body, thick=0.005, subdiv=(1, 2), offset=1.0)
    tag(body, "", "twill")
    for h in hs:
        h.data.materials.append(materials.flat_material("handle", (0.93, 0.91, 0.86), rough=0.9))
    save(man)
elif ITEM == "A4":
    gl.boot("MAN")
    ob, man = AC.make_patch()
    ob.location.z += 1.2                       # lift off the studio floor (macro subject)
    tag(ob, "", "twill")
    save(man)
elif ITEM == "A5":
    gl.boot("MAN")
    ob, man = AC.make_label()
    ob.location.z += 1.2
    tag(ob, "", "twill")
    save(man)
