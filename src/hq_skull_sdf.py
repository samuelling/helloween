"""Human skull from anatomical landmarks (metres; face toward -Y, Z up, origin ~ centre of the cranium).
Landmarks follow average adult proportions: glabella-opisthocranion 19.5 cm, bizygomatic 13 cm,
vertex-gnathion 22 cm."""
import numpy as np, math
import sdf as S

E, C, B = S.ellipsoid, S.cone, S.blade


def sides(f):
    return [f(-1), f(1)]


def arch(t, w, yf, depth, z):
    return (w * t, yf + depth * t * t, z)


def cranium_sdf():
    vault = S.union(E((0, 0.008, 0.012), (0.068, 0.092, 0.068)),
                    E((0, -0.05, 0.0), (0.058, 0.048, 0.06)), k=0.03)
    vault = S.sub(vault, *sides(lambda s: E((s * 0.092, -0.052, -0.022), (0.032, 0.036, 0.042))), k=0.02)
    face = S.union(
        B([(-0.05, -0.084, -0.009), (0, -0.098, -0.006), (0.05, -0.084, -0.009)], 0.008, 0.008, nrm=(0, 0, 1)),  # brow
        E((0, -0.08, -0.048), (0.05, 0.028, 0.032)),                                   # mid-face
        E((0, -0.088, -0.072), (0.036, 0.022, 0.02)),                                  # maxilla
        B([arch(t, 0.028, -0.097, 0.042, -0.081) for t in np.linspace(-1, 1, 9)], 0.0065, 0.007, nrm=(0, 0, 1), k=0.004),
        C((0, -0.095, -0.014), (0, -0.105, -0.04), 0.006, 0.0038),                     # nasal bones
        *sides(lambda s: E((s * 0.05, -0.074, -0.048), (0.014, 0.013, 0.016))),         # cheekbone
        *sides(lambda s: B([(s * 0.05, -0.08, -0.008), (s * 0.053, -0.077, -0.046)], 0.005, 0.008, nrm=(0, 1, 0))),  # lateral orbital rim
        k=0.012)
    arches = S.union(
        *sides(lambda s: B([(s * 0.056, -0.066, -0.05), (s * 0.066, -0.022, -0.042), (s * 0.062, 0.0, -0.038)],
                           0.0032, [0.008, 0.0068, 0.006], nrm=(1, 0, 0))),
        *sides(lambda s: E((s * 0.052, 0.018, -0.058), (0.009, 0.011, 0.015))))           # mastoid
    sk = S.union(S.union(vault, face, k=0.016), arches, k=0.006)
    cuts = [
        *sides(lambda s: E((s * 0.033, -0.1, -0.028), (0.022, 0.035, 0.019), S.rotm(0.1, 0, -0.2 * s))),
        *sides(lambda s: E((s * 0.03, -0.072, -0.03), (0.014, 0.03, 0.013))),
        E((0, -0.105, -0.055), (0.0095, 0.03, 0.017), S.rotm(0.2, 0, 0)),
        *sides(lambda s: E((s * 0.006, -0.103, -0.064), (0.0075, 0.03, 0.009))),
        *sides(lambda s: E((s * 0.06, 0.01, -0.035), (0.008, 0.0045, 0.0045))),
        *sides(lambda s: E((s * 0.057, -0.03, -0.046), (0.0065, 0.02, 0.0095))),
        E((0, 0.03, -0.07), (0.015, 0.02, 0.03)),
    ]
    sk = S.sub(sk, *cuts, k=0.0025)
    return sk


def mandible_sdf():
    body = [(0.048 * t, -0.098 + 0.096 * t * t, -0.119) for t in (0.0, 0.3, 0.6, 0.85, 1.0)]
    jaw = S.union(
        E((0, -0.097, -0.128), (0.014, 0.007, 0.008)),
        *sides(lambda s: B([(s * x, y, z) for x, y, z in body], [0.015, 0.0145, 0.013, 0.012, 0.012], 0.0065, nrm=(0, 0, 1))),
        B([arch(t, 0.025, -0.095, 0.04, -0.109) for t in np.linspace(-1, 1, 9)], 0.006, 0.006, nrm=(0, 0, 1), k=0.004),
        *sides(lambda s: B([(s * 0.049, -0.004, -0.12), (s * 0.053, -0.002, -0.085), (s * 0.055, 0.0, -0.054)],
                           0.0045, [0.015, 0.012, 0.007], nrm=(1, 0, 0))),
        *sides(lambda s: E((s * 0.055, 0.001, -0.048), (0.01, 0.005, 0.0045))),
        *sides(lambda s: C((s * 0.051, -0.018, -0.09), (s * 0.05, -0.03, -0.062), 0.006, 0.0025)),
        k=0.008)
    return jaw


def teeth_sdf(upper=True, n=16):
    t_ = []
    for i in range(n):
        t = -0.96 + 1.92 * i / (n - 1)
        if upper:
            x, y, z0 = arch(t, 0.0265, -0.0985, 0.04, -0.086)
        else:
            x, y, z0 = arch(t, 0.0245, -0.0955, 0.04, -0.103)
        front = abs(t) < 0.3
        w = 0.0036 if front else (0.004 if abs(t) < 0.55 else 0.0048)
        h = 0.0052 if front else (0.0045 if abs(t) < 0.55 else 0.0036)
        zc = z0 - h * 0.9 if upper else z0 + h * 0.9
        yaw = math.atan2(2 * 0.04 * t, 0.0265)
        t_.append(S.box((x, y, zc), (w * 2, 0.0055 if front else 0.0085, h * 2), 0.0012 if front else 0.0018, S.rotm(0, 0, yaw)))
    return S.union(*t_, k=0.0006)


def human_skull_sdf(noise=True):
    sk, jaw = cranium_sdf(), mandible_sdf()
    if noise:
        sk = S.noisy(S.noisy(sk, 0.0012, 18, 2), 0.0004, 90, 3)
        jaw = S.noisy(jaw, 0.0004, 90, 3)
    return sk, jaw, teeth_sdf(True), teeth_sdf(False)
