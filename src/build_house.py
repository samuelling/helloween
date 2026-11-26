"""House, porch, steps and ground for the left half of the two-family house."""
import math, random
from mathutils import Vector as V, Matrix, Euler
from lib import *

# ------------------------------------------------------------------ dimensions (m)
HX0, HX1 = -6.6, 6.6        # main house width
HD = 10.0                   # depth
PORCH_Z = 1.1               # porch floor top
PX0, PX1 = -6.6, 7.4        # porch extent
PY = -2.7                   # porch front edge
EAVE_Z = 7.45
PITCH = math.radians(38)
COLS_X = [-6.4, -1.4, 1.5, 4.1, 7.2]
STAIR_X = (-0.3, 4.1)
RISE, TREAD, N_TREADS = 0.22, 0.30, 4


def materials():
    M = {}
    M["siding"] = mat("Siding_White", (0.78, 0.79, 0.80), 0.6)
    wave_bump(M["siding"], 2.62, "Z", "SAW", 0.6, 0.012)
    M["trim"] = mat("Trim_White", (0.85, 0.85, 0.84), 0.45)
    M["shutter"] = mat("Shutter_Red", (0.30, 0.035, 0.03), 0.5)
    wave_bump(M["shutter"], 9.0, "Z", "SAW", 0.8, 0.01)
    M["bracket"] = mat("Bracket_Red", (0.45, 0.04, 0.03), 0.45)
    M["roof"] = mat("Roof_Shingle", (0.035, 0.035, 0.038), 0.85)
    wave_bump(M["roof"], 2.0, "Z", "SAW", 0.5, 0.02)
    M["porch_floor"] = mat("Porch_Floor_Paint", (0.22, 0.07, 0.05), 0.55)
    wave_bump(M["porch_floor"], 7.0, "X", "SIN", 0.3, 0.004)
    M["ceiling"] = mat("Porch_Ceiling_Beadboard", (0.20, 0.09, 0.04), 0.45)
    wave_bump(M["ceiling"], 7.0, "X", "SIN", 0.4, 0.004)
    M["door"] = mat("Door_Honey_Wood", (0.45, 0.22, 0.08), 0.4, coat=0.3)
    M["door_dark"] = mat("Door_Dark_Wood", (0.12, 0.06, 0.035), 0.4)
    M["chimney"] = mat("Chimney_Brick_Dark", (0.06, 0.05, 0.05), 0.9)
    noise_bump(M["chimney"], 30, 0.4)
    M["lattice"] = lattice_mat()
    M["foundation"] = mat("Foundation_Stone", (0.12, 0.11, 0.10), 0.9)
    noise_bump(M["foundation"], 8, 0.6)
    M["concrete"] = mat("Concrete", (0.30, 0.29, 0.28), 0.85)
    noise_color(M["concrete"], (0.22, 0.21, 0.20), (0.34, 0.33, 0.32), 9)
    M["asphalt"] = mat("Asphalt", (0.035, 0.035, 0.04), 0.9)
    noise_bump(M["asphalt"], 60, 0.5)
    M["granite"] = mat("Curb_Granite", (0.25, 0.25, 0.26), 0.7)
    M["mulch"] = mat("Mulch", (0.05, 0.03, 0.02), 0.95)
    noise_color(M["mulch"], (0.025, 0.015, 0.01), (0.09, 0.05, 0.03), 18)
    noise_bump(M["mulch"], 40, 0.8)
    M["grass"] = mat("Grass_Night", (0.04, 0.05, 0.025), 0.95)
    noise_color(M["grass"], (0.03, 0.04, 0.02), (0.08, 0.07, 0.035), 12)
    M["plant"] = mat("Plant_Dark", (0.03, 0.06, 0.03), 0.7)
    M["basket"] = mat("Wicker", (0.25, 0.15, 0.07), 0.8)
    M["glass_frame"] = M["trim"]
    # interiors (seen through windows)
    M["int_warm"] = interior_mat("Interior_Warm", (1.0, 0.72, 0.42), 2.5)
    M["int_red"] = interior_mat("Interior_Red", (1.0, 0.18, 0.12), 2.5)
    M["int_blue"] = interior_mat("Interior_TV_Blue", (0.25, 0.45, 1.0), 1.6)
    M["int_dim"] = interior_mat("Interior_Dim", (0.45, 0.42, 0.40), 0.7)
    M["int_dark"] = interior_mat("Interior_Dark", (0.08, 0.08, 0.1), 0.3)
    return M


def lattice_mat():
    m = mat("Lattice_Skirt", (0.75, 0.75, 0.74), 0.6)
    nt = m.node_tree
    tc = tex_coord(m)
    outs = []
    for ang in (45, -45):
        mp = nt.nodes.new("ShaderNodeMapping")
        mp.inputs["Rotation"].default_value = (0, math.radians(ang), 0)
        nt.links.new(tc, mp.inputs["Vector"])
        w = nt.nodes.new("ShaderNodeTexWave")
        w.wave_type = "BANDS"; w.bands_direction = "X"; w.wave_profile = "SAW"
        w.inputs["Scale"].default_value = 1.3
        nt.links.new(mp.outputs["Vector"], w.inputs["Vector"])
        outs.append(w)
    mx = nt.nodes.new("ShaderNodeMath"); mx.operation = "MINIMUM"
    nt.links.new(outs[0].outputs["Fac"], mx.inputs[0])
    nt.links.new(outs[1].outputs["Fac"], mx.inputs[1])
    gt = nt.nodes.new("ShaderNodeMath"); gt.operation = "GREATER_THAN"
    gt.inputs[1].default_value = 0.72
    nt.links.new(mx.outputs[0], gt.inputs[0])
    mixc = nt.nodes.new("ShaderNodeMix"); mixc.data_type = "RGBA"
    mixc.inputs[6].default_value = (0.75, 0.75, 0.74, 1)
    mixc.inputs[7].default_value = (0.01, 0.01, 0.01, 1)
    nt.links.new(gt.outputs[0], mixc.inputs[0])
    nt.links.new(mixc.outputs[2], nt.nodes["Principled BSDF"].inputs["Base Color"])
    return m


# --------------------------------------------------------------- window helper
class Face:
    """Local frame on a wall: u = along wall, v = up, n = outward normal."""
    def __init__(self, origin, u, n):
        self.o, self.u, self.n = V(origin), V(u).normalized(), V(n).normalized()
        self.v = V((0, 0, 1))
        self.rot = Matrix((self.u, self.n, self.v)).transposed().to_euler()

    def p(self, a, b, d=0.0):
        return self.o + self.u * a + self.v * b + self.n * d


def window(trim, inter, face, cu, cz, w, h, panes=(1, 2), int_mi=0, sill=True, depth=0.06):
    """Frame + muntins into `trim`, glowing interior quad into `inter` (material index int_mi)."""
    t = 0.09
    # interior quad
    inter.mi = int_mi
    a0, a1, b0, b1 = cu - w / 2, cu + w / 2, cz - h / 2, cz + h / 2
    inter.quad([face.p(a0, b0, 0.012), face.p(a1, b0, 0.012), face.p(a1, b1, 0.012),
                face.p(a0, b1, 0.012)])
    # casing
    for (cc, sz) in [((cu, b1 + t / 2), (w + 2 * t, t)), ((cu, b0 - t / 2), (w + 2 * t, t)),
                     ((a0 - t / 2, cz), (t, h)), ((a1 + t / 2, cz), (t, h))]:
        trim.box(face.p(cc[0], cc[1], depth / 2), (sz[0], depth, sz[1]), face.rot)
    if sill:
        trim.box(face.p(cu, b0 - t - 0.02, 0.06), (w + 2 * t + 0.1, 0.12, 0.04), face.rot)
    # sash split + muntins
    cols, rows = panes
    for i in range(1, cols):
        x = a0 + w * i / cols
        trim.box(face.p(x, cz, 0.03), (0.025, 0.03, h), face.rot)
    for j in range(1, rows):
        z = b0 + h * j / rows
        trim.box(face.p(cu, z, 0.035), (w, 0.04 if rows == 2 and j == 1 else 0.025, 0.04), face.rot)


def shutter_pair(sh, face, cu, cz, w, h, gap=0.12):
    for s in (-1, 1):
        sh.box(face.p(cu + s * (w / 2 + gap + w * 0.25), cz, 0.04), (w * 0.5, 0.04, h), face.rot)


# --------------------------------------------------------------- lathe profiles
def turned_post(mb, x, y, z0, z1):
    L = z1 - z0
    prof = [(0.085, 0), (0.085, 0.12), (0.06, 0.14), (0.06, 0.16), (0.075, 0.18), (0.075, 0.30),
            (0.055, 0.33), (0.065, 0.36), (0.05, 0.40)]
    shaft = [(0.05, 0.42), (0.065, 0.55), (0.06, 0.70), (0.055, 0.82), (0.065, 0.87),
             (0.06, 0.90), (0.075, 0.93), (0.075, 0.96), (0.09, 0.985), (0.09, 1.0)]
    profile = [(r, z0 + f * L) for r, f in [(r, f * 1.0) for r, f in
               [(0.085, 0.0), (0.085, 0.06), (0.06, 0.07), (0.075, 0.09), (0.075, 0.16),
                (0.055, 0.18), (0.068, 0.21), (0.05, 0.25), (0.062, 0.40), (0.058, 0.60),
                (0.052, 0.74), (0.066, 0.78), (0.058, 0.81), (0.078, 0.85), (0.078, 0.92),
                (0.095, 0.95), (0.095, 1.0)]]]
    mb.lathe(profile, segs=16, c=(x, y, 0), cap_top=True, cap_bottom=True)


def build_house(C, M):
    rnd = random.Random(117)
    # ---------------- main body (siding)
    body = MB()
    body.smooth = False
    body.box_pts((HX0, 0, 0.9), (HX1, HD, EAVE_Z - 0.3))
    # gable end triangles
    rz = EAVE_Z + (HD / 2 + 0.45) * math.tan(PITCH)
    for x in (HX0, HX1):
        body.quad([(x, 0, EAVE_Z - 0.3), (x, HD, EAVE_Z - 0.3), (x, HD, EAVE_Z), (x, 0, EAVE_Z)])
        vs = [body.bm.verts.new(p) for p in [(x, 0, EAVE_Z), (x, HD, EAVE_Z),
                                              (x, HD / 2, EAVE_Z + HD / 2 * math.tan(PITCH))]]
        body.bm.faces.new(vs if x > 0 else list(reversed(vs)))
    house = body.obj("House_Body", [M["siding"]], C)

    # foundation
    fd = MB(); fd.smooth = False
    fd.box_pts((HX0 - 0.05, -0.05, 0.0), (HX1 + 0.05, HD + 0.05, 0.92))
    fd.obj("House_Foundation", [M["foundation"]], C)

    # ---------------- trim: corner boards, frieze, eaves
    trim = MB(); trim.smooth = False
    for x in (HX0, HX1):
        trim.box_pts((x - 0.12 if x < 0 else x - 0.06, -0.06, 0.9), (x + 0.06 if x < 0 else x + 0.12, 0.08, EAVE_Z))
    trim.box_pts((HX0 - 0.1, -0.1, EAVE_Z - 0.32), (HX1 + 0.1, 0.02, EAVE_Z))      # frieze
    trim.box_pts((HX0 - 0.45, -0.5, EAVE_Z - 0.06), (HX1 + 0.45, 0.0, EAVE_Z + 0.06))  # soffit/fascia
    trim.box_pts((HX0 - 0.45, -0.55, EAVE_Z - 0.06), (HX1 + 0.45, -0.45, EAVE_Z + 0.22))
    trim.box_pts((HX0 - 0.1, -0.08, 4.05), (HX1 + 0.1, 0.0, 4.25))                  # belt at porch roof

    # ---------------- shutters + windows (2nd floor)
    inter = MB(); inter.smooth = False
    sh = MB(); sh.smooth = False
    front = Face((0, 0, 0), (1, 0, 0), (0, -1, 0))
    int_slots = ["int_warm", "int_red", "int_blue", "int_dim", "int_dark"]
    second = [(-3.6, 0), (-0.4, 1), (1.4, 4), (4.4, 0)]
    for x, mi in second:
        window(trim, inter, front, x, 5.6, 0.92, 1.62, (1, 2), mi)
        shutter_pair(sh, front, x, 5.6, 0.92, 1.72)

    # ---------------- first floor (behind porch)
    # bay window: front face + two angled faces
    bx0, bx1, by = -4.3, -2.9, -0.6
    bay = MB(); bay.smooth = False
    pts = [(-4.95, 0.0), (bx0, by), (bx1, by), (-2.25, 0.0)]
    for (x0, y0), (x1, y1) in zip(pts[:-1], pts[1:]):
        vs = [bay.bm.verts.new(p) for p in [(x0, y0, PORCH_Z), (x1, y1, PORCH_Z), (x1, y1, 4.05),
                                              (x0, y0, 4.05)]]
        bay.bm.faces.new(vs)
    bay.box_pts((-4.98, -0.65, 4.0), (-2.22, 0.0, 4.12))
    bay.obj("Bay_Window_Walls", [M["siding"]], C)
    bf = Face((bx0, by, 0), (1, 0, 0), (0, -1, 0))
    window(trim, inter, bf, 0.7, 2.6, 1.22, 2.2, (3, 2), 0)
    for (x0, y0), (x1, y1) in [(pts[0], pts[1]), (pts[2], pts[3])]:
        u = V((x1 - x0, y1 - y0, 0))
        n = V((u.y, -u.x, 0)).normalized()
        f = Face((x0, y0, 0), u, n)
        window(trim, inter, f, u.length / 2, 2.55, 0.5, 2.0, (1, 2), 0)
    shutter_pair(sh, Face((-3.6, 0, 0), (1, 0, 0), (0, -1, 0)), 0, 2.6, 2.75, 2.4, gap=0.05)

    # doors
    dr = MB(); dr.smooth = False
    for cx, mi, glass in [(0.75, 0, True), (2.3, 1, False)]:
        dr.mi = mi
        dr.box((cx, -0.03, PORCH_Z + 1.05), (0.92, 0.06, 2.1))
        if glass:   # 9-lite upper glass
            inter.mi = 0
            inter.quad([(cx - 0.33, -0.065, 2.25), (cx + 0.33, -0.065, 2.25),
                        (cx + 0.33, -0.065, 3.05), (cx - 0.33, -0.065, 3.05)])
            for i in (-1, 1):
                trim.box((cx + i * 0.11, -0.07, 2.65), (0.025, 0.02, 0.8))
                trim.box((cx, -0.07, 2.65 + i * 0.13), (0.66, 0.02, 0.025))
        else:
            dr.box((cx, -0.07, PORCH_Z + 0.55), (0.7, 0.02, 0.7))
            dr.box((cx, -0.07, PORCH_Z + 1.5), (0.7, 0.02, 0.9))
        for i in (-1, 1):   # casing
            trim.box((cx + i * 0.52, -0.04, PORCH_Z + 1.1), (0.12, 0.08, 2.2))
        trim.box((cx, -0.04, PORCH_Z + 2.25), (1.2, 0.08, 0.14))
    dr.obj("Front_Doors", [M["door"], M["door_dark"]], C)

    # right-hand first-floor windows
    for x, mi in [(3.45, 3), (5.5, 0)]:
        window(trim, inter, front, x, 2.6, 0.9, 1.9, (1, 2), mi)
        shutter_pair(sh, front, x, 2.6, 0.9, 2.0)

    # ---------------- dormer
    dx, dw, dy = -0.1, 2.8, 0.3
    dz0, dz1 = 7.2, 9.65
    dapex = dz1 + dw / 2 * math.tan(math.radians(38))
    dm = MB(); dm.smooth = False
    dm.box_pts((dx - dw / 2, dy, dz0), (dx + dw / 2, 4.5, dz1))
    vs = [dm.bm.verts.new(p) for p in [(dx - dw / 2, dy, dz1), (dx + dw / 2, dy, dz1), (dx, dy, dapex)]]
    dm.bm.faces.new(vs)
    dm.obj("Dormer_Body", [M["siding"]], C)
    dface = Face((dx, dy, 0), (1, 0, 0), (0, -1, 0))
    window(trim, inter, dface, -0.62, 8.72, 0.78, 1.28, (1, 2), 0)
    window(trim, inter, dface, 0.62, 8.72, 0.78, 1.28, (1, 2), 4)
    for cu in (-0.62, 0.62):
        sh.box(dface.p(cu + (-0.55 if cu < 0 else 0.55), 8.72, 0.04), (0.3, 0.04, 1.35), dface.rot)
    # dormer roof + gable trim
    rf = MB(); rf.smooth = False
    over = 0.3
    for s in (-1, 1):
        L = (dw / 2 + over) / math.cos(math.radians(38))
        c = V((dx + s * (dw / 4 + over / 2), (dy - 0.25 + 4.5) / 2, (dz1 + dapex) / 2 - 0.05))
        rf.box(c, (L, 4.75 + 0.25, 0.1), (0, s * math.radians(38), 0))
    # main roof
    run = HD / 2 + 0.45
    L = run / math.cos(PITCH)
    for s, yc in ((1, (-0.45 + HD / 2) / 2), (-1, (HD / 2 + HD + 0.45) / 2)):
        rf.box((0, yc, EAVE_Z + run / 2 * math.tan(PITCH) + 0.08), (HX1 - HX0 + 0.9, L, 0.14),
               (s * PITCH, 0, 0))
    roof = rf.obj("Roof", [M["roof"]], C)
    for s in (-1, 1):   # dormer gable fascia
        L = (dw / 2 + 0.1) / math.cos(math.radians(38))
        trim.box((dx + s * dw / 4, dy - 0.28, (dz1 + dapex) / 2 + 0.02), (L, 0.06, 0.16),
                 (0, s * math.radians(38), 0))
    trim.box_pts((dx - dw / 2 - 0.08, dy - 0.3, dz1 - 0.2), (dx + dw / 2 + 0.08, dy, dz1))
    trim.box_pts((dx - dw / 2 - 0.08, dy - 0.06, dz0), (dx - dw / 2 + 0.05, dy + 0.06, dz1))
    trim.box_pts((dx + dw / 2 - 0.05, dy - 0.06, dz0), (dx + dw / 2 + 0.08, dy + 0.06, dz1))

    # chimneys
    ch = MB(); ch.smooth = False
    for cx, cy in [(-4.6, 3.2), (4.1, 6.8)]:
        ch.box_pts((cx - 0.32, cy - 0.45, 9.0), (cx + 0.32, cy + 0.45, 12.6))
        ch.box_pts((cx - 0.38, cy - 0.51, 12.5), (cx + 0.38, cy + 0.51, 12.68))
    ch.obj("Chimneys", [M["chimney"]], C)

    inter.obj("Window_Interiors", [M[k] for k in int_slots], C)
    sh.obj("Shutters", [M["shutter"]], C)
    trim_ob = trim.obj("House_Trim", [M["trim"]], C)
    return house


def build_porch(C, M):
    # floor + skirt
    fl = MB(); fl.smooth = False
    fl.box_pts((PX0, PY, PORCH_Z - 0.14), (PX1, 0.0, PORCH_Z))
    fl.obj("Porch_Floor", [M["porch_floor"]], C)
    lat = MB(); lat.smooth = False
    for x0, x1 in [(PX0, STAIR_X[0]), (STAIR_X[1], PX1)]:
        lat.box_pts((x0, PY + 0.02, 0.0), (x1, PY + 0.05, PORCH_Z - 0.14))
    lat.box_pts((PX0 - 0.03, PY, 0.0), (PX0, 0, PORCH_Z - 0.14))
    lat.obj("Porch_Lattice_Skirt", [M["lattice"]], C)

    trim = MB(); trim.smooth = False
    # skirt framing + floor edge board
    trim.box_pts((PX0 - 0.04, PY - 0.04, PORCH_Z - 0.2), (PX1 + 0.04, PY + 0.03, PORCH_Z + 0.01))
    for x in [PX0, -3.5, STAIR_X[0], STAIR_X[1], PX1]:
        trim.box_pts((x - 0.06, PY - 0.02, 0.0), (x + 0.06, PY + 0.05, PORCH_Z - 0.14))

    # columns
    posts = MB()
    for x in COLS_X:
        turned_post(posts, x, PY + 0.15, PORCH_Z, 3.55)
    posts.obj("Porch_Columns", [M["trim"]], C)

    # roof: beam, ceiling, roof deck
    trim.box_pts((PX0 - 0.1, PY - 0.08, 3.5), (PX1 + 0.1, PY + 0.3, 3.92))       # beam
    trim.box_pts((PX0 - 0.1, PY - 0.3, 3.92), (PX1 + 0.1, PY - 0.08, 4.02))      # drip edge
    trim.box_pts((PX0 - 0.1, PY - 0.08, 3.5), (PX0 + 0.15, 0.0, 3.92))           # side beam
    cl = MB(); cl.smooth = False
    cl.quad([(PX0, 0, 3.72), (PX1, 0, 3.72), (PX1, PY + 0.3, 3.72), (PX0, PY + 0.3, 3.72)][::-1])
    cl.obj("Porch_Ceiling", [M["ceiling"]], C)
    rf = MB(); rf.smooth = False
    rf.box((0.4, (PY - 0.35) / 2, 4.07), (PX1 - PX0 + 0.3, -(PY - 0.35), 0.1),
           (math.radians(-5), 0, 0))
    rf.obj("Porch_Roof", [M["roof"]], C)

    # red scroll brackets at each column (both sides)
    br = MB(); br.smooth = False
    import bmesh as bm_
    for x in COLS_X:
        for s in (-1, 1):
            if (x == COLS_X[0] and s < 0) or (x == COLS_X[-1] and s > 0):
                continue
            # scroll bracket: right-angle plate with a concave quarter-round cut
            L = Hh = 0.42
            pts = [(0.0, Hh), (L, Hh), (L, Hh - 0.04)]
            for i in range(1, 12):
                a = math.radians(90 + 90 * i / 12)
                pts.append((L + (L - 0.04) * math.cos(a), (Hh - 0.04) * math.sin(a)))
            pts += [(0.04, 0.0), (0.0, 0.0)]
            pts = list(reversed(pts))
            vs = [br.bm.verts.new((x + s * (0.07 + u), PY + 0.15 - 0.025, 3.5 - Hh + v)) for u, v in pts]
            f = br.bm.faces.new(vs if s > 0 else list(reversed(vs)))
            res = bm_.ops.extrude_face_region(br.bm, geom=[f])
            nv = [e for e in res["geom"] if isinstance(e, bm_.types.BMVert)]
            bm_.ops.translate(br.bm, vec=(0, 0.05, 0), verts=nv)
            for ff in {ff for v in vs + nv for ff in v.link_faces}:
                ff.material_index = 0
        br.box((x, PY + 0.15, 3.47), (0.2, 0.2, 0.08))
    bm_.ops.recalc_face_normals(br.bm, faces=br.bm.faces[:])
    br.obj("Porch_Brackets", [M["bracket"]], C)

    # railings
    rail = MB(); rail.smooth = False
    def run(p0, p1, z_top0, z_top1=None, step=0.115):
        z_top1 = z_top0 if z_top1 is None else z_top1
        p0, p1 = V(p0), V(p1)
        d = p1 - p0
        L = d.length
        ang = math.atan2(d.y, d.x)
        slope = math.atan2(z_top1 - z_top0, L)
        mid = (p0 + p1) / 2
        hl = L / math.cos(slope)
        zt = (z_top0 + z_top1) / 2
        rail.box((mid.x, mid.y, zt), (hl, 0.09, 0.06), (0, -slope, ang))
        rail.box((mid.x, mid.y, zt - 0.78), (hl, 0.07, 0.05), (0, -slope, ang))
        n = max(2, int(L / step))
        for i in range(1, n):
            f = i / n
            p = p0 + d * f
            zt_i = z_top0 + (z_top1 - z_top0) * f
            rail.box((p.x, p.y, zt_i - 0.39), (0.035, 0.035, 0.74))
    top = PORCH_Z + 0.9
    y = PY + 0.15
    run((COLS_X[0], y), (COLS_X[1], y), top)
    run((COLS_X[1], y), (STAIR_X[0], y), top)
    run((STAIR_X[1], y), (COLS_X[3], y), top)
    run((COLS_X[3], y), (COLS_X[4], y), top)
    run((COLS_X[0], y), (COLS_X[0], -0.1), top)
    # stair rails + newels
    sy0, sy1 = PY, PY - TREAD * N_TREADS
    for x in STAIR_X:
        xx = x + (0.05 if x < 1 else -0.05)
        run((xx, sy0), (xx, sy1 + 0.1), top, 0.95)
        rail.box((xx, sy1 + 0.05, 0.55), (0.12, 0.12, 1.1))
        rail.box((xx, sy1 + 0.05, 1.13), (0.15, 0.15, 0.06))
        rail.sphere((xx, sy1 + 0.05, 1.22), 0.07)
    rail.obj("Railings", [M["trim"]], C)

    # stairs: red-brown treads, white risers
    st = MB(); st.smooth = False
    for i in range(1, N_TREADS + 1):
        ztop = PORCH_Z - RISE * i
        y0 = PY - TREAD * (i - 1)
        y1 = PY - TREAD * i
        st.mi = 0
        st.box_pts((STAIR_X[0], y1 - 0.03, ztop - 0.04), (STAIR_X[1], y0 + 0.02, ztop))
        st.mi = 1
        st.box_pts((STAIR_X[0], y1, 0.0), (STAIR_X[1], y1 + 0.02, ztop - 0.04))
    st.mi = 1
    st.box_pts((STAIR_X[0], PY - 0.02, PORCH_Z - RISE - 0.04), (STAIR_X[1], PY, PORCH_Z - 0.14))
    st.obj("Front_Steps", [M["porch_floor"], M["trim"]], C)

    trim.obj("Porch_Trim", [M["trim"]], C)

    # house number on the stair newel
    import bpy
    cu = bpy.data.curves.new("House_Number", "FONT")
    cu.body = "117"
    cu.size = 0.09
    cu.extrude = 0.004
    t = bpy.data.objects.new("House_Number_117", cu)
    t.location = (STAIR_X[0] - 0.05, PY - 0.08, PORCH_Z + 0.55)
    t.rotation_euler = (math.radians(90), 0, 0)
    cu.materials.append(mat("Number_Black", (0.01, 0.01, 0.01), 0.5))
    C.objects.link(t)

    # hanging baskets
    bk = MB()
    bk.mi = 0
    for x in (-5.4, -2.2, 6.2):
        bk.sphere((x, PY + 0.45, 3.05), 0.22, (1, 1, 0.6), segs=(12, 8))
        bk.mi = 1
        for j in range(9):
            a = j * 0.7
            bk.sphere((x + 0.15 * math.cos(a), PY + 0.45 + 0.15 * math.sin(a), 3.0 - 0.1 * (j % 3)),
                      0.08, segs=(8, 6))
        bk.mi = 0
        for a in (0, 2.1, 4.2):
            bk.cyl((x + 0.2 * math.cos(a), PY + 0.45 + 0.2 * math.sin(a), 3.12), (x, PY + 0.45, 3.72),
                   0.004, segs=4)
    bk.obj("Hanging_Baskets", [M["basket"], M["plant"]], C)


def build_ground(C, M):
    g = MB(); g.smooth = False
    g.mi = 0   # grass / lawn base
    g.quad([(-40, -10.2, 0), (40, -10.2, 0), (40, 40, 0), (-40, 40, 0)])
    g.obj("Lawn", [M["grass"]], C)
    bed = MB(); bed.smooth = False
    bed.box_pts((-6.8, -8.35, 0.0), (STAIR_X[0], PY, 0.05))
    bed.box_pts((STAIR_X[1], -8.35, 0.0), (8.5, PY, 0.04))
    bed.obj("Mulch_Bed", [M["mulch"]], C)
    walk = MB(); walk.smooth = False
    walk.box_pts((STAIR_X[0] + 0.3, -8.4, 0.0), (STAIR_X[1] - 0.3, PY - TREAD * N_TREADS, 0.03))
    walk.box_pts((-40, -10.0, 0.0), (40, -8.45, 0.03))            # sidewalk
    walk.obj("Walk_and_Sidewalk", [M["concrete"]], C)
    cb = MB(); cb.smooth = False
    cb.box_pts((-40, -8.48, 0.0), (STAIR_X[0] + 0.3, -8.35, 0.14))  # bed curb stones
    cb.box_pts((STAIR_X[1] - 0.3, -8.48, 0.0), (40, -8.35, 0.14))
    cb.box_pts((-40, -10.15, -0.18), (40, -10.0, 0.03))           # street curb
    cb.obj("Curbs", [M["granite"]], C)
    st = MB(); st.smooth = False
    st.box_pts((-40, -30, -0.4), (40, -10.15, -0.18))
    st.obj("Street", [M["asphalt"]], C)


def build_all(root):
    M = materials()
    Ch = coll("House", root)
    build_house(Ch, M)
    Cp = coll("Porch", root)
    build_porch(Cp, M)
    Cg = coll("Ground", root)
    build_ground(Cg, M)
    return M
