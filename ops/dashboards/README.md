# T8 Dashboards

Detta kit renderar en Markdown-dashboard med Mermaid-grafer från `data/ops/drift_history.jsonl` och RCA-artefakter.

## Användning
- `make dash` – rendera dashboard → `ops/dashboards/dashboard.md`
- `make dash-fake` – skapa fejkhistorik och rendera (för lokalt test)
- I CI (nightly) laddas dashboard upp som artefakt

## Källor
- Drift history: `data/ops/drift_history.jsonl` (skapad av drift_watch)
- RCA: `data/ops/rca/reasons_hist.json` (skapad av rca_sample_failures)