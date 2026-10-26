# TPL-crater_basin-1 — Crater Basin

Status: **in_review**. Prepared against the requested Core baseline `1cd178d410ab5125069ab4afed52fa3447e2f17c`.

## Changes

- `atlasforge/templates/crater_basin.py`: converted normalized terrain radius to elmos (`size * 512`) before evaluating the authored rim and basin radii; scaled the outer circuit profile in the same units.
- `tests/test_template_crater_basin.py`: added a direct terrain contract check for a low center, raised rim over the outside flank, and four lower ramp crossings.
- `docs/template_briefs/crater_basin.json`: English design brief for the four-ramp basin and outer rotation circuit.
- `docs/TEMPLATE_BACKLOG.md`: status updated to implementation complete and awaiting Core review.

## Verification

- `python F:\Paperclip\tools\qa.py quick crater_basin`: PASS; focused tests 7 passed; quick workflow 1/1.
- `python F:\Paperclip\tools\qa.py full crater_basin`: PASS; 86/86 cases, 0 advanced failures.
- Full QA log: `F:\Paperclip\qa-logs\20261023-162909-forge-templates-full-crater_basin.log`.
- QA result directory: `out/template_workflow/crater_basin/full`.
- Reviewed `contact_sheet.png`: ten seeds show the crater ring, depressed central basin, and four ramp breaks.

## Baseline and delivery

- Requested Core baseline: `1cd178d410ab5125069ab4afed52fa3447e2f17c`. This template workspace does not contain that Core commit object; the patch is a selected-file patch for review against that named baseline.
- This workspace's `.workspace-baseline.json` has no original hashes for the newly introduced crater template, its tests, brief, or handoff. There is no pre-existing crater file to overwrite. The backlog file is shared with concurrent template assignments; the package patch includes only the crater status row change, not unrelated workspace modifications.
- Contact sheet: `contact_sheet.png` (from the full QA result directory).
- Suggested ROADMAP.md row: `| Crater Basin | Add a contested crater basin with four traversable rim ramps, a continuous outer rotation route, and mirrored economy. |`
- Core integration owner assigns the registry entry and watermark ID.
