"""Anatomical human skeleton, sculpted as signed-distance fields per rig bone group, then joined into one
skinned mesh whose vertex groups match build_props.BONES (so the web articulator keeps working).
Facing -Y, standing on z=0, 1.78 m tall, arms hanging at x=+-0.18 with palms facing the thighs."""
import math
import numpy as np
import sdf as S
from hq_skull_sdf import cranium_sdf, mandible_sdf, teeth_sdf

E, C, B, CH = S.ellipsoid, S.cone, S.blade, S.chain


def T(node, dx=0, dy=0, dz=0, rx=0, ry=0, rz=0, s=1.0):
    M = np.eye(4); M[:3, :3] = S.rotm(rx, ry, rz) * s; M[:3, 3] = (dx, dy, dz)
    return S.xform(node, M)


# ----------------------------------------------------------------- spine
def spine_y(z):
    if z < 1.18:
        return 0.035 - 0.012 * math.sin(math.pi * (z - 0.98) / 0.2)
    if z < 1.5:
        return 0.035 + 0.02 * math.sin(math.pi * (z - 1.18) / 0.32)
    return 0.035 - 0.01 * math.sin(math.pi * (z - 1.5) / 0.12)


def vertebra(z, rb, h, kind):
    y = spine_y(z)
    c = np.array([0, y, z])
    parts = [C(c - (0, 0, h / 2), c + (0, 0, h / 2), rb, rb * 1.02)]
    canal = c + (0, rb + 0.009 * (rb / 0.02), 0)
    parts.append(S.torus(canal, 0.0085 * (rb / 0.02) + 0.003, 0.0035 * max(rb / 0.02, 0.7)))
    sp = {"L": 0.032, "T": 0.03, "C": 0.016}[kind]
    drop = {"L": 0.004, "T": 0.022, "C": 0.006}[kind]
    tip = canal + (0, sp, -drop)
    parts.append(B([canal + (0, 0.008, 0), tip], 0.003 if kind != "L" else 0.0045,
                   0.0065 if kind == "L" else 0.0045, nrm=(1, 0, 0)))
    tw = {"L": 0.032, "T": 0.026, "C": 0.022}[kind]
    for sx in (-1, 1):
        parts.append(C(canal + (sx * 0.006, -0.002, 0), canal + (sx * tw, 0.004 if kind != "T" else 0.012, 0.002),
                       0.004 * (1.2 if kind == "L" else 1), 0.0032))
    return S.union(*parts, k=0.004)


def spine_groups():
    vs = []
    for i in range(5):
        vs.append((1.0 + i * 0.037, 0.021, 0.026, "L"))
    for i in range(12):
        vs.append((1.188 + i * 0.026, 0.0135 + 0.0055 * (11 - i) / 11, 0.019, "T"))
    for i in range(7):
        vs.append((1.505 + i * 0.0145, 0.0105, 0.011, "C"))
    groups = {"pelvis": [], "spine": [], "chest": [], "neck": []}
    for z, rb, h, kind in vs:
        g = "pelvis" if z < 1.1 else "spine" if z < 1.3 else "chest" if z < 1.5 else "neck"
        groups[g].append(vertebra(z, rb, h, kind))
    return {g: S.union(*v) for g, v in groups.items()}


# ----------------------------------------------------------------- thorax
RX = [0.058, 0.08, 0.098, 0.11, 0.119, 0.125, 0.128, 0.128, 0.124, 0.117, 0.1, 0.08]
RY = [0.045, 0.058, 0.068, 0.075, 0.08, 0.083, 0.085, 0.085, 0.083, 0.08, 0.066, 0.05]


def ribs():
    bone, cart = [], []
    st_top, st_bot = np.array([0, -0.088, 1.455]), np.array([0, -0.104, 1.325])
    for k in range(12):
        z0 = 1.478 - k * 0.0235
        yb = spine_y(z0) + 0.025
        Rx, Ry = RX[k], RY[k]
        yc = yb - Ry
        th_end = 2.55 if k < 10 else (1.95 if k == 10 else 1.6)
        drop = 0.03 + 0.07 * min(k, 7) / 7
        for sx in (-1, 1):
            pts = [(sx * 0.016, spine_y(z0) + 0.012, z0)]
            for th in np.linspace(0.35, th_end, 9):
                f = th / th_end
                pts.append((sx * Rx * math.sin(th), yc + Ry * math.cos(th), z0 + 0.012 - drop * f ** 1.4))
            w = 0.0055 if k > 0 else 0.007
            bone.append(B(pts, [0.006] + [0.007 if k else 0.008] * (len(pts) - 1), [0.0045] + [0.0028] * (len(pts) - 1),
                          nrm=(0, 0, 1), k=0.003))
            end = np.array(pts[-1])
            if k < 7:   # true ribs: cartilage to the sternum
                t = k / 6.0
                sp = st_top * (1 - t) + st_bot * t + (sx * 0.014, 0, 0)
                mid = (end + sp) / 2 + (0, -0.004, 0.006 * k / 6)
                cart.append(CH([end, mid, sp], [0.0055, 0.005, 0.0045], k=0.002))
            elif k < 10:   # false ribs: cartilage sweeps up to the rib above
                tgt = np.array((sx * (0.045 - 0.006 * (k - 7)), -0.098 + 0.003 * (k - 7), 1.33 - 0.004 * (k - 7)))
                mid = (end + tgt) / 2 + (0, -0.01, -0.012)
                cart.append(CH([end, mid, tgt], [0.005, 0.0045, 0.004], k=0.002))
    sternum = S.union(E((0, -0.086, 1.452), (0.026, 0.007, 0.02)),
                      B([st_top + (0, 0, -0.02), st_bot], 0.016, 0.0055, nrm=(1, 0, 0)),
                      C(st_bot, st_bot + (0, -0.004, -0.03), 0.006, 0.003), k=0.006)
    return S.union(S.union(*bone), sternum), S.union(*cart)


def shoulder_girdle(sx):
    clav = CH([(sx * 0.02, -0.088, 1.472), (sx * 0.07, -0.088, 1.478), (sx * 0.13, -0.05, 1.49), (sx * 0.172, -0.005, 1.488)],
              [0.0068, 0.0058, 0.0058, 0.0075], k=0.004)
    sup, inf, gl = np.array((sx * 0.072, 0.092, 1.465)), np.array((sx * 0.1, 0.105, 1.3)), np.array((sx * 0.158, 0.035, 1.44))
    plate_c = (sup + inf + gl) / 3
    R = S.frame(sup, inf, (sx * 0.9, -0.45 * sx * sx, 0))
    plate = E(plate_c, (0.032, 0.0035, 0.083), R)
    rim = S.union(CH([sup, inf, gl, sup], [0.004, 0.0045, 0.006, 0.004], k=0.003))
    spine = CH([(sx * 0.075, 0.098, 1.418), (sx * 0.14, 0.07, 1.452), (sx * 0.175, 0.02, 1.485)], [0.004, 0.006, 0.005], k=0.004)
    acromion = E((sx * 0.175, 0.012, 1.487), (0.016, 0.014, 0.0045))
    glenoid = E(gl, (0.009, 0.012, 0.016))
    coracoid = CH([(sx * 0.14, 0.04, 1.465), (sx * 0.15, 0.0, 1.47), (sx * 0.152, -0.018, 1.462)], [0.005, 0.004, 0.0035])
    return S.union(clav, S.union(plate, rim, spine, acromion, glenoid, coracoid, k=0.006))


# ----------------------------------------------------------------- pelvis
def pelvis():
    bowl = S.shell(E((0, 0.012, 1.065), (0.135, 0.085, 0.1)), 0.0035)
    parts = []
    for sx in (-1, 1):
        wing = S.inter(bowl, E((sx * 0.1, 0.012, 1.075), (0.06, 0.09, 0.052)), k=0.004)
        parts.append(wing)
        crest = [(sx * 0.135 * math.sin(b), 0.012 + 0.085 * math.cos(b), 1.118 - 0.03 * (b - 0.5) / 1.7) for b in np.linspace(0.5, 2.2, 8)]
        parts.append(CH(crest, [0.006, 0.0075, 0.008, 0.008, 0.0075, 0.007, 0.0065, 0.0075], k=0.004))
        ac = np.array((sx * 0.092, -0.004, 0.968))
        parts.append(S.sub(E(ac, (0.025, 0.025, 0.025)), S.sphere(ac + (-sx * 0.012, 0, 0), 0.02), k=0.003))
        parts.append(CH([ac + (sx * 0.006, 0.012, 0.02), (sx * 0.112, 0.02, 1.03)], [0.016, 0.009], k=0.006))   # body of ilium
        parts.append(CH([(sx * 0.115, -0.05, 1.08), ac + (sx * 0.01, -0.01, 0.02)], [0.007, 0.012], k=0.005))     # anterior border
        parts.append(CH([(sx * 0.052, 0.07, 1.06), ac + (0, 0.02, 0.012)], [0.008, 0.012], k=0.005))              # sciatic border
        # pubis + ischium ring (obturator foramen in the middle)
        parts.append(CH([ac + (-sx * 0.01, -0.012, 0.004), (sx * 0.045, -0.05, 0.965), (sx * 0.012, -0.06, 0.955)],
                        [0.009, 0.0075, 0.009], k=0.004))
        parts.append(CH([(sx * 0.012, -0.058, 0.945), (sx * 0.04, -0.035, 0.915), (sx * 0.07, 0.0, 0.905), ac + (0, 0.012, -0.02)],
                        [0.008, 0.0075, 0.012, 0.013], k=0.004))
    sac = S.union(E((0, 0.064, 1.03), (0.045, 0.017, 0.058), S.rotm(-0.45, 0, 0)),
                  C((0, 0.086, 0.985), (0, 0.098, 0.955), 0.012, 0.005), k=0.008)
    return S.union(S.union(*parts, k=0.008), sac, k=0.008)


# ----------------------------------------------------------------- limbs
def humerus(sx):
    x = sx * 0.18
    return S.union(
        S.sphere((sx * 0.166, 0.004, 1.442), 0.023),
        S.sphere((sx * 0.186, -0.008, 1.442), 0.014),
        C((x, 0.0, 1.425), (x, 0.004, 1.2), 0.0115, 0.0095),
        E((x, 0.006, 1.18), (0.03, 0.011, 0.013)),
        S.sphere((x + sx * 0.012, -0.004, 1.168), 0.0095),
        E((x - sx * 0.009, -0.004, 1.167), (0.011, 0.009, 0.0085)),
        k=0.012)


def forearm(sx):
    x = sx * 0.18
    ulna = S.union(E((x - sx * 0.008, 0.016, 1.172), (0.009, 0.01, 0.014)),
                   C((x - sx * 0.008, 0.006, 1.16), (x - sx * 0.008, 0.004, 0.925), 0.0085, 0.0045),
                   S.sphere((x - sx * 0.008, 0.004, 0.921), 0.006), k=0.006)
    radius = S.union(C((x + sx * 0.011, -0.002, 1.156), (x + sx * 0.011, -0.002, 1.148), 0.0095, 0.009),
                     C((x + sx * 0.011, -0.002, 1.15), (x + sx * 0.012, -0.006, 0.93), 0.0055, 0.0105),
                     C((x + sx * 0.016, -0.006, 0.93), (x + sx * 0.017, -0.006, 0.918), 0.004, 0.0025), k=0.006)
    return S.union(ulna, radius)


def hand(sx, curl=0.35):
    x = sx * 0.18
    parts = []
    for i, (cy, cz) in enumerate([(-0.012, 0.905), (0.0, 0.906), (0.012, 0.903), (-0.008, 0.893), (0.004, 0.892), (0.015, 0.893)]):
        parts.append(E((x + sx * 0.001 * (i % 2), cy, cz), (0.0085, 0.0075, 0.0065)))
    fingers = [(-0.015, 1.0), (-0.004, 1.08), (0.007, 1.0), (0.017, 0.84)]
    for ys, L in fingers:
        base = np.array((x, ys * 0.9, 0.885))
        head = np.array((x - sx * 0.002, ys * 1.1, 0.83 + (1 - L) * 0.02))
        parts.append(CH([base, head], [0.0048, 0.0036], k=0.002))
        parts.append(S.sphere(head, 0.0047))
        p, d, ang = head, np.array((0, ys * 0.1, -1.0)), 0.0
        for seg, sl in enumerate((0.038, 0.024, 0.017)):
            ang += curl * (0.6 + 0.3 * seg)
            dirv = np.array((-sx * math.sin(ang), d[1] * 0.3, -math.cos(ang)))
            q = p + dirv * sl * L
            r0 = 0.0042 - 0.0007 * seg
            parts.append(CH([p, q], [r0, r0 * 0.82], k=0.001))
            parts.append(E(q, (r0 * 0.95, r0 * 1.05, r0 * 0.8)))
            p = q
    th = [np.array((x - sx * 0.003, -0.02, 0.9)), np.array((x - sx * 0.012, -0.036, 0.868)),
          np.array((x - sx * 0.018, -0.046, 0.842)), np.array((x - sx * 0.022, -0.052, 0.822))]
    parts.append(CH(th, [0.0055, 0.0048, 0.0042, 0.0034], k=0.002))
    for q in th[1:]:
        parts.append(S.sphere(q, 0.0047))
    return S.union(*parts, k=0.0016)


def femur(sx):
    return S.union(
        S.sphere((sx * 0.083, 0.0, 0.966), 0.0225),
        C((sx * 0.085, 0.0, 0.964), (sx * 0.122, 0.003, 0.935), 0.0135, 0.016),
        E((sx * 0.133, 0.01, 0.95), (0.016, 0.017, 0.022)),
        C((sx * 0.124, 0.003, 0.92), (sx * 0.1, -0.004, 0.58), 0.0145, 0.0135),
        E((sx * 0.1, 0.004, 0.56), (0.035, 0.022, 0.022)),
        S.sphere((sx * 0.082, 0.008, 0.545), 0.019),
        S.sphere((sx * 0.118, 0.008, 0.545), 0.018),
        k=0.012)


def shin(sx):
    x = sx * 0.1
    tib = S.union(E((x, 0.002, 0.512), (0.036, 0.026, 0.011)),
                  E((x, -0.02, 0.488), (0.01, 0.008, 0.014)),
                  C((x, 0.0, 0.5), (x - sx * 0.004, 0.002, 0.13), 0.0165, 0.0115),
                  E((x - sx * 0.003, 0.002, 0.115), (0.021, 0.018, 0.012)),
                  S.sphere((x - sx * 0.019, 0.002, 0.1), 0.01), k=0.01)
    fib = S.union(S.sphere((x + sx * 0.028, 0.012, 0.49), 0.009),
                  C((x + sx * 0.028, 0.012, 0.485), (x + sx * 0.026, 0.01, 0.12), 0.0055, 0.005),
                  E((x + sx * 0.027, 0.008, 0.098), (0.008, 0.009, 0.013)), k=0.006)
    pat = E((x, -0.031, 0.54), (0.018, 0.008, 0.021))
    return S.union(tib, fib, pat)


def foot(sx):
    x = sx * 0.1
    tars = [E((x, 0.004, 0.083), (0.017, 0.022, 0.012)),                # talus
             E((x + sx * 0.003, 0.035, 0.058), (0.016, 0.034, 0.02), S.rotm(-0.25, 0, 0)),   # calcaneus
             E((x - sx * 0.006, -0.03, 0.07), (0.016, 0.011, 0.013)),
             E((x + sx * 0.016, -0.025, 0.058), (0.012, 0.013, 0.011)),
             E((x, -0.045, 0.06), (0.026, 0.009, 0.01))]
    parts = [S.union(*tars, k=0.012)]
    toes = [(-0.022, 0.0085, 1.0), (-0.008, 0.0055, 0.95), (0.004, 0.005, 0.9), (0.015, 0.0048, 0.84), (0.026, 0.0046, 0.76)]
    for dx, r, L in toes:
        b = np.array((x + sx * dx, -0.05, 0.058))
        h = np.array((x + sx * dx * 1.15, -0.05 - 0.072 * L, 0.024))
        parts.append(CH([b, h], [r, r * 0.8], k=0.002))
        parts.append(S.sphere(h, r * 0.95))
        p = h
        for seg, sl in enumerate((0.028, 0.014, 0.01)[: 2 if dx == -0.022 else 3]):
            q = p + np.array((sx * dx * 0.05, -sl * L, -0.003 if seg == 0 else -0.002))
            parts.append(CH([p, q], [r * 0.8 - 0.0006 * seg, r * 0.7 - 0.0006 * seg], k=0.001))
            p = q
    return S.union(*parts, k=0.004)


# ----------------------------------------------------------------- assembly
HEAD_T = dict(dx=0, dy=-0.004, dz=1.69)


def groups():
    """[(group, node, voxel, target_tris, material_key)]"""
    out = []
    sk = T(S.noisy(cranium_sdf(), 0.0004, 90, 3), **HEAD_T)
    jw = T(mandible_sdf(), **HEAD_T)
    th = T(S.union(teeth_sdf(True), teeth_sdf(False)), **HEAD_T)
    out += [("head", sk, 0.0014, 8000, "bone"), ("head", jw, 0.0014, 2600, "bone"), ("head", th, 0.0008, 1600, "tooth")]
    for g, n in spine_groups().items():
        out.append((g, n, 0.0013, {"pelvis": 1200, "spine": 1700, "chest": 2600, "neck": 1200}[g], "bone"))
    rb, cart = ribs()
    out += [("chest", rb, 0.0014, 6000, "bone"), ("chest", cart, 0.0014, 1600, "cartilage")]
    out.append(("pelvis", pelvis(), 0.0016, 3200, "bone"))
    for s, sx in (("L", 1), ("R", -1)):
        out.append(("chest", shoulder_girdle(sx), 0.0014, 1800, "bone"))
        out.append((f"upper_arm.{s}", humerus(sx), 0.0016, 1400, "bone"))
        out.append((f"forearm.{s}", forearm(sx), 0.0014, 1500, "bone"))
        out.append((f"hand.{s}", hand(sx), 0.0009, 3000, "bone"))
        out.append((f"thigh.{s}", femur(sx), 0.0018, 1800, "bone"))
        out.append((f"shin.{s}", shin(sx), 0.0016, 2000, "bone"))
        out.append((f"foot.{s}", foot(sx), 0.0011, 2400, "bone"))
    return out


def build(name, M, noise=True):
    """Returns one joined mesh object with vertex groups per rig bone (not yet parented to a rig)."""
    import bpy
    objs = []
    for i, (g, node, vox, target, mk) in enumerate(groups()):
        if noise and g != "head":
            node = S.noisy(node, 0.00035, 110, 2)
        ob = S.mesh(node, f"{name}_{g}_{i}", vox, [M[mk]], target=target)
        vg = ob.vertex_groups.new(name=g)
        vg.add(list(range(len(ob.data.vertices))), 1.0, "REPLACE")
        objs.append(ob)
    bpy.ops.object.select_all(action="DESELECT")
    for o in objs:
        o.select_set(True)
    bpy.context.view_layer.objects.active = objs[0]
    bpy.ops.object.join()
    ob = bpy.context.view_layer.objects.active
    ob.name = name
    return ob
