"""Blender materials for the collection (bpy).  Image-based: the same albedo/normal/ORM atlas that is
exported to glTF is what Cycles renders, so the web viewer matches the stills.  Micro detail (knit,
fleece nap, twill) is layered on top procedurally for the renders only (glTF has no such layer)."""
import bpy, os, math


def _img(path, srgb=True, name=None):
    im = bpy.data.images.load(path, check_existing=True)
    im.colorspace_settings.name = "sRGB" if srgb else "Non-Color"
    return im


def atlas_material(name, albedo, normal=None, orm=None, uvmap="pattern", normal_strength=1.0, sheen=0.35,
                   sheen_roughness=0.5, micro="fleece", micro_scale=1.0, side_m=1.7, subsurface=0.0,
                   specular=0.35, double_sided=False):
    """Principled BSDF fed by atlas textures.  micro in {None,'fleece','jersey','twill','rib'}."""
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    nt = mat.node_tree
    nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputMaterial"); out.location = (900, 0)
    bsdf = nt.nodes.new("ShaderNodeBsdfPrincipled"); bsdf.location = (600, 0)
    nt.links.new(bsdf.outputs["BSDF"], out.inputs["Surface"])
    uv = nt.nodes.new("ShaderNodeUVMap"); uv.uv_map = uvmap; uv.location = (-900, 0)
    ta = nt.nodes.new("ShaderNodeTexImage"); ta.image = _img(albedo, True); ta.location = (-600, 300)
    ta.interpolation = "Cubic"
    nt.links.new(uv.outputs["UV"], ta.inputs["Vector"])
    base = ta.outputs["Color"]
    if orm:
        to = nt.nodes.new("ShaderNodeTexImage"); to.image = _img(orm, False); to.location = (-600, -100)
        nt.links.new(uv.outputs["UV"], to.inputs["Vector"])
        sep = nt.nodes.new("ShaderNodeSeparateColor"); sep.location = (-350, -100)
        nt.links.new(to.outputs["Color"], sep.inputs["Color"])
        nt.links.new(sep.outputs["Green"], bsdf.inputs["Roughness"])
        nt.links.new(sep.outputs["Blue"], bsdf.inputs["Metallic"])
        mix = nt.nodes.new("ShaderNodeMix"); mix.data_type = "RGBA"; mix.blend_type = "MULTIPLY"; mix.location = (-150, 300)
        mix.inputs["Factor"].default_value = 0.9
        nt.links.new(base, mix.inputs["A"]); nt.links.new(sep.outputs["Red"], mix.inputs["B"])
        base = mix.outputs["Result"]
    nt.links.new(base, bsdf.inputs["Base Color"])

    nrm_out = None
    if normal:
        tn = nt.nodes.new("ShaderNodeTexImage"); tn.image = _img(normal, False); tn.location = (-600, -450)
        tn.interpolation = "Cubic"
        nt.links.new(uv.outputs["UV"], tn.inputs["Vector"])
        nm = nt.nodes.new("ShaderNodeNormalMap"); nm.location = (-300, -450); nm.uv_map = uvmap
        nm.inputs["Strength"].default_value = normal_strength
        nt.links.new(tn.outputs["Color"], nm.inputs["Color"])
        nrm_out = nm.outputs["Normal"]
    # procedural micro relief on top (renders only)
    if micro:
        cfg = dict(fleece=(900.0, 0.10, 0.5, 0.55), jersey=(1500.0, 0.18, 0.3, 0.45),
                   twill=(2400.0, 0.12, 0.2, 0.4), rib=(700.0, 0.10, 0.4, 0.5))[micro]
        sc, st, det, rg = cfg
        mp = nt.nodes.new("ShaderNodeMapping"); mp.location = (-600, -800)
        mp.inputs["Scale"].default_value = (side_m * sc * micro_scale, side_m * sc * micro_scale, 1)
        nt.links.new(uv.outputs["UV"], mp.inputs["Vector"])
        if micro in ("jersey", "twill"):
            wv = nt.nodes.new("ShaderNodeTexWave"); wv.location = (-380, -800)
            wv.wave_type = "BANDS"; wv.bands_direction = "DIAGONAL" if micro == "twill" else "X"
            wv.inputs["Scale"].default_value = 1.0; wv.inputs["Distortion"].default_value = 1.2; wv.inputs["Detail"].default_value = 2.0
            nt.links.new(mp.outputs["Vector"], wv.inputs["Vector"])
            h = wv.outputs["Fac"]
        else:
            ns = nt.nodes.new("ShaderNodeTexNoise"); ns.location = (-380, -800)
            ns.inputs["Scale"].default_value = 1.0; ns.inputs["Detail"].default_value = 6.0; ns.inputs["Roughness"].default_value = 0.7
            nt.links.new(mp.outputs["Vector"], ns.inputs["Vector"])
            h = ns.outputs["Fac"]
        bp = nt.nodes.new("ShaderNodeBump"); bp.location = (-100, -700)
        bp.inputs["Strength"].default_value = st; bp.inputs["Distance"].default_value = 0.0015
        nt.links.new(h, bp.inputs["Height"])
        if nrm_out is not None:
            nt.links.new(nrm_out, bp.inputs["Normal"])
        nrm_out = bp.outputs["Normal"]
    if nrm_out is not None:
        nt.links.new(nrm_out, bsdf.inputs["Normal"])
    if not orm:
        bsdf.inputs["Roughness"].default_value = 0.9
    try:
        bsdf.inputs["Sheen Weight"].default_value = sheen
        bsdf.inputs["Sheen Roughness"].default_value = sheen_roughness
        bsdf.inputs["Sheen Tint"].default_value = (1, 1, 1, 1)
    except Exception:
        pass
    try:
        bsdf.inputs["Specular IOR Level"].default_value = specular
    except Exception:
        pass
    if subsurface:
        bsdf.inputs["Subsurface Weight"].default_value = subsurface
    mat.use_backface_culling = not double_sided
    return mat


def flat_material(name, rgb, rough=0.6, metal=0.0, spec=0.5):
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    b = mat.node_tree.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = (*rgb, 1)
    b.inputs["Roughness"].default_value = rough
    b.inputs["Metallic"].default_value = metal
    return mat


def skin_material(name="mannequin", rgb=(0.80, 0.66, 0.58), rough=0.55, sss=0.15):
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    b = mat.node_tree.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = (*rgb, 1)
    b.inputs["Roughness"].default_value = rough
    try:
        b.inputs["Subsurface Weight"].default_value = sss
        b.inputs["Subsurface Radius"].default_value = (0.9, 0.35, 0.2)
        b.inputs["Subsurface Scale"].default_value = 0.01
    except Exception:
        pass
    return mat


def apply(ob, *mats):
    """Assign materials by slot (face material_index already encodes piece index)."""
    ob.data.materials.clear()
    for m in mats:
        ob.data.materials.append(m)


def apply_all(ob, mat):
    """Same material in every slot (pieces share one atlas; face material_index = piece index)."""
    n = max((p.material_index for p in ob.data.polygons), default=0) + 1
    ob.data.materials.clear()
    for _ in range(n):
        ob.data.materials.append(mat)


def export_material(name, albedo, normal=None, orm=None, uvmap="pattern", normal_strength=1.0):
    """Plain glTF-friendly material: Base Color / Normal Map -> Normal / Separate(G rough, B metal).  No procedural micro."""
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    nt = mat.node_tree
    nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    bsdf = nt.nodes.new("ShaderNodeBsdfPrincipled")
    nt.links.new(bsdf.outputs["BSDF"], out.inputs["Surface"])
    uv = nt.nodes.new("ShaderNodeUVMap"); uv.uv_map = uvmap
    ta = nt.nodes.new("ShaderNodeTexImage"); ta.image = _img(albedo, True)
    nt.links.new(uv.outputs["UV"], ta.inputs["Vector"]); nt.links.new(ta.outputs["Color"], bsdf.inputs["Base Color"])
    if orm:
        to = nt.nodes.new("ShaderNodeTexImage"); to.image = _img(orm, False)
        nt.links.new(uv.outputs["UV"], to.inputs["Vector"])
        sep = nt.nodes.new("ShaderNodeSeparateColor")
        nt.links.new(to.outputs["Color"], sep.inputs["Color"])
        nt.links.new(sep.outputs["Green"], bsdf.inputs["Roughness"]); nt.links.new(sep.outputs["Blue"], bsdf.inputs["Metallic"])
    if normal:
        tn = nt.nodes.new("ShaderNodeTexImage"); tn.image = _img(normal, False)
        nt.links.new(uv.outputs["UV"], tn.inputs["Vector"])
        nm = nt.nodes.new("ShaderNodeNormalMap"); nm.inputs["Strength"].default_value = normal_strength
        nt.links.new(tn.outputs["Color"], nm.inputs["Color"]); nt.links.new(nm.outputs["Normal"], bsdf.inputs["Normal"])
    return mat
