# Makefile – T7 + Drift

# --- T7 pipeline

prefs-build:
	python services/rl/prefs/prepare_pairs.py --in data/rl/v1/train.jsonl --out data/rl/prefs/v1/pairs.jsonl
	python services/rl/prefs/filters.py --in data/rl/prefs/v1/pairs.jsonl --out data/rl/prefs/v1/pairs_clean.jsonl

prefs-train:
	python services/rl/prefs/train_dpo.py --data data/rl/prefs/v1/pairs_clean.jsonl --out services/rl/weights/dpo/v1/

prefs-eval:
	python services/rl/prefs/eval_prefs.py --pairs data/rl/prefs/v1/pairs_clean.jsonl --model services/rl/weights/dpo/v1/ --out data/rl/prefs/v1/report.json

prefs-ci: prefs-build prefs-train prefs-eval

verifier-test:
	pytest -q tests/test_verifier.py tests/test_self_correction.py

# --- Canary ops

canary-on:
	@echo "PREFS_CANARY_SHARE=0.05" > .env.canary && echo "[canary-on] share=0.05"

canary-off:
	@echo "PREFS_CANARY_SHARE=0.00" > .env.canary && echo "[canary-off] share=0.00"

canary-promote:
	python ops/scripts/canary_promote.py

canary-rollback:
	python ops/scripts/canary_rollback.py

# Hjälp

help:
	@echo "Targets: prefs-build | prefs-train | prefs-eval | prefs-ci | verifier-test | canary-on | canary-off | canary-promote | canary-rollback"

# ––– Human eval helpers –––

human-ab:
	python tools/ab_runner.py

human-aggregate:
	python eval/human/aggregate.py

# ––– Utilities –––

eval-help:
	@echo "Kör: make human-ab && fyll i eval/human/judgments.jsonl, sedan make human-aggregate"

# --- T8 ops ---
t8-drift:
	python services/rl/drift/drift_watch.py || true

t8-help:
	@echo "T8: t8-drift (PSI/KS), nightly via .github/workflows/t8-nightly.yml"

# --- T8 prod telemetry ---
t8-telemetry-prod:
	python ops/scripts/ingest_prod_telemetry.py

t8-drift-prod: t8-telemetry-prod
	python services/rl/drift/drift_watch.py || true