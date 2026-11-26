"""Sculpted animal parts (SDF): cervid skull + antlers, cow mandible, horns, canine skull."""
import math
import numpy as np
import sdf as S
import build_props as BP

E, C, B, CH = S.ellipsoid, S.cone, S.blade, S.chain


def sides(f):
    return [f(-1), f(1)]


def deer_skull_sdf(k=1.0):
    """White-tailed-deer skull, ~0.34 m long at k=1; faces -Y, origin at the braincase, no mandible."""
    def P(x, y, z):
        return (x * k, y * k, z * k)

    def R(r):
        return tuple(v * k for v in r) if hasattr(r, "__len__") else r * k
    brain = S.union(E(P(0, 0.03, 0.0), R((0.044, 0.058, 0.042))),
                    E(P(0, 0.075, -0.012), R((0.036, 0.03, 0.034))), k=0.02 * k)
    face = S.union(
        C(P(0, -0.03, -0.006), P(0, -0.17, -0.03), 0.036 * k, 0.019 * k),           # maxilla
        C(P(0, -0.17, -0.03), P(0, -0.245, -0.042), 0.019 * k, 0.009 * k),          # premaxilla
        B([P(0, -0.0, 0.03), P(0, -0.09, 0.018), P(0, -0.19, -0.012)], 0.0055 * k, [0.02 * k, 0.017 * k, 0.01 * k], nrm=(0, 0, 1)),  # nasals
        *sides(lambda s: E(P(s * 0.03, -0.07, -0.025), R((0.012, 0.05, 0.018)))),   # cheek tooth row bulge
        *sides(lambda s: E(P(s * 0.04, -0.042, 0.01), R((0.02, 0.024, 0.021)))),  # orbital boss (rim)
        *sides(lambda s: B([P(s * 0.05, -0.05, -0.012), P(s * 0.053, -0.0, -0.02), P(s * 0.045, 0.04, -0.018)], 0.004 * k, 0.007 * k, nrm=(1, 0, 0))),  # zygomatic
        *sides(lambda s: C(P(s * 0.028, 0.012, 0.035), P(s * 0.033, 0.018, 0.05), 0.014 * k, 0.013 * k)),  # pedicles
        k=0.012 * k)
    sk = S.union(brain, face, k=0.016 * k)
    cuts = [*sides(lambda s: S.sphere(P(s * 0.054, -0.042, 0.01), 0.017 * k)),
            *sides(lambda s: E(P(s * 0.036, -0.1, 0.01), R((0.008, 0.016, 0.007)))),      # preorbital vacuity
            E(P(0, -0.235, -0.022), R((0.012, 0.07, 0.012))),                            # nasal aperture
            E(P(0, 0.1, -0.035), R((0.012, 0.012, 0.012)))]
    sk = S.sub(sk, *cuts, k=0.003 * k)
    # cheek teeth
    teeth = [S.box(P(s * 0.03, -0.035 - 0.0165 * i, -0.043), R((0.012, 0.016, 0.014)), 0.003 * k) for s in (-1, 1) for i in range(6)]
    return sk, S.union(*teeth, k=0.001 * k)


def antlers_sdf(kind="deer", scale=1.0, k=1.0, seed=3, base_z=0.03):
    import random
    rnd = random.Random(seed)
    nodes = []
    r0 = (0.03 if kind == "elk" else 0.02) * scale
    for s in (-1, 1):
        spl = BP.antler_splines(s, scale, kind, rnd)
        for j, sp in enumerate(spl):
            pts = [np.array((co[0], co[1], co[2] + base_z * k)) for co, r in sp]
            rad = [max(r * r0, 0.005 * scale) for co, r in sp]
            nodes.append(CH(pts, rad, k=0.008 * scale))
        burr = np.array(spl[0][0][0]) + (0, 0, base_z * k)
        nodes.append(S.torus(burr, r0 * 1.05, r0 * 0.45, S.rotm(0.2, s * 0.3, 0)))
    a = S.union(*nodes, k=0.006 * scale)
    return S.noisy(S.noisy(a, 0.0016 * scale, 60 / scale, 3, ridged=True, stretch=(1, 1, 0.35)), 0.0008 * scale, 150 / scale, 2)


def cow_mandible_sdf():
    """Cow hemi-mandible (one half), lying along -Y with the ramus rising at +Y. Origin at the angle."""
    body = B([(0, 0.0, 0.0), (0, -0.1, 0.008), (0, -0.2, 0.012), (0, -0.3, 0.004)], 0.009, [0.032, 0.03, 0.025, 0.016], nrm=(1, 0, 0))
    ramus = B([(0, 0.01, -0.01), (0, 0.03, 0.06), (0, 0.04, 0.14), (0, 0.035, 0.2)], 0.008, [0.035, 0.04, 0.03, 0.016], nrm=(1, 0, 0))
    angle = E((0, 0.03, -0.01), (0.009, 0.04, 0.035))
    incisors = S.union(*[C((0, -0.3, 0.008), (0.002 * (i - 1.5), -0.34 - 0.004 * i, 0.03), 0.005, 0.0035) for i in range(4)], k=0.002)
    j = S.union(body, ramus, angle, k=0.015)
    j = S.sub(j, E((0, 0.02, 0.06), (0.02, 0.01, 0.02)), k=0.006)        # thin ramus window
    teeth = S.union(*[S.box((0, -0.03 - 0.022 * i, 0.036 + 0.0015 * i), (0.016, 0.021, 0.02), 0.003, S.rotm(0, 0, 0.1 * math.sin(i * 1.7))) for i in range(6)], k=0.001)
    return S.union(j, incisors, k=0.004), teeth


def ram_horn_sdf(s, scale=1.0, turns=1.15, r0=0.045, seed=0):
    """Spiral ram horn growing from a skull at the origin: out, back, down, forward. Ridged growth rings."""
    pts, rad = [], []
    n = 26
    for i in range(n):
        t = i / (n - 1)
        a = t * turns * 2 * math.pi
        R = (0.11 - 0.05 * t) * scale
        pts.append(np.array((s * (0.04 + 0.12 * t) * scale, (0.0 + R * math.sin(a)) * 1.0 + 0.02 * scale, (R * math.cos(a) - 0.11 * scale) * 1.0 + 0.11 * scale)))
        rad.append(r0 * scale * (1 - 0.82 * t) + 0.004 * scale)
    h = CH(pts, rad, k=0.01 * scale)
    return S.noisy(h, 0.0035 * scale, 90 / scale, 2, ridged=True, stretch=(1, 3, 3))


def horn_curve_sdf(pts, r0, r1, ridged=0.0025):
    n = len(pts)
    h = CH([np.array(p) for p in pts], [r0 + (r1 - r0) * i / (n - 1) for i in range(n)], k=0.01)
    return S.noisy(h, ridged, 140, 2, ridged=True, stretch=(0.3, 0.3, 3)) if ridged else h
