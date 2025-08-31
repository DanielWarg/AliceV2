# Guardian incident runbook

## EMERGENCY (>10s)
**Symptom**: /api/status/guardian -> state=EMERGENCY, users får 503/429.

**Check**
1. Se `/api/status/simple` P95 per route.
2. Kolla `data/telemetry/*/guardian.jsonl` senaste 5 min.

**Åtgärd (i ordning)**
- Stoppa Deep tillfälligt:
  `POST /api/guard/degrade { "profile":"heavy" }`
- Sänk RAG-K: `POST /api/brain/rag/set { "top_k": 3 }`
- Stäng Vision: `POST /api/brain/tools/disable ["vision.detect"]`
- Starta om tunga workers (om RAM peak kvarstår).

**Återställning**
- När RAM<75% i 60s: `POST /api/guard/resume-intake`
- Re-enable tools: `POST /api/brain/tools/enable-all`

**Post-mortem**
- Exportera /data/telemetry och larma team.

## BROWNOUT (>2m)
**Symptom**: /api/status/guardian -> state=BROWNOUT, långsamma svar.

**Check**
1. Kolla RAM/CPU usage i Guardian logs.
2. Verifiera att rate limiting fungerar.

**Åtgärd**
- Aktivera aggressive caching.
- Sänk concurrency för tunga operations.
- Monitora recovery automatiskt.

## NORMAL -> BROWNOUT (frequent)
**Symptom**: Systemet växlar mellan NORMAL och BROWNOUT.

**Check**
1. Kolla för memory leaks.
2. Verifiera resource cleanup.
3. Analysera load patterns.

**Åtgärd**
- Optimera memory usage.
- Implementera connection pooling.
- Tune Guardian thresholds.
