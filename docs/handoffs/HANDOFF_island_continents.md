# TPL-island_continents-1 — SCU-65

## Lieferung

Zwei gespiegelte, große Kontinente mit getrennten Landfronten und einem durchgehenden tiefen Seekanal. Die Häfen liegen mit Abstand im Kanal; Amphibien können von beiden Basen dorthin fahren. Spielertexte sind Englisch.

Ausgewählte Dateien im Patch:

- `atlasforge/templates/island_continents.py` — neu
- `tests/test_template_island_continents.py` — neu
- `docs/template_briefs/island_continents.json` — neu
- `docs/TEMPLATE_BACKLOG.md` — nur Vergabezeile

Patch-Basis: lokaler `forge-templates`-Hauptbranch `e6745b5770983539f61da1f1d1b0344cc4823eb3`. Der Auftrag nennt Core `55f129e`; dieser Commit ist in diesem Template-Repository nicht vorhanden. Core-Owner muss die vier Dateien gegen seinen aktuellen Stand einzeln prüfen. Die Naval-Hilfe hat hier die Signatur `islands(h, xx, zz, edge, v, shapes)`.

Baseline-SHA-256: `docs/TEMPLATE_BACKLOG.md` = `2EF109976E7B2C9AE220C1B515E80ED38178299DF39EDC0F9C74FBCF5E27307A`. Die drei übrigen Dateien fehlen in der Basis.

## Prüfung

- `python F:\Paperclip\tools\qa.py quick island_continents`: PASS, 4 Tests und Seed 1 (vor den letzten Grenzfalltests).
- `python F:\Paperclip\tools\qa.py test tests/test_template_island_continents.py`: PASS, 6 Tests.
- `python F:\Paperclip\tools\qa.py full island_continents`: PASS, 6 Tests, 74/74 Konfigurationen. Sechs Advanced-Konfigurationen sind erzeugbar, aber nicht spielbar: Größe 8/10, Strandneigung 5/40 und beide kombinierten Extremwerte.
- Full-Log: `F:\Paperclip\qa-logs\20261026-210540-forge-templates-sol-full-island_continents.log`.
- Ergebnisordner: `out/template_workflow/island_continents/full`.
- `contact_sheet.png` für Seeds 1–10 angesehen: zwei getrennte Landmassen, spiegelgleiche Ressourcen, offener Kanal und zwei Hafenmarkierungen.

Die QA-Matrix ist technische Validierung. Ein echter Zero-K-Spieltest ist offen.

## Core-Integration

Registry, Galerie und Watermark-ID vergibt der Core-Owner. Er soll den Patch gegen seinen aktuellen Core-Stand prüfen und die neue Template-ID dort registrieren. Keine gemeinsamen Naval-Hilfen wurden für diese Lieferung verändert.

Vorgeschlagene ROADMAP.md-Zeile (Englisch): `Island Continents — Add broad opposing landmasses with independent ground fronts, a deep fleet channel, and amphibious landing routes.`
