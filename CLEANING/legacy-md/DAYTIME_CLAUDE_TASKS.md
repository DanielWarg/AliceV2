# 🌅 Daytime Tasks för Claude Code (medan overnight-8h rullar)

Eftersom overnight data collection behöver köras nattetid för realistisk användarmönster, här är värdefulla tasks för dagtid med Claude Code:

---

## 🎯 Prioriterade Tasks (hög impact)

### 1. Incident Playbook & Emergency Procedures
**Prompt för Claude Code:**
```
Skapa en T8 Incident Playbook i ops/runbooks/T8_INCIDENT_RESPONSE.md som täcker:
- Vad gör vi när PSI plötsligt sticker iväg (>1.0)?
- Emergency rollback procedures för config changes  
- Escalation paths för olika severity levels
- Quick diagnosis commands för troubleshooting
- Contact info + team responsibilities

Inkludera konkreta make commands och decision trees.
```

### 2. Team Presentation Materials  
**Prompt för Claude Code:**
```
Bygg en "Alice v2 T8 Pre-GO Status" presentation i ops/presentations/:
- T8_STATUS_PRESENTATION.md med executive summary
- Include screenshots från `ops/dashboards/dashboard.md`  
- Key metrics: baseline vs targets (VF: 37.5%→1.0%, PSI: 13.296→0.2)
- Timeline för GO decision (4-day plan)
- Risk mitigation strategies

Make it executive-friendly med clear GO/NO-GO criteria.
```

### 3. Adversarial Test Suite Enhancement
**Prompt för Claude Code:**
```
Utöka tests/test_intent_classification_adversarial.py med:
- Svenska slang + dialekter ("Tjena", "Hallå", "Tjo")
- Edge cases för code detection (embedded SQL, weird syntax) 
- Financial terms variations (swish vs "mobilt betalning")
- Travel booking scenarios (SJ, flyg, hotell edge cases)
- Generate 50+ test cases med expected intent buckets

Kör mot våra 18 intent regex patterns för validation.
```

---

## 🔧 Tekniska Förbättringar (medium impact)

### 4. T9 Multi-Agent Preference Prep
**Prompt för Claude Code:**
```
Skapa skelett för T9 i services/rl/multi_agent/:
- multi_agent_optimizer.py (placeholder för Thompson sampling mellan agents)
- preference_aggregator.py (combine preferences från flera agents)  
- conflict_resolver.py (resolve när agents disagree)
- tests/test_multi_agent_basic.py

T9 kommer använda T8s stabilized metrics som input för multi-agent optimization.
```

### 5. API Documentation Generation
**Prompt för Claude Code:**
```
Generera OpenAPI specs för T8 monitoring endpoints:
- GET /api/t8/metrics (PSI, KS, VF current values)
- GET /api/t8/dashboard (dashboard data som JSON)
- POST /api/t8/config-patch (safe config updating)
- GET /api/t8/slo-status (current gate status)

Skriv till ops/api/t8_monitoring_api.yml + generate docs.
```

### 6. Enhanced Dashboard Features
**Prompt för Claude Code:**
```
Förbättra ops/dashboards/render_dashboard.py:
- Add trend arrows (↑↓) för metrics changes
- SLO gate status indicators (🔴🟡🟢)  
- Add "time to SLO compliance" projections
- Export dashboard som PNG via mermaid-cli integration
- Add email alerting när metrics breach thresholds

Testa med `make dash-enhanced`.
```

---

## 📚 Dokumentation & Kunskapsdelning (low impact, men värdefull)

### 7. T8 Deep Dive Technical Guide
**Prompt för Claude Code:**
```
Skriv docs/T8_TECHNICAL_DEEP_DIVE.md som förklarar:
- Varför PSI är bästa metric för intent drift detection
- Matematik bakom FormatGuard preprocessing  
- Thompson sampling för intent bucket optimization
- Safe config management patterns vi använder

Target: senior developers som vill förstå T8 internals.
```

### 8. Troubleshooting Database
**Prompt för Claude Code:**
```
Skapa ops/troubleshooting/T8_COMMON_ISSUES.md:
- "PSI won't drop below 5.0" → likely causes + fixes
- "FormatGuard not applying fixes" → debug steps
- "Config patches failing" → validation issues
- "Dashboard showing no data" → data pipeline debug

Format as searchable FAQ med concrete solutions.
```

---

## 🎮 Testing & Quality Assurance  

### 9. Load Testing for T8 Components
**Prompt för Claude Code:**
```
Skapa tests/load/t8_load_test.py som testar:
- FormatGuard performance under 1000 requests/sec
- Intent classification latency med 18 regex patterns
- Dashboard rendering med 10k+ data points  
- Config patch generation speed

Använd locust eller similar för realistic load simulation.
```

### 10. End-to-End Integration Test
**Prompt för Claude Code:**
```
Bygg tests/integration/test_t8_e2e_flow.py som kör:
1. Generate fake overnight data
2. Run intent simulation  
3. Generate config patch
4. Apply patch (test mode)
5. Validate metrics improvement  
6. Generate dashboard
7. Verify all artifacts exist

Full T8 pipeline test för CI/CD confidence.
```

---

## 🏆 Success Criteria för Daytime Tasks

- [ ] **Incident Response:** Ready att hantera T8 issues under production load
- [ ] **Team Readiness:** Presentation materials klara för GO/NO-GO meeting  
- [ ] **Technical Debt:** T9 foundation + enhanced monitoring på plats
- [ ] **Quality Assurance:** Robust testing suite för T8 components

---

## 💡 Starter Commands

```bash
# Quick task validation
make test-t8-adversarial     # Test new adversarial cases
make dash-enhanced           # Render enhanced dashboard  
make t8-api-docs            # Generate T8 API documentation
make t8-load-test           # Run T8 component load tests

# Documentation check
grep -r "TODO\|FIXME" docs/  # Find documentation gaps
make validate-docs          # Check all docs render correctly
```

---

**🎯 DAYTIME GOAL:** Ha ett robust, well-documented, battle-tested T8 system redo för produktion när overnight data kommer in imorgon.**