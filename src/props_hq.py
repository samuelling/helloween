"""HQ rebuilds of the prop arsenal: sculpted SDF forms, simulated cloth, and baked PBR texture atlases
(colour+AO, roughness/metal, normal, emission), exported as GLB with JPEG textures, then quantized.

python3 props_hq.py <out_dir> [prop_id ...]
"""
import sys, os, json, time, traceback, subprocess
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import bpy
import props_lib as PL
import build_props as BP
import hq_lib as H

OUT = PL.OUT
GT = "/tmp/gt/node_modules/.bin/gltf-transform"
from hq_registry import HQ, hq


def convert_curves():
    s = bpy.context.scene
    dg = bpy.context.evaluated_depsgraph_get()
    for ob in list(s.objects):
        if ob.type in ("CURVE", "FONT"):
            me = bpy.data.meshes.new_from_object(ob.evaluated_get(dg), depsgraph=dg)
            new = bpy.data.objects.new(ob.name, me)
            s.collection.objects.link(new)
            new.parent = ob.parent
            new.matrix_world = ob.matrix_world.copy()
            for ch in list(ob.children):
                mw = ch.matrix_world.copy(); ch.parent = new; ch.matrix_world = mw
            bpy.data.objects.remove(ob)
    bpy.context.view_layer.update()


def quantize(path):
    if not os.path.exists(GT):
        return
    tmp = path + ".q.glb"
    r = subprocess.run([GT, "meshopt", path, tmp, "--level", "medium"], capture_output=True, text=True)
    if r.returncode == 0 and os.path.exists(tmp):
        os.replace(tmp, path)
    else:
        print("quantize failed", r.stderr[-400:])


def finalize(pid, info, tex):
    convert_curves()
    meshes = [o for o in bpy.context.scene.objects if o.type == "MESH" and len(o.data.polygons)]
    t = time.time()
    H.bake_atlas(meshes, pid, tex)
    print(f"  bake {pid}: {time.time() - t:.0f}s", flush=True)
    PL.IMG_FMT = "JPEG"
    info = PL.finalize_and_export(pid, info)
    path = os.path.join(OUT, pid + ".glb")
    quantize(path)
    info["kb"] = os.path.getsize(path) // 1024
    info["hq"] = True
    return info


def fresh():
    M = PL.fresh()
    H.library(M)
    return M


# ====================================================================== builders
from hq_props_bones import *      # noqa: E402,F401  (registers via @hq)
from hq_props_occult import *     # noqa: E402,F401
from hq_props_grave import *      # noqa: E402,F401
from hq_props_figures import *    # noqa: E402,F401


if __name__ == "__main__":
    cat_path = os.path.join(OUT, "catalog.json")
    catalog = json.load(open(cat_path)) if os.path.exists(cat_path) else {}
    ONLY = PL.ONLY
    for pid, (fn, tex) in HQ.items():
        if ONLY and pid not in ONLY:
            continue
        t0 = time.time()
        try:
            M = fresh()
            info = fn(M)
            info = finalize(pid, info, tex)
            catalog = json.load(open(cat_path)) if os.path.exists(cat_path) else {}   # re-read: other runners may have written
            old = catalog.get(pid, {})
            catalog[pid] = {**old, **info}
            if "order" not in catalog[pid]:
                catalog[pid]["order"] = len(catalog)
            json.dump(catalog, open(cat_path, "w"), indent=1)
            print("PROP_OK", pid, catalog[pid]["kb"], "KB", catalog[pid]["tris"], "tris", f"{time.time() - t0:.0f}s", flush=True)
        except Exception:
            print("PROP_FAIL", pid, flush=True)
            traceback.print_exc()
