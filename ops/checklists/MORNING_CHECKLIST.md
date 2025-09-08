# Alice v2 — Morning Checklist (T8 & T9)

> Syfte: 20–30 min morgonrutin för att besluta **GO/NO-GO** och planera dagens jobb.
> Förutsätter att overnight pipelines (T8 soak, T9 nightly) har kört klart.

## 0) Snabb koll (flaggor & hälsa)

* [ ] Prodflaggor: `T8_ENABLED=false`, `T8_ONLINE_ADAPTATION=false`
* [ ] Nightly OK i CI (inga röda steg)
* [ ] Artefakter finns:

  * T8: telemetry/drift, RCA, dashboard
  * T9: multi-agent rapport (synthetic + real)

## 1) T8 — Hämta nattens resultat

```bash
make morning-report        # visar PSI/KS/VF + topp-RCA + förslag
make dash                  # uppdatera dashboard (ops/dashboards/dashboard.md)
```

Checklist:

* [ ] **verifier_fail p95 ≤ 1.0%** (target)
* [ ] **PSI p95 ≤ 0.20**, **KS p95 ≤ 0.20** (eller tydligt fallande trend)
* [ ] **policy breaches = 0**

## 2) Intent tuning — simulera och förbered patch

```bash
make intent-simulate       # skriver ops/suggestions/intent_tuning.json
make intent-apply-dry      # skriver patch + patched yaml
```

Tolka:

* [ ] `intent_tuning.json`: **psi_sim < psi_now** (helst rejäl sänkning)
* [ ] Diff ser rimlig ut: `ops/suggestions/telemetry_sources.patch`

> Om bra: **applicera** (med din sedvanliga kodreview)

```bash
make config-apply          # om ni har ett säkrat target, annars manuell apply via diff
make t8-telemetry-prod && make t8-drift-prod
```

## 3) T8 — Smoke snapshot efter patch

```bash
make smoke-test
make rca-report
make dash
```

Godkänt om:

* [ ] `verifier_fail` ↓ **≥50% relativ** mot igår
* [ ] `unbalanced_code_fences` + `json_parse_error` inte topp-orsaker

## 4) T8 — Halvdag loop (vid förbättring)

* [ ] Kör `make halfday-loop` varje timme (6–8h)
* [ ] Mål: **VF ≤ 1.0%**, **PSI/KS ≤ 0.20** eller fallande

## 5) T8 — 72h soak → GO-check

```bash
make soak-check && make go-check
```

GO-kriterier:

* [ ] PSI ≤ 0.20 • KS ≤ 0.20 • VF ≤ 1.0%
* [ ] policy=0 • p95 latens Δ ≤ +10% • 0 kritiska incidenter (72h)

**Om 🚀 GO:**

1. Sätt `T8_ENABLED=true`, behåll `T8_ONLINE_ADAPTATION=false` (canary `PREFS_CANARY_SHARE=0.05`)
2. Efter 24–72h fortsatt grönt → `T8_ONLINE_ADAPTATION=true` (bandit + safety gate)

## 6) T9 — Multi-Agent rapport

* Hämta artefakter i CI:

  * `t9-multi-agent-report` (synthetic)
  * `t9-multi-agent-report-real` (real/fallback)
* Notera **win-rate** per agent:

  * [ ] `borda+bt` win-rate: ___
  * [ ] `borda-only` win-rate: ___
* Välj **candidate agent** för staging när T8 är grönt.

## 7) Staging-plan (när T8 är stabilt)

* [ ] Koppla T9 vinnande agent till bandit-router @ 5% i staging
* [ ] Mät verifier_ok, human-like, latens • rollback via flaggor
* [ ] Dokumentera resultat i CHANGELOG

---

## Quick commands (copy-paste)

```bash
# T8 morgon
make morning-report && make dash
make intent-simulate && make intent-apply-dry
make t8-telemetry-prod && make t8-drift-prod
make smoke-test && make rca-report && make dash

# T9 morgon
make t9-test && make t9-eval-real
cat data/rl/prefs/t9/multi_agent_report.json
```

## Troubleshooting (snabb)

* **PSI fastnar högt:** slå ihop sällsynta intents → `other`; lägg nya regex från suggestions; kör om simulate.
* **VF sjunker inte:** kontrollera schema-regler vs svarsmall; öka `MAX_CHARS`/justera FormatGuard; RCA topp-orsaker.
* **KS hög:** cap:a överlånga svar i de värsta flödena; verifierens max_len ska matcha verklig mall.

---

### Anteckningar / dagens beslut

* T8 status: ___________________________
* T9 status: ___________________________
* Dagens fokus: _______________________

---