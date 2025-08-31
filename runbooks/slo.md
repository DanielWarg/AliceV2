# SLO breach runbook

## Deep P95 > 3000ms
**Symptom**: Deep route svarar långsamt, P95 över 3000ms.

**Check**
1. Kolla `/api/status/routes` för deep route metrics.
2. Verifiera Guardian state.
3. Analysera request patterns.

**Åtgärd**
- Öka prompt-speculativ decoding (om vLLM i fas 2).
- Tvinga planner-route för stora prompts tills last sjunker.
- Minska max concurrency för Deep till 1.
- Aktivera request queuing.

**Återställning**
- När P95 < 2000ms: Återställ concurrency.
- Monitora trend i 10 minuter.

## Fast P95 > 250ms
**Symptom**: Micro route svarar långsamt, P95 över 250ms.

**Check**
1. Kolla `/api/status/routes` för micro route metrics.
2. Verifiera system load.
3. Analysera request volume.

**Åtgärd**
- Aktivera cache för NLU/översättningar.
- Pre-warm Micro-LLM.
- Optimera prompt processing.
- Sänk batch size.

**Återställning**
- När P95 < 150ms: Återställ optimizations.
- Monitora trend i 5 minuter.

## Planner P95 > 1500ms
**Symptom**: Planner route svarar långsamt, P95 över 1500ms.

**Check**
1. Kolla `/api/status/routes` för planner route metrics.
2. Verifiera tool availability.
3. Analysera planning complexity.

**Åtgärd**
- Optimera tool selection logic.
- Implementera planning cache.
- Sänk planning depth.
- Aktivera fallback till micro.

**Återställning**
- När P95 < 1000ms: Återställ planning depth.
- Monitora trend i 5 minuter.

## Error Rate > 2%
**Symptom**: 5xx errors över 2% i 3 minuter.

**Check**
1. Kolla `/api/status/simple` för error budget.
2. Analysera error patterns.
3. Verifiera dependencies.

**Åtgärd**
- Aktivera circuit breakers.
- Implementera graceful degradation.
- Sänk request volume.
- Checka external dependencies.

**Återställning**
- När error rate < 0.5%: Återställ full functionality.
- Monitora trend i 10 minuter.
