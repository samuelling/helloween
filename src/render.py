"""Render cameras from helloween.blend.
python3 render.py <outdir> <percent> <samples> [daylight] Cam_01 Cam_02 ...
"""
import sys, os, bpy
args = sys.argv[1:]
outdir, pct, spp = args[0], int(args[1]), int(args[2])
rest = args[3:]
day = None
if rest and rest[0].replace(".", "").isdigit():
    day = float(rest[0]); rest = rest[1:]
HERE = os.path.dirname(os.path.abspath(__file__))
bpy.ops.wm.open_mainfile(filepath=os.path.join(HERE, "out", "helloween.blend"))
s = bpy.context.scene
if day is not None:
    s.objects["Scene_Controls"]["daylight"] = day
s.render.resolution_percentage = pct
s.cycles.samples = spp
os.makedirs(outdir, exist_ok=True)
cams = rest or [o.name for o in s.objects if o.type == "CAMERA"]
for c in cams:
    s.camera = s.objects[c]
    s.render.filepath = os.path.join(outdir, c + ("_day" if day else "") + ".png")
    bpy.ops.render.render(write_still=True)
    print("RENDERED", s.render.filepath)
