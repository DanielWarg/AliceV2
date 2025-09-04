# Tech Debt Burndown 🔥

> **Goal**: Systematically eliminate technical debt to maintain high velocity and quality.

## 🚨 High Priority (Do First)

- [ ] **Duplicated HTTP client patterns** - Standardize httpx usage with retry/timeout in `packages/http-client/`
- [ ] **Inconsistent environment variable loading** - Migrate all services to pydantic BaseSettings pattern
- [ ] **Copy-pasted utils functions** - Consolidate into `packages/common/` shared library
- [ ] **Missing type hints** - Add types to all public APIs in orchestrator and guardian
- [ ] **Legacy cache v0 remnants** - Remove old cache code, keep only smart_cache
- [ ] **Hardcoded timeouts/retries** - Move to config files with sensible defaults

## 🧹 Medium Priority (Next Sprint)

- [ ] **Docker health check inconsistencies** - Standardize all services to use same pattern
- [ ] **Log format differences** - Unified JSON logging with trace_id across all services
- [ ] **Dead imports and unused code** - Run `vulture` and clean up
- [ ] **Makefile target duplication** - DRY principle for common patterns
- [ ] **Test fixture duplication** - Shared test utilities in `tests/fixtures/`
- [ ] **Environment-specific code** - Abstract away dev/prod differences

## 🎯 Low Priority (Technical Improvements)

- [ ] **Python packaging modernization** - Move to pyproject.toml completely
- [ ] **Docker multi-stage optimization** - Reduce image sizes by 50%
- [ ] **Dependency version pinning** - Lock all transitive dependencies
- [ ] **API versioning strategy** - Implement v1/v2 endpoints where needed
- [ ] **Metrics naming consistency** - Follow Prometheus naming conventions
- [ ] **Documentation generation** - Auto-generate API docs from code

## ✅ Completed

- [x] **Port conflicts fixed** - Redis 6379→16379 for eval harness
- [x] **Makefile duplication removed** - Consolidated development commands
- [x] **Formatter standardization** - black + ruff configured project-wide
- [x] **CI stabilization** - docker compose v2 syntax + health check fixes
- [x] **Branch cleanup** - Removed stale feature branches
- [x] **Security scanning** - gitleaks configuration and CI integration

## 📊 Debt Metrics

| Category        | Items | Est. Hours | Impact                 |
| --------------- | ----- | ---------- | ---------------------- |
| High Priority   | 6     | 16h        | 🔴 Blocks development  |
| Medium Priority | 6     | 12h        | 🟡 Slows development   |
| Low Priority    | 6     | 20h        | 🟢 Quality improvement |

**Next Review**: Weekly during team standup

## 🎯 Success Criteria

- **Code Quality**: All new code follows established patterns
- **Development Velocity**: No blockers due to technical debt
- **Maintainability**: New team members can contribute within 2 days
- **Reliability**: SLO breaches due to tech debt → zero

---

💡 **Tip**: Use `git grep -n "TODO\|FIXME\|XXX"` to find inline debt markers.
