# SCU-38 — TPL-fortress_front-1

## Delivery

Fortress Front has two mirrored forward positions, three open sorties per position, and expansion resources beyond the home shoulders. The delivered patch contains the template, its focused tests, the design brief, and the local backlog ownership update. Core owns final registration, watermark ID, and release checks.

The prototype came from Template's `forge-templates` workspace. Sol fixed the empty flank masks by keeping the direction angle signed, and aligned the terrain shoulders with `Symmetry.starts()` (0.11 for east/west and north/south; 0.14 for diagonal starts). The focused test now checks all three layouts across seeds 1–3.

## Baselines and files

- Template baseline: `571d63c5dc21659afb6ccc4074e1d6d900722aa0` (`sol/base`).
- Core `atlas-map-forge` main at delivery: `c15cd4d1e3177664f0faae67856ea6ff1283b846`. Core integration must compare against its current main before applying.
- New files, absent from the template baseline: `atlasforge/templates/fortress_front.py`, `tests/test_template_fortress_front.py`, `docs/template_briefs/fortress_front.json`, this handoff.
- Updated local ownership row: `docs/TEMPLATE_BACKLOG.md`. Baseline SHA-256: `5ef748aa6f1c9336ea19b01c0ae0f4b3b43493e92ab5efd90351dbd344dbd08e`.
- No registry, watermark, terrain engine, UI, or release file was changed.

## Verification

- `python F:\Paperclip\tools\qa.py quick fortress_front`: PASS; 5 focused tests and 1/1 generator cases, before expanding the layout parameterization. Logs: `F:\Paperclip\qa-logs\20261023-200211-.scu38-tests-fortress_front.log` and `20261023-200215-.scu38-quick-fortress_front.log`.
- `python F:\Paperclip\tools\qa.py full fortress_front` on final code: PASS; 11 focused tests, 78/78 seed and parameter cases, 0 advanced cases unplayable. Logs: `F:\Paperclip\qa-logs\20261023-200439-.scu38-tests-fortress_front.log` and `20261023-200446-.scu38-full-fortress_front.log`.
- Result folder: `out/template_workflow/fortress_front/full`, containing `report.json`, `contact_sheet.png`, `fortress_front_preview.png`, and `fortress_front.jpg`.
- Visually inspected the complete 10-seed contact sheet and enlarged default preview. Two opposing positions and open shoulders are visible. The map was not loaded or played in Zero-K.

## Core integration

Register `fortress_front`, assign its final watermark ID, and run Core's merge/release gates. The local patch is selected files only; reconcile the backlog row with Core's current document instead of replacing that document wholesale.

Suggested ROADMAP.md row (English):

| `fortress_front` | Fortress Front | Mirrored forward positions with three sorties per side and exposed outer expansions | Template QA passed; awaiting Core integration and in-game review |
