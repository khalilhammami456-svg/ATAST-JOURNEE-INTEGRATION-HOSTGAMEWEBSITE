import bpy, bmesh, sys, os
bpy.ops.wm.open_mainfile(filepath=os.environ["SRC"])
g = [o for o in bpy.data.objects if o.name.startswith("CD_Garment")][0]
bm = bmesh.new(); bm.from_mesh(g.data); bm.edges.ensure_lookup_table()
bnd = [e for e in bm.edges if len(e.link_faces) == 1]
adj = {}
for e in bnd:
    for v in e.verts: adj.setdefault(v.index, []).append(e)
seen, loops = set(), []
for e in bnd:
    if e.index in seen: continue
    stack, comp = [e], []
    while stack:
        x = stack.pop()
        if x.index in seen: continue
        seen.add(x.index); comp.append(x)
        for v in x.verts:
            for y in adj[v.index]:
                if y.index not in seen: stack.append(y)
    loops.append(comp)
print("verts", len(bm.verts), "faces", len(bm.faces), "boundary edges", len(bnd), "loops", len(loops))
for comp in sorted(loops, key=lambda c: -len(c)):
    vs = {v for e in comp for v in e.verts}
    c = sum((v.co for v in vs), type(next(iter(vs)).co)()) / len(vs)
    L = sum(e.calc_length() for e in comp)
    print("loop edges %3d len %.2f centre (%.2f %.2f %.2f)" % (len(comp), L, c.x, c.y, c.z))
