# Guardian Incident Runbook

## EMERGENCY (>10s)
**Symptom**: /api/status/guardian -> state=EMERGENCY, users get 503/429.

**Check**
1. See `/api/status/simple` P95 per route.
2. Check `data/telemetry/*/guardian.jsonl` last 5 min.

**Action (in order)**
- Stop Deep temporarily:
  `POST /api/guard/degrade { "profile":"heavy" }`
- Lower RAG-K: `POST /api/brain/rag/set { "top_k": 3 }`
- Disable Vision: `POST /api/brain/tools/disable ["vision.detect"]`
- Restart heavy workers (if RAM peak persists).

**Recovery**
- When RAM<75% for 60s: `POST /api/guard/resume-intake`
- Re-enable tools: `POST /api/brain/tools/enable-all`

**Post-mortem**
- Export /data/telemetry and alert team.

## BROWNOUT (>2m)
**Symptom**: /api/status/guardian -> state=BROWNOUT, slow responses.

**Check**
1. Check RAM/CPU usage in Guardian logs.
2. Verify that rate limiting is working.

**Action**
- Activate aggressive caching.
- Lower concurrency for heavy operations.
- Monitor recovery automatically.

## NORMAL -> BROWNOUT (frequent)
**Symptom**: System switches between NORMAL and BROWNOUT.

**Check**
1. Check for memory leaks.
2. Verify resource cleanup.
3. Analyze load patterns.

**Action**
- Optimize memory usage.
- Implement connection pooling.
- Tune Guardian thresholds.
