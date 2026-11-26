"""Build the real neighbourhood around the house for the web viewer.

Inputs (fetched separately, not committed): geo/map.osm (OSM API), geo/elev_grid.json (USGS 3DEP point
queries), geo/tiles + geo/aerial_meta.json (MassGIS 2025 orthoimagery, z20). geo/frame.json maps local
east/north metres onto the Blender model frame (x along the street, -y toward the street).

Output (model-local metres only, no lat/lon): <out>/geo/neighborhood.json + <out>/geo/aerial.jpg
"""
import json, math, sys, os
import xml.etree.ElementTree as ET
import numpy as np
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
G = os.path.join(HERE, "geo")
OUT = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, "web")
os.makedirs(os.path.join(OUT, "geo"), exist_ok=True)

F = json.load(open(os.path.join(G, "frame.json")))
P0, ex, ey = np.array(F["P0"]), np.array(F["ex"]), np.array(F["ey"])
lat0, lon0, k, kx = F["lat0"], F["lon0"], F["k"], F["kx"]


def enu_to_model(e, n):
    d = np.array([e, n]) - P0
    return float(d @ ex), float(d @ ey)


def model_to_enu(X, Y):
    return P0 + X * ex + Y * ey


# ------------------------------------------------------------- terrain (relative to the house)
E = json.load(open(os.path.join(G, "elev_grid.json")))
N = E["N"]
Z = np.full((N, N), np.nan)
for i, j, la, lo, v in E["pts"]:
    if v is not None:
        Z[i, j] = v
for _ in range(3):   # fill the few failed samples from neighbours
    m = np.isnan(Z)
    if not m.any():
        break
    P = np.pad(Z, 1, constant_values=np.nan)
    nb = np.nanmean(np.stack([P[:-2, 1:-1], P[2:, 1:-1], P[1:-1, :-2], P[1:-1, 2:]]), 0)
    Z[m] = nb[m]
la_min, la_max = E["lat0"] - E["span_lat"], E["lat0"] + E["span_lat"]
lo_min, lo_max = E["lon0"] - E["span_lon"], E["lon0"] + E["span_lon"]


def elev_enu(e, n):
    la, lo = lat0 + n / k, lon0 + e / kx
    fi = (la - la_min) / (la_max - la_min) * (N - 1)
    fj = (lo - lo_min) / (lo_max - lo_min) * (N - 1)
    fi, fj = min(max(fi, 0), N - 1.001), min(max(fj, 0), N - 1.001)
    i, j = int(fi), int(fj)
    a, b = fi - i, fj - j
    return ((1 - a) * (1 - b) * Z[i, j] + (1 - a) * b * Z[i, j + 1] + a * (1 - b) * Z[i + 1, j] + a * b * Z[i + 1, j + 1])


H0 = elev_enu(*model_to_enu(0.5, 4.0))
LOT = (-8.5, 10.0, -10.3, 12.5)   # model x0, x1, y0, y1 kept flat at z=0 (the hand-built yard)


def lot_weight(X, Y, blend=9.0):
    dx = max(LOT[0] - X, 0, X - LOT[1])
    dy = max(LOT[2] - Y, 0, Y - LOT[3])
    d = math.hypot(dx, dy)
    t = min(1.0, d / blend)
    return t * t * (3 - 2 * t)


def terrain_z(X, Y):
    raw = elev_enu(*model_to_enu(X, Y)) - H0
    return raw * lot_weight(X, Y)


EXT = 105.0
STEP = 2.5
xs = np.arange(-EXT, EXT + 0.01, STEP)
ys = np.arange(-EXT, EXT + 0.01, STEP)
heights = [[round(terrain_z(X, Y), 3) for X in xs] for Y in ys]

# ------------------------------------------------------------- aerial: affine map model (X,Y) -> uv
A = json.load(open(os.path.join(G, "aerial_meta.json")))
nz = 2 ** A["z"]


def aerial_px(X, Y):
    e, n = model_to_enu(X, Y)
    la, lo = lat0 + n / k, lon0 + e / kx
    x = (lo + 180) / 360 * nz
    y = (1 - math.asinh(math.tan(math.radians(la))) / math.pi) / 2 * nz
    return (x - A["xa"]) * 256, (y - A["ya"]) * 256


src = np.array([[0, 0, 1], [100, 0, 1], [0, 100, 1], [-80, -60, 1], [60, 90, 1]], float)
dst = np.array([aerial_px(x, y) for x, y, _ in src])
M, *_ = np.linalg.lstsq(src, dst, rcond=None)          # 3x2: [X Y 1] @ M = (px, py)
W, Hh = A["W"], A["H"]
uv_affine = [[M[0, 0] / W, M[1, 0] / W, M[2, 0] / W], [M[0, 1] / Hh, M[1, 1] / Hh, M[2, 1] / Hh]]
img = Image.open(os.path.join(G, "aerial_mosaic.jpg")).convert("RGB")
img.save(os.path.join(OUT, "geo", "aerial.jpg"), quality=80, optimize=True)

# ------------------------------------------------------------- buildings from OSM
t = ET.parse(os.path.join(G, "map.osm")).getroot()
nodes = {nd.get("id"): ((float(nd.get("lon")) - lon0) * kx, (float(nd.get("lat")) - lat0) * k) for nd in t.iter("node")}
OWN = "29778628"
buildings = []
for w in t.iter("way"):
    tg = {x.get("k"): x.get("v") for x in w.iter("tag")}
    if "building" not in tg or w.get("id") == OWN:
        continue
    pts = [enu_to_model(*nodes[r.get("ref")]) for r in w.iter("nd") if r.get("ref") in nodes]
    if len(pts) < 4:
        continue
    pts = pts[:-1] if pts[0] == pts[-1] else pts
    if max(abs(x) for x, y in pts) > EXT - 3 or max(abs(y) for x, y in pts) > EXT - 3:
        continue
    area = 0.5 * sum(pts[i][0] * pts[i - 1][1] - pts[i - 1][0] * pts[i][1] for i in range(len(pts)))
    if area < 0:
        pts.reverse()
    area = abs(area)
    kind = tg.get("building", "yes")
    lv = tg.get("building:levels")
    if lv:
        walls = float(lv) * 2.9
    elif kind in ("garage", "garages", "shed") or area < 30:
        walls = 2.7
    elif area < 70:
        walls = 5.2
    elif area < 260:
        walls = 6.4
    else:
        walls = 8.5
    roof = 0.0 if kind in ("garages", "commercial", "retail") or area > 600 else min(3.6, 0.9 + area ** 0.5 * 0.22)
    base = min(terrain_z(x, y) for x, y in pts)
    buildings.append({"pts": [[round(x, 2), round(y, 2)] for x, y in pts], "base": round(base, 2),
                      "walls": round(walls, 2), "roof": round(roof, 2), "kind": kind})

roads = []
for w in t.iter("way"):
    tg = {x.get("k"): x.get("v") for x in w.iter("tag")}
    hw = tg.get("highway")
    if hw not in ("residential", "tertiary", "primary", "secondary", "service", "unclassified"):
        continue
    pts = [enu_to_model(*nodes[r.get("ref")]) for r in w.iter("nd") if r.get("ref") in nodes]
    roads.append({"kind": hw, "name": tg.get("name", ""), "pts": [[round(x, 2), round(y, 2)] for x, y in pts]})

out = {"note": "Model-local metres (x along Irving St, y = -toward street, z up), house porch front at y=-2.7.",
       "terrain": {"x0": float(xs[0]), "y0": float(ys[0]), "step": STEP, "nx": len(xs), "ny": len(ys), "z": heights},
       "aerial": {"file": "geo/aerial.jpg", "uv_affine": uv_affine},
       "buildings": buildings, "roads": roads,
       "attribution": "Buildings & streets © OpenStreetMap contributors (ODbL). Aerial: MassGIS 2025 orthoimagery. "
                      "Elevation: USGS 3DEP."}
json.dump(out, open(os.path.join(OUT, "geo", "neighborhood.json"), "w"), separators=(",", ":"))
zs = np.array(heights)
print("buildings", len(buildings), "roads", len(roads), "terrain", zs.min(), zs.max(), "H0", H0)
