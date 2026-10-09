import os, sys, bpy
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import garment_lib as gl
bpy.ops.wm.open_mainfile(filepath=os.environ["SRC"])
gl.attach()
g = gl.garment()
gl.finish(g, push=os.environ.get("PUSH", "1") == "1")
print("loops after finish:")
import bmesh
bm = bmesh.new(); bm.from_mesh(g.data)
print("boundary edges", sum(1 for e in bm.edges if len(e.link_faces) == 1))
bpy.ops.wm.save_as_mainfile(filepath=os.environ["OUT"])
print("saved")
