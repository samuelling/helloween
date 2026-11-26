"""Signed-distance sculpting: build organic forms from primitives with smooth unions / carves, add
fbm surface noise, then polygonise with marching cubes into a Blender mesh.

Think of it as clay: smooth union (k) is how much the thumb blends two lumps together, smooth subtract
is a rounded gouge. Every node is f(P[N,3]) -> distance[N]."""
import math
import numpy as np
import bpy
from skimage.measure import marching_cubes

BIG = 1e3
PAD = 0.035   # far-field margin: must exceed the largest smooth-blend radius k


def _v(x):
    return np.asarray(x, dtype=np.float32)


class N:
    """SDF node with an axis-aligned bound (lo, hi) used to skip far points."""
    def __init__(self, f, lo, hi, margin=0.02):
        self.f, self.lo, self.hi, self.margin = f, _v(lo), _v(hi), margin

    def __call__(self, P):
        lo, hi = self.lo, self.hi
        inside = np.all((P >= lo) & (P <= hi), axis=1)
        out = np.empty(len(P), np.float32)
        if inside.any():
            out[inside] = self.f(P[inside])
        o = ~inside
        if o.any():   # distance to the bound box (a lower bound on the true distance)
            q = np.maximum(np.maximum(lo - P[o], P[o] - hi), 0)
            out[o] = np.sqrt((q * q).sum(1)) + self.margin
        return out

    # operators
    def __or__(self, o):
        return union(self, o)

    def __sub__(self, o):
        return sub(self, o)


def _pad(lo, hi, m):
    return _v(lo) - m, _v(hi) + m


# ----------------------------------------------------------------- primitives
def sphere(c, r):
    c = _v(c)
    return N(lambda P: np.linalg.norm(P - c, axis=1) - r, *_pad(c, c, r + PAD), PAD)


def ellipsoid(c, r, rot=None):
    """r = radii; rot = 3x3 matrix (local->world) or None."""
    c, r = _v(c), _v(r)
    R = None if rot is None else _v(rot)
    def f(P):
        q = P - c
        if R is not None:
            q = q @ R          # world -> local (R orthonormal)
        k0 = np.linalg.norm(q / r, axis=1)
        k1 = np.linalg.norm(q / (r * r), axis=1) + 1e-9
        return np.where(k0 < 1e-6, -float(r.min()), k0 * (k0 - 1) / k1)
    m = (r + PAD) if R is None else float(r.max()) + PAD
    return N(f, c - m, c + m, PAD)


def cone(a, b, r1, r2):
    """Round cone (capsule with different end radii)."""
    a, b = _v(a), _v(b)
    ba = b - a; l2 = float(ba @ ba); rr = r1 - r2; a2 = l2 - rr * rr; il2 = 1.0 / max(l2, 1e-12)
    def f(P):
        pa = P - a
        y = pa @ ba
        z = y - l2
        w = pa * l2 - np.outer(y, ba)
        x2 = (w * w).sum(1)
        y2 = y * y * l2; z2 = z * z * l2
        k = np.sign(rr) * rr * rr * x2
        d = (np.sqrt(np.maximum(x2 * a2 * il2, 0)) + y * rr) * il2 - r1
        c1 = np.sign(z) * a2 * z2 > k
        c2 = np.sign(y) * a2 * y2 < k
        d = np.where(c2, np.sqrt(x2 + y2) * il2 - r1, d)
        d = np.where(c1, np.sqrt(x2 + z2) * il2 - r2, d)
        return d
    m = max(r1, r2) + PAD
    return N(f, np.minimum(a, b) - m, np.maximum(a, b) + m, PAD)


def capsule(a, b, r):
    return cone(a, b, r, r)


def chain(pts, radii, k=0.01):
    """Tube through points, radius per point, joints smoothly blended."""
    rs = radii if hasattr(radii, "__len__") else [radii] * len(pts)
    segs = [cone(pts[i], pts[i + 1], rs[i], rs[i + 1]) for i in range(len(pts) - 1)]
    return union(*segs, k=k)


def box(c, size, r=0.0, rot=None):
    c, h = _v(c), _v(size) / 2 - r
    R = None if rot is None else _v(rot)
    def f(P):
        q = P - c
        if R is not None:
            q = q @ R
        q = np.abs(q) - h
        return np.linalg.norm(np.maximum(q, 0), axis=1) + np.minimum(q.max(1), 0) - r
    m = (_v(size) / 2 + PAD) if R is None else float(np.linalg.norm(_v(size))) / 2 + PAD
    return N(f, c - m, c + m, PAD)


def torus(c, R, r, rot=None):
    c = _v(c); Rm = None if rot is None else _v(rot)
    def f(P):
        q = P - c
        if Rm is not None:
            q = q @ Rm
        a = np.sqrt(q[:, 0] ** 2 + q[:, 1] ** 2) - R
        return np.sqrt(a * a + q[:, 2] ** 2) - r
    m = _v((R + r + PAD, R + r + PAD, r + PAD)) if Rm is None else R + r + PAD
    return N(f, c - m, c + m, PAD)


def plane_cut(n, d):
    """Half-space n·p > d (use with sub to slice)."""
    n = _v(n) / np.linalg.norm(n)
    return N(lambda P: d - P @ n, (-BIG,) * 3, (BIG,) * 3, 0.0)


def lathe(c, profile, rot=None):
    """Revolve a 2D (r, z) polyline profile around local Z. Closed solid."""
    c = _v(c); pr = _v(profile); R = None if rot is None else _v(rot)
    def f(P):
        q = P - c
        if R is not None:
            q = q @ R
        x = np.sqrt(q[:, 0] ** 2 + q[:, 1] ** 2); y = q[:, 2]
        p2 = np.stack([x, y], 1)
        d = np.full(len(P), 1e9, np.float32); s = np.ones(len(P), np.float32)
        poly = np.concatenate([[[0, pr[0, 1]]], pr, [[0, pr[-1, 1]]]], 0)
        for i in range(len(poly)):
            a, b = poly[i], poly[(i + 1) % len(poly)]
            e = b - a; w = p2 - a
            t = np.clip((w @ e) / max(e @ e, 1e-12), 0, 1)
            dd = w - np.outer(t, e)
            d = np.minimum(d, (dd * dd).sum(1))
            c1 = p2[:, 1] >= a[1]; c2 = p2[:, 1] < b[1]; c3 = e[0] * w[:, 1] > e[1] * w[:, 0]
            flip = (c1 & c2 & c3) | (~c1 & ~c2 & ~c3)
            s = np.where(flip, -s, s)
        return s * np.sqrt(d)
    m = float(np.abs(pr).max()) + PAD
    return N(f, c - m, c + m, PAD)


# ----------------------------------------------------------------- combinators
def _smin(a, b, k):
    if k <= 0:
        return np.minimum(a, b)
    h = np.maximum(k - np.abs(a - b), 0) / k
    return np.minimum(a, b) - h * h * k * 0.25


def union(*ns, k=0.0):
    ns = [n for n in ns if n is not None]
    lo = np.min([n.lo for n in ns], 0); hi = np.max([n.hi for n in ns], 0)
    def f(P):
        d = ns[0](P)
        for n in ns[1:]:
            d = _smin(d, n(P), k)
        return d
    return N(f, lo - k, hi + k, min(n.margin for n in ns))


def sub(a, *cutters, k=0.0):
    def f(P):
        d = a(P)
        for c in cutters:
            d = -_smin(-d, c(P), k)
        return d
    return N(f, a.lo, a.hi, a.margin)


def inter(a, b, k=0.0):
    def f(P):
        return -_smin(-a(P), -b(P), k)
    return N(f, np.maximum(a.lo, b.lo), np.minimum(a.hi, b.hi))


def shell(a, t):
    return N(lambda P: np.abs(a(P)) - t, a.lo, a.hi)


def offset(a, r):
    return N(lambda P: a(P) - r, a.lo - abs(r), a.hi + abs(r))


def xform(a, M):
    """Apply a 4x4 (world <- local) transform with uniform-ish scale to node a."""
    M = np.asarray(M, np.float64); Mi = np.linalg.inv(M).astype(np.float32)
    s = float(np.cbrt(abs(np.linalg.det(M[:3, :3]))))
    corners = np.array([[x, y, z, 1] for x in (a.lo[0], a.hi[0]) for y in (a.lo[1], a.hi[1]) for z in (a.lo[2], a.hi[2])], np.float32)
    w = corners @ M.T.astype(np.float32)
    def f(P):
        q = P @ Mi[:3, :3].T + Mi[:3, 3]
        return a(q) * s
    return N(f, w[:, :3].min(0), w[:, :3].max(0), a.margin * s)


def mirror_x(a):
    """Union of a with its mirror image across x=0."""
    b = N(lambda P: a(P * _v((-1, 1, 1))), a.lo * _v((-1, 1, 1)), a.hi * _v((-1, 1, 1)))
    b.lo, b.hi = np.minimum(b.lo, b.hi), np.maximum(b.lo, b.hi)
    return union(a, b)


# ----------------------------------------------------------------- noise
_rng = np.random.default_rng(7)
_PERM = _rng.permutation(256).astype(np.int32); _PERM = np.concatenate([_PERM, _PERM])
_GRAD = _rng.normal(size=(256, 3)).astype(np.float32); _GRAD /= np.linalg.norm(_GRAD, axis=1, keepdims=True)


def _perlin(P):
    pi = np.floor(P).astype(np.int32); pf = (P - pi).astype(np.float32)
    u = pf * pf * pf * (pf * (pf * 6 - 15) + 10)
    out = 0
    xi, yi, zi = pi[:, 0] & 255, pi[:, 1] & 255, pi[:, 2] & 255
    acc = []
    for dx in (0, 1):
        for dy in (0, 1):
            for dz in (0, 1):
                h = _PERM[_PERM[_PERM[xi + dx] + yi + dy] + zi + dz]
                g = _GRAD[h]
                d = pf - _v((dx, dy, dz))
                acc.append((g * d).sum(1))
    x00 = acc[0] + u[:, 2] * (acc[1] - acc[0]); x01 = acc[2] + u[:, 2] * (acc[3] - acc[2])
    x10 = acc[4] + u[:, 2] * (acc[5] - acc[4]); x11 = acc[6] + u[:, 2] * (acc[7] - acc[6])
    y0 = x00 + u[:, 1] * (x01 - x00); y1 = x10 + u[:, 1] * (x11 - x10)
    return y0 + u[:, 0] * (y1 - y0)


def fbm(P, scale, octaves=4, gain=0.5, ridged=False):
    s, a, out = scale, 1.0, 0.0
    for _ in range(octaves):
        n = _perlin(P * s + 17.3)
        out = out + a * ((1 - np.abs(n) * 2) if ridged else n)
        s *= 2.03; a *= gain
    return out


def noisy(a, amp, scale, octaves=4, ridged=False, stretch=(1, 1, 1), band=None):
    """Surface noise; only evaluated in a thin band around the surface (the rest is untouched)."""
    st = _v(stretch); band = amp * 2.5 if band is None else band
    def f(P):
        d = a(P)
        m = np.abs(d) < band
        if m.any():
            d[m] = d[m] + amp * fbm(P[m] * st, scale, octaves, ridged=ridged)
        return d
    return N(f, a.lo - amp, a.hi + amp, max(a.margin - amp, 0.002))


def warp(a, amp, scale):
    """Domain warp: lumps and twists the form like hand-pressed clay."""
    def f(P):
        d = a(P)
        m = np.abs(d) < amp * 2.5
        if m.any():
            Q = P[m]
            o = np.stack([fbm(Q + 3.1 * i, scale, 2) for i in range(3)], 1) * amp
            d[m] = a(Q + o)
        return d
    return N(f, a.lo - amp, a.hi + amp, max(a.margin - amp, 0.002))


# ----------------------------------------------------------------- meshing
def mesh(node, name, voxel, mats=(), pad=None, target=None, chunk=2_000_000, smooth=1, max_pts=24e6):
    pad = voxel * 3 if pad is None else pad
    lo = node.lo - pad; hi = node.hi + pad
    lo = np.maximum(lo, -50); hi = np.minimum(hi, 50)
    n = np.ceil((hi - lo) / voxel).astype(int) + 1
    if np.prod(n) > max_pts:          # keep memory/time sane: coarsen rather than blow up
        voxel *= float(np.cbrt(np.prod(n) / max_pts)) * 1.02
        n = np.ceil((hi - lo) / voxel).astype(int) + 1
        print(f"  [sdf] {name}: grid too large, voxel -> {voxel:.4f}")
    xs = [lo[i] + np.arange(n[i], dtype=np.float32) * voxel for i in range(3)]
    G = np.empty(tuple(n), np.float32)
    # evaluate slab by slab along x
    per = max(1, chunk // (n[1] * n[2]))
    Y, Z = np.meshgrid(xs[1], xs[2], indexing="ij")
    for i0 in range(0, n[0], per):
        i1 = min(n[0], i0 + per)
        X = np.repeat(xs[0][i0:i1], n[1] * n[2])
        P = np.stack([X, np.tile(Y.ravel(), i1 - i0), np.tile(Z.ravel(), i1 - i0)], 1).astype(np.float32)
        G[i0:i1] = node(P).reshape(i1 - i0, n[1], n[2])
    G[0, :, :] = G[-1, :, :] = G[:, 0, :] = G[:, -1, :] = G[:, :, 0] = G[:, :, -1] = abs(voxel)
    if G.min() > 0:
        raise ValueError(f"{name}: empty SDF")
    verts, faces, _, _ = marching_cubes(G, 0.0, spacing=(voxel, voxel, voxel))
    verts = verts + lo
    me = bpy.data.meshes.new(name)
    me.from_pydata(verts.tolist(), [], faces.tolist())
    me.validate(); me.update()
    for m in mats:
        me.materials.append(m)
    ob = bpy.data.objects.new(name, me)
    bpy.context.scene.collection.objects.link(ob)
    import hq_lib as H
    if smooth:
        H.relax(ob, smooth, 0.5)
    if target:
        H.decimate(ob, target)
    ob.data.shade_smooth()
    return ob


def rotm(rx=0, ry=0, rz=0):
    from mathutils import Euler
    return np.array(Euler((rx, ry, rz)).to_matrix(), np.float32)


def frame(a, b, nrm=(1, 0, 0)):
    """Rotation whose local Z runs a->b and local X is as close as possible to nrm."""
    a, b = _v(a), _v(b); z = b - a; z = z / (np.linalg.norm(z) + 1e-12)
    x = _v(nrm) - z * float(_v(nrm) @ z)
    if np.linalg.norm(x) < 1e-6:
        x = np.cross(z, _v((0, 0, 1)))
    x = x / np.linalg.norm(x); y = np.cross(z, x)
    return np.stack([x, y, z], 1)


def seg_ell(a, b, rx, ry, nrm=(1, 0, 0), extra=0.0):
    """Ellipsoid spanning a->b (half-length along the segment + extra), radii rx (toward nrm) and ry."""
    a, b = _v(a), _v(b)
    L = float(np.linalg.norm(b - a)) / 2 + extra
    return ellipsoid((a + b) / 2, (rx, ry, L), frame(a, b, nrm))


def blade(pts, rx, ry, nrm=(1, 0, 0), k=0.006):
    rxs = rx if hasattr(rx, "__len__") else [rx] * len(pts)
    rys = ry if hasattr(ry, "__len__") else [ry] * len(pts)
    segs = []
    for i in range(len(pts) - 1):
        segs.append(seg_ell(pts[i], pts[i + 1], (rxs[i] + rxs[i + 1]) / 2, (rys[i] + rys[i + 1]) / 2, nrm,
                            extra=max(rxs[i], rys[i]) * 0.6))
    return union(*segs, k=k)


def orient(node, origin, zdir, ydir, s=1.0):
    """Place a node built along local +Z (with local +Y as 'up/dorsal') at origin, aligned to zdir/ydir."""
    z = _v(zdir); z = z / np.linalg.norm(z)
    y = _v(ydir); y = y - z * float(y @ z); y = y / np.linalg.norm(y)
    x = np.cross(y, z)
    M = np.eye(4); M[:3, 0], M[:3, 1], M[:3, 2] = x * s, y * s, z * s; M[:3, 3] = origin
    return xform(node, M)


def move(node, dx=0, dy=0, dz=0, rx=0, ry=0, rz=0, s=1.0):
    M = np.eye(4); M[:3, :3] = rotm(rx, ry, rz) * s; M[:3, 3] = (dx, dy, dz)
    return xform(node, M)


def revolve(c, profile, mod=None, sy=1.0, lip=0.6, axis_rot=None, smooth=True):
    """Solid of revolution about local Z from an (r, z) profile (z increasing), with an optional radial
    modulation mod(theta, z) -> dr for cloth folds. sy squashes depth (Y)."""
    c = _v(c); pr = np.asarray(profile, np.float32); R = None if axis_rot is None else _v(axis_rot)
    if smooth and len(pr) >= 3:
        from scipy.interpolate import PchipInterpolator
        zs, idx = np.unique(pr[:, 1], return_index=True)
        if len(zs) >= 3:
            zz = np.linspace(zs[0], zs[-1], max(60, len(zs) * 8))
            pr = np.stack([PchipInterpolator(zs, pr[idx, 0])(zz), zz], 1).astype(np.float32)
    z0, z1 = float(pr[0, 1]), float(pr[-1, 1])
    def f(P):
        q = P - c
        if R is not None:
            q = q @ R
        x, y, z = q[:, 0], q[:, 1] / sy, q[:, 2]
        rho = np.sqrt(x * x + y * y)
        r = np.interp(z, pr[:, 1], pr[:, 0])
        if mod is not None:
            r = r + mod(np.arctan2(y, x), z)
        d = (rho - r) * lip
        return np.maximum(d, np.maximum(z0 - z, z - z1))
    m = float(pr[:, 0].max()) * max(1, sy) + 0.08 + PAD
    lo = c + _v((-m, -m, z0 - PAD)); hi = c + _v((m, m, z1 + PAD))
    if R is not None:
        r_ = max(m, z1 - z0 + PAD)
        lo, hi = c - r_ - abs(z0) - abs(z1), c + r_ + abs(z0) + abs(z1)
    return N(f, lo, hi, PAD)


def _catmull(P, sub=8):
    """Centripetal-ish Catmull-Rom resampling of a polyline (keeps end points)."""
    P = np.asarray(P, np.float32)
    Q = np.vstack([P[0] * 2 - P[1], P, P[-1] * 2 - P[-2]])
    out = []
    for i in range(1, len(Q) - 2):
        p0, p1, p2, p3 = Q[i - 1], Q[i], Q[i + 1], Q[i + 2]
        for t in np.linspace(0, 1, sub, endpoint=False):
            t2, t3 = t * t, t * t * t
            out.append(0.5 * ((2 * p1) + (-p0 + p2) * t + (2 * p0 - 5 * p1 + 4 * p2 - p3) * t2 + (-p0 + 3 * p1 - 3 * p2 + p3) * t3))
    out.append(P[-1])
    return np.array(out, np.float32)


def folds(n=9, amp=0.03, z_full=0.0, z_none=1.2, seed=0, amp_min=0.004, twist=1.5):
    """Cloth-fold modulation: deep folds at the hem fading out toward z_none."""
    rng = np.random.default_rng(seed)
    ph = rng.uniform(0, 6.28, 3)
    def mod(th, z):
        t = np.clip((z_none - z) / (z_none - z_full), 0, 1) ** 1.3
        a = amp_min + amp * t
        return a * (0.6 * np.sin(n * th + ph[0] + twist * z) + 0.3 * np.sin((n + 4) * th + ph[1] - 2 * z) + 0.25 * np.sin(3 * th + ph[2]))
    return mod


def prism(poly, y0, y1, r=0.0, rot=None, c=(0, 0, 0)):
    """2D polygon in the XZ plane (list of (x, z)), extruded along Y from y0 to y1; r rounds the edges."""
    pr = np.asarray(poly, np.float32); c = _v(c); R = None if rot is None else _v(rot)
    def f(P):
        q = P - c
        if R is not None:
            q = q @ R
        p2 = np.stack([q[:, 0], q[:, 2]], 1)
        d = np.full(len(P), 1e9, np.float32); s = np.ones(len(P), np.float32)
        n = len(pr)
        for i in range(n):
            a, b = pr[i], pr[(i + 1) % n]
            e = b - a; w = p2 - a
            t = np.clip((w @ e) / max(float(e @ e), 1e-12), 0, 1)
            dd = w - np.outer(t, e)
            d = np.minimum(d, (dd * dd).sum(1))
            c1 = p2[:, 1] >= a[1]; c2 = p2[:, 1] < b[1]; c3 = e[0] * w[:, 1] > e[1] * w[:, 0]
            flip = (c1 & c2 & c3) | (~c1 & ~c2 & ~c3)
            s = np.where(flip, -s, s)
        d2 = s * np.sqrt(d) + r
        dy = np.maximum(y0 + r - q[:, 1], q[:, 1] - y1 + r)
        out = np.stack([d2, dy], 1)
        return np.linalg.norm(np.maximum(out, 0), axis=1) + np.minimum(out.max(1), 0) - r
    if R is None:
        lo = c + _v((pr[:, 0].min() - PAD, y0 - PAD, pr[:, 1].min() - PAD)); hi = c + _v((pr[:, 0].max() + PAD, y1 + PAD, pr[:, 1].max() + PAD))
        return N(f, lo, hi, PAD)
    m = float(np.abs(pr).max()) + max(abs(y0), abs(y1)) + PAD
    return N(f, c - m, c + m, PAD)


def frustum(z0, z1, w0, w1, d0=None, d1=None, c=(0, 0, 0)):
    """Square-section taper (obelisk shaft / pyramidion) from half-widths w0 at z0 to w1 at z1."""
    c = _v(c); d0 = w0 if d0 is None else d0; d1 = w1 if d1 is None else d1
    def f(P):
        q = P - c
        t = np.clip((q[:, 2] - z0) / (z1 - z0), 0, 1)
        wx = w0 + (w1 - w0) * t; wy = d0 + (d1 - d0) * t
        k = 1.0 / math.sqrt(1 + ((w0 - w1) / (z1 - z0)) ** 2)
        return np.maximum.reduce([(np.abs(q[:, 0]) - wx) * k, (np.abs(q[:, 1]) - wy) * k, z0 - q[:, 2], q[:, 2] - z1])
    m = max(w0, w1, d0, d1) + PAD
    return N(f, c + _v((-m, -m, z0 - PAD)), c + _v((m, m, z1 + PAD)), PAD)
