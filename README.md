# Atlas Map Forge

A map generator for [Zero-K](https://zero-k.info). It builds complete, ready-to-play `.sdz` maps:
heightmap, high-resolution texture, minimap, metal spots, geovents, start boxes, trees, and optional
map gadgets such as lava cliffs, lava tides and an erupting volcano.

> **Status: early development (0.1).** The command line works today. A Windows app with a visual
> preview and ready-made map templates is in progress, see the [roadmap](docs/ROADMAP.md).

## What you get

- **Playable maps:** every map is checked with the engine's own slope rules. Ramps are carved
  automatically until tanks can reach the enemy base and every metal spot.
- **Good looks:** biome palettes (temperate, desert, arctic, volcanic, ashland, alien, moon, autumn),
  slope-based rock, shores, detail normal maps, splat materials and soft terrain transitions.
- **Fair layouts:** two-team symmetry (diagonal, north/south, east/west) for terrain and resources.
- **Map gadgets:** maps can carry their own Lua rules, for example damaging lava on cliffs that only
  spiders can climb, or lava tides with an on-screen countdown.
- **Your name on it:** maps are named `<prefix> <title> v<version>`, carry your author name and show a
  small FORGE badge in the map browser (not in game).

## Install (command line)

Python 3.9 or newer:

```
pip install git+https://github.com/Scuide/atlas-map-forge
```

## Quick start

```
atlasforge config --author "YourName"
atlasforge procedural --title "Ashfall Ridge" --size 12 12 --biome volcanic --style plateaus --seed 7 --install
```

This builds `Forge Ashfall Ridge v1.sdz`, a preview image, and copies the map into your Zero-K folder
(found automatically for Steam installs; otherwise pass `--install "C:\path\to\Zero-K"`).

Options of `atlasforge procedural`:

| Option | Meaning |
|---|---|
| `--size W H` | map size in Spring units, even numbers from 4 to 32 (12 12 is a typical 1v1/2v2 size) |
| `--biome` | temperate, desert, arctic, volcanic, ashland, alien, moon, autumn |
| `--style` | hills, plateaus, canyon, islands, crater |
| `--layout` | diag (NW vs SE), ns (north vs south), ew (west vs east) |
| `--seed` | any number; the same seed builds the same map |
| `--relief` | height scale, 1.0 = default |
| `--mex` | metal spots per side |
| `--version` | version number in the map name; raise it when you change a map you already shared |

Settings (`atlasforge config`): `--author`, `--prefix` (empty for none), `--badge forge|none`,
`--no-credit` (drop "Made with Atlas Map Forge." from the description).

### Seeing your map in the lobby

Zero-K's map list only shows local maps when **"Only show featured maps"** is switched off in the lobby
settings. The installer also writes a minimap picture for the lobby.

### Sharing maps

Upload the `.sdz` on [zero-k.info](https://zero-k.info/Maps) so other players download it
automatically. Please give every changed map a new version number: two different files with the same
map name cause download conflicts.

## Development

```
pip install -e .[test]
pytest
```

Code layout:

| Module | Purpose |
|---|---|
| `atlasforge.terrain` | terrain building blocks (plateaus, pits, ring walls, roads, ramps), engine slope test |
| `atlasforge.procedural` | procedural skirmish maps |
| `atlasforge.render`, `materials` | texture, paint layers (lava, ice, scorch, concrete), detail materials |
| `atlasforge.formats`, `archive` | SMF/SMT/DDS writers, mapinfo and config files, the .sdz archive |
| `atlasforge.checks` | reachability per movement class |
| `atlasforge.gadgets` | map gadgets (Lua) and their settings |
| `atlasforge.install` | find Zero-K, install maps |

## License

GPL-2.0-or-later, see [LICENSE](LICENSE). Bundled font: Inter Display (SIL Open Font License),
see `atlasforge/assets/InterDisplay-LICENSE.txt`. Maps you build are yours.

Zero-K and the Recoil engine are separate projects; this tool only writes files they can load.
