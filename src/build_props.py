"""Yard + porch props: poseable skeletons, mannequin girls, horned figure, antler staves, cairn,
candles, chairs, wreaths, lanterns, pumpkins, string lights."""
import bpy, math, random
from mathutils import Vector as V, Matrix, Euler
from lib import *

CAIRN = V((-3.3, -5.3, 0.0))
RND = random.Random(1031)

# ======================================================================== materials
def materials(M):
    M["bone"] = mat("Bone_Plastic", (0.82, 0.78, 0.68), 0.45, sss=0.05)
    M["socket"] = mat("Bone_Socket", (0.015, 0.01, 0.01), 0.7)
    M["bone_real"] = mat("Bone_Weathered", (0.72, 0.66, 0.54), 0.75)
    noise_color(M["bone_real"], (0.45, 0.38, 0.28), (0.78, 0.72, 0.6), 14, 0.3, 0.6)
    noise_bump(M["bone_real"], 40, 0.4)
    M["antler"] = mat("Antler", (0.62, 0.52, 0.40), 0.6)
    noise_bump(M["antler"], 60, 0.6, 0.004)
    M["horn"] = mat("Horn_Dark_Ridged", (0.035, 0.025, 0.02), 0.35, coat=0.3)
    wave_bump(M["horn"], 6.0, "Z", "SIN", 0.9, 0.006)
    M["ramhorn"] = mat("Ram_Horn", (0.07, 0.055, 0.045), 0.5)
    noise_bump(M["ramhorn"], 50, 0.6)
    M["skin"] = mat("Mannequin_Skin", (0.80, 0.68, 0.60), 0.35, sss=0.03)
    M["dress"] = mat("Dress_Peach_White", (0.86, 0.74, 0.70), 0.75, sheen=0.4)
    M["gown"] = mat("Nightgown_Tan_Linen", (0.46, 0.34, 0.22), 0.8, sheen=0.3)
    noise_bump(M["gown"], 80, 0.25, 0.003)
    M["hair"] = mat("Hair_Auburn", (0.18, 0.08, 0.04), 0.5)
    wave_bump(M["hair"], 25, "Z", "SIN", 0.5, 0.004)
    M["hair_light"] = mat("Hair_Light_Brown", (0.32, 0.18, 0.09), 0.5)
    wave_bump(M["hair_light"], 25, "Z", "SIN", 0.5, 0.004)
    M["eye"] = mat("Mannequin_Eye", (0.03, 0.02, 0.015), 0.2)
    M["twine"] = mat("Twine", (0.55, 0.43, 0.27), 0.9)
    M["wood_stake"] = mat("Stake_Wood", (0.62, 0.48, 0.32), 0.7)
    wave_bump(M["wood_stake"], 40, "Z", "SIN", 0.3, 0.002)
    M["stone"] = mat("Cairn_Stone", (0.24, 0.23, 0.22), 0.8)
    noise_color(M["stone"], (0.12, 0.115, 0.11), (0.36, 0.34, 0.31), 3.5)
    noise_bump(M["stone"], 9, 0.8, 0.02)
    M["wax"] = mat("LED_Candle_Wax", (0.92, 0.82, 0.58), 0.5, sss=0.3,
                   emit=(1.0, 0.75, 0.35), emit_strength=0.6)
    M["flame"] = emission_mat("LED_Flame", (1.0, 0.62, 0.22), 25.0)
    M["led_red"] = emission_mat("String_LED_Red", (1.0, 0.05, 0.03), 40.0)
    M["led_warm"] = emission_mat("String_LED_Warm", (1.0, 0.8, 0.5), 25.0)
    M["star"] = mat("Star_Lantern_Glass", (0.6, 0.35, 0.1), 0.3,
                    emit=(1.0, 0.45, 0.15), emit_strength=6.0)
    M["chair"] = mat("Rocker_White", (0.82, 0.82, 0.80), 0.45)
    M["wreath"] = mat("Wreath_Greens", (0.03, 0.06, 0.035), 0.7)
    M["moss"] = mat("Hanging_Moss", (0.12, 0.16, 0.10), 0.9)
    M["twig"] = mat("Twig_Black", (0.03, 0.02, 0.015), 0.8)
    M["pumpkin"] = mat("Pumpkin", (0.75, 0.22, 0.02), 0.5)
    M["stem"] = mat("Pumpkin_Stem", (0.2, 0.15, 0.07), 0.8)
    M["fixture"] = mat("Fixture_Black_Plastic", (0.015, 0.015, 0.015), 0.4)
    M["bin_lid"] = mat("Recycle_Bin_Green", (0.02, 0.12, 0.05), 0.5)
    M["ghost"] = mat("Ghost_Sheet", (0.9, 0.9, 0.9), 0.8, sss=0.2)
    M["leaf"] = mat("Fallen_Leaves", (0.30, 0.12, 0.04), 0.7)
    noise_color(M["leaf"], (0.18, 0.06, 0.02), (0.45, 0.25, 0.06), 30)
    return M


# ======================================================================== skeleton
BONES = {
    "pelvis": ((0, 0, 0.98), (0, 0, 1.10), None),
    "spine": ((0, 0, 1.10), (0, 0, 1.30), "pelvis"),
    "chest": ((0, 0, 1.30), (0, 0, 1.50), "spine"),
    "neck": ((0, 0, 1.50), (0, 0, 1.58), "chest"),
    "head": ((0, 0, 1.58), (0, 0, 1.78), "neck"),
}
for s, sx in (("L", 1), ("R", -1)):
    BONES.update({
        f"upper_arm.{s}": ((0.18 * sx, 0, 1.45), (0.18 * sx, 0, 1.16), "chest"),
        f"forearm.{s}": ((0.18 * sx, 0, 1.16), (0.18 * sx, 0, 0.91), f"upper_arm.{s}"),
        f"hand.{s}": ((0.18 * sx, 0, 0.91), (0.18 * sx, 0, 0.74), f"forearm.{s}"),
        f"thigh.{s}": ((0.10 * sx, 0, 0.97), (0.10 * sx, 0, 0.53), "pelvis"),
        f"shin.{s}": ((0.10 * sx, 0, 0.53), (0.10 * sx, 0, 0.10), f"thigh.{s}"),
        f"foot.{s}": ((0.10 * sx, 0, 0.10), (0.10 * sx, -0.16, 0.03), f"shin.{s}"),
    })
ORDER = ["pelvis", "spine", "chest", "neck", "head"] + [
    f"{b}.{s}" for s in "LR" for b in ("upper_arm", "forearm", "hand", "thigh", "shin", "foot")]


def skeleton_mesh(M):
    mb = MB()
    G = {n: i for i, n in enumerate(ORDER)}
    def g(n):
        mb.gi = G[n]
    mb.mi = 0
    # ---- skull
    g("head")
    mb.sphere((0, 0.0, 1.675), 0.095, (0.85, 1.05, 1.0), segs=(18, 12))
    mb.sphere((0, -0.055, 1.615), 0.062, (1.0, 0.85, 0.85), segs=(14, 9))         # maxilla
    mb.sphere((0, -0.05, 1.56), 0.05, (1.15, 0.9, 0.45), segs=(14, 8))           # jaw
    for sx in (-1, 1):
        mb.sphere((0.065 * sx, -0.045, 1.635), 0.025, (0.8, 1.6, 0.8))           # cheekbones
    mb.box((0, -0.105, 1.588), (0.07, 0.012, 0.022))                              # teeth
    mb.mi = 1
    for sx in (-1, 1):
        mb.sphere((0.034 * sx, -0.083, 1.672), 0.024, (1.0, 0.7, 1.05), segs=(10, 7))
    mb.sphere((0, -0.1, 1.625), 0.012, (0.8, 0.6, 1.3), segs=(8, 6))
    mb.mi = 0
    # ---- neck + spine
    g("neck")
    for k in range(3):
        mb.cyl((0, 0.02, 1.505 + k * 0.026), (0, 0.02, 1.522 + k * 0.026), 0.022, segs=8)
    for k in range(13):
        z = 1.0 + k * 0.038
        g("pelvis" if z < 1.1 else "spine" if z < 1.3 else "chest")
        mb.cyl((0, 0.04, z), (0, 0.04, z + 0.026), 0.024, segs=8)
        mb.box((0, 0.068, z + 0.013), (0.012, 0.03, 0.018))
    # ---- ribcage
    g("chest")
    radii = [0.06, 0.088, 0.108, 0.122, 0.13, 0.131, 0.126, 0.116, 0.10]
    for k, R in enumerate(radii):
        z = 1.475 - k * 0.03
        mb.torus((0, 0.005, z - 0.012 * (k / 8)), R, 0.008, (1.0, 0.68, 1.0),
                 (math.radians(-12), 0, 0), segs=(26, 5))
    mb.box((0, -0.088, 1.40), (0.026, 0.012, 0.17), (math.radians(-12), 0, 0))       # sternum
    for sx in (-1, 1):
        mb.cyl((0.02 * sx, -0.05, 1.49), (0.17 * sx, 0.0, 1.475), 0.011, segs=6)      # clavicle
        mb.sphere((0.12 * sx, 0.055, 1.40), 0.06, (0.75, 0.25, 1.2), segs=(10, 6))    # scapula
    # ---- pelvis
    g("pelvis")
    mb.torus((0, 0.0, 0.985), 0.1, 0.022, (1.2, 0.75, 1.0), (0, 0, 0), segs=(22, 6))
    for sx in (-1, 1):
        mb.sphere((0.095 * sx, 0.015, 1.04), 0.065, (0.35, 0.95, 0.8), (0, math.radians(-30 * sx), 0),
                  segs=(12, 8))
        mb.sphere((0.1 * sx, -0.005, 0.965), 0.024)
    mb.sphere((0, 0.05, 1.0), 0.04, (0.6, 0.45, 1.1))                                # sacrum
    # ---- limbs
    for s, sx in (("L", 1), ("R", -1)):
        x = 0.18 * sx
        g(f"upper_arm.{s}")
        mb.sphere((x, 0, 1.445), 0.03)
        mb.cyl((x, 0, 1.43), (x, 0, 1.17), 0.016, segs=8)
        mb.sphere((x, 0, 1.165), 0.026, (1.2, 0.9, 0.9))
        g(f"forearm.{s}")
        mb.cyl((x - 0.012 * sx, 0, 1.15), (x - 0.008 * sx, -0.005, 0.92), 0.011, segs=6)
        mb.cyl((x + 0.012 * sx, 0, 1.15), (x + 0.012 * sx, 0.004, 0.92), 0.009, segs=6)
        g(f"hand.{s}")
        mb.box((x, 0, 0.875), (0.055, 0.02, 0.06))
        for f in range(4):
            fx = x - 0.021 * sx + 0.014 * f * sx
            mb.cyl((fx, 0, 0.845), (fx, -0.006, 0.755 + 0.01 * abs(f - 1.5)), 0.0055, segs=5)
        mb.cyl((x - 0.03 * sx, -0.01, 0.88), (x - 0.045 * sx, -0.03, 0.82), 0.006, segs=5)
        g(f"thigh.{s}")
        x = 0.10 * sx
        mb.sphere((x, 0, 0.955), 0.03)
        mb.cyl((x, 0, 0.94), (x, 0, 0.56), 0.02, segs=8)
        mb.sphere((x, 0, 0.545), 0.032, (1.15, 1.0, 0.8))
        g(f"shin.{s}")
        mb.sphere((x, -0.03, 0.525), 0.02, (1, 0.6, 1))                               # patella
        mb.cyl((x, 0, 0.51), (x, 0, 0.12), 0.018, segs=8)
        mb.cyl((x + 0.03 * sx, 0.005, 0.5), (x + 0.025 * sx, 0.005, 0.13), 0.009, segs=6)
        g(f"foot.{s}")
        mb.sphere((x, 0.02, 0.07), 0.03, (0.9, 1.2, 0.9))                               # heel
        for f in range(5):
            fx = x - 0.028 * sx + 0.014 * f * sx
            mb.cyl((x, -0.01, 0.08), (fx, -0.12, 0.03), 0.007, segs=5)
            mb.cyl((fx, -0.12, 0.03), (fx, -0.175, 0.022), 0.006, segs=5)
    return mb.mesh("Skeleton_Mesh", [M["bone"], M["socket"]])


def skeleton_armature():
    arm = bpy.data.armatures.new("Skeleton_Rig")
    ob = bpy.data.objects.new("_rig_tmp", arm)
    bpy.context.scene.collection.objects.link(ob)
    bpy.context.view_layer.objects.active = ob
    bpy.ops.object.mode_set(mode="EDIT")
    for n in ORDER:
        h, t, p = BONES[n]
        eb = arm.edit_bones.new(n)
        eb.head, eb.tail = h, t
        if p:
            eb.parent = arm.edit_bones[p]
            eb.use_connect = (V(BONES[p][1]) - V(h)).length < 1e-4
    bpy.ops.object.mode_set(mode="OBJECT")
    bpy.data.objects.remove(ob)
    arm.display_type = "STICK"
    return arm


def aim(rig, name, d):
    pb = rig.pose.bones[name]
    Mx = pb.matrix.copy()
    head = Mx.translation.copy()
    cur = (Mx.to_3x3() @ V((0, 1, 0))).normalized()
    q = cur.rotation_difference(V(d).normalized())
    pb.matrix = Matrix.Translation(head) @ q.to_matrix().to_4x4() @ Matrix.Translation(-head) @ Mx
    bpy.context.view_layer.update()


POSES = {
    "prone_propped": {
        "pelvis": (0, -1, 0.12), "spine": (0, -0.9, 0.45), "chest": (0, -0.55, 0.85),
        "neck": (0, -0.4, 0.92), "head": (0, -0.1, 1),
        "upper_arm.L": (0.18, -0.25, -1), "forearm.L": (0.06, -0.35, -1), "hand.L": (0.04, -1, -0.15),
        "thigh.L": (0.12, 1, -0.1), "shin.L": (0.05, 1, 0.15), "foot.L": (0, 0.35, -1)},
    "reach_crawl": {
        "pelvis": (0, -0.75, 0.65), "spine": (0, -0.85, 0.5), "chest": (0, -0.75, 0.62),
        "neck": (0, -0.55, 0.85), "head": (0, -0.15, 1),
        "upper_arm.L": (0.18, -1, -0.35), "forearm.L": (0.05, -1, -0.35), "hand.L": (0, -1, -0.6),
        "upper_arm.R": (-0.3, -0.5, -1), "forearm.R": (-0.1, -0.9, -0.5),
        "thigh.L": (0.15, 0.2, -1), "shin.L": (0, 1, -0.3), "foot.L": (0, 0.3, -1)},
    "kneel_hunch": {
        "pelvis": (0, -0.3, 1), "spine": (0, -0.75, 0.66), "chest": (0, -0.95, 0.35),
        "neck": (0, -0.98, 0.0), "head": (0, -0.55, -0.85),
        "upper_arm.L": (0.18, -0.45, -1), "forearm.L": (0.05, -0.7, -0.75), "hand.L": (0, -0.9, -0.5),
        "thigh.L": (0.15, -1, -0.28), "shin.L": (0, 1, -0.06), "foot.L": (0, 1, -0.25)},
    "kneel_reach": {
        "pelvis": (0, 0, 1), "spine": (0, -0.2, 1), "chest": (0, -0.35, 1),
        "neck": (0, -0.35, 1), "head": (0, -0.05, 1),
        "upper_arm.L": (0.15, -0.85, -0.5), "forearm.L": (0.02, -0.95, -0.3), "hand.L": (0, -0.9, -0.45),
        "upper_arm.R": (-0.1, -0.6, -0.8), "forearm.R": (0.1, -1, -0.1),
        "thigh.L": (0.06, -0.12, -1), "shin.L": (0, 1, -0.04), "foot.L": (0, 1, -0.3)},
    "sit_chair": {
        "pelvis": (0, 0.25, 1), "spine": (0, 0.12, 1), "chest": (0, 0.02, 1),
        "neck": (0.05, -0.12, 1), "head": (0.35, -0.2, 1),
        "upper_arm.L": (0.3, 0.12, -1), "forearm.L": (0.08, -1, -0.12), "hand.L": (0.03, -1, -0.4),
        "thigh.L": (0.12, -1, 0.06), "shin.L": (0.03, -0.12, -1), "foot.L": (0, -1, -0.3)},
    "sit_reach": {
        "pelvis": (0, 0.35, 1), "spine": (0, -0.15, 1), "chest": (0, -0.55, 0.85),
        "neck": (0, -0.5, 0.86), "head": (0, -0.2, 1),
        "upper_arm.L": (0.25, -1, -0.45), "forearm.L": (0.02, -1, -0.2), "hand.L": (0, -1, -0.3),
        "upper_arm.R": (-0.45, -0.25, -1), "forearm.R": (-0.25, -0.65, -0.8), "hand.R": (0, -1, -0.6),
        "thigh.L": (0.3, -1, 0.5), "shin.L": (0.05, -0.35, -1), "foot.L": (0, -1, -0.25),
        "thigh.R": (-0.35, -1, 0.15), "shin.R": (0.05, -0.75, -0.65), "foot.R": (0, -1, -0.2)},
}


def pose_rig(rig, pose, jitter=0.12, rnd=RND):
    spec = dict(POSES[pose])
    for k, d in list(spec.items()):
        if k.endswith(".L") and k[:-2] + ".R" not in spec:
            spec[k[:-2] + ".R"] = (-d[0], d[1], d[2])
    for n in ORDER:
        if n in spec:
            d = V(spec[n])
            d.normalize()
            if jitter:
                d += V((rnd.uniform(-1, 1), rnd.uniform(-1, 1), rnd.uniform(-1, 1))) * jitter
            aim(rig, n, d)


def ground_snap(rig, mesh_ob, bury=0.0):
    bpy.context.view_layer.update()
    dg = bpy.context.evaluated_depsgraph_get()
    ev = mesh_ob.evaluated_get(dg)
    me = ev.to_mesh()
    mw = mesh_ob.matrix_world
    zmin = min((mw @ v.co).z for v in me.vertices)
    ev.to_mesh_clear()
    rig.location.z += (rig.location.z * 0) - zmin + 0.0 - bury + rig.location.z * 0


def make_skeleton(name, C, me, arm, loc, heading_to=None, rot_z=None, pose="prone_propped",
                  bury=0.0, ground=0.0, jitter=0.12, rnd=RND):
    rig = bpy.data.objects.new(name + "_Rig", arm)
    C.objects.link(rig)
    rig.location = (loc[0], loc[1], 0)
    if heading_to is not None:
        d = V(heading_to) - V((loc[0], loc[1], 0))
        rig.rotation_euler.z = math.atan2(d.x, -d.y)
    if rot_z is not None:
        rig.rotation_euler.z = rot_z
    rig.show_in_front = True
    ob = bpy.data.objects.new(name, me)
    C.objects.link(ob)
    ob.parent = rig
    for n in ORDER:
        ob.vertex_groups.new(name=n)
    mod = ob.modifiers.new("Armature", "ARMATURE")
    mod.object = rig
    bpy.context.view_layer.update()
    pose_rig(rig, pose, jitter, rnd)
    if ground is not None:
        bpy.context.view_layer.update()
        dg = bpy.context.evaluated_depsgraph_get()
        ev = ob.evaluated_get(dg)
        m2 = ev.to_mesh()
        zmin = min((ob.matrix_world @ v.co).z for v in m2.vertices)
        ev.to_mesh_clear()
        rig.location.z += ground - zmin - bury
    rig["pose_preset"] = pose
    return rig, ob


# ======================================================================== antlers & skulls
def antler_splines(s, scale=1.0, kind="deer", rnd=RND):
    """Splines for one side (s=+1 left/-1 right) in skull space (skull faces -Y, up +Z)."""
    sp = []
    n = 9
    main = []
    for i in range(n):
        t = i / (n - 1)
        if kind == "elk":
            x = s * (0.04 + 0.55 * math.sin(t * math.pi * 0.5))
            y = 0.05 + 0.55 * t - 0.15 * t * t
            z = 0.05 + 0.45 * t + 0.1 * math.sin(t * math.pi)
        else:
            x = s * (0.04 + 0.30 * math.sin(t * math.pi * 0.62))
            y = 0.04 + 0.22 * t - 0.36 * t ** 2.2
            z = 0.05 + 0.42 * t - 0.06 * t * t
        main.append(((x * scale, y * scale, z * scale), 1.0 - 0.6 * t))
    sp.append(main)
    tines = ([(0.12, (s * 0.1, -1, 0.35), 0.22), (0.4, (s * 0.15, -0.4, 1), 0.28),
              (0.6, (s * 0.1, -0.2, 1), 0.25), (0.78, (s * 0.05, -0.1, 1), 0.2)]
             if kind == "elk" else
             [(0.15, (s * 0.05, -1, 0.5), 0.12), (0.45, (s * 0.12, -0.2, 1), 0.17),
              (0.7, (s * 0.08, -0.1, 1), 0.14)])
    for t, d, L in tines:
        i = t * (n - 1)
        a, b = main[int(i)][0], main[min(int(i) + 1, n - 1)][0]
        f = i - int(i)
        base = V(a).lerp(V(b), f)
        d = V(d).normalized()
        L *= scale * rnd.uniform(0.8, 1.15)
        pts = []
        for k in range(4):
            u = k / 3
            p = base + d * L * u + V((0, 0, 0.25 * L * u * u))
            pts.append((tuple(p), (1.0 - 0.6 * t) * (0.8 - 0.6 * u)))
        sp.append(pts)
    return sp


def deer_skull(name, C, M, loc, rot, scale=1.0, kind="deer", parent=None, rnd=RND):
    root = empty(name, loc, C, 0.15)
    root.rotation_euler = rot
    if parent:
        root.parent = parent
    mb = MB()
    k = scale * (1.35 if kind == "elk" else 1.0)
    mb.sphere((0, 0.02 * k, 0.0), 0.065 * k, (0.9, 1.0, 0.85), segs=(14, 9))
    mb.cyl((0, -0.02 * k, -0.01 * k), (0, -0.25 * k, -0.06 * k), 0.045 * k, 0.022 * k, segs=10)
    mb.sphere((0, -0.25 * k, -0.06 * k), 0.024 * k)
    for sx in (-1, 1):
        mb.torus((0.045 * sx * k, -0.07 * k, 0.012 * k), 0.022 * k, 0.007 * k, rot=(0, math.radians(80 * sx), 0),
                 segs=(12, 4))
        mb.sphere((0.03 * sx * k, 0.0, 0.05 * k), 0.018 * k, segs=(8, 6))   # pedicle
    mb.mi = 1
    for sx in (-1, 1):
        mb.sphere((0.045 * sx * k, -0.07 * k, 0.012 * k), 0.018 * k, segs=(8, 6))
        mb.sphere((0.012 * sx * k, -0.2 * k, -0.035 * k), 0.012 * k, (1, 3, 1), segs=(8, 6))
    sk = mb.obj(name + "_Bone", [M["bone_real"], M["socket"]], C)
    sk.parent = root
    splines = antler_splines(1, scale, kind, rnd) + antler_splines(-1, scale, kind, rnd)
    for spl in splines:
        for j, (co, r) in enumerate(spl):
            spl[j] = ((co[0], co[1] + 0.0, co[2] + 0.03 * k), r)
    a = tube_curve(name + "_Antlers", splines, bevel=(0.022 if kind == "elk" else 0.016) * scale,
                   mats=[M["antler"]], c=C, res=3)
    a.parent = root
    return root


# ======================================================================== mannequins
def mannequin(name, C, M, loc, rot_z=0.0, height=1.3, hair="long", headpiece=None,
              dress="dress", hair_mat="hair_light", gown=False):
    k = height / 1.3
    mb = MB()
    mb.mi = 0  # skin
    if gown:   # adult: long gown nearly to floor, bare feet
        for sx in (-1, 1):
            mb.cyl((0.075 * sx * k, 0, 0.02), (0.075 * sx * k, 0, 0.3 * k), 0.035 * k)
            mb.sphere((0.075 * sx * k, -0.05 * k, 0.025), 0.035 * k, (0.8, 2.0, 0.6))
        prof = [(0.185, 0.12), (0.18, 0.2), (0.165, 0.4), (0.145, 0.62), (0.13, 0.8), (0.125, 0.9),
                (0.135, 0.99), (0.13, 1.05), (0.09, 1.09), (0.045, 1.1)]
        amp = 0.02
    else:
        for sx in (-1, 1):
            mb.cyl((0.06 * sx * k, 0, 0.03), (0.06 * sx * k, 0, 0.5 * k), 0.032 * k)
            mb.sphere((0.06 * sx * k, -0.035 * k, 0.03), 0.03 * k, (0.8, 1.8, 0.6))
        prof = [(0.27, 0.42), (0.25, 0.5), (0.2, 0.64), (0.155, 0.77), (0.125, 0.85), (0.135, 0.92),
                (0.125, 0.975), (0.08, 0.995), (0.05, 1.0)]
        amp = 0.022
    z_hem = prof[0][1]
    span = prof[-1][1] - z_hem
    prof = [(r * k, z * k) for r, z in prof]
    def folds(t, z, r, idx):
        f = max(0.0, 1 - (z / k - z_hem) / (span * 0.75))
        return r + amp * k * f * math.sin(9 * t + 0.6 * math.sin(3 * t))
    mb.mi = 1
    mb.lathe(prof, 36, (0, 0, 0), folds, cap_top=True, scale=(1, 0.8))
    top = prof[-1][1]
    sh_z = top - 0.07 * k
    for sx in (-1, 1):
        mb.mi = 1
        if gown:   # wide bell sleeves
            mb.cyl((0.135 * sx * k, 0, sh_z), (0.175 * sx * k, -0.04 * k, sh_z - 0.33 * k), 0.045 * k,
                   0.085 * k, segs=14, cap=False)
            mb.mi = 0
            mb.cyl((0.17 * sx * k, -0.03 * k, sh_z - 0.25 * k), (0.185 * sx * k, -0.07 * k, sh_z - 0.43 * k),
                   0.022 * k)
            mb.sphere((0.188 * sx * k, -0.08 * k, sh_z - 0.47 * k), 0.032 * k, (0.6, 1, 1.5))
        else:
            mb.sphere((0.125 * sx * k, 0, sh_z), 0.048 * k, (1, 0.9, 0.9))
            mb.mi = 0
            mb.cyl((0.15 * sx * k, 0, sh_z - 0.03 * k), (0.17 * sx * k, -0.02 * k, sh_z - 0.36 * k),
                   0.021 * k)
            mb.sphere((0.172 * sx * k, -0.022 * k, sh_z - 0.39 * k), 0.028 * k, (0.7, 1, 1.4))
    mb.mi = 0
    mb.cyl((0, 0, top - 0.02 * k), (0, 0, top + 0.07 * k), 0.03 * k)
    hz = top + 0.14 * k
    mb.sphere((0, -0.005 * k, hz), 0.085 * k, (0.85, 0.92, 1.08), segs=(18, 12))
    mb.sphere((0, -0.08 * k, hz - 0.005 * k), 0.012 * k, (1, 1, 1.4))              # nose
    mb.mi = 2
    for sx in (-1, 1):
        mb.sphere((0.03 * sx * k, -0.07 * k, hz + 0.008 * k), 0.011 * k, (1.1, 0.6, 0.8))
    mats = [M["skin"], M[dress], M["eye"], M[hair_mat]]
    if hair:
        mb.mi = 3
        mb.sphere((0, 0.02 * k, hz + 0.01 * k), 0.092 * k, (0.92, 0.9, 1.05), segs=(16, 10))
        length = 0.42 if hair == "long" else 0.25
        mb.sphere((0, 0.05 * k, hz - length * 0.45 * k), 0.1 * k, (1.15, 0.5, length * 5), segs=(16, 10))
        for sx in (-1, 1):
            mb.sphere((0.072 * sx * k, -0.01 * k, hz - 0.08 * k), 0.06 * k, (0.5, 0.75, 2.4), segs=(10, 8))
    ob = mb.obj(name, mats, C)
    ob.location = loc
    ob.rotation_euler.z = rot_z
    return ob, hz


def mandible_headpiece(name, C, M, parent, hz, k=1.0):
    """Cow jawbone strapped to the side of a bald mannequin head (IMG_0138): the ramus runs up
    past the ear, the toothed body juts forward under the chin."""
    x = -0.078
    ramus = [((x, 0.035, hz + 0.13), 0.7), ((x - 0.006, 0.03, hz + 0.05), 0.95),
             ((x - 0.01, 0.015, hz - 0.04), 1.1), ((x - 0.008, -0.03, hz - 0.085), 1.0)]
    body = [((x - 0.008, -0.03, hz - 0.085), 1.0), ((x - 0.004, -0.12, hz - 0.08), 0.85),
            ((x, -0.22, hz - 0.07), 0.7), ((x + 0.004, -0.31, hz - 0.075), 0.5)]
    pts = [((co[0] - x, co[1], co[2]), r) for co, r in ramus + body[1:]]
    jb = tube_curve(name, [pts], bevel=0.026, mats=[M["bone_real"]], c=C, res=2)
    jb.parent = parent
    jb.location = (x, 0, 0)
    jb.scale = (0.45, 1, 1)   # flat jaw plate
    mb = MB()
    for i in range(10):   # molar row along the top of the jaw body
        y = -0.06 - 0.022 * i
        mb.box((x - 0.002, y, hz - 0.052 + 0.001 * i), (0.016, 0.02, 0.028), (0, 0, 0.12 * math.sin(i * 1.7)))
    mb.mi = 1
    for zz, tilt in ((hz + 0.035, 8), (hz - 0.02, -10)):
        mb.torus((0, -0.004, zz), 0.077, 0.0035, (0.95, 1.02, 1), (math.radians(tilt), 0, 0), segs=(28, 4))
    tw = mb.obj(name + "_Teeth_Twine", [M["bone_real"], M["twine"]], C)
    tw.parent = parent
    return jb


# ======================================================================== staves, cairn
def stave(name, C, M, base, h=2.35, skull_rot=0.0, kind="deer", scale=1.0, lean=(0, 0), rnd=RND):
    root = empty(name, base, C, 0.3)
    root.rotation_euler = (lean[0], lean[1], skull_rot)
    mb = MB(); mb.smooth = False
    mb.box((0, 0, h / 2), (0.075, 0.035, h + 0.3))
    mb.mi = 1
    mb.smooth = True
    for i in range(7):
        mb.torus((0, 0, h - 0.18 + 0.025 * i), 0.045, 0.005, (1.1, 0.75, 1),
                 (rnd.uniform(-0.3, 0.3), rnd.uniform(-0.3, 0.3), 0), segs=(14, 4))
    st = mb.obj(name + "_Pole", [M["wood_stake"], M["twine"]], C)
    st.parent = root
    deer_skull(name + "_Skull", C, M, (0, -0.07, h - 0.1), (math.radians(38), 0, 0), scale, kind,
               parent=root, rnd=rnd)
    return root


def build_cairn(C, M, rnd=RND):
    variants = []
    for vi in range(4):
        mb = MB(); mb.smooth = False
        r = bmesh_rock(mb, rnd)
        variants.append(mb.mesh(f"Rock_Variant_{vi}", [M["stone"]]))
    layers = [(1.05, 0.0, 15), (0.85, 0.12, 13), (0.65, 0.24, 10), (0.45, 0.36, 7), (0.25, 0.47, 4),
              (0.0, 0.56, 1)]
    i = 0
    for R, z, n in layers:
        for j in range(n):
            a = 2 * math.pi * j / n + rnd.uniform(-0.15, 0.15) + z * 3
            rr = R * rnd.uniform(0.85, 1.05)
            ob = bpy.data.objects.new(f"Cairn_Stone_{i:02d}", variants[i % 4])
            C.objects.link(ob)
            ob.location = (CAIRN.x + rr * math.cos(a), CAIRN.y + rr * math.sin(a), z + 0.05)
            tilt = 0.32 if R > 0.3 else 0.12
            ob.rotation_euler = Euler((rnd.uniform(-0.2, 0.2) + tilt * math.sin(a) * -1,
                                       tilt * math.cos(a) + rnd.uniform(-0.2, 0.2), a + rnd.uniform(-0.6, 0.6)),
                                      "XYZ")
            sc = rnd.uniform(0.8, 1.15)
            ob.scale = (sc * rnd.uniform(0.9, 1.25), sc, sc * rnd.uniform(0.9, 1.6))
            i += 1
    # elk skull crowning the pile
    deer_skull("Cairn_Elk_Skull", C, M, (CAIRN.x, CAIRN.y - 0.05, 0.74), (math.radians(18), 0, 0.3), 1.25,
               "elk", rnd=rnd)
    # red + warm string lights threaded through
    mb = MB()
    for j in range(46):
        a = rnd.uniform(0, 2 * math.pi)
        r = rnd.uniform(0.15, 1.3)
        z = max(0.03, 0.6 * (1 - r / 1.25)) + 0.06
        mb.mi = 0 if j % 3 else 1
        mb.sphere((CAIRN.x + r * math.cos(a), CAIRN.y + r * math.sin(a), z), 0.012, segs=(6, 4))
    mb.obj("Cairn_String_Lights", [M["led_red"], M["led_warm"]], C)


def bmesh_rock(mb, rnd):
    """Flat, angular slab (fieldstone) built from a jittered, beveled box."""
    import bmesh as bm_
    res = bm_.ops.create_cube(mb.bm, size=1.0, matrix=Matrix.Diagonal((0.32, 0.25, 0.11, 1)))
    bm_.ops.bevel(mb.bm, geom=mb.bm.edges[:], offset=0.035, segments=2, affect="EDGES")
    bm_.ops.subdivide_edges(mb.bm, edges=mb.bm.edges[:], cuts=1, use_grid_fill=True)
    for v in mb.bm.verts:
        v.co += V((rnd.uniform(-1, 1) * 0.018, rnd.uniform(-1, 1) * 0.018, rnd.uniform(-1, 1) * 0.01))
        v.co.z *= 1.0 - 0.3 * (abs(v.co.x) / 0.16) ** 2
    for f in mb.bm.faces:
        f.smooth = False


# ======================================================================== porch props
def rocking_chair(name, C, M, loc, rot_z=0.0):
    mb = MB(); mb.smooth = False
    w, d = 0.55, 0.5
    mb.box((0, 0, 0.45), (w, d, 0.04))
    for sx in (-1, 1):
        for sy in (-1, 1):
            mb.box((sx * w / 2 * 0.9, sy * d / 2 * 0.85, 0.27), (0.035, 0.035, 0.38))
        pts = [(sx * w / 2 * 0.9, -0.42 + 0.84 * t / 8, 0.06 + 0.12 * ((t / 8 - 0.5) * 2) ** 2) for t in range(9)]
        for a, b in zip(pts[:-1], pts[1:]):
            mb.box(((a[0] + b[0]) / 2, (a[1] + b[1]) / 2, (a[2] + b[2]) / 2), (0.03, 0.115, 0.04),
                   (math.atan2(b[2] - a[2], b[1] - a[1]), 0, 0))
        mb.box((sx * (w / 2 + 0.03), -0.03, 0.68), (0.07, 0.5, 0.025))           # arms
        mb.box((sx * (w / 2 + 0.03), -0.25, 0.57), (0.03, 0.03, 0.22))
    for i in range(7):   # back spindles
        x = -w / 2 * 0.85 + w * 0.85 * i / 6
        mb.box((x, d / 2 + 0.03, 0.82), (0.022, 0.022, 0.72), (math.radians(-10), 0, 0))
    mb.box((0, d / 2 + 0.1, 1.2), (w + 0.05, 0.06, 0.08), (math.radians(-10), 0, 0))
    ob = mb.obj(name, [M["chair"]], C)
    ob.location = loc
    ob.rotation_euler.z = rot_z
    return ob


def wreath(name, C, M, loc, r=0.27, kind="green", rnd=RND):
    mb = MB()
    if kind == "green":
        mb.torus((0, 0, 0), r, 0.07, (1, 1, 1), (math.radians(90), 0, 0), segs=(28, 8))
        for i in range(60):
            a = rnd.uniform(0, 2 * math.pi)
            rr = r + rnd.uniform(-0.07, 0.07)
            mb.sphere((rr * math.cos(a), -0.03, rr * math.sin(a)), rnd.uniform(0.03, 0.05),
                      (1, 0.6, 1), segs=(6, 4))
        mb.mi = 1
        for i in range(16):   # hanging moss drips
            x = rnd.uniform(-r, r)
            ztop = -math.sqrt(max(0.0, r * r - x * x))
            mb.cyl((x, -0.04, ztop), (x + rnd.uniform(-0.03, 0.03), -0.05, ztop - rnd.uniform(0.15, 0.45)),
                   0.018, 0.003, segs=5)
        mats = [M["wreath"], M["moss"]]
    else:   # black twig wreath
        mb.torus((0, 0, 0), r, 0.03, (1, 1, 1), (math.radians(90), 0, 0), segs=(24, 6))
        for i in range(90):
            a = rnd.uniform(0, 2 * math.pi)
            p = V((r * math.cos(a), 0, r * math.sin(a)))
            out = p.normalized() * rnd.uniform(0.04, 0.17)
            tang = V((-math.sin(a), 0, math.cos(a))) * rnd.uniform(-0.08, 0.08)
            mb.cyl(p, p + out + tang + V((0, rnd.uniform(-0.03, 0.02), 0)), 0.005, 0.0015, segs=4)
        mats = [M["twig"]]
    ob = mb.obj(name, mats, C)
    ob.location = loc
    return ob


def ram_horns(name, C, M, loc):
    splines = []
    for s in (1, -1):
        pts = []
        for i in range(14):
            th = 1.75 * math.pi * i / 13
            r = 0.14 * (1 - th / (2.6 * math.pi))
            pts.append(((s * (0.05 + 0.13 * math.sin(th / 2.2)), -0.02 - r * math.sin(th) * 0.5,
                         0.08 - (0.14 - r * math.cos(th))), 1.0 - 0.75 * i / 13))
        splines.append(pts)
    ob = tube_curve(name, splines, bevel=0.035, mats=[M["ramhorn"]], c=C)
    ob.location = loc
    mb = MB()
    mb.sphere((0, 0, 0.08), 0.05, (1, 1.3, 0.8))
    sk = mb.obj(name + "_Skullcap", [M["bone_real"]], C)
    sk.parent = ob
    mb = MB()
    mb.cyl((0, 0, 0.12), (0, 0, 0.75), 0.003, segs=4)
    t = mb.obj(name + "_Hanger", [M["twine"]], C)
    t.parent = ob
    return ob


def star_lantern(name, C, M, loc):
    mb = MB(); mb.smooth = False
    import bmesh as bm_
    tmp = bm_.new()
    bm_.ops.create_icosphere(tmp, subdivisions=1, radius=1.0)
    dirs = [v.co.copy() for v in tmp.verts]
    tmp.free()
    for d in dirs:
        mb.cyl(d * 0.03, d * 0.13, 0.035, 0.002, segs=5)
    mb.sphere((0, 0, 0), 0.05)
    mb.mi = 1
    mb.cyl((0, 0, 0.1), (0, 0, 0.35), 0.006, segs=5)
    ob = mb.obj(name, [M["star"], M["fixture"]], C)
    ob.location = loc
    return ob


def pumpkin(name, C, M, loc, r=0.16, rnd=RND):
    mb = MB()
    prof = [(0.001, 0.0), (0.55, 0.05), (0.92, 0.25), (1.0, 0.5), (0.9, 0.78), (0.55, 0.95), (0.08, 0.9)]
    prof = [(a * r, b * r * 1.6 * rnd.uniform(0.85, 1.05)) for a, b in prof]
    mb.lathe(prof, 40, (0, 0, 0), lambda t, z, rr, i: rr * (1 - 0.06 * abs(math.sin(5 * t))))
    mb.mi = 1
    mb.cyl((0, 0, prof[-1][1] - 0.01), (0.02, 0.01, prof[-1][1] + 0.08), 0.022, 0.016, segs=7)
    ob = mb.obj(name, [M["pumpkin"], M["stem"]], C)
    ob.location = loc
    ob.rotation_euler.z = rnd.uniform(0, 6.28)
    return ob


def led_candle(mb_wax, mb_flame, x, y, z, h, r=0.04, rnd=RND):
    def wob(t, zz, rr, i):
        return rr * (1 + (0.12 * math.sin(3 * t + x * 9) if zz > z + h - 0.01 else 0))
    mb_wax.lathe([(r, z), (r, z + h - 0.012), (r * 0.97, z + h), (r * 0.25, z + h - 0.006)], 18,
                 (x, y, 0), wob, cap_bottom=True, cap_top=True)
    mb_flame.sphere((x, y, z + h + 0.012), 0.008, (0.7, 0.7, 1.6), segs=(8, 6))


def build_candles(C, M, rnd=RND):
    """Battery pillar candles cascading down the steps under the horned figure (IMG_0137)."""
    wax, fl = MB(), MB()
    PY, RISE, TREAD = -2.7, 0.22, 0.30
    cx = 1.5
    rows = {0: [-0.62, -0.42, 0.42, 0.62], 1: [-0.55, -0.32, 0.32, 0.55],
            2: [-0.4, -0.15, 0.15, 0.4], 3: [-0.28, 0.0, 0.28], 4: [-0.14, 0.14]}
    for step, xs in rows.items():
        z = 1.1 - RISE * step
        y = -1.6 if step == 0 else PY - TREAD * (step - 0.5)
        if step == 0:
            y = PY + 0.18
        for dx in xs:
            led_candle(wax, fl, cx + dx + rnd.uniform(-0.03, 0.03), y + rnd.uniform(-0.04, 0.04), z,
                       rnd.choice([0.1, 0.13, 0.15, 0.2, 0.24]), rnd.choice([0.035, 0.04, 0.045]), rnd)
    for x in (-0.1, 0.12, 0.3):   # a few on the porch floor to the left
        led_candle(wax, fl, x, PY + 0.25 + rnd.uniform(0, 0.15), 1.1, rnd.choice([0.08, 0.1, 0.13]), 0.035, rnd)
    wax.obj("LED_Candles", [M["wax"]], C)
    fl.obj("LED_Candle_Flames", [M["flame"]], C)


def horned_figure(C, M):
    """Mannequin in tan nightgown with an oryx skull hung from the porch beam (IMG_0137/0138)."""
    loc = (1.5, -2.86, 0.88)
    body, hz = mannequin("Horned_Figure", C, M, loc, 0.0, 1.72, hair="long", dress="gown",
                         hair_mat="hair", gown=True)
    k = 1.72 / 1.3
    root = empty("Oryx_Skull", (loc[0], loc[1] - 0.06, loc[2] + hz + 0.02), C, 0.2)
    mb = MB()
    mb.sphere((0, 0, 0.05), 0.075, (0.85, 0.75, 1.0), segs=(16, 10))
    mb.cyl((0, -0.02, 0.02), (0, -0.07, -0.26), 0.055, 0.03, segs=12)
    mb.sphere((0, -0.07, -0.26), 0.03, (1, 0.8, 1))
    mb.mi = 1
    for sx in (-1, 1):
        mb.sphere((0.05 * sx, -0.05, 0.01), 0.022, (0.8, 1, 1.2), segs=(8, 6))
        mb.sphere((0.012 * sx, -0.085, -0.2), 0.009, (1, 1, 3), segs=(6, 4))
    sk = mb.obj("Oryx_Skull_Bone", [M["bone_real"], M["socket"]], C)
    sk.parent = root
    for s in (1, -1):
        pts = []
        for i in range(7):
            t = i / 6
            pts.append(((s * (0.035 + 0.13 * t), 0.03 + 0.1 * t + 0.05 * t * t, 0.1 + 1.0 * t),
                        1.0 - 0.88 * t))
        h = tube_curve(f"Oryx_Horn_{'L' if s > 0 else 'R'}", [pts], bevel=0.03, mats=[M["horn"]], c=C)
        h.parent = root
    mb = MB()
    for s in (1, -1):    # twine from horn bases up to the column bracket
        mb.cyl((0.04 * s, 0.03, 0.12), (0.0, 0.3, 3.45 - (loc[2] + hz + 0.02)), 0.0025, segs=4)
    tw = mb.obj("Oryx_Hanging_Twine", [M["twine"]], C)
    tw.parent = root
    return body


def ghost_in_window(C, M):
    mb = MB()
    prof = [(0.22, 0.0), (0.2, 0.15), (0.15, 0.4), (0.12, 0.55), (0.13, 0.65), (0.1, 0.75), (0.0, 0.8)]
    mb.lathe(prof, 20, (0, 0, 0), lambda t, z, r, i: r * (1 + 0.15 * math.sin(7 * t) * (z < 0.2)))
    ob = mb.obj("Attic_Ghost", [M["ghost"]], C)
    ob.location = (-0.72, 0.36, 8.08)
    return ob


def leaves(C, M, rnd=RND):
    mb = MB(); mb.smooth = False
    for i in range(1400):
        if i < 700:
            x, y = rnd.uniform(-6.7, -0.4), rnd.uniform(-8.3, -2.8)
            if (V((x, y, 0)) - CAIRN).length < 1.0:
                continue
            z = 0.055
        elif i < 1150:
            x, y, z = rnd.uniform(-12, 12), rnd.uniform(-10.0, -8.5), 0.035
        else:
            x, y, z = rnd.uniform(-12, 12), rnd.uniform(-12, -10.2), -0.175
        a = rnd.uniform(0, 6.28)
        s = rnd.uniform(0.03, 0.06)
        c, sn = math.cos(a) * s, math.sin(a) * s
        mb.quad([(x - c, y - sn, z), (x + sn * 0.6, y - c * 0.6, z + 0.004), (x + c, y + sn, z),
                 (x - sn * 0.6, y + c * 0.6, z + 0.004)])
    mb.obj("Fallen_Leaves", [M["leaf"]], C)


# ======================================================================== assemble
def build_all(root, M):
    materials(M)
    rnd = RND
    Csk = coll("Skeletons", root)
    me = skeleton_mesh(M)
    arm = skeleton_armature()
    ring = [  # (angle deg around cairn, radius, pose, bury)
        (205, 1.85, "prone_propped", 0.0), (240, 1.5, "reach_crawl", 0.3),
        (272, 1.95, "prone_propped", 0.0), (303, 1.55, "reach_crawl", 0.3),
        (336, 1.45, "kneel_hunch", 0.0), (12, 1.55, "sit_reach", 0.0),
        (165, 1.45, "kneel_hunch", 0.0), (145, 1.95, "prone_propped", 0.0),
        (112, 1.22, "kneel_reach", 0.0), (66, 1.22, "kneel_reach", 0.0),
    ]
    for i, (ang, r, pose, bury) in enumerate(ring):
        a = math.radians(ang)
        loc = (CAIRN.x + r * math.cos(a), CAIRN.y + r * math.sin(a))
        make_skeleton(f"Skeleton_{i + 1:02d}_{pose}", Csk, me, arm, loc, heading_to=CAIRN, pose=pose,
                      bury=bury, ground=0.05, rnd=rnd)
    Cpo = coll("Porch_Props", root)
    for i, (x, y) in enumerate([(-4.95, -1.55), (-2.25, -1.55)]):
        rocking_chair(f"Rocking_Chair_{i + 1}", Cpo, M, (x, y, 1.1), 0.0)
        make_skeleton(f"Porch_Skeleton_{i + 1}", Csk, me, arm, (x, y - 0.05), rot_z=0.0, pose="sit_chair",
                      ground=None, jitter=0.06, rnd=rnd)
    for ob in Csk.objects:
        if ob.name.startswith("Porch_Skeleton_") and ob.type == "ARMATURE":
            ob.location.z = 1.1 + 0.48 - 0.98 + 0.01
    Cg = coll("Girls", root)
    g1, hz = mannequin("Girl_Left_LongHair", Cg, M, (-4.5, -3.45, 0.05), 0.15, 1.3, "long")
    g2, hz2 = mannequin("Girl_Center_Jawbone", Cg, M, (-3.3, -3.3, 0.05), 0.0, 1.27, None)
    mandible_headpiece("Girl_Center_Jawbone_Mandible", Cg, M, g2, hz2)
    g3, _ = mannequin("Girl_Right_LongHair", Cg, M, (-2.1, -3.45, 0.05), -0.15, 1.32, "long",
                      hair_mat="hair_light")
    Cst = coll("Antler_Staves", root)
    for i, (x, y, kind, sc, rz) in enumerate([(-5.85, -4.55, "elk", 0.95, 0.4), (-4.0, -3.15, "deer", 1.15, 0.1),
                                             (-1.55, -3.3, "deer", 1.2, -0.15), (-0.75, -5.9, "deer", 1.0, -0.6)]):
        stave(f"Stave_{i + 1}", Cst, M, (x, y, 0.0), 2.35 + 0.1 * (i % 2), rz, kind, sc,
              (RND.uniform(-0.05, 0.05), RND.uniform(-0.05, 0.05)), rnd)
    Cc = coll("Cairn", root)
    build_cairn(Cc, M, rnd)
    Cf = coll("Horned_Figure", root)
    horned_figure(Cf, M)
    build_candles(Cf, M, rnd)
    wreath("Wreath_Bay_Window", Cpo, M, (-3.6, -0.7, 3.12), 0.27, "green", rnd)
    wreath("Wreath_Twig_Door", Cpo, M, (-0.3, -0.06, 2.75), 0.23, "twig", rnd)
    ram_horns("Ram_Horns_Bay_Window", Cpo, M, (-3.6, -0.75, 2.35))
    for i, x in enumerate((0.4, 2.7)):
        star_lantern(f"Star_Lantern_{i + 1}", Cpo, M, (x, -1.3, 3.45))
    for i, (x, y, z) in enumerate([(-0.05, -3.12, 0.66), (4.3, -3.7, 0.05), (4.65, -4.1, 0.05),
                                   (3.75, -3.36, 0.66), (-0.6, -3.0, 0.05)]):
        pumpkin(f"Pumpkin_{i + 1}", Cpo, M, (x, y, z), RND.uniform(0.12, 0.2), rnd)
    Cyd = coll("Yard_Extras", root)
    ghost_in_window(Cyd, M)
    leaves(Cyd, M, rnd)
    # trash + recycling bins at the curb (they're in IMG_9899)
    mb = MB(); mb.smooth = False
    mb.box((3.85, -9.3, 0.55), (0.6, 0.72, 1.04)); mb.box((3.85, -9.33, 1.1), (0.66, 0.8, 0.06))
    mb.box((2.55, -9.35, 0.4), (0.45, 0.5, 0.74))
    mb.mi = 1
    mb.box((2.55, -9.37, 0.79), (0.5, 0.56, 0.05))
    mb.obj("Curb_Bins", [M["fixture"], M["bin_lid"]], Cyd)
    return M
