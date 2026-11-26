"""Batch B — the occult set, re-sculpted: robed figures with SDF cloth folds, cloth-simulated drapes,
painted boards/banners, dripping candles. Sigils are invented glyphs."""
import math, random
import numpy as np
import bpy
from mathutils import Vector as V, Matrix, Euler
import props_lib as PL
import props_occult as PO
import build_props as BP
import hq_lib as H
import sdf as S
import hq_animal as A
import hq_textures as TX
from hq_skull_sdf import cranium_sdf, mandible_sdf
from hq_props_bones import mk, mat4, parent, long_bone
from hq_registry import hq

E, C, B, CH = S.ellipsoid, S.cone, S.blade, S.chain
CAT = "Occult"


def mats(M):
    PO.occult_mats(M)
    H.library(M)          # HQ cloth/metal/glass materials take precedence over the flat originals
    M["wax_black"] = H.hq_mat("HQ_Wax_Black", (0.012, 0.011, 0.013), (0.05, 0.045, 0.05), 0.28, 10, 0.15, 30, rough2=0.5)
    M["stone_altar"] = H.hq_mat("HQ_Altar_Stone", (0.03, 0.03, 0.032), (0.12, 0.115, 0.11), 0.75, 5, 1.0, 25, rough2=0.95)
    M["char"] = H.hq_mat("HQ_Char", (0.01, 0.009, 0.008), (0.05, 0.045, 0.04), 0.95, 8, 0.6, 30)
    M["walnut"] = H.hq_mat("HQ_Walnut", (0.05, 0.022, 0.012), (0.16, 0.08, 0.04), 0.4, 3, 0.25, 30, kind="wood", rough2=0.6)
    M["timber"] = H.hq_mat("HQ_Timber", (0.07, 0.045, 0.03), (0.22, 0.15, 0.09), 0.8, 2, 0.8, 18, kind="wood", grain_dir="Z")
    M["twine"] = H.hq_mat("HQ_Twine", (0.3, 0.22, 0.12), (0.5, 0.4, 0.25), 0.9, 200, 0.4, 300, kind="weave")
    M["fur"] = H.hq_mat("HQ_Goat_Fur", (0.012, 0.01, 0.01), (0.06, 0.05, 0.045), 0.9, 40, 1.2, 140)
    M["horn_ram"] = H.hq_mat("HQ_Ram_Horn", (0.12, 0.1, 0.08), (0.42, 0.36, 0.28), 0.5, 6, 0.6, 40, rough2=0.8)
    M["gilt"] = H.hq_mat("HQ_Gilt", (0.3, 0.19, 0.05), (0.7, 0.5, 0.18), 0.25, 8, 0.25, 50, metal=1.0, rough2=0.55)
    return M


# ------------------------------------------------------------------ shared sculpts
def hand_sdf(wrist, fwd, palm, k=1.0, curl=0.3, spread=0.12, skinny=1.0):
    """Long-fingered hand from the wrist along fwd, palm facing `palm`."""
    w, f, p = np.array(wrist, float), np.array(fwd, float), np.array(palm, float)
    f /= np.linalg.norm(f); p = p - f * (p @ f); p /= np.linalg.norm(p)
    side = np.cross(f, p)
    parts = [E(w + f * 0.045 * k, (0.034 * k, 0.014 * k, 0.045 * k), S.frame(w, w + f, side))]
    for i, L in enumerate((0.95, 1.05, 1.0, 0.82)):
        o = (i - 1.5) * 0.017 * k
        base = w + f * 0.085 * k + side * o
        d = f + side * (i - 1.5) * spread
        pts, q = [base], base
        for seg, sl in enumerate((0.045, 0.03, 0.024)):
            d = d * math.cos(curl) + p * math.sin(curl) * (0.6 + 0.3 * seg)
            d = d / np.linalg.norm(d)
            q = q + d * sl * L * k
            pts.append(q)
        parts.append(CH(pts, [0.0075 * k * skinny, 0.0065 * k * skinny, 0.0055 * k * skinny, 0.0042 * k * skinny], k=0.003 * k))
    th = [w + f * 0.03 * k - side * 0.025 * k, w + f * 0.06 * k - side * 0.05 * k + p * 0.015 * k, w + f * 0.09 * k - side * 0.06 * k + p * 0.025 * k]
    parts.append(CH(th, [0.009 * k, 0.0075 * k, 0.006 * k], k=0.004 * k))
    return S.union(*parts, k=0.008 * k)


def hood_local(k=1.0):
    outer = S.union(E((0, 0.02, 0.0), (0.135 * k, 0.16 * k, 0.175 * k)),
                    C((0, 0.07 * k, 0.09 * k), (0, 0.19 * k, 0.17 * k), 0.07 * k, 0.012 * k),
                    E((0, 0.05 * k, -0.15 * k), (0.2 * k, 0.17 * k, 0.08 * k)), k=0.06 * k)
    hood = S.sub(outer, E((0, -0.13 * k, -0.01 * k), (0.088 * k, 0.13 * k, 0.125 * k)), k=0.02 * k)
    hood = S.noisy(hood, 0.006 * k, 9 / k, 2, stretch=(1, 0.5, 2.5))
    void = E((0, -0.035 * k, -0.01 * k), (0.078 * k, 0.05 * k, 0.11 * k))
    return hood, void


def sleeve(s0, el, wr, r0, r1, r2, k=1.0):
    """Robe sleeve: shoulder->elbow->wrist, belling out with an open cuff and a hanging drape."""
    s0, el, wr = map(np.array, (s0, el, wr))
    d = (wr - el) / np.linalg.norm(wr - el)
    sl = S.union(C(s0, el, r0, r1), C(el, wr, r1, r2), k=0.03 * k)
    drape = E(el + (wr - el) * 0.55 + np.array((0, 0, -r2 * 0.7)), (r2 * 0.75, r2 * 0.75, np.linalg.norm(wr - el) * 0.45),
              S.frame(el, wr, (0, 0, 1)))
    sl = S.union(sl, drape, k=0.04 * k)
    sl = S.sub(sl, S.sphere(wr + d * r2 * 0.4, r2 * 0.85), k=0.01 * k)
    return S.noisy(sl, 0.006 * k, 10 / k, 2, stretch=(0.7, 0.7, 2))


POSES = {
    # shoulder offsets are relative to the chest centre; elbow/wrist are absolute for the standing figure
    "clasped": {"el": (0.23, -0.07, 1.14), "wr": (0.075, -0.2, 1.03), "fwd": (-1, -0.35, -0.15), "palm": (-1, 0, 0)},
    "raised": {"el": (0.34, -0.06, 1.62), "wr": (0.4, -0.1, 1.9), "fwd": (0.1, -0.1, 1), "palm": (0, -1, 0)},
    "out": {"el": (0.42, -0.18, 0.77), "wr": (0.62, -0.25, 0.64), "fwd": (0.8, -0.3, -0.3), "palm": (0, 0, -1)},
}


def robed_figure(M, robe_key, pose="clasped", kneel=False, head=True, h=1.78, seed=0):
    """Returns objects: robe (cloth), void (black face/neck) and hands."""
    k = h / 1.78
    if kneel:
        hip, chest, hc_ = np.array((0, 0.1, 0.42)), np.array((0, -0.12, 0.9)), np.array((0, -0.25, 1.06))
        skirt = S.revolve((0, 0.05, 0), [(0.47, 0.0), (0.45, 0.06), (0.38, 0.2), (0.26, 0.42), (0.2, 0.5)],
                          S.folds(11, 0.035, 0.0, 0.5, seed), sy=1.15)
        torso = S.union(C(hip, chest, 0.21, 0.2), E(chest + (0, 0.02, 0.0), (0.24, 0.15, 0.09)), k=0.08)
        up, fwd = (0, -0.45, 1), (0, -1, -0.5)
    else:
        chest, hc_ = np.array((0, 0.0, 1.4 * k)), np.array((0, -0.02 * k, 1.66 * k))
        skirt = S.revolve((0, 0, 0), [(0.39 * k, 0.0), (0.37 * k, 0.1 * k), (0.3 * k, 0.5 * k), (0.23 * k, 0.95 * k), (0.205 * k, 1.25 * k),
                                      (0.2 * k, 1.38 * k)], S.folds(10, 0.03 * k, 0.0, 1.15 * k, seed), sy=0.82)
        torso = E(chest, (0.23 * k, 0.13 * k, 0.09 * k))
        up, fwd = (0, 0.05, 1), (0, -1, 0)
    robe = S.union(skirt, torso, k=0.08 * k)
    sh = chest + np.array((0, 0, 0.02 * k))
    hands = []
    P = POSES[pose]
    for sx in (-1, 1):
        s0 = sh + np.array((sx * 0.19 * k, 0, 0))
        el, wr = np.array(P["el"]) * (sx, 1, 1), np.array(P["wr"]) * (sx, 1, 1)
        if kneel:
            el = el + (0, -0.08, 0) if pose != "out" else el
            wr = wr + (0, -0.1, 0) if pose != "out" else wr
            if pose == "clasped":
                el, wr = s0 + (sx * 0.05, -0.18, -0.25), np.array((sx * 0.06, -0.38, 0.72))
        else:
            el, wr = el * (1, 1, k), wr * (1, 1, k)
        if pose == "raised":   # sleeves slide back to the elbow, bare forearms raised
            cuff = el + (wr - el) * 0.35
            robe = S.union(robe, sleeve(s0, el, cuff, 0.07 * k, 0.085 * k, 0.12 * k, k), k=0.04 * k)
            hands.append(C(cuff - (cuff - el) * 0.3, wr, 0.03 * k, 0.022 * k))
        else:
            robe = S.union(robe, sleeve(s0, el, wr, 0.07 * k, 0.085 * k, 0.12 * k, k), k=0.04 * k)
        fw = np.array(P["fwd"]) * (sx, 1, 1)
        if pose == "clasped" and kneel:
            fw = np.array((-sx * 0.6, -0.6, 0.4))
        hands.append(hand_sdf(wr - (wr - el) / np.linalg.norm(wr - el) * 0.05 * k, fw, np.array(P["palm"]) * (sx, 1, 1), k, curl=0.35))
    void = None
    if head:
        hood, void = hood_local(k)
        hood = S.orient(hood, hc_, up, -np.array(fwd))
        void = S.orient(void, hc_, up, -np.array(fwd))
        robe = S.union(robe, hood, k=0.05 * k)
    else:
        neck = chest + np.array((0, 0, 0.1 * k))
        collar = S.torus(neck, 0.085 * k, 0.03 * k, S.rotm(-0.4 if kneel else 0, 0, 0))
        robe = S.sub(S.union(robe, collar, k=0.03 * k), C(neck - (0, 0, 0.1 * k), neck + (0, 0, 0.2 * k), 0.065 * k, 0.065 * k), k=0.01)
        void = E(neck - (0, 0, 0.04 * k), (0.07 * k, 0.07 * k, 0.05 * k))
    robe = S.noisy(robe, 0.0015 * k, 60, 2)
    objs = [mk(robe, "Robe", 0.007 * k, M[robe_key], 22000)]
    objs.append(mk(void, "Hood_Void", 0.006 * k, M["void"], 1200))
    objs.append(mk(S.union(*hands), "Hands", 0.0022 * k, M["pale"], 5000))
    return objs


def candle_sdf(x, y, z, h, r, drips=3, rnd=None):
    rnd = rnd or random.Random(int(x * 1000 + y * 77))
    top = z + h
    body = S.revolve((x, y, 0), [(r, z - 0.002), (r * 1.01, z + h * 0.5), (r, top - 0.006), (r * 0.9, top)])
    crater = S.sphere((x, y, top + r * 0.45), r * 0.62)
    wax = S.sub(body, crater, k=r * 0.2)
    rim = S.torus((x, y, top - 0.002), r * 0.9, r * 0.14)
    parts = [wax, rim]
    for i in range(drips):
        a = rnd.uniform(0, 6.28); L = rnd.uniform(0.25, 0.85) * h
        p0 = np.array((x + r * math.cos(a), y + r * math.sin(a), top - 0.004))
        p1 = p0 + np.array((0.002 * math.cos(a), 0.002 * math.sin(a), -L))
        parts.append(CH([p0, (p0 + p1) / 2 + np.array((r * 0.08 * math.cos(a), r * 0.08 * math.sin(a), 0)), p1],
                        [r * 0.18, r * 0.2, r * 0.26], k=r * 0.15))
    wick = C((x, y, top - r * 0.1), (x + 0.002, y, top + 0.012), 0.0018, 0.0012)
    flame = S.union(E((x, y, top + 0.026), (r * 0.26 + 0.004, r * 0.26 + 0.004, 0.02)),
                    C((x, y, top + 0.03), (x, y, top + 0.062), r * 0.24 + 0.004, 0.0008), k=0.006)
    return S.union(*parts, k=r * 0.25), wick, flame


def candles(M, specs, name, pool=None, rnd=None):
    rnd = rnd or random.Random(3)
    waxes, wicks, flames = [], [], []
    for (x, y, z, h, r, d) in specs:
        w, wk, f = candle_sdf(x, y, z, h, r, d, rnd)
        waxes.append(w); wicks.append(wk); flames.append(f)
    wax = S.union(*waxes, *( [pool] if pool is not None else []), k=0.01)
    return [mk(S.noisy(wax, 0.0006, 80, 2), name + "_Wax", 0.0022, M["wax_black"], 1500 + 900 * len(specs)),
            mk(S.union(*wicks), name + "_Wicks", 0.0009, M["ink"], 60 * len(specs)),
            mk(S.union(*flames), name + "_Flames", 0.0018, M["flame"], 250 * len(specs))]


def sigil_strokes(cx, cz, R, y, w, depth=0.006, plane="XZ"):
    """The invented glyph as SDF capsules in a vertical XZ plane at depth y (or XY plane on the ground)."""
    segs = []
    n = 48
    ring = [(cx + R * math.cos(2 * math.pi * i / n), cz + R * math.sin(2 * math.pi * i / n)) for i in range(n + 1)]
    pts = [(cx - 0.55 * R, cz + 0.55 * R), (cx, cz - 0.75 * R), (cx + 0.55 * R, cz + 0.55 * R)]
    lines = [ring, pts, [(cx - 0.6 * R, cz + 0.1 * R), (cx + 0.6 * R, cz + 0.1 * R)], [(cx, cz + 0.9 * R), (cx, cz - 0.95 * R)],
             [(cx - 0.3 * R, cz + 0.6 * R), (cx + 0.3 * R, cz + 0.6 * R)],
             [(cx + 0.35 * R, cz - 0.35 * R), (cx + 0.75 * R, cz - 0.1 * R)], [(cx - 0.35 * R, cz - 0.35 * R), (cx - 0.75 * R, cz - 0.1 * R)]]
    P = (lambda a, b: (a, y, b)) if plane == "XZ" else (lambda a, b: (a, b, y))
    for L in lines:
        segs.append(CH([P(*p) for p in L], w, k=w * 0.5))
    for dx in (-0.25, 0, 0.25):
        segs.append(S.sphere(P(cx + dx * R, cz - 1.15 * R), w * 1.5))
    return S.union(*segs)


def cloth_sheet(name, w, h, nx, ny, center, rot, colliders, frames=60, pin=None, mass=0.3, tension=15, bending=0.08, thick=0.004,
                trim=None, jitter=0.0):
    cl = H.grid_cloth(name, w, h, nx, ny, center, rot)
    if trim or jitter:
        import bmesh
        bm = bmesh.new(); bm.from_mesh(cl.data)
        rng = random.Random(1)
        if jitter:
            for v in bm.verts:
                v.co.z += jitter * math.sin(v.co.x * 9 + rng.random()) * math.sin(v.co.y * 7)
        if trim:
            bmesh.ops.delete(bm, geom=[v for v in bm.verts if trim(v.co)], context="VERTS")
        bm.to_mesh(cl.data); bm.free()
    if pin:
        H.pin_where(cl, pin, "pin")
    H.cloth_drape(cl, colliders, frames=frames, pin_group="pin" if pin else None, mass=mass, tension=tension, bending=bending,
                  quality=6, thickness=thick)
    H.solidify(cl, thick, 0.0)
    H.subsurf(cl, 1)
    H.decimate(cl, 24000)
    return cl


def remove(objs):
    for o in objs:
        bpy.data.objects.remove(o)


# ====================================================================== props
@hq("seance_table", 1024)
def seance_table(M):
    mats(M)
    root = PL.root_empty("seance_table")
    rnd = random.Random(4)
    objs = []
    top = S.revolve((0, 0, 0), [(0.6, 0.735), (0.612, 0.75), (0.605, 0.765), (0.6, 0.78)])
    col = S.revolve((0, 0, 0), [(0.08, 0.1), (0.1, 0.14), (0.055, 0.2), (0.075, 0.3), (0.05, 0.42), (0.065, 0.55), (0.045, 0.62), (0.11, 0.7), (0.13, 0.74)])
    legs = [CH([(0.07 * math.cos(a), 0.07 * math.sin(a), 0.16), (0.24 * math.cos(a), 0.24 * math.sin(a), 0.09), (0.33 * math.cos(a), 0.33 * math.sin(a), 0.03)],
               [0.045, 0.032, 0.026], k=0.02) for a in (math.pi / 2 + i * 2 * math.pi / 3 for i in range(3))]
    feet = [S.noisy(S.union(*[CH([(0.33 * math.cos(a) + 0.03 * math.cos(a + o), 0.33 * math.sin(a) + 0.03 * math.sin(a + o), 0.03),
                                  (0.36 * math.cos(a) + 0.045 * math.cos(a + o), 0.36 * math.sin(a) + 0.045 * math.sin(a + o), 0.008)],
                                 [0.012, 0.008], k=0.004) for o in (-0.6, 0, 0.6)], S.sphere((0.34 * math.cos(a), 0.34 * math.sin(a), 0.03), 0.032), k=0.01), 0.002, 40, 2)
            for a in (math.pi / 2 + i * 2 * math.pi / 3 for i in range(3))]
    table = mk(S.union(top, col, *legs, *feet, k=0.015), "Table", 0.0035, M["walnut"], 9000)
    objs.append(table)
    coll = mk(S.revolve((0, 0, 0), [(0.6, 0.7), (0.605, 0.78)]), "_coll", 0.01, M["walnut"])
    cloth = cloth_sheet("Velvet_Cloth", 1.55, 1.55, 70, 70, (0, 0, 0.83), (0, 0, 0.35), [coll], frames=70, bending=0.06, thick=0.005)
    H.set_mat(cloth, M["velvet"])
    remove([coll])
    objs.append(cloth)
    bpy.context.view_layer.update()
    zt = max((cloth.matrix_world @ v.co).z for v in cloth.data.vertices if abs(v.co.x) < 0.3 and abs(v.co.y) < 0.3)
    board = mk(S.box((0, 0.0, zt + 0.007), (0.6, 0.41, 0.014), 0.004), "Spirit_Board", 0.002, M["walnut"], 800)
    face = BP.MB(); face.quad([(-0.295, -0.2, zt + 0.0142), (0.295, -0.2, zt + 0.0142), (0.295, 0.2, zt + 0.0142), (-0.295, 0.2, zt + 0.0142)])
    face = face.obj("Board_Face", [H.image_mat("Board_Art", TX.spirit_board(), 0.6)])
    H.planar_uv(face, "Z")
    objs += [board, face]
    pl = S.sub(S.union(E((0.08, -0.04, zt + 0.03), (0.055, 0.075, 0.012)), C((0.08, -0.1, zt + 0.03), (0.08, -0.13, zt + 0.03), 0.03, 0.004), k=0.03),
               S.sphere((0.08, -0.02, zt + 0.03), 0.02))
    pl = S.union(pl, *[C((0.08 + dx, -0.04 + dy, zt + 0.02), (0.08 + dx, -0.04 + dy, zt + 0.014), 0.006, 0.005) for dx, dy in ((-0.035, 0.03), (0.035, 0.03), (0, -0.06))])
    objs.append(mk(pl, "Planchette", 0.0015, M["walnut"], 1500))
    specs = [(x, y, zt - 0.004, 0.12 + 0.07 * (i % 3), 0.024, 3) for i, (x, y) in enumerate([(-0.42, 0.25), (0.45, 0.2), (-0.3, -0.38), (0.36, -0.36), (0.0, 0.44)])]
    objs += candles(M, specs, "Seance")
    # four turned chairs (one mesh, instanced)
    seat = S.box((0, 0, 0.46), (0.42, 0.4, 0.035), 0.01)
    legsc = [S.revolve((0.17 * sx, 0.16 * sy, 0), [(0.016, 0.0), (0.02, 0.08), (0.014, 0.16), (0.022, 0.24), (0.017, 0.44)]) for sx in (-1, 1) for sy in (-1, 1)]
    posts = [S.revolve((0.17 * sx, 0.17, 0.44), [(0.02, 0.0), (0.016, 0.15), (0.022, 0.3), (0.016, 0.5), (0.024, 0.56), (0.004, 0.6)]) for sx in (-1, 1)]
    rail = B([(-0.18, 0.18, 0.94), (0, 0.19, 0.97), (0.18, 0.18, 0.94)], 0.04, 0.014, nrm=(0, 0, 1))
    spind = [S.revolve((x, 0.175, 0.47), [(0.009, 0.0), (0.014, 0.12), (0.009, 0.24), (0.008, 0.46)]) for x in (-0.09, 0, 0.09)]
    stret = [C((-0.16, sy * 0.16, 0.14), (0.16, sy * 0.16, 0.14), 0.01, 0.01) for sy in (-1, 1)]
    chair = mk(S.noisy(S.union(seat, *legsc, *posts, rail, *spind, *stret, k=0.008), 0.0006, 50, 2), "Chair", 0.0032, M["walnut"], 6000)
    for i, a in enumerate((0, 90, 180, 270)):
        r = math.radians(a)
        objs.append(H.instance(chair, f"Chair_{i}", mat4((0.95 * math.sin(r), -0.95 * math.cos(r), 0), (0, 0, r + math.pi))))
    remove([chair])
    parent(objs, root)
    return {"name": "Séance table", "cat": CAT, "behaviors": ["flicker"],
            "light": {"type": "point", "color": "#ff9a3c", "intensity": 3, "offset": [0, 1.05, 0]},
            "desc": "Turned walnut table under a draped velvet cloth: painted spirit board, planchette, dripping black candles, four spindle chairs."}


@hq("ritual_circle", 1024)
def ritual_circle(M):
    mats(M)
    root = PL.root_empty("ritual_circle")
    R = 1.6
    rnd = random.Random(8)
    lines = [S.torus((0, 0, 0.0), rr, 0.012, S.rotm(0, 0, 0)) for rr in (R, R * 0.9)]
    pts = [np.array((R * 0.88 * math.cos(math.radians(-90 + 72 * i)), R * 0.88 * math.sin(math.radians(-90 + 72 * i)), 0.0)) for i in range(5)]
    for i in range(5):
        lines.append(C(pts[i], pts[(i + 2) % 5], 0.014, 0.014))
    for i in range(30):   # invented rune strokes between the rings
        a = 2 * math.pi * i / 30
        c = np.array((R * 0.95 * math.cos(a), R * 0.95 * math.sin(a), 0))
        t = np.array((-math.sin(a), math.cos(a), 0)); n = c / np.linalg.norm(c)
        shape = rnd.choice(["v", "bar", "hook", "x"])
        L = 0.035
        if shape == "v":
            lines.append(CH([c - t * L + n * L, c - n * L, c + t * L + n * L], 0.006))
        elif shape == "bar":
            lines.append(CH([c - n * L, c + n * L], 0.006)); lines.append(S.sphere(c + t * L * 0.9, 0.009))
        elif shape == "hook":
            lines.append(CH([c - n * L - t * L * 0.5, c + n * L - t * L * 0.5, c + n * L + t * L * 0.6], 0.006))
        else:
            lines.append(CH([c - t * L - n * L, c + t * L + n * L], 0.006)); lines.append(CH([c - t * L + n * L, c + t * L - n * L], 0.006))
    glow = S.inter(S.noisy(S.union(*lines), 0.002, 30, 2), S.box((0, 0, 0.0), (4, 4, 0.016), 0.0))
    objs = [mk(glow, "Ritual_Lines", 0.004, M["sigil"], 26000)]
    ash = S.inter(S.noisy(S.sub(S.revolve((0, 0, 0), [(R * 1.06, -0.01), (R * 1.04, 0.004)]), S.revolve((0, 0, 0), [(R * 0.86, -0.02), (R * 0.86, 0.02)]), k=0.02),
                          0.003, 6, 3), S.box((0, 0, 0), (4, 4, 0.012)))
    objs.append(mk(ash, "Ash_Ring", 0.008, M["char"], 6000))
    specs = [(p[0] * 1.13, p[1] * 1.13, 0.0, 0.22 + 0.07 * (i % 2), 0.04, 4) for i, p in enumerate(pts)]
    pools = [S.inter(S.noisy(E((p[0] * 1.13, p[1] * 1.13, 0.0), (0.1, 0.09, 0.012)), 0.004, 25, 2), S.box((p[0] * 1.13, p[1] * 1.13, 0.02), (0.3, 0.3, 0.04))) for p in pts]
    objs += candles(M, specs, "Circle", pool=S.union(*pools), rnd=rnd)
    parent(objs, root)
    return {"name": "Ritual circle", "cat": CAT, "behaviors": ["pulse"],
            "light": {"type": "point", "color": "#ff1a0a", "intensity": 4, "offset": [0, 0.3, 0]},
            "desc": "3 m glowing inverted star in a double ring of invented runes on scorched ash, a guttering black candle on each point."}


def cultist_prop(M, pid, name, robe, pose, kneel, head, desc, seed):
    mats(M)
    root = PL.root_empty(pid)
    objs = robed_figure(M, robe, pose, kneel, head, seed=seed)
    parent(objs, root)
    return {"name": name, "cat": CAT, "behaviors": ["sway_body"], "desc": desc}


@hq("cultist", 1024)
def cultist(M):
    return cultist_prop(M, "cultist", "Hooded cultist", "robe_black", "clasped", False, True,
                        "Faceless figure in a heavy black robe, long pale hands clasped. Place them in a ring.", 1)


@hq("cultist_crimson", 1024)
def cultist_crimson(M):
    return cultist_prop(M, "cultist_crimson", "Crimson acolyte", "robe_red", "raised", False, True,
                        "Crimson-robed acolyte with both arms raised, sleeves falling back.", 2)


@hq("kneeling_acolyte", 1024)
def kneeling_acolyte(M):
    return cultist_prop(M, "kneeling_acolyte", "Kneeling acolyte", "robe_black", "out", True, True,
                        "Bowed, kneeling worshipper in a pooled robe, arms spread low, palms down.", 3)


@hq("headless_worshipper", 1024)
def headless_worshipper(M):
    return cultist_prop(M, "headless_worshipper", "Headless worshipper", "robe_white", "clasped", True, False,
                        "Kneeling robed figure with nothing above the collar. No gore, just absence.", 4)


def goat_skull_horns(M, name, k=1.0):
    sk, th = A.deer_skull_sdf(0.85 * k)
    horns = []
    for s in (-1, 1):
        pts = [(s * (0.025 + 0.11 * t) * k, (0.02 + 0.17 * math.sin(t * 2.1)) * k, (0.05 + 0.16 * math.cos(t * 2.1) - 0.02) * k) for t in np.linspace(0, 1, 10)]
        horns.append(A.horn_curve_sdf(pts, 0.03 * k, 0.006 * k, 0.002 * k))
    return [mk(S.noisy(sk, 0.0005, 80, 2), name + "_Skull", 0.0014 * k, M["bone_old"], 5000),
            mk(th, name + "_Teeth", 0.001 * k, M["tooth"], 600),
            mk(S.union(*horns), name + "_Horns", 0.002 * k, M["horn_ram"], 5000)]


@hq("black_altar", 1024)
def black_altar(M):
    mats(M)
    root = PL.root_empty("black_altar")
    objs = []
    block = S.union(S.box((0, 0, 0.45), (1.3, 0.6, 0.9), 0.02), S.box((0, 0, 0.93), (1.42, 0.7, 0.06), 0.012),
                    S.box((0, 0, 0.04), (1.42, 0.7, 0.08), 0.012), k=0.004)
    block = S.sub(block, S.box((0, -0.3, 0.5), (0.9, 0.04, 0.6), 0.01), k=0.004)                          # recessed front panel
    block = S.sub(block, sigil_strokes(0, 0.5, 0.2, -0.28, 0.012), k=0.002)                              # engraved sigil
    block = S.noisy(S.noisy(block, 0.006, 4, 3, ridged=True), 0.0015, 30, 2)
    objs.append(mk(block, "Altar_Block", 0.006, M["stone_altar"], 14000))
    objs.append(mk(S.inter(sigil_strokes(0, 0.5, 0.2, -0.276, 0.008), S.box((0, -0.27, 0.5), (0.6, 0.02, 0.6))), "Altar_Sigil", 0.003, M["sigil"], 4000))
    coll = mk(S.box((0, 0, 0.5), (1.42, 0.7, 0.92), 0.01), "_coll", 0.02, M["stone_altar"])
    runner = cloth_sheet("Altar_Runner", 0.45, 1.7, 22, 80, (0.0, 0.0, 1.0), (0, 0, 0), [coll], frames=60, bending=0.1, thick=0.004)
    H.set_mat(runner, M["robe_red"])
    remove([coll])
    objs.append(runner)
    sk = goat_skull_horns(M, "Goat", 1.0)
    for o in sk:
        o.matrix_world = mat4((0, 0.12, 1.08), (math.radians(-8), 0, 0)) @ o.matrix_world
    objs += sk
    eyes = BP.MB()
    for sx in (-1, 1):
        eyes.sphere((sx * 0.033, 0.084, 1.09), 0.012, segs=(12, 8))
    objs.append(eyes.obj("Goat_Eyes", [M["eye_red"]]))
    chal = S.sub(S.revolve((0.38, -0.05, 0), [(0.06, 0.96), (0.05, 0.975), (0.014, 0.99), (0.011, 1.04), (0.022, 1.05), (0.012, 1.07),
                                               (0.03, 1.1), (0.055, 1.16), (0.062, 1.21)]), S.sphere((0.38, -0.05, 1.235), 0.055), k=0.004)
    objs.append(mk(chal, "Chalice", 0.0016, M["gilt"], 3000))
    blade = S.union(S.box((-0.25, -0.15, 0.967), (0.26, 0.032, 0.005), 0.001, S.rotm(0, 0, 0.3)),
                    C((-0.1 - 0.0, -0.2, 0.972), (-0.03, -0.22, 0.972), 0.012, 0.012) if False else S.box((-0.08, -0.205, 0.972), (0.11, 0.022, 0.02), 0.008, S.rotm(0, 0, 0.3)),
                    S.box((-0.125, -0.19, 0.972), (0.012, 0.08, 0.012), 0.004, S.rotm(0, 0, 0.3)))
    objs.append(mk(blade, "Athame", 0.0015, M["iron"], 2000))
    pages = S.union(*[S.box((s * 0.115, 0.12, 0.98), (0.22, 0.3, 0.02), 0.004, S.rotm(0, s * 0.1, 0)) for s in (-1, 1)])
    cover = S.union(*[S.box((s * 0.12, 0.12, 0.97), (0.235, 0.315, 0.008), 0.002, S.rotm(0, s * 0.1, 0)) for s in (-1, 1)])
    objs.append(mk(cover, "Grimoire_Cover", 0.0025, M["leather"], 1200))
    pg = mk(pages, "Grimoire_Pages", 0.0025, M["muslin"], 1500)
    H.set_mat(pg, H.image_mat("Grimoire_Art", TX.grimoire_pages(), 0.8)); H.planar_uv(pg, "Z")
    objs.append(pg)
    specs = [(x, 0.15 - 0.1 * (i % 2), 0.96, 0.25 + 0.1 * (i % 2), 0.032, 4) for i, x in enumerate((-0.6, -0.48, 0.5, 0.62))]
    objs += candles(M, specs, "Altar")
    parent(objs, root)
    return {"name": "Black altar", "cat": CAT, "behaviors": ["flicker"],
            "light": {"type": "point", "color": "#ff8a30", "intensity": 3, "offset": [0, 1.4, 0.2]},
            "desc": "Chipped basalt altar with an engraved glowing sigil, crimson runner, horned goat skull, gilt chalice, athame, open grimoire and black tapers."}


@hq("horned_idol", 1024)
def horned_idol(M):
    mats(M)
    root = PL.root_empty("horned_idol")
    objs = []
    plinth = S.noisy(S.union(S.box((0, 0, 0.3), (1.1, 0.9, 0.6), 0.015), S.box((0, 0, 0.625), (1.2, 1.0, 0.05), 0.01), k=0.004), 0.005, 4, 3, ridged=True)
    plinth = S.sub(plinth, sigil_strokes(0, 0.32, 0.18, -0.452, 0.012), k=0.002)
    objs.append(mk(plinth, "Plinth", 0.007, M["stone_altar"], 9000))
    objs.append(mk(S.inter(sigil_strokes(0, 0.32, 0.18, -0.448, 0.008), S.box((0, -0.45, 0.32), (0.6, 0.02, 0.6))), "Plinth_Sigil", 0.003, M["sigil"], 3000))
    hip, chest = np.array((0, 0.08, 0.78)), np.array((0, 0.02, 1.52))
    body = S.union(C(hip, chest, 0.3, 0.26), E(chest + (0, 0, 0.05), (0.33, 0.2, 0.11)),
                   *[C((sx * 0.18, 0.02, 0.8), (sx * 0.2, -0.45, 0.88), 0.15, 0.13) for sx in (-1, 1)],
                   *[C((sx * 0.2, -0.45, 0.85), (sx * 0.22, -0.5, 0.65), 0.13, 0.17) for sx in (-1, 1)],
                   S.revolve((0, -0.15, 0.62), [(0.42, 0.0), (0.38, 0.12), (0.3, 0.3)], S.folds(9, 0.03, 0.0, 0.3, 5), sy=1.2), k=0.08)
    for sx, raise_ in ((1, True), (-1, False)):
        s0 = chest + (sx * 0.3, 0, 0.02)
        el = s0 + (sx * 0.18, -0.12, -0.3)
        wr = el + ((sx * 0.02, -0.15, 0.32) if raise_ else (sx * 0.02, -0.3, -0.05))
        body = S.union(body, sleeve(s0, el, wr, 0.1, 0.11, 0.14), k=0.05)
        objs.append(mk(hand_sdf(wr, (0, -0.1, 1) if raise_ else (0, -1, -0.5), (0, -1, 0) if raise_ else (0, 0, -1), 1.35, curl=0.15 if raise_ else 0.5),
                       f"Idol_Hand_{sx + 1}", 0.003, M["fur"], 3000))
    objs.append(mk(S.noisy(body, 0.002, 40, 2), "Idol_Robe", 0.008, M["robe_black"], 16000))
    hc = np.array((0, -0.02, 1.95))
    head = S.union(E(hc, (0.13, 0.15, 0.15)), C(hc + (0, -0.05, -0.02), hc + (0, -0.31, -0.13), 0.095, 0.05),
                   C(hc + (0, -0.24, -0.17), hc + (0, -0.22, -0.4), 0.045, 0.008),
                   *[CH([hc + (sx * 0.12, 0.0, 0.02), hc + (sx * 0.24, 0.02, -0.02), hc + (sx * 0.3, 0.03, -0.07)], [0.035, 0.03, 0.008], k=0.02) for sx in (-1, 1)],
                   C(hc + (0, 0.0, -0.1), chest + (0, 0.02, 0.1), 0.1, 0.13), k=0.05)
    head = S.sub(head, *[S.sphere(hc + (sx * 0.07, -0.12, 0.04), 0.03) for sx in (-1, 1)], k=0.01)
    head = S.noisy(S.noisy(head, 0.006, 70, 2, ridged=True, stretch=(1, 1, 0.3)), 0.002, 150, 1)
    objs.append(mk(head, "Goat_Head", 0.004, M["fur"], 12000))
    eyes = BP.MB()
    for sx in (-1, 1):
        eyes.sphere(tuple(hc + (sx * 0.07, -0.12, 0.04)), 0.022, segs=(12, 8))
    objs.append(eyes.obj("Idol_Eyes", [M["eye_red"]]))
    horns = []
    for s in (-1, 1):
        n = S.move(A.ram_horn_sdf(s, 1.9, 1.05, 0.05), dx=hc[0] + s * 0.06, dy=hc[1] + 0.02, dz=hc[2] + 0.06)
        horns.append(n)
    objs.append(mk(S.union(*horns), "Idol_Horns", 0.006, M["horn_ram"], 9000))
    objs += candles(M, [(0.0, 0.02, 2.1, 0.12, 0.024, 3)], "Idol_Crown")
    parent(objs, root)
    return {"name": "Horned idol", "cat": CAT, "behaviors": ["pulse"],
            "light": {"type": "point", "color": "#ff6a2a", "intensity": 2.5, "offset": [0, 2.35, 0]},
            "desc": "Enthroned goat-headed effigy with spiralled ram horns and a furred head, one hand raised, a candle burning between its horns."}


@hq("sigil_banner", 1024)
def sigil_banner(M):
    mats(M)
    root = PL.root_empty("sigil_banner")
    objs = []
    iron = S.union(C((0, 0.03, -0.1), (0, 0.03, 2.9), 0.026, 0.022), C((-0.58, 0.03, 2.75), (0.58, 0.03, 2.75), 0.018, 0.018),
                   *[S.union(S.sphere((x, 0.03, 2.75), 0.032), C((x * 1.04, 0.03, 2.75), (x * 1.1, 0.03, 2.75), 0.02, 0.002), k=0.01) for x in (-0.58, 0.58)],
                   S.union(S.sphere((0, 0.03, 2.92), 0.04), C((0, 0.03, 2.95), (0, 0.03, 3.08), 0.02, 0.001), k=0.01), k=0.01)
    objs.append(mk(S.noisy(iron, 0.001, 50, 2), "Banner_Pole", 0.003, M["iron"], 5000))
    rings = S.union(*[S.torus((x, 0.03, 2.73), 0.026, 0.005, S.rotm(0, math.pi / 2, 0)) for x in np.linspace(-0.46, 0.46, 6)])
    objs.append(mk(rings, "Banner_Rings", 0.0015, M["iron"], 1500))
    coll = mk(C((-0.6, 0.03, 2.75), (0.6, 0.03, 2.75), 0.022, 0.022), "_coll", 0.005, M["iron"])
    def hem(co):
        return co.y < -0.85 + 0.25 * (1 - abs(co.x) * 2) * 0 and False
    cl = H.grid_cloth("Banner", 1.0, 1.75, 40, 70, (0, 0, 0), (0, 0, 0))
    import bmesh
    bm = bmesh.new(); bm.from_mesh(cl.data)
    bmesh.ops.delete(bm, geom=[v for v in bm.verts if v.co.y < -0.875 + 0.28 * (1 - abs(v.co.x) * 2)], context="VERTS")   # swallowtail
    bm.to_mesh(cl.data); bm.free()
    cl.rotation_euler = (math.pi / 2, 0, 0); cl.location = (0, 0.0, 2.73 - 0.875)
    for v in cl.data.vertices:
        v.co.z += 0.012 * math.sin(v.co.x * 14) * (0.875 - v.co.y) / 1.75
    bpy.context.view_layer.update()
    H.pin_where(cl, lambda p: p.z > 2.72, "pin")
    H.cloth_drape(cl, [coll], frames=45, pin_group="pin", mass=0.35, tension=20, bending=0.4, quality=6, thickness=0.004)
    H.solidify(cl, 0.004); H.subsurf(cl, 1); H.decimate(cl, 16000)
    cp, ep = TX.sigil_cloth()
    H.set_mat(cl, H.image_mat("Banner_Art", cp, 0.8, ep, (1.0, 0.06, 0.02), 6.0))
    remove([coll])
    objs.append(cl)
    parent(objs, root)
    return {"name": "Sigil banner", "cat": CAT, "behaviors": ["pulse", "swing"],
            "desc": "Crimson swallowtail banner hanging from a forged iron standard, a gilt invented sigil glowing through the cloth."}


@hq("wall_sigil", 1024)
def wall_sigil(M):
    mats(M)
    root = PL.root_empty("wall_sigil")
    rnd = random.Random(5)
    paint = sigil_strokes(0, 0.0, 0.45, -0.004, 0.028)
    drips = []
    for i in range(16):
        x = rnd.uniform(-0.42, 0.42)
        ztop = -0.45 * math.sqrt(max(0, 1 - (x / 0.45) ** 2)) + 0.01 if abs(x) < 0.45 else -0.1
        L = rnd.uniform(0.08, 0.4)
        drips.append(CH([(x, -0.004, ztop), (x + rnd.uniform(-0.01, 0.01), -0.004, ztop - L * 0.6), (x, -0.004, ztop - L)], [0.012, 0.008, 0.011], k=0.006))
    node = S.inter(S.noisy(S.union(paint, *drips, k=0.01), 0.002, 30, 2), S.box((0, -0.003, 0), (1.4, 0.006, 2.2)))
    objs = [mk(node, "Wall_Sigil", 0.003, M["sigil_paint"], 12000)]
    parent(objs, root)
    return {"name": "Painted sigil", "cat": CAT, "decal": True, "behaviors": ["pulse"],
            "desc": "Dripping red glyph that sticks flat to whatever you click: siding, door, porch floor."}


@hq("black_candles", 1024)
def black_candles(M):
    mats(M)
    root = PL.root_empty("black_candles")
    rnd = random.Random(21)
    specs = []
    for i in range(19):
        a, r = rnd.uniform(0, 6.28), rnd.uniform(0, 0.5)
        specs.append((r * math.cos(a), r * math.sin(a), 0.0, rnd.uniform(0.12, 0.6), rnd.uniform(0.022, 0.045), rnd.randint(2, 5)))
    pool = S.inter(S.noisy(E((0, 0, 0), (0.64, 0.6, 0.02)), 0.006, 6, 3), S.box((0, 0, 0.03), (1.6, 1.6, 0.06)))
    objs = candles(M, specs, "Cluster", pool=pool, rnd=rnd)
    parent(objs, root)
    return {"name": "Black candle cluster", "cat": CAT, "behaviors": ["flicker"],
            "light": {"type": "point", "color": "#ffa040", "intensity": 3, "offset": [0, 0.8, 0]},
            "desc": "Nineteen guttering black candles fused into a spreading pool of wax."}


@hq("inverted_cross", 1024)
def inverted_cross(M):
    mats(M)
    root = PL.root_empty("inverted_cross")
    beam = S.union(S.box((0, 0, 1.2), (0.12, 0.12, 2.4), 0.008), S.box((0, 0, 0.75), (0.86, 0.12, 0.12), 0.008), k=0.004)
    beam = S.noisy(S.noisy(beam, 0.004, 4, 3, stretch=(1, 1, 0.08)), 0.002, 30, 2, ridged=True, stretch=(1, 1, 0.1))
    objs = [mk(beam, "Cross_Timber", 0.005, M["timber"], 9000)]
    nails = S.union(*[S.union(C((x, -0.06, z), (x, -0.08, z), 0.01, 0.01), S.sphere((x, -0.082, z), 0.012), k=0.004) for x, z in ((0, 0.72), (0, 0.78), (-0.03, 0.75), (0.03, 0.75))])
    objs.append(mk(S.noisy(nails, 0.0008, 60, 1), "Cross_Spikes", 0.0018, M["iron"], 1200))
    base = S.noisy(S.box((0, 0, 0.06), (0.55, 0.55, 0.12), 0.02), 0.008, 5, 3, ridged=True)
    objs.append(mk(base, "Cross_Base", 0.008, M["stone_altar"], 3000))
    specs = [(x, y, 0.12 if abs(x) < 0.27 and abs(y) < 0.27 else 0.0, 0.25 + 0.08 * i, 0.032, 3) for i, (x, y) in enumerate(((-0.2, -0.36), (0.2, -0.36), (-0.4, -0.1), (0.4, -0.1)))]
    objs += candles(M, specs, "Cross")
    parent(objs, root)
    return {"name": "Inverted cross", "cat": CAT, "behaviors": ["flicker"],
            "light": {"type": "point", "color": "#ff9040", "intensity": 1.5, "offset": [0, 0.6, 0.3]},
            "desc": "2.4 m adze-hewn upside-down timber cross, iron-spiked, on a stone footing with black tapers."}


@hq("wicker_effigy", 1024)
def wicker_effigy(M):
    mats(M)
    root = PL.root_empty("wicker_effigy")
    rnd = random.Random(7)
    twigs = []
    def bundle(a, b, n=7, r=0.012):
        a, b = np.array(a), np.array(b)
        for _ in range(n):
            j = np.array([rnd.uniform(-0.035, 0.035) for _ in range(3)])
            m = (a + b) / 2 + j * 1.6
            twigs.append(CH([a + j, m, b + j * 0.7 + np.array([rnd.uniform(-0.03, 0.03) for _ in range(3)])], [r, r * 0.9, r * 0.6], k=0.006))
        for t in np.linspace(0.15, 0.85, 3):   # twine bindings
            p = a + (b - a) * t
            twigs.append(S.torus(p, 0.05, 0.006, S.frame(p, p + (b - a))))
    bundle((0.15, 0, 0.0), (0.12, 0, 1.0)); bundle((-0.15, 0, 0.0), (-0.12, 0, 1.0))
    bundle((0, 0, 0.95), (0, 0, 1.82), 9)
    bundle((0, 0, 1.65), (0.62, -0.05, 1.22)); bundle((0, 0, 1.65), (-0.62, -0.05, 1.22))
    for i in range(6):
        z = 1.05 + i * 0.12
        pts = [(0.23 * math.cos(t), 0.15 * math.sin(t), z + 0.02 * math.sin(3 * t)) for t in np.linspace(0, 2 * math.pi, 14)]
        twigs.append(CH(pts, 0.009, k=0.004))
    for i in range(8):
        a0 = i * 0.8
        pts = [(0.13 * math.cos(a0 + t) * math.sin(u), 0.11 * math.sin(a0 + t) * math.sin(u), 1.95 + 0.13 * math.cos(u)) for t, u in zip(np.linspace(0, 3, 9), np.linspace(0.3, 2.8, 9))]
        twigs.append(CH(pts, 0.008, k=0.004))
    effigy = S.noisy(S.union(*twigs), 0.0015, 60, 2, stretch=(0.5, 0.5, 2))
    objs = [mk(effigy, "Wicker_Effigy", 0.004, M["wicker"], 30000)]
    crown = S.union(S.torus((0, 0, 2.06), 0.12, 0.012), *[C((0.12 * math.cos(a), 0.12 * math.sin(a), 2.06), (0.14 * math.cos(a), 0.14 * math.sin(a), 2.22), 0.014, 0.002)
                                                         for a in np.linspace(0, 2 * math.pi, 8)[:-1]], k=0.006)
    objs.append(mk(crown, "Effigy_Crown", 0.002, M["gilt"], 2500))
    flames = []
    for i in range(11):
        a, r = rnd.uniform(0, 6.28), rnd.uniform(0.0, 0.25)
        base = np.array((r * math.cos(a), r * math.sin(a), 0.05))
        hgt = rnd.uniform(0.25, 0.6)
        flames.append(S.union(E(base + (0, 0, hgt * 0.25), (0.07, 0.07, hgt * 0.3)), C(base + (0, 0, hgt * 0.35), base + (rnd.uniform(-0.05, 0.05), rnd.uniform(-0.05, 0.05), hgt), 0.06, 0.004), k=0.04))
    objs.append(mk(S.warp(S.union(*flames, k=0.05), 0.03, 6), "Effigy_Fire", 0.01, M["fire"], 6000))
    coals = S.inter(S.union(*[S.noisy(S.sphere((rnd.uniform(-0.35, 0.35), rnd.uniform(-0.35, 0.35), 0.0), rnd.uniform(0.04, 0.08)), 0.01, 20, 2) for _ in range(40)], k=0.02),
                    S.box((0, 0, 0.05), (1.2, 1.2, 0.1)))
    objs.append(mk(coals, "Effigy_Coals", 0.008, M["coal"], 6000))
    ash = S.inter(S.noisy(E((0, 0, 0), (0.55, 0.55, 0.03)), 0.006, 8, 2), S.box((0, 0, 0.02), (1.4, 1.4, 0.04)))
    objs.append(mk(ash, "Effigy_Ash", 0.01, M["char"], 2000))
    parent(objs, root)
    return {"name": "Burning wicker effigy", "cat": CAT, "behaviors": ["flicker"],
            "light": {"type": "point", "color": "#ff6a1a", "intensity": 8, "offset": [0, 0.6, 0]},
            "desc": "Twine-bound bundled-twig effigy with a gilt crown, smouldering on a bed of coals."}


@hq("crown_under_glass", 1024)
def crown_under_glass(M):
    mats(M)
    root = PL.root_empty("crown_under_glass")
    objs = []
    plinth = S.revolve((0, 0, 0), [(0.22, 0.0), (0.23, 0.03), (0.2, 0.06), (0.08, 0.12), (0.06, 0.2), (0.075, 0.45), (0.055, 0.7), (0.065, 0.9),
                                   (0.2, 0.96), (0.215, 1.0), (0.2, 1.04)])
    objs.append(mk(S.noisy(plinth, 0.0005, 60, 1), "Plinth", 0.003, M["walnut"], 5000))
    cushion = S.noisy(S.box((0, 0, 1.065), (0.21, 0.21, 0.05), 0.022), 0.002, 30, 2)
    objs.append(mk(cushion, "Cushion", 0.003, M["velvet"], 2500))
    band = S.sub(S.revolve((0, 0, 0), [(0.076, 1.085), (0.078, 1.1), (0.075, 1.13)]), S.revolve((0, 0, 0), [(0.068, 1.08), (0.068, 1.14)]))
    pts = [S.union(C((0.074 * math.cos(a), 0.074 * math.sin(a), 1.12), (0.068 * math.cos(a), 0.068 * math.sin(a), 1.215), 0.017, 0.002),
                   S.sphere((0.068 * math.cos(a), 0.068 * math.sin(a), 1.218), 0.005), k=0.003) for a in np.linspace(0, 2 * math.pi, 9)[:-1]]
    beads = [S.sphere((0.079 * math.cos(a), 0.079 * math.sin(a), 1.093), 0.0035) for a in np.linspace(0, 2 * math.pi, 41)[:-1]]
    objs.append(mk(S.union(band, *pts, *beads, k=0.003), "Crown", 0.0011, M["gilt"], 7000))
    gems = BP.MB()
    for a in np.linspace(0, 2 * math.pi, 5)[:-1]:
        gems.sphere((0.08 * math.cos(a + 0.4), 0.08 * math.sin(a + 0.4), 1.11), 0.008, (0.6, 1, 1), (0, 0, a + 0.4), segs=(10, 6))
    objs.append(gems.obj("Crown_Gems", [M["eye_red"]]))
    jar = BP.MB()
    jar.lathe([(0.17, 1.04), (0.17, 1.35), (0.14, 1.45), (0.06, 1.49), (0.03, 1.53), (0.001, 1.55)], 48)
    jar.lathe([(0.03, 1.53), (0.035, 1.56), (0.02, 1.6), (0.001, 1.61)], 16)
    objs.append(jar.obj("Bell_Jar", [M["glass"]]))
    parent(objs, root)
    return {"name": "Crown under glass", "cat": CAT,
            "desc": "A small beaded gold crown on a velvet cushion, under a bell jar on a turned plinth. Waiting for a head."}


@hq("hanging_poppets", 1024)
def hanging_poppets(M):
    mats(M)
    root = PL.root_empty("hanging_poppets")
    rnd = random.Random(2)
    frame = S.union(CH([(-0.9, 0, -0.1), (-0.88, 0.02, 0.9), (-0.86, -0.01, 1.7), (-0.85, 0, 2.3)], [0.05, 0.045, 0.04, 0.035], k=0.02),
                    CH([(0.9, 0, -0.1), (0.89, -0.02, 1.0), (0.86, 0.01, 1.8), (0.85, 0, 2.3)], [0.05, 0.045, 0.04, 0.035], k=0.02),
                    CH([(-0.96, 0, 2.25), (-0.4, 0.01, 2.29), (0.3, -0.01, 2.27), (0.96, 0, 2.28)], [0.04, 0.038, 0.036, 0.034], k=0.02),
                    *[S.noisy(S.sphere((rnd.choice([-0.88, 0.88]), 0, rnd.uniform(0.4, 2.1)), 0.05), 0.01, 20, 2) for _ in range(6)], k=0.03)
    objs = [mk(S.noisy(S.noisy(frame, 0.006, 6, 3, ridged=True, stretch=(1, 1, 0.3)), 0.002, 40, 2), "Gnarled_Frame", 0.006, M["bark"], 9000)]
    strings, dolls, eyes, nails = [], [], [], []
    for i in range(5):
        x = -0.6 + i * 0.3
        L = rnd.uniform(0.3, 0.7)
        top = 2.25 - L
        strings.append(CH([(x, 0, 2.25), (x, 0, top - 0.01)], 0.003))
        c = np.array((x, 0, top))
        doll = S.union(S.sphere(c + (0, 0, -0.06), 0.05), E(c + (0, 0, -0.2), (0.05, 0.04, 0.1)),
                       *[C(c + (sx * 0.035, 0, -0.13), c + (sx * 0.1, 0, -0.22), 0.017, 0.014) for sx in (-1, 1)],
                       *[C(c + (sx * 0.025, 0, -0.28), c + (sx * 0.03, 0, -0.4), 0.02, 0.017) for sx in (-1, 1)],
                       S.torus(c + (0, 0, -0.105), 0.028, 0.006), k=0.012)
        doll = S.sub(doll, *[S.torus(c + (0, 0, -0.06), 0.0505, 0.0012, S.rotm(0, math.pi / 2, 0))], k=0.001)
        dolls.append(S.noisy(doll, 0.0015, 40, 2))
        for sx in (-1, 1):
            eyes.append(S.sub(C(c + (sx * 0.018, -0.044, -0.05), c + (sx * 0.018, -0.052, -0.05), 0.0095, 0.009),
                              *[S.sphere(c + (sx * 0.018 + dx, -0.053, -0.05 + dz), 0.0018) for dx, dz in ((-0.003, 0.003), (0.003, -0.003))]))
        eyes.append(CH([c + (-0.015, -0.047, -0.09), c + (0.015, -0.047, -0.08)], 0.002))
        eyes.append(CH([c + (-0.015, -0.047, -0.08), c + (0.015, -0.047, -0.09)], 0.002))
        nails.append(S.union(C(c + (0, -0.08, -0.18), c + (0, 0.04, -0.18), 0.004, 0.002), C(c + (0, -0.08, -0.18), c + (0, -0.083, -0.18), 0.011, 0.011), k=0.002))
    objs.append(mk(S.union(*strings), "Twine", 0.0015, M["twine"], 1500))
    objs.append(mk(S.union(*dolls), "Poppets", 0.0025, M["muslin"], 12000))
    objs.append(mk(S.union(*eyes), "Button_Eyes", 0.001, M["ink"], 3000))
    objs.append(mk(S.union(*nails), "Nails", 0.0012, M["iron"], 1500))
    parent(objs, root)
    return {"name": "Hanging poppets", "cat": CAT, "behaviors": ["swing"],
            "desc": "Five stitched muslin poppets with button eyes and X-stitched mouths, iron nails through their chests, dangling from a gnarled frame."}


@hq("shrouded_mirror", 1024)
def shrouded_mirror(M):
    mats(M)
    root = PL.root_empty("shrouded_mirror")
    objs = []
    oval = lambda R, r, y=0: S.move(S.torus((0, 0, 0), R, r), dy=y, dz=1.15, rx=math.pi / 2, s=1.0)
    frame = S.union(S.xform(S.torus((0, 0, 0), 0.42, 0.038), np.array([[1, 0, 0, 0], [0, 0, -1, 0.0], [0, 1.35, 0, 1.15], [0, 0, 0, 1]], float)),
                    *[S.sphere((0.45 * math.cos(a), -0.02, 1.15 + 0.6 * math.sin(a)), 0.014) for a in np.linspace(0, 2 * math.pi, 49)[:-1]],
                    CH([(-0.12, 0.0, 1.74), (-0.06, -0.01, 1.82), (0, -0.01, 1.86), (0.06, -0.01, 1.82), (0.12, 0.0, 1.74)], [0.02, 0.025, 0.03, 0.025, 0.02], k=0.01),
                    *[CH([(sx * 0.12, 0.0, 1.74), (sx * 0.2, -0.01, 1.77), (sx * 0.22, -0.015, 1.71), (sx * 0.18, -0.02, 1.7)], [0.018, 0.014, 0.01, 0.006], k=0.006) for sx in (-1, 1)],
                    k=0.006)
    stand = S.union(*[C((0.36 * sx, 0.06, 0.0), (0.33 * sx, 0.04, 1.0), 0.028, 0.022) for sx in (-1, 1)], C((-0.42, 0.06, 0.03), (0.42, 0.06, 0.03), 0.028, 0.028),
                    *[S.sphere((0.42 * sx, 0.06, 0.03), 0.04) for sx in (-1, 1)], k=0.01)
    objs.append(mk(S.noisy(S.union(frame, stand, k=0.01), 0.0008, 60, 2), "Mirror_Frame", 0.0035, M["gilt"], 16000))
    glass = BP.MB(); glass.sphere((0, 0.008, 1.15), 0.4, (1.0, 0.02, 1.34), segs=(48, 16))
    mirror = glass.obj("Mirror_Glass", [M["mirror"]])
    objs.append(mirror)
    coll = mk(S.union(S.xform(S.torus((0, 0, 0), 0.42, 0.045), np.array([[1, 0, 0, 0], [0, 0, -1, 0.0], [0, 1.35, 0, 1.15], [0, 0, 0, 1]], float)),
                      E((0, 0.0, 1.15), (0.4, 0.03, 0.55)), S.sphere((0, -0.01, 1.83), 0.05)), "_coll", 0.012, M["gilt"])
    shroud = cloth_sheet("Shroud", 1.25, 1.2, 56, 54, (0.0, 0.0, 1.95), (0, 0, 0.25), [coll], frames=60, bending=0.05, mass=0.25, thick=0.004)
    H.set_mat(shroud, M["robe_black"])
    remove([coll])
    objs.append(shroud)
    parent(objs, root)
    return {"name": "Shrouded mirror", "cat": CAT,
            "desc": "Beaded gilt cheval mirror with a black cloth thrown over its crest, as is done in a house of mourning."}


@hq("miniature_house", 1024)
def miniature_house(M):
    mats(M)
    root = PL.root_empty("miniature_house")
    objs = []
    bench = S.union(S.box((0, 0, 0.78), (1.3, 0.75, 0.05), 0.008),
                    *[S.revolve((0.6 * sx, 0.32 * sy, 0), [(0.035, 0.0), (0.03, 0.1), (0.04, 0.2), (0.028, 0.45), (0.035, 0.7), (0.035, 0.76)]) for sx in (-1, 1) for sy in (-1, 1)],
                    *[S.box((0, 0.32 * sy, 0.2), (1.15, 0.03, 0.03), 0.005) for sy in (-1, 1)], k=0.006)
    objs.append(mk(S.noisy(bench, 0.0006, 50, 2, stretch=(1, 0.3, 0.3)), "Workbench", 0.004, M["walnut"], 7000))
    W, D, Hh, z0 = 1.0, 0.5, 0.36, 0.805
    wp = TX.wallpaper()
    wall_m = H.image_mat("Wallpaper", wp, 0.8)
    back = mk(S.box((0, D / 2, z0 + Hh), (W, 0.02, 2 * Hh), 0.003), "Back_Wall", 0.004, wall_m, 800)
    H.planar_uv(back, "Y")
    sides = mk(S.union(*[S.box((x, 0, z0 + Hh), (0.02, D, 2 * Hh), 0.003) for x in (-W / 2, W / 2)], S.box((0, 0, z0 + Hh / 2), (0.02, D, Hh), 0.003),
                       S.box((0.15, 0, z0 + 1.5 * Hh), (0.02, D, Hh), 0.003)), "Side_Walls", 0.004, wall_m, 1600)
    H.planar_uv(sides, "X")
    for o in (back, sides):   # tile the paper
        for l in o.data.uv_layers["SrcUV"].data:
            l.uv = (l.uv[0] * 4, l.uv[1] * 3)
    objs += [back, sides]
    floors = S.union(*[S.box((0, 0, z), (W, D, 0.02), 0.002) for z in (z0, z0 + Hh, z0 + 2 * Hh)])
    floors = S.sub(floors, *[S.box((x, 0, z + 0.0105), (0.003, D * 1.1, 0.004)) for z in (z0, z0 + Hh) for x in np.linspace(-0.45, 0.45, 13)], k=0.001)
    objs.append(mk(floors, "Floors", 0.003, M["walnut"], 3000))
    roof = S.union(*[S.box((s * W / 4, 0, z0 + 2 * Hh + 0.12), (W / 2 * 1.18, D + 0.06, 0.02), 0.003, S.rotm(0, s * 0.45, 0)) for s in (-1, 1)])
    roof = S.noisy(roof, 0.0015, 60, 2, ridged=True, stretch=(1, 0.2, 1))
    objs.append(mk(roof, "Roof", 0.004, M["stone_altar"], 3000))
    furn = S.union(S.box((-0.3, 0.12, z0 + 0.04), (0.18, 0.12, 0.06), 0.006), S.box((-0.3, 0.17, z0 + 0.09), (0.18, 0.02, 0.1), 0.004),
                   S.box((0.25, 0.1, z0 + 0.06), (0.25, 0.14, 0.012), 0.003), *[C((0.25 + dx, 0.1 + dy, z0 + 0.01), (0.25 + dx, 0.1 + dy, z0 + 0.06), 0.006, 0.005) for dx in (-0.1, 0.1) for dy in (-0.05, 0.05)],
                   S.box((-0.2, 0.12, z0 + Hh + 0.05), (0.2, 0.22, 0.08), 0.008), S.box((0.33, 0.18, z0 + Hh + 0.1), (0.1, 0.07, 0.2), 0.004), k=0.002)
    objs.append(mk(furn, "Furniture", 0.0025, M["wood"], 5000))
    figs = []
    for (x, z) in ((-0.32, z0), (0.22, z0), (-0.12, z0 + Hh), (0.34, z0 + Hh)):
        figs.append(S.union(S.revolve((x, -0.05, 0), [(0.022, z + 0.01), (0.02, z + 0.04), (0.012, z + 0.09), (0.008, z + 0.1)]), S.sphere((x, -0.05, z + 0.115), 0.016),
                            *[C((x + sx * 0.012, -0.052, z + 0.085), (x + sx * 0.018, -0.06, z + 0.045), 0.004, 0.003) for sx in (-1, 1)], k=0.004))
    objs.append(mk(S.union(*figs), "Tiny_Figures", 0.0012, M["pale"], 4000))
    lamps = BP.MB()
    for (x, z) in ((-0.25, z0 + 0.3), (0.3, z0 + 0.3), (-0.2, z0 + Hh + 0.3), (0.33, z0 + Hh + 0.3)):
        lamps.cyl((x, 0.1, z + 0.06), (x, 0.1, z + 0.02), 0.002, segs=4)
        lamps.lathe([(0.02, z - 0.02), (0.012, z + 0.02)], 12, (x, 0.1, 0))
    objs.append(lamps.obj("Tiny_Lamps", [M["mini_lit"]]))
    parent(objs, root)
    return {"name": "Miniature house", "cat": CAT,
            "light": {"type": "point", "color": "#ffb070", "intensity": 0.8, "offset": [0, 1.2, 0.1]},
            "desc": "Open-front dollhouse on a turned workbench: papered rooms, plank floors, tiny lit lamps and furniture, a small still figure in every room."}
