"""Helper toolkit for the Helloween scene (Blender 5.x, bpy)."""
import bpy, bmesh, math, random
from mathutils import Vector, Matrix, Quaternion, Euler

V = Vector

# ---------------------------------------------------------------- collections
def coll(name, parent=None):
    c = bpy.data.collections.get(name) or bpy.data.collections.new(name)
    p = parent or bpy.context.scene.collection
    if c.name not in [x.name for x in p.children]:
        p.children.link(c)
    return c

def link(ob, c):
    for uc in list(ob.users_collection):
        uc.objects.unlink(ob)
    c.objects.link(ob)
    return ob

# ---------------------------------------------------------------- materials
def _bsdf(m):
    return m.node_tree.nodes.get("Principled BSDF")

def mat(name, color=(0.8, 0.8, 0.8), rough=0.5, metal=0.0, emit=None, emit_strength=0.0,
        sss=0.0, sheen=0.0, coat=0.0, alpha=1.0):
    m = bpy.data.materials.get(name)
    if m:
        return m
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    b = _bsdf(m)
    b.inputs["Base Color"].default_value = (*color, 1)
    b.inputs["Roughness"].default_value = rough
    b.inputs["Metallic"].default_value = metal
    if sss:
        b.inputs["Subsurface Weight"].default_value = sss
        b.inputs["Subsurface Radius"].default_value = (0.05, 0.03, 0.02)
    if sheen:
        b.inputs["Sheen Weight"].default_value = sheen
    if coat:
        b.inputs["Coat Weight"].default_value = coat
    if emit:
        b.inputs["Emission Color"].default_value = (*emit, 1)
        b.inputs["Emission Strength"].default_value = emit_strength
    m.diffuse_color = (*color, 1)
    return m

def tex_coord(m, out="Object"):
    nt = m.node_tree
    tc = nt.nodes.get("TexCoord") or nt.nodes.new("ShaderNodeTexCoord")
    tc.name = "TexCoord"
    return tc.outputs[out]

def add_bump(m, height_socket, strength=0.3, distance=0.01):
    nt = m.node_tree
    bump = nt.nodes.new("ShaderNodeBump")
    bump.inputs["Strength"].default_value = strength
    bump.inputs["Distance"].default_value = distance
    nt.links.new(height_socket, bump.inputs["Height"])
    nt.links.new(bump.outputs["Normal"], _bsdf(m).inputs["Normal"])
    return bump

def wave_bump(m, scale, direction="Z", profile="SAW", strength=0.4, distance=0.01, coord="Object"):
    nt = m.node_tree
    w = nt.nodes.new("ShaderNodeTexWave")
    w.wave_type = "BANDS"
    w.bands_direction = direction
    w.wave_profile = profile
    w.inputs["Scale"].default_value = scale
    nt.links.new(tex_coord(m, coord), w.inputs["Vector"])
    add_bump(m, w.outputs["Fac"], strength, distance)
    return w

def noise_bump(m, scale=20, strength=0.3, distance=0.01, detail=6):
    nt = m.node_tree
    n = nt.nodes.new("ShaderNodeTexNoise")
    n.inputs["Scale"].default_value = scale
    n.inputs["Detail"].default_value = detail
    nt.links.new(tex_coord(m), n.inputs["Vector"])
    add_bump(m, n.outputs["Fac"], strength, distance)
    return n

def noise_color(m, c1, c2, scale=5, lo=0.35, hi=0.65):
    nt = m.node_tree
    n = nt.nodes.new("ShaderNodeTexNoise")
    n.inputs["Scale"].default_value = scale
    n.inputs["Detail"].default_value = 8
    nt.links.new(tex_coord(m), n.inputs["Vector"])
    r = nt.nodes.new("ShaderNodeValToRGB")
    r.color_ramp.elements[0].position = lo
    r.color_ramp.elements[0].color = (*c1, 1)
    r.color_ramp.elements[1].position = hi
    r.color_ramp.elements[1].color = (*c2, 1)
    nt.links.new(n.outputs["Fac"], r.inputs["Fac"])
    nt.links.new(r.outputs["Color"], _bsdf(m).inputs["Base Color"])
    return n

def emission_mat(name, color, strength):
    return mat(name, color=(0.02, 0.02, 0.02), rough=0.6, emit=color, emit_strength=strength)

def interior_mat(name, color, strength, dark=(0.05, 0.03, 0.02)):
    """Lit interior seen through a window: warm glow broken up by soft silhouettes."""
    m = bpy.data.materials.get(name)
    if m:
        return m
    m = mat(name, color=(0.02, 0.02, 0.02), rough=0.8)
    nt = m.node_tree
    b = _bsdf(m)
    n = nt.nodes.new("ShaderNodeTexNoise")
    n.inputs["Scale"].default_value = 0.9
    n.inputs["Detail"].default_value = 1
    nt.links.new(tex_coord(m), n.inputs["Vector"])
    r = nt.nodes.new("ShaderNodeValToRGB")
    r.color_ramp.elements[0].position = 0.25
    r.color_ramp.elements[0].color = tuple(c * 0.45 for c in color) + (1,)
    r.color_ramp.elements[1].position = 0.75
    r.color_ramp.elements[1].color = (*color, 1)
    nt.links.new(n.outputs["Fac"], r.inputs["Fac"])
    nt.links.new(r.outputs["Color"], b.inputs["Emission Color"])
    b.inputs["Emission Strength"].default_value = strength
    return m

# ---------------------------------------------------------------- mesh builder
class MB:
    """bmesh-based builder: primitives in world/local coords, tagged with material + vertex group."""
    def __init__(self):
        self.bm = bmesh.new()
        self.dl = self.bm.verts.layers.deform.verify()
        self.mi = 0
        self.gi = None
        self.smooth = True

    def _tag(self, verts):
        faces = {f for v in verts for f in v.link_faces}
        for f in faces:
            f.material_index = self.mi
            f.smooth = self.smooth
        if self.gi is not None:
            for v in verts:
                v[self.dl][self.gi] = 1.0
        return verts

    def cyl(self, p1, p2, r1, r2=None, segs=10, cap=True):
        p1, p2 = V(p1), V(p2)
        d = p2 - p1
        L = d.length
        if L < 1e-6:
            return []
        q = V((0, 0, 1)).rotation_difference(d.normalized())
        M = Matrix.Translation((p1 + p2) / 2) @ q.to_matrix().to_4x4()
        r = bmesh.ops.create_cone(self.bm, cap_ends=cap, segments=segs, radius1=r1,
                                  radius2=r1 if r2 is None else r2, depth=L, matrix=M)
        return self._tag(r["verts"])

    def sphere(self, c, r, scale=(1, 1, 1), rot=(0, 0, 0), segs=(14, 9)):
        M = (Matrix.Translation(V(c)) @ Euler(rot).to_matrix().to_4x4()
             @ Matrix.Diagonal((*scale, 1)))
        res = bmesh.ops.create_uvsphere(self.bm, u_segments=segs[0], v_segments=segs[1],
                                        radius=r, matrix=M)
        return self._tag(res["verts"])

    def box(self, c, size, rot=(0, 0, 0)):
        M = (Matrix.Translation(V(c)) @ Euler(rot).to_matrix().to_4x4()
             @ Matrix.Diagonal((*size, 1)))
        res = bmesh.ops.create_cube(self.bm, size=1.0, matrix=M)
        f = {f for v in res["verts"] for f in v.link_faces}
        sm, self.smooth = self.smooth, False
        out = self._tag(res["verts"])
        self.smooth = sm
        return out

    def box_pts(self, lo, hi):
        lo, hi = V(lo), V(hi)
        return self.box((lo + hi) / 2, hi - lo)

    def torus(self, c, R, r, scale=(1, 1, 1), rot=(0, 0, 0), segs=(24, 6), arc=2 * math.pi):
        M = (Matrix.Translation(V(c)) @ Euler(rot).to_matrix().to_4x4()
             @ Matrix.Diagonal((*scale, 1)))
        bm = self.bm
        closed = abs(arc - 2 * math.pi) < 1e-6
        n_u = segs[0] if closed else segs[0] + 1
        rings = []
        for i in range(n_u):
            a = arc * i / segs[0]
            ring = []
            for j in range(segs[1]):
                b = 2 * math.pi * j / segs[1]
                p = V(((R + r * math.cos(b)) * math.cos(a), (R + r * math.cos(b)) * math.sin(a),
                       r * math.sin(b)))
                ring.append(bm.verts.new(M @ p))
            rings.append(ring)
        verts = [v for ring in rings for v in ring]
        for i in range(segs[0] if closed else segs[0]):
            r1, r2 = rings[i], rings[(i + 1) % n_u]
            for j in range(segs[1]):
                bm.faces.new((r1[j], r2[j], r2[(j + 1) % segs[1]], r1[(j + 1) % segs[1]]))
        return self._tag(verts)

    def lathe(self, profile, segs=24, c=(0, 0, 0), rmod=None, cap_bottom=False, cap_top=False,
              scale=(1, 1)):
        """profile: list of (r, z). rmod(theta, z, r, k)->r for folds/flutes."""
        bm = self.bm
        c = V(c)
        rings = []
        for k, (r, z) in enumerate(profile):
            ring = []
            for i in range(segs):
                t = 2 * math.pi * i / segs
                rr = rmod(t, z, r, k) if rmod else r
                ring.append(bm.verts.new(c + V((rr * math.cos(t) * scale[0],
                                                rr * math.sin(t) * scale[1], z))))
            rings.append(ring)
        for k in range(len(rings) - 1):
            a, b = rings[k], rings[k + 1]
            for i in range(segs):
                bm.faces.new((a[i], a[(i + 1) % segs], b[(i + 1) % segs], b[i]))
        if cap_bottom:
            bm.faces.new(list(reversed(rings[0])))
        if cap_top:
            bm.faces.new(rings[-1])
        return self._tag([v for ring in rings for v in ring])

    def quad(self, pts):
        vs = [self.bm.verts.new(V(p)) for p in pts]
        self.bm.faces.new(vs)
        sm, self.smooth = self.smooth, False
        self._tag(vs)
        self.smooth = sm
        return vs

    def obj(self, name, mats, c=None, groups=()):
        me = bpy.data.meshes.new(name)
        self.bm.normal_update()
        self.bm.to_mesh(me)
        self.bm.free()
        for m in mats:
            me.materials.append(m)
        ob = bpy.data.objects.new(name, me)
        for g in groups:
            ob.vertex_groups.new(name=g)
        (c or bpy.context.scene.collection).objects.link(ob)
        return ob

    def mesh(self, name, mats):
        me = bpy.data.meshes.new(name)
        self.bm.normal_update()
        self.bm.to_mesh(me)
        self.bm.free()
        for m in mats:
            me.materials.append(m)
        return me

# ---------------------------------------------------------------- curves
def tube_curve(name, splines, bevel=0.02, mats=(), c=None, res=4):
    """splines: list of [(co, radius), ...]. Returns curve object (editable, malleable)."""
    cu = bpy.data.curves.new(name, "CURVE")
    cu.dimensions = "3D"
    cu.bevel_depth = bevel
    cu.bevel_resolution = res
    cu.use_fill_caps = True
    for pts in splines:
        sp = cu.splines.new("NURBS")
        sp.points.add(len(pts) - 1)
        for p, (co, rad) in zip(sp.points, pts):
            p.co = (*co, 1)
            p.radius = rad
        sp.use_endpoint_u = True
        sp.order_u = min(4, len(pts))
        sp.use_smooth = True
    for m in mats:
        cu.materials.append(m)
    ob = bpy.data.objects.new(name, cu)
    (c or bpy.context.scene.collection).objects.link(ob)
    return ob

def look_at(ob, target, up="Y", track="-Z"):
    d = V(target) - ob.location
    ob.rotation_euler = d.to_track_quat(track, up).to_euler()

def empty(name, loc=(0, 0, 0), c=None, size=0.3, kind="PLAIN_AXES"):
    e = bpy.data.objects.new(name, None)
    e.empty_display_type = kind
    e.empty_display_size = size
    e.location = loc
    (c or bpy.context.scene.collection).objects.link(e)
    return e

def parent_keep(child, parent):
    child.parent = parent
    child.matrix_parent_inverse = parent.matrix_world.inverted()
