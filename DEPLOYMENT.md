# T7 Deployment & Operations Guide

## Översikt

Den här guiden beskriver hur T7 (Preference Optimization + verifierad 1-shot självkorrektion) rullas ut, övervakas och eventuellt rullas tillbaka. Mål: deterministisk win-rate ≥ 65%, hallucination ≤ 0.5%, p95-latens ±10% mot baseline, 0 policy-brott.

## Förutsättningar

* Artefakter: `services/rl/weights/dpo/v1/adapter.safetensors` + `manifest.json`
* Konfig: `services/rl/prefs/config_prefs.yaml`
* IQ-gates gröna i CI (`.github/workflows/rl-prefs.yml`)

## Snabbkommandon (lokalt)

1. make prefs-build
2. make prefs-train
3. make prefs-eval
4. make verifier-test

## Canary-deploy (5%)

* Sätt env: `PREFS_CANARY_SHARE=0.05`
* Aktivera canary-flagga: `make canary-on`
* Verifiera i logg/telemetri: `verifier.ok`, `retry_used`, `p95_latency`, `human_like_score`

## Promote/rollback

* Promote → 20% om 24h uplift ≥ +5pp win-rate och latensdrift ≤ +10%: `make canary-promote`
* Rollback vid fail (hallucinationer/policy/latens): `make canary-rollback` eller `make canary-off`

## SLO & Watchdog

* Win-rate ≥ 0.65
* Hallucination ≤ 0.005
* Policy-brott = 0
* p95-latens Δ ≤ 0.10
  Se `.github/workflows/canary-watch.yml` (kör periodiskt kontroller).

## Incident

1. `make canary-rollback`
2. Tagga incident i CHANGELOG
3. Skapa GitHub Issue med loggutdrag och `ops/dashboards/telemetry_schema.json`
4. Korrigera verifierar-regler eller databalans, kör `prefs-ci` igen

## Artefakt-manifest

`services/rl/weights/dpo/v1/manifest.json` innehåller hash, r-rank, skapad-tid, par-antal. Logga den vid varje release.