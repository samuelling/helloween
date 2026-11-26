"""High-quality sculpt + bake toolkit (Blender 5.x, headless).

Sculpting here is SDF-style: rough forms are unioned and fused with a voxel remesh, sockets and
openings are carved with exact booleans, then the surface is relaxed and given fine displacement.
Drapery comes from cloth simulation. Everything is then baked to texture atlases (colour with AO,
roughness+metal, tangent normals, emission) so the procedural detail survives glTF export.
"""
import bpy, bmesh, math, random, os
import numpy as np
from mathutils import Vector as V, Matrix, Euler, Quaternion
from lib import MB, mat, tex_coord, add_bump, noise_bump, wave_bump, noise_color, tube_curve, empty

SC = lambda: bpy.context.scene


# =================================================================== object plumbing
def new_obj(name, me, coll=None):
    ob = bpy.data.objects.new(name, me)
    (coll or SC().collection).objects.link(ob)
    return ob


def mb_obj(mb, name, mats):
    return mb.obj(name, mats)


def apply_mods(ob):
    dg = bpy.context.evaluated_depsgraph_get()
    me = bpy.data.meshes.new_from_object(ob.evaluated_get(dg), depsgraph=dg)
    ob.modifiers.clear()
    old = ob.data
    ob.data = me
    if old.users == 0:
        bpy.data.meshes.remove(old)
    return ob


def merge(objs, name):
    """Join meshes (world transforms baked in) into one new object; deletes the inputs."""
    bm = bmesh.new()
    mats, mat_index = [], {}
    for ob in objs:
        if ob.type != "MESH":
            continue
        me = ob.data.copy()
        me.transform(ob.matrix_world)
        # remap material indices into the merged slot list
        remap = []
        for m in me.materials:
            if m is None:
                remap.append(0); continue
            if m.name not in mat_index:
                mat_index[m.name] = len(mats); mats.append(m)
            remap.append(mat_index[m.name])
        for p in me.polygons:
            p.material_index = remap[p.material_index] if remap else 0
        bm.from_mesh(me)
        bpy.data.meshes.remove(me)
    out = bpy.data.meshes.new(name)
    bm.to_mesh(out); bm.free()
    for m in mats:
        out.materials.append(m)
    for ob in objs:
        bpy.data.objects.remove(ob, do_unlink=True)
    return new_obj(name, out)


def prim(kind, loc=(0, 0, 0), size=(1, 1, 1), rot=(0, 0, 0), segs=(32, 16), name="p", mats=()):
    mb = MB()
    if kind == "sphere":
        mb.sphere((0, 0, 0), 1.0, size, (0, 0, 0), segs)
    elif kind == "cube":
        mb.box((0, 0, 0), size)
    ob = mb.obj(name, list(mats))
    ob.location, ob.rotation_euler = loc, rot
    return ob


def capsule(p1, p2, r1, r2=None, name="cap", segs=16):
    r2 = r1 if r2 is None else r2
    mb = MB()
    mb.cyl(p1, p2, r1, r2, segs=segs)
    mb.sphere(p1, r1, segs=(segs, segs // 2))
    mb.sphere(p2, r2, segs=(segs, segs // 2))
    return mb.obj(name, [])


def ellipsoid(c, r, rot=(0, 0, 0), name="ell", segs=(28, 16)):
    mb = MB()
    mb.sphere(c, 1.0, r, rot, segs)
    return mb.obj(name, [])


def sweep(path, radii, name="sweep", ring=10, flat=1.0, up=V((0, 0, 1)), close=True):
    """Tube along a polyline with per-point radius; flat<1 squashes the cross-section along the
    in-plane normal (ribs, blades)."""
    bm = bmesh.new()
    pts = [V(p) for p in path]
    rings = []
    for i, p in enumerate(pts):
        t = (pts[min(i + 1, len(pts) - 1)] - pts[max(i - 1, 0)]).normalized()
        n = up.cross(t)
        if n.length < 1e-6:
            n = V((1, 0, 0)).cross(t)
        n.normalize()
        b = t.cross(n).normalized()
        r = radii[i] if isinstance(radii, (list, tuple)) else radii
        ring_v = []
        for k in range(ring):
            a = 2 * math.pi * k / ring
            ring_v.append(bm.verts.new(p + n * math.cos(a) * r + b * math.sin(a) * r * flat))
        rings.append(ring_v)
    for i in range(len(rings) - 1):
        for k in range(ring):
            bm.faces.new((rings[i][k], rings[i][(k + 1) % ring], rings[i + 1][(k + 1) % ring], rings[i + 1][k]))
    if close:
        bm.faces.new(list(reversed(rings[0]))); bm.faces.new(rings[-1])
    me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free()
    return new_obj(name, me)


# =================================================================== sculpt operations
def fuse(objs, voxel, name, smooth=4, smooth_factor=0.6, adaptivity=0.0):
    ob = merge(objs, name)
    m = ob.modifiers.new("Remesh", "REMESH")
    m.mode = "VOXEL"; m.voxel_size = voxel; m.adaptivity = adaptivity; m.use_smooth_shade = True
    apply_mods(ob)
    if smooth:
        s = ob.modifiers.new("Smooth", "SMOOTH"); s.iterations = smooth; s.factor = smooth_factor
        apply_mods(ob)
    shade_smooth(ob)
    return ob


def carve(ob, cutters):
    for c in cutters:
        m = ob.modifiers.new("Carve", "BOOLEAN")
        m.operation = "DIFFERENCE"; m.object = c; m.solver = "EXACT"
        apply_mods(ob)
        bpy.data.objects.remove(c, do_unlink=True)
    shade_smooth(ob)
    return ob


def add(ob, others, voxel=None, name=None):
    """Union by voxel fuse (robust) of ob with others."""
    return fuse([ob] + list(others), voxel, name or ob.name)


def relax(ob, iterations=6, factor=0.5):
    s = ob.modifiers.new("Relax", "SMOOTH"); s.iterations = iterations; s.factor = factor
    return apply_mods(ob)


def displace(ob, strength, size, kind="CLOUDS", depth=2, coords="LOCAL", basis="BLENDER_ORIGINAL", subdiv=0):
    if subdiv:
        sd = ob.modifiers.new("Sub", "SUBSURF"); sd.levels = subdiv; sd.render_levels = subdiv
        apply_mods(ob)
    tx = bpy.data.textures.new(f"{ob.name}_{kind}", kind)
    if kind in ("CLOUDS", "VORONOI", "MUSGRAVE", "DISTORTED_NOISE"):
        tx.noise_scale = size
    if kind == "CLOUDS":
        tx.noise_depth = depth; tx.noise_basis = basis
    m = ob.modifiers.new("Disp", "DISPLACE")
    m.texture = tx; m.strength = strength; m.texture_coords = coords; m.mid_level = 0.5
    return apply_mods(ob)


def decimate(ob, target_tris):
    tris = sum(len(p.vertices) - 2 for p in ob.data.polygons)
    if tris > target_tris:
        m = ob.modifiers.new("Dec", "DECIMATE"); m.ratio = target_tris / tris; m.use_collapse_triangulate = True
        apply_mods(ob)
    shade_smooth(ob)
    return ob


def shade_smooth(ob):
    if ob.type == "MESH":
        ob.data.shade_smooth()


def set_mat(ob, m):
    ob.data.materials.clear(); ob.data.materials.append(m)
    for p in ob.data.polygons:
        p.material_index = 0
    return ob


def tris(ob):
    return sum(len(p.vertices) - 2 for p in ob.data.polygons)


# =================================================================== cloth
def cloth_drape(cloth, colliders, frames=50, pin_group=None, mass=0.25, tension=12, bending=0.4, quality=6,
                self_collide=False, shrink=0.0, thickness=0.004, gravity=None, air=1.0, pressure=0.0):
    sc = SC()
    for c in colliders:
        cm = c.modifiers.new("Collision", "COLLISION")
        c.collision.thickness_outer = thickness; c.collision.cloth_friction = 8
    m = cloth.modifiers.new("Cloth", "CLOTH")
    s = m.settings
    s.quality = quality; s.mass = mass; s.air_damping = air
    s.tension_stiffness = tension; s.compression_stiffness = tension; s.shear_stiffness = tension * 0.5
    s.bending_stiffness = bending
    s.shrink_min = shrink
    if pin_group:
        s.vertex_group_mass = pin_group; s.pin_stiffness = 1.0
    if pressure:
        s.use_pressure = True; s.uniform_pressure_force = pressure
    cs = m.collision_settings
    cs.distance_min = thickness; cs.use_self_collision = self_collide; cs.self_distance_min = thickness
    cs.collision_quality = 3
    if gravity is not None:
        sc.gravity = gravity
    m.point_cache.frame_start = 1; m.point_cache.frame_end = frames
    sc.frame_start, sc.frame_end = 1, frames
    for f in range(1, frames + 1):
        sc.frame_set(f)
    apply_mods(cloth)
    for c in colliders:
        for mm in list(c.modifiers):
            if mm.type == "COLLISION":
                c.modifiers.remove(mm)
    sc.frame_set(1)
    shade_smooth(cloth)
    return cloth


def grid_cloth(name, w, h, nx, ny, center=(0, 0, 0), rot=(0, 0, 0)):
    """Subdivided rectangle in the XY plane (before rot)."""
    bm = bmesh.new()
    vs = [[bm.verts.new(((i / nx - 0.5) * w, (j / ny - 0.5) * h, 0)) for i in range(nx + 1)] for j in range(ny + 1)]
    for j in range(ny):
        for i in range(nx):
            bm.faces.new((vs[j][i], vs[j][i + 1], vs[j + 1][i + 1], vs[j + 1][i]))
    uvl = bm.loops.layers.uv.new("SrcUV")
    for f in bm.faces:
        for l in f.loops:
            co = l.vert.co
            l[uvl].uv = (co.x / w + 0.5, co.y / h + 0.5)
    me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free()
    ob = new_obj(name, me); ob.location = center; ob.rotation_euler = rot
    return ob


def tube_cloth(name, radius, height, nr, nh, z0, scale=(1, 1)):
    bm = bmesh.new()
    rings = []
    for j in range(nh + 1):
        z = z0 + height * j / nh
        rings.append([bm.verts.new((radius * scale[0] * math.cos(2 * math.pi * i / nr), radius * scale[1] * math.sin(2 * math.pi * i / nr), z)) for i in range(nr)])
    for j in range(nh):
        for i in range(nr):
            bm.faces.new((rings[j][i], rings[j][(i + 1) % nr], rings[j + 1][(i + 1) % nr], rings[j + 1][i]))
    me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free()
    return new_obj(name, me)


def pin_where(ob, pred, name="pin"):
    g = ob.vertex_groups.new(name=name)
    idx = [v.index for v in ob.data.vertices if pred(ob.matrix_world @ v.co)]
    g.add(idx, 1.0, "REPLACE")
    return name


def solidify(ob, t, offset=0.0):
    m = ob.modifiers.new("Solid", "SOLIDIFY"); m.thickness = t; m.offset = offset
    return apply_mods(ob)


def subsurf(ob, levels=1):
    m = ob.modifiers.new("Sub", "SUBSURF"); m.levels = levels; m.render_levels = levels
    return apply_mods(ob)


# =================================================================== HQ materials (procedural, baked later)
def _bsdf(m):
    return m.node_tree.nodes["Principled BSDF"]


def hq_mat(name, c1, c2, rough=0.6, scale=6.0, bump=0.3, bump_scale=40, metal=0.0, kind="noise", sss=0.0,
           emit=None, emit_strength=0.0, grain_dir="Z", rough2=None):
    """Colour variation + micro bump. kind: noise | wood | weave | bone | stone | metal_worn | wax."""
    m = bpy.data.materials.get(name)
    if m:
        return m
    m = mat(name, c1, rough, metal=metal, sss=sss, emit=emit, emit_strength=emit_strength)
    nt = m.node_tree; b = _bsdf(m)
    tc = tex_coord(m, "Object")
    if kind == "wood":
        w = nt.nodes.new("ShaderNodeTexWave"); w.wave_type = "RINGS"; w.rings_direction = grain_dir
        w.inputs["Scale"].default_value = scale; w.inputs["Distortion"].default_value = 6; w.inputs["Detail"].default_value = 4
        nt.links.new(tc, w.inputs["Vector"]); fac = w.outputs["Fac"]
    elif kind == "weave":
        w = nt.nodes.new("ShaderNodeTexWave"); w.wave_type = "BANDS"; w.bands_direction = "DIAGONAL"
        w.inputs["Scale"].default_value = scale; nt.links.new(tc, w.inputs["Vector"]); fac = w.outputs["Fac"]
    else:
        n = nt.nodes.new("ShaderNodeTexNoise")
        n.inputs["Scale"].default_value = scale; n.inputs["Detail"].default_value = 10
        n.inputs["Roughness"].default_value = 0.6
        nt.links.new(tc, n.inputs["Vector"]); fac = n.outputs["Fac"]
    r = nt.nodes.new("ShaderNodeValToRGB")
    r.color_ramp.elements[0].position = 0.3; r.color_ramp.elements[0].color = (*c1, 1)
    r.color_ramp.elements[1].position = 0.75; r.color_ramp.elements[1].color = (*c2, 1)
    nt.links.new(fac, r.inputs["Fac"])
    nt.links.new(r.outputs["Color"], b.inputs["Base Color"])
    if rough2 is not None:
        rr = nt.nodes.new("ShaderNodeMapRange")
        rr.inputs["To Min"].default_value = rough; rr.inputs["To Max"].default_value = rough2
        nt.links.new(fac, rr.inputs["Value"]); nt.links.new(rr.outputs["Result"], b.inputs["Roughness"])
    if bump:
        n2 = nt.nodes.new("ShaderNodeTexNoise"); n2.inputs["Scale"].default_value = bump_scale
        n2.inputs["Detail"].default_value = 12
        nt.links.new(tc, n2.inputs["Vector"])
        if kind == "bone":   # pitted
            vo = nt.nodes.new("ShaderNodeTexVoronoi"); vo.inputs["Scale"].default_value = bump_scale * 2.5
            nt.links.new(tc, vo.inputs["Vector"])
            mx = nt.nodes.new("ShaderNodeMath"); mx.operation = "MULTIPLY_ADD"
            mx.inputs[1].default_value = 0.35
            nt.links.new(vo.outputs["Distance"], mx.inputs[0]); nt.links.new(n2.outputs["Fac"], mx.inputs[2])
            add_bump(m, mx.outputs[0], bump, 0.002)
        elif kind == "weave":
            add_bump(m, fac, bump, 0.002)
        else:
            add_bump(m, n2.outputs["Fac"], bump, 0.003)
    m.diffuse_color = (*c1, 1)
    return m


def library(M=None):
    M = M if M is not None else {}
    M["bone"] = hq_mat("HQ_Bone", (0.45, 0.37, 0.25), (0.8, 0.73, 0.58), 0.5, 7, 0.5, 60, kind="bone", sss=0.04, rough2=0.75)
    M["bone_old"] = hq_mat("HQ_Bone_Weathered", (0.42, 0.34, 0.24), (0.8, 0.73, 0.6), 0.6, 9, 0.7, 50, kind="bone", rough2=0.85)
    M["tooth"] = hq_mat("HQ_Tooth", (0.7, 0.62, 0.45), (0.88, 0.84, 0.72), 0.3, 20, 0.1, 80)
    M["horn"] = hq_mat("HQ_Horn", (0.04, 0.03, 0.025), (0.16, 0.12, 0.08), 0.35, 4, 0.5, 30, rough2=0.6)
    M["antler"] = hq_mat("HQ_Antler", (0.36, 0.27, 0.18), (0.72, 0.62, 0.48), 0.6, 5, 0.9, 25, kind="bone")
    M["wood"] = hq_mat("HQ_Wood_Dark", (0.06, 0.03, 0.015), (0.2, 0.1, 0.05), 0.45, 3, 0.25, 30, kind="wood", rough2=0.6)
    M["wood_raw"] = hq_mat("HQ_Wood_Raw", (0.3, 0.2, 0.12), (0.6, 0.45, 0.3), 0.75, 2, 0.5, 20, kind="wood")
    M["bark"] = hq_mat("HQ_Bark", (0.03, 0.025, 0.02), (0.14, 0.11, 0.09), 0.95, 3, 1.2, 12)
    M["stone"] = hq_mat("HQ_Stone", (0.13, 0.13, 0.13), (0.42, 0.41, 0.39), 0.85, 4, 0.9, 15, kind="stone")
    M["stone_dark"] = hq_mat("HQ_Stone_Dark", (0.04, 0.04, 0.045), (0.14, 0.13, 0.13), 0.8, 4, 0.8, 18)
    M["iron"] = hq_mat("HQ_Iron", (0.03, 0.028, 0.027), (0.18, 0.1, 0.06), 0.4, 6, 0.4, 40, metal=0.85, rough2=0.85)
    M["gold"] = hq_mat("HQ_Gold", (0.35, 0.22, 0.06), (0.75, 0.55, 0.2), 0.25, 6, 0.2, 40, metal=1.0, rough2=0.5)
    M["brass"] = M["gold"]
    M["robe_black"] = hq_mat("HQ_Robe_Black", (0.008, 0.008, 0.01), (0.03, 0.028, 0.03), 0.85, 120, 0.35, 300, kind="weave")
    M["robe_red"] = hq_mat("HQ_Robe_Crimson", (0.09, 0.004, 0.008), (0.22, 0.015, 0.02), 0.8, 120, 0.35, 300, kind="weave")
    M["robe_white"] = hq_mat("HQ_Robe_Bone", (0.5, 0.46, 0.4), (0.7, 0.66, 0.58), 0.85, 120, 0.35, 300, kind="weave")
    M["linen"] = hq_mat("HQ_Linen_Tan", (0.33, 0.24, 0.15), (0.52, 0.41, 0.28), 0.85, 140, 0.3, 300, kind="weave")
    M["velvet"] = hq_mat("HQ_Velvet_Purple", (0.04, 0.008, 0.05), (0.14, 0.03, 0.14), 0.9, 8, 0.15, 60)
    M["muslin"] = hq_mat("HQ_Muslin", (0.5, 0.42, 0.3), (0.7, 0.62, 0.48), 0.9, 150, 0.4, 300, kind="weave")
    M["burlap"] = hq_mat("HQ_Burlap", (0.3, 0.21, 0.1), (0.55, 0.42, 0.24), 0.95, 90, 0.8, 200, kind="weave")
    M["sheet"] = hq_mat("HQ_Sheet", (0.78, 0.8, 0.84), (0.92, 0.93, 0.95), 0.8, 140, 0.25, 300, kind="weave", sss=0.2)
    M["dress"] = hq_mat("HQ_Dress_Peach", (0.7, 0.55, 0.5), (0.88, 0.76, 0.72), 0.8, 140, 0.3, 300, kind="weave")
    M["skin"] = hq_mat("HQ_Mannequin", (0.68, 0.57, 0.5), (0.82, 0.72, 0.65), 0.35, 4, 0.05, 50, sss=0.05)
    M["pale"] = hq_mat("HQ_Pale_Skin", (0.6, 0.52, 0.48), (0.8, 0.72, 0.66), 0.45, 4, 0.08, 60, sss=0.1)
    M["hair"] = hq_mat("HQ_Hair_Auburn", (0.06, 0.025, 0.012), (0.25, 0.11, 0.05), 0.45, 30, 0.6, 120, kind="weave")
    M["hair_brown"] = hq_mat("HQ_Hair_Brown", (0.08, 0.05, 0.03), (0.3, 0.2, 0.11), 0.45, 30, 0.6, 120, kind="weave")
    M["wax_black"] = hq_mat("HQ_Wax_Black", (0.01, 0.01, 0.012), (0.05, 0.045, 0.05), 0.3, 10, 0.15, 30, rough2=0.5)
    M["wax"] = hq_mat("HQ_Wax_Ivory", (0.7, 0.6, 0.4), (0.9, 0.82, 0.62), 0.4, 10, 0.1, 30, sss=0.3)
    M["chitin"] = hq_mat("HQ_Chitin", (0.004, 0.004, 0.005), (0.05, 0.035, 0.03), 0.25, 9, 0.6, 70, rough2=0.6)
    M["pumpkin"] = hq_mat("HQ_Pumpkin", (0.5, 0.13, 0.01), (0.85, 0.36, 0.04), 0.5, 5, 0.3, 30)
    M["moss"] = hq_mat("HQ_Moss", (0.03, 0.05, 0.02), (0.15, 0.2, 0.08), 0.9, 25, 0.8, 60)
    M["dirt"] = hq_mat("HQ_Dirt", (0.022, 0.017, 0.012), (0.09, 0.07, 0.05), 0.95, 12, 1.0, 40)
    M["flesh"] = hq_mat("HQ_Flesh", (0.18, 0.03, 0.07), (0.45, 0.12, 0.2), 0.3, 6, 0.5, 40, sss=0.25)
    M["parchment"] = hq_mat("HQ_Parchment", (0.42, 0.32, 0.18), (0.66, 0.55, 0.36), 0.75, 6, 0.1, 40)
    M["cartilage"] = hq_mat("HQ_Cartilage", (0.5, 0.45, 0.38), (0.66, 0.6, 0.5), 0.35, 8, 0.1, 60, sss=0.1)
    M["socket"] = mat("HQ_Void", (0.0, 0.0, 0.0), 1.0)
    M["ink"] = mat("HQ_Ink", (0.02, 0.012, 0.008), 0.5)
    M["glass"] = bpy.data.materials.get("HQ_Glass") or mat("HQ_Glass", (0.9, 0.92, 0.95), 0.02)
    M["glass"].node_tree.nodes["Principled BSDF"].inputs["Transmission Weight"].default_value = 1.0
    M["mirror"] = mat("HQ_Mirror", (0.6, 0.6, 0.62), 0.05, metal=1.0)
    for k, col, s in (("glow_red", (1.0, 0.04, 0.02), 25), ("glow_green", (0.3, 1.0, 0.15), 20), ("flame", (1.0, 0.6, 0.2), 30),
                      ("glow_orange", (1.0, 0.4, 0.06), 20), ("glow_purple", (0.6, 0.2, 1.0), 15), ("brew", (0.35, 1.0, 0.12), 6),
                      ("sigil", (1.0, 0.04, 0.02), 14), ("lamp", (1.0, 0.65, 0.3), 5), ("coal", (1.0, 0.12, 0.02), 8),
                      ("throat", (1.0, 0.08, 0.04), 8), ("led_red", (1.0, 0.05, 0.03), 30)):
        M[k] = bpy.data.materials.get("HQ_" + k) or mat("HQ_" + k, (0.02, 0.02, 0.02), 0.6, emit=col, emit_strength=s)
    return M


# =================================================================== baking
def _emit_strength(m):
    b = m.node_tree.nodes.get("Principled BSDF") if m.node_tree else None
    if not b:
        return 0.0
    c = b.inputs["Emission Color"].default_value
    s = b.inputs["Emission Strength"].default_value
    return s if (c[0] + c[1] + c[2]) > 0.01 else 0.0


def bake_atlas(objs, name, size=1024, ao=True, margin=6, skip_transmission=True):
    """Bake every material on `objs` into one shared atlas and swap in a single PBR material."""
    sc = SC()
    sc.render.engine = "CYCLES"; sc.cycles.device = "CPU"
    objs = [o for o in objs if o.type == "MESH" and len(o.data.polygons)]
    keep = []
    if skip_transmission:
        def is_glass(o):
            return any(m and m.node_tree and m.node_tree.nodes.get("Principled BSDF") and
                       m.node_tree.nodes["Principled BSDF"].inputs["Transmission Weight"].default_value > 0.5 for m in o.data.materials)
        keep = [o for o in objs if is_glass(o)]
        objs = [o for o in objs if o not in keep]
    if not objs:
        return None
    allobjs = list(objs)
    seen, uniq = set(), []
    for o in objs:   # instanced meshes (shared data) are baked once and share their UV island
        if o.data.name in seen:
            continue
        seen.add(o.data.name); uniq.append(o)
    objs = uniq
    for o in objs:   # a fresh atlas UV layer (source layers such as "SrcUV" stay until the bake is done)
        old = o.data.uv_layers.get("BakeUV")
        if old:
            o.data.uv_layers.remove(old)
        uv = o.data.uv_layers.new(name="BakeUV")
        o.data.uv_layers.active = uv
        uv.active_render = True
    bpy.ops.object.select_all(action="DESELECT")
    for o in objs:
        o.hide_set(False); o.select_set(True)
    bpy.context.view_layer.objects.active = objs[0]
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_all(action="SELECT")
    bpy.ops.uv.smart_project(angle_limit=math.radians(62), island_margin=0.0015, scale_to_bounds=False)
    bpy.ops.uv.pack_islands(margin=0.002, rotate=True)
    bpy.ops.object.mode_set(mode="OBJECT")

    mats = []
    for o in objs:
        for m in o.data.materials:
            if m and m not in mats:
                mats.append(m)
    S = max([_emit_strength(m) for m in mats] + [0.0])
    imgs = {}
    def img(k, noncolor):
        im = bpy.data.images.new(f"{name}_{k}", size, size, alpha=False)
        im.colorspace_settings.name = "Non-Color" if noncolor else "sRGB"
        imgs[k] = im
        return im
    nodes = {}
    for m in mats:
        nt = m.node_tree
        n = nt.nodes.new("ShaderNodeTexImage"); n.name = "BAKE_TARGET"
        nt.nodes.active = n; nodes[m.name] = n

    def target(k):
        for m in mats:
            nodes[m.name].image = imgs[k]; m.node_tree.nodes.active = nodes[m.name]

    def emission_swap(socket_name, fallback):
        """Temporarily render an input of the BSDF as pure emission (colour/metal bakes)."""
        saved = []
        for m in mats:
            nt = m.node_tree; b = nt.nodes.get("Principled BSDF"); out = nt.nodes.get("Material Output")
            if not b or not out:
                continue
            em = nt.nodes.new("ShaderNodeEmission"); em.name = "BAKE_EMIT"
            inp = b.inputs[socket_name]
            if inp.is_linked:
                nt.links.new(inp.links[0].from_socket, em.inputs["Color"])
            else:
                v = inp.default_value
                em.inputs["Color"].default_value = (v[0], v[1], v[2], 1) if hasattr(v, "__len__") else (v, v, v, 1)
            old = out.inputs["Surface"].links[0].from_socket if out.inputs["Surface"].is_linked else None
            nt.links.new(em.outputs["Emission"], out.inputs["Surface"])
            saved.append((m, em, old))
        return saved

    def restore(saved):
        for m, em, old in saved:
            nt = m.node_tree; out = nt.nodes["Material Output"]
            if old:
                nt.links.new(old, out.inputs["Surface"])
            nt.nodes.remove(em)

    sc.cycles.samples = 1
    sc.render.bake.margin = margin
    # colour
    img("color", False); target("color")
    sv = emission_swap("Base Color", (0.5, 0.5, 0.5)); bpy.ops.object.bake(type="EMIT", margin=margin); restore(sv)
    # metallic
    img("metal", True); target("metal")
    sv = emission_swap("Metallic", 0.0); bpy.ops.object.bake(type="EMIT", margin=margin); restore(sv)
    # roughness
    img("rough", True); target("rough")
    bpy.ops.object.bake(type="ROUGHNESS", margin=margin)
    # normal (includes the procedural bump)
    img("normal", True); target("normal")
    bpy.ops.object.bake(type="NORMAL", normal_space="TANGENT", margin=margin)
    # emission, normalised by the strongest emitter
    if S > 0:
        saved = []
        for m in mats:
            b = m.node_tree.nodes.get("Principled BSDF")
            if b:
                saved.append((b, b.inputs["Emission Strength"].default_value))
                b.inputs["Emission Strength"].default_value = b.inputs["Emission Strength"].default_value / S
        img("emit", False); target("emit")
        bpy.ops.object.bake(type="EMIT", margin=margin)
        for b, v in saved:
            b.inputs["Emission Strength"].default_value = v
    if ao:
        img("ao", True); target("ao")
        sc.cycles.samples = 24
        bpy.ops.object.bake(type="AO", margin=margin)
        sc.cycles.samples = 1

    # compose: colour *= AO, ORM = (1, rough, metal)
    def arr(im):
        return np.array(im.pixels[:], dtype=np.float32).reshape(size, size, 4)
    col = arr(imgs["color"])
    if ao:
        a = arr(imgs["ao"])[..., :1]
        col[..., :3] *= (0.3 + 0.7 * a)
    imgs["color"].pixels.foreach_set(col.ravel())
    orm = np.ones((size, size, 4), np.float32)
    orm[..., 1] = arr(imgs["rough"])[..., 0]
    orm[..., 2] = arr(imgs["metal"])[..., 0]
    im_orm = bpy.data.images.new(f"{name}_orm", size, size, alpha=False); im_orm.colorspace_settings.name = "Non-Color"
    im_orm.pixels.foreach_set(orm.ravel())
    im_orm.scale(size // 2, size // 2)     # roughness/metal are low-frequency: half resolution
    for k in ("color", "normal", "emit"):
        if k in imgs:
            imgs[k].pack()
    im_orm.pack()

    # final material
    fm = bpy.data.materials.new(f"{name}_PBR"); fm.use_nodes = True
    nt = fm.node_tree; b = nt.nodes["Principled BSDF"]
    tcol = nt.nodes.new("ShaderNodeTexImage"); tcol.image = imgs["color"]
    nt.links.new(tcol.outputs["Color"], b.inputs["Base Color"])
    torm = nt.nodes.new("ShaderNodeTexImage"); torm.image = im_orm
    sep = nt.nodes.new("ShaderNodeSeparateColor")
    nt.links.new(torm.outputs["Color"], sep.inputs["Color"])
    nt.links.new(sep.outputs["Green"], b.inputs["Roughness"]); nt.links.new(sep.outputs["Blue"], b.inputs["Metallic"])
    tn = nt.nodes.new("ShaderNodeTexImage"); tn.image = imgs["normal"]
    nm = nt.nodes.new("ShaderNodeNormalMap")
    nt.links.new(tn.outputs["Color"], nm.inputs["Color"]); nt.links.new(nm.outputs["Normal"], b.inputs["Normal"])
    if S > 0:
        te = nt.nodes.new("ShaderNodeTexImage"); te.image = imgs["emit"]
        nt.links.new(te.outputs["Color"], b.inputs["Emission Color"])
        b.inputs["Emission Strength"].default_value = S
    for o in objs:
        set_mat(o, fm)
        for l in [l for l in o.data.uv_layers if l.name != "BakeUV"]:
            o.data.uv_layers.remove(l)
        o.data.uv_layers["BakeUV"].name = "UVMap"
    for o in allobjs:
        if o.data.materials and o.data.materials[0] is not fm:
            set_mat(o, fm)
    for m in mats:
        n = m.node_tree.nodes.get("BAKE_TARGET")
        if n:
            m.node_tree.nodes.remove(n)
    return fm


def weights_by_bones(ob, bones, names, power=4.0, top=2):
    """Smooth skin weights: each vertex is shared between its nearest bone segments (inverse distance)."""
    import numpy as np
    P = np.array([ob.matrix_world @ v.co for v in ob.data.vertices], np.float32)
    D = []
    for n in names:
        a, b = np.array(bones[n][0], np.float32), np.array(bones[n][1], np.float32)
        ab = b - a; t = np.clip(((P - a) @ ab) / max(float(ab @ ab), 1e-9), 0, 1)
        D.append(np.linalg.norm(P - (a + np.outer(t, ab)), axis=1))
    D = np.stack(D, 1) + 1e-4
    idx = np.argsort(D, 1)[:, :top]
    w = 1.0 / np.take_along_axis(D, idx, 1) ** power
    w /= w.sum(1, keepdims=True)
    groups = {n: (ob.vertex_groups.get(n) or ob.vertex_groups.new(name=n)) for n in names}
    for j in range(top):
        for gi, n in enumerate(names):
            sel = np.where(idx[:, j] == gi)[0]
            for v, ww in zip(sel.tolist(), w[sel, j].tolist()):
                if ww > 0.01:
                    groups[n].add([v], ww, "ADD")


def assign_group(ob, name):
    g = ob.vertex_groups.get(name) or ob.vertex_groups.new(name=name)
    g.add(list(range(len(ob.data.vertices))), 1.0, "REPLACE")


def join(objs, name):
    bpy.ops.object.select_all(action="DESELECT")
    for o in objs:
        o.select_set(True)
    bpy.context.view_layer.objects.active = objs[0]
    bpy.ops.object.join()
    ob = bpy.context.view_layer.objects.active
    ob.name = name
    return ob


def instance(ob, name, M4):
    """Linked duplicate sharing ob's mesh data, placed by a 4x4 world matrix."""
    o = bpy.data.objects.new(name, ob.data)
    SC().collection.objects.link(o)
    o.matrix_world = M4
    return o


def image_mat(name, path, rough=0.7, emit_path=None, emit_color=(1, 0.05, 0.02), emit_strength=0.0, uv="SrcUV",
              bump=0.0, metal=0.0):
    """Material whose colour comes from an image on a named UV layer (baked into the atlas later)."""
    m = bpy.data.materials.new(name); m.use_nodes = True
    nt = m.node_tree; b = nt.nodes["Principled BSDF"]
    uvn = nt.nodes.new("ShaderNodeUVMap"); uvn.uv_map = uv
    tx = nt.nodes.new("ShaderNodeTexImage"); tx.image = bpy.data.images.load(path); tx.interpolation = "Cubic"
    nt.links.new(uvn.outputs["UV"], tx.inputs["Vector"])
    nt.links.new(tx.outputs["Color"], b.inputs["Base Color"])
    b.inputs["Roughness"].default_value = rough
    b.inputs["Metallic"].default_value = metal
    if emit_path:
        te = nt.nodes.new("ShaderNodeTexImage"); te.image = bpy.data.images.load(emit_path)
        te.image.colorspace_settings.name = "Non-Color"
        nt.links.new(uvn.outputs["UV"], te.inputs["Vector"])
        mix = nt.nodes.new("ShaderNodeMix"); mix.data_type = "RGBA"; mix.blend_type = "MULTIPLY"
        mix.inputs["Factor"].default_value = 1.0
        nt.links.new(te.outputs["Color"], mix.inputs["A"])
        mix.inputs["B"].default_value = (*emit_color, 1)
        nt.links.new(mix.outputs["Result"], b.inputs["Emission Color"])
        b.inputs["Emission Strength"].default_value = emit_strength
    if bump:
        tc = tex_coord(m, "Object")
        n2 = nt.nodes.new("ShaderNodeTexNoise"); n2.inputs["Scale"].default_value = 300
        nt.links.new(tc, n2.inputs["Vector"])
        add_bump(m, n2.outputs["Fac"], bump, 0.002)
    m.diffuse_color = (0.5, 0.5, 0.5, 1)
    return m


def planar_uv(ob, axis="Z", name="SrcUV"):
    """Simple planar UVs (normalised to the object's bounds) for image materials on boards and decals."""
    import numpy as np
    me = ob.data
    uv = me.uv_layers.get(name) or me.uv_layers.new(name=name)
    co = np.array([v.co for v in me.vertices])
    a, b = {"Z": (0, 1), "Y": (0, 2), "X": (1, 2)}[axis]
    lo, hi = co.min(0), co.max(0)
    for l in me.loops:
        p = co[l.vertex_index]
        uv.data[l.index].uv = ((p[a] - lo[a]) / (hi[a] - lo[a] + 1e-9), (p[b] - lo[b]) / (hi[b] - lo[b] + 1e-9))


def engraved_mat(name, mask_path, c1, c2, rough=0.85, depth=0.6, uv="SrcUV", front_only=True, kind="stone"):
    """Stone with carved lettering from a mask image (front faces only): the letters are darker and
    recessed through a bump, which the normal bake captures."""
    m = hq_mat(name + "_base", c1, c2, rough, 4, 0.8, 18, kind=kind).copy()
    m.name = name
    nt = m.node_tree; b = nt.nodes["Principled BSDF"]
    uvn = nt.nodes.new("ShaderNodeUVMap"); uvn.uv_map = uv
    tx = nt.nodes.new("ShaderNodeTexImage"); tx.image = bpy.data.images.load(mask_path)
    tx.image.colorspace_settings.name = "Non-Color"; tx.extension = "CLIP"
    nt.links.new(uvn.outputs["UV"], tx.inputs["Vector"])
    fac = tx.outputs["Color"]
    if front_only:
        geo = nt.nodes.new("ShaderNodeNewGeometry")
        sep = nt.nodes.new("ShaderNodeSeparateXYZ"); nt.links.new(geo.outputs["Normal"], sep.inputs["Vector"])
        mr = nt.nodes.new("ShaderNodeMapRange"); mr.inputs["From Min"].default_value = -0.6; mr.inputs["From Max"].default_value = -0.85
        nt.links.new(sep.outputs["Y"], mr.inputs["Value"])
        mul = nt.nodes.new("ShaderNodeMath"); mul.operation = "MULTIPLY"
        bw = nt.nodes.new("ShaderNodeRGBToBW"); nt.links.new(fac, bw.inputs["Color"])
        nt.links.new(bw.outputs["Val"], mul.inputs[0]); nt.links.new(mr.outputs["Result"], mul.inputs[1])
        fac = mul.outputs[0]
    # darken letters
    mix = nt.nodes.new("ShaderNodeMix"); mix.data_type = "RGBA"; mix.blend_type = "MULTIPLY"
    nt.links.new(fac, mix.inputs["Factor"])
    src = b.inputs["Base Color"].links[0].from_socket
    nt.links.new(src, mix.inputs["A"]); mix.inputs["B"].default_value = (0.25, 0.24, 0.23, 1)
    nt.links.new(mix.outputs["Result"], b.inputs["Base Color"])
    inv = nt.nodes.new("ShaderNodeMath"); inv.operation = "SUBTRACT"; inv.inputs[0].default_value = 1.0
    nt.links.new(fac, inv.inputs[1])
    bump2 = nt.nodes.new("ShaderNodeBump"); bump2.inputs["Strength"].default_value = depth; bump2.inputs["Distance"].default_value = 0.004
    nt.links.new(inv.outputs[0], bump2.inputs["Height"])
    old = b.inputs["Normal"].links[0].from_socket if b.inputs["Normal"].is_linked else None
    if old:
        nt.links.new(old, bump2.inputs["Normal"])
    nt.links.new(bump2.outputs["Normal"], b.inputs["Normal"])
    return m
