# Roadmap

## 0.1 - foundation (done)

- Python package `atlasforge` with the generator core: terrain blocks, texture renderer, file formats,
  archive, reachability checks, map gadgets.
- Command line: `procedural`, `config`, `find-zerok`, `install`.
- User settings: author, name prefix, FORGE badge, credit line.
- Works on Windows (spawn) and Linux (fork); automatic tests in CI.

## 0.2 - templates (done)

Ready-made map templates with declared parameters (name, type, range, default, description), so the app
can build its controls automatically:

| Template | Parameters (examples) |
|---|---|
| Procedural Skirmish | size, biome, style, symmetry, relief |
| Chokepoint Front | number of gates, gate types (level, hump, water), wall height |
| River Crossing | fords, bridges, lava tides on/off |
| Arena (4 players) | ring size, gates, rich centre |
| Volcano | size, eruption interval, bomb damage |
| Chicken Defense | shape, entrances |

Fast preview (heightmap, metal spots, start points) in a few seconds, plain-English check report.

## 0.3 - Windows app (done, first Windows build pending)

- Web interface in its own window, optimised for looking at the map: large zoomable preview,
  overlays for metal spots, start boxes and the routes each unit class can take.
- Template gallery, sliders, seed dice, "Build & install" with progress.
- Finds the Zero-K folder automatically; one-file download from GitHub Releases.

## 1.0 - release

- Quick-start guide with pictures, template gallery.
- Talk to the Zero-K moderators before announcing (forum/Discord).

## Later

- Beyond All Reason (BAR) profile.
- Advanced mapping: layout files with free building blocks, a simple layout editor.
- More twists: meteor showers, supply drops, control points, crumbling walls, day/night.
- Online configurator with preview; in-game generation from a seed.
- Upload helper for zero-k.info, name collision check.
