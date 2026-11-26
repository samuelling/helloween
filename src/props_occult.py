"""Occult set for the Helloween decorator: séance, coven and ritual pieces. All designs are original
(sigils are invented glyphs, not any film's or grimoire's). Builders follow props_lib's conventions:
each creates a root empty named after the prop id and returns its catalog info.
"""
import math, random
import bpy
from mathutils import Vector as V, Matrix, Euler
from lib import *
import build_props as BP
from props_lib import root_empty, text_mesh, pumpkin_mesh

CAT = "Occult"


def occult_mats(M):
    M["robe_black"] = mat("Robe_Black", (0.012, 0.011, 0.013), 0.85, sheen=0.5)
    M["robe_red"] = mat("Robe_Crimson", (0.16, 0.008, 0.012), 0.8, sheen=0.5)
    M["robe_white"] = mat("Robe_Bone_White", (0.62, 0.58, 0.52), 0.85, sheen=0.4)
    M["void"] = mat("Hood_Void", (0.0, 0.0, 0.0), 1.0)
    M["gold"] = mat("Old_Gold", (0.6, 0.42, 0.12), 0.28, metal=1.0)
    M["black_wax"] = mat("Black_Wax", (0.02, 0.018, 0.02), 0.35, coat=0.4)
    M["red_wax"] = mat("Red_Wax", (0.3, 0.01, 0.015), 0.35, coat=0.4)
    M["sigil"] = emission_mat("Sigil_Red", (1.0, 0.04, 0.02), 14)
    M["sigil_paint"] = mat("Sigil_Paint", (0.28, 0.0, 0.01), 0.6, emit=(0.6, 0.0, 0.0), emit_strength=1.2)
    M["purple_cloth"] = mat("Seance_Velvet", (0.09, 0.02, 0.09), 0.9, sheen=0.7)
    M["table_wood"] = mat("Old_Walnut", (0.11, 0.055, 0.03), 0.45, coat=0.4)
    M["parchment"] = mat("Board_Parchment", (0.55, 0.45, 0.3), 0.7)
    M["ink"] = mat("Ink_Black", (0.02, 0.015, 0.01), 0.5)
    M["altar_stone"] = mat("Altar_Stone", (0.09, 0.085, 0.085), 0.8)
    M["glass"] = mat("Bell_Jar_Glass", (0.9, 0.92, 0.95), 0.02)
    M["glass"].node_tree.nodes["Principled BSDF"].inputs["Transmission Weight"].default_value = 1.0
    M["mirror"] = mat("Old_Mirror", (0.7, 0.7, 0.72), 0.06, metal=1.0)
    M["wicker"] = mat("Wicker_Branch", (0.32, 0.22, 0.12), 0.9)
    M["fire"] = emission_mat("Fire_Core", (1.0, 0.35, 0.05), 30)
    M["coal"] = emission_mat("Ember_Coal", (1.0, 0.12, 0.02), 6)
    M["doll_cloth"] = mat("Poppet_Muslin", (0.6, 0.52, 0.4), 0.95)
    M["house_wall"] = mat("Miniature_Wall", (0.42, 0.36, 0.3), 0.8)
    M["mini_lit"] = emission_mat("Miniature_Lamp", (1.0, 0.65, 0.3), 4)
    M["skin_pale"] = mat("Pale_Skin", (0.78, 0.7, 0.64), 0.45, sss=0.08)
    M["goat_fur"] = mat("Goat_Fur_Black", (0.025, 0.02, 0.02), 0.95, sheen=0.8)
    return M


# ------------------------------------------------------------------ shared pieces
def robe_figure(mb, M_idx, h=1.75, kneel=False, arms="clasped", head=True, robe_mi=0, void_mi=1, skin_mi=2):
    """Hooded robe built from lathes. Faces -Y. Returns head centre."""
    k = h / 1.75
    if kneel:
        mb.mi = robe_mi
        # kneeling: robe pooled on ground + torso leaning forward
        mb.lathe([(0.42 * k, 0.0), (0.4 * k, 0.12 * k), (0.3 * k, 0.4 * k), (0.001, 0.45 * k)], 28,
                 rmod=lambda t, z, r, i: r * (1 + 0.05 * math.sin(7 * t)), scale=(1, 1.2))
        top = V((0, -0.1 * k, 0.95 * k))
        mb.cyl((0, 0.08 * k, 0.35 * k), top, 0.24 * k, 0.17 * k, segs=20)
        neck = top + V((0, -0.06 * k, 0.08 * k))
    else:
        mb.mi = robe_mi
        mb.lathe([(0.38 * k, 0.0), (0.36 * k, 0.15 * k), (0.28 * k, 0.6 * k), (0.21 * k, 1.1 * k), (0.2 * k, 1.38 * k),
                  (0.24 * k, 1.45 * k), (0.14 * k, 1.52 * k), (0.06 * k, 1.55 * k)], 32,
                 rmod=lambda t, z, r, i: r * (1 + (0.05 * math.sin(9 * t) if z < 0.5 else 0.015 * math.sin(5 * t))),
                 cap_top=True, scale=(1, 0.85))
        neck = V((0, 0, 1.53 * k))
    hc = neck + V((0, -0.02 * k, 0.17 * k))
    sh = neck + V((0, 0, -0.06 * k))
    if head:
        mb.mi = robe_mi   # hood: shell open at the front
        mb.sphere(hc + V((0, 0.03 * k, 0.02 * k)), 0.15 * k, (0.95, 1.1, 1.2), segs=(20, 14))
        mb.sphere(hc + V((0, 0.05 * k, -0.12 * k)), 0.17 * k, (1.1, 1.0, 0.5), segs=(18, 10))   # hood drape onto shoulders
        mb.mi = void_mi
        mb.sphere(hc + V((0, -0.11 * k, -0.01 * k)), 0.1 * k, (0.9, 0.35, 1.05), segs=(16, 10))
    else:
        mb.mi = void_mi
        mb.cyl(neck - V((0, 0, 0.02)), neck + V((0, 0, 0.04)), 0.06 * k, 0.06 * k, segs=14)
        mb.mi = robe_mi
        mb.torus(neck + V((0, 0, 0.03)), 0.08 * k, 0.025 * k, segs=(18, 6))
    for sx in (-1, 1):
        s0 = sh + V((0.17 * sx * k, 0, -0.03 * k))
        if arms == "clasped":
            el = s0 + V((0.06 * sx * k, -0.1 * k, -0.32 * k))
            hand = V((0.03 * sx * k, sh.y - 0.2 * k, sh.z - 0.45 * k))
        elif arms == "raised":
            el = s0 + V((0.16 * sx * k, -0.12 * k, 0.28 * k))
            hand = el + V((0.06 * sx * k, -0.06 * k, 0.32 * k))
        else:   # palms down, arms out (levitation / worship)
            el = s0 + V((0.3 * sx * k, -0.05 * k, -0.08 * k))
            hand = el + V((0.28 * sx * k, -0.02 * k, -0.06 * k))
        mb.mi = robe_mi
        mb.cyl(s0, el, 0.07 * k, 0.09 * k, segs=12)
        mb.cyl(el, el + (hand - el) * 0.7, 0.09 * k, 0.12 * k, segs=12, cap=False)
        mb.mi = skin_mi
        mb.sphere(hand, 0.04 * k, (0.8, 1.0, 1.3), segs=(10, 8))
    return hc


def candle(mbw, mbf, x, y, z, h, r, drips=3, rnd=None):
    rnd = rnd or random.Random(int(x * 1000 + y * 77))
    mbw.lathe([(r, z), (r, z + h - 0.01), (r * 0.85, z + h), (r * 0.2, z + h - 0.005)], 14, (x, y, 0), cap_bottom=True, cap_top=True)
    for i in range(drips):
        a = rnd.uniform(0, 6.28)
        L = rnd.uniform(0.2, 0.7) * h
        mbw.cyl((x + r * math.cos(a), y + r * math.sin(a), z + h - 0.005), (x + r * 1.02 * math.cos(a), y + r * 1.02 * math.sin(a), z + h - L),
                r * 0.18, r * 0.25, segs=5)
    mbf.sphere((x, y, z + h + 0.014), r * 0.28, (0.7, 0.7, 1.9), segs=(8, 6))


def sigil_lines(mb, cx, cz, R, y, w=0.012, seed=0):
    """An invented glyph: circle, inverted chevron, crossed bars, three dots. Drawn as thin boxes in XZ at depth y."""
    rnd = random.Random(seed)
    segs = []
    n = 40
    for i in range(n):
        a0, a1 = 2 * math.pi * i / n, 2 * math.pi * (i + 1) / n
        segs.append(((cx + R * math.cos(a0), cz + R * math.sin(a0)), (cx + R * math.cos(a1), cz + R * math.sin(a1))))
    pts = [(cx - 0.55 * R, cz + 0.55 * R), (cx, cz - 0.75 * R), (cx + 0.55 * R, cz + 0.55 * R)]
    segs += [(pts[0], pts[1]), (pts[1], pts[2])]
    segs += [((cx - 0.6 * R, cz + 0.1 * R), (cx + 0.6 * R, cz + 0.1 * R)), ((cx, cz + 0.9 * R), (cx, cz - 0.95 * R)),
             ((cx - 0.3 * R, cz + 0.6 * R), (cx + 0.3 * R, cz + 0.6 * R)),
             ((cx + 0.35 * R, cz - 0.35 * R), (cx + 0.75 * R, cz - 0.1 * R)), ((cx - 0.35 * R, cz - 0.35 * R), (cx - 0.75 * R, cz - 0.1 * R))]
    for (x0, z0), (x1, z1) in segs:
        L = math.hypot(x1 - x0, z1 - z0)
        ang = math.atan2(z1 - z0, x1 - x0)
        mb.box(((x0 + x1) / 2, y, (z0 + z1) / 2), (L + w, w * 0.6, w), (0, -ang, 0))
    for dx in (-0.25, 0, 0.25):
        mb.sphere((cx + dx * R, y, cz - 1.15 * R), w * 1.6, (1, 0.4, 1), segs=(8, 6))


# ------------------------------------------------------------------ props
def p_seance(M):
    occult_mats(M)
    root = root_empty("seance_table")
    mb = MB()
    mb.mi = 0   # table
    mb.lathe([(0.6, 0.74), (0.6, 0.78), (0.001, 0.78)], 40, cap_bottom=True)
    mb.lathe([(0.3, 0.0), (0.26, 0.05), (0.07, 0.12), (0.06, 0.6), (0.12, 0.7), (0.001, 0.72)], 20)
    mb.mi = 1   # velvet cloth draped
    mb.lathe([(0.001, 0.785), (0.64, 0.785), (0.66, 0.7), (0.67, 0.45)], 48,
             rmod=lambda t, z, r, i: r * (1 + (0.04 * math.sin(10 * t) if z < 0.72 else 0)))
    mb.mi = 2   # spirit board
    mb.box((0, 0.0, 0.8), (0.56, 0.38, 0.015))
    mb.mi = 3
    mb.sphere((0.08, -0.04, 0.815), 0.06, (0.8, 1.0, 0.12), segs=(14, 6))   # planchette
    mb.cyl((0.08, -0.04, 0.81), (0.08, -0.04, 0.83), 0.018, segs=10)
    tb = mb.obj("Seance_Table", [M["table_wood"], M["purple_cloth"], M["parchment"], M["table_wood"]])
    tb.parent = root
    rows = [("A B C D E F G H I J K L M", 0.07), ("N O P Q R S T U V W X Y Z", 0.0), ("1 2 3 4 5 6 7 8 9 0", -0.07)]
    for s, y in rows:
        t = text_mesh(s, 0.04, 0.001, M["ink"], (0, y, 0.8085), (0, 0, 0), name="Board_Text")
        t.parent = root
    for s, x in (("YES", -0.2), ("NO", 0.2)):
        t = text_mesh(s, 0.045, 0.001, M["ink"], (x, 0.14, 0.8085), (0, 0, 0), name="Board_YesNo"); t.parent = root
    t = text_mesh("GOODBYE", 0.04, 0.001, M["ink"], (0, -0.15, 0.8085), (0, 0, 0), name="Board_Bye"); t.parent = root
    w, f = MB(), MB()
    for i, (x, y) in enumerate([(-0.42, 0.25), (0.45, 0.2), (-0.3, -0.38), (0.36, -0.36), (0.0, 0.42)]):
        candle(w, f, x, y, 0.785, 0.12 + 0.07 * (i % 3), 0.025)
    w.obj("Seance_Candles", [M["black_wax"]]).parent = root
    f.obj("Seance_Flames", [M["flame"]]).parent = root
    ch = MB(); ch.smooth = False
    for a in (0, 90, 180, 270):
        r = math.radians(a)
        cx, cy = 0.95 * math.sin(r), -0.95 * math.cos(r)
        R = Matrix.Rotation(r, 4, "Z")
        def P(p): return tuple((R @ V(p)).to_3d() + V((cx, cy, 0)))
        ch.box(P((0, 0, 0.46)), (0.42, 0.42, 0.04), (0, 0, r))
        for sx in (-1, 1):
            for sy in (-1, 1):
                ch.box(P((0.18 * sx, 0.18 * sy, 0.23)), (0.035, 0.035, 0.46), (0, 0, r))
        ch.box(P((0, -0.19, 0.95)), (0.42, 0.04, 0.1), (0, 0, r))
        for sx in (-0.14, 0, 0.14):
            ch.box(P((sx, -0.19, 0.7)), (0.03, 0.03, 0.48), (0, 0, r))
    ch.obj("Seance_Chairs", [M["table_wood"]]).parent = root
    return {"name": "Séance table", "cat": CAT, "behaviors": ["flicker"],
            "light": {"type": "point", "color": "#ff9a3c", "intensity": 3, "offset": [0, 1.05, 0]},
            "desc": "Velvet-draped table with a spirit board, planchette, black candles and four empty chairs."}


def p_pentagram(M):
    occult_mats(M)
    root = root_empty("ritual_circle")
    mb = MB()
    R = 1.6
    mb.mi = 0
    for rr in (R, R * 0.92):
        mb.torus((0, 0, 0.012), rr, 0.012, (1, 1, 0.4), segs=(96, 4))
    pts = [V((R * 0.9 * math.cos(math.radians(-90 + 72 * i)), R * 0.9 * math.sin(math.radians(-90 + 72 * i)), 0.012)) for i in range(5)]
    for i in range(5):   # inverted star (one point toward -Y, the front)
        a, b = pts[i], pts[(i + 2) % 5]
        L = (b - a).length
        ang = math.atan2(b.y - a.y, b.x - a.x)
        mb.box((a + b) / 2, (L, 0.03, 0.01), (0, 0, ang))
    for i in range(24):   # tick glyphs between the rings
        a = 2 * math.pi * i / 24
        mb.box((R * 0.96 * math.cos(a), R * 0.96 * math.sin(a), 0.012), (0.08 if i % 3 else 0.12, 0.012, 0.01), (0, 0, a + (0.6 if i % 2 else -0.6)))
    mb.obj("Ritual_Lines", [M["sigil"]]).parent = root
    w, f = MB(), MB()
    for i, p in enumerate(pts):
        candle(w, f, p.x * 1.12, p.y * 1.12, 0.0, 0.22 + 0.06 * (i % 2), 0.04)
    w.obj("Circle_Candles", [M["black_wax"]]).parent = root
    f.obj("Circle_Flames", [M["flame"]]).parent = root
    return {"name": "Ritual circle", "cat": CAT, "behaviors": ["pulse"],
            "light": {"type": "point", "color": "#ff1a0a", "intensity": 4, "offset": [0, 0.3, 0]},
            "desc": "3 m glowing inverted star in a double ring, a black candle on each point."}


def cultist(M, pid, name, robe, arms="clasped", kneel=False, head=True, desc=""):
    occult_mats(M)
    root = root_empty(pid)
    mb = MB()
    robe_figure(mb, None, 1.78, kneel=kneel, arms=arms, head=head)
    mb.obj(pid.title(), [M[robe], M["void"], M["skin_pale"]]).parent = root
    return {"name": name, "cat": CAT, "behaviors": ["sway_body"], "desc": desc}


def p_cultist(M):
    return cultist(M, "cultist", "Hooded cultist", "robe_black",
                   desc="Faceless figure in a black robe, hands clasped. Place them in a ring.")


def p_cultist_red(M):
    return cultist(M, "cultist_crimson", "Crimson acolyte", "robe_red", arms="raised",
                   desc="Crimson-robed acolyte with both arms raised.")


def p_kneeler(M):
    return cultist(M, "kneeling_acolyte", "Kneeling acolyte", "robe_black", arms="out", kneel=True,
                   desc="Bowed, kneeling worshipper, arms spread low.")


def p_headless(M):
    return cultist(M, "headless_worshipper", "Headless worshipper", "robe_white", arms="clasped", kneel=True, head=False,
                   desc="Kneeling robed figure with nothing above the collar. No gore, just absence.")


def p_levitating(M):
    occult_mats(M)
    root = root_empty("levitating_woman")
    C = bpy.context.scene.collection
    body, hz = BP.mannequin("Levitating_Body", C, M, (0, 0, 0), 0, 1.7, "long", dress="gown", hair_mat="hair", gown=True)
    piv = empty("Levitate_Pivot", (0, 0, 0), None, 0.2)
    piv.parent = root
    body.parent = piv
    body.rotation_euler = (math.radians(-90), 0, 0)   # lying face-up, head toward +Y
    body.location = (0, -0.85, 2.3)
    # gown hem hanging + hair falling toward the ground
    mb = MB()
    mb.mi = 0
    for i in range(9):
        x = -0.15 + i * 0.04
        mb.cyl((x, -0.55, 2.25), (x * 1.1, -0.6, 1.95 - 0.1 * (i % 3)), 0.03, 0.01, segs=6)
    mb.mi = 1
    for i in range(12):
        x = -0.1 + i * 0.018
        mb.cyl((x, 0.85, 2.3), (x * 1.4, 0.9, 1.55 + 0.08 * (i % 4)), 0.012, 0.004, segs=5)
    mb.obj("Levitating_Drapes", [M["gown"], M["hair"]]).parent = piv
    return {"name": "Levitating woman", "cat": CAT, "behaviors": ["levitate"],
            "desc": "Nightgowned figure floating face-up at 2.3 m, hair hanging toward the lawn."}


def p_altar(M):
    occult_mats(M)
    root = root_empty("black_altar")
    mb = MB(); mb.smooth = False
    mb.box((0, 0, 0.45), (1.3, 0.6, 0.9))
    mb.box((0, 0, 0.93), (1.42, 0.7, 0.06))
    mb.mi = 1
    mb.box((0, -0.18, 0.75), (1.0, 0.02, 0.4))        # hanging cloth
    mb.smooth = True
    mb.mi = 2
    mb.lathe([(0.06, 0.96), (0.05, 0.98), (0.012, 1.02), (0.012, 1.1), (0.05, 1.14), (0.06, 1.22)], 20, (0.38, -0.05, 0), cap_bottom=True)
    mb.mi = 3
    mb.box((-0.25, -0.15, 0.967), (0.34, 0.035, 0.006), (0, 0, 0.3))   # athame blade
    mb.mi = 0
    mb.box((-0.08, -0.2, 0.972), (0.11, 0.025, 0.018), (0, 0, 0.3))
    mb.mi = 4   # open book
    for s in (-1, 1):
        mb.box((0.0 + s * 0.11, 0.12, 0.98), (0.22, 0.3, 0.012), (0, s * 0.12, 0))
    mb.mi = 5
    sigil_lines(mb, 0, 0.75, 0.12, -0.195, w=0.008, seed=3)
    mb.obj("Altar", [M["altar_stone"], M["robe_black"], M["gold"], M["iron"], M["parchment"], M["sigil"]]).parent = root
    # goat skull with swept-back horns
    gs = MB()
    gs.sphere((0, 0.12, 1.08), 0.07, (0.85, 1.0, 0.85))
    gs.cyl((0, 0.08, 1.06), (0, -0.12, 1.0), 0.05, 0.025, segs=10)
    gs.mi = 1
    for sx in (-1, 1):
        gs.sphere((0.04 * sx, 0.05, 1.1), 0.018)
    gs.obj("Goat_Skull", [M["bone_real"], M["eye_red"]]).parent = root
    horns = []
    for sx in (-1, 1):
        pts = []
        for i in range(9):
            t = i / 8
            a = t * 2.2
            pts.append(((sx * (0.04 + 0.1 * t), 0.15 + 0.15 * math.sin(a) , 1.12 + 0.15 * math.cos(a) - 0.02), 1 - 0.85 * t))
        horns.append(pts)
    tube_curve("Goat_Horns", horns, bevel=0.03, mats=[M["ramhorn"]]).parent = root
    w, f = MB(), MB()
    for i, x in enumerate((-0.6, -0.48, 0.5, 0.62)):
        candle(w, f, x, 0.15 - 0.1 * (i % 2), 0.96, 0.25 + 0.1 * (i % 2), 0.035)
    w.obj("Altar_Candles", [M["black_wax"]]).parent = root
    f.obj("Altar_Flames", [M["flame"]]).parent = root
    return {"name": "Black altar", "cat": CAT, "behaviors": ["flicker"],
            "light": {"type": "point", "color": "#ff8a30", "intensity": 3, "offset": [0, 1.4, 0.2]},
            "desc": "Stone altar: goat skull, gold chalice, ritual dagger, open grimoire, black tapers."}


def p_goat_idol(M):
    occult_mats(M)
    root = root_empty("horned_idol")
    mb = MB(); mb.smooth = False
    mb.box((0, 0, 0.3), (1.1, 0.9, 0.6))
    mb.box((0, 0, 0.62), (1.2, 1.0, 0.05))
    mb.smooth = True
    mb.mi = 1   # seated robed body
    mb.lathe([(0.42, 0.64), (0.4, 0.8), (0.32, 1.1), (0.28, 1.5), (0.32, 1.65), (0.12, 1.75)], 28, cap_top=True, scale=(1, 0.8))
    for sx in (-1, 1):
        mb.cyl((0.18 * sx, -0.02, 0.9), (0.2 * sx, -0.45, 0.9), 0.13, 0.12, segs=14)       # knees/thighs
        mb.cyl((0.3 * sx, 0, 1.6), (0.48 * sx, -0.1, 1.25), 0.09, 0.08, segs=12)            # upper arm
        mb.cyl((0.48 * sx, -0.1, 1.25), (0.42 * sx, -0.45, 1.05 if sx > 0 else 1.5), 0.08, 0.07, segs=12)
    mb.mi = 2   # goat head
    mb.sphere((0, -0.02, 1.95), 0.15, (0.85, 1.0, 1.0), segs=(18, 12))
    mb.cyl((0, -0.06, 1.93), (0, -0.33, 1.82), 0.1, 0.055, segs=14)
    mb.cyl((0, -0.25, 1.78), (0, -0.25, 1.62), 0.03, 0.01, segs=8)                           # beard
    for sx in (-1, 1):
        mb.cyl((0.14 * sx, 0.0, 1.98), (0.3 * sx, 0.03, 1.92), 0.04, 0.01, segs=8)            # ears
    mb.mi = 3
    for sx in (-1, 1):
        mb.sphere((0.07 * sx, -0.14, 2.0), 0.025)
    mb.mi = 4   # candle flame between the horns
    mb.sphere((0, 0.02, 2.28), 0.03, (0.7, 0.7, 2.0))
    mb.mi = 5
    mb.cyl((0, 0.02, 2.1), (0, 0.02, 2.25), 0.025, segs=10)
    mb.mi = 6
    sigil_lines(mb, 0, 0.32, 0.18, -0.452, w=0.012, seed=9)
    mb.obj("Horned_Idol", [M["altar_stone"], M["robe_black"], M["goat_fur"], M["eye_red"], M["flame"], M["black_wax"], M["sigil"]]).parent = root
    horns = []
    for sx in (-1, 1):
        horns.append([((sx * (0.07 + 0.22 * t), 0.02 + 0.12 * t, 2.05 + 0.32 * t - 0.12 * t * t), 1 - 0.85 * t) for t in [i / 7 for i in range(8)]])
    tube_curve("Idol_Horns", horns, bevel=0.045, mats=[M["ramhorn"]]).parent = root
    return {"name": "Horned idol", "cat": CAT, "behaviors": ["pulse"],
            "light": {"type": "point", "color": "#ff6a2a", "intensity": 2.5, "offset": [0, 2.35, 0]},
            "desc": "Enthroned goat-headed effigy, one hand raised and one lowered, a flame burning between its horns."}


def p_banner(M):
    occult_mats(M)
    root = root_empty("sigil_banner")
    mb = MB()
    mb.mi = 0
    mb.cyl((0, 0.03, 0), (0, 0.03, 2.9), 0.03, segs=8)
    mb.cyl((-0.55, 0.03, 2.75), (0.55, 0.03, 2.75), 0.02, segs=8)
    for x in (-0.55, 0.55):
        mb.sphere((x, 0.03, 2.75), 0.035)
    mb.sphere((0, 0.03, 2.92), 0.05)
    mb.mi = 1
    mb.smooth = False
    # cloth with a swallowtail hem, slightly rippled
    cols, rows = 10, 14
    vs = []
    for j in range(rows + 1):
        z = 2.73 - 1.7 * j / rows
        row = []
        for i in range(cols + 1):
            x = -0.5 + i / cols
            hem = 0.25 * (1 - abs(x) * 2) if j == rows else 0
            row.append(mb.bm.verts.new((x, 0.0 + 0.02 * math.sin(i * 1.3 + j * 0.7), z + hem * (j / rows))))
        vs.append(row)
    for j in range(rows):
        for i in range(cols):
            mb.bm.faces.new((vs[j][i], vs[j][i + 1], vs[j + 1][i + 1], vs[j + 1][i]))
    mb._tag([v for r in vs for v in r])
    mb.mi = 2
    sigil_lines(mb, 0, 2.05, 0.33, -0.03, w=0.02, seed=1)
    mb.obj("Sigil_Banner", [M["iron"], M["robe_red"], M["sigil"]]).parent = root
    return {"name": "Sigil banner", "cat": CAT, "behaviors": ["pulse", "swing"],
            "desc": "Crimson swallowtail banner bearing a glowing invented sigil."}


def p_wall_sigil(M):
    occult_mats(M)
    root = root_empty("wall_sigil")
    mb = MB()
    sigil_lines(mb, 0, 0.0, 0.45, -0.005, w=0.035, seed=5)
    for i in range(14):   # paint drips
        x = random.Random(i).uniform(-0.4, 0.4)
        mb.cyl((x, -0.006, -0.1), (x, -0.006, -0.25 - 0.3 * random.Random(i + 9).random()), 0.008, 0.003, segs=5)
    mb.obj("Wall_Sigil", [M["sigil_paint"]]).parent = root
    return {"name": "Painted sigil", "cat": CAT, "decal": True, "behaviors": ["pulse"],
            "desc": "Dripping red glyph that sticks flat to whatever you click: siding, door, porch floor."}


def p_black_candles(M):
    occult_mats(M)
    root = root_empty("black_candles")
    rnd = random.Random(21)
    w, f = MB(), MB()
    for i in range(19):
        a, r = rnd.uniform(0, 6.28), rnd.uniform(0, 0.5)
        candle(w, f, r * math.cos(a), r * math.sin(a), 0, rnd.uniform(0.12, 0.6), rnd.uniform(0.025, 0.05), rnd.randint(2, 5), rnd)
    w.mi = 0
    w.lathe([(0.001, 0.0), (0.62, 0.0), (0.6, 0.01)], 32)   # wax pool
    w.obj("Black_Candles", [M["black_wax"]]).parent = root
    f.obj("Black_Candle_Flames", [M["flame"]]).parent = root
    return {"name": "Black candle cluster", "cat": CAT, "behaviors": ["flicker"],
            "light": {"type": "point", "color": "#ffa040", "intensity": 3, "offset": [0, 0.8, 0]},
            "desc": "Nineteen dripping black candles in a pool of wax."}


def p_dollhouse(M):
    occult_mats(M)
    root = root_empty("miniature_house")
    mb = MB(); mb.smooth = False
    mb.mi = 0   # workbench
    mb.box((0, 0, 0.78), (1.3, 0.75, 0.05))
    for sx in (-1, 1):
        for sy in (-1, 1):
            mb.box((0.6 * sx, 0.32 * sy, 0.38), (0.06, 0.06, 0.76))
    mb.mi = 1   # cutaway house: back + sides + floors + roof, open front (-Y)
    W, D, H = 1.0, 0.5, 0.36
    z0 = 0.805
    mb.box((0, D / 2, z0 + H), (W, 0.02, 2 * H))
    for x in (-W / 2, W / 2):
        mb.box((x, 0, z0 + H), (0.02, D, 2 * H))
    for z in (z0, z0 + H, z0 + 2 * H):
        mb.box((0, 0, z), (W, D, 0.02))
    mb.box((0, 0, z0 + H / 2), (0.02, D, H))
    mb.box((0.15, 0, z0 + 1.5 * H), (0.02, D, H))
    mb.mi = 2
    for s in (-1, 1):   # roof
        mb.box((s * W / 4, 0, z0 + 2 * H + 0.12), (W / 2 * 1.18, D + 0.06, 0.02), (0, s * 0.45, 0))
    mb.mi = 3   # tiny lamps
    for (x, z) in ((-0.25, z0 + 0.3), (0.3, z0 + 0.3), (-0.2, z0 + H + 0.3), (0.33, z0 + H + 0.3)):
        mb.sphere((x, 0.1, z), 0.018)
    mb.mi = 4   # furniture
    mb.box((-0.3, 0.05, z0 + 0.05), (0.18, 0.12, 0.08))
    mb.box((0.25, 0.1, z0 + 0.06), (0.25, 0.14, 0.1))
    mb.box((-0.2, 0.08, z0 + H + 0.05), (0.2, 0.25, 0.08))
    mb.box((0.33, 0.1, z0 + H + 0.08), (0.1, 0.06, 0.14))
    mb.smooth = True
    mb.mi = 5   # tiny figures (one in each room, all facing out)
    for (x, z) in ((-0.32, z0), (0.22, z0), (-0.12, z0 + H), (0.34, z0 + H)):
        mb.cyl((x, -0.05, z + 0.01), (x, -0.05, z + 0.09), 0.018, 0.012, segs=8)
        mb.sphere((x, -0.05, z + 0.11), 0.016)
    mb.obj("Miniature_House", [M["table_wood"], M["house_wall"], M["roof"] if "roof" in M else M["robe_black"],
                                M["mini_lit"], M["wood_dark"], M["skin_pale"]]).parent = root
    return {"name": "Miniature house", "cat": CAT,
            "light": {"type": "point", "color": "#ffb070", "intensity": 0.8, "offset": [0, 1.2, 0.1]},
            "desc": "Open-front dollhouse on a workbench: lit rooms, tiny furniture, a small still figure in every room."}


def p_inverted_cross(M):
    occult_mats(M)
    root = root_empty("inverted_cross")
    mb = MB(); mb.smooth = False
    mb.box((0, 0, 1.2), (0.12, 0.12, 2.4))
    mb.box((0, 0, 0.75), (0.85, 0.12, 0.12))
    mb.box((0, 0, 0.05), (0.5, 0.5, 0.1))
    mb.smooth = True
    w, f = MB(), MB()
    for i, (x, y) in enumerate(((-0.2, -0.32), (0.2, -0.32), (-0.35, -0.12), (0.35, -0.12))):
        candle(w, f, x, y, 0.0, 0.25 + 0.08 * i, 0.035)
    mb.obj("Inverted_Cross", [M["table_wood"]]).parent = root
    w.obj("Cross_Candles", [M["black_wax"]]).parent = root
    f.obj("Cross_Flames", [M["flame"]]).parent = root
    return {"name": "Inverted cross", "cat": CAT, "behaviors": ["flicker"],
            "light": {"type": "point", "color": "#ff9040", "intensity": 1.5, "offset": [0, 0.6, 0.3]},
            "desc": "2.4 m upside-down timber cross with black tapers at its foot."}


def p_wicker(M):
    occult_mats(M)
    root = root_empty("wicker_effigy")
    splines = []
    rnd = random.Random(7)
    def limb(a, b, n=5):
        for _ in range(n):
            j = V((rnd.uniform(-0.04, 0.04), rnd.uniform(-0.04, 0.04), rnd.uniform(-0.04, 0.04)))
            splines.append([(tuple(V(a) + j), 1.0), (tuple((V(a) + V(b)) / 2 + j * 2), 0.9), (tuple(V(b) + j), 0.7)])
    limb((0.15, 0, 0.0), (0.12, 0, 1.0)); limb((-0.15, 0, 0.0), (-0.12, 0, 1.0))
    limb((0, 0, 0.95), (0, 0, 1.8), 7)
    limb((0, 0, 1.65), (0.6, 0, 1.25)); limb((0, 0, 1.65), (-0.6, 0, 1.25))
    for i in range(6):   # ribs of the torso
        z = 1.05 + i * 0.12
        a = [(0.22 * math.cos(t), 0.14 * math.sin(t), z) for t in [k * 0.9 for k in range(8)]]
        splines.append([(p, 0.6) for p in a])
    head = [(0.12 * math.cos(t), 0.12 * math.sin(t) * 0.8, 1.95 + 0.1 * math.sin(t * 2)) for t in [k * 0.8 for k in range(9)]]
    splines.append([(p, 0.6) for p in head])
    tube_curve("Wicker_Effigy", splines, bevel=0.018, mats=[M["wicker"]], res=2).parent = root
    mb = MB()
    mb.mi = 0   # crown
    for i in range(7):
        a = 2 * math.pi * i / 7
        mb.cyl((0.12 * math.cos(a), 0.1 * math.sin(a), 2.03), (0.14 * math.cos(a), 0.12 * math.sin(a), 2.18), 0.012, 0.002, segs=5)
    mb.torus((0, 0, 2.04), 0.12, 0.012, (1, 0.85, 1), segs=(20, 5))
    mb.mi = 1   # fire at the base
    for i in range(9):
        a = rnd.uniform(0, 6.28); r = rnd.uniform(0, 0.25)
        mb.cyl((r * math.cos(a), r * math.sin(a), 0.0), (r * math.cos(a) * 0.6, r * math.sin(a) * 0.6, rnd.uniform(0.3, 0.6)), 0.08, 0.005, segs=8)
    mb.mi = 2
    mb.sphere((0, 0, 0.03), 0.4, (1, 1, 0.12))
    mb.obj("Effigy_Fire_Crown", [M["gold"], M["fire"], M["coal"]]).parent = root
    return {"name": "Burning wicker effigy", "cat": CAT, "behaviors": ["flicker"],
            "light": {"type": "point", "color": "#ff6a1a", "intensity": 8, "offset": [0, 0.6, 0]},
            "desc": "Crowned stick-man effigy smouldering on a bed of coals."}


def p_crown_jar(M):
    occult_mats(M)
    root = root_empty("crown_under_glass")
    mb = MB()
    mb.mi = 0
    mb.lathe([(0.22, 0.0), (0.2, 0.05), (0.07, 0.12), (0.06, 0.95), (0.2, 1.0), (0.22, 1.04), (0.001, 1.04)], 24, cap_bottom=True)
    mb.mi = 1   # bell jar
    mb.lathe([(0.17, 1.04), (0.17, 1.35), (0.14, 1.45), (0.06, 1.49), (0.03, 1.53), (0.001, 1.55)], 32)
    mb.mi = 2   # pointed crown
    mb.lathe([(0.075, 1.05), (0.075, 1.1)], 24)
    for i in range(8):
        a = 2 * math.pi * i / 8
        mb.cyl((0.075 * math.cos(a), 0.075 * math.sin(a), 1.09), (0.07 * math.cos(a), 0.07 * math.sin(a), 1.18), 0.016, 0.002, segs=5)
    mb.mi = 3
    mb.sphere((0, -0.074, 1.075), 0.012)
    mb.obj("Crown_Under_Glass", [M["table_wood"], M["glass"], M["gold"], M["eye_red"]]).parent = root
    return {"name": "Crown under glass", "cat": CAT, "desc": "A small gold crown kept under a bell jar on a plinth. Waiting for a head."}


def p_poppets(M):
    occult_mats(M)
    root = root_empty("hanging_poppets")
    mb = MB()
    mb.mi = 0   # gnarled frame
    mb.cyl((-0.9, 0, 0), (-0.85, 0, 2.3), 0.05, 0.035, segs=8)
    mb.cyl((0.9, 0, 0), (0.85, 0, 2.3), 0.05, 0.035, segs=8)
    mb.cyl((-0.95, 0, 2.25), (0.95, 0, 2.28), 0.04, segs=8)
    rnd = random.Random(2)
    for i in range(5):
        x = -0.6 + i * 0.3
        L = rnd.uniform(0.3, 0.7)
        top = 2.25 - L
        mb.mi = 1
        mb.cyl((x, 0, 2.25), (x, 0, top), 0.003, segs=4)
        mb.mi = 2   # poppet: stuffed body, round head, button eyes, stitched X mouth
        mb.sphere((x, 0, top - 0.06), 0.05)
        mb.cyl((x, 0, top - 0.1), (x, 0, top - 0.3), 0.045, 0.06, segs=10)
        for sx in (-1, 1):
            mb.cyl((x + 0.03 * sx, 0, top - 0.13), (x + 0.1 * sx, 0, top - 0.22), 0.016, segs=6)
            mb.cyl((x + 0.025 * sx, 0, top - 0.29), (x + 0.03 * sx, 0, top - 0.4), 0.02, segs=6)
        mb.mi = 3
        for sx in (-1, 1):
            mb.sphere((x + 0.018 * sx, -0.045, top - 0.05), 0.009, (1, 0.4, 1))
        mb.box((x, -0.048, top - 0.085), (0.03, 0.004, 0.004), (0, 0.7, 0))
        mb.box((x, -0.048, top - 0.085), (0.03, 0.004, 0.004), (0, -0.7, 0))
        mb.mi = 4
        mb.box((x, -0.04, top - 0.18), (0.006, 0.01, 0.07))   # iron nail through the chest
    mb.obj("Hanging_Poppets", [M["bark"], M["twine"], M["doll_cloth"], M["ink"], M["iron"]]).parent = root
    return {"name": "Hanging poppets", "cat": CAT, "behaviors": ["swing"],
            "desc": "Five muslin poppets with button eyes and nails through their chests, dangling from a gnarled frame."}


def p_mirror(M):
    occult_mats(M)
    root = root_empty("shrouded_mirror")
    mb = MB()
    mb.mi = 0
    mb.torus((0, 0, 1.15), 0.42, 0.04, (0.8, 1, 1.35), (math.radians(90), 0, 0), segs=(40, 8))
    for sx in (-1, 1):
        mb.cyl((0.36 * sx, 0.05, 0.0), (0.33 * sx, 0.04, 1.0), 0.03, segs=8)
    mb.cyl((-0.4, 0.05, 0.02), (0.4, 0.05, 0.02), 0.03, segs=8)
    mb.mi = 1
    mb.sphere((0, 0.01, 1.15), 0.4, (0.8, 0.02, 1.33), segs=(32, 12))
    mb.mi = 2   # black shroud thrown over the top half
    mb.lathe([(0.001, 1.74), (0.3, 1.7), (0.4, 1.6), (0.43, 1.45), (0.44, 1.3)], 28,
             rmod=lambda t, z, r, i: r * (1 + 0.07 * math.sin(6 * t + z * 4)), scale=(1, 0.16))
    mb.obj("Shrouded_Mirror", [M["gold"], M["mirror"], M["robe_black"]]).parent = root
    return {"name": "Shrouded mirror", "cat": CAT,
            "desc": "Gilt standing mirror half-covered with black cloth, as is done in a house of mourning."}


OCCULT = {
    "seance_table": p_seance, "ritual_circle": p_pentagram, "cultist": p_cultist, "cultist_crimson": p_cultist_red,
    "kneeling_acolyte": p_kneeler, "headless_worshipper": p_headless, "levitating_woman": p_levitating,
    "black_altar": p_altar, "horned_idol": p_goat_idol, "sigil_banner": p_banner, "wall_sigil": p_wall_sigil,
    "black_candles": p_black_candles, "miniature_house": p_dollhouse, "inverted_cross": p_inverted_cross,
    "wicker_effigy": p_wicker, "crown_under_glass": p_crown_jar, "hanging_poppets": p_poppets,
    "shrouded_mirror": p_mirror,
}
