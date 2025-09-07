# T1-T6 Pre-T7 Hardening Checklist

**CRITICAL**: Alla exit-kriterier MÅSTE vara uppfyllda innan T7.

## T1 – Schema & I/O Hardening

### Actions Required
- [ ] Lock lib versions in `services/rl/requirements.txt`
- [ ] Add `schema_version` to all Episode + migration hook
- [ ] Freeze seeds (`SEED=20250907`) in builder/splits
- [ ] Add Pydantic strict mode (`extra: forbid`) + negative tests

### Exit Criteria
- [ ] `make rl-build-ci` produces **identical** hash for train/val/test over 3 runs
- [ ] CI schema-diff = 0 breaking changes

### Validation Commands
```bash
# Test reproducibility
for i in {1..3}; do
  make rl-build-ci
  sha256sum data/rl/v1/train.jsonl >> /tmp/t1_hashes_$i.txt
done
diff /tmp/t1_hashes_*.txt || echo "FAIL: Non-deterministic builds"

# Check schema stability  
git diff HEAD~1 services/rl/pipelines/dataset_schemas.py | grep -E "^\+.*field|^\-.*field" && echo "FAIL: Breaking schema change"
```

## T2 – Build Pipeline Hardening

### Actions Required
- [ ] PII mask unit tests (email/phone/ssn/Unicode)
- [ ] Coverage report → `data/rl/v1/report.json`
- [ ] Drift monitoring (PSI/K-S) vs frozen baseline
- [ ] Backfill with ≥7 days telemetry

### Exit Criteria  
- [ ] Coverage ≥ 90% of active intents/tools
- [ ] PSI < 0.2; yellow warning if exceeded

### Validation Commands
```bash
# Check coverage
jq '.coverage.intent_coverage >= 0.90 and .coverage.tool_coverage >= 0.90' data/rl/v1/report.json || echo "FAIL: Coverage too low"

# Check drift
jq '.drift.psi < 0.2' data/rl/v1/report.json || echo "WARN: High drift detected"
```

## T3 – φ-Reward Hardening  

### Actions Required
- [ ] Per-component missing policies in `reward_config.yaml`
- [ ] Winsorize latency/energy at p99; clamp [0,1]
- [ ] 12 matrix tests (all missing/available combos) + snapshot tests

### Exit Criteria
- [ ] `reward_components.total` ∈ [0,1] for all episodes; 0 NaN
- [ ] Test: 100% pass

### Validation Commands
```bash
# Check reward bounds
python3 -c "
import json
with open('data/rl/v1/train.jsonl') as f:
    rewards = [json.loads(line)['reward_components']['total'] for line in f]
assert all(0 <= r <= 1 for r in rewards), 'Reward out of bounds'
assert not any(r != r for r in rewards), 'NaN rewards found'  # NaN check
print('✅ All rewards in [0,1] bounds')
"

# Run reward tests
python3 -m pytest services/rl/tests/test_reward_shaping.py -v
```

## T4 – Bandits Hardening

### Actions Required
- [ ] Atomic checkpoint writes + file locking
- [ ] Reproducible replay with seeds + report to `bench/replay_report.json`
- [ ] Feature drift monitoring (min/max/var delta alerts)
- [ ] Fail-open policy: static router on bandit server errors

### Exit Criteria
- [ ] Offline uplift ≥ +5pp vs baseline on validation
- [ ] Live p95 for bandit server < 10ms

### Validation Commands
```bash
# Check replay uplift
jq '.metrics.replay_uplift >= 0.05' artefacts/rl_bench/summary.json || echo "FAIL: Insufficient uplift"

# Check bandit server latency
curl -s -w "%{time_total}" http://localhost:8850/health | awk '{if($1*1000 > 10) print "FAIL: Latency " $1*1000 "ms > 10ms"}'
```

## T5 – Live Routing Hardening

### Actions Required  
- [ ] Stable canary hash + `CANARY_SHARE` from env
- [ ] Guardian override: `EMERGENCY→micro`, `BROWNOUT→no deep`
- [ ] Snapshot rotation tested: 15min, 24h retention, recovery OK
- [ ] Telemetry: log every decision + reward to `events_bandit.jsonl`

### Exit Criteria
- [ ] Canary rate = config ±0.5pp
- [ ] 0 decisions lost during rotation/restart

### Validation Commands
```bash
# Test canary rate
python3 test_t5_gates.py | grep "Canary rate" | awk -F: '{if($2 < 4.5 || $2 > 5.5) print "FAIL: Canary rate " $2 "% outside 5.0±0.5%"}'

# Check telemetry logging
test -f data/telemetry/events_bandit.jsonl || echo "FAIL: Bandit telemetry not logging"
```

## T6 – ToolSelector v2 Hardening

### Actions Required
- [ ] Contract tests vs `tool_schema.gbnf`: invalid JSON must FAIL
- [ ] Canary ramp: 5%→20% if SLO green for 24h  
- [ ] Drift monitoring: precision <-3pp → auto-rollback to v1
- [ ] A/B shadow logging: v1 & v2 parallel to `toolselector_ab.jsonl`
- [ ] Svenska rules: date/slang test cases

### Exit Criteria
- [ ] Schema compliance 100% on CI
- [ ] P95 latency < 5ms
- [ ] Accuracy: v2 ≥ v1 on val; shadow win-rate ≥ +5pp

### Validation Commands  
```bash
# Test schema compliance
python3 test_t6_toolselector.py | grep "GBNF schema validation" | grep "✅" || echo "FAIL: Schema validation failed"

# Check latency SLO
python3 test_t6_toolselector.py | grep "P95 latency" | awk '{if($3 > 5.0) print "FAIL: Latency " $3 "ms > 5ms"}'

# Shadow A/B results
test -f data/telemetry/toolselector_ab.jsonl || echo "WARN: Shadow A/B logging not active"
```

## Cross-Cutting Must-Haves

### Security & Stability
```bash
# IQ Gates
make rl-assert || echo "FAIL: IQ gates failed"

# Security scan
trivy fs . --severity HIGH,CRITICAL --exit-code 1 || echo "FAIL: Security vulnerabilities found"

# Git secrets
gitleaks detect --source . --exit-code 1 || echo "FAIL: Secrets detected"
```

### Observability
```bash
# Check dashboard endpoints
curl -s http://localhost:8501/health || echo "WARN: Dashboard unavailable"

# Alert configuration validation
test -f monitoring/alerts.yml && echo "✅ Monitoring configured" || echo "WARN: No monitoring alerts"
```

### Reproducibility  
```bash
# Full CI pipeline
make rl-ci || echo "FAIL: Full CI pipeline failed"

# Artifact validation
test -f data/rl/v1/manifest.json || echo "FAIL: Missing manifest"
jq -r '.hash' data/rl/v1/manifest.json | grep -E '^[a-f0-9]{64}$' || echo "FAIL: Invalid manifest hash"
```

## Go/No-Go Decision Matrix

### Pre-T7 Gates (ALL must be ✅)
- [ ] **T1**: Schema stability + reproducible builds
- [ ] **T2**: Coverage ≥90% + drift PSI <0.2  
- [ ] **T3**: Reward bounds [0,1] + 100% test pass
- [ ] **T4**: Replay uplift ≥5pp + bandit latency <10ms
- [ ] **T5**: Canary rate accurate + 0 decision loss
- [ ] **T6**: Schema compliance 100% + latency <5ms
- [ ] **Security**: 0 CRITICAL CVEs + 0 secrets
- [ ] **CI**: 3 consecutive green builds
- [ ] **Auto-revert**: Tested and functional

### Go/No-Go Command
```bash
#!/bin/bash
# Run full validation
echo "🚦 T1-T6 Go/No-Go Validation"
echo "================================="

FAIL_COUNT=0

# T1-T6 individual checks
for T in {1..6}; do
  echo "Testing T$T..."
  # Insert specific validation commands here
  # Increment FAIL_COUNT on failures
done

# Final decision
if [ $FAIL_COUNT -eq 0 ]; then
  echo "🎉 GO FOR T7: All gates passed"
  exit 0
else
  echo "🛑 NO-GO: $FAIL_COUNT failures detected"  
  echo "Fix issues and re-run validation"
  exit 1
fi
```

## Quick Status Commands

```bash
# Current system status
make rl-ci && echo "✅ Full pipeline" || echo "❌ Pipeline issues"
python3 test_t5_gates.py && echo "✅ T5 live" || echo "❌ T5 issues"  
python3 test_t6_toolselector.py && echo "✅ T6 tools" || echo "❌ T6 issues"

# Performance snapshot
curl -s http://localhost:8850/bandit/stats | jq '.router.total_pulls, .tools.total_intents'
curl -s http://localhost:8001/health | jq '.status'
```

---

**Remember**: This is production-critical infrastructure. Every check must pass before proceeding to T7.

Generated: 2025-09-07 | For: Alice v2 T1-T6 Hardening