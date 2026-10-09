import os, sys, bpy
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import garment_lib as gl
gl.boot("MAN")
import presets_bac as pb
g = gl.draft(pb.preset_hoodie_zip, "G", fit=0.3, cuff_h=0.0)
me = g.data
used = set()
for p in me.polygons:
    vs = list(p.vertices)
    for i in range(len(vs)): used.add((min(vs[i], vs[i-1]), max(vs[i], vs[i-1])))
names = {vg.index: vg.name for vg in g.vertex_groups}
def piece(v):
    for gr in me.vertices[v].groups:
        if gr.weight > .5: return names[gr.group]
rows = []
for e in me.edges:
    if tuple(sorted(e.vertices)) in used: continue
    a, b = e.vertices
    pa, pb_ = piece(a), piece(b)
    if {"G_Front_L", "G_Sleeve_L"} == {pa, pb_}:
        va, vb = me.vertices[a].co, me.vertices[b].co
        rows.append((a, pa[2:], tuple(round(x, 2) for x in va), pb_[2:], tuple(round(x, 2) for x in vb), round((va - vb).length, 3)))
for r in sorted(rows)[:19]: print(r)
