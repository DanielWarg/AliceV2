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
	@echo "T7 Targets: prefs-build | prefs-train | prefs-eval | prefs-ci | verifier-test"
	@echo "Canary: canary-on | canary-off | canary-promote | canary-rollback"
	@echo "T8 Drift: t8-drift-run | t8-drift-history | t8-telemetry-prod | t8-drift-prod"
	@echo ""
	@echo "🚀 T8 TESTING PHASES (strukturerad approach):"
	@echo "  pre-flight      # 10min: Freeze baseline metrics for comparison"
	@echo "  smoke-test      # 30min: FormatGuard on + RCA + drift check"
	@echo "  halfday-loop    # Hourly: RCA + telemetry + drift (target: VF ≤ 1.0%)"  
	@echo "  soak-check      # 72h: Rolling metrics validation"
	@echo "  go-check        # GO/NO-GO decision based on criteria"
	@echo ""
	@echo "T8 Analysis: rca-sample | rca-report | t8-formatguard-on | t8-formatguard-off"
	@echo "🌙 Overnight: overnight-8h | morning-report (PII-safe optimization suggestions)"

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

# --- T8 trends & rollup ---
t8-drift-history:
	python ops/scripts/drift_history_rollup.py

t8-drift-run:
	python services/rl/drift/drift_watch.py || true

# --- T8 stabilization targets ---

# RCA failure sampling from prod logs
rca-sample:
	python ops/scripts/rca_sample_failures.py --log_path data/logs/prod_requests.jsonl --output data/ops/rca_failures.json --sample_size 100

rca-report:
	@echo "[RCA-REPORT] Top failure patterns from last analysis:"
	@python -c "import json; data=json.load(open('data/ops/rca_failures.json')); patterns=data.get('patterns',{}); print(f'Verifier errors: {dict(list(patterns.get(\"verifier_errors\",{}).items())[:3])}'); print(f'Route distribution: {patterns.get(\"routes\",{})}'); print(f'Avg latency: {patterns.get(\"avg_latency\",0)}ms'); [print(f'- {rec}') for rec in data.get('recommendations',[])[:3]]"

t8-rca-sample-daily:
	python ops/scripts/rca_sample_failures.py --log_path data/logs/prod_requests.jsonl --output data/ops/rca_failures_daily.json --lookback_hours 24 --sample_size 100

# FormatGuard testing and validation
t8-formatguard-test:
	pytest -q tests/test_format_guard.py

# RCA testing
t8-rca-test:
	pytest -q tests/test_rca_sampling.py

# Complete stabilization test suite
t8-stabilization-test:
	pytest -q tests/test_format_guard.py tests/test_rca_sampling.py tests/test_t8_integration.py

# Testing phases (strukturerad approach)

# PRE-FLIGHT: Frys baseline för jämförelse (10 min)
pre-flight:
	@echo "[PRE-FLIGHT] Freezing baseline metrics for comparison..."
	make t8-telemetry-prod
	make t8-drift-run
	@echo "[PRE-FLIGHT] Baseline frozen. Ready for smoke test."

# PHASE 1: 30-min smoke test
smoke-test: t8-formatguard-on rca-sample rca-report t8-drift-prod
	@echo "[SMOKE-TEST] 30min smoke complete. Check verifier_fail reduction vs baseline."
	@echo "🎯 Target: verifier_fail ↓ ≥50%, format errors ↓ ≥60%, KS trending down"

# PHASE 2: Halvdag loop (kör var timme)
halfday-loop: rca-sample rca-report t8-telemetry-prod t8-drift-prod
	@echo "[HALFDAY-LOOP] Hourly check complete. Target: verifier_fail ≤ 1.0%"

# PHASE 3: 72h soak validation
soak-check: t8-drift-run t8-drift-history
	@echo "[SOAK-CHECK] 7-day rolling metrics for GO/NO-GO decision"

# Combined stabilization pipeline (legacy)
t8-stabilization-run: rca-sample t8-formatguard-test t8-stabilization-test
	@echo "[T8-STABILIZATION] Complete pipeline run finished"

# Debug and troubleshooting
t8-debug-formatguard:
	python -c "from orchestrator.src.response.format_guard import preprocess_response; result=preprocess_response('Test aa text with ae problems'); print(f'Changed: {result[\"changed\"]}'); print(f'Fixes: {result[\"fixes_applied\"]}'); print(f'Text: {result[\"text\"]}')"

t8-debug-rca:
	python ops/scripts/rca_sample_failures.py --log_path data/logs/prod_requests.jsonl --sample_size 5 --lookback_hours 1

# Feature flag helpers för T8 stabilization
t8-formatguard-on:
	@echo "FORMATGUARD_ENABLED=true" >> .env.local && echo "[T8] FormatGuard enabled"

t8-formatguard-off:
	@echo "FORMATGUARD_ENABLED=false" >> .env.local && echo "[T8] FormatGuard disabled"

# GO decision helper
go-check:
	@echo "[GO-CHECK] Validating GO/NO-GO criteria..."
	@python -c "import json; data=json.load(open('data/ops/drift_rollup.json')); latest=list(data['days'].values())[-1] if data.get('days') else {}; psi_ok = latest.get('psi_intents',{}).get('p95',999) <= 0.20; ks_ok = latest.get('ks_length',{}).get('p95',999) <= 0.20; vf_ok = latest.get('verifier_fail',{}).get('p95',999) <= 0.01; print(f'PSI ≤ 0.20: {\"✅\" if psi_ok else \"❌\"} ({latest.get(\"psi_intents\",{}).get(\"p95\",\"?\")})'); print(f'KS ≤ 0.20: {\"✅\" if ks_ok else \"❌\"} ({latest.get(\"ks_length\",{}).get(\"p95\",\"?\")})'); print(f'VF ≤ 1.0%: {\"✅\" if vf_ok else \"❌\"} ({latest.get(\"verifier_fail\",{}).get(\"p95\",\"?\")})'); print(f'GO DECISION: {\"🚀 GO\" if all([psi_ok,ks_ok,vf_ok]) else \"🚨 NO-GO\"}')"

# --- Overnight Auto-Stabilizer (8h) ---
overnight-8h:
	python ops/scripts/overnight_optimizer.py

morning-report:
	@echo "---- Morning Report ----"
	@python3 -c "import json, pathlib; md = pathlib.Path('ops/suggestions/morning_report.md'); js = pathlib.Path('ops/suggestions/morning_report.json'); print('Ingen morning_report ännu. Kör: make overnight-8h') if not md.exists() else print(md.read_text(encoding='utf-8') + '\\n(JSON sammanfattning:)\\n' + (js.read_text(encoding='utf-8') if js.exists() else '(saknas)'))"

# --- Intent tuning ---
intent-analyze:
	python3 ops/scripts/intent_tuner.py

intent-simulate:
	python3 ops/scripts/intent_tuner.py --simulate

intent-quick:
	python3 ops/scripts/overnight_optimizer.py || true
	python3 ops/scripts/intent_tuner.py --simulate || true
	@echo "Se ops/suggestions/intent_tuning.json + intent_regex_suggestions.yaml"

# --- Safe config management ---
config-dry-run:
	python3 ops/scripts/apply_suggestions.py --dry-run

config-summary:
	python3 ops/scripts/apply_suggestions.py --summary

config-apply:
	@echo "🚨 WARNING: This will modify production config!"
	@read -p "Type 'YES' to continue: " confirm && [ "$$confirm" = "YES" ] || { echo "Aborted."; exit 1; }
	python3 ops/scripts/apply_suggestions.py --apply

# --- Dashboards ---
dash:
	python3 ops/dashboards/render_dashboard.py

dash-fake:
	python3 ops/dashboards/make_fake_history.py
	python3 ops/dashboards/render_dashboard.py
	@echo "Öppna ops/dashboards/dashboard.md"

# --- T9 multi-agent (offline) ---
t9-eval:
	python services/rl/prefs/eval_multi_agent.py

t9-test:
	pytest -q tests/test_agents.py

t9-nightly-local: t9-test t9-eval
	@echo "Report -> data/rl/prefs/t9/multi_agent_report.json"

# --- T9 real data ---
t9-extract:
	python services/rl/prefs/realdata_adapter.py --cfg ops/config/t9_realdata.yaml

t9-eval-real:
	python services/rl/prefs/eval_multi_agent.py --realdata --cfg ops/config/t9_agents.yaml --real_cfg ops/config/t9_realdata.yaml
	@echo "Report -> data/rl/prefs/t9/multi_agent_report.json"

# --- Morning routine ---
morning:
	@echo "=== Alice v2 Morning Checklist ==="
	@echo "📋 Full checklist: ops/checklists/MORNING_CHECKLIST.md"
	@echo ""
	@echo "🌅 Quick Status:"
	@echo "  - T8 overnight data: $(shell ls -la data/logs/prod_*.ndjson 2>/dev/null | wc -l) files"
	@echo "  - T9 reports available: $(shell ls -la data/rl/prefs/t9/*.json 2>/dev/null | wc -l) files"
	@echo ""
	@echo "📊 Key Commands:"
	@echo "  make morning-report     # T8 overnight results"
	@echo "  make intent-simulate    # T8 PSI optimization"
	@echo "  make t9-eval-real       # T9 agent performance"
	@echo "  make dash               # Update dashboard"