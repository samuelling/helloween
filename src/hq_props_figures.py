"""Batch C (part 2) — figures: mannequins of the 2026 display, levitating woman, plague doctor, scarecrow, ghost."""
import math, random
import numpy as np
import bpy, bmesh
from mathutils import Vector as V, Matrix, Euler
from mathutils.bvhtree import BVHTree
import props_lib as PL
import build_props as BP
from lib import MB, empty
import hq_lib as H
import sdf as S
import hq_animal as A
from hq_props_bones import mk, mat4, parent
from hq_props_occult import hand_sdf, remove, mats as occ_mats
from hq_props_grave import gmats
from hq_registry import hq

E, C, B, CH = S.ellipsoid, S.cone, S.blade, S.chain


def fmats(M):
    gmats(M)
    M["hair_blonde"] = H.hq_mat("HQ_Hair_Blonde", (0.32, 0.22, 0.1), (0.62, 0.48, 0.28), 0.45, 30, 0.6, 120, kind="weave")
    M["felt"] = H.hq_mat("HQ_Felt", (0.03, 0.025, 0.022), (0.1, 0.085, 0.07), 0.95, 30, 0.4, 100)
    M["flannel_hq"] = plaid_mat("HQ_Flannel", (0.32, 0.03, 0.025), (0.03, 0.02, 0.02), (0.6, 0.5, 0.35))
    M["straw_hq"] = H.hq_mat("HQ_Straw", (0.45, 0.33, 0.12), (0.8, 0.66, 0.32), 0.7, 40, 0.6, 120, kind="weave")
    M["gown_ivory"] = H.hq_mat("HQ_Gown_Ivory", (0.62, 0.58, 0.5), (0.82, 0.78, 0.7), 0.85, 140, 0.3, 300, kind="weave", sss=0.1)
    M["shoe"] = H.hq_mat("HQ_Shoe", (0.01, 0.01, 0.012), (0.04, 0.035, 0.04), 0.25, 10, 0.1, 30)
    M["eye_paint"] = H.hq_mat("HQ_Painted_Eye", (0.03, 0.025, 0.03), (0.12, 0.1, 0.12), 0.15, 10, 0.0, 30)
    M["lens_green"] = M["eye_green"]
    return M


def plaid_mat(name, c_base, c_line, c_thread):
    m = bpy.data.materials.get(name)
    if m:
        return m
    m = H.mat(name, c_base, 0.9)
    nt = m.node_tree; b = nt.nodes["Principled BSDF"]
    tc = H.tex_coord(m, "Object")
    sep = nt.nodes.new("ShaderNodeSeparateXYZ"); nt.links.new(tc, sep.inputs["Vector"])
    def bands(sock, scale):
        mth = nt.nodes.new("ShaderNodeMath"); mth.operation = "MULTIPLY"; mth.inputs[1].default_value = scale
        nt.links.new(sock, mth.inputs[0])
        s = nt.nodes.new("ShaderNodeMath"); s.operation = "SINE"; nt.links.new(mth.outputs[0], s.inputs[0])
        g = nt.nodes.new("ShaderNodeMath"); g.operation = "GREATER_THAN"; g.inputs[1].default_value = 0.55
        nt.links.new(s.outputs[0], g.inputs[0])
        return g.outputs[0]
    bx, bz = bands(sep.outputs["X"], 45), bands(sep.outputs["Z"], 45)
    mx = nt.nodes.new("ShaderNodeMath"); mx.operation = "MAXIMUM"; nt.links.new(bx, mx.inputs[0]); nt.links.new(bz, mx.inputs[1])
    mix = nt.nodes.new("ShaderNodeMix"); mix.data_type = "RGBA"
    nt.links.new(mx.outputs[0], mix.inputs["Factor"]); mix.inputs["A"].default_value = (*c_base, 1); mix.inputs["B"].default_value = (*c_line, 1)
    thin = bands(sep.outputs["X"], 180)
    mix2 = nt.nodes.new("ShaderNodeMix"); mix2.data_type = "RGBA"
    f2 = nt.nodes.new("ShaderNodeMath"); f2.operation = "MULTIPLY"; f2.inputs[1].default_value = 0.35; nt.links.new(thin, f2.inputs[0])
    nt.links.new(f2.outputs[0], mix2.inputs["Factor"]); nt.links.new(mix.outputs["Result"], mix2.inputs["A"]); mix2.inputs["B"].default_value = (*c_thread, 1)
    nt.links.new(mix2.outputs["Result"], b.inputs["Base Color"])
    n2 = nt.nodes.new("ShaderNodeTexWave"); n2.wave_type = "BANDS"; n2.bands_direction = "DIAGONAL"; n2.inputs["Scale"].default_value = 300
    nt.links.new(tc, n2.inputs["Vector"]); H.add_bump(m, n2.outputs["Fac"], 0.25, 0.002)
    return m


# ------------------------------------------------------------------ mannequin
CHILD_DRESS = [(0.27, 0.42), (0.25, 0.5), (0.2, 0.64), (0.155, 0.77), (0.125, 0.85), (0.135, 0.92), (0.125, 0.975), (0.08, 0.995), (0.05, 1.0)]
GOWN = [(0.19, 0.1), (0.18, 0.2), (0.165, 0.4), (0.145, 0.62), (0.13, 0.8), (0.125, 0.9), (0.135, 0.99), (0.13, 1.05), (0.09, 1.09), (0.045, 1.1)]


def mannequin(h=1.3, gown=False, hair="long", seed=0, sleeves="puff"):
    """SDF nodes for a doll-like mannequin facing -Y on z=0. Returns dict(skin, dress, hair, eyes, shoes, hz, k)."""
    k = h / 1.3
    prof = [(r * k, z * k) for r, z in (GOWN if gown else CHILD_DRESS)]
    z_hem, top = prof[0][1], prof[-1][1]
    dress = S.revolve((0, 0, 0), prof, S.folds(9, 0.022 * k, z_hem, z_hem + (top - z_hem) * 0.7, seed, 0.002 * k), sy=0.8)
    skin, shoes = [], []
    if gown:
        for sx in (-1, 1):
            skin.append(C((0.075 * sx * k, 0, 0.04 * k), (0.075 * sx * k, 0, 0.3 * k), 0.032 * k, 0.036 * k))
            skin.append(E((0.075 * sx * k, -0.045 * k, 0.025 * k), (0.032 * k, 0.07 * k, 0.025 * k)))
    else:
        for sx in (-1, 1):
            skin.append(C((0.06 * sx * k, 0, 0.06 * k), (0.06 * sx * k, 0, 0.5 * k), 0.028 * k, 0.034 * k))
            skin.append(E((0.06 * sx * k, -0.004 * k, 0.3 * k), (0.03 * k, 0.03 * k, 0.03 * k)))
            shoes.append(S.union(E((0.06 * sx * k, -0.03 * k, 0.03 * k), (0.032 * k, 0.065 * k, 0.03 * k)),
                                 S.box((0.06 * sx * k, -0.03 * k, 0.008 * k), (0.06 * k, 0.13 * k, 0.016 * k), 0.006 * k), k=0.01 * k))
    sh_z = top - 0.07 * k
    for sx in (-1, 1):
        s0 = np.array((0.125 * sx * k, 0, sh_z))
        if gown:
            el = s0 + np.array((0.03 * sx * k, -0.01 * k, -0.25 * k))
            wr = s0 + np.array((0.055 * sx * k, -0.06 * k, -0.44 * k))
            sl = S.union(C(s0, el, 0.045 * k, 0.07 * k), C(el, el + (wr - el) * 0.45, 0.07 * k, 0.085 * k), k=0.02 * k)
            sl = S.sub(sl, S.sphere(el + (wr - el) * 0.6, 0.075 * k), k=0.01 * k)
            dress = S.union(dress, S.noisy(sl, 0.004 * k, 12 / k, 2, stretch=(0.6, 0.6, 2)), k=0.02 * k)
        else:
            el = s0 + np.array((0.03 * sx * k, -0.01 * k, -0.18 * k))
            wr = s0 + np.array((0.045 * sx * k, -0.03 * k, -0.36 * k))
            dress = S.union(dress, S.noisy(E(s0 + (sx * 0.01 * k, 0, -0.01 * k), (0.05 * k, 0.045 * k, 0.045 * k)), 0.003 * k, 20, 2), k=0.015 * k)
        skin.append(S.union(C(s0 + (0, 0, -0.02 * k), el, 0.022 * k, 0.019 * k), C(el, wr, 0.019 * k, 0.015 * k), k=0.01 * k))
        skin.append(hand_sdf(wr, wr - el, (-sx, 0.3, 0), 0.55 * k, curl=0.25, spread=0.05, skinny=1.25))
    hz = top + 0.14 * k
    neck = C((0, 0, top - 0.04 * k), (0, 0.004 * k, top + 0.07 * k), 0.032 * k, 0.028 * k)
    head = S.union(E((0, 0.0, hz), (0.073 * k, 0.08 * k, 0.092 * k)), E((0, -0.03 * k, hz - 0.045 * k), (0.052 * k, 0.05 * k, 0.05 * k)),
                   E((0, -0.077 * k, hz - 0.005 * k), (0.011 * k, 0.012 * k, 0.017 * k)),                               # nose
                   *[E((sx * 0.072 * k, 0.0, hz - 0.005 * k), (0.008 * k, 0.016 * k, 0.022 * k)) for sx in (-1, 1)],   # ears
                   E((0, -0.07 * k, hz - 0.045 * k), (0.018 * k, 0.008 * k, 0.006 * k)), k=0.02 * k)                      # lips
    head = S.sub(head, *[E((sx * 0.03 * k, -0.075 * k, hz + 0.012 * k), (0.018 * k, 0.012 * k, 0.011 * k)) for sx in (-1, 1)], k=0.008 * k)
    skin += [neck, head]
    eyes = S.union(*[E((sx * 0.03 * k, -0.064 * k, hz + 0.012 * k), (0.012 * k, 0.007 * k, 0.008 * k)) for sx in (-1, 1)])
    hair_n = None
    if hair:
        L = (0.45 if hair == "long" else 0.25) * k
        cap = S.inter(E((0, 0.012 * k, hz + 0.012 * k), (0.081 * k, 0.088 * k, 0.1 * k)), S.plane_cut((0, 0.4, -1), -(hz - 0.0 * k) * 1.0 + 0.0) if False else
                      S.union(S.box((0, 0.06 * k, hz), (0.3 * k, 0.15 * k, 0.4 * k)), S.box((0, 0, hz + 0.06 * k), (0.3 * k, 0.3 * k, 0.12 * k))))
        back = S.union(B([(0, 0.05 * k, hz + 0.02 * k), (0, 0.075 * k, hz - L * 0.4), (0, 0.06 * k, hz - L)], [0.095 * k, 0.11 * k, 0.1 * k],
                         [0.035 * k, 0.03 * k, 0.012 * k], nrm=(1, 0, 0)),
                       *[CH([(sx * 0.072 * k, -0.01 * k, hz + 0.0), (sx * 0.08 * k, -0.02 * k, hz - L * 0.4), (sx * 0.085 * k, -0.035 * k, hz - L * 0.75)],
                            [0.022 * k, 0.026 * k, 0.012 * k], k=0.01 * k) for sx in (-1, 1)], k=0.02 * k)
        hair_n = S.union(cap, back, k=0.02 * k)
        hair_n = S.noisy(S.noisy(hair_n, 0.004 * k, 120 / k, 2, ridged=True, stretch=(1, 1, 0.08)), 0.002 * k, 300, 1)
    return {"skin": S.union(*skin, k=0.012 * k), "dress": S.noisy(dress, 0.0012 * k, 60, 2), "hair": hair_n, "eyes": eyes,
            "shoes": S.union(*shoes) if shoes else None, "hz": hz, "k": k}


def mannequin_objs(M, P, name, dress_key, hair_key="hair"):
    k = P["k"]
    objs = [mk(P["skin"], name + "_Skin", 0.0026 * k, M["skin"], 14000), mk(P["dress"], name + "_Dress", 0.004 * k, M[dress_key], 14000),
            mk(P["eyes"], name + "_Eyes", 0.0015 * k, M["eye_paint"], 600)]
    if P["hair"] is not None:
        objs.append(mk(P["hair"], name + "_Hair", 0.003 * k, M[hair_key], 12000))
    if P["shoes"] is not None:
        objs.append(mk(P["shoes"], name + "_Shoes", 0.002 * k, M["shoe"], 2000))
    return objs


@hq("mannequin_girl", 1024)
def mannequin_girl(M):
    fmats(M)
    root = PL.root_empty("mannequin_girl")
    P = mannequin(1.3, False, "long", 2)
    parent(mannequin_objs(M, P, "Girl", "dress", "hair_blonde"), root)
    return {"name": "Mannequin girl", "cat": "2026 display", "desc": "Doll-faced girl with long hair in a pleated peach dress and patent shoes."}


@hq("jawbone_girl", 1024)
def jawbone_girl(M):
    fmats(M)
    root = PL.root_empty("jawbone_girl")
    P = mannequin(1.27, False, None, 3)
    objs = mannequin_objs(M, P, "Girl", "dress")
    hz, k = P["hz"], P["k"]
    jaw, teeth = A.cow_mandible_sdf()
    T = np.eye(4); T[:3, :3] = S.rotm(0.05, 0, 0) * 0.95; T[:3, 3] = (-0.088 * k, 0.03 * k, hz - 0.1 * k)
    objs.append(mk(S.noisy(S.xform(jaw, T), 0.0006, 70, 2), "Cow_Mandible", 0.0018, M["bone_old"], 7000))
    objs.append(mk(S.xform(teeth, T), "Cow_Molars", 0.0014, M["tooth"], 2500))
    tw = S.union(*[S.torus((0, -0.004 * k, hz + dz * k), 0.08 * k, 0.0035, S.rotm(math.radians(t), 0, 0)) for dz, t in ((0.035, 8), (-0.02, -10))])
    objs.append(mk(S.noisy(tw, 0.0006, 300, 1), "Jaw_Twine", 0.0014, M["twine"], 2500))
    parent(objs, root)
    return {"name": "Jawbone girl", "cat": "2026 display", "desc": "Bald mannequin girl with a weathered cow jawbone lashed to her head with twine."}


def oryx_parts(M, base, k=1.0):
    sk, th = A.deer_skull_sdf(0.75 * k)
    T = np.eye(4); T[:3, :3] = S.rotm(1.32, 0, 0); T[:3, 3] = base
    horns = []
    for s in (-1, 1):
        a = np.array(base) + (s * 0.028 * k, -0.035 * k, 0.03 * k)
        pts = [a + np.array((s * 0.14 * t * k, (0.05 * t + 0.09 * t * t) * k, 1.05 * t * k)) for t in np.linspace(0, 1, 8)]
        h = A.horn_curve_sdf(pts, 0.036 * k, 0.008 * k, 0.0)
        rings = S.union(*[S.torus(pts[0] + (pts[-1] - pts[0]) * t, (0.036 - 0.02 * t) * k * 1.02, 0.005 * k, S.frame(pts[0], pts[-1])) for t in np.linspace(0.04, 0.45, 12)])
        horns.append(S.union(h, rings, k=0.003))
    return [mk(S.noisy(S.xform(sk, T), 0.0005, 80, 2), "Oryx_Skull_Bone", 0.0013, M["bone_old"], 5000),
            mk(S.xform(th, T), "Oryx_Teeth", 0.001, M["tooth"], 500),
            mk(S.union(*horns), "Oryx_Horns", 0.002, M["horn"], 7000)]


@hq("horned_figure", 1024)
def horned_figure(M):
    fmats(M)
    root = PL.root_empty("horned_figure")
    P = mannequin(1.72, True, "long", 5)
    objs = mannequin_objs(M, P, "Horned_Figure", "linen", "hair")
    hz = P["hz"]
    objs += oryx_parts(M, (0, -0.13, hz + 0.06), 1.15)
    tw = S.union(*[CH([(0.04 * s, -0.05, hz + 0.12), (0.0, 0.3, 2.57)], 0.0025) for s in (1, -1)])
    objs.append(mk(tw, "Oryx_Hanging_Twine", 0.0016, M["twine"], 1200))
    parent(objs, root)
    return {"name": "Horned figure", "cat": "2026 display", "desc": "Long-haired mannequin in a tan gown, face hidden behind a hanging oryx skull with ringed horns."}


@hq("levitating_woman", 1024)
def levitating_woman(M):
    fmats(M)
    occ_mats(M)
    fmats(M)
    root = PL.root_empty("levitating_woman")
    piv = empty("Levitate_Pivot", (0, 0, 0), None, 0.2)
    piv.parent = root
    P = mannequin(1.7, True, None, 7)
    objs = mannequin_objs(M, P, "Levitating", "gown_ivory")
    Tw = mat4((0, -0.85, 2.3), (-math.pi / 2, 0, 0))
    for o in objs:
        o.matrix_world = Tw @ o.matrix_world
    rnd = random.Random(4)
    drapes = []
    for sx in (-1, 1):
        for y in np.linspace(-0.7, 0.3, 5):
            top = np.array((sx * 0.13, y, 2.24)); bot = top + np.array((sx * 0.03 + rnd.uniform(-0.01, 0.01), rnd.uniform(-0.03, 0.03), -rnd.uniform(0.22, 0.34)))
            drapes.append(B([top, (top + bot) / 2 + (sx * 0.02, 0, 0), bot], 0.006, [0.12, 0.11, 0.09], nrm=(1, 0, 0), k=0.03))
    hem = S.noisy(S.union(*drapes, k=0.04), 0.003, 8, 2, stretch=(1, 0.6, 0.15))
    objs.append(mk(hem, "Gown_Drape", 0.004, M["gown_ivory"], 9000))
    strands = []
    hc = np.array((0, 0.86, 2.3))
    for i in range(46):
        a = rnd.uniform(-1.4, 1.4); rr = 0.07
        p0 = hc + np.array((rr * math.sin(a), rnd.uniform(-0.03, 0.05), -rr * math.cos(a) * 0.6))
        L = rnd.uniform(0.6, 0.78)
        pts = [p0 + np.array((math.sin(a) * 0.04 * t + 0.01 * math.sin(t * 9 + i), 0.04 * t + rnd.uniform(-0.01, 0.01), -L * t)) for t in np.linspace(0, 1, 7)]
        strands.append(CH(pts, [0.009, 0.008, 0.007, 0.006, 0.005, 0.004, 0.002], k=0.004))
    hair = S.noisy(S.union(*strands, S.inter(E(hc + (0, 0.01, 0.01), (0.085, 0.09, 0.085)), S.box(hc + (0, 0.04, 0), (0.3, 0.12, 0.3))), k=0.006), 0.0015, 200, 1, ridged=True, stretch=(1, 1, 0.1))
    objs.append(mk(hair, "Hanging_Hair", 0.003, M["hair"], 14000))
    for o in objs:
        mw = o.matrix_world.copy(); o.parent = piv; o.matrix_world = mw
    return {"name": "Levitating woman", "cat": "Occult", "behaviors": ["levitate"],
            "desc": "Nightgowned figure floating face-up at 2.3 m, gown and long hair hanging toward the lawn."}


@hq("plague_doctor", 1024)
def plague_doctor(M):
    fmats(M)
    root = PL.root_empty("plague_doctor")
    P = mannequin(1.8, True, None, 9)
    hz, k = P["hz"], P["k"]
    objs = [mk(P["skin"], "Plague_Body", 0.004, M["leather"], 9000)]
    coat = S.revolve((0, 0, 0), [(0.38, 0.04), (0.35, 0.3), (0.3, 0.7), (0.25, 1.1), (0.22, 1.35), (0.25, 1.44), (0.14, 1.5), (0.08, 1.53)],
                     S.folds(11, 0.035, 0.04, 1.1, 9), sy=0.85)
    cape = S.revolve((0, 0, 0), [(0.36, 1.18), (0.33, 1.3), (0.27, 1.42), (0.14, 1.5), (0.07, 1.54)], S.folds(14, 0.02, 1.18, 1.45, 3), sy=0.85)
    coat = S.union(coat, S.noisy(cape, 0.004, 10, 2), k=0.03)
    sleeves = []
    for sx in (-1, 1):
        s0 = np.array((0.17 * sx, 0, 1.44)); el = s0 + (0.05 * sx, -0.06, -0.33); wr = el + (0.01 * sx if sx < 0 else 0.1, -0.16, -0.1)
        sleeves.append(S.noisy(S.union(C(s0, el, 0.06, 0.068), C(el, wr, 0.068, 0.08), k=0.03), 0.005, 10, 2, stretch=(0.6, 0.6, 2)))
        objs.append(mk(hand_sdf(wr, wr - el, (0, 0, -1) if sx > 0 else (-sx, 0, 0), 0.95, curl=0.7 if sx > 0 else 0.3), f"Glove_{sx + 1}", 0.0025, M["leather"], 3000))
    objs.append(mk(S.noisy(S.union(coat, *sleeves, k=0.04), 0.0015, 50, 2), "Plague_Coat", 0.006, M["robe_black"], 18000))
    mask = S.union(E((0, -0.005, hz), (0.095, 0.1, 0.11)),
                   CH([(0, -0.07, hz - 0.02), (0, -0.2, hz - 0.09), (0, -0.33, hz - 0.17), (0, -0.4, hz - 0.24)], [0.065, 0.045, 0.022, 0.006], k=0.02), k=0.03)
    seams = S.union(*[S.torus((0, -0.07 - 0.07 * i, hz - 0.02 - 0.05 * i), 0.06 - 0.012 * i, 0.003, S.rotm(1.0, 0, 0)) for i in range(4)])
    objs.append(mk(S.noisy(S.union(mask, seams, k=0.003), 0.0008, 90, 2), "Beak_Mask", 0.0025, M["leather"], 9000))
    rims = S.union(*[S.torus((sx * 0.042, -0.088, hz + 0.03), 0.026, 0.006, S.rotm(math.pi / 2 - 0.2, 0, 0)) for sx in (-1, 1)])
    objs.append(mk(rims, "Lens_Rims", 0.0015, M["gilt"], 2000))
    lens = MB()
    for sx in (-1, 1):
        lens.sphere((sx * 0.042, -0.088, hz + 0.03), 0.024, (1, 0.35, 1), (0.2, 0, 0), segs=(16, 8))
    objs.append(lens.obj("Lenses", [M["eye_green"]]))
    hat = S.union(S.revolve((0, 0, 0), [(0.34, hz + 0.07), (0.345, hz + 0.08), (0.13, hz + 0.1), (0.115, hz + 0.29), (0.001, hz + 0.3)],
                            lambda th, z: 0.012 * np.sin(3 * th) * np.clip((hz + 0.09 - z) * 50, 0, 1)), S.torus((0, 0, hz + 0.11), 0.118, 0.012), k=0.01)
    objs.append(mk(S.noisy(hat, 0.001, 50, 2), "Wide_Hat", 0.003, M["felt"], 6000))
    cane = S.union(C((0.32, -0.15, 0.0), (0.3, -0.18, 1.22), 0.012, 0.012), S.sphere((0.3, -0.18, 1.24), 0.03), k=0.006)
    objs.append(mk(cane, "Cane", 0.002, M["walnut"], 2000))
    parent(objs, root)
    return {"name": "Plague doctor", "cat": "Ghouls", "desc": "1.9 m plague doctor: stitched leather beak mask, glowing green lenses in brass, caped coat, wide hat and cane."}


@hq("scarecrow", 1024)
def scarecrow(M):
    fmats(M)
    root = PL.root_empty("scarecrow")
    rnd = random.Random(5)
    wood = S.noisy(S.union(S.box((0, 0.05, 0.95), (0.08, 0.08, 2.1), 0.006), S.box((0, 0.05, 1.5), (1.4, 0.07, 0.07), 0.006), k=0.004),
                   0.003, 5, 3, stretch=(1, 1, 0.08))
    objs = [mk(wood, "Scarecrow_Post", 0.005, M["timber"], 5000)]
    shirt = S.revolve((0, 0, 0), [(0.21, 0.82), (0.23, 0.95), (0.2, 1.25), (0.22, 1.47), (0.12, 1.56), (0.05, 1.59)], S.folds(8, 0.015, 0.82, 1.4, 2), sy=0.7)
    sleeves = [S.noisy(CH([(0.15 * sx, 0.02, 1.49), (0.38 * sx, 0.02, 1.48), (0.62 * sx, 0.02, 1.46)], [0.09, 0.085, 0.075], k=0.02), 0.01, 10, 2, stretch=(0.3, 1, 1)) for sx in (-1, 1)]
    patch = S.box((0.08, -0.15, 1.15), (0.1, 0.02, 0.1), 0.01, S.rotm(0, 0.1, 0.1))
    objs.append(mk(S.noisy(S.union(shirt, *sleeves, k=0.03), 0.0015, 40, 2), "Flannel_Shirt", 0.005, M["flannel_hq"], 12000))
    objs.append(mk(S.inter(patch, S.offset(shirt, 0.006)), "Shirt_Patch", 0.003, M["burlap"], 800))
    tufts = []
    def tuft(c, d, n, L):
        straw = []
        for _ in range(n):
            dd = np.array(d) + np.array([rnd.uniform(-0.5, 0.5) for _ in range(3)])
            dd = dd / np.linalg.norm(dd)
            straw.append(C(np.array(c), np.array(c) + dd * L * rnd.uniform(0.6, 1.2), 0.004, 0.0012))
        tufts.append(mk(S.union(*straw), f"Straw_{len(tufts)}", 0.0018, M["straw_hq"], 3000))
    for sx in (-1, 1):
        tuft((0.66 * sx, 0.02, 1.46), (sx, 0, 0), 22, 0.14)
    for a in np.linspace(0, 2 * math.pi, 5)[:-1]:
        tuft((0.15 * math.cos(a), 0.1 * math.sin(a), 0.84), (math.cos(a) * 0.4, math.sin(a) * 0.4, -1), 12, 0.2)
    tuft((0, 0, 1.6), (0, 0, 1), 26, 0.08)
    objs.append(H.join(tufts, "Straw"))
    head = S.noisy(S.union(E((0, 0, 1.78), (0.165, 0.16, 0.185)), C((0, 0, 1.6), (0, 0, 1.66), 0.07, 0.09), k=0.04), 0.008, 7, 3)
    head = S.sub(head, S.torus((0, 0, 1.63), 0.085, 0.02), k=0.01)
    objs.append(mk(head, "Burlap_Head", 0.004, M["burlap"], 9000))
    face = []
    for sx in (-1, 1):
        c = np.array((0.06 * sx, -0.155, 1.82))
        face.append(CH([c + (-0.025, 0, 0.025), c + (0.025, 0, -0.025)], 0.006)); face.append(CH([c + (-0.025, 0, -0.025), c + (0.025, 0, 0.025)], 0.006))
    mouth = [np.array((x, -0.162 + 0.01 * x * x * 30, 1.7 - 0.25 * x * x)) for x in np.linspace(-0.09, 0.09, 9)]
    face.append(CH(mouth, 0.0035, k=0.002))
    for p in mouth[::1]:
        face.append(CH([p + (0, 0, 0.018), p - (0, 0, 0.018)], 0.003))
    objs.append(mk(face, "Stitched_Face", 0.0014, M["ink"], 3000) if False else mk(S.union(*face), "Stitched_Face", 0.0014, M["ink"], 3000))
    objs.append(mk(S.noisy(S.torus((0, 0, 1.63), 0.08, 0.008), 0.001, 200, 1), "Neck_Twine", 0.0015, M["twine"], 1500))
    hat = S.revolve((0, 0, 0), [(0.33, 1.9), (0.335, 1.915), (0.15, 1.93), (0.135, 2.1), (0.06, 2.12), (0.001, 2.1)],
                    lambda th, z: 0.02 * np.sin(2 * th + 1) * np.clip((1.95 - z) * 30, 0, 1))
    hat = S.sub(S.noisy(hat, 0.006, 6, 2), S.box((0.0, 0.0, 2.11), (0.04, 0.3, 0.03), 0.01), k=0.02)
    objs.append(mk(hat, "Felt_Hat", 0.004, M["felt"], 6000))
    parent(objs, root)
    return {"name": "Scarecrow", "cat": "Ghouls", "desc": "Burlap-sack scarecrow in patched plaid flannel, straw bursting from cuffs and hem, stitched grin, slouch hat."}


@hq("ghost", 1024)
def ghost(M):
    fmats(M)
    root = PL.root_empty("ghost")
    form = S.union(S.sphere((0, 0, 1.45), 0.16), E((0, 0, 1.22), (0.24, 0.15, 0.1)),
                   *[CH([(0.18 * sx, -0.02, 1.2), (0.33 * sx, -0.18, 1.05), (0.4 * sx, -0.32, 0.98)], [0.06, 0.05, 0.035], k=0.03) for sx in (-1, 1)],
                   E((0, 0.0, 0.95), (0.2, 0.15, 0.25)), k=0.06)
    coll = mk(form, "_coll", 0.015, M["sheet"])
    sheet = H.grid_cloth("Ghost_Sheet", 2.4, 2.4, 80, 80, (0, 0, 1.68), (0, 0, 0.4))
    H.cloth_drape(sheet, [coll], frames=70, mass=0.2, tension=12, bending=0.05, quality=6, thickness=0.006, air=2.0)
    H.solidify(sheet, 0.004); H.subsurf(sheet, 1); H.decimate(sheet, 30000)
    H.set_mat(sheet, M["sheet"])
    sheet.data.transform(sheet.matrix_world); sheet.matrix_world = Matrix.Identity(4)
    bpy.context.view_layer.update()
    dg = bpy.context.evaluated_depsgraph_get()
    bvh = BVHTree.FromObject(sheet, dg)
    holes = MB()
    for (x, z, sx_, sz_) in ((-0.065, 1.48, 0.032, 0.05), (0.065, 1.48, 0.032, 0.05), (0.0, 1.33, 0.05, 0.035)):
        hit = bvh.ray_cast(V((x, -1.0, z)), V((0, 1, 0)))
        if hit[0] is not None:
            p, n = hit[0], hit[1]
            if n.y > 0:
                n = -n
            q = n.to_track_quat("-Y", "Z").to_euler()
            holes.sphere(tuple(p + n * 0.002), 1, (sx_, 0.012, sz_), tuple(q), segs=(16, 10))
    objs = [sheet, holes.obj("Ghost_Face", [M["socket"]])]
    remove([coll])
    for o in objs:
        o.matrix_world = Matrix.Translation((0, 0, 0.0)) @ o.matrix_world
    parent(objs, root)
    return {"name": "Floating ghost", "cat": "Ghouls", "behaviors": ["bob"],
            "desc": "Cloth-simulated bedsheet ghost draped over unseen outstretched arms; it hovers and sways."}
