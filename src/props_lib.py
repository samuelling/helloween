"""Prop arsenal for the Helloween decorator: each prop is built procedurally in Blender, exported as its own
GLB (rigged props keep their armature so the web articulator can pose them) with a Cycles thumbnail and
an entry in catalog.json.

python3 props_lib.py <out_dir> [prop_id ...]
"""
import sys, os, math, json, random, traceback
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import bpy, bmesh
from mathutils import Vector as V, Matrix, Euler
from lib import *
import build_props as BP

OUT = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, "props_out")
ONLY = set(sys.argv[2:])
os.makedirs(os.path.join(OUT, "thumbs"), exist_ok=True)

# ===================================================================== shared
def fresh():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    M = {}
    BP.materials(M)
    M["chitin"] = mat("Chitin_Black", (0.015, 0.013, 0.014), 0.35, coat=0.6)
    M["eye_red"] = emission_mat("Eye_Glow_Red", (1.0, 0.05, 0.02), 30)
    M["eye_green"] = emission_mat("Eye_Glow_Green", (0.3, 1.0, 0.15), 25)
    M["eye_purple"] = emission_mat("Glow_Purple", (0.6, 0.2, 1.0), 20)
    M["glow_orange"] = emission_mat("Glow_Orange", (1.0, 0.45, 0.08), 25)
    M["brew"] = emission_mat("Witch_Brew", (0.35, 1.0, 0.12), 6)
    M["iron"] = mat("Wrought_Iron", (0.02, 0.02, 0.022), 0.45, metal=0.8)
    M["stone_grave"] = mat("Grave_Stone", (0.34, 0.34, 0.33), 0.85)
    M["wood_dark"] = mat("Coffin_Wood", (0.12, 0.05, 0.025), 0.5, coat=0.4)
    M["velvet"] = mat("Coffin_Velvet", (0.35, 0.01, 0.03), 0.9, sheen=0.6)
    M["burlap"] = mat("Burlap", (0.48, 0.36, 0.2), 0.95)
    M["straw"] = mat("Straw", (0.7, 0.55, 0.22), 0.8)
    M["flannel"] = mat("Flannel_Red", (0.35, 0.05, 0.04), 0.9)
    M["cloth_black"] = mat("Cloak_Black", (0.012, 0.012, 0.014), 0.8, sheen=0.4)
    M["leather"] = mat("Plague_Leather", (0.32, 0.22, 0.14), 0.55)
    M["sheet"] = mat("Ghost_Sheet_Glow", (0.9, 0.92, 0.95), 0.8, sss=0.3, emit=(0.6, 0.75, 1.0), emit_strength=0.4)
    M["bark"] = mat("Dead_Bark", (0.07, 0.055, 0.045), 0.95)
    M["eyeball"] = mat("Eyeball_White", (0.92, 0.88, 0.82), 0.15, sss=0.15)
    M["iris"] = emission_mat("Iris_Amber", (1.0, 0.55, 0.05), 6)
    M["flesh"] = mat("Tentacle_Flesh", (0.35, 0.08, 0.16), 0.35, sss=0.25, coat=0.5)
    M["sucker"] = mat("Tentacle_Sucker", (0.85, 0.6, 0.6), 0.4)
    M["gum"] = mat("Gum_Red", (0.45, 0.03, 0.05), 0.3, coat=0.7)
    M["throat"] = emission_mat("Throat_Glow", (1.0, 0.08, 0.04), 8)
    M["moth"] = mat("Moth_Wing", (0.35, 0.27, 0.2), 0.8)
    M["moth_eye"] = mat("Moth_Eyespot", (0.04, 0.03, 0.03), 0.5)
    M["crystal"] = mat("Crystal_Ball", (0.6, 0.35, 0.95), 0.05, emit=(0.55, 0.2, 1.0), emit_strength=3)
    M["brass"] = mat("Brass", (0.55, 0.38, 0.12), 0.3, metal=1.0)
    M["mulch"] = mat("Dirt_Mound", (0.06, 0.035, 0.02), 0.95)
    M["web"] = mat("Web_Silk", (0.9, 0.9, 0.92), 0.6, emit=(0.6, 0.6, 0.7), emit_strength=0.15)
    return M


def root_empty(pid):
    return empty(pid, (0, 0, 0), bpy.context.scene.collection, 0.3)


def parent_all(root):
    for ob in bpy.context.scene.objects:
        if ob is not root and ob.parent is None:
            ob.parent = root


def make_rig(name, bones, order):
    arm = bpy.data.armatures.new(name + "_Armature")
    ob = bpy.data.objects.new(name + "_Rig", arm)
    bpy.context.scene.collection.objects.link(ob)
    bpy.context.view_layer.objects.active = ob
    bpy.ops.object.mode_set(mode="EDIT")
    for n in order:
        h, t, p = bones[n]
        eb = arm.edit_bones.new(n)
        eb.head, eb.tail = h, t
        if p:
            eb.parent = arm.edit_bones[p]
            eb.use_connect = (V(bones[p][1]) - V(h)).length < 1e-4
    bpy.ops.object.mode_set(mode="OBJECT")
    return ob


def skin(mesh_ob, rig, order):
    for n in order:
        if n not in mesh_ob.vertex_groups:
            mesh_ob.vertex_groups.new(name=n)
    mesh_ob.parent = rig
    m = mesh_ob.modifiers.new("Armature", "ARMATURE")
    m.object = rig


def rigged_mb(order):
    mb = MB()
    G = {n: i for i, n in enumerate(order)}
    return mb, (lambda n: setattr(mb, "gi", G[n]))


def text_mesh(body, size, depth, m, loc, rot=(math.radians(90), 0, 0), name="Text"):
    cu = bpy.data.curves.new(name, "FONT")
    cu.body = body
    cu.size = size
    cu.extrude = depth
    cu.align_x = "CENTER"
    cu.materials.append(m)
    ob = bpy.data.objects.new(name, cu)
    bpy.context.scene.collection.objects.link(ob)
    ob.location, ob.rotation_euler = loc, rot
    return ob


# ===================================================================== rigged props
def p_skeleton(M):
    root = root_empty("skeleton")
    me = BP.skeleton_mesh(M)
    rig = make_rig("Skeleton", BP.BONES, BP.ORDER)
    ob = bpy.data.objects.new("Skeleton_Body", me)
    bpy.context.scene.collection.objects.link(ob)
    skin(ob, rig, BP.ORDER)
    rig.parent = root
    return {"name": "Skeleton", "cat": "Bones", "rig": "human",
            "desc": "Life-size, fully articulated. Pick a preset pose or rotate any joint."}


def p_dog(M):
    root = root_empty("skeleton_dog")
    B = {"hips": ((0, 0.3, 0.55), (0, 0.14, 0.58), None),
         "spine": ((0, 0.14, 0.58), (0, -0.12, 0.6), "hips"),
         "chest": ((0, -0.12, 0.6), (0, -0.3, 0.62), "spine"),
         "neck": ((0, -0.3, 0.62), (0, -0.42, 0.8), "chest"),
         "head": ((0, -0.42, 0.8), (0, -0.66, 0.76), "neck"),
         "tail1": ((0, 0.32, 0.56), (0, 0.48, 0.62), "hips"),
         "tail2": ((0, 0.48, 0.62), (0, 0.64, 0.7), "tail1"),
         "tail3": ((0, 0.64, 0.7), (0, 0.8, 0.8), "tail2")}
    for s, sx in (("L", 1), ("R", -1)):
        x = 0.09 * sx
        B.update({f"front_upper.{s}": ((x, -0.27, 0.55), (x, -0.29, 0.33), "chest"),
                  f"front_lower.{s}": ((x, -0.29, 0.33), (x, -0.27, 0.08), f"front_upper.{s}"),
                  f"front_paw.{s}": ((x, -0.27, 0.08), (x, -0.35, 0.02), f"front_lower.{s}"),
                  f"hind_upper.{s}": ((x, 0.28, 0.52), (x, 0.2, 0.32), "hips"),
                  f"hind_lower.{s}": ((x, 0.2, 0.32), (x, 0.33, 0.09), f"hind_upper.{s}"),
                  f"hind_paw.{s}": ((x, 0.33, 0.09), (x, 0.26, 0.02), f"hind_lower.{s}")})
    order = list(B)
    mb, g = rigged_mb(order)
    g("head")
    mb.sphere((0, -0.47, 0.82), 0.07, (0.85, 1.1, 0.8))
    mb.cyl((0, -0.5, 0.8), (0, -0.68, 0.76), 0.04, 0.022, segs=10)
    mb.box((0, -0.58, 0.735), (0.05, 0.16, 0.018))
    for sx in (-1, 1):
        mb.cyl((0.03 * sx, -0.66, 0.77), (0.03 * sx, -0.665, 0.73), 0.006, 0.001, segs=5)  # canines
        mb.cyl((0.04 * sx, -0.44, 0.86), (0.06 * sx, -0.42, 0.95), 0.02, 0.004, segs=6)    # ears (bone nubs)
    mb.mi = 1
    for sx in (-1, 1):
        mb.sphere((0.035 * sx, -0.53, 0.82), 0.02)
    mb.mi = 0
    chain = [("neck", 0.62, 0.8, -0.3, -0.42, 5), ("chest", 0.6, 0.62, -0.12, -0.3, 4),
             ("spine", 0.58, 0.6, 0.14, -0.12, 6), ("hips", 0.55, 0.58, 0.3, 0.14, 4)]
    for bone, z0, z1, y0, y1, n in chain:
        g(bone)
        for i in range(n):
            f = (i + 0.5) / n
            mb.cyl((0, y0 + (y1 - y0) * f - 0.012, z0 + (z1 - z0) * f), (0, y0 + (y1 - y0) * f + 0.012, z0 + (z1 - z0) * f),
                   0.022, segs=8)
            mb.box((0, y0 + (y1 - y0) * f, z0 + (z1 - z0) * f + 0.03), (0.008, 0.015, 0.03))
    g("chest")
    for i in range(7):
        y = -0.28 + i * 0.05
        R = 0.1 + 0.03 * math.sin(i / 6 * math.pi)
        mb.torus((0, y, 0.6 - R * 0.9), R, 0.007, (0.75, 1, 1.1), (0, math.radians(90), math.radians(90)), segs=(20, 4))
    g("hips")
    mb.torus((0, 0.28, 0.52), 0.06, 0.016, (1.1, 0.6, 1), (math.radians(70), 0, 0), segs=(16, 5))
    for i, t in enumerate(("tail1", "tail2", "tail3")):
        g(t)
        h, tl, _ = B[t]
        mb.cyl(h, tl, 0.014 - 0.003 * i, 0.011 - 0.003 * i, segs=6)
    for s, sx in (("L", 1), ("R", -1)):
        for part in ("front_upper", "front_lower", "front_paw", "hind_upper", "hind_lower", "hind_paw"):
            g(f"{part}.{s}")
            h, tl, _ = B[f"{part}.{s}"]
            r = 0.016 if "paw" not in part else 0.012
            mb.sphere(h, r * 1.5)
            mb.cyl(h, tl, r, r * 0.8, segs=7)
    me = mb.mesh("Dog_Bones", [M["bone"], M["eye_red"]])
    ob = bpy.data.objects.new("Dog_Body", me)
    bpy.context.scene.collection.objects.link(ob)
    rig = make_rig("Dog", B, order)
    skin(ob, rig, order)
    rig.parent = root
    return {"name": "Skeleton hound", "cat": "Bones", "rig": "dog",
            "desc": "Bony dog with glowing eyes. Articulated spine, tail and legs."}


def p_spider(M):
    root = root_empty("giant_spider")
    B = {"body": ((0, 0.25, 0.55), (0, -0.25, 0.55), None)}
    legs = []
    for s, sx in (("L", 1), ("R", -1)):
        for k, a in enumerate((30, 65, 105, 140)):
            ar = math.radians(a)
            d = V((math.sin(ar) * sx, -math.cos(ar), 0))
            r0 = V((0, -0.12, 0.5)) + d * 0.18
            knee = r0 + d * 0.65 + V((0, 0, 0.5))
            ank = r0 + d * 1.25 + V((0, 0, 0.25))
            tip = r0 + d * 1.55 + V((0, 0, -0.48))
            n = f"leg{k}.{s}"
            B[n + "_a"] = (tuple(r0), tuple(knee), "body")
            B[n + "_b"] = (tuple(knee), tuple(ank), n + "_a")
            B[n + "_c"] = (tuple(ank), tuple(tip), n + "_b")
            legs.append(n)
    order = list(B)
    mb, g = rigged_mb(order)
    g("body")
    mb.mi = 0
    mb.sphere((0, 0.5, 0.65), 0.45, (0.85, 1.15, 0.8), segs=(24, 16))
    mb.sphere((0, -0.12, 0.52), 0.24, (1, 1.1, 0.75), segs=(18, 12))
    mb.sphere((0, 0.18, 0.56), 0.1)
    for sx in (-1, 1):
        mb.cyl((0.05 * sx, -0.32, 0.5), (0.04 * sx, -0.4, 0.33), 0.035, 0.008, segs=8)   # fangs
        mb.cyl((0.12 * sx, -0.3, 0.5), (0.18 * sx, -0.45, 0.42), 0.02, 0.012, segs=6)   # palps
    mb.mi = 1
    for i, (x, y, z, r) in enumerate([(0.05, -0.33, 0.6, 0.035), (-0.05, -0.33, 0.6, 0.035), (0.11, -0.3, 0.62, 0.022),
                                      (-0.11, -0.3, 0.62, 0.022), (0.03, -0.3, 0.67, 0.018), (-0.03, -0.3, 0.67, 0.018),
                                      (0.14, -0.26, 0.58, 0.015), (-0.14, -0.26, 0.58, 0.015)]):
        mb.sphere((x, y, z), r)
    # glowing skull marking on the abdomen
    mb.sphere((0, 0.5, 1.0), 0.09, (1, 1.1, 0.3))
    mb.mi = 0
    for sx in (-1, 1):
        mb.sphere((0.035 * sx, 0.46, 1.03), 0.025, (1, 1, 0.5))
    for n in legs:
        for seg, r0, r1 in (("_a", 0.05, 0.04), ("_b", 0.04, 0.028), ("_c", 0.028, 0.008)):
            g(n + seg)
            h, t, _ = B[n + seg]
            mb.sphere(h, r0 * 1.15)
            mb.cyl(h, t, r0, r1, segs=8)
    me = mb.mesh("Spider_Body", [M["chitin"], M["eye_red"]])
    ob = bpy.data.objects.new("Spider_Body", me)
    bpy.context.scene.collection.objects.link(ob)
    rig = make_rig("Spider", B, order)
    skin(ob, rig, order)
    rig.parent = root
    return {"name": "Giant spider", "cat": "Creatures", "rig": "spider",
            "desc": "3 m leg span, 24 posable leg joints, glowing skull on its back."}


def p_serpent(M):
    root = root_empty("bone_serpent")
    N = 16
    B, order = {}, []
    prev = None
    for i in range(N):
        y0, y1 = 2.4 - i * 0.18, 2.4 - (i + 1) * 0.18
        n = f"seg{i:02d}"
        B[n] = ((0, y0, 0.14), (0, y1, 0.14), prev)
        order.append(n)
        prev = n
    B["head"] = ((0, y1, 0.14), (0, y1 - 0.3, 0.14), prev)
    order.append("head")
    mb, g = rigged_mb(order)
    for i in range(N):
        n = f"seg{i:02d}"
        g(n)
        h, t, _ = B[n]
        k = 0.45 + 0.55 * min(1, (N - i) / N * 1.6) if i < N else 1
        k = 0.35 + 0.65 * (i / (N - 1))
        mb.cyl(h, t, 0.045 * k, 0.045 * k, segs=10)
        mb.sphere(t, 0.055 * k)
        y = (h[1] + t[1]) / 2
        mb.box((0, y, 0.14 + 0.07 * k), (0.012, 0.03, 0.08 * k))
        for sx in (-1, 1):   # ribs curving down
            mb.torus((0.0, y, 0.12), 0.12 * k, 0.008, (1, 1, 1), (math.radians(90), 0, math.radians(90 * sx)),
                     segs=(12, 4), arc=math.pi * 0.75)
    g("head")
    hy = B["head"][0][1]
    mb.sphere((0, hy - 0.08, 0.15), 0.08, (0.9, 1.4, 0.65))
    mb.cyl((0, hy - 0.12, 0.13), (0, hy - 0.3, 0.12), 0.06, 0.02, segs=10)
    mb.box((0, hy - 0.2, 0.085), (0.08, 0.2, 0.015))
    for sx in (-1, 1):
        mb.cyl((0.03 * sx, hy - 0.26, 0.11), (0.03 * sx, hy - 0.27, 0.03), 0.01, 0.001, segs=5)
    mb.mi = 1
    for sx in (-1, 1):
        mb.sphere((0.045 * sx, hy - 0.12, 0.18), 0.022)
    me = mb.mesh("Serpent", [M["bone"], M["eye_green"]])
    ob = bpy.data.objects.new("Serpent_Body", me)
    bpy.context.scene.collection.objects.link(ob)
    rig = make_rig("Serpent", B, order)
    skin(ob, rig, order)
    rig.parent = root
    return {"name": "Bone serpent", "cat": "Bones", "rig": "chain",
            "desc": "3 m vertebra snake with 17 joints. Coil it, rear it up, or drape it over the railing."}


def p_tentacles(M):
    root = root_empty("lawn_tentacles")
    B, order = {}, []
    bases = [(-0.4, 0.1, 1.6, 0.4), (0.35, -0.15, 1.3, -0.3), (0.05, 0.45, 2.0, 0.1), (0.6, 0.4, 1.1, -0.6)]
    mb = MB()
    groups = []
    for t, (x, y, h, lean) in enumerate(bases):
        prev = None
        n_seg = 8
        pts = []
        for i in range(n_seg + 1):
            f = i / n_seg
            pts.append(V((x + lean * 0.4 * f * f, y + 0.25 * math.sin(f * 2.5 + t), -0.05 + h * f)))
        for i in range(n_seg):
            n = f"t{t}_{i}"
            B[n] = (tuple(pts[i]), tuple(pts[i + 1]), prev)
            order.append(n)
            prev = n
    mb, g = rigged_mb(order)
    for t, (x, y, h, lean) in enumerate(bases):
        for i in range(8):
            n = f"t{t}_{i}"
            g(n)
            a, b = V(B[n][0]), V(B[n][1])
            r0 = 0.13 * (1 - i / 8) + 0.012
            r1 = 0.13 * (1 - (i + 1) / 8) + 0.01
            mb.mi = 0
            mb.sphere(a, r0 * 1.02, segs=(12, 8))
            mb.cyl(a, b, r0, r1, segs=12)
            mb.mi = 1
            d = (b - a).normalized()
            side = d.cross(V((0, 0, 1))).normalized() if abs(d.z) < 0.99 else V((1, 0, 0))
            for k in range(2):
                p = a.lerp(b, 0.25 + 0.5 * k) + side * (r0 * 0.9)
                mb.sphere(p, r0 * 0.28, (1, 1, 1), segs=(8, 5))
    mb.mi = 2   # dirt mound
    mb.gi = None
    me = mb.mesh("Tentacles", [M["flesh"], M["sucker"], M["mulch"]])
    ob = bpy.data.objects.new("Tentacles_Body", me)
    bpy.context.scene.collection.objects.link(ob)
    rig = make_rig("Tentacles", B, order)
    skin(ob, rig, order)
    rig.parent = root
    mound = MB()
    mound.sphere((0.15, 0.2, -0.05), 0.9, (1.2, 1.0, 0.18), segs=(24, 10))
    mound.obj("Tentacle_Dirt", [M["mulch"]]).parent = root
    return {"name": "Lawn tentacles", "cat": "Creatures", "rig": "chain", "behaviors": ["sway"],
            "desc": "Four tentacles bursting out of the lawn. They sway; every segment can be posed."}


# ===================================================================== static props
def p_giant_skull(M):
    root = root_empty("giant_skull")
    mb = MB()
    k = 7.0
    mb.sphere((0, 0.0, 1.675 * k - 10.7), 0.095 * k, (0.85, 1.05, 1.0), segs=(32, 20))
    z0 = -10.7
    mb.sphere((0, -0.055 * k, 1.615 * k + z0), 0.062 * k, (1.0, 0.85, 0.85), segs=(24, 14))
    mb.sphere((0, -0.05 * k, 1.56 * k + z0), 0.05 * k, (1.15, 0.9, 0.45), segs=(24, 12))
    for sx in (-1, 1):
        mb.sphere((0.065 * sx * k, -0.045 * k, 1.635 * k + z0), 0.025 * k, (0.8, 1.6, 0.8))
    for i in range(10):
        x = (i - 4.5) * 0.009 * k
        mb.box((x, -0.105 * k, 1.585 * k + z0), (0.008 * k, 0.012 * k, 0.022 * k))
    mb.mi = 1
    for sx in (-1, 1):
        mb.sphere((0.034 * sx * k, -0.083 * k, 1.672 * k + z0), 0.024 * k, (1.0, 0.7, 1.05))
    mb.mi = 2
    for sx in (-1, 1):
        mb.sphere((0.034 * sx * k, -0.1 * k, 1.672 * k + z0), 0.008 * k)
    mb.mi = 1
    mb.sphere((0, -0.1 * k, 1.625 * k + z0), 0.012 * k, (0.8, 0.6, 1.3))
    ob = mb.obj("Giant_Skull", [M["bone"], M["socket"], M["eye_red"]])
    ob.parent = root
    return {"name": "Giant skull", "cat": "Bones", "behaviors": ["pulse"],
            "light": {"type": "point", "color": "#ff2210", "intensity": 6, "offset": [0, 1.1, 0.7]},
            "desc": "1.4 m skull with pulsing red eyes."}


def p_skull_pile(M):
    root = root_empty("skull_pile")
    rnd = random.Random(4)
    mb = MB()
    layers = [(0.6, 0.11, 11), (0.42, 0.3, 8), (0.25, 0.48, 5), (0.0, 0.64, 1)]
    for R, z, n in layers:
        for j in range(n):
            a = 2 * math.pi * j / n + z
            c = V((R * math.cos(a), R * math.sin(a), z))
            yaw = math.atan2(-c.y, -c.x) + math.pi / 2 if R > 0 else 0
            yaw += rnd.uniform(-0.4, 0.4)
            Rz = Matrix.Rotation(yaw + math.pi, 4, "Z")
            def P(p):
                return c + (Rz @ V(p)).to_3d() * 1.0
            mb.mi = 0
            mb.sphere(P((0, 0.0, 0.0)), 0.095, (0.85, 1.05, 1.0), (0, 0, yaw), segs=(14, 9))
            mb.sphere(P((0, -0.055, -0.06)), 0.062, (1.0, 0.85, 0.85), (0, 0, yaw), segs=(12, 8))
            mb.mi = 1
            for sx in (-1, 1):
                mb.sphere(P((0.034 * sx, -0.083, -0.003)), 0.024, (1.0, 0.7, 1.05), (0, 0, yaw), segs=(8, 6))
    ob = mb.obj("Skull_Pile", [M["bone"], M["socket"]])
    ob.parent = root
    return {"name": "Ossuary pile", "cat": "Bones", "desc": "Pyramid of 25 skulls, all facing out."}


def p_grasping_arms(M):
    root = root_empty("grasping_arms")
    rnd = random.Random(9)
    mb = MB()
    for i in range(6):
        a = 2 * math.pi * i / 6 + rnd.uniform(-0.3, 0.3)
        r = rnd.uniform(0.15, 0.55)
        base = V((r * math.cos(a), r * math.sin(a), -0.05))
        d = V((math.cos(a) * 0.3, math.sin(a) * 0.3, 1)).normalized()
        L = rnd.uniform(0.45, 0.75)
        wrist = base + d * L
        mb.mi = 0
        mb.cyl(base, wrist, 0.014, 0.011, segs=6)
        mb.cyl(base + V((0.025, 0, 0)), wrist + V((0.022, 0, 0)), 0.01, 0.008, segs=6)
        mb.sphere(wrist, 0.02)
        side = d.cross(V((0, 0, 1))).normalized() if abs(d.z) < 0.99 else V((1, 0, 0))
        palm = wrist + d * 0.06
        mb.cyl(wrist, palm, 0.026, 0.024, segs=6)
        curl = rnd.uniform(0.2, 0.9)
        for f in range(4):
            fb = palm + side * (-0.03 + 0.02 * f)
            k1 = fb + d * 0.05
            k2 = k1 + (d * (1 - curl) + side.cross(d) * curl * 0.7).normalized() * 0.04
            mb.cyl(fb, k1, 0.006, segs=5)
            mb.cyl(k1, k2, 0.005, 0.003, segs=5)
        mb.cyl(wrist + side * -0.035, wrist + side * -0.07 + d * 0.04, 0.006, 0.004, segs=5)
    mb.mi = 1
    mb.sphere((0, 0, -0.04), 0.75, (1.0, 1.0, 0.15), segs=(24, 10))
    ob = mb.obj("Grasping_Arms", [M["bone"], M["mulch"]])
    ob.parent = root
    return {"name": "Grasping arms", "cat": "Bones", "desc": "Six skeletal arms clawing out of a dirt mound."}


def p_rib_arch(M):
    root = root_empty("ribcage_arch")
    mb = MB()
    n = 7
    for i in range(n):
        y = -1.8 + i * 0.6
        s = 1.0 - 0.25 * abs(i - n / 2 + 0.5) / (n / 2)
        mb.torus((0, y, 0.0), 1.3 * s, 0.07 * s, (1.0, 1.85, 1.0), (math.radians(90), 0, 0), segs=(40, 8), arc=math.pi)
    for i in range(14):   # spine along the top
        y = -2.0 + i * 0.32
        mb.cyl((0, y - 0.1, 2.41), (0, y + 0.1, 2.41), 0.12, segs=12)
        mb.box((0, y, 2.6), (0.05, 0.12, 0.25))
    mb.mi = 1
    for i in range(n):   # dangling LED drops
        y = -1.8 + i * 0.6
        mb.sphere((0, y, 2.15), 0.04)
    ob = mb.obj("Ribcage_Arch", [M["bone_real"], M["led_red"]])
    ob.parent = root
    return {"name": "Ribcage archway", "cat": "Bones", "desc": "Walk-through tunnel of giant ribs, 2.6 m tall."}


def p_eyeball_tree(M):
    root = root_empty("eyeball_tree")
    rnd = random.Random(13)
    splines, tips = [], []
    def branch(p, d, L, r, depth):
        pts = [(tuple(p), r)]
        q = V(p)
        for i in range(4):
            d = (d + V((rnd.uniform(-0.35, 0.35), rnd.uniform(-0.35, 0.35), rnd.uniform(-0.1, 0.25)))).normalized()
            q = q + d * (L / 4)
            pts.append((tuple(q), r * (1 - 0.18 * (i + 1))))
        splines.append(pts)
        if depth > 0:
            for _ in range(rnd.choice((2, 3))):
                nd = (d + V((rnd.uniform(-1, 1), rnd.uniform(-1, 1), rnd.uniform(0, 0.6)))).normalized()
                branch(q, nd, L * 0.65, r * 0.4, depth - 1)
        else:
            tips.append((q, d))
    branch(V((0, 0, -0.1)), V((0, 0, 1)), 1.9, 1.0, 3)
    tr = tube_curve("Eyeball_Tree_Bark", splines, bevel=0.17, mats=[M["bark"]], res=2)
    tr.parent = root
    for i, (q, d) in enumerate(tips[:16]):
        mb = MB()
        r = rnd.uniform(0.08, 0.13)
        mb.sphere((0, 0, 0), r, segs=(16, 10))
        mb.mi = 1
        mb.sphere((0, r * 0.82, 0), r * 0.42, (1, 0.35, 1), segs=(12, 8))
        mb.mi = 2
        mb.sphere((0, r * 0.95, 0), r * 0.18, (1, 0.3, 1), segs=(8, 6))
        eye = mb.obj(f"Eye_{i:02d}", [M["eyeball"], M["iris"], M["socket"]])
        eye.location = q + d * r
        eye.parent = root
    return {"name": "Eyeball tree", "cat": "Creatures", "behaviors": ["eyes_follow"],
            "desc": "Dead tree with 16 eyeballs that turn to watch you."}


def p_coffin(M):
    root = root_empty("coffin")
    def coffin_shape(mb, w, h, d, y0, mi):
        pts = [(-w * 0.32, 0), (w * 0.32, 0), (w * 0.5, h * 0.72), (w * 0.38, h), (-w * 0.38, h), (-w * 0.5, h * 0.72)]
        mb.mi = mi
        vs0 = [mb.bm.verts.new((x, y0, z)) for x, z in pts]
        vs1 = [mb.bm.verts.new((x, y0 + d, z)) for x, z in pts]
        mb.bm.faces.new(vs0[::-1]); mb.bm.faces.new(vs1)
        for i in range(len(pts)):
            j = (i + 1) % len(pts)
            mb.bm.faces.new((vs0[i], vs0[j], vs1[j], vs1[i]))
        mb._tag(vs0 + vs1)
    mb = MB(); mb.smooth = False
    coffin_shape(mb, 0.78, 2.0, 0.08, 0.32, 0)       # back
    for sx in (-1, 1):                                # side walls
        pass
    pts = [(-0.25, 0), (0.25, 0), (0.39, 1.44), (0.3, 2.0), (-0.3, 2.0), (-0.39, 1.44)]
    for i in range(len(pts)):
        a, b = pts[i], pts[(i + 1) % len(pts)]
        mb.mi = 0
        L = math.hypot(b[0] - a[0], b[1] - a[1])
        ang = math.atan2(b[1] - a[1], b[0] - a[0])
        mb.box(((a[0] + b[0]) / 2, 0.16, (a[1] + b[1]) / 2), (L + 0.04, 0.32, 0.05), (0, -ang, 0))
    mb.mi = 1
    mb.quad([(-0.22, 0.31, 0.05), (0.22, 0.31, 0.05), (0.34, 0.31, 1.42), (-0.34, 0.31, 1.42)])
    mb.quad([(-0.34, 0.31, 1.42), (0.34, 0.31, 1.42), (0.27, 0.31, 1.95), (-0.27, 0.31, 1.95)])
    body = mb.obj("Coffin_Body", [M["wood_dark"], M["velvet"]])
    body.parent = root
    lid = MB(); lid.smooth = False
    coffin_shape(lid, 0.8, 2.02, 0.06, 0.0, 0)
    lid.mi = 1
    lid.box((0, -0.01, 1.35), (0.06, 0.02, 0.7))
    lid.box((0, -0.01, 1.5), (0.35, 0.02, 0.06))
    lo = lid.obj("Lid", [M["wood_dark"], M["brass"]])
    hinge = empty("Lid_Hinge", (0.4, -0.02, 0), None, 0.1)
    hinge.parent = root
    lo.parent = hinge
    lo.location = (-0.4, -0.04, 0)
    hinge.rotation_euler.z = math.radians(-35)
    return {"name": "Upright coffin", "cat": "Graveyard", "behaviors": ["creak"],
            "desc": "Velvet-lined coffin whose lid slowly creaks open and shut."}


def p_tombstone(M, kind):
    pid = {"round": "tombstone_rip", "cross": "tombstone_cross", "obelisk": "obelisk"}[kind]
    root = root_empty(pid)
    mb = MB(); mb.smooth = False
    if kind == "round":
        mb.box((0, 0, 0.42), (0.6, 0.14, 0.84))
        mb.smooth = True
        mb.cyl((0, -0.07, 0.84), (0, 0.07, 0.84), 0.3, segs=32)
        mb.smooth = False
        mb.box((0, 0, 0.04), (0.76, 0.24, 0.08))
        t = text_mesh("R.I.P.", 0.16, 0.01, M["socket"], (0, -0.075, 0.78), name="Tomb_Text")
        t2 = text_mesh("HERE LIES\nA DECORATOR", 0.055, 0.006, M["socket"], (0, -0.075, 0.55), name="Tomb_Text2")
        t.parent = t2.parent = root
        info = {"name": "R.I.P. headstone", "desc": "Rounded slate headstone."}
    elif kind == "cross":
        mb.box((0, 0, 0.62), (0.13, 0.13, 1.24))
        mb.box((0, 0, 0.92), (0.62, 0.13, 0.13))
        mb.box((0, 0, 0.05), (0.4, 0.3, 0.1))
        info = {"name": "Stone cross", "desc": "Weathered Celtic-style grave cross."}
        mb.smooth = True
        mb.torus((0, -0.0, 0.92), 0.2, 0.03, (1, 1, 1), (math.radians(90), 0, 0), segs=(28, 6))
    else:
        mb.box((0, 0, 0.12), (0.6, 0.6, 0.24))
        mb.box((0, 0, 0.34), (0.45, 0.45, 0.2))
        mb.lathe([(0.17, 0.44), (0.17, 0.45), (0.12, 1.95), (0.0, 2.15)], segs=4, cap_bottom=True)
        info = {"name": "Obelisk", "desc": "2.2 m granite obelisk."}
    ob = mb.obj(pid.title(), [M["stone_grave"]])
    ob.parent = root
    info["cat"] = "Graveyard"
    return info


def p_fence(M):
    root = root_empty("iron_fence")
    mb = MB()
    for i in range(16):
        x = -1.5 + i * 0.2
        mb.cyl((x, 0, 0), (x, 0, 1.25), 0.012, segs=6)
        mb.cyl((x, 0, 1.25), (x, 0, 1.38), 0.03, 0.001, segs=4)
    for z in (0.15, 1.1):
        mb.box((0, 0, z), (3.1, 0.03, 0.03))
    for i in range(15):
        mb.torus((-1.4 + i * 0.2, 0, 1.0), 0.06, 0.006, (1, 1, 1), (math.radians(90), 0, 0), segs=(14, 4))
    for x in (-1.6, 1.6):
        mb.box((x, 0, 0.75), (0.12, 0.12, 1.5))
        mb.sphere((x, 0, 1.58), 0.09)
    ob = mb.obj("Iron_Fence", [M["iron"]])
    ob.parent = root
    return {"name": "Iron fence (3 m)", "cat": "Graveyard", "desc": "Wrought-iron graveyard fence section with spear tips."}


def p_cauldron(M):
    root = root_empty("cauldron")
    mb = MB()
    prof = [(0.001, 0.12), (0.25, 0.14), (0.42, 0.3), (0.46, 0.48), (0.42, 0.66), (0.36, 0.72), (0.4, 0.75), (0.4, 0.78)]
    mb.lathe(prof, 32)
    for a in (0, 2.1, 4.2):
        mb.cyl((0.3 * math.cos(a), 0.3 * math.sin(a), 0.2), (0.38 * math.cos(a), 0.38 * math.sin(a), 0.0), 0.04, segs=8)
    mb.mi = 1
    mb.lathe([(0.0, 0.68), (0.37, 0.68)], 32)
    for i in range(7):
        a = i * 1.3
        r = 0.08 + 0.2 * ((i * 37) % 10) / 10
        mb.sphere((r * math.cos(a), r * math.sin(a), 0.7), 0.03 + 0.02 * (i % 3), (1, 1, 0.7))
    ob = mb.obj("Cauldron", [M["iron"], M["brew"]])
    ob.parent = root
    logs = MB()
    for a in (0.3, 1.8, 3.6):
        logs.cyl((0.35 * math.cos(a), 0.35 * math.sin(a), 0.04), (-0.35 * math.cos(a), -0.35 * math.sin(a), 0.04), 0.05, segs=8)
    logs.mi = 1
    logs.sphere((0, 0, 0.08), 0.18, (1, 1, 0.5))
    logs.obj("Cauldron_Fire", [M["bark"], M["glow_orange"]]).parent = root
    return {"name": "Bubbling cauldron", "cat": "Spooky stuff", "behaviors": ["flicker"],
            "light": {"type": "point", "color": "#66ff33", "intensity": 5, "offset": [0, 1.0, 0]},
            "desc": "Iron cauldron of glowing green brew over a fire."}


def jack_face(mb, r, z_c, style, mi_glow):
    """Carved face: glowing shapes set just proud of the pumpkin surface, facing -Y."""
    mb.mi = mi_glow
    def tri(cx, cz, w, h, up=True):
        y = -r * 0.98
        pts = [(cx - w / 2, y, cz - h / 2), (cx + w / 2, y, cz - h / 2), (cx, y, cz + h / 2)] if up else \
              [(cx - w / 2, y, cz + h / 2), (cx, y, cz - h / 2), (cx + w / 2, y, cz + h / 2)]
        vs = [mb.bm.verts.new(p) for p in pts]
        mb.bm.faces.new(vs if up else vs)
        mb._tag(vs)
    s = r
    tri(-0.38 * s, z_c + 0.2 * s, 0.28 * s, 0.26 * s, style != "angry")
    tri(0.38 * s, z_c + 0.2 * s, 0.28 * s, 0.26 * s, style != "angry")
    tri(0, z_c + 0.0, 0.14 * s, 0.12 * s)
    n = 7
    for i in range(n):   # toothy grin
        x0 = -0.55 * s + 1.1 * s * i / n
        x1 = x0 + 1.1 * s / n
        zc = z_c - 0.3 * s + 0.1 * s * ((i - n / 2) / (n / 2)) ** 2
        tri((x0 + x1) / 2, zc, (x1 - x0), 0.16 * s, i % 2 == 0)


def pumpkin_mesh(mb, r, z0, mi):
    mb.mi = mi
    prof = [(0.001, 0.0), (0.55, 0.05), (0.92, 0.25), (1.0, 0.5), (0.9, 0.78), (0.55, 0.95), (0.08, 0.9)]
    mb.lathe([(a * r, z0 + b * r * 1.6) for a, b in prof], 40, (0, 0, 0),
             lambda t, z, rr, i: rr * (1 - 0.06 * abs(math.sin(5 * t))))


def p_jack(M):
    root = root_empty("jack_o_lantern")
    mb = MB()
    r = 0.3
    pumpkin_mesh(mb, r, 0, 0)
    jack_face(mb, r * 1.02, r * 0.85, "classic", 1)
    mb.mi = 2
    mb.cyl((0, 0, r * 1.45), (0.03, 0.02, r * 1.75), 0.04, 0.03, segs=7)
    mb.obj("Jack_O_Lantern", [M["pumpkin"], M["glow_orange"], M["stem"]]).parent = root
    return {"name": "Jack-o'-lantern", "cat": "Spooky stuff", "behaviors": ["flicker"],
            "light": {"type": "point", "color": "#ff8a1e", "intensity": 2.5, "offset": [0, 0.45, 0]},
            "desc": "Classic carved pumpkin with a candle flicker."}


def p_pumpkin_totem(M):
    root = root_empty("pumpkin_totem")
    mb = MB()
    z = 0
    for i, r in enumerate((0.34, 0.28, 0.23, 0.18)):
        pumpkin_mesh(mb, r, z, 0)
        jack_face(mb, r * 1.02, z + r * 0.85, "angry" if i % 2 else "classic", 1)
        z += r * 1.42
    mb.mi = 2
    mb.cyl((0, 0, z), (0.02, 0.01, z + 0.12), 0.03, 0.02, segs=7)
    mb.obj("Pumpkin_Totem", [M["pumpkin"], M["glow_orange"], M["stem"]]).parent = root
    return {"name": "Pumpkin totem", "cat": "Spooky stuff", "behaviors": ["flicker"],
            "light": {"type": "point", "color": "#ff8a1e", "intensity": 3, "offset": [0, 0.9, 0.25]},
            "desc": "Four grinning jack-o'-lanterns stacked into a 1.6 m totem."}


def p_scarecrow(M):
    root = root_empty("scarecrow")
    mb = MB(); mb.smooth = False
    mb.mi = 0
    mb.box((0, 0.05, 1.0), (0.08, 0.08, 2.0))
    mb.box((0, 0.05, 1.5), (1.4, 0.07, 0.07))
    mb.smooth = True
    mb.mi = 1   # flannel torso + sleeves
    mb.lathe([(0.2, 0.85), (0.22, 1.0), (0.2, 1.3), (0.22, 1.5), (0.12, 1.58), (0.05, 1.6)], 16, cap_top=True, scale=(1, 0.7))
    for sx in (-1, 1):
        mb.cyl((0.15 * sx, 0, 1.5), (0.62 * sx, 0, 1.47), 0.09, 0.07, segs=10)
    mb.mi = 2   # straw
    rnd = random.Random(5)
    for sx in (-1, 1):
        for i in range(9):
            mb.cyl((0.62 * sx, 0, 1.47), (0.75 * sx, rnd.uniform(-0.06, 0.06), 1.47 + rnd.uniform(-0.12, 0.08)), 0.006, segs=4)
    for i in range(12):
        a = i * 0.52
        mb.cyl((0.1 * math.cos(a), 0.07 * math.sin(a), 0.88), (0.13 * math.cos(a), 0.09 * math.sin(a), 0.7), 0.006, segs=4)
    mb.mi = 3   # burlap head
    mb.sphere((0, 0, 1.78), 0.17, (1, 0.95, 1.1), segs=(18, 12))
    mb.mi = 4
    for sx in (-1, 1):
        mb.box((0.06 * sx, -0.16, 1.82), (0.05, 0.01, 0.05), (0, 0, 0.785))
    for i in range(7):
        mb.box((-0.08 + i * 0.027, -0.162, 1.7), (0.004, 0.01, 0.035))
    mb.box((0, -0.162, 1.7), (0.17, 0.01, 0.005))
    mb.mi = 5   # hat
    mb.lathe([(0.32, 1.9), (0.32, 1.92), (0.15, 1.93), (0.13, 2.1), (0.001, 2.12)], 20, cap_bottom=True)
    mb.obj("Scarecrow", [M["wood_stake"], M["flannel"], M["straw"], M["burlap"], M["socket"], M["cloth_black"]]).parent = root
    return {"name": "Scarecrow", "cat": "Ghouls", "desc": "Burlap-headed scarecrow with a stitched grin."}


def p_plague_doctor(M):
    root = root_empty("plague_doctor")
    body, hz = BP.mannequin("Plague_Body", bpy.context.scene.collection, M, (0, 0, 0), 0, 1.8, None,
                            dress="cloth_black", gown=True)
    body.parent = root
    k = 1.8 / 1.3
    mb = MB()
    mb.mi = 0   # cloak
    mb.lathe([(0.42, 0.05), (0.36, 0.5), (0.25, 1.1), (0.2, 1.4), (0.24, 1.47), (0.08, 1.52)], 32,
             rmod=lambda t, z, r, i: r * (1 + 0.04 * math.sin(7 * t) * (z < 0.6)), cap_top=True)
    mb.mi = 1   # beak
    mb.cyl((0, -0.07, hz - 0.02), (0, -0.42, hz - 0.2), 0.075, 0.008, segs=16)
    mb.sphere((0, -0.03, hz + 0.01), 0.1, (0.95, 1, 1.05))
    mb.mi = 2   # lenses
    for sx in (-1, 1):
        mb.cyl((0.04 * sx, -0.075, hz + 0.03), (0.042 * sx, -0.1, hz + 0.03), 0.026, segs=12)
    mb.mi = 0   # hat
    mb.lathe([(0.34, hz + 0.07), (0.34, hz + 0.09), (0.12, hz + 0.1), (0.11, hz + 0.3), (0.001, hz + 0.3)], 24, cap_bottom=True)
    mb.mi = 3   # cane
    mb.cyl((0.32, -0.15, 0.0), (0.3, -0.18, 1.25), 0.012, segs=6)
    mb.obj("Plague_Gear", [M["cloth_black"], M["leather"], M["eye_green"], M["wood_dark"]]).parent = root
    return {"name": "Plague doctor", "cat": "Ghouls", "desc": "1.9 m beaked plague doctor with glowing green lenses."}


def p_ghost(M):
    root = root_empty("ghost")
    mb = MB()
    prof = [(0.34, 0.25), (0.3, 0.4), (0.24, 0.8), (0.21, 1.1), (0.22, 1.3), (0.17, 1.45), (0.001, 1.55)]
    mb.lathe(prof, 36, rmod=lambda t, z, r, i: r * (1 + (0.22 * math.sin(6 * t) if z < 0.3 else 0)))
    for sx in (-1, 1):
        mb.cyl((0.18 * sx, 0, 1.15), (0.42 * sx, -0.12, 0.85), 0.08, 0.04, segs=12)
    mb.mi = 1
    for sx in (-1, 1):
        mb.sphere((0.07 * sx, -0.2, 1.3), 0.035, (1, 0.5, 1.5))
    mb.sphere((0, -0.2, 1.17), 0.04, (1, 0.5, 1.4))
    mb.obj("Ghost_Sheet", [M["sheet"], M["socket"]]).parent = root
    return {"name": "Floating ghost", "cat": "Ghouls", "behaviors": ["bob"],
            "desc": "Bedsheet ghost that hovers and sways."}


def p_hanging_cage(M):
    root = root_empty("hanging_cage")
    mb = MB()
    mb.cyl((0, 0.6, 0), (0, 0.6, 2.6), 0.04, segs=8)                          # shepherd hook post
    mb.torus((0, 0.35, 2.6), 0.25, 0.035, (1, 1, 1), (math.radians(90), 0, math.radians(90)), segs=(20, 6), arc=math.pi)
    mb.cyl((0, 0.1, 2.6), (0, 0.1, 1.9), 0.006, segs=4)                     # chain
    for i in range(12):
        a = 2 * math.pi * i / 12
        x, y = 0.22 * math.cos(a), 0.1 + 0.22 * math.sin(a)
        mb.cyl((x, y, 1.15), (x, y, 1.75), 0.008, segs=4)
    for z in (1.15, 1.45, 1.75):
        mb.torus((0, 0.1, z), 0.22, 0.012, segs=(24, 4))
    mb.lathe([(0.22, 1.75), (0.12, 1.86), (0.001, 1.9)], 16)
    mb.lathe([(0.001, 1.15), (0.22, 1.15)], 16)
    mb.mi = 1
    mb.sphere((0.02, 0.08, 1.27), 0.095, (0.85, 1.05, 1.0))
    mb.sphere((0.02, 0.03, 1.21), 0.06, (1, 0.85, 0.85))
    mb.mi = 2
    for sx in (-1, 1):
        mb.sphere((0.034 * sx + 0.02, 0.0, 1.27), 0.024)
    mb.obj("Hanging_Cage", [M["iron"], M["bone"], M["eye_red"]]).parent = root
    return {"name": "Hanging cage", "cat": "Spooky stuff", "behaviors": ["swing"],
            "desc": "Gibbet cage on a shepherd's hook with a red-eyed skull inside."}


def p_bats(M):
    root = root_empty("bat_swarm")
    rnd = random.Random(3)
    for i in range(7):
        b = empty(f"Bat_{i}", (rnd.uniform(-1, 1), rnd.uniform(-1, 1), 2.0 + rnd.uniform(-0.4, 0.6)), None, 0.05)
        b.parent = root
        b.rotation_euler.z = rnd.uniform(0, 6.28)
        b.scale = (1.8, 1.8, 1.8)
        mb = MB()
        mb.sphere((0, 0, 0), 0.05, (0.8, 1.3, 0.8))
        mb.sphere((0, -0.07, 0.01), 0.035)
        for sx in (-1, 1):
            mb.cyl((0.02 * sx, -0.08, 0.04), (0.03 * sx, -0.07, 0.07), 0.01, 0.001, segs=4)
        mb.mi = 1
        for sx in (-1, 1):
            mb.sphere((0.014 * sx, -0.1, 0.02), 0.007)
        body = mb.obj(f"Bat_{i}_Body", [M["chitin"], M["eye_red"]])
        body.parent = b
        for s, sx in (("L", 1), ("R", -1)):
            wing = empty(f"Wing_{s}_{i}", (0.03 * sx, 0, 0.01), None, 0.02)
            wing.parent = b
            w = MB(); w.smooth = False
            pts = [(0, -0.05, 0), (0.18 * sx, -0.06, 0.03), (0.3 * sx, 0.02, 0.0), (0.22 * sx, 0.05, 0), (0.14 * sx, 0.03, 0),
                   (0.08 * sx, 0.07, 0), (0, 0.05, 0)]
            vs = [w.bm.verts.new(p) for p in pts]
            w.bm.faces.new(vs if sx > 0 else vs[::-1])
            w._tag(vs)
            wm = w.obj(f"Wing_{s}_{i}_Membrane", [M["chitin"]])
            wm.parent = wing
    return {"name": "Bat swarm", "cat": "Creatures", "behaviors": ["flap", "orbit"],
            "desc": "Seven red-eyed bats circling overhead."}


def p_moth(M):
    root = root_empty("giant_moth")
    mb = MB()
    mb.mi = 0
    mb.cyl((0, 0.25, 0), (0, 0.25, 1.3), 0.02, segs=6)
    mb.sphere((0, 0.15, 1.45), 0.06, (0.9, 1.0, 2.6))
    mb.sphere((0, 0.15, 1.66), 0.05)
    for sx in (-1, 1):
        mb.cyl((0.02 * sx, 0.12, 1.69), (0.14 * sx, 0.05, 1.85), 0.006, 0.002, segs=4)
    mb.obj("Moth_Body", [M["moth"]]).parent = root
    for s, sx in (("L", 1), ("R", -1)):
        wing = empty(f"Wing_{s}", (0.04 * sx, 0.15, 1.5), None, 0.05)
        wing.parent = root
        w = MB(); w.smooth = False
        up = [(0, 0, 0.12), (0.35, 0, 0.32), (0.62, 0, 0.18), (0.55, 0, -0.05), (0.2, 0, -0.08), (0, 0, -0.02)]
        lo = [(0, 0, -0.05), (0.3, 0, -0.12), (0.4, 0, -0.35), (0.2, 0, -0.42), (0.03, 0, -0.2)]
        for pts in (up, lo):
            vs = [w.bm.verts.new((x * sx, y, z)) for x, y, z in pts]
            w.bm.faces.new(vs if sx > 0 else vs[::-1])
            w._tag(vs)
        w.mi = 1
        w.smooth = True
        w.sphere((0.36 * sx, -0.005, 0.15), 0.09, (1, 0.05, 1), segs=(16, 6))
        w.sphere((0.24 * sx, -0.005, -0.24), 0.06, (1, 0.05, 1), segs=(16, 6))
        w.mi = 2
        w.sphere((0.36 * sx, -0.008, 0.15), 0.035, (1, 0.05, 1), segs=(12, 6))
        w.sphere((0.24 * sx, -0.008, -0.24), 0.025, (1, 0.05, 1), segs=(12, 6))
        wo = w.obj(f"Wing_{s}_Membrane", [M["moth"], M["moth_eye"], M["eye_red"]])
        wo.parent = wing
    return {"name": "Giant moth", "cat": "Creatures", "behaviors": ["flutter"],
            "desc": "1.3 m moth with staring eyespots, slowly fanning its wings."}


def p_web(M):
    root = root_empty("spider_web")
    mb = MB()
    for x in (-1.3, 1.3):
        mb.mi = 1
        mb.cyl((x, 0, 0), (x, 0, 2.4), 0.03, segs=6)
    mb.mi = 0
    c = V((0, 0, 1.35))
    spokes = 16
    for i in range(spokes):
        a = 2 * math.pi * i / spokes
        L = 1.25 if abs(math.cos(a)) > 0.5 else 1.0
        mb.cyl(c, c + V((math.cos(a) * L, 0, math.sin(a) * L)), 0.004, segs=3)
    for ring in range(1, 9):
        r = ring * 0.13
        for i in range(spokes):
            a0, a1 = 2 * math.pi * i / spokes, 2 * math.pi * (i + 1) / spokes
            p0 = c + V((math.cos(a0) * r, 0, math.sin(a0) * r))
            p1 = c + V((math.cos(a1) * r, 0, math.sin(a1) * r))
            mid = (p0 + p1) / 2 - (p0 + p1 - 2 * c).normalized() * 0.02 * r
            mb.cyl(p0, mid, 0.0025, segs=3)
            mb.cyl(mid, p1, 0.0025, segs=3)
    mb.obj("Spider_Web", [M["web"], M["wood_stake"]]).parent = root
    return {"name": "Giant web", "cat": "Creatures", "desc": "2.6 m orb web strung between two stakes."}


def p_candelabra(M):
    root = root_empty("candelabra")
    mb = MB()
    mb.lathe([(0.2, 0.0), (0.18, 0.04), (0.04, 0.08), (0.03, 1.2), (0.05, 1.25), (0.02, 1.3)], 20, cap_bottom=True)
    flames = MB()
    for i, x in enumerate((-0.36, -0.18, 0, 0.18, 0.36)):
        z = 1.3 + (0.12 if x == 0 else 0.05 * (1 - abs(x) / 0.36))
        if x != 0:
            mb.torus((x / 2, 0, 1.25), abs(x) / 2, 0.012, (1, 1, 1), (math.radians(90), 0, 0), segs=(12, 4), arc=math.pi)
        mb.lathe([(0.035, z - 0.02), (0.04, z)], 12)
        mb.mi = 1
        h = 0.18 + 0.06 * ((i * 7) % 3)
        mb.cyl((x, 0, z), (x, 0, z + h), 0.022, segs=10)
        mb.mi = 0
        flames.sphere((x, 0, z + h + 0.03), 0.014, (0.7, 0.7, 1.8))
    mb.obj("Candelabra", [M["brass"], M["wax"]]).parent = root
    flames.obj("Candelabra_Flames", [M["flame"]]).parent = root
    return {"name": "Candelabra", "cat": "Spooky stuff", "behaviors": ["flicker"],
            "light": {"type": "point", "color": "#ffb04a", "intensity": 2.5, "offset": [0, 1.65, 0]},
            "desc": "Five-candle brass candelabra with a warm flicker."}


def p_crystal_ball(M):
    root = root_empty("crystal_ball")
    mb = MB()
    mb.lathe([(0.25, 0), (0.22, 0.05), (0.06, 0.15), (0.05, 0.85), (0.14, 0.95), (0.16, 1.0)], 20, cap_bottom=True)
    for a in range(4):
        aa = a * math.pi / 2
        mb.cyl((0.14 * math.cos(aa), 0.14 * math.sin(aa), 0.98), (0.1 * math.cos(aa), 0.1 * math.sin(aa), 1.13), 0.012, segs=5)
    mb.mi = 1
    mb.sphere((0, 0, 1.2), 0.17, segs=(28, 18))
    mb.obj("Crystal_Ball", [M["brass"], M["crystal"]]).parent = root
    return {"name": "Crystal ball", "cat": "Spooky stuff", "behaviors": ["pulse"],
            "light": {"type": "point", "color": "#9a40ff", "intensity": 2.5, "offset": [0, 1.2, 0]},
            "desc": "Fortune-teller's orb on a brass pedestal. It pulses violet."}


def p_lawn_maw(M):
    root = root_empty("lawn_maw")
    rnd = random.Random(8)
    mb = MB()
    mb.mi = 0
    mb.torus((0, 0, 0.0), 1.0, 0.25, (1, 1, 0.5), segs=(40, 10))
    mb.mi = 2
    mb.lathe([(0.001, -0.45), (0.85, -0.05), (0.95, 0.02)], 40)
    mb.mi = 1
    for ring, (R, n, h, tilt) in enumerate(((1.0, 18, 0.45, 0.35), (0.78, 14, 0.32, 0.55))):
        for i in range(n):
            a = 2 * math.pi * (i + 0.5 * ring) / n
            base = V((R * math.cos(a), R * math.sin(a), 0.08))
            inward = V((-math.cos(a), -math.sin(a), 0))
            tip = base + inward * h * tilt + V((0, 0, h * rnd.uniform(0.8, 1.15)))
            mb.cyl(base, tip, 0.07, 0.006, segs=8)
    mb.obj("Lawn_Maw", [M["gum"], M["bone"], M["throat"]]).parent = root
    return {"name": "Lawn maw", "cat": "Creatures", "behaviors": ["pulse"],
            "light": {"type": "point", "color": "#ff2010", "intensity": 4, "offset": [0, 0.2, 0]},
            "desc": "A ring of fangs where the lawn should be, glowing from the throat."}


def p_bone_throne(M):
    root = root_empty("bone_throne")
    mb = MB()
    for x in (-0.35, 0.35):
        for y in (-0.3, 0.3):
            mb.cyl((x, y, 0), (x, y, 0.5), 0.03, segs=8)
            mb.sphere((x, y, 0.5), 0.05)
    for i in range(9):   # seat of crossed femurs
        x = -0.36 + i * 0.09
        mb.cyl((x, -0.32, 0.52), (x, 0.32, 0.52), 0.022, segs=8)
    for i in range(11):   # tall back
        x = -0.38 + i * 0.076
        h = 1.7 - 0.4 * abs(i - 5) / 5
        mb.cyl((x, 0.33, 0.5), (x, 0.42, h), 0.02, segs=8)
    for sx in (-1, 1):
        mb.cyl((0.4 * sx, -0.3, 0.8), (0.4 * sx, 0.33, 0.85), 0.03, segs=8)
    for i in range(5):   # crown of skulls on top
        x = -0.32 + i * 0.16
        z = 1.75 - 0.35 * abs(i - 2) / 2
        mb.mi = 0
        mb.sphere((x, 0.42, z), 0.08, (0.85, 1.05, 1.0))
        mb.mi = 1
        for sx in (-1, 1):
            mb.sphere((x + 0.028 * sx, 0.355, z + 0.005), 0.02)
    for sx in (-1, 1):
        mb.mi = 0
        mb.sphere((0.4 * sx, -0.32, 0.88), 0.07, (0.85, 1.05, 1.0))
    mb.obj("Bone_Throne", [M["bone_real"], M["eye_red"]]).parent = root
    return {"name": "Bone throne", "cat": "Bones", "desc": "A throne of femurs and skulls. Seat a skeleton in it."}


def p_crow(M):
    root = root_empty("crow_post")
    mb = MB(); mb.smooth = False
    mb.box((0, 0, 0.6), (0.1, 0.1, 1.2))
    mb.smooth = True
    mb.obj("Crow_Post", [M["wood_stake"]]).parent = root
    head = empty("Head", (0, -0.06, 1.47), None, 0.05)
    head.parent = root
    b = MB()
    b.mi = 0
    b.sphere((0, 0.06, 1.33), 0.11, (0.75, 1.4, 0.8))
    b.cyl((0, 0.18, 1.3), (0, 0.38, 1.27), 0.05, 0.01, segs=8)
    b.obj("Crow_Body", [M["chitin"]]).parent = root
    h = MB()
    h.sphere((0, 0, 0), 0.06)
    h.mi = 1
    h.cyl((0, -0.04, -0.01), (0, -0.15, -0.03), 0.022, 0.001, segs=8)
    h.mi = 2
    for sx in (-1, 1):
        h.sphere((0.035 * sx, -0.03, 0.015), 0.012)
    h.obj("Crow_Head", [M["chitin"], M["iron"], M["eye_red"]]).parent = head
    return {"name": "Crow on a post", "cat": "Creatures", "behaviors": ["peck"],
            "desc": "Red-eyed crow that jerks its head around."}


# ---- the 2026 display, as reusable pieces
def p_stave(M):
    root = root_empty("antler_stave")
    s = BP.stave("Stave", bpy.context.scene.collection, M, (0, 0, 0), 2.35, 0, "deer", 1.15, (0, 0))
    s.parent = root
    return {"name": "Antler stave", "cat": "2026 display", "desc": "Pole topped with a twine-wrapped deer skull."}


def p_girl(M):
    root = root_empty("jawbone_girl")
    g, hz = BP.mannequin("Girl", bpy.context.scene.collection, M, (0, 0, 0), 0.0, 1.27, None)
    BP.mandible_headpiece("Girl_Mandible", bpy.context.scene.collection, M, g, hz)
    g.parent = root
    return {"name": "Jawbone girl", "cat": "2026 display", "desc": "Bald mannequin girl with a cow jawbone strapped on."}


def p_girl_hair(M):
    root = root_empty("mannequin_girl")
    g, hz = BP.mannequin("Girl", bpy.context.scene.collection, M, (0, 0, 0), 0.0, 1.3, "long")
    g.parent = root
    return {"name": "Mannequin girl", "cat": "2026 display", "desc": "Long-haired girl in a peach dress."}


def p_horned(M):
    root = root_empty("horned_figure")
    C = bpy.context.scene.collection
    body = BP.horned_figure(C, M)
    for ob in list(C.objects):
        if ob.parent is None and ob is not root:
            ob.location.x -= 1.5; ob.location.y += 2.86; ob.location.z -= 0.88
    return {"name": "Horned figure", "cat": "2026 display", "desc": "Tan-gowned mannequin wearing an oryx skull."}


def p_cairn(M):
    root = root_empty("stone_cairn")
    C = bpy.context.scene.collection
    BP.build_cairn(C, M)
    for ob in list(C.objects):
        if ob.parent is None and ob is not root:
            ob.location.x -= BP.CAIRN.x; ob.location.y -= BP.CAIRN.y
    return {"name": "Stone cairn + elk skull", "cat": "2026 display", "desc": "Fieldstone cairn with string lights and an elk skull."}


def p_elk(M):
    root = root_empty("elk_skull")
    BP.deer_skull("Elk", bpy.context.scene.collection, M, (0, 0, 0.12), (math.radians(18), 0, 0), 1.25, "elk").parent = root
    return {"name": "Elk skull", "cat": "Bones", "desc": "Weathered elk skull with a full rack."}


PROPS = {
    "skeleton": p_skeleton, "skeleton_dog": p_dog, "giant_spider": p_spider, "bone_serpent": p_serpent,
    "lawn_tentacles": p_tentacles, "giant_skull": p_giant_skull, "skull_pile": p_skull_pile,
    "grasping_arms": p_grasping_arms, "ribcage_arch": p_rib_arch, "eyeball_tree": p_eyeball_tree,
    "coffin": p_coffin, "tombstone_rip": lambda M: p_tombstone(M, "round"),
    "tombstone_cross": lambda M: p_tombstone(M, "cross"), "obelisk": lambda M: p_tombstone(M, "obelisk"),
    "iron_fence": p_fence, "cauldron": p_cauldron, "jack_o_lantern": p_jack, "pumpkin_totem": p_pumpkin_totem,
    "scarecrow": p_scarecrow, "plague_doctor": p_plague_doctor, "ghost": p_ghost, "hanging_cage": p_hanging_cage,
    "bat_swarm": p_bats, "giant_moth": p_moth, "spider_web": p_web, "candelabra": p_candelabra,
    "crystal_ball": p_crystal_ball, "lawn_maw": p_lawn_maw, "bone_throne": p_bone_throne, "crow_post": p_crow,
    "elk_skull": p_elk, "antler_stave": p_stave, "jawbone_girl": p_girl, "mannequin_girl": p_girl_hair,
    "horned_figure": p_horned, "stone_cairn": p_cairn,
}


# ===================================================================== export + thumbnail
def finalize_and_export(pid, info):
    s = bpy.context.scene
    root = s.objects[pid]
    parent_all(root)
    dg = bpy.context.evaluated_depsgraph_get()
    for ob in list(s.objects):   # curves/text -> meshes so they export cleanly
        if ob.type in ("CURVE", "FONT"):
            me = bpy.data.meshes.new_from_object(ob.evaluated_get(dg), depsgraph=dg)
            new = bpy.data.objects.new(ob.name, me)
            s.collection.objects.link(new)
            new.parent = ob.parent
            new.matrix_world = ob.matrix_world.copy()
            for ch in list(ob.children):
                mw = ch.matrix_world.copy(); ch.parent = new; ch.matrix_world = mw
            bpy.data.objects.remove(ob)
    bpy.context.view_layer.update()
    # bounds (evaluated, world)
    dg = bpy.context.evaluated_depsgraph_get()
    lo, hi = V((1e9,) * 3), V((-1e9,) * 3)
    tris = 0
    for ob in s.objects:
        if ob.type != "MESH":
            continue
        ev = ob.evaluated_get(dg); me = ev.to_mesh()
        for v in me.vertices:
            p = ob.matrix_world @ v.co
            lo = V(map(min, lo, p)); hi = V(map(max, hi, p))
        tris += sum(len(p.vertices) - 2 for p in me.polygons)
        ev.to_mesh_clear()
    rigged = any(o.type == "ARMATURE" for o in s.objects)
    bones = None
    import re
    san = lambda n: re.sub(r"[\[\]\.:/]", "", re.sub(r"\s", "_", n))
    for o in s.objects:
        if o.type == "ARMATURE":
            mw = o.matrix_world
            g = lambda v: [round(v.x, 4), round(v.z, 4), round(-v.y, 4)]
            bones = [{"n": san(b.name), "h": g(mw @ b.head_local), "t": g(mw @ b.tail_local),
                      "p": san(b.parent.name) if b.parent else None} for b in o.data.bones]
            info["bones"] = bones
    path = os.path.join(OUT, pid + ".glb")
    bpy.ops.export_scene.gltf(filepath=path, export_format="GLB", export_apply=True, export_skins=True,
                              export_animations=False, export_lights=False, export_cameras=False,
                              export_draco_mesh_compression_enable=not rigged, export_yup=True)
    thumb(pid, lo, hi)
    info.update({"id": pid, "file": f"props/{pid}.glb", "thumb": f"props/thumbs/{pid}.jpg",
                 "size": [round(hi.x - lo.x, 2), round(hi.z - lo.z, 2), round(hi.y - lo.y, 2)],
                 "tris": tris, "kb": os.path.getsize(path) // 1024})
    return info


def thumb(pid, lo, hi):
    s = bpy.context.scene
    c = (lo + hi) / 2
    R = max((hi - lo).length / 2, 0.1)
    cd = bpy.data.cameras.new("thumbcam"); cd.lens = 50
    cam = bpy.data.objects.new("thumbcam", cd); s.collection.objects.link(cam)
    d = V((0.75, -1.0, 0.45)).normalized()
    fov = 2 * math.atan(18 / 50)
    cam.location = c + d * (R / math.sin(fov / 2) * 1.02)
    look_at(cam, c)
    s.camera = cam
    for name, loc, energy, col in [("key", c + V((2, -3, 3)) * R, 600, (1, 0.95, 0.9)),
                                   ("rim", c + V((-2.5, 2.5, 1.5)) * R, 500, (1, 0.15, 0.08)),
                                   ("fill", c + V((-3, -2, 0.5)) * R, 150, (0.5, 0.6, 1.0))]:
        L = bpy.data.lights.new(name, "POINT"); L.energy = energy * R * R; L.color = col; L.shadow_soft_size = R * 0.5
        o = bpy.data.objects.new(name, L); s.collection.objects.link(o); o.location = loc
    if not s.world:
        s.world = bpy.data.worlds.new("w")
    s.world.use_nodes = True
    s.world.node_tree.nodes["Background"].inputs[0].default_value = (0.02, 0.02, 0.03, 1)
    s.world.node_tree.nodes["Background"].inputs[1].default_value = 0.5
    s.render.engine = "CYCLES"; s.cycles.samples = 24; s.cycles.use_denoising = True
    s.render.resolution_x = s.render.resolution_y = 256
    s.render.film_transparent = True
    try:
        s.view_settings.view_transform = "AgX"
    except Exception:
        pass
    tmp = os.path.join(OUT, "thumbs", pid + ".png")
    s.render.filepath = tmp
    bpy.ops.render.render(write_still=True)
    from PIL import Image
    im = Image.open(tmp).convert("RGBA")
    bg = Image.new("RGBA", im.size, (18, 14, 16, 255))
    bg.alpha_composite(im)
    bg.convert("RGB").save(os.path.join(OUT, "thumbs", pid + ".jpg"), quality=86)
    os.remove(tmp)


if __name__ == "__main__":
    from props_occult import OCCULT
    PROPS.update(OCCULT)
    cat_path = os.path.join(OUT, "catalog.json")
    catalog = json.load(open(cat_path)) if os.path.exists(cat_path) else {}
    for pid, fn in PROPS.items():
        if ONLY and pid not in ONLY:
            continue
        try:
            M = fresh()
            info = fn(M)
            catalog[pid] = finalize_and_export(pid, info)
            catalog[pid]["order"] = list(PROPS).index(pid)
            print("PROP_OK", pid, catalog[pid]["kb"], "KB", catalog[pid]["tris"], "tris", flush=True)
        except Exception:
            print("PROP_FAIL", pid, flush=True)
            traceback.print_exc()
        json.dump(catalog, open(cat_path, "w"), indent=1)
