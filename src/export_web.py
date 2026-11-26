"""Export helloween.blend -> web/scene.glb (+ scene.json with cameras & lights) for the three.js viewer."""
import os, sys, json, math, bpy
from mathutils import Vector as V
HERE = os.path.dirname(os.path.abspath(__file__))
WEB = sys.argv[-1] if len(sys.argv) > 1 and sys.argv[-1].endswith("web") else os.path.join(HERE, "web")
os.makedirs(WEB, exist_ok=True)
bpy.ops.wm.open_mainfile(filepath=os.path.join(HERE, "out", "helloween.blend"))
s = bpy.context.scene
dg = bpy.context.evaluated_depsgraph_get()

def gl(v):  # Blender Z-up -> glTF Y-up
    return [round(v.x, 4), round(v.z, 4), round(-v.y, 4)]

# ---- cameras + lights to JSON (evaluated, drivers resolved)
info = {"cameras": [], "lights": []}
for ob in sorted([o for o in s.objects if o.type == "CAMERA"], key=lambda o: o.name):
    fwd = ob.matrix_world.to_3x3() @ V((0, 0, -1))
    pos = ob.matrix_world.translation
    info["cameras"].append({"name": ob.name, "photo": ob.get("reference_photo", ""), "pos": gl(pos),
                            "target": gl(pos + fwd * 4.0),
                            "vfov": round(math.degrees(2 * math.atan(18 / ob.data.lens)), 2)})
for ob in s.objects:
    if ob.type != "LIGHT":
        continue
    ev = ob.evaluated_get(dg)
    L = ev.data
    fwd = ob.matrix_world.to_3x3() @ V((0, 0, -1))
    pos = ob.matrix_world.translation
    d = {"name": ob.name, "data": ob.data.name, "type": L.type, "pos": gl(pos), "target": gl(pos + fwd * 3),
         "color": [round(c, 4) for c in L.color], "watts": round(L.energy, 3)}
    if L.type == "SPOT":
        d["angle"] = round(L.spot_size / 2, 4)
        d["blend"] = round(L.spot_blend, 3)
    d["red"] = ob.data.name.startswith("Red_")
    info["lights"].append(d)

# ---- bake skeleton poses and curves into plain meshes
for ob in list(s.objects):
    if ob.type == "MESH" and any(m.type == "ARMATURE" for m in ob.modifiers):
        me = bpy.data.meshes.new_from_object(ob.evaluated_get(dg), preserve_all_data_layers=False,
                                             depsgraph=dg)
        mw = ob.matrix_world.copy()
        ob.modifiers.clear()
        ob.data = me
        ob.parent = None
        ob.matrix_world = mw
for ob in list(s.objects):
    if ob.type in ("CURVE", "FONT"):
        me = bpy.data.meshes.new_from_object(ob.evaluated_get(dg), depsgraph=dg)
        new = bpy.data.objects.new(ob.name, me)
        for c in ob.users_collection:
            c.objects.link(new)
        new.matrix_world = ob.matrix_world.copy()
        bpy.data.objects.remove(ob)
for ob in list(s.objects):
    if ob.type in ("ARMATURE", "LIGHT", "CAMERA"):
        bpy.data.objects.remove(ob)
bpy.context.view_layer.update()

# drivers would re-evaluate emission on export; freeze them at their night values
for m in bpy.data.materials:
    if m.node_tree and m.node_tree.animation_data:
        for fc in list(m.node_tree.animation_data.drivers):
            m.node_tree.driver_remove(fc.data_path, fc.array_index)

# procedural colour (noise ramps) doesn't survive glTF: bake each to its flat representative colour
for m in bpy.data.materials:
    if not m.node_tree:
        continue
    b = m.node_tree.nodes.get("Principled BSDF")
    if b and b.inputs["Base Color"].is_linked:
        for l in list(b.inputs["Base Color"].links):
            m.node_tree.links.remove(l)
        b.inputs["Base Color"].default_value = m.diffuse_color
    for inp in ("Normal",):
        if b and b.inputs[inp].is_linked:
            for l in list(b.inputs[inp].links):
                m.node_tree.links.remove(l)

bpy.ops.export_scene.gltf(filepath=os.path.join(WEB, "scene.glb"), export_format="GLB",
                          export_apply=True, export_lights=False, export_cameras=False,
                          export_draco_mesh_compression_enable=True, export_draco_mesh_compression_level=7,
                          export_yup=True, export_extras=False)
json.dump(info, open(os.path.join(WEB, "scene.json"), "w"), indent=1)
print("EXPORTED", os.path.getsize(os.path.join(WEB, "scene.glb")) // 1024, "KB")
