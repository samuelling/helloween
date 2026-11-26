"""Batch C (part 1) — graveyard, spooky stuff and creatures, re-sculpted."""
import math, random
import numpy as np
import bpy, bmesh
from mathutils import Vector as V, Matrix, Euler
import props_lib as PL
import build_props as BP
from lib import MB, empty
import hq_lib as H
import sdf as S
import hq_animal as A
import hq_textures as TX
from hq_skull_sdf import cranium_sdf, mandible_sdf, teeth_sdf
from hq_props_bones import mk, mat4, parent, skull_objs, cervid
from hq_props_occult import candle_sdf, candles, mats as occ_mats, remove
from hq_registry import hq

E, C, B, CH = S.ellipsoid, S.cone, S.blade, S.chain


def gmats(M):
    occ_mats(M)
    M["slate"] = H.hq_mat("HQ_Slate", (0.08, 0.085, 0.09), (0.25, 0.26, 0.27), 0.8, 5, 0.9, 20, rough2=0.95)
    M["granite"] = H.hq_mat("HQ_Granite", (0.18, 0.17, 0.17), (0.42, 0.4, 0.38), 0.7, 40, 0.5, 60)
    M["cast_iron"] = H.hq_mat("HQ_Cast_Iron", (0.018, 0.017, 0.017), (0.09, 0.05, 0.03), 0.55, 8, 0.6, 40, metal=0.7, rough2=0.9)
    M["coffin_wood"] = H.hq_mat("HQ_Coffin_Wood", (0.04, 0.016, 0.008), (0.14, 0.06, 0.03), 0.35, 2.5, 0.2, 30, kind="wood", rough2=0.55)
    M["tufted"] = H.hq_mat("HQ_Tufted_Velvet", (0.12, 0.004, 0.012), (0.32, 0.02, 0.04), 0.85, 10, 0.3, 50)
    M["pumpkin_hq"] = H.hq_mat("HQ_Pumpkin_Skin", (0.42, 0.1, 0.008), (0.85, 0.36, 0.04), 0.45, 4, 0.35, 40, rough2=0.6)
    M["stem_hq"] = H.hq_mat("HQ_Stem", (0.1, 0.09, 0.04), (0.32, 0.28, 0.14), 0.8, 30, 0.8, 80, kind="weave")
    M["silk"] = H.hq_mat("HQ_Silk", (0.75, 0.75, 0.78), (0.95, 0.95, 0.97), 0.4, 20, 0.0, 30, emit=(0.6, 0.6, 0.7), emit_strength=0.25)
    M["feather"] = H.hq_mat("HQ_Feather", (0.006, 0.006, 0.008), (0.04, 0.04, 0.06), 0.35, 60, 0.6, 200, kind="weave", rough2=0.6)
    M["beak"] = H.hq_mat("HQ_Beak", (0.02, 0.02, 0.02), (0.08, 0.08, 0.08), 0.3, 10, 0.2, 40)
    M["gum_hq"] = H.hq_mat("HQ_Gum", (0.25, 0.015, 0.03), (0.55, 0.08, 0.12), 0.3, 8, 0.6, 40, sss=0.2, rough2=0.45)
    M["eye_white"] = H.hq_mat("HQ_Eye_White", (0.75, 0.66, 0.6), (0.92, 0.88, 0.84), 0.12, 12, 0.05, 40, sss=0.15)
    M["bat_skin"] = H.hq_mat("HQ_Bat_Skin", (0.03, 0.018, 0.016), (0.1, 0.06, 0.05), 0.55, 30, 0.5, 120, sss=0.1)
    M["moth_fuzz"] = H.hq_mat("HQ_Moth_Fuzz", (0.18, 0.13, 0.09), (0.42, 0.33, 0.24), 0.95, 60, 1.0, 200, kind="weave")
    M["rock"] = H.hq_mat("HQ_Fieldstone", (0.12, 0.115, 0.11), (0.38, 0.36, 0.33), 0.85, 6, 1.1, 20, rough2=0.95)
    return M


def led(M, pts, name, r=0.012):
    mb = MB()
    for i, p in enumerate(pts):
        mb.mi = 0 if i % 3 else 1
        mb.sphere(tuple(p), r, (1, 1, 1.3), segs=(10, 7))
    return mb.obj(name, [M["led_red"], M["lamp"]])


# ====================================================================== graveyard
@hq("coffin", 1024)
def coffin(M):
    gmats(M)
    root = PL.root_empty("coffin")
    poly = [(-0.25, 0), (0.25, 0), (0.39, 1.44), (0.3, 2.0), (-0.3, 2.0), (-0.39, 1.44)]
    inner = [(x * 0.86, 0.04 + z * 0.96) for x, z in poly]
    shell = S.sub(S.prism(poly, 0.0, 0.32, 0.012), S.prism(inner, -0.05, 0.27, 0.01), k=0.006)
    bands = S.union(*[S.prism([(x * 1.01, z) for x, z in poly], 0.03 + 0.12 * i, 0.05 + 0.12 * i, 0.004) for i in range(3)])
    shell = S.union(shell, S.sub(bands, S.prism(inner, -0.1, 0.4)), k=0.004)
    shell = S.noisy(shell, 0.0008, 40, 2, stretch=(1, 1, 0.1))
    objs = [mk(shell, "Coffin_Body", 0.0045, M["coffin_wood"], 9000)]
    lining = S.sub(S.prism([(x * 0.85, 0.045 + z * 0.955) for x, z in poly], 0.24, 0.3, 0.02),
                   *[S.sphere((x, 0.235, z), 0.02) for x in np.linspace(-0.24, 0.24, 5) for z in np.linspace(0.2, 1.8, 9)], k=0.03)
    objs.append(mk(S.noisy(lining, 0.002, 20, 2), "Coffin_Lining", 0.006, M["tufted"], 6000))
    handles = []
    for z in (0.6, 1.1, 1.5):
        for sx in (-1, 1):
            x = sx * (0.25 + (0.39 - 0.25) * z / 1.44 + 0.025)
            handles.append(S.union(C((x, 0.1, z), (x + sx * 0.03, 0.1, z), 0.008, 0.008), C((x, 0.22, z), (x + sx * 0.03, 0.22, z), 0.008, 0.008),
                                   C((x + sx * 0.035, 0.08, z), (x + sx * 0.035, 0.24, z), 0.011, 0.011), k=0.006))
    objs.append(mk(S.union(*handles), "Coffin_Handles", 0.002, M["gilt"], 3000))
    hinge = empty("Lid_Hinge", (0.4, -0.02, 0), None, 0.1)
    hinge.parent = root
    hinge.rotation_euler.z = math.radians(-35)
    lidpoly = [(x * 1.02, z * 1.01) for x, z in poly]
    lid = S.union(S.prism(lidpoly, -0.06, 0.0, 0.01), S.prism([(x * 0.9, 0.06 + z * 0.94) for x, z in poly], -0.075, -0.04, 0.008), k=0.004)
    cross = S.union(S.box((0, -0.08, 1.35), (0.06, 0.02, 0.7), 0.005), S.box((0, -0.08, 1.5), (0.35, 0.02, 0.06), 0.005), k=0.003)
    studs = S.union(*[S.sphere((x * 0.97, -0.065, z), 0.009) for x, z in [(p[0] + (q[0] - p[0]) * t, p[1] + (q[1] - p[1]) * t)
                                                                        for p, q in zip(lidpoly, lidpoly[1:] + lidpoly[:1]) for t in np.linspace(0, 1, 6)[:-1]]])
    lo = mk(S.noisy(lid, 0.0008, 40, 2, stretch=(1, 1, 0.1)), "Lid", 0.0045, M["coffin_wood"], 5000)
    lc = mk(S.union(cross, studs), "Lid_Cross", 0.002, M["gilt"], 3500)
    for o in (lo, lc):
        o.parent = hinge
        o.matrix_parent_inverse = Matrix.Identity(4)
        o.location = (-0.4, -0.04 + 0.06, 0)
    parent(objs, root)
    return {"name": "Upright coffin", "cat": "Graveyard", "behaviors": ["creak"],
            "desc": "Toe-pincher coffin in banded mahogany with a tufted crimson lining, brass handles and a studded lid that creaks open and shut."}


def headstone(M, pid, node, lines, name, desc, mat_c=((0.08, 0.085, 0.09), (0.3, 0.31, 0.32)), top=0.2):
    root = PL.root_empty(pid)
    ob = mk(S.noisy(S.noisy(node, 0.006, 5, 3, ridged=True), 0.0012, 40, 2), name, 0.004, M["slate"], 9000)
    if lines:
        H.planar_uv(ob, "Y")
        mask = TX.engraving(lines, pid + "_text", top=top)
        H.set_mat(ob, H.engraved_mat(pid + "_Stone", mask, *mat_c))
    moss = S.inter(S.noisy(S.offset(node, 0.002), 0.004, 8, 2), S.box((0, 0, 0.0), (2, 2, 0.35)))
    mo = mk(S.inter(moss, S.noisy(S.box((0, 0, 0.12), (2, 2, 0.24)), 0.08, 3, 2)), name + "_Moss", 0.006, M["moss"], 3000)
    parent([ob, mo], root)
    return {"name": desc[0], "cat": "Graveyard", "desc": desc[1]}


@hq("tombstone_rip", 1024)
def tombstone_rip(M):
    gmats(M)
    slab = S.union(S.box((0, 0, 0.42), (0.6, 0.12, 0.84), 0.01), S.prism([(0.3 * math.cos(a), 0.84 + 0.3 * math.sin(a)) for a in np.linspace(0, math.pi, 24)], -0.06, 0.06, 0.01),
                   S.box((0, 0, 0.04), (0.78, 0.26, 0.1), 0.015), k=0.004)
    slab = S.sub(slab, S.prism([(0.25 * math.cos(a), 0.83 + 0.25 * math.sin(a)) for a in np.linspace(0, math.pi, 20)] + [(-0.25, 0.2), (0.25, 0.2)], -0.08, -0.055, 0.004), k=0.003)
    slab = S.sub(slab, S.box((0.24, -0.06, 1.0), (0.12, 0.1, 0.14), 0.02, S.rotm(0, 0.6, 0)), k=0.01)   # chipped shoulder
    return headstone(M, "tombstone_rip", slab, [("R.I.P.", 210), ("HERE LIES\nA DECORATOR", 92), ("MDCCCLXXI — MCMXXVI", 62)],
                     "Headstone", ("R.I.P. headstone", "Weathered slate headstone with a recessed arch, carved lettering and moss at the foot."), top=0.27)


@hq("tombstone_cross", 1024)
def tombstone_cross(M):
    gmats(M)
    cross = S.union(S.box((0, 0, 0.62), (0.13, 0.13, 1.24), 0.012), S.box((0, 0, 0.92), (0.62, 0.13, 0.13), 0.012),
                    S.sub(S.torus((0, 0, 0.92), 0.2, 0.032, S.rotm(math.pi / 2, 0, 0)), S.box((0, 0, 0.92), (0.13, 0.4, 0.13))),
                    S.box((0, 0, 0.06), (0.42, 0.32, 0.12), 0.02), S.box((0, 0, 0.16), (0.24, 0.2, 0.08), 0.01), k=0.006)
    knots = S.union(*[S.sphere((0, -0.068, z), 0.012) for z in np.linspace(0.3, 1.15, 12)], *[S.sphere((x, -0.068, 0.92), 0.012) for x in np.linspace(-0.27, 0.27, 9)])
    cross = S.union(cross, knots, k=0.006)
    return headstone(M, "tombstone_cross", cross, None, "Grave_Cross",
                     ("Stone cross", "Weathered ringed grave cross with beaded carving and lichen creeping up the plinth."))


@hq("obelisk", 1024)
def obelisk(M):
    gmats(M)
    ob = S.union(S.box((0, 0, 0.12), (0.62, 0.62, 0.24), 0.015), S.box((0, 0, 0.34), (0.46, 0.46, 0.2), 0.012),
                 S.box((0, 0, 0.47), (0.38, 0.38, 0.06), 0.008), S.frustum(0.5, 1.95, 0.17, 0.12), S.frustum(1.95, 2.15, 0.125, 0.001), k=0.004)
    node = S.noisy(ob, 0.0015, 12, 2)
    root = PL.root_empty("obelisk")
    o = mk(S.noisy(node, 0.0006, 60, 2), "Obelisk", 0.006, M["granite"], 6000)
    H.planar_uv(o, "Y")
    mask = TX.engraving([("IN", 64), ("MEMORIAM", 64)], "obelisk_text", W=1024, H=2200, top=0.42, ornament=False)
    H.set_mat(o, H.engraved_mat("Obelisk_Stone", mask, (0.18, 0.17, 0.17), (0.45, 0.43, 0.4), kind="noise"))
    moss = mk(S.inter(S.noisy(S.offset(ob, 0.002), 0.005, 8, 2), S.noisy(S.box((0, 0, 0.1), (2, 2, 0.22)), 0.06, 3, 2)), "Obelisk_Moss", 0.006, M["moss"], 2500)
    parent([o, moss], root)
    return {"name": "Obelisk", "cat": "Graveyard", "desc": "2.2 m tapered granite obelisk on a stepped plinth, carved IN MEMORIAM."}


@hq("iron_fence", 1024)
def iron_fence(M):
    gmats(M)
    root = PL.root_empty("iron_fence")
    parts = []
    for i in range(14):
        x = -1.3 + i * 0.2
        parts.append(S.box((x, 0, 0.66), (0.018, 0.018, 1.26), 0.002))
        tip = S.union(C((x, 0, 1.28), (x, 0, 1.4), 0.024, 0.0015), S.sphere((x, 0, 1.27), 0.016),
                      *[CH([(x, 0, 1.3), (x + sx * 0.03, 0, 1.31), (x + sx * 0.035, 0, 1.35)], 0.0045) for sx in (-1, 1)], k=0.004)
        parts.append(tip)
    for z in (0.15, 1.1):
        parts.append(S.box((0, 0, z), (2.84, 0.022, 0.03), 0.003))
    for i in range(13):
        x = -1.2 + i * 0.2
        parts.append(S.sub(S.torus((x, 0, 1.0), 0.055, 0.006, S.rotm(math.pi / 2, 0, 0)), S.box((x, 0, 1.0), (0.02, 0.1, 0.2))))
        parts.append(CH([(x - 0.1, 0, 0.22), (x - 0.05, 0, 0.3), (x, 0, 0.24), (x + 0.05, 0, 0.3), (x + 0.1, 0, 0.22)], 0.005, k=0.003))
    rail = S.noisy(S.union(*parts, k=0.004), 0.0006, 50, 2)
    objs = [mk(rail, "Fence_Iron", 0.003, M["cast_iron"], 20000)]
    pil = []
    for x in (-1.5, 1.5):
        pil.append(S.union(S.box((x, 0, 0.75), (0.16, 0.16, 1.5), 0.01), S.box((x, 0, 1.53), (0.2, 0.2, 0.06), 0.008),
                           S.sphere((x, 0, 1.63), 0.085), S.box((x, 0, 0.05), (0.2, 0.2, 0.1), 0.01), k=0.004))
    objs.append(mk(S.noisy(S.noisy(S.union(*pil), 0.004, 6, 3, ridged=True), 0.001, 40, 2), "Fence_Pillars", 0.005, M["granite"], 6000))
    parent(objs, root)
    return {"name": "Iron fence (3 m)", "cat": "Graveyard", "desc": "Wrought-iron cemetery railing with spear finials and scrollwork between two granite pillars."}


# ====================================================================== spooky stuff
@hq("cauldron", 1024)
def cauldron(M):
    gmats(M)
    root = PL.root_empty("cauldron")
    rnd = random.Random(3)
    pot = S.revolve((0, 0, 0), [(0.18, 0.11), (0.33, 0.16), (0.44, 0.3), (0.465, 0.46), (0.44, 0.62), (0.37, 0.7), (0.38, 0.73), (0.41, 0.76), (0.4, 0.79)])
    pot = S.sub(pot, S.revolve((0, 0, 0), [(0.15, 0.16), (0.3, 0.2), (0.41, 0.33), (0.43, 0.46), (0.4, 0.62), (0.34, 0.72), (0.36, 0.9)]), k=0.01)
    feet = [S.union(C((0.32 * math.cos(a), 0.32 * math.sin(a), 0.2), (0.38 * math.cos(a), 0.38 * math.sin(a), 0.02), 0.045, 0.035),
                    E((0.39 * math.cos(a), 0.39 * math.sin(a), 0.02), (0.05, 0.05, 0.025)), k=0.02) for a in (0.3, 2.4, 4.5)]
    lugs = [S.torus((0.44 * sx, 0, 0.7), 0.04, 0.012, S.rotm(math.pi / 2, 0, 0)) for sx in (-1, 1)]
    bail = CH([(0.47 * math.cos(t), 0, 0.7 + 0.42 * math.sin(t)) for t in np.linspace(0, math.pi, 18)], 0.008)
    objs = [mk(S.noisy(S.noisy(S.union(pot, *feet, *lugs, k=0.02), 0.002, 15, 3, ridged=True), 0.0006, 70, 2), "Cauldron", 0.005, M["cast_iron"], 14000),
            mk(bail, "Cauldron_Bail", 0.002, M["cast_iron"], 1500)]
    brew = S.union(S.inter(S.revolve((0, 0, 0), [(0.42, 0.6), (0.42, 0.665)]), S.noisy(S.box((0, 0, 0.6), (1, 1, 0.13)), 0.01, 6, 2)),
                   *[S.sub(S.sphere((r * math.cos(a), r * math.sin(a), 0.665), rr), S.sphere((r * math.cos(a), r * math.sin(a), 0.665 + rr * 0.9), rr * 0.5))
                     for a, r, rr in [(rnd.uniform(0, 6.28), rnd.uniform(0.05, 0.3), rnd.uniform(0.02, 0.06)) for _ in range(12)]], k=0.01)
    objs.append(mk(brew, "Brew", 0.004, M["brew"], 4000))
    logs = []
    for a in (0.3, 1.8, 3.6):
        p = np.array((0.42 * math.cos(a), 0.42 * math.sin(a), 0.05)); q = -p * 0.55 + np.array((0, 0, 0.0))
        logs.append(S.noisy(C(p, q + np.array((0, 0, 0.03)), 0.055, 0.045), 0.006, 30, 2, ridged=True, stretch=(0.3, 0.3, 0.3)))
    objs.append(mk(S.union(*logs), "Fire_Logs", 0.005, M["bark"], 4000))
    fl = []
    for i in range(9):
        a, r = rnd.uniform(0, 6.28), rnd.uniform(0, 0.15)
        b = np.array((r * math.cos(a), r * math.sin(a), 0.06)); hgt = rnd.uniform(0.08, 0.16)
        fl.append(S.union(E(b + (0, 0, hgt * 0.3), (0.04, 0.04, hgt * 0.35)), C(b + (0, 0, hgt * 0.4), b + (0, 0, hgt), 0.035, 0.003), k=0.02))
    objs.append(mk(S.warp(S.union(*fl, k=0.03), 0.015, 9), "Fire_Flames", 0.006, M["fire"], 3000))
    parent(objs, root)
    return {"name": "Bubbling cauldron", "cat": "Spooky stuff", "behaviors": ["flicker"],
            "light": {"type": "point", "color": "#66ff33", "intensity": 5, "offset": [0, 1.0, 0]},
            "desc": "Pitted cast-iron cauldron on three feet, bail handle up, glowing green brew bubbling over a log fire."}


def pumpkin_node(r, z0, ribs=10, seed=0):
    ts = np.linspace(0.0, 1.0, 40)
    prof = [(r * (0.08 + 0.92 * math.sin(math.pi * t) ** 0.55) * (1 - 0.06 * t), z0 + r * 1.5 * t - (0.06 * r if t > 0.96 else 0)) for t in ts]
    mod = lambda th, z: -0.085 * r * (1 - np.abs(np.sin(ribs / 2 * th))) ** 2.5
    return S.revolve((0, 0, 0), prof, mod, lip=0.6, smooth=False)


def jack_face_cut(r, zc, style, seed=0):
    """Carved face cutters (prisms pushed through the front of the shell, facing -Y)."""
    s = r
    eye_up = style != "angry"
    def tri(cx, cz, w, h, up=True):
        pts = [(cx - w / 2, cz - h / 2), (cx + w / 2, cz - h / 2), (cx, cz + h / 2)] if up else [(cx - w / 2, cz + h / 2), (cx + w / 2, cz + h / 2), (cx, cz - h / 2)]
        return S.prism(pts, -r * 1.3, 0.0, 0.004)
    cuts = [tri(-0.38 * s, zc + 0.2 * s, 0.3 * s, 0.28 * s, eye_up), tri(0.38 * s, zc + 0.2 * s, 0.3 * s, 0.28 * s, eye_up), tri(0, zc, 0.15 * s, 0.13 * s)]
    mouth = [(-0.6 * s, zc - 0.22 * s)]
    n = 8
    for i in range(n + 1):
        x = -0.6 * s + 1.2 * s * i / n
        base = zc - 0.36 * s + 0.16 * s * (x / (0.6 * s)) ** 2
        mouth.append((x, base + (0.09 * s if i % 2 else 0)))
    upper = [(x, zc - 0.22 * s + 0.12 * s * (x / (0.6 * s)) ** 2 - (0.07 * s if i % 2 == 0 and 0 < i < n else 0)) for i, x in enumerate(np.linspace(0.6 * s, -0.6 * s, n + 1))]
    cuts.append(S.prism(mouth[1:] + upper, -r * 1.3, 0.0, 0.004))
    return cuts


def jack(M, name, r, z0, style, seed):
    shell_o = pumpkin_node(r, z0, seed=seed)
    shell = S.sub(shell_o, S.offset(shell_o, -0.03 * r / 0.3))
    zc = z0 + r * 0.85
    shell = S.sub(shell, *jack_face_cut(r, zc, style), k=0.003)
    shell = S.noisy(shell, 0.0015 * r / 0.3, 20 / r * 0.3, 2)
    glow = S.offset(shell_o, -0.035 * r / 0.3)
    stem = S.noisy(CH([(0, 0, z0 + r * 1.4), (0.01, 0.01, z0 + r * 1.6), (0.035, 0.02, z0 + r * 1.75)], [0.045 * r / 0.3, 0.035 * r / 0.3, 0.03 * r / 0.3], k=0.01),
                   0.004 * r / 0.3, 80, 2, ridged=True, stretch=(0.3, 0.3, 1))
    return (mk(shell, name + "_Shell", 0.004 * r / 0.3, M["pumpkin_hq"], 9000), mk(glow, name + "_Glow", 0.008 * r / 0.3, M["glow_orange"], 2000),
            mk(stem, name + "_Stem", 0.0025 * r / 0.3, M["stem_hq"], 1200))


@hq("jack_o_lantern", 1024)
def jack_o_lantern(M):
    gmats(M)
    root = PL.root_empty("jack_o_lantern")
    objs = list(jack(M, "Jack", 0.3, 0.0, "classic", 1))
    parent(objs, root)
    return {"name": "Jack-o'-lantern", "cat": "Spooky stuff", "behaviors": ["flicker"],
            "light": {"type": "point", "color": "#ff8a1e", "intensity": 2.5, "offset": [0, 0.45, 0]},
            "desc": "Deep-ribbed pumpkin with a cut-through toothy grin, glowing from inside, gnarled stem."}


@hq("pumpkin_totem", 1024)
def pumpkin_totem(M):
    gmats(M)
    root = PL.root_empty("pumpkin_totem")
    objs, z = [], 0
    for i, r in enumerate((0.34, 0.28, 0.23, 0.18)):
        sh, gl, st = jack(M, f"Totem{i}", r, z, "angry" if i % 2 else "classic", i)
        objs += [sh, gl] + ([st] if i == 3 else [])
        if i != 3:
            bpy.data.objects.remove(st)
        z += r * 1.42
    parent(objs, root)
    return {"name": "Pumpkin totem", "cat": "Spooky stuff", "behaviors": ["flicker"],
            "light": {"type": "point", "color": "#ff8a1e", "intensity": 3, "offset": [0, 0.9, 0.25]},
            "desc": "Four carved jack-o'-lanterns stacked into a 1.6 m totem, alternating grins and scowls."}


@hq("hanging_cage", 1024)
def hanging_cage(M):
    gmats(M)
    root = PL.root_empty("hanging_cage")
    post = S.union(S.noisy(C((0, 0.6, -0.1), (0, 0.6, 2.6), 0.035, 0.03), 0.002, 30, 2),
                   CH([(0, 0.6, 2.6), (0, 0.55, 2.75), (0, 0.38, 2.85), (0, 0.18, 2.78), (0, 0.1, 2.62)], [0.03, 0.03, 0.028, 0.026, 0.024], k=0.02),
                   S.sphere((0, 0.1, 2.6), 0.03), k=0.01)
    chain = S.union(*[S.torus((0, 0.1, 2.56 - 0.045 * i), 0.022, 0.0055, S.rotm(math.pi / 2, 0, (i % 2) * math.pi / 2)) for i in range(15)])
    bars = [C((0.22 * math.cos(a), 0.1 + 0.22 * math.sin(a), 1.15), (0.22 * math.cos(a), 0.1 + 0.22 * math.sin(a), 1.75), 0.008, 0.008) for a in np.linspace(0, 2 * math.pi, 13)[:-1]]
    bands = [S.box((0, 0.1, z), (0.47, 0.47, 0.03), 0.0) for z in ()] + [S.sub(S.revolve((0, 0.1, 0), [(0.232, z - 0.015), (0.232, z + 0.015)]), S.revolve((0, 0.1, 0), [(0.212, z - 0.03), (0.212, z + 0.03)])) for z in (1.15, 1.45, 1.75)]
    dome = S.sub(S.revolve((0, 0.1, 0), [(0.232, 1.75), (0.15, 1.85), (0.001, 1.9)]), S.revolve((0, 0.1, 0), [(0.21, 1.74), (0.13, 1.84), (0.001, 1.88)]))
    floor = S.revolve((0, 0.1, 0), [(0.232, 1.13), (0.232, 1.16)])
    rivets = [S.sphere((0.235 * math.cos(a), 0.1 + 0.235 * math.sin(a), z), 0.007) for a in np.linspace(0, 2 * math.pi, 13)[:-1] for z in (1.15, 1.45, 1.75)]
    ring = S.torus((0, 0.1, 1.93), 0.025, 0.006, S.rotm(math.pi / 2, 0, 0))
    cage = S.noisy(S.union(*bars, *bands, dome, floor, *rivets, ring, k=0.004), 0.0008, 50, 2)
    objs = [mk(post, "Hook_Post", 0.004, M["cast_iron"], 4000), mk(chain, "Chain", 0.0016, M["cast_iron"], 5000), mk(cage, "Gibbet_Cage", 0.003, M["cast_iron"], 14000)]
    sk = skull_objs(M, "Cage_Skull", 0.0016, jaw=True, targets=(5000, 1600, 1000), mat="bone_old")
    for o in sk:
        o.matrix_world = mat4((0.02, 0.06, 1.27), (0.15, 0, 0.3)) @ o.matrix_world
    objs += sk
    eyes = MB()
    for sx in (-1, 1):
        eyes.sphere((0.02 + 0.034 * sx * math.cos(0.3), 0.06 - 0.09, 1.25), 0.012, segs=(10, 7))
    objs.append(eyes.obj("Cage_Eyes", [M["eye_red"]]))
    parent(objs, root)
    return {"name": "Hanging cage", "cat": "Spooky stuff", "behaviors": ["swing"],
            "desc": "Riveted gibbet cage on a forged shepherd's hook and chain, a red-eyed skull rattling inside."}


@hq("candelabra", 1024)
def candelabra(M):
    gmats(M)
    root = PL.root_empty("candelabra")
    base = S.union(S.revolve((0, 0, 0), [(0.13, 0.04), (0.15, 0.06), (0.1, 0.1), (0.045, 0.14), (0.06, 0.18), (0.03, 0.24), (0.032, 0.6), (0.06, 0.64),
                                         (0.03, 0.68), (0.028, 1.1), (0.055, 1.15), (0.04, 1.22), (0.02, 1.27)]),
                   *[S.union(CH([(0.12 * math.cos(a), 0.12 * math.sin(a), 0.06), (0.2 * math.cos(a), 0.2 * math.sin(a), 0.03), (0.22 * math.cos(a), 0.22 * math.sin(a), 0.0)], [0.02, 0.016, 0.014], k=0.008),
                             S.sphere((0.22 * math.cos(a), 0.22 * math.sin(a), 0.012), 0.022), k=0.008) for a in (0.5, 2.6, 4.7)], k=0.01)
    arms, cups, specs = [], [], []
    for i, x in enumerate((-0.36, -0.18, 0.0, 0.18, 0.36)):
        z = 1.3 + (0.12 if x == 0 else 0.05 * (1 - abs(x) / 0.36))
        if x != 0:
            sx = 1 if x > 0 else -1
            arms.append(CH([(0, 0, 1.18), (x * 0.3, 0, 1.15), (x * 0.7, 0, 1.18), (x, 0, z - 0.06), (x, 0, z - 0.02)], [0.012, 0.011, 0.011, 0.012, 0.014], k=0.01))
            arms.append(CH([(x * 0.55, 0, 1.17), (x * 0.45, 0, 1.08), (x * 0.52, 0, 1.03), (x * 0.6, 0, 1.06)], 0.006, k=0.004))
        cups.append(S.sub(S.revolve((x, 0, 0), [(0.018, z - 0.06), (0.03, z - 0.03), (0.055, z - 0.01), (0.06, z)]), S.revolve((x, 0, 0), [(0.05, z - 0.004), (0.05, z + 0.02)])))
        specs.append((x, 0.0, z - 0.008, 0.18 + 0.06 * ((i * 7) % 3), 0.021, 3))
    objs = [mk(S.noisy(S.union(base, *arms, *cups, k=0.008), 0.0005, 60, 2), "Candelabra", 0.0025, M["gilt"], 12000)]
    for o in candles(M, specs, "Candelabra"):
        if o.name.endswith("_Wax"):
            H.set_mat(o, M["wax"])
        objs.append(o)
    parent(objs, root)
    return {"name": "Candelabra", "cat": "Spooky stuff", "behaviors": ["flicker"],
            "light": {"type": "point", "color": "#ffb04a", "intensity": 2.5, "offset": [0, 1.65, 0]},
            "desc": "Five-branch scrolled brass candelabra on clawed feet, ivory tapers running with wax."}


@hq("crystal_ball", 1024)
def crystal_ball(M):
    gmats(M)
    root = PL.root_empty("crystal_ball")
    stand = S.union(S.revolve((0, 0, 0), [(0.25, 0.0), (0.26, 0.03), (0.22, 0.06), (0.08, 0.14), (0.055, 0.2), (0.07, 0.3), (0.045, 0.45), (0.065, 0.62),
                                          (0.045, 0.8), (0.09, 0.88), (0.15, 0.95), (0.16, 0.99)]),
                    *[S.union(CH([(0.14 * math.cos(a), 0.14 * math.sin(a), 0.98), (0.15 * math.cos(a), 0.15 * math.sin(a), 1.06), (0.11 * math.cos(a), 0.11 * math.sin(a), 1.14),
                                   (0.085 * math.cos(a), 0.085 * math.sin(a), 1.13)], [0.016, 0.014, 0.01, 0.006], k=0.008)) for a in np.linspace(0, 2 * math.pi, 5)[:-1] + math.pi / 4], k=0.008)
    objs = [mk(S.noisy(stand, 0.0006, 60, 2), "Orb_Stand", 0.003, M["gilt"], 9000)]
    mb = MB(); mb.sphere((0, 0, 1.2), 0.17, segs=(48, 32))
    objs.append(mb.obj("Crystal_Orb", [M["crystal"]]))
    wisps = S.union(*[CH([(0.1 * math.cos(t + p), 0.1 * math.sin(t + p), 1.2 + 0.06 * math.sin(2 * t)) for t in np.linspace(0, 4, 12)], 0.008, k=0.006) for p in (0, 2.1, 4.2)])
    objs.append(mk(S.warp(wisps, 0.01, 12), "Orb_Wisps", 0.003, M["glow_purple"], 3000))
    parent(objs, root)
    return {"name": "Crystal ball", "cat": "Spooky stuff", "behaviors": ["pulse"],
            "light": {"type": "point", "color": "#9a40ff", "intensity": 2.5, "offset": [0, 1.2, 0]},
            "desc": "Violet orb held in brass claws on a turned pedestal, smoke-wisps coiling inside. It pulses."}


# ====================================================================== creatures
@hq("lawn_maw", 1024)
def lawn_maw(M):
    gmats(M)
    root = PL.root_empty("lawn_maw")
    rnd = random.Random(8)
    lip = S.noisy(S.noisy(S.torus((0, 0, 0.0), 1.0, 0.25), 0.03, 4, 3), 0.006, 25, 2, ridged=True)
    lip = S.inter(lip, S.box((0, 0, 0.2), (3, 3, 0.4)))
    throat = S.shell(S.revolve((0, 0, 0), [(0.001, -0.55), (0.5, -0.4), (0.85, -0.12), (0.95, 0.06)]), 0.03)
    gum = S.union(lip, S.noisy(S.inter(throat, S.box((0, 0, -0.25), (3, 3, 0.7))), 0.01, 8, 2, ridged=True), k=0.06)
    gum = S.inter(gum, S.revolve((0, 0, 0), [(1.3, -0.7), (1.3, 0.5)], smooth=False))
    objs = [mk(gum, "Maw_Gums", 0.012, M["gum_hq"], 16000)]
    teeth = []
    for ring, (R, n, h, tilt) in enumerate(((1.0, 18, 0.45, 0.35), (0.78, 14, 0.32, 0.55))):
        for i in range(n):
            a = 2 * math.pi * (i + 0.5 * ring) / n
            base = np.array((R * math.cos(a), R * math.sin(a), 0.06 - 0.1 * ring))
            inward = np.array((-math.cos(a), -math.sin(a), 0))
            hh = h * rnd.uniform(0.8, 1.15)
            mid = base + inward * hh * tilt * 0.4 + np.array((0, 0, hh * 0.6))
            tip = base + inward * hh * tilt + np.array((0, 0, hh))
            teeth.append(CH([base, mid, tip], [0.07, 0.045, 0.006], k=0.02))
    objs.append(mk(S.noisy(S.union(*teeth), 0.003, 30, 2, ridged=True, stretch=(0.5, 0.5, 2)), "Maw_Teeth", 0.006, M["tooth"], 12000))
    glow = S.revolve((0, 0, 0), [(0.001, -0.56), (0.4, -0.45), (0.6, -0.3)])
    objs.append(mk(glow, "Maw_Throat", 0.02, M["throat"], 1500))
    grass = []
    for i in range(160):
        a = rnd.uniform(0, 2 * math.pi); r = rnd.uniform(1.25, 1.5)
        b = np.array((r * math.cos(a), r * math.sin(a), 0.0))
        grass.append(C(b, b + np.array((rnd.uniform(-0.04, 0.04), rnd.uniform(-0.04, 0.04), rnd.uniform(0.06, 0.16))), 0.006, 0.0008))
    objs.append(mk(S.union(*grass), "Torn_Grass", 0.003, M["moss"], 5000))
    parent(objs, root)
    return {"name": "Lawn maw", "cat": "Creatures", "behaviors": ["pulse"],
            "light": {"type": "point", "color": "#ff2010", "intensity": 4, "offset": [0, 0.2, 0]},
            "desc": "Two rings of ridged, curved fangs set in wet gums where the lawn tore open, glowing from the throat."}


@hq("crow_post", 1024)
def crow_post(M):
    gmats(M)
    root = PL.root_empty("crow_post")
    post = S.noisy(S.noisy(S.box((0, 0, 0.58), (0.1, 0.1, 1.24), 0.006), 0.004, 4, 3, stretch=(1, 1, 0.06)), 0.0015, 40, 2, ridged=True, stretch=(1, 1, 0.1))
    objs = [mk(post, "Crow_Post", 0.004, M["timber"], 4000)]
    body = S.union(E((0, 0.06, 1.33), (0.08, 0.15, 0.09), S.rotm(0.25, 0, 0)), E((0, -0.04, 1.39), (0.065, 0.07, 0.07)),
                   *[B([(sx * 0.07, -0.02, 1.38), (sx * 0.085, 0.12, 1.34), (sx * 0.05, 0.27, 1.3)], 0.012, [0.05, 0.05, 0.02], nrm=(1, 0, 0)) for sx in (-1, 1)],
                   B([(0, 0.2, 1.31), (0, 0.38, 1.27)], [0.04, 0.06], 0.008, nrm=(0, 0, 1)), k=0.03)
    body = S.noisy(body, 0.003, 60, 2, ridged=True, stretch=(1, 0.3, 1))
    feet = S.union(*[S.union(CH([(sx * 0.03, 0.04, 1.26), (sx * 0.03, 0.03, 1.215)], 0.006),
                             *[CH([(sx * 0.03, 0.03, 1.212), (sx * 0.03 + dx, -0.04, 1.205), (sx * 0.03 + dx, -0.055, 1.19)], 0.0035, k=0.002) for dx in (-0.015, 0, 0.015)],
                             CH([(sx * 0.03, 0.03, 1.212), (sx * 0.03, 0.07, 1.205)], 0.0035), k=0.003) for sx in (-1, 1)])
    objs.append(mk(body, "Crow_Body", 0.003, M["feather"], 9000))
    objs.append(mk(feet, "Crow_Feet", 0.0012, M["beak"], 2000))
    head = empty("Head", (0, -0.06, 1.47), None, 0.05)
    head.parent = root
    hn = S.union(S.sphere((0, 0, 0), 0.055), C((0, -0.035, -0.005), (0, -0.14, -0.025), 0.022, 0.002), k=0.012)
    hn = S.noisy(hn, 0.0015, 90, 2, ridged=True, stretch=(1, 0.3, 1))
    ho = mk(hn, "Crow_Head", 0.0018, M["feather"], 4000)
    bk = mk(S.union(C((0, -0.04, -0.005), (0, -0.145, -0.026), 0.02, 0.0018), k=0), "Crow_Beak", 0.0012, M["beak"], 1200)
    ey = MB()
    for sx in (-1, 1):
        ey.sphere((0.034 * sx, -0.03, 0.014), 0.011, segs=(10, 7))
    eo = ey.obj("Crow_Eyes", [M["eye_red"]])
    for o in (ho, bk, eo):
        o.parent = head
    parent(objs, root)
    return {"name": "Crow on a post", "cat": "Creatures", "behaviors": ["peck"],
            "desc": "Glossy feathered crow gripping a split post, red-eyed, jerking its head around."}


@hq("eyeball_tree", 1024)
def eyeball_tree(M):
    gmats(M)
    root = PL.root_empty("eyeball_tree")
    rnd = random.Random(13)
    limbs, tips = [], []
    def branch(p, d, L, r, depth):
        pts, rads, q = [p.copy()], [r], p.copy()
        for i in range(5):
            d = d + np.array((rnd.uniform(-0.35, 0.35), rnd.uniform(-0.35, 0.35), rnd.uniform(-0.1, 0.25)))
            d = d / np.linalg.norm(d)
            q = q + d * (L / 5)
            pts.append(q.copy()); rads.append(max(r * (1 - 0.1 * (i + 1)), 0.022))
        limbs.append(CH(pts, rads, k=r * 0.5))
        if depth > 0:
            for _ in range(rnd.choice((2, 3))):
                nd = d + np.array((rnd.uniform(-1, 1), rnd.uniform(-1, 1), rnd.uniform(0, 0.6)))
                branch(q, nd / np.linalg.norm(nd), L * 0.65, r * 0.5, depth - 1)
        else:
            tips.append((q, d))
    branch(np.array((0.0, 0.0, -0.1)), np.array((0.0, 0.0, 1.0)), 1.9, 0.22, 3)
    for a in np.linspace(0, 2 * math.pi, 6)[:-1]:   # roots
        limbs.append(CH([(0.05 * math.cos(a), 0.05 * math.sin(a), 0.3), (0.3 * math.cos(a + 0.3), 0.3 * math.sin(a + 0.3), 0.04), (0.55 * math.cos(a + 0.5), 0.55 * math.sin(a + 0.5), -0.03)],
                        [0.12, 0.06, 0.02], k=0.05))
    tree = S.noisy(S.noisy(S.union(*limbs, k=0.03), 0.012, 6, 3, ridged=True, stretch=(1, 1, 0.3)), 0.003, 40, 2)
    objs = [mk(tree, "Eyeball_Tree_Bark", 0.009, M["bark"], 20000)]
    # one eyeball mesh, instanced: pupil looks along local +Y
    eb = S.union(S.sphere((0, 0, 0), 0.1), S.sphere((0, 0.055, 0), 0.06), k=0.01)
    ew = mk(eb, "Eyeball_Master", 0.003, M["eye_white"], 2500)
    ir = MB(); ir.mi = 0; ir.sphere((0, 0.082, 0), 0.042, (1, 0.3, 1), segs=(20, 8)); ir.mi = 1; ir.sphere((0, 0.094, 0), 0.018, (1, 0.25, 1), segs=(14, 6))
    iro = ir.obj("Iris_Master", [M["iris"], M["socket"]])
    veins = S.union(*[CH([(0.1 * math.cos(a) * math.sin(b), 0.1 * math.cos(b) * -1, 0.1 * math.sin(a) * math.sin(b)) for b in np.linspace(0.6, 1.6, 5)], 0.0025)
                      for a in np.linspace(0, 2 * math.pi, 9)[:-1]])
    vo = mk(S.inter(S.offset(veins, 0), S.sphere((0, 0, 0), 0.102)), "Veins_Master", 0.0012, M["gum_hq"], 1500)
    eye_master = H.join([ew, iro, vo], "Eye_Master")
    for i, (q, d) in enumerate(tips[:16]):
        r = rnd.uniform(0.8, 1.3)
        e = H.instance(eye_master, f"Eye_{i:02d}", mat4(tuple(q + d * 0.1 * r), (0, 0, rnd.uniform(0, 6.28)), r))
        objs.append(e)
    bpy.data.objects.remove(eye_master)
    parent(objs, root)
    return {"name": "Eyeball tree", "cat": "Creatures", "behaviors": ["eyes_follow"],
            "desc": "Gnarled dead tree with 16 bloodshot eyeballs on its branch tips that turn to watch you."}


@hq("spider_web", 1024)
def spider_web(M):
    gmats(M)
    root = PL.root_empty("spider_web")
    rnd = random.Random(6)
    stakes = S.union(*[S.noisy(C((x, 0, -0.1), (x * 0.98, 0, 2.45), 0.035, 0.025), 0.004, 8, 2, ridged=True, stretch=(1, 1, 0.1)) for x in (-1.3, 1.3)])
    objs = [mk(stakes, "Web_Stakes", 0.004, M["timber"], 3000)]
    mb = MB()
    c = V((0, 0, 1.35))
    spokes = 18
    ends = []
    for i in range(spokes):
        a = 2 * math.pi * i / spokes + rnd.uniform(-0.05, 0.05)
        L = (1.25 if abs(math.cos(a)) > 0.5 else 1.0) * rnd.uniform(0.92, 1.0)
        e = c + V((math.cos(a) * L, rnd.uniform(-0.01, 0.01), math.sin(a) * L))
        ends.append((a, L))
        mb.cyl(c, e, 0.0035, segs=4)
    # anchor lines to the stakes and ground
    for (a, L) in ends:
        e = c + V((math.cos(a) * L, 0, math.sin(a) * L))
        tgt = V((math.copysign(1.3, math.cos(a)), 0, min(2.4, max(0.05, e.z + math.sin(a) * 0.2)))) if abs(math.cos(a)) > 0.4 else V((e.x * 1.1, 0, 0.0 if math.sin(a) < 0 else 2.45))
        mb.cyl(e, tgt, 0.003, segs=4)
    # capture spiral
    t = 0.0
    prev = None
    while True:
        r = 0.09 + 0.0115 * t * spokes / (2 * math.pi) * 0.9
        a = t
        k = int((a % (2 * math.pi)) / (2 * math.pi) * spokes)
        Lmax = ends[k][1] * 0.95
        if r > Lmax and r > 1.15:
            break
        p = c + V((math.cos(a) * min(r, Lmax), 0, math.sin(a) * min(r, Lmax) - 0.008 * math.sin(a * spokes)))
        if prev is not None:
            mb.cyl(prev, p, 0.0022, segs=3)
            if rnd.random() < 0.12:
                mb.sphere(tuple(p + V((0, 0, -0.006))), 0.006, (1, 1, 1.3), segs=(6, 4))   # dew drop
        prev = p
        t += 2 * math.pi / spokes / 2
    mb.sphere(tuple(c), 0.03, (1, 0.3, 1), segs=(10, 6))
    objs.append(mb.obj("Spider_Web", [M["silk"]]))
    parent(objs, root)
    return {"name": "Giant web", "cat": "Creatures", "desc": "2.6 m orb web with a true capture spiral and dew drops, guyed between two split stakes."}


@hq("bat_swarm", 512)
def bat_swarm(M):
    gmats(M)
    root = PL.root_empty("bat_swarm")
    rnd = random.Random(3)
    body = S.union(E((0, 0, 0), (0.035, 0.06, 0.035)), S.sphere((0, -0.065, 0.012), 0.028),
                   C((0, -0.08, 0.012), (0, -0.098, 0.006), 0.016, 0.009),
                   *[C((sx * 0.014, -0.07, 0.03), (sx * 0.028, -0.06, 0.075), 0.012, 0.002) for sx in (-1, 1)],
                   *[C((sx * 0.01, -0.094, 0.002), (sx * 0.01, -0.096, -0.012), 0.0025, 0.0004) for sx in (-1, 1)], k=0.01)
    bo = mk(S.noisy(body, 0.0015, 120, 2), "Bat_Body_Master", 0.0012, M["bat_skin"], 3500)
    eyes = MB()
    for sx in (-1, 1):
        eyes.sphere((sx * 0.013, -0.088, 0.022), 0.006, segs=(8, 6))
    eo = eyes.obj("Bat_Eyes_Master", [M["eye_red"]])
    body_master = H.join([bo, eo], "Bat_Body_Master")
    def wing(sx):
        sh = np.array((0.0, -0.03, 0.01))
        wrist = np.array((sx * 0.14, -0.06, 0.04))
        fingers = [np.array((sx * 0.31, -0.02, 0.02)), np.array((sx * 0.27, 0.06, 0.0)), np.array((sx * 0.19, 0.08, 0.0)), np.array((sx * 0.1, 0.07, 0.0))]
        bones = [CH([sh, wrist], [0.006, 0.004])] + [CH([wrist, f], [0.0028, 0.0012]) for f in fingers]
        pts = [(0.0, -0.04), (wrist[0], wrist[1] - 0.005)] + [(f[0], f[1]) for f in fingers] + [(0.0, 0.06)]
        poly = []
        for (x0, y0), (x1, y1) in zip(pts, pts[1:]):
            for t in np.linspace(0, 1, 6)[:-1]:
                x, y = x0 + (x1 - x0) * t, y0 + (y1 - y0) * t
                sag = math.sin(t * math.pi) * 0.025 if (x0, y0) != (0.0, -0.04) else 0
                poly.append((x, y + sag))
        poly.append(pts[-1])
        mem = S.xform(S.prism([(p[0], p[1]) for p in (poly if sx > 0 else poly[::-1])], -0.0016, 0.0016, 0.0), np.array([[1, 0, 0, 0], [0, 0, 1, 0], [0, -1, 0, 0], [0, 0, 0, 1]], float))
        return S.union(mem, *bones, k=0.002)
    wings = {s: mk(S.noisy(wing(sx), 0.0008, 60, 1), f"Wing_{s}_Master", 0.0014, M["bat_skin"], 2500) for s, sx in (("L", 1), ("R", -1))}
    for i in range(7):
        b = empty(f"Bat_{i}", (rnd.uniform(-1, 1), rnd.uniform(-1, 1), 2.0 + rnd.uniform(-0.4, 0.6)), None, 0.05)
        b.parent = root
        b.rotation_euler.z = rnd.uniform(0, 6.28)
        b.scale = (1.8, 1.8, 1.8)
        bod = H.instance(body_master, f"Bat_{i}_Body", Matrix.Identity(4)); bod.parent = b
        for s, sx in (("L", 1), ("R", -1)):
            wg = empty(f"Wing_{s}_{i}", (0.03 * sx, 0, 0.01), None, 0.02)
            wg.parent = b
            wm = H.instance(wings[s], f"Wing_{s}_{i}_Membrane", Matrix.Identity(4)); wm.parent = wg
            wm.location = (-0.03 * sx, 0, -0.01)
    remove([body_master] + list(wings.values()))
    return {"name": "Bat swarm", "cat": "Creatures", "behaviors": ["flap", "orbit"],
            "desc": "Seven furred, red-eyed bats with finger-boned membrane wings, circling overhead."}


@hq("giant_moth", 1024)
def giant_moth(M):
    gmats(M)
    root = PL.root_empty("giant_moth")
    post = S.noisy(C((0, 0.25, -0.1), (0, 0.25, 1.32), 0.022, 0.016), 0.003, 10, 2, ridged=True, stretch=(1, 1, 0.1))
    objs = [mk(post, "Moth_Perch", 0.003, M["bark"], 2000)]
    body = S.union(E((0, 0.15, 1.42), (0.055, 0.06, 0.16)), E((0, 0.16, 1.62), (0.06, 0.055, 0.06)), S.sphere((0, 0.13, 1.69), 0.042),
                   *[CH([(sx * 0.02, 0.11, 1.71), (sx * 0.08, 0.06, 1.8), (sx * 0.15, 0.04, 1.86)], [0.004, 0.003, 0.002], k=0.002) for sx in (-1, 1)],
                   *[CH([(sx * 0.04, 0.12 + dy, 1.58), (sx * 0.1, 0.1 + dy, 1.52), (sx * 0.12, 0.12 + dy, 1.42)], 0.005, k=0.003) for sx in (-1, 1) for dy in (-0.03, 0.0, 0.03)], k=0.015)
    for i in range(7):
        body = S.sub(body, S.torus((0, 0.15, 1.3 + 0.035 * i), 0.055 - 0.003 * abs(i - 3), 0.004), k=0.004)
    feathers = []
    for sx in (-1, 1):
        for t in np.linspace(0.15, 0.95, 9):
            p = np.array((sx * (0.02 + 0.13 * t), 0.11 - 0.07 * t, 1.71 + 0.15 * t))
            feathers.append(C(p, p + np.array((0, 0.02, 0.02)), 0.002, 0.0008)); feathers.append(C(p, p + np.array((0, -0.02, 0.02)), 0.002, 0.0008))
    objs.append(mk(S.noisy(S.union(body, *feathers, k=0.004), 0.004, 80, 2, ridged=True), "Moth_Body", 0.0022, M["moth_fuzz"], 12000))
    ey = MB()
    for sx in (-1, 1):
        ey.sphere((sx * 0.03, 0.11, 1.7), 0.018, segs=(12, 8))
    objs.append(ey.obj("Moth_Eyes", [M["socket"]]))
    cp, ep = TX.wing_pattern()
    wmat = H.image_mat("Moth_Wing_Art", cp, 0.85, ep, (1.0, 0.1, 0.03), 5.0)
    for s, sx in (("L", 1), ("R", -1)):
        wing = empty(f"Wing_{s}", (0.04 * sx, 0.15, 1.5), None, 0.05)
        wing.parent = root
        outline = [(0, 0.12), (0.18, 0.28), (0.4, 0.34), (0.6, 0.24), (0.64, 0.1), (0.55, -0.04), (0.35, -0.08), (0.42, -0.2), (0.38, -0.36), (0.22, -0.44), (0.06, -0.3), (0, -0.05)]
        bm = bmesh.new()
        uvl = bm.loops.layers.uv.new("SrcUV")
        vs = [bm.verts.new((sx * x, 0.0, z)) for x, z in outline]
        f = bm.faces.new(vs if sx < 0 else vs[::-1])
        bmesh.ops.triangulate(bm, faces=[f])
        bmesh.ops.subdivide_edges(bm, edges=bm.edges[:], cuts=3, use_grid_fill=True)
        for v in bm.verts:
            v.co.y += 0.015 * math.sin(v.co.x * 9) * abs(v.co.x) + 0.01 * v.co.x * v.co.x * 10
        for fa in bm.faces:
            for l in fa.loops:
                l[uvl].uv = (abs(l.vert.co.x) / 0.66, (l.vert.co.z + 0.45) / 0.8)
        me = bpy.data.meshes.new(f"Wing_{s}_Membrane"); bm.to_mesh(me); bm.free()
        wo = bpy.data.objects.new(f"Wing_{s}_Membrane", me); bpy.context.scene.collection.objects.link(wo)
        H.solidify(wo, 0.003); H.subsurf(wo, 1)
        H.set_mat(wo, wmat)
        wo.parent = wing
        wo.location = (0, 0, 0)
    parent(objs, root)
    return {"name": "Giant moth", "cat": "Creatures", "behaviors": ["flutter"],
            "desc": "1.3 m fuzzy moth with feathered antennae and painted wings whose red eyespots glow, slowly fanning."}


@hq("stone_cairn", 1024)
def stone_cairn(M):
    gmats(M)
    root = PL.root_empty("stone_cairn")
    rnd = random.Random(31)
    variants = []
    for vi in range(5):
        rock = S.box((0, 0, 0), (0.62, 0.48, 0.22), 0.07)
        rock = S.noisy(S.noisy(S.warp(rock, 0.07, 1.6 + 0.3 * vi), 0.015, 5, 3, ridged=True), 0.003, 30, 2)
        variants.append(mk(rock, f"Rock_{vi}", 0.008, M["rock"], 1400))
    layers = [(1.05, 0.0, 15), (0.85, 0.12, 13), (0.65, 0.24, 10), (0.45, 0.36, 7), (0.25, 0.47, 4), (0.0, 0.56, 1)]
    objs, i = [], 0
    for R, z, n in layers:
        for j in range(n):
            a = 2 * math.pi * j / n + rnd.uniform(-0.15, 0.15) + z * 3
            rr = R * rnd.uniform(0.85, 1.05)
            tilt = 0.32 if R > 0.3 else 0.12
            rot = (rnd.uniform(-0.2, 0.2) - tilt * math.sin(a), tilt * math.cos(a) + rnd.uniform(-0.2, 0.2), a + rnd.uniform(-0.6, 0.6))
            sc = rnd.uniform(0.8, 1.15)
            Mx = mat4((rr * math.cos(a), rr * math.sin(a), z + 0.05), rot) @ Matrix.Diagonal((sc * rnd.uniform(0.9, 1.25) * 0.68, sc * 0.68, sc * rnd.uniform(0.9, 1.5) * 0.6, 1))
            objs.append(H.instance(variants[i % 5], f"Cairn_Stone_{i:02d}", Mx)); i += 1
    remove(variants)
    sk = cervid(M, "Cairn_Elk", "elk", 1.69, 1.25, 1.69)
    for o in sk:
        o.matrix_world = mat4((0, -0.05, 0.74), (math.radians(18), 0, 0.3)) @ o.matrix_world
    objs += sk
    pts = []
    for j in range(60):
        a = rnd.uniform(0, 2 * math.pi); r = rnd.uniform(0.15, 1.3)
        pts.append((r * math.cos(a), r * math.sin(a), max(0.03, 0.6 * (1 - r / 1.25)) + 0.07))
    objs.append(led(M, pts, "Cairn_String_Lights"))
    parent(objs, root)
    return {"name": "Stone cairn + elk skull", "cat": "2026 display",
            "desc": "Fieldstone cairn of 50 weathered slabs, threaded with red and warm string lights, crowned with an elk skull."}
