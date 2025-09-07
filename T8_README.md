# T8 – Multi-agent Preferences & Drift-Ops

## Mål
- Multi-agent preferenser (A/B/C) + domaraggregator
- Driftdetektion (PSI/KS) och grindar i CI
- Säker online-adaptation (bandit-router) bakom feature-flagga

## Feature-flaggor
- T8_ENABLED=false
- T8_ONLINE_ADAPTATION=false

## Grindar
- PSI_intents ≤ 0.20 (7-dagars)
- verifier_fail ≤ 1.0%
- policy_breaches = 0
- p95_latency_Δ ≤ +10%

## Quickstart – real data (prod)
1) Lägg/peka dina prod-loggar (NDJSON/JSONL) i `ops/config/telemetry_sources.yaml` under `sources:`
2) Kör `make t8-telemetry-prod` → bygger `data/ops/telemetry_window.json` från verkliga händelser (PII-säkert)
3) Kör `make t8-drift-prod` → PSI/KS/verifier_fail beräknas via drift_watch
4) Håll grindarna gröna i 3–7 dagar → överväg T8_ONLINE_ADAPTATION=true bakom `safety_gate`