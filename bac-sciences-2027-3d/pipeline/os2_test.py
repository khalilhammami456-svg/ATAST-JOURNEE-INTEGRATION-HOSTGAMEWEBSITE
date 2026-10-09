import bpy, sys, os, time
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "third_party", "opensew2"))
bpy.ops.wm.read_homefile(use_empty=True)
t0 = time.time()
r = bpy.ops.preferences.addon_enable(module="clothing_design"); print("addon_enable", r, round(time.time()-t0,1))
from clothing_design import avatar, library, build, sim
print("presets:", list(library.PRESETS.keys()))
ctx = bpy.context; scn = ctx.scene
r = bpy.ops.cd.import_character(figure=os.environ.get("FIG", "MAN")); print("import", r)
m = avatar.measure(ctx, force=True); print("height", round(m["height"], 3), "figure", m.get("figure_auto"))
preset = os.environ.get("PRESET", "HOODIE")
t = time.time(); r = bpy.ops.cd.add_garment(preset=preset, fit=float(os.environ.get("FIT", "0.10"))); print("add_garment", r, round(time.time()-t, 1), "s")
print("props:", [p for p in dir(scn.cd) if not p.startswith("_")][:60])
t = time.time(); r = bpy.ops.cd.sew(); print("sew", r, round(time.time()-t, 1), "s")
g = build.garment_object(ctx, create=False)
print("garment", g.name, len(g.data.vertices), "verts")
out = os.environ.get("OUT", "/home/user/work/os2_" + preset.lower() + ".blend")
bpy.ops.wm.save_as_mainfile(filepath=out); print("saved", out)
