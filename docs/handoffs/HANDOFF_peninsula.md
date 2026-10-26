# TPL-peninsula-1 Handoff

## Delivery

Template: `peninsula` (Peninsula)  
Requested integration base: current Core `main` (assignment supplied no commit ID).  
Template workspace base: `571d63c`  
Package: `TPL-peninsula-1`

Selected files:

- `atlasforge/templates/peninsula.py`
- `tests/test_template_peninsula.py`
- `docs/template_briefs/peninsula.json`

Registry registration and watermark assignment remain with the Core integration owner. The worktree already contained unrelated, concurrent changes; they are excluded from this package.

## Design

Paired land tongues extend from the west and east home shores, narrowing through a defendable neck and widening into forward heads. The heads stop short of the center, leaving an open deep-water crossing. Their long outer coasts support side landings. Tests cover the standard map check, connected home ground and naval routes, east-west symmetry, determinism, metadata serialization and safe geometry parameter bounds.

## Verification

- `python F:\Paperclip\tools\qa.py quick peninsula`: not run. The required local registry edit was rejected by the automatic approval reviewer because registry changes are reserved to Core.
- `python F:\Paperclip\tools\qa.py full peninsula`: not run for the same reason. Core should register the class locally and run both required QA levels before integration.
- No preview was reviewed because the QA workflow could not resolve the unregistered ID.
- QA workflow has emitted an unmanaged-install warning in this workspace (`expected str, bytes or os.PathLike object, not NoneType`) on prior invocations.

## Baseline SHA-256 at template workspace `571d63c`

These are existing helpers used by the new template. The selected patch does not replace them.

| File | SHA-256 |
|---|---|
| `atlasforge/templates/_naval.py` | `e07566e2dea689cd1cf54b87b3293dd007d6b365b98fa4426de00cc10f367017` |
| `atlasforge/templates/base.py` | `bc4ff53ead36dfe10410258f0f33a46e26f593b903bfff8eeb18969fa18151dc` |
| `atlasforge/terrain.py` | `d6dc93b0d6c0d39e2b0bea338d7c6563fc477fedd409372b7925e0faa320bf2a` |

## Core integration notes

- Import and register `Peninsula` in `atlasforge/templates/__init__.py` in the Core workspace.
- Assign its final watermark/template ID in Core.
- Run `qa.py quick peninsula` and `qa.py full peninsula` after registration; inspect the resulting preview.
- Roadmap proposal: `Add Peninsula, a naval layout with opposing land tongues, defensible necks, long exposed coasts and lateral landing routes.`
