# Changelog

## 0.3.0 - unreleased

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
