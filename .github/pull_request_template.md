## What/Why
<!-- Describe what this PR does and why it's needed -->

- [ ] ADR/PRD/workflow updated (links below)
- [ ] Affects: ☐ Orchestrator ☐ Guardian ☐ Memory ☐ Voice ☐ Tools ☐ HUD ☐ n8n

**Architecture Links:**
- ADR: [link to ADR.mdc update]
- PRD: [link to PRD.mdc update] 
- Workflow: [link to workflow.mdc update]

## Tests & Gates
<!-- All must be green for merge -->

- [ ] Unit/Integration/E2E green
- [ ] `./scripts/auto_verify.sh` green (attach `data/tests/summary.json`)
- [ ] SLO met: fast P95 ≤250ms, planner_openai P95 ≤900ms, tail >1.5s <1%
- [ ] Schema_ok ≥99% (planner_openai, 2×50 req)
- [ ] Arg-build success ≥95% (attach metrics)
- [ ] Cost today within budget; OpenAI cost delta shown in HUD

## Security/Privacy
<!-- Security requirements -->

- [ ] No secrets in code; .env via secrets
- [ ] cloud_ok flow respected (opt-in required)
- [ ] n8n webhook HMAC verified (±300s, replay-guard)

## Rollback
<!-- How to disable this feature if needed -->

- [ ] Feature-flag/ENV to disable feature (e.g., `PLANNER_PROVIDER=local`)

## Checklist
<!-- Final verification -->

- [ ] Code follows style guidelines
- [ ] Self-review completed
- [ ] Documentation updated
- [ ] Tests added/updated
- [ ] Performance impact assessed
- [ ] Security implications reviewed
