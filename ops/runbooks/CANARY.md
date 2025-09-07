# Runbook – Canary T7

## Start (5%)

1. Sätt `PREFS_CANARY_SHARE=0.05`
2. `make canary-on`
3. Verifiera sticky-routing i logs

## Övervakning (0–24h)

* Tracka:

  * `verifier.ok` (andel OK)
  * `retry_used` (bör vara låg)
  * `win_rate_diff_vs_T6` (minst +5pp)
  * `p95_latency_delta` (≤ +10%)

## Beslut efter 24h

* **PROMOTE**: `make canary-promote` (till 0.20) → därefter stegvis upp
* **ROLLBACK**: `make canary-rollback` + `make canary-off`

## Post-mortem vid rollback

* Samla `ops/dashboards/telemetry_schema.json` fält
* Notera vilka verifierar-regler som fällde svar
* Skapa förbättrings-PR (filters, verifier, parbalans)