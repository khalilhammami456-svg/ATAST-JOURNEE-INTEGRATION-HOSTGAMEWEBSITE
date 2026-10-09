import bpy, sys, os, time
sys.path.insert(0, os.path.dirname(__file__))
import studio
studio.clear_scene()
with bpy.data.libraries.load(os.path.join(studio.ROOT, "3d/models/avatar_f.blend")) as (src, dst): dst.objects = src.objects
for o in dst.objects: bpy.context.scene.collection.objects.link(o)
studio.studio(focus_z=0.92, cam_dist=6.2, lens=85)
studio.render_settings(900, 1350, samples=48, threads=4)
t = time.time(); studio.render("/home/user/work/avatar_test.png"); print("render s", round(time.time() - t, 1))
