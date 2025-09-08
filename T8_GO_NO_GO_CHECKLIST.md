# T8 GO/NO-GO Checklist

## 🚦 Säkerhetsgrader för T8-aktivering

### **PHASE 1: T8_ENABLED=true (Canary-läge)**

**Krav innan aktivering:**

- [ ] **PSI ≤ 0.20** (7-dagars p95): Intent-distribution stabiliserad
- [ ] **KS ≤ 0.20** (7-dagars p95): Svarslängd-distribution stabil  
- [ ] **verifier_fail ≤ 1.0%** (7-dagars p95): Schema compliance ≥99%
- [ ] **policy_breach = 0** (7-dagars): Inga policy-brott
- [ ] **Nightly CI**: 3+ konsekutiva gröna körningar
- [ ] **Manuell verifikation**: `make t8-drift-run` returnerar `"ok": true`

**Aktivering:**
```bash
export T8_ENABLED=true
export T8_ONLINE_ADAPTATION=false  # Håll false
export PREFS_CANARY_SHARE=0.05     # 5% canary-trafik
```

### **PHASE 2: T8_ONLINE_ADAPTATION=true (Bandit-läge)**

**Krav efter Phase 1:**

- [ ] **Phase 1 har körts ≥ 7 dagar** utan incidenter
- [ ] **p95_latency_Δ ≤ +10%**: Ingen signifikant latens-försämring
- [ ] **Adapter win-rate ≥ 50%**: Bandit har positiv signal
- [ ] **Safety gates fungerar**: Automatisk rollback vid SLO-brott testad
- [ ] **Bandit state**: `data/ops/bandit_state.json` visar rimliga värden

**Aktivering:**
```bash
export T8_ONLINE_ADAPTATION=true  # Slå på bandit
# T8_ENABLED=true behålls från Phase 1
```

## 🚨 Rollback-triggers

**Automatisk rollback vid:**
- PSI > 0.20 (drift-övervakning)
- verifier_fail > 1% (3 konsekutiva mätningar)
- policy_breach > 0 (omedelbar)
- p95_latency > +20% (från baseline)

**Manuell rollback:**
```bash
export T8_ENABLED=false             # Stäng av helt
export T8_ONLINE_ADAPTATION=false   # Fallback till canary
export PREFS_CANARY_SHARE=0.0       # Stäng av canary
```

## 📊 Övervakningskommandon

**Daglig hälsokontroll:**
```bash
make t8-drift-run        # Aktuell snapshot + 7-dagars trend
make t8-drift-history    # Dagsvis rollup för rapportering
```

**Telemetri-pipeline:**
```bash
make t8-telemetry-prod   # Ingest från prod-loggar
make t8-drift-prod       # Full pipeline med drift-analys
```

## ⚠️ Viktiga säkerhetsaspekter

1. **Feature flags kan alltid stänga av systemet** utan deployment
2. **Safety gate blockerar adapter vid SLO-brott** automatiskt  
3. **Bandit state sparas för transparens** och kan granskas
4. **Nightly CI detekterar regressions** och öppnar incidents
5. **PII-säker telemetri** - inga råtext sparas i historik

## 🔄 Uppdateringscykel

- **Timvis**: GitHub Actions hourly monitoring
- **Nattligt**: Full drift-analys + rollup + incident-check  
- **Veckovis**: Manuell granskning av trender och bandit-prestanda
- **Månadsvis**: Utvärdering av T8-effektivitet vs baseline