# helloween

Our Watertown Halloween 2026 yard, rebuilt in Blender from photos. Live at **[linglab.org/helloween](https://linglab.org/helloween)**.

- `index.html`: interactive three.js viewer. Use the camera presets to see the views matched to the photos, slide from night to day, or recolour the red lights.
- `blend/helloween.blend`: the editable Blender 5.3 scene. Select `Scene_Controls` for the main knobs. Twelve skeletons are rigged and poseable, every camera shows its reference photo as a background, and a README is packed inside the file.
- `src/`: procedural build scripts. `python3 build_scene.py` regenerates the whole scene (it needs `pip install bpy` or `blender -b -P`). `render.py` renders the cameras, and `export_web.py` writes `scene.glb` and `scene.json` for the viewer.
- `renders/`, `photos/`: Cycles renders and the photos they were matched to.
