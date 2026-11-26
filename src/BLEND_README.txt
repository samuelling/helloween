HELLOWEEN — Watertown, Halloween 2026
==========================================
A procedural, fully editable rebuild of the yard display from the reference photos.
Units are metres. +Y points into the house, -Y toward the street, and the porch floor is at z = 1.1.

QUICK CONTROLS  (select the "Scene_Controls" empty -> Object Properties -> Custom Properties)
  red_power    master brightness for every red light
  red_color    one colour for all red lights (try green or purple)
  window_glow  interior light seen through the windows
  candle_glow  LED candles on the steps
  daylight     0 = Halloween night, 1 = sunny afternoon (matches the daytime photos)

COLLECTIONS
  House / Porch / Ground   siding, trim, shutters, dormer, turned posts, brackets, railings, steps, lattice
  Skeletons                12 rigged skeletons. Select a *_Rig -> Pose Mode to repose it.
                           All of them share one mesh, so editing the mesh changes every skeleton.
                           The rig's "pose_preset" property shows which preset it started from.
  Girls                    three mannequin girls (the centre girl wears the jawbone headpiece)
  Antler_Staves            each stave is an Empty; move or rotate the Empty and its pole, skull
                           and antlers follow. Antlers are curves, so you can edit their points.
  Cairn                    46 individual stones built from 4 shared rock meshes, plus the elk skull and string lights
  Horned_Figure            tan-gown mannequin, oryx skull (Empty "Oryx_Skull"), cascading LED candles
  Porch_Props              rocking chairs, wreaths, ram horns, star lanterns, pumpkins
  Lights_and_Controls      red spot lights. Uplights share one light datablock and stake spots share
                           another, so changing one changes them all.
  Cameras                  each camera matches a reference photo, which is shown at 50% as the
                           camera background when you look through it (Numpad 0).

Everything is rebuilt by build_scene.py (in the helloween repo). Change a number there and re-run it.
