# ✅ T8 Final Checklist - GO/NO-GO Decision

**Alice v2 T8 Stabilization → Production Deployment**

---

## 📋 Phase 1: Stabilisering (KOMPLETT ✅)

- [x] **FormatGuard aktiverad och verifierad**  
  - Svenska language fixes (aa→å, ae→ä, oe→ö) 
  - JSON/markdown structural corrections
  - Conservative mode (safe defaults)

- [x] **RCA fungerar och ger top-orsaker**  
  - PII-safe failure sampling från prod logs
  - Stratified sampling för failure pattern analysis
  - Top failure reasons identificerade

- [x] **Overnight optimizer installerad (8h tick)**  
  - Autonomous 8-hour optimization cycles
  - Morning reports med concrete suggestions
  - Off-policy parameter testing

- [x] **Intent tuner & dry-run patcher på plats**  
  - PSI simulation system klar
  - Safe config management med backup
  - 18 intent regex patterns redo (code, finance, travel, time, weather)

---

## 🌙 Phase 2: Körning (REDO FÖR NATT)

- [ ] **make overnight-8h körd minst en gång (helst nattetid)**  
  - Samla 8 timmar verklig telemetri
  - Generera morning_report.json med suggestions

- [ ] **make intent-simulate på morgonen efter → se PSI now vs sim**  
  - Ladda overnight data + regex suggestions  
  - Simulera PSI-förbättring: 13.296 → ≤0.2 (97% reduction target)

- [ ] **make config-dry-run → patch-fil skapad (telemetry_sources.patch)**  
  - Säker patch generation utan prod-impact
  - Human-readable config diff för granskning

- [ ] **Patch granskad manuellt**  
  - Verifiera intent regex patterns ser vettig ut
  - Kontrollera inga breaking changes

- [ ] **make config-apply om förbättring ser bra ut**  
  - Bara om PSI simulation visar >50% improvement
  - Automatic backup av original config

---

## 📊 Phase 3: Validering (EFTER CONFIG-APPLY)

- [ ] **make t8-telemetry-prod && make t8-drift-prod → PSI ≤0.20, VF ≤1.0%**  
  - Verifiera nya intent buckets fungerar
  - Kontrollera metrics inom SLO gates

- [ ] **Kör make halfday-loop (6–8h) → metrics stabila**  
  - Kontinuerlig mätning tills VF ≤ 1.0%
  - Använd `make dash` för real-time monitoring

- [ ] **Kör make soak-check (72h) → alla gates gröna**  
  - 72 timmar production soak testing
  - PSI, KS, VF alla under thresholds

---

## 🚀 Phase 4: GO (PRODUKTIONSDEPLOY)

- [ ] **make go-check → 🚀 GO**  
  - Final GO/NO-GO decision baserat på 72h soak
  - Alla SLO gates under thresholds

- [ ] **Sätt T8_ENABLED=true (canary, 5%)**  
  - Aktivera T8 stabilization för 5% av trafik
  - Monitor via dashboard för 24-72h

- [ ] **Efter 24–72h fortsatt grönt → T8_ONLINE_ADAPTATION=true (bandit)**  
  - Aktivera full online adaptation
  - Thompson sampling bandit för intent optimization

---

## 🎯 Success Criteria (Alla måste uppfyllas)

### Kritiska Thresholds:
- **verifier_fail ≤ 1.0%** (nu: 37.5%, 37.5x över threshold)
- **PSI intents ≤ 0.20** (nu: 13.296, 66x över threshold) 
- **KS length ≤ 0.20** (nu: 0.25, 1.25x över threshold)

### Performance Gates:
- P95 response latency < 2s (efter FormatGuard pre-processing)
- Intent classification accuracy ≥ 85%
- No degradation i user satisfaction metrics

### Operational Requirements:
- Dashboard visual ✅ (`make dash` working)
- Morning reports generation ✅
- Automated rollback capability ✅
- PII-safe telemetry ✅

---

## 🛠️ Dagtid Tasks (medan overnight-8h rullar)

### Dashboard & Monitoring:
- [x] **T8 Dashboard Kit** - Mermaid grafer för PSI/KS/VF trends
- [ ] Test `make dash` mot real drift data när tillgänglig
- [ ] Setup monitoring alerts för SLO threshold breaches

### Documentation & Readiness:
- [ ] **Incident Playbook** - vad gör vi när PSI sticker iväg?
- [ ] **Team Presentation** - "Alice v2 T8 Pre-GO Status" med screenshots
- [ ] **Rollback Procedures** - dokumentera emergency rollback steps

### Future-Proofing:
- [ ] **T9 Skeleton** - multi-agent preference optimization prep
- [ ] **Adversarial Test Suite** - fler edge-cases för intent classification
- [ ] **API Documentation** - T8 configuration + monitoring endpoints

---

## 📈 Monitoring Commands (Under Stabilization)

```bash
# Real-time dashboard
make dash                    # Render current drift metrics

# Quick status check  
make config-summary         # Show PSI simulation results

# During halfday-loop
make t8-drift-prod          # Check current SLO status

# Emergency procedures
make canary-rollback        # Emergency rollback if metrics degrade
```

---

## 🎯 Expected Timeline

- **Tonight:** `make overnight-8h` (8 timmar data collection)
- **Tomorrow morning:** Intent simulation + config patching (2-4 timmar)  
- **Tomorrow afternoon:** Config apply + halfday-loop start (6-8 timmar)
- **Day 2-4:** Soak testing + monitoring (72 timmar)
- **Day 4:** GO/NO-GO decision + production deployment

---

**🎯 READY STATE:** All infrastructure in place, waiting for overnight telemetry data to optimize intent classification and achieve PSI ≤ 0.20, VF ≤ 1.0% targets för production deployment.**