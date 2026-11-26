# helloween

Our Watertown Halloween 2026 yard, rebuilt in Blender from photos. Live at **[linglab.org/helloween](https://linglab.org/helloween)**.

- **Walk mode:** press *Walk around* or open [linglab.org/helloween/#walk](https://linglab.org/helloween/#walk). WASD or arrow keys move, the mouse looks, Shift runs, Space jumps, F toggles a flashlight and Esc brings the menu back. On a phone, drag the left half of the screen to move and the right half to look. Collision uses a BVH (`walk.js`), so you climb the porch steps and can't walk through walls or skeletons.
- `neighborhood.js` + `geo/`: the real block around the house, which you can walk. It has terrain from USGS 3DEP elevation draped with the MassGIS 2025 aerial photo, and OpenStreetMap building footprints extruded into houses with hip roofs textured from that aerial. Heights are estimated from footprint area because none of the sources record them. `src/geo_build.py` rebuilds it; the files store model-local metres only (no lat/lon). Data: © OpenStreetMap contributors (ODbL), MassGIS, USGS.
- **Decorate mode** (`decorator.js`, `poses.js`, `props/`): a drawer of 54 props sculpted in Blender by `src/props_hq.py` (originals: `src/props_lib.py`). Categories are Occult, Bones, Creatures, Ghouls, Graveyard, Spooky stuff and the 2026 display pieces, plus 10 light types and 4 effects. The Occult set has 18 séance and coven pieces: séance table with a spirit board, ritual circle, hooded cultists, crimson acolytes, kneeling and headless worshippers, levitating woman, black altar, horned idol, sigil banner, a painted sigil that sticks to walls, black candles, miniature house, inverted cross, burning wicker effigy, crown under glass, hanging poppets and shrouded mirror. It also adds a hellfire pit, a blacklight, a blood-moon sky and a positional coven chant (synthesized audio that gets louder as you approach).
  - **Placing:** click a prop, then click any surface (lawn, porch, roof). Shift-click places several.
  - **Editing:** W/E/R switch between move, rotate and scale; D duplicates, G drops to the ground, Del deletes, ⌘Z undoes.
  - **Articulator:** the skeleton, skeleton hound, giant spider, bone serpent and lawn tentacles are rigged. Use the pose presets (crawl, emerging from grave, kneel, sit, zombie, wave, dance; sit and howl for the hound; rear up and pounce for the spider; coil and S-curve for the chains), or click *Pose joints* and rotate any joint.
  - **Lights:** spotlight, floodlight, uplight, searchlight with a visible beam, orb, tiki torch, strobe and colour wash, each with colour, brightness, cone, soft edge and shadows, plus flicker, pulse, strobe, hue-cycle and sweep effects. Lightning storm and ground fog are under Effects.
  - **Originals:** hide groups of the original display (skeletons, girls, staves, cairn, horned figure, porch props, red lights) to replace them.
  - **Saving:** layouts autosave in the browser and can be saved to or loaded from a JSON file. Share copies a link with the whole design compressed into it.
- `index.html`: interactive three.js viewer. Use the camera presets to see the views matched to the photos, slide from night to day, or recolour the red lights.
- `blend/helloween.blend`: the editable Blender 5.3 scene. Select `Scene_Controls` for the main knobs. Twelve skeletons are rigged and poseable, every camera shows its reference photo as a background, and a README is packed inside the file.
- `src/`: procedural build scripts. `python3 build_scene.py` regenerates the whole scene (it needs `pip install bpy` or `blender -b -P`). `render.py` renders the cameras, and `export_web.py` writes `scene.glb` and `scene.json` for the viewer.
- `renders/`, `photos/`: Cycles renders and the photos they were matched to.

### HQ sculpts

All 54 props are re-sculpted at much higher quality (`src/props_hq.py`). Think of it as swapping LEGO for clay:

- **Sculpting** (`src/sdf.py`): each form is a signed-distance field, built from anatomical landmarks and reference images (a human skull from glabella/zygion/gnathion measurements, cervid skulls, canine skull, vertebrae, ribs, ilium bowls, hands with phalanges). Pieces are blended with smooth unions, sockets and openings are carved with smooth subtractions, and surface detail comes from fbm/ridged noise and domain warping. Marching cubes turns the field into a mesh, which is relaxed and decimated to a budget.
- **Drapery**: tablecloths, the altar runner, the banner, the mirror shroud and the ghost's sheet are Blender cloth simulations; robes use fold-modulated solids of revolution.
- **Baking** (`src/hq_lib.py`): every material (procedural colour, bump, roughness, metal, emission, painted textures such as the spirit board and sigil cloth) is baked into one atlas per prop — colour × ambient occlusion, a tangent normal map, roughness/metal and emission — so the detail survives the trip to the browser.
- **Size**: JPEG textures plus meshopt geometry compression keep most props at 0.3–1 MB.

Rigged props keep their bone names, so poses and the articulator still work.
