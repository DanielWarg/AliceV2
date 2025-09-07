# Versionering av modeller & adapters

* Modellversion (semver): MAJOR.MINOR.PATCH
* Adaptertagg: adapter-YYYYMMDD-HHMMSS-<short_hash>
* Vid varje release:

  1. Uppdatera manifest.json (commit, datahash, LoRA-parametrar)
  2. Bumpa PATCH om endast preferenser/adapter; MINOR vid större kvalitetshopp; MAJOR vid brytande API
  3. Skriv CHANGELOG (kort, mätbart: win_rate, hallucinationer, p95)