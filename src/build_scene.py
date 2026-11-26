"""Build the full Helloween 2026 scene (Watertown) and save helloween.blend.
Run:  python3 build_scene.py   (Blender 5.x as the `bpy` module, or: blender -b -P build_scene.py)
"""
import sys, os, math
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import bpy
from mathutils import Vector as V
from lib import *
import build_house as BH
import build_props as BP

OUT = os.path.join(HERE, "out")
REF = os.path.join(HERE, "reference")
os.makedirs(OUT, exist_ok=True)

bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene
scene.name = "Helloween_2026"
scene.unit_settings.system = "METRIC"
root = coll("Helloween_2026")

M = BH.build_all(root)
BP.build_all(root, M)

# =============================================================== controls
Cctl = coll("Lights_and_Controls", root)
ctrl = empty("Scene_Controls", (8.5, -6, 0.5), Cctl, 0.6, "SPHERE")
props = {
    "red_power": (1.0, 0.0, 5.0, "Master brightness for all red lights"),
    "window_glow": (1.0, 0.0, 5.0, "Interior light seen through windows"),
    "candle_glow": (1.0, 0.0, 5.0, "LED candles + flames"),
    "daylight": (0.0, 0.0, 1.0, "0 = Halloween night, 1 = sunny afternoon"),
}
for k, (v, lo, hi, desc) in props.items():
    ctrl[k] = v
    ui = ctrl.id_properties_ui(k)
    ui.update(min=lo, max=hi, soft_min=lo, soft_max=hi, description=desc)
ctrl["red_color"] = [1.0, 0.035, 0.022]
ctrl.id_properties_ui("red_color").update(subtype="COLOR", min=0.0, max=1.0,
                                          description="Colour of every red light")


def drive(id_block, path, expr, vars_, index=-1):
    fc = id_block.driver_add(path, index) if index >= 0 else id_block.driver_add(path)
    d = fc.driver
    d.type = "SCRIPTED"
    d.expression = expr
    for name, prop in vars_:
        v = d.variables.new()
        v.name = name
        v.type = "SINGLE_PROP"
        v.targets[0].id = ctrl
        v.targets[0].data_path = f'["{prop}"]' if "[" not in prop else prop
    return fc


def red_light(data_name, kind, energy, size_deg=60, blend=0.4, radius=0.05):
    L = bpy.data.lights.get(data_name)
    if L:
        return L
    L = bpy.data.lights.new(data_name, kind)
    L.shadow_soft_size = radius
    if kind == "SPOT":
        L.spot_size = math.radians(size_deg)
        L.spot_blend = blend
    L["base_energy"] = energy
    drive(L, "energy", f"{energy}*p*(1-d)", [("p", "red_power"), ("d", "daylight")])
    for i in range(3):
        drive(L, "color", "c", [("c", f'["red_color"][{i}]')], i)
    return L


def place_light(name, data, loc, target, C):
    ob = bpy.data.objects.new(name, data)
    C.objects.link(ob)
    ob.location = loc
    look_at(ob, target)
    return ob


Clr = coll("Red_Lights", Cctl)
wash = red_light("Red_Wash_Porch", "SPOT", 2200, 66, 0.5, 0.15)
for i, x in enumerate((-3.4, 2.6)):
    place_light(f"Red_Wash_{i + 1}", wash, (x, -7.2, 0.25), (x * 0.9, -0.5, 2.3), Clr)
up = red_light("Red_Uplight_Small", "SPOT", 45, 45, 0.3, 0.03)
for st in [o for o in bpy.data.objects if o.name.startswith("Stave_") and o.type == "EMPTY"
           and o.parent is None]:
    p = st.location
    place_light(f"Uplight_{st.name}", up, (p.x + 0.05, p.y - 0.18, 0.12), (p.x, p.y, 3.0), Clr)
for g in [o for o in bpy.data.objects if o.name.startswith("Girl_") and o.type == "MESH" and o.parent is None]:
    p = g.location
    place_light(f"Uplight_{g.name}", up, (p.x, p.y - 0.4, 0.1), (p.x, p.y, 1.6), Clr)
stake = red_light("Red_Stake_Spot", "SPOT", 120, 40, 0.5, 0.04)
mbx = MB(); mbx.smooth = False
for i, x in enumerate((-5.7, -4.5, -3.3, -2.1, -0.9)):
    place_light(f"Stake_Spot_{i + 1}", stake, (x, -7.9, 0.3), (BP.CAIRN.x + (x - BP.CAIRN.x) * 0.3,
                                                                BP.CAIRN.y, 0.5), Clr)
    mbx.box((x, -7.92, 0.28), (0.09, 0.07, 0.09), (math.radians(60), 0, 0))
    mbx.cyl((x, -7.95, 0.0), (x, -7.95, 0.24), 0.008, segs=5)
    mbx.box((x, -8.0, 0.36), (0.14, 0.01, 0.1), (math.radians(-30), 0, 0))
mbx.obj("Solar_Stake_Light_Fixtures", [M["fixture"]], Clr)

Cwl = coll("Warm_Lights", Cctl)
cand = bpy.data.lights.new("Candle_Glow", "POINT")
cand.color = (1.0, 0.62, 0.28)
cand.shadow_soft_size = 0.15
drive(cand, "energy", "6*c", [("c", "candle_glow")])
for i, p in enumerate([(1.5, -3.05, 1.05), (1.5, -3.6, 0.6), (1.5, -2.55, 1.35)]):
    o = bpy.data.objects.new(f"Candle_Glow_{i + 1}", cand); Cwl.objects.link(o); o.location = p
lan = bpy.data.lights.new("Star_Lantern_Light", "POINT")
lan.color = (1.0, 0.45, 0.15)
lan.shadow_soft_size = 0.02
drive(lan, "energy", "5*(1-d)", [("d", "daylight")])
for i, x in enumerate((0.4, 2.7)):
    o = bpy.data.objects.new(f"Star_Lantern_Light_{i + 1}", lan); Cwl.objects.link(o)
    o.location = (x, -1.3, 3.45)
for m, base in [(M["flame"], 25.0), (M["wax"], 0.6)]:
    b = m.node_tree.nodes["Principled BSDF"]
    drive(b.inputs["Emission Strength"], "default_value", f"{base}*c", [("c", "candle_glow")])
for name in ("Interior_Warm", "Interior_Red", "Interior_TV_Blue", "Interior_Dim", "Interior_Dark"):
    b = bpy.data.materials[name].node_tree.nodes["Principled BSDF"]
    base = b.inputs["Emission Strength"].default_value
    drive(b.inputs["Emission Strength"], "default_value", f"{base}*w*(1-0.85*d)",
          [("w", "window_glow"), ("d", "daylight")])
for name, base in (("String_LED_Red", 40.0), ("String_LED_Warm", 25.0), ("Star_Lantern_Glass", 6.0)):
    b = bpy.data.materials[name].node_tree.nodes["Principled BSDF"]
    drive(b.inputs["Emission Strength"], "default_value", f"{base}*(1-0.9*d)", [("d", "daylight")])

# night ambience (street glow / moon) and the daylight sun
night = bpy.data.lights.new("Night_Street_Fill", "SUN")
night.color = (0.72, 0.8, 1.0)
night.angle = math.radians(25)
drive(night, "energy", "0.12*(1-d)", [("d", "daylight")])
o = bpy.data.objects.new("Night_Street_Fill", night); Cctl.objects.link(o)
o.rotation_euler = (math.radians(62), 0, math.radians(-28))
sun = bpy.data.lights.new("Day_Sun", "SUN")
sun.color = (1.0, 0.93, 0.82)
sun.angle = math.radians(1.5)
drive(sun, "energy", "4.5*d", [("d", "daylight")])
o = bpy.data.objects.new("Day_Sun", sun); Cctl.objects.link(o)
o.rotation_euler = (math.radians(58), 0, math.radians(-40))

# world: night navy <-> day sky
w = bpy.data.worlds.new("Sky")
scene.world = w
w.use_nodes = True
nt = w.node_tree
bg = nt.nodes["Background"]
bg.inputs["Color"].default_value = (0.004, 0.007, 0.022, 1)
bg.inputs["Strength"].default_value = 1.0
bg2 = nt.nodes.new("ShaderNodeBackground")
bg2.inputs["Color"].default_value = (0.42, 0.6, 0.95, 1)
bg2.inputs["Strength"].default_value = 1.0
mix = nt.nodes.new("ShaderNodeMixShader")
outn = nt.nodes["World Output"]
nt.links.new(bg.outputs[0], mix.inputs[1])
nt.links.new(bg2.outputs[0], mix.inputs[2])
nt.links.new(mix.outputs[0], outn.inputs["Surface"])
drive(mix.inputs["Fac"], "default_value", "d", [("d", "daylight")])

# =============================================================== cameras (+ reference photos)
Ccam = coll("Cameras", root)
PHOTOS = {  # camera -> (reference photo, location, target, lens)
    "Cam_01_Street_Wide": ("IMG_9899.jpeg", (1.0, -17.6, 1.35), (-0.7, -1.0, 4.4), 23),
    "Cam_02_Yard_Front": ("IMG_0133.jpeg", (-0.8, -12.3, 1.3), (-0.9, -2.0, 3.6), 25),
    "Cam_03_Ritual": ("IMG_0134.jpeg", (-2.3, -9.3, 1.55), (-2.6, -3.0, 1.75), 25),
    "Cam_04_Horned_Figure": ("IMG_0135.jpeg", (1.5, -5.1, 1.0), (1.5, -2.8, 2.05), 26),
    "Cam_05_Low_Angle": ("IMG_0137.jpeg", (1.45, -3.75, 0.75), (1.5, -2.85, 2.6), 22),
    "Cam_06_Horns_Closeup": ("IMG_0136.jpeg", (1.05, -3.55, 1.65), (1.5, -2.9, 2.9), 30),
    "Cam_07_Jawbone_Girl": ("IMG_0138.jpeg", (-3.92, -3.78, 1.2), (-3.3, -3.36, 1.12), 32),
    "Cam_08_Overhead": ("IMG_0140.jpeg", (-3.2, -7.6, 3.9), (-3.3, -5.0, 0.2), 24),
}
for name, (photo, loc, tgt, lens) in PHOTOS.items():
    cd = bpy.data.cameras.new(name)
    cd.lens = lens
    cd.sensor_fit = "AUTO"
    cd.clip_start = 0.05
    cam = bpy.data.objects.new(name, cd)
    Ccam.objects.link(cam)
    cam.location = loc
    look_at(cam, tgt)
    cam["reference_photo"] = photo
    pth = os.path.join(REF, photo)
    if os.path.exists(pth):
        img = bpy.data.images.load(pth, check_existing=True)
        bgi = cd.background_images.new()
        bgi.image = img
        bgi.alpha = 0.5
        cd.show_background_images = True
scene.camera = bpy.data.objects["Cam_01_Street_Wide"]

# =============================================================== render settings
r = scene.render
r.engine = "CYCLES"
r.resolution_x, r.resolution_y = 1080, 1440
r.resolution_percentage = 100
c = scene.cycles
c.device = "CPU"
c.samples = 96
c.use_adaptive_sampling = True
c.adaptive_threshold = 0.02
c.use_denoising = True
c.max_bounces = 6
c.caustics_reflective = c.caustics_refractive = False
c.sample_clamp_indirect = 4.0
try:
    scene.view_settings.view_transform = "AgX"
    scene.view_settings.look = "AgX - Medium High Contrast"
except Exception as e:
    print("look:", e)
scene.view_settings.exposure = 0.0

# README inside the .blend
txt = bpy.data.texts.new("README")
txt.write(open(os.path.join(HERE, "BLEND_README.txt")).read())

bpy.context.view_layer.update()
if "--nosave" not in sys.argv:
    bpy.ops.file.pack_all()
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(OUT, "helloween.blend"), compress=True)
    print("SAVED", os.path.join(OUT, "helloween.blend"))
