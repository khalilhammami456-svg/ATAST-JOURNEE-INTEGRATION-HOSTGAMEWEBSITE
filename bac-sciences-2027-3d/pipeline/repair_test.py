import os, sys, bpy
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import garment_lib as gl
bpy.ops.wm.open_mainfile(filepath=os.environ["SRC"])
gl.attach()
g = gl.garment()
sc = bpy.context.scene
print("frames", sc.frame_start, sc.frame_current, sc.frame_end)
pass
print("freeze", gl.freeze(g))
print("before", gl.penetration_stats(g))
gl.fix_penetration(g, clearance=float(os.environ.get('CLR', '0.008')), smooth_passes=2)
print("after", gl.penetration_stats(g))
bpy.ops.wm.save_as_mainfile(filepath=os.environ["OUT"])
