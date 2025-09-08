# T9 – Multi-Agent Preference Optimization (offline)

## Syfte
Köra flera preferensstrategier parallellt mot syntetiska triples och välja vinnare via objektiv win-rate – utan att påverka produktion.

## Kör lokalt
- `make t9-test` – enhetstester
- `make t9-eval` – genererar `data/rl/prefs/t9/multi_agent_report.json`

## Nightly
- `.github/workflows/t9-nightly.yml` kör eval i CI och laddar upp rapport.

## Real Data Adapter (PII-säker)
- Konfig: `ops/config/t9_realdata.yaml`
- Extract:
  - `make t9-extract`  → bygger `data/rl/prefs/t9/triples_real.jsonl`
- Eval på real-data (fallback till syntetiskt om för få triples):
  - `make t9-eval-real`

## Nästa steg (efter T9 skelett)
- Byt ut syntetiska triples mot riktiga A/B/C-kandidater från loggar (maskade).
- Koppla bästa agenten till bandit-router i staging (T8_ONLINE_ADAPTATION=true i liten share).