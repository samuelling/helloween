"""Fast shape check: workbench renders of the current scene from front / side / 3-quarter, tiled into one PNG.
usage (inside a script): import hq_preview; hq_preview.views(out_png, target=(0,0,0), dist=0.6)"""
import bpy, math, os
import numpy as np
from mathutils import Vector as V
from lib import look_at


def views(path, target=(0, 0, 0), dist=0.6, res=320, dirs=((0, -1, 0.05), (-1, 0, 0.05), (-0.7, -0.75, 0.35), (0.2, -0.5, -0.6)), ortho=None):
    sc = bpy.context.scene
    sc.render.engine = "BLENDER_WORKBENCH"
    sc.display.shading.light = "STUDIO"; sc.display.shading.color_type = "MATERIAL"
    sc.display.shading.show_cavity = True; sc.display.shading.cavity_type = "BOTH"
    sc.display.shading.show_shadows = False
    sc.render.resolution_x = sc.render.resolution_y = res
    sc.render.film_transparent = False
    cam = bpy.data.objects.get("_pv") or bpy.data.objects.new("_pv", bpy.data.cameras.new("_pv"))
    if cam.name not in sc.collection.objects:
        sc.collection.objects.link(cam)
    sc.camera = cam
    cam.data.type = "ORTHO"; cam.data.ortho_scale = ortho or dist
    tiles = []
    for i, d in enumerate(dirs):
        d = V(d).normalized()
        cam.location = V(target) + d * 3; look_at(cam, target)
        cam.data.clip_end = 10
        p = f"/tmp/_pv{i}.png"; sc.render.filepath = p
        bpy.ops.render.render(write_still=True)
        im = bpy.data.images.load(p)
        tiles.append(np.array(im.pixels[:]).reshape(res, res, 4)); bpy.data.images.remove(im)
    row = np.concatenate(tiles, axis=1)
    out = bpy.data.images.new("_pvout", row.shape[1], row.shape[0])
    out.pixels.foreach_set(row.astype(np.float32).ravel()); out.filepath_raw = path; out.file_format = "PNG"; out.save()
    bpy.data.images.remove(out)
