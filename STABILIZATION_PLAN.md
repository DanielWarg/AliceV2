# Alice v2 Stabilization Plan 🔧

## 🎯 Mission: Gör CI grönt INNAN RL deployment

**Princip**: Stabilisera in-place, migrera bara om absolut nödvändigt.

## 📋 Stabilization Checklist

### ✅ Phase 1: Immediate Actions (nu)

```bash
# 1. Skapa stabiliseringsbranch
git checkout -b stabilize/main
git push -u origin stabilize/main

# 2. Lokala health checks
make down && make up
curl -sf http://localhost:18000/health
docker compose ps

# 3. Code quality
black --line-length 100 services/
flake8 services/ --max-line-length=100

# 4. Security scan
docker run --rm -v "$PWD":/src aquasec/trivy fs /src --severity HIGH,CRITICAL
```

### 🔨 Phase 2: CI Pipeline Fix

- [x] **Ren CI pipeline** (`.github/workflows/ci-clean.yml`)
  - Seriell ordning: build → stack → quality → security → tests → eval
  - Hård health-väntan (5 min timeout)
  - Låsta versioner (Node 20, Python 3.11, pnpm 8)
  - SLO gates: Tool precision ≥85%, P95 ≤900ms

- [ ] **Disable gamla workflows**
  ```bash
  # Flytta gamla workflows till backup
  mkdir -p .github/workflows/backup
  mv .github/workflows/*.yml .github/workflows/backup/
  mv .github/workflows/ci-clean.yml .github/workflows/ci.yml
  ```

- [ ] **Port standardisering**
  - Orchestrator: `18000` (ej 8002)
  - Guardian: `8787`
  - NLU: `9002`
  - Redis: `6379`

### 🛡️ Phase 3: Branch Protection

När CI är grönt:

```bash
# Via GitHub CLI
gh api repos/:owner/:repo/branches/main/protection \
  --method PUT \
  --field required_status_checks='{"strict":true,"contexts":["🔒 Security Scan","📊 Eval Harness (SLO Gate)","🧹 Code Quality"]}' \
  --field enforce_admins=true \
  --field required_pull_request_reviews='{"required_approving_review_count":1}' \
  --field restrictions=null
```

### 🏷️ Phase 4: Baseline Tagging

```bash
# När allt är grönt
git checkout main
git merge --no-ff stabilize/main
git tag v2.0.0-baseline
git push --tags
```

## 🚨 Common Root Causes & Fixes

### 1. **Health Check Failures**
```yaml
# Problem: Services inte uppe när tests börjar
# Fix: Hård wait-loop i CI
wait_for_health() {
  for i in {1..60}; do
    curl -sf http://localhost:18000/health && break || sleep 5
  done
}
```

### 2. **Port Drift**
```bash
# Problem: Lokalt :18000, CI :8002  
# Fix: Standardisera via env vars
ORCHESTRATOR_PORT: 18000
```

### 3. **Package Lock Drift**
```bash
# Problem: CI installerar andra dependencies än lokalt
# Fix: Frozen lockfile
pnpm install --frozen-lockfile
```

### 4. **Trivy CVE Noise**
```bash
# Problem: Debian base images får nya CVE:er
# Fix: Slim images + pull latest
FROM python:3.11-slim-bookworm
```

### 5. **Flaky Tests**
```python
# Problem: Externa nätverksanrop i tests
# Fix: Mock dependencies
@patch('httpx.AsyncClient')
def test_with_mock(mock_client):
    # Deterministiskt test
```

## 🔍 Debug Commands

### Lokala health checks
```bash
# Verifiera stack
docker compose ps
docker compose logs orchestrator --tail=50

# Test endpoints
curl -v http://localhost:18000/health
curl -v http://localhost:8787/health  
curl -v http://localhost:9002/healthz

# Eval test
docker compose run --rm eval
```

### CI troubleshooting
```bash
# Lokalt reproducera CI steps
docker compose build --pull
docker compose up -d guardian orchestrator alice-cache nlu

# Vänta på health som CI gör
for service in orchestrator:18000/health guardian:8787/health nlu:9002/healthz; do
  curl -sf "http://localhost:$(echo $service | cut -d: -f2-)" || echo "FAIL: $service"
done
```

## 📊 SLO Targets (Hårda krav)

| Metric | Target | Current | Status |
|--------|--------|---------|--------|
| Tool Precision | ≥85% | 54.7% | 🔴 FAIL |
| P95 Latency | ≤900ms | 9580ms | 🔴 FAIL |  
| Success Rate | ≥95% | ~83% | 🔴 FAIL |
| Health Check | 200 OK | ? | ❓ CHECK |

**Regel**: Ingen merge till main förrän ALLA targets är ✅.

## 🚫 DO NOT DO

- ❌ Skapa nytt repo utan att fixa rotorsaker först
- ❌ Hoppa över health-väntan i CI
- ❌ Köra RL förrän SLO gates är gröna  
- ❌ Merge PR med röda checks
- ❌ Använd flaky tests som gates

## ✅ SUCCESS CRITERIA

När följande checklist är ✅, då är systemet redo för RL:

- [ ] CI pipeline grönt (alla jobb pass)
- [ ] Tool precision ≥85%
- [ ] P95 latency ≤900ms  
- [ ] Alla health endpoints 200 OK
- [ ] Security scan 0 CRITICAL/HIGH
- [ ] Branch protection aktiverat
- [ ] Baseline tagged (`v2.0.0-baseline`)

## 📞 Escalation

Om stabiliseringen fastnar:

1. **Day 1-2**: Fokusera på health checks och port-drift
2. **Day 3**: Security scan fixes (update base images)
3. **Day 4**: Eval harness performance tuning
4. **Day 5+**: Överväg migration till nytt repo med sanerad historik

## 📈 Post-Stabilization

När allt är ✅ grönt:

```bash
# 1. Bootstrap RL data  
python services/rl/generate_bootstrap_data.py --episodes 1000 --out data/bootstrap.json

# 2. Initial RL training
python services/rl/automate_rl_pipeline.py --telemetry data/bootstrap.json

# 3. Start shadow mode
python services/rl/shadow_mode.py --action start

# 4. Monitor för canary promotion
python services/rl/shadow_mode.py --action status
```

---
**Status**: 🔄 IN PROGRESS  
**Next Action**: Kör lokal health check och fix första röda flaggan  
**ETA to Green**: 2-3 dagar om inget större hittas