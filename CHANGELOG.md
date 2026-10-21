# Changelog

## 0.4.0 - unreleased

- Rocks and crystals: every map carries its own procedural 3D models (.s3o) and feature definitions;
  rock clusters gather at slopes, glowing crystals on alien and moon maps; all reclaimable.
- Battlefield wrecks of Zero-K units between the bases (reclaimable metal). New general settings "Rocks"
  and "Wrecks"; the check report lists the reclaim metal; the app shows them (layer "Features").
- Textures: snow only on gentle slopes with rocks poking through, sediment bands, light rims and dark
  cracks on rock, scree at the foot of cliffs, wet sand and foam at the water line, shallow water
  gradient, driven paths on carved ramps.
- Faster previews (noise and masks computed separably, about 2x faster overall).
- Hidden watermark in every map: a keyed pattern over the heightmap (about 0.04 elmos, invisible) plus a
  record in the lowest height bits (tool version, template, seed, build date, build id). `atlasforge verify
  map.sdz` and "Check a map file" in the app's Settings tell whether a map was made with Atlas Map Forge.
  Tested against 353 Zero-K maps (no false alarm) and after re-packing, smoothing, re-quantising and
  local edits of the heightmap.
- Advanced mode (Settings, with a warning): lifts the limits of every map setting - sizes 4-32, more
  gates/fords/rings, extreme heights and timings. Values beyond the safe range are shown in orange.
- General settings for every template: metal amount, tree density, erosion.
- Erosion: simulated rain carves gullies and valleys into natural slopes; start areas, metal spots,
  chokes, walls and ramps are protected. If erosion would cut a route, it is lowered automatically.
- Seamless symmetry: the noise is made symmetric with a blend at the dividing line before anything is
  built on it, so mirrored maps no longer show a crease along the centre (River, Arena, Chokepoint,
  Volcano, procedural maps).
- Ramps carved by the procedural generator no longer leave fans of radial streaks at tight bends.

## 0.3.1 - merged into 0.4.0

- Every map carries the `Forge` name prefix, the FORGE badge and the credit line; these are no longer
  settings. The author name is the only setting and is required to build (app and command line).
- The app asks for the author name on the first start; "Build map" stays disabled without it.
- Volcano: lava bombs only hit solid ground on the volcano island and the ring (precomputed spots, never in
  the lava), bigger impacts (new setting "Lava bomb size", default radius 320 instead of 170) with more
  splash effects; bomb zones shown in the app (Danger layer, amber).

## 0.3.0 - 2026-10-21

- The app (`atlasforge app`, Windows program `AtlasMapForge.exe`): template gallery, controls built from
  the template parameters, seed dice, automatic preview.
- Large zoomable map preview: metal spots with values, geovents, start points and start boxes, chokes,
  dangerous ground, grid, and "Where can it go?" per unit class; height and passable unit classes under
  the mouse.
- Check report, map facts, Build & install with progress, existing map versions detected (next free
  version suggested), "Show file".
- Settings in the app: author, prefix, badge, credit line, Zero-K folder, output folder.
- Windows build with PyInstaller and a self-test of the packed program (`--selftest --build`).

## 0.2.0 - unreleased

- Six map templates with declared parameters: Procedural Skirmish, Chokepoint Front, River Crossing,
  Arena (4 players), Volcano, Chicken Defense.
- Pipeline `atlasforge.forge`: design, plain-English check report, quick preview (about 1 second), build.
- Commands `templates`, `preview`, `build` with `--set key=value`.
- Check report knows about lava (ground nobody survives) and template-specific checks.
- Chicken zones gadget keeps chicken roosts out of the player area.

## 0.1.0 - unreleased

- First package version: procedural skirmish maps from the command line.
- Map gadgets: lava cliffs, lava tide warning, volcano eruption (used by templates later).
- Settings for author, name prefix and FORGE badge; maps credit "Made with Atlas Map Forge."
- Install into Zero-K with lobby minimap and thumbnail.
