"""Shape preview of HQ builders (no bake): python3 hq_pv.py out_dir pid [pid...]"""
import sys, os, time
sys.argv = [sys.argv[0], "/tmp/pvprops"] + sys.argv[1:]
OUTD = sys.argv[2]; PIDS = sys.argv[3:]
sys.argv = [sys.argv[0], "/tmp/pvprops"]
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bpy
import props_hq as PH
import hq_preview as PV
from mathutils import Vector as V
os.makedirs(OUTD, exist_ok=True)
for pid in PIDS:
    t = time.time()
    M = PH.fresh()
    fn, tex = PH.HQ[pid]
    try:
        fn(M)
    except Exception:
        import traceback; traceback.print_exc(); continue
    bpy.context.view_layer.update()
    lo, hi = V((1e9,) * 3), V((-1e9,) * 3)
    tris = 0
    for o in bpy.context.scene.objects:
        if o.type == "MESH":
            for c in o.bound_box:
                p = o.matrix_world @ V(c); lo = V(map(min, lo, p)); hi = V(map(max, hi, p))
            tris += sum(len(p.vertices) - 2 for p in o.data.polygons)
    c = (lo + hi) / 2; size = max(hi - lo) * 1.15
    PV.views(f"{OUTD}/{pid}.png", tuple(c), ortho=size, res=360, dirs=((0, -1, 0.15), (-1, 0, 0.15), (-0.7, -0.75, 0.45)))
    print("PV", pid, round(time.time() - t), "s", tris, "tris", flush=True)
