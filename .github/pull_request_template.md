# Pull Request

## 🎯 What

Brief description of changes

## 🔍 Why

Problem / SLO breach / tech debt / feature requirement

## 🧪 Testing

- [ ] `make fmt && make lint && make type` passes locally
- [ ] `./scripts/ci_start_stack.sh` passes locally (≥3 services healthy)
- [ ] `make test-all` passes (if adding/changing functionality)
- [ ] Manual testing completed for user-facing changes

## 🚨 Risk Assessment

- [ ] No functional changes (refactor/cleanup only)
- [ ] Metrics/logging maintained or improved
- [ ] Rollback plan: revert this PR + restart services
- [ ] Database migrations are backwards compatible (if applicable)

## 📊 SLO Impact

- [ ] Tool precision: ≥85% maintained
- [ ] P95 latency: ≤900ms maintained
- [ ] Success rate: ≥98% maintained
- [ ] Watchdog alerts reviewed

## 📝 Documentation

- [ ] README updated (if API/setup changes)
- [ ] Runbooks updated (if operational changes)
- [ ] ADR created (if architectural decisions)

## 🔗 Related Issues

- Closes #
- Related to #

---

**Definition of Done**: All checkboxes above must be ✅ before merge.
