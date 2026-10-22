# Roadmap

Features first, balance tools after them.

## 0.1 - foundation (done)

Generator core, command line, user settings, Windows and Linux, automatic tests.

## 0.2 - templates (done)

Six templates with declared parameters, quick preview, plain-English check report.

## 0.3 - Windows app (done)

Local web interface in its own window: template gallery, large zoomable preview with overlays, check
report, build & install with progress. One-file Windows program built and self-tested on GitHub.

## 0.4 - terrain quality and control (done)

- Done: seamless symmetry, erosion, smoother ramps, advanced mode, hidden watermark with `atlasforge
  verify`, fixed Forge prefix and badge, author required, textures (snow, rock, scree, shore, paths),
  rocks, crystals and Zero-K wrecks (reclaim), template picker with filters, general settings on every map
  (metal spots, metal per spot, geothermal vents, wind, tidal, trees, rocks, wrecks, erosion) with an info
  popup for every setting, build-finished dialog.
- Done: more biomes (jungle, swamp, industrial), a painted sky per map, engine grass, time of day.

## 0.5 - more ways to play and more templates

- Done: free-for-all for 3 to 8 players (rotational symmetry, one start box per player, FFA Ring template).
  Open: naval free-for-all with several ports.
- Team games 2v2 to 5v5 with several start points per box.
- Done: sea templates (Open Sea, Archipelago, Island Straits, Coastal Front, Atoll) with a naval check
  profile; Three Lanes.
- In progress (template agent): smoother underwater transitions on sea maps.
- Next templates: Open Dunes, Twin Plateaus, Lake District, River Delta, Fjord Coast; later Canyon Network,
  Mountain Spine, King of the Hill, Fortress Front, Crater Basin, Inland Sea, Island Continents,
  Peninsula, Team Battlefront, Chicken Mesa, Chicken Three Fronts, City Grid.

## 0.6 - twists (map gadgets)

- Meteor showers, control points with bonuses, crumbling passes, supply drops, day and night, siege.

## 0.7 - balance and testing

- Fairness check: travel times per unit class to metal, centre and enemy, metal per side, high ground.
- Metal layout in expansion stages; metal total by map size.
- "Test in Zero-K": start the map against the AI from the app; AI-vs-AI quick run with a short report.
- Map values: gravity, extractor radius (wind and tidal are done).

## App and distribution (alongside)

- Next: Windows program attached to GitHub Releases as a direct download, code-signed through the SignPath
  Foundation (signing inside the GitHub Actions build).
- Map codes (template + settings + seed as short text) to share and paste; compare two seeds side by side.
- Start-up time of the one-file program, update notice.
- Upload helper for zero-k.info, name collision check.

## 1.0 - release

Quick-start guide with pictures, template gallery, talk to the Zero-K moderators before announcing.

## Later

- Beyond All Reason (BAR) profile.
- Mapper tools: move metal spots and start points in the preview, layout files, a simple layout editor.
- Online configurator with preview; in-game generation from a seed.
