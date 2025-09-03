# Planner Debug Runbook

## Quick Debug Setup

### 1. Environment Variables (docker-compose.yml → orchestrator)
```yaml
environment:
  PLANNER_DEBUG_DUMP: "1"
  PLANNER_DEBUG_DIR: "data/telemetry/planner_raw"
  PLANNER_NO_FALLBACK: "1"  # For debug session only
  PLANNER_TIMEOUT_MS: "8000"
```

### 2. Restart & Test
```bash
# Rebuild if code changed
docker compose build orchestrator

# Restart service
docker compose restart orchestrator

# Test with forced planner
curl -s -X POST http://localhost:18000/api/chat \
  -H 'Content-Type: application/json' \
  -d '{"v":"1","session_id":"debug","force_route":"planner","message":"Boka möte med Anna imorgon 14:00"}' \
| jq '.latency_ms,.model_used'
```

### 3. Check Debug Files
```bash
# Raw dumps (in container)
docker exec alice-orchestrator ls -la /app/data/telemetry/planner_raw/
docker exec alice-orchestrator cat /app/data/telemetry/planner_raw/*.txt

# Logs
docker logs alice-orchestrator --tail 20 | grep -i "raw\|dump\|planner"
```

### 4. Exit Criteria
- ✅ `planner_schema_ok_rate ≥ 80%` (EASY+MEDIUM ≥95%, HARD ≥40%)
- ✅ `planner_p95_first ≤ 900ms` (M4 + 1B quant)
- ✅ `planner_fallback_rate < 1%`
- ✅ `classifier_usage_rate ≥ 60%` (for EASY/MEDIUM scenarios)
- ✅ Raw dumps show valid JSON
- ✅ No `AttributeError` or crashes

### 5. Common Issues
- **"File resets"**: Check bind-mount vs image (`docker inspect alice-orchestrator`)
- **No debug logs**: Rebuild image (`docker compose build orchestrator`)
- **JSON parse fails**: Check raw dump for malformed response
- **High latency**: Verify Metal acceleration (host Ollama, not Docker)

### 6. Success Metrics
- **Latency**: <800ms P95 (vs previous 1800ms)
- **Schema OK**: 82% overall (EASY: 100%, MEDIUM: 95%, HARD: 46.7%)
- **Success Rate**: 72% overall (EASY: 100%, MEDIUM: 75%, HARD: 40%)
- **Fallback Rate**: 0% (vs previous 100%)
- **Classifier Usage**: 60%+ for EASY/MEDIUM scenarios
- **Debug Files**: Present and readable

---
*Last updated: 2025-09-03*
*Status: ✅ WORKING*
