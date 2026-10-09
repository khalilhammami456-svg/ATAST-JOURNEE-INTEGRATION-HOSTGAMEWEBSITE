import os, sys, bpy
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import garment_lib as gl, materials, studio, shell
gl.boot("MAN"); gl.pose_arms(0.7); gl.cd["avatar"].measure(bpy.context, force=True)
body = shell.Body()
man, head = shell.make_mannequin(body)
tr = shell.make_trousers(body); sh = shell.make_shoes(body)
body.ob.hide_render = True
mm = materials.flat_material("mannequin", (0.80, 0.76, 0.72), rough=0.5)
man.data.materials.append(mm); head.data.materials.append(mm)
tr.data.materials.append(materials.flat_material("trousers", (0.04, 0.05, 0.09), rough=0.85))
sh.data.materials.append(materials.flat_material("upper", (0.05, 0.06, 0.1), rough=0.6)); sh.data.materials.append(materials.flat_material("sole", (0.85, 0.83, 0.8), rough=0.5))
sc = bpy.context.scene
studio.render_settings(700, 1000, samples=16, threads=4)
for name, yaw in (("front", 0), ("q", 40)):
    for o in [o for o in sc.objects if o.name.startswith(("StudioRig", "cyclorama", "key", "fill", "rim", "top", "cam"))]: bpy.data.objects.remove(o)
    studio.studio(focus_z=0.95, cam_dist=5.2, lens=85, yaw_deg=yaw, key=0.6)
    studio.render(f"/home/user/work/prev/style_{name}.png")
