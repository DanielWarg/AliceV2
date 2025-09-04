# SLO Breach Runbook

## Deep P95 > 3000ms

**Symptom**: Deep route responds slowly, P95 over 3000ms.

**Check**

1. Check `/api/status/routes` for deep route metrics.
2. Verify Guardian state.
3. Analyze request patterns.

**Action**

- Increase prompt-speculative decoding (if vLLM in phase 2).
- Force planner-route for large prompts until load decreases.
- Reduce max concurrency for Deep to 1.
- Activate request queuing.

**Recovery**

- When P95 < 2000ms: Restore concurrency.
- Monitor trend for 10 minutes.

## Fast P95 > 250ms

**Symptom**: Micro route responds slowly, P95 over 250ms.

**Check**

1. Check `/api/status/routes` for micro route metrics.
2. Verify system load.
3. Analyze request volume.

**Action**

- Activate cache for NLU/translations.
- Pre-warm Micro-LLM.
- Optimize prompt processing.
- Lower batch size.

**Recovery**

- When P95 < 150ms: Restore optimizations.
- Monitor trend for 5 minutes.

## Planner P95 > 1500ms

**Symptom**: Planner route responds slowly, P95 over 1500ms.

**Check**

1. Check `/api/status/routes` for planner route metrics.
2. Verify tool availability.
3. Analyze planning complexity.

**Action**

- Optimize tool selection logic.
- Implement planning cache.
- Lower planning depth.
- Activate fallback to micro.

**Recovery**

- When P95 < 1000ms: Restore planning depth.
- Monitor trend for 5 minutes.

## Error Rate > 2%

**Symptom**: 5xx errors over 2% for 3 minutes.

**Check**

1. Check `/api/status/simple` for error budget.
2. Analyze error patterns.
3. Verify dependencies.

**Action**

- Activate circuit breakers.
- Implement graceful degradation.
- Lower request volume.
- Check external dependencies.

**Recovery**

- When error rate < 0.5%: Restore full functionality.
- Monitor trend for 10 minutes.
