# Utvärdering & Kvalitetssäkring (Alice v2)

Syfte: Kontinuerligt bevisa kvalitet i produktion via mänsklig A/B, nattliga adversarial-tester och tydlig rapportering.

## 1) Mänsklig A/B (svenska)

* Datakälla: eval/human/prompts_swe_testset.jsonl
* Generering: tools/ab_runner.py (producerar eval/human/ab_candidates.jsonl)
* Panelbedömning: eval/human/aggregate.py (skapar eval/human/human_report.json)

## 2) Nattliga adversarial-tester

* CI: .github/workflows/nightly-adversarial.yml
* Mål: fånga drift, promptinjektion, påhittade claims, schemafel.

## 3) Rapportering

* IQ-gates (CI): min win_rate ≥ 0.65, hallucination ≤ 0.005, policy = 0.
* Human A/B: v2 win-rate vs v1 ≥ +5pp över 7-dagars glidande fönster.

## 4) Versionsstyrning

* Följ VERSIONING.md och uppdatera CHANGELOG.md vid varje adapter-release.
* Manifest (services/rl/weights/dpo/v1/manifest.json) ska innehålla datahash och commit.