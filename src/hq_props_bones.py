"""Batch A — bones and rigged creatures (HQ sculpts)."""
import math, random
import numpy as np
import bpy
from mathutils import Vector as V, Matrix, Euler
import props_lib as PL
import build_props as BP
import hq_lib as H
import sdf as S
import hq_skeleton as SK
import hq_animal as A
from hq_skull_sdf import cranium_sdf, mandible_sdf, teeth_sdf
from hq_registry import hq

E, C, B, CH = S.ellipsoid, S.cone, S.blade, S.chain


def mk(node, name, vox, mat, target=None, smooth=1):
    return S.mesh(node, name, vox, [mat], target=target, smooth=smooth)


def mat4(loc=(0, 0, 0), rot=(0, 0, 0), s=1.0):
    return Matrix.Translation(loc) @ Euler(rot).to_matrix().to_4x4() @ Matrix.Scale(s, 4)


def parent(objs, root):
    for o in objs:
        mw = o.matrix_world.copy(); o.parent = root; o.matrix_world = mw


def skull_objs(M, name, vox=0.0016, jaw=True, targets=(6000, 2000, 1400), mat="bone"):
    """A full-size human skull as 2-3 meshes in skull space (origin = cranium centre)."""
    sk = S.noisy(S.noisy(cranium_sdf(), 0.001, 22, 2), 0.0004, 90, 2)
    out = [mk(sk, name + "_cranium", vox, M[mat], targets[0])]
    if jaw:
        out.append(mk(S.noisy(mandible_sdf(), 0.0004, 90, 2), name + "_jaw", vox, M[mat], targets[1]))
        out.append(mk(S.union(teeth_sdf(True), teeth_sdf(False)), name + "_teeth", 0.0008, M["tooth"], targets[2]))
    else:
        out.append(mk(teeth_sdf(True), name + "_teeth", 0.0008, M["tooth"], targets[2] // 2))
    return out


def long_bone(a, b, r, knob=1.45):
    """Generic femur-like long bone between a and b."""
    a, b = np.asarray(a, float), np.asarray(b, float)
    d = (b - a) / np.linalg.norm(b - a)
    side = np.cross(d, (0, 0, 1.0))
    if np.linalg.norm(side) < 1e-3:
        side = np.cross(d, (1.0, 0, 0))
    side /= np.linalg.norm(side)
    parts = [C(a + d * r, b - d * r, r * 1.05, r * 0.95)]
    for p, sgn in ((a, 1), (b, -1)):
        parts.append(S.sphere(p + side * r * 0.75 + d * sgn * r * 0.4, r * knob * 0.85))
        parts.append(S.sphere(p - side * r * 0.75 + d * sgn * r * 0.4, r * knob * 0.8))
    return S.noisy(S.union(*parts, k=r * 1.2), r * 0.04, 0.8 / r, 2)


def vert_local(rb, h, kind="T", spine=1.0):
    """Vertebra at the origin: body along local Z, spinous process toward local +Y."""
    parts = [C((0, 0, -h / 2), (0, 0, h / 2), rb, rb * 1.02)]
    canal = np.array((0, rb + 0.45 * rb, 0))
    parts.append(S.torus(canal, 0.57 * rb, 0.17 * rb))
    sp = rb * 1.5 * spine
    parts.append(B([canal + (0, 0.35 * rb, 0), canal + (0, sp, -0.4 * rb)], 0.15 * rb, 0.3 * rb, nrm=(1, 0, 0)))
    for sx in (-1, 1):
        parts.append(C(canal + (sx * 0.3 * rb, -0.1 * rb, 0), canal + (sx * 1.4 * rb, 0.25 * rb, 0), 0.2 * rb, 0.15 * rb))
    return S.union(*parts, k=0.2 * rb)


# =========================================================================== skeleton
@hq("skeleton", 1536)
def skeleton(M):
    root = PL.root_empty("skeleton")
    ob = SK.build("Skeleton_Body", M)
    rig = PL.make_rig("Skeleton", BP.BONES, BP.ORDER)
    PL.skin(ob, rig, BP.ORDER)
    rig.parent = root
    return {"name": "Skeleton", "cat": "Bones", "rig": "human",
            "desc": "Anatomical, life-size and fully articulated: 24 vertebrae, 24 ribs, sculpted skull. Pick a pose or rotate any joint."}


# =========================================================================== skulls
@hq("giant_skull", 1024)
def giant_skull(M):
    root = PL.root_empty("giant_skull")
    K = 7.0
    sk = S.noisy(S.noisy(cranium_sdf(), 0.0012, 20, 3, ridged=True), 0.0004, 80, 2)
    objs = [mk(sk, "Giant_Skull", 0.0013, M["bone_old"], 22000),
            mk(S.noisy(mandible_sdf(), 0.0005, 70, 2), "Giant_Jaw", 0.0013, M["bone_old"], 6000),
            mk(S.union(teeth_sdf(True), teeth_sdf(False)), "Giant_Teeth", 0.0007, M["tooth"], 3000)]
    for sx in (-1, 1):
        mb = BP.MB(); mb.sphere((sx * 0.031, -0.082, -0.03), 0.012, segs=(16, 10))
        objs.append(mb.obj("Eye_Glow_" + ("L" if sx > 0 else "R"), [M["eye_red"]]))
    for o in objs:
        o.matrix_world = mat4((0, 0, 0.137 * K), (0, 0, 0), K) @ o.matrix_world
    parent(objs, root)
    return {"name": "Giant skull", "cat": "Bones", "behaviors": ["pulse"],
            "light": {"type": "point", "color": "#ff2210", "intensity": 6, "offset": [0, 1.1, 0.7]},
            "desc": "1.5 m sculpted skull, weathered and cracked, with pulsing red eyes."}


@hq("skull_pile", 1024)
def skull_pile(M):
    root = PL.root_empty("skull_pile")
    rnd = random.Random(4)
    variants = []
    for v in range(2):
        cr = S.noisy(S.noisy(cranium_sdf(), 0.0012 + 0.0004 * v, 18 + 6 * v, 2, ridged=bool(v)), 0.0004, 90, 2)
        a = mk(cr, f"PileSkull{v}", 0.0019, M["bone_old" if v else "bone"], 2600)
        t = mk(teeth_sdf(True), f"PileTeeth{v}", 0.001, M["tooth"], 500)
        variants.append(H.join([a, t], f"PileSkull{v}"))
    layers = [(0.56, 0.0, 14), (0.4, 0.15, 10), (0.24, 0.3, 6), (0.08, 0.44, 2), (0.0, 0.56, 1)]
    objs = []
    for R, z, n in layers:
        for j in range(n):
            a = 2 * math.pi * j / n + z * 3
            c = V((R * math.cos(a), R * math.sin(a), z + 0.085))
            yaw = (math.atan2(c.y, c.x) + math.pi / 2) if R > 0 else 0
            yaw += rnd.uniform(-0.35, 0.35)
            rot = (rnd.uniform(-0.15, 0.12), rnd.uniform(-0.2, 0.2), yaw)
            src = variants[rnd.randrange(2)]
            objs.append(H.instance(src, f"Skull_{len(objs):02d}", mat4(c, rot, rnd.uniform(1.05, 1.15))))
    lb = []
    for i in range(7):
        a = 2 * math.pi * i / 7 + 0.4
        p = np.array((0.78 * math.cos(a), 0.78 * math.sin(a), 0.02))
        d = np.array((-math.sin(a), math.cos(a), 0.0)) * 0.22
        lb.append(long_bone(p - d, p + d, 0.016))
    objs.append(mk(S.union(*lb), "Loose_Bones", 0.002, M["bone_old"], 3500))
    for v in variants:
        bpy.data.objects.remove(v)
    parent(objs, root)
    return {"name": "Ossuary pile", "cat": "Bones", "desc": "Pyramid of 33 sculpted skulls facing out, ringed with long bones."}


# =========================================================================== arms, ribs, throne
@hq("grasping_arms", 1024)
def grasping_arms(M):
    root = PL.root_empty("grasping_arms")
    rnd = random.Random(9)
    objs = []
    for i in range(6):
        a = 2 * math.pi * i / 6 + rnd.uniform(-0.3, 0.3)
        r = rnd.uniform(0.15, 0.5)
        base = (r * math.cos(a), r * math.sin(a), rnd.uniform(-0.12, -0.02))
        tilt = rnd.uniform(0.15, 0.55)
        Mx = mat4(base, (0, 0, a - math.pi / 2)) @ mat4((0, 0, 0), (math.pi - tilt, 0, 0), 1.4) @ mat4((-0.18, 0, -1.2))
        curl = rnd.uniform(0.25, 1.05)
        fa = mk(S.noisy(SK.forearm(1), 0.0004, 100, 2), f"Arm{i}_forearm", 0.0016, M["bone_old"], 900)
        hd = mk(S.noisy(SK.hand(1, curl), 0.0003, 120, 2), f"Arm{i}_hand", 0.001, M["bone_old"], 2200)
        for o in (fa, hd):
            o.matrix_world = Mx
        objs += [fa, hd]
    mound = S.warp(S.noisy(E((0, 0, -0.06), (0.85, 0.8, 0.17)), 0.02, 4, 3), 0.04, 2.5)
    clods = [S.noisy(S.sphere((0.9 * math.cos(t), 0.85 * math.sin(t), 0.0), rnd.uniform(0.04, 0.09)), 0.015, 12, 2)
             for t in np.linspace(0, 2 * math.pi, 11)[:-1] + rnd.uniform(0, 0.3)]
    objs.append(mk(S.union(mound, *clods, k=0.05), "Dirt_Mound", 0.012, M["dirt"], 6000))
    parent(objs, root)
    return {"name": "Grasping arms", "cat": "Bones", "desc": "Six anatomical skeletal arms clawing up out of a churned dirt mound."}


@hq("ribcage_arch", 1024)
def ribcage_arch(M):
    root = PL.root_empty("ribcage_arch")
    objs = []
    n = 7
    for i in range(n):
        y = -1.8 + i * 0.6
        s = 1.0 - 0.25 * abs(i - n / 2 + 0.5) / (n / 2)
        ribs = []
        for sx in (-1, 1):
            pts = [(sx * 1.3 * s * math.cos(th) * (1 + 0.06 * math.sin(2 * th)), y, -0.15 + (2.4 * s + 0.15) * math.sin(th))
                   for th in np.linspace(0.0, math.pi / 2 - 0.04, 12)]
            pts.append((sx * 0.1, y, 2.38))
            rr = [0.1 * s * (1.05 - 0.25 * f) for f in np.linspace(0, 1, len(pts))]
            ribs.append(B(pts, [0.042 * s] * len(pts), rr, nrm=(0, 1, 0), k=0.02))
            ribs.append(E((sx * 0.13, y, 2.36), (0.06, 0.05, 0.05)))
        node = S.noisy(S.noisy(S.union(*ribs, k=0.03), 0.006, 3, 2), 0.002, 25, 2)
        objs.append(mk(node, f"Rib_{i}", 0.01, M["bone_old"], 2600))
    verts = [S.orient(vert_local(0.11, 0.2, spine=1.4), (0, -2.0 + i * 0.32, 2.43), (0, 1, 0), (0, 0, 1)) for i in range(14)]
    objs.append(mk(S.noisy(S.union(*verts), 0.004, 8, 2), "Spine", 0.012, M["bone_old"], 7000))
    mb = BP.MB()
    for i in range(n):
        y = -1.8 + i * 0.6
        mb.cyl((0, y, 2.32), (0, y, 2.2), 0.004, segs=4)
        mb.sphere((0, y, 2.17), 0.04, segs=(12, 8))
    objs.append(mb.obj("LED_Drops", [M["led_red"]]))
    parent(objs, root)
    return {"name": "Ribcage archway", "cat": "Bones",
            "desc": "Walk-through tunnel of giant flat ribs under a vertebral ridge, 2.6 m tall, with red LED drops."}


@hq("bone_throne", 1024)
def bone_throne(M):
    root = PL.root_empty("bone_throne")
    rnd = random.Random(12)
    objs = []
    legs = [long_bone((x, y, 0.0), (x, y, 0.5), 0.028) for x in (-0.35, 0.35) for y in (-0.3, 0.3)]
    seat = [long_bone((-0.38 + i * 0.095, -0.34, 0.53 + 0.006 * (i % 2)), (-0.38 + i * 0.095, 0.34, 0.53 + 0.006 * ((i + 1) % 2)), 0.022)
            for i in range(9)]
    rails = [long_bone((-0.43, y, 0.5), (0.43, y, 0.5), 0.024) for y in (-0.32, 0.32)]
    objs.append(mk(S.union(*legs, *seat, *rails, k=0.012), "Throne_Base", 0.004, M["bone_old"], 9000))
    back = []
    for i in range(11):
        x = -0.4 + i * 0.08
        h = 1.65 - 0.38 * abs(i - 5) / 5
        back.append(long_bone((x * 0.95, 0.33, 0.5), (x, 0.42, h), 0.019 + 0.004 * (i % 2)))
    for k in range(4):     # ribs woven across the back
        z = 0.75 + k * 0.2
        pts = [(x, 0.4 - 0.03 * math.cos(x * 6), z + 0.02 * math.sin(x * 9)) for x in np.linspace(-0.42, 0.42, 9)]
        back.append(B(pts, 0.006, 0.014, nrm=(0, 1, 0), k=0.004))
    objs.append(mk(S.union(*back, k=0.008), "Throne_Back", 0.0035, M["bone_old"], 8000))
    arms = [long_bone((0.42 * sx, -0.34, 0.82), (0.42 * sx, 0.35, 0.86), 0.028) for sx in (-1, 1)]
    arms += [long_bone((0.42 * sx, -0.3, 0.52), (0.42 * sx, -0.3, 0.8), 0.02) for sx in (-1, 1)]
    objs.append(mk(S.union(*arms, k=0.01), "Throne_Arms", 0.0035, M["bone_old"], 3000))
    master = H.join(skull_objs(M, "ThroneSkull", 0.0019, jaw=True, targets=(2600, 900, 500)), "ThroneSkull")
    for i in range(5):
        x = -0.32 + i * 0.16
        z = 1.72 - 0.36 * abs(i - 2) / 2
        objs.append(H.instance(master, f"Crown_Skull_{i}", mat4((x, 0.44, z), (0.1, 0, rnd.uniform(-0.25, 0.25)), 0.85)))
    for sx in (-1, 1):
        objs.append(H.instance(master, f"Arm_Skull_{sx + 1}", mat4((0.42 * sx, -0.36, 0.93), (0, 0, -0.3 * sx), 0.95)))
    bpy.data.objects.remove(master)
    parent(objs, root)
    return {"name": "Bone throne", "cat": "Bones", "desc": "A throne of knobbed femurs, woven ribs and a crown of skulls. Seat a skeleton in it."}


# =========================================================================== cervids
def cervid(M, name, kind, k, ant_scale, ant_k):
    sk, th = A.deer_skull_sdf(k)
    sk = S.noisy(sk, 0.0005 * k, 80 / k, 2)
    return [mk(sk, name + "_Skull", 0.0016 * k, M["bone_old"], 7000),
            mk(th, name + "_Teeth", 0.0012 * k, M["tooth"], 800),
            mk(A.antlers_sdf(kind, ant_scale, ant_k), name + "_Antlers", 0.0028 * ant_scale, M["antler"], 9000)]


@hq("elk_skull", 1024)
def elk_skull(M):
    root = PL.root_empty("elk_skull")
    objs = cervid(M, "Elk", "elk", 1.69, 1.25, 1.69)
    for o in objs:
        o.matrix_world = mat4((0, 0, 0.14), (math.radians(18), 0, 0)) @ o.matrix_world
    parent(objs, root)
    return {"name": "Elk skull", "cat": "Bones", "desc": "Weathered elk skull with a full, ridged rack."}


@hq("antler_stave", 1024)
def antler_stave(M):
    root = PL.root_empty("antler_stave")
    h = 2.35
    pole = S.noisy(S.noisy(S.box((0, 0, h / 2 - 0.12), (0.075, 0.035, h + 0.24), 0.006), 0.003, 6, 3, stretch=(1, 1, 0.06)), 0.0008, 60, 2)
    objs = [mk(pole, "Stave_Pole", 0.003, M["wood_raw"], 2500)]
    rnd = random.Random(5)
    tw = [S.torus((0, 0, h - 0.18 + 0.022 * i), 0.044, 0.0045, S.rotm(rnd.uniform(-0.3, 0.3), rnd.uniform(-0.3, 0.3), 0)) for i in range(8)]
    objs.append(mk(S.noisy(S.union(*tw, k=0.002), 0.0008, 200, 1), "Stave_Twine", 0.0015, M["burlap"], 3000))
    sk = cervid(M, "Stave", "deer", 1.15, 1.15, 1.15)
    for o in sk:
        o.matrix_world = mat4((0, -0.07, h - 0.1), (math.radians(38), 0, 0)) @ o.matrix_world
    objs += sk
    parent(objs, root)
    return {"name": "Antler stave", "cat": "2026 display", "desc": "Split pole topped with a twine-wrapped deer skull and antlers."}


# =========================================================================== rigged creatures
DOG_B = {"hips": ((0, 0.3, 0.55), (0, 0.14, 0.58), None),
         "spine": ((0, 0.14, 0.58), (0, -0.12, 0.6), "hips"),
         "chest": ((0, -0.12, 0.6), (0, -0.3, 0.62), "spine"),
         "neck": ((0, -0.3, 0.62), (0, -0.42, 0.8), "chest"),
         "head": ((0, -0.42, 0.8), (0, -0.66, 0.76), "neck"),
         "tail1": ((0, 0.32, 0.56), (0, 0.48, 0.62), "hips"),
         "tail2": ((0, 0.48, 0.62), (0, 0.64, 0.7), "tail1"),
         "tail3": ((0, 0.64, 0.7), (0, 0.8, 0.8), "tail2")}
for _s, _sx in (("L", 1), ("R", -1)):
    _x = 0.09 * _sx
    DOG_B.update({f"front_upper.{_s}": ((_x, -0.27, 0.55), (_x, -0.29, 0.33), "chest"),
                  f"front_lower.{_s}": ((_x, -0.29, 0.33), (_x, -0.27, 0.08), f"front_upper.{_s}"),
                  f"front_paw.{_s}": ((_x, -0.27, 0.08), (_x, -0.35, 0.02), f"front_lower.{_s}"),
                  f"hind_upper.{_s}": ((_x, 0.28, 0.52), (_x, 0.2, 0.32), "hips"),
                  f"hind_lower.{_s}": ((_x, 0.2, 0.32), (_x, 0.33, 0.09), f"hind_upper.{_s}"),
                  f"hind_paw.{_s}": ((_x, 0.33, 0.09), (_x, 0.26, 0.02), f"hind_lower.{_s}")})


def along(bone, n, B_):
    h, t = np.array(B_[bone][0]), np.array(B_[bone][1])
    return [(h + (t - h) * (i + 0.5) / n, (h - t) / np.linalg.norm(h - t)) for i in range(n)]


def dog_skull():
    braincase = E((0, -0.465, 0.83), (0.042, 0.052, 0.042))
    crest = B([(0, -0.43, 0.86), (0, -0.48, 0.872), (0, -0.52, 0.86)], 0.004, 0.012, nrm=(1, 0, 0))
    snout = S.union(C((0, -0.515, 0.81), (0, -0.665, 0.77), 0.034, 0.016),
                    B([(0, -0.52, 0.835), (0, -0.66, 0.785)], 0.014, 0.006, nrm=(1, 0, 0)), k=0.01)
    zyg = [B([(sx * 0.03, -0.535, 0.8), (sx * 0.058, -0.5, 0.795), (sx * 0.045, -0.455, 0.795)], 0.004, 0.009, nrm=(1, 0, 0)) for sx in (-1, 1)]
    occ = E((0, -0.42, 0.815), (0.035, 0.012, 0.03))
    sk = S.union(braincase, crest, snout, occ, *zyg, k=0.014)
    sk = S.sub(sk, *[S.sphere((sx * 0.036, -0.535, 0.825), 0.017) for sx in (-1, 1)], E((0, -0.67, 0.775), (0.01, 0.02, 0.012)), k=0.003)
    jaw = S.union(*[B([(sx * 0.04, -0.455, 0.775), (sx * 0.038, -0.5, 0.758), (sx * 0.022, -0.6, 0.75), (sx * 0.01, -0.66, 0.748)],
                      0.005, [0.018, 0.012, 0.011, 0.009], nrm=(0, 0, 1)) for sx in (-1, 1)], k=0.012)
    teeth = []
    for sx in (-1, 1):
        teeth.append(C((sx * 0.02, -0.645, 0.77), (sx * 0.022, -0.65, 0.735), 0.0055, 0.0012))
        teeth.append(C((sx * 0.016, -0.652, 0.75), (sx * 0.018, -0.645, 0.78), 0.0045, 0.001))
        for i in range(5):
            y = -0.625 + i * 0.026
            teeth.append(C((sx * (0.022 + i * 0.004), y, 0.768), (sx * (0.022 + i * 0.004), y + 0.004, 0.755), 0.006, 0.0015))
        for i in range(3):
            teeth.append(C((sx * 0.0036 * (i + 1), -0.664, 0.768), (sx * 0.0036 * (i + 1), -0.666, 0.758), 0.0025, 0.001))
    return S.union(sk, jaw, k=0.004), S.union(*teeth, k=0.001)


def paw(h, t, n=4, r=0.008):
    h, t = np.array(h), np.array(t)
    d = t - h
    parts = [E(h + d * 0.15, (0.024, 0.02, 0.02))]
    for i in range(n):
        ox = (i - (n - 1) / 2) * 0.014
        base = h + d * 0.2 + np.array((ox, 0, 0))
        k1 = h + d * 0.8 + np.array((ox * 1.25, 0, 0))
        k2 = k1 + np.array((ox * 0.1, -0.03, -0.012))
        k3 = k2 + np.array((0, -0.025, -0.012))
        parts += [CH([base, k1, k2], [r, r * 0.8, r * 0.75], k=0.003), C(k2, k3, r * 0.6, 0.0015)]
    return S.union(*parts, k=0.004)


@hq("skeleton_dog", 1024)
def skeleton_dog(M):
    root = PL.root_empty("skeleton_dog")
    order = list(DOG_B)
    G = {}

    def add(g, node):
        G.setdefault(g, []).append(node)
    for g, n, rb in (("neck", 5, 0.018), ("chest", 4, 0.02), ("spine", 6, 0.021), ("hips", 4, 0.02)):
        for c, d in along(g, n, DOG_B):
            add(g, S.orient(vert_local(rb, rb * 1.25, spine=1.6 if g == "chest" else 1.0), c, d, (0, 0, 1)))
    for i, t in enumerate(("tail1", "tail2", "tail3")):
        for c, d in along(t, 4, DOG_B):
            add(t, S.orient(vert_local(0.011 - 0.0025 * i, 0.03, spine=0.5), c, d, (0, 0, 1)))
    for i in range(10):
        y = -0.27 + i * 0.042
        zt = 0.6 - 0.02 * (i / 9)
        R = 0.085 + 0.025 * math.sin(i / 9 * math.pi)
        depth = 0.2 - 0.05 * max(0, i - 6) / 3
        g = "chest" if y < -0.12 else "spine"
        for sx in (-1, 1):
            pts = [(sx * 0.02, y, zt), (sx * R * 0.9, y + 0.01, zt - 0.04), (sx * R, y + 0.02, zt - depth * 0.5),
                   (sx * R * 0.6, y + 0.01, zt - depth * 0.9), (sx * 0.012, y - 0.005, zt - depth - 0.01)]
            add(g, B(pts, 0.006, 0.0035, nrm=(0, 1, 0), k=0.003))
    add("chest", CH([(0, -0.3, 0.41), (0, -0.2, 0.39), (0, -0.1, 0.4)], [0.01, 0.009, 0.008], k=0.004))
    for sx in (-1, 1):
        add("chest", E((sx * 0.075, -0.225, 0.58), (0.006, 0.05, 0.035), S.rotm(0.5, 0, 0)))
    pel = []
    for sx in (-1, 1):
        pel.append(B([(sx * 0.03, 0.2, 0.6), (sx * 0.06, 0.24, 0.57), (sx * 0.085, 0.285, 0.52)], 0.006, [0.03, 0.025, 0.015], nrm=(1, 0, 0)))
        pel.append(CH([(sx * 0.085, 0.29, 0.51), (sx * 0.06, 0.36, 0.5), (sx * 0.02, 0.33, 0.46), (sx * 0.08, 0.3, 0.505)], [0.011, 0.009, 0.007, 0.01], k=0.004))
        pel.append(S.sphere((sx * 0.087, 0.283, 0.515), 0.016))
    add("hips", S.union(*pel, k=0.008))
    sk, teeth = dog_skull()
    add("head", sk)
    for s, sx in (("L", 1), ("R", -1)):
        for part, r in (("front_upper", 0.014), ("front_lower", 0.011), ("hind_upper", 0.016), ("hind_lower", 0.012)):
            h, t, _ = DOG_B[f"{part}.{s}"]
            add(f"{part}.{s}", long_bone(h, t, r, knob=1.35))
            if part == "front_lower":
                add(f"{part}.{s}", S.sphere(np.array(h) + (0, 0.025, 0.01), 0.012))
            if part == "hind_lower":
                add(f"{part}.{s}", E(np.array(h) + (0, -0.02, 0.01), (0.012, 0.007, 0.014)))
        add(f"front_paw.{s}", paw(DOG_B[f"front_paw.{s}"][0], DOG_B[f"front_paw.{s}"][1]))
        add(f"hind_paw.{s}", S.union(E(DOG_B[f"hind_paw.{s}"][0], (0.016, 0.03, 0.016)),
                                     paw(DOG_B[f"hind_paw.{s}"][0], DOG_B[f"hind_paw.{s}"][1], r=0.0085), k=0.006))
    objs = []
    for g, nodes in G.items():
        ob = mk(S.noisy(S.union(*nodes), 0.0003, 120, 2), f"Dog_{g}", 0.0013, M["bone"],
                900 if "paw" in g else 1400 if g != "head" else 6000)
        H.assign_group(ob, g)
        objs.append(ob)
    th = mk(teeth, "Dog_teeth", 0.0008, M["tooth"], 1500); H.assign_group(th, "head"); objs.append(th)
    eyes = BP.MB()
    for sx in (-1, 1):
        eyes.sphere((sx * 0.033, -0.535, 0.825), 0.013, segs=(14, 9))
    e = eyes.obj("Dog_eyes", [M["eye_red"]]); H.assign_group(e, "head"); objs.append(e)
    body = H.join(objs, "Dog_Body")
    rig = PL.make_rig("Dog", DOG_B, order)
    PL.skin(body, rig, order)
    rig.parent = root
    return {"name": "Skeleton hound", "cat": "Bones", "rig": "dog",
            "desc": "Anatomical canine skeleton with a keeled ribcage and glowing eyes. Articulated spine, tail and legs."}


def spider_bones():
    Bd = {"body": ((0, 0.25, 0.55), (0, -0.25, 0.55), None)}
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
            Bd[n + "_a"] = (tuple(r0), tuple(knee), "body")
            Bd[n + "_b"] = (tuple(knee), tuple(ank), n + "_a")
            Bd[n + "_c"] = (tuple(ank), tuple(tip), n + "_b")
            legs.append(n)
    return Bd, legs


@hq("giant_spider", 1024)
def giant_spider(M):
    root = PL.root_empty("giant_spider")
    Bd, legs = spider_bones()
    order = list(Bd)
    rnd = random.Random(2)
    objs = []
    ceph = S.union(E((0, -0.12, 0.52), (0.235, 0.27, 0.16)), E((0, -0.22, 0.6), (0.13, 0.12, 0.1)), k=0.06)
    ceph = S.sub(ceph, *[E((0.12 * math.cos(t), -0.12 + 0.14 * math.sin(t), 0.67), (0.012, 0.05, 0.03), S.rotm(0, 0, t))
                         for t in np.linspace(0, 2 * math.pi, 9)[:-1]], k=0.01)
    abd = S.noisy(E((0, 0.5, 0.66), (0.37, 0.52, 0.35)), 0.006, 6, 2)
    rings = [S.torus((0, 0.5 + 0.1 * i, 0.66), 0.33 * math.sqrt(max(0.05, 1 - (0.2 * i) ** 2)), 0.008, S.rotm(math.pi / 2, 0, 0)) for i in range(-3, 4)]
    pedicel = C((0, 0.1, 0.55), (0, 0.2, 0.6), 0.06, 0.08)
    chel = [S.union(E((sx * 0.055, -0.36, 0.5), (0.05, 0.05, 0.075), S.rotm(0.4, 0, 0)),
                    CH([(sx * 0.055, -0.39, 0.45), (sx * 0.05, -0.43, 0.39), (sx * 0.035, -0.4, 0.33)], [0.018, 0.012, 0.003], k=0.006), k=0.02)
            for sx in (-1, 1)]
    palps = [CH([(sx * 0.11, -0.32, 0.5), (sx * 0.17, -0.42, 0.5), (sx * 0.2, -0.5, 0.42)], [0.022, 0.018, 0.012], k=0.01) for sx in (-1, 1)]
    body = S.union(ceph, abd, pedicel, *chel, *palps, k=0.04)
    body = S.union(body, *rings, k=0.02)
    body = S.noisy(S.noisy(body, 0.004, 10, 2), 0.0012, 60, 2)
    ob = mk(body, "Spider_body", 0.006, M["chitin"], 12000); H.assign_group(ob, "body"); objs.append(ob)
    mark = S.move(S.union(cranium_sdf(), mandible_sdf()), dx=0, dy=0.44, dz=0.995, rx=-1.2, s=1.25)
    ob = mk(mark, "Spider_skullmark", 0.0022, M["eye_red"], 3000); H.assign_group(ob, "body"); objs.append(ob)
    mb = BP.MB()
    for x, y, z, r in [(0.05, -0.33, 0.6, 0.035), (-0.05, -0.33, 0.6, 0.035), (0.11, -0.3, 0.62, 0.022), (-0.11, -0.3, 0.62, 0.022),
                       (0.03, -0.3, 0.67, 0.018), (-0.03, -0.3, 0.67, 0.018), (0.14, -0.26, 0.58, 0.015), (-0.14, -0.26, 0.58, 0.015)]:
        mb.sphere((x, y, z), r, segs=(14, 9))
    ob = mb.obj("Spider_eyes", [M["eye_red"]]); H.assign_group(ob, "body"); objs.append(ob)
    for n in legs:
        for seg, r0, r1 in (("_a", 0.05, 0.04), ("_b", 0.04, 0.028), ("_c", 0.028, 0.008)):
            h, t, _ = Bd[n + seg]
            h, t = np.array(h), np.array(t)
            d = (t - h) / np.linalg.norm(t - h)
            parts = [C(h, t, r0, r1), S.sphere(h, r0 * 1.12)]
            for j in range(3):
                p = h + (t - h) * (0.25 + 0.25 * j)
                parts.append(S.torus(p, (r0 + (r1 - r0) * (0.25 + 0.25 * j)) * 0.95, 0.004, S.frame(p, p + d)))
            for j in range(7):
                p = h + (t - h) * rnd.uniform(0.1, 0.9)
                side = np.cross(d, rnd.choice([(0, 0, 1), (1, 0, 0), (0, 1, 0)]))
                if np.linalg.norm(side) < 0.1:
                    continue
                side = side / np.linalg.norm(side)
                rr = r0 + (r1 - r0) * 0.5
                parts.append(C(p + side * rr * 0.6, p + side * (rr + 0.05) + d * 0.04, 0.006, 0.0008))
            node = S.noisy(S.union(*parts, k=0.012), 0.002, 25, 2)
            ob = mk(node, f"Spider_{n}{seg}", 0.004, M["chitin"], 900)
            H.assign_group(ob, n + seg)
            objs.append(ob)
    body = H.join(objs, "Spider_Body")
    rig = PL.make_rig("Spider", Bd, order)
    PL.skin(body, rig, order)
    rig.parent = root
    return {"name": "Giant spider", "cat": "Creatures", "rig": "spider",
            "desc": "3 m leg span, banded bristly legs with 24 posable joints, fangs, eight red eyes and a glowing skull on its back."}


@hq("bone_serpent", 1024)
def bone_serpent(M):
    root = PL.root_empty("bone_serpent")
    N = 16
    Bd, order, prev = {}, [], None
    for i in range(N):
        y0, y1 = 2.4 - i * 0.18, 2.4 - (i + 1) * 0.18
        n = f"seg{i:02d}"
        Bd[n] = ((0, y0, 0.14), (0, y1, 0.14), prev)
        order.append(n); prev = n
    Bd["head"] = ((0, y1, 0.14), (0, y1 - 0.3, 0.14), prev)
    order.append("head")
    objs = []
    for i in range(N):
        n = f"seg{i:02d}"
        k = 0.35 + 0.65 * (i / (N - 1))
        h, t, _ = Bd[n]
        parts = []
        for j in range(3):
            c = np.array(h) + (np.array(t) - np.array(h)) * (j + 0.5) / 3
            parts.append(S.orient(vert_local(0.032 * k, 0.05, spine=1.3), c, (0, -1, 0), (0, 0, 1)))
            if j != 1:
                for sx in (-1, 1):
                    pts = [c + (sx * 0.03 * k, 0, 0.01), c + (sx * 0.1 * k, 0.01, -0.0), c + (sx * 0.13 * k, 0.025, -0.07 * k),
                           c + (sx * 0.11 * k, 0.04, -0.12)]
                    parts.append(B(pts, 0.007 * k + 0.002, 0.004 * k + 0.0015, nrm=(0, 1, 0), k=0.003))
        ob = mk(S.noisy(S.union(*parts, k=0.004), 0.0004, 100, 2), f"Serpent_{n}", 0.0018, M["bone_old"], 1500)
        H.assign_group(ob, n); objs.append(ob)
    hy = Bd["head"][0][1]
    head = S.union(E((0, hy - 0.08, 0.15), (0.07, 0.11, 0.05)),
                   C((0, hy - 0.12, 0.15), (0, hy - 0.3, 0.12), 0.055, 0.018),
                   *[B([(sx * 0.07, hy - 0.04, 0.12), (sx * 0.075, hy - 0.15, 0.11), (sx * 0.03, hy - 0.29, 0.1)], 0.006, 0.01, nrm=(0, 0, 1)) for sx in (-1, 1)], k=0.02)
    head = S.sub(head, *[S.sphere((sx * 0.05, hy - 0.13, 0.17), 0.024) for sx in (-1, 1)], k=0.004)
    jaw = S.union(*[B([(sx * 0.065, hy - 0.03, 0.09), (sx * 0.05, hy - 0.16, 0.08), (sx * 0.015, hy - 0.29, 0.085)], 0.006, 0.012, nrm=(0, 0, 1))
                    for sx in (-1, 1)], k=0.01)
    fangs = S.union(*[C((sx * 0.03, hy - 0.26, 0.11), (sx * 0.032, hy - 0.275, 0.04), 0.01, 0.0012) for sx in (-1, 1)],
                    *[C((sx * 0.05, hy - 0.1 - 0.025 * i, 0.1), (sx * 0.05, hy - 0.11 - 0.025 * i, 0.08), 0.004, 0.0008) for sx in (-1, 1) for i in range(6)], k=0.002)
    ob = mk(S.noisy(S.union(head, jaw, k=0.01), 0.0006, 70, 2), "Serpent_head", 0.0018, M["bone_old"], 5000); H.assign_group(ob, "head"); objs.append(ob)
    ob = mk(fangs, "Serpent_fangs", 0.0009, M["tooth"], 1200); H.assign_group(ob, "head"); objs.append(ob)
    mb = BP.MB()
    for sx in (-1, 1):
        mb.sphere((sx * 0.05, hy - 0.13, 0.168), 0.019, segs=(14, 9))
    ob = mb.obj("Serpent_eyes", [M["eye_green"]]); H.assign_group(ob, "head"); objs.append(ob)
    body = H.join(objs, "Serpent_Body")
    rig = PL.make_rig("Serpent", Bd, order)
    PL.skin(body, rig, order)
    rig.parent = root
    return {"name": "Bone serpent", "cat": "Bones", "rig": "chain",
            "desc": "3 m snake skeleton: 48 vertebrae with ribs, fanged skull, green eyes, 17 joints. Coil it or rear it up."}


@hq("lawn_tentacles", 1024)
def lawn_tentacles(M):
    root = PL.root_empty("lawn_tentacles")
    bases = [(-0.4, 0.1, 1.6, 0.4), (0.35, -0.15, 1.3, -0.3), (0.05, 0.45, 2.0, 0.1), (0.6, 0.4, 1.1, -0.6)]
    Bd, order = {}, []
    objs = []
    for t, (x, y, h, lean) in enumerate(bases):
        prev = None
        pts = [np.array((x + lean * 0.4 * f * f, y + 0.25 * math.sin(f * 2.5 + t), -0.05 + h * f)) for f in np.linspace(0, 1, 9)]
        names = []
        for i in range(8):
            n = f"t{t}_{i}"
            Bd[n] = (tuple(pts[i]), tuple(pts[i + 1]), prev)
            order.append(n); names.append(n); prev = n
        rad = [0.13 * (1 - i / 8) + 0.012 for i in range(9)]
        fine, frad = [], []
        for i in range(8):
            for u in np.linspace(0, 1, 4, endpoint=False):
                fine.append(pts[i] * (1 - u) + pts[i + 1] * u); frad.append(rad[i] * (1 - u) + rad[i + 1] * u)
        fine.append(pts[-1]); frad.append(0.008)
        tent = CH(fine, frad, k=0.02)
        tent = S.noisy(tent, 0.004, 30, 2, ridged=True, stretch=(0.4, 0.4, 3))
        tent = S.noisy(tent, 0.0015, 90, 2)
        ob = mk(tent, f"Tentacle{t}", 0.006, M["flesh"], 7000)
        suck = []
        for j in range(4, len(fine) - 3):
            p, q = fine[j], fine[j + 1]
            d = (q - p) / (np.linalg.norm(q - p) + 1e-9)
            side = np.cross(d, (0, 0, 1)); side = side / (np.linalg.norm(side) + 1e-9)
            for sgn in (-0.45, 0.45):
                n_ = side * math.cos(sgn) + np.cross(side, d) * math.sin(sgn)
                c = p + n_ * frad[j] * 0.92
                rr = frad[j] * 0.3
                suck.append(S.sub(S.sphere(c, rr), S.sphere(c + n_ * rr * 0.75, rr * 0.75), k=0.002))
        so = mk(S.union(*suck), f"Suckers{t}", 0.004, M["sucker"], 3500)
        for o in (ob, so):
            H.weights_by_bones(o, Bd, names)
        objs += [ob, so]
    body = H.join(objs, "Tentacles_Body")
    rig = PL.make_rig("Tentacles", Bd, order)
    PL.skin(body, rig, order)
    rig.parent = root
    mound = S.warp(S.noisy(E((0.15, 0.2, -0.06), (1.05, 0.9, 0.16)), 0.02, 4, 3), 0.05, 2.0)
    clumps = [S.noisy(S.box((0.15 + 0.95 * math.cos(a), 0.2 + 0.8 * math.sin(a), 0.03), (0.22, 0.14, 0.06), 0.02, S.rotm(0.3, 0.2, a)), 0.012, 9, 2)
              for a in np.linspace(0, 2 * math.pi, 8)[:-1]]
    d = mk(S.union(mound, *clumps, k=0.04), "Tentacle_Dirt", 0.014, M["dirt"], 5000)
    d.parent = root
    return {"name": "Lawn tentacles", "cat": "Creatures", "rig": "chain", "behaviors": ["sway"],
            "desc": "Four ridged, sucker-lined tentacles bursting out of torn sod. They sway; every segment can be posed."}
