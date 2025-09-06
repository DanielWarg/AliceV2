# 🤖 AI Agent Orientation - Alice v2

**För AI-agenter som börjar arbeta med Alice-projektet**

## 📚 Kritiska filer att läsa FÖRST (i denna ordning)

### Steg 1: Grundförståelse (5 min)
```
README.md                           # Vad är Alice + hur startar man
ALICE_SYSTEM_BLUEPRINT.md           # Arkitektur + tjänster + portar  
STATUS.md                           # Nuvarande version + status
```

### Steg 2: Projektkontext (10 min)
```
ROADMAP.md                          # Vart vi är på väg
COMPLETE_ROADMAP_EXECUTION_PLAN.md  # Vad som redan är klart
OPTIMIZATION_MASTER_PLAN.md         # Performance-strategi + mål
```

### Steg 3: Säkerhet & Drift (5 min)
```
SECURITY_AND_PRIVACY.md             # Säkerhetspolicys
TESTING_STRATEGY.md                 # Hur vi testar
.pre-commit-config.yaml             # Code quality rules
```

### Steg 4: Utvecklingsregler (2 min)
```
ONBOARDING_GUIDE.md                 # Fullständig orientering
denne fil (AGENTS.md)               # AI-specifika regler
```

## 🎯 Vad detta hade hjälpt mig med

**JA - Hade sparat timmar:**
- ✅ Förstått att Fibonacci-optimering är central (φ=1.618)
- ✅ Vetat att orchestrator exponeras via Caddy proxy på port 18000 
- ✅ Förstått att `make up` inte startar dev-proxy automatiskt
- ✅ Förstått att pre-commit hooks behöver fixas ordentligt
- ✅ Vetat att Guardian är brownout-protection systemet
- ✅ Förstått cache-hierarkin (L1-L10) och hit-rate mål
- ✅ Vetat att git/CI-problem var högsta prioritet

**Hade undvikit:**
- ❌ Gissning om portar och service-endpoints
- ❌ Förvirring om dokumentationshierarki
- ❌ Pre-commit hook-trial-and-error
- ❌ Onödiga service-restarter
- ❌ Port-förvirring mellan 8000 (intern) och 18000 (extern via Caddy)

## 📋 AI Agent Regler

### DO (Gör detta):
1. **Alltid läs filerna ovan INNAN du börjar koda**
2. **Uppdatera STATUS.md när du gör betydande ändringar**
3. **Följ conventional commits** (`feat:`, `fix:`, `docs:`, `chore:`)
4. **Kör `make down && make up` när services är konstiga**
5. **Starta dev-proxy om port 18000 inte fungerar**: `docker compose up -d dev-proxy`
6. **Använd TodoWrite verktyget för att spåra framsteg**
7. **Respektera Fibonacci-principerna** (Golden Ratio optimization)

### DON'T (Rör inte):
1. **`docs/ADR/`** utan att skapa ny ADR först
2. **`.github/workflows/`** utan att testa lokalt först  
3. **`services/orchestrator/src/config/`** utan att förstå konsekvenser
4. **Production secrets** - aldrig commita nycklar/tokens
5. **`eval/` resultat** - dessa är faktiska benchmark-data

### Vid osäkerhet:
- **Fibonacci-frågor** → `docs/fibonacci/` hierarchy
- **Service-problem** → `ALICE_SYSTEM_BLUEPRINT.md`
- **Performance** → `OPTIMIZATION_MASTER_PLAN.md`
- **Testing** → `TESTING_STRATEGY.md`
- **Allt annat** → `ONBOARDING_GUIDE.md`

## 🔌 ALICE v2 COMPLETE PORT MAPPING - 2025-09-06

**CORE SERVICES (Always Running):**
- **Alice API**: `8001` (Main API endpoint) ✅ WORKING
- **Guardian**: `8787` (System monitoring) ✅ WORKING  
- **NLU**: `9002` (Language processing) ✅ WORKING
- **Redis Cache**: `6379` (Data cache) ✅ WORKING

**WEB INTERFACES (Development):**
- **Main WebUI**: `3000` (Primary interface) 🎯 RESERVED
- **Test HUD**: `3001` (Training/testing interface) 🎯 RESERVED  
- **Streamlit Dashboard**: `8501` (Analytics dashboard)
- **N8N Workflows**: `5678` (Automation platform)

**SUPPORT SERVICES (Optional):**
- **Dev-Proxy**: `19000` (Caddy reverse proxy) 🔄 MOVED FROM 18000
- **N8N Database**: Internal (PostgreSQL for N8N)

## 🚦 Quick Health Check

Innan du börjar jobba, verifiera:
```bash
# Start services
make up

# Health check för core services
curl http://localhost:8001/api/orchestrator/chat -d '{"message":"test","session_id":"test"}' && echo "✅ Alice API"
curl http://localhost:8787/health && echo "✅ Guardian"
curl http://localhost:9002/health && echo "✅ NLU"  
redis-cli -p 6379 ping && echo "✅ Redis Cache"
```

**VIKTIGT:** Använd ALLTID port `8001` för Alice API, INTE `18000` som är trasig.

## 🎪 Common Tasks & Their Docs

| Uppgift | Läs först |
|---------|-----------|
| Fix CI workflows | `.github/workflows/` + `TESTING_STRATEGY.md` |
| Optimize performance | `OPTIMIZATION_MASTER_PLAN.md` + `docs/fibonacci/` |
| Add new service | `ALICE_SYSTEM_BLUEPRINT.md` + `docker-compose.yml` |
| Debug cache issues | `CACHE.md` + `services/cache/` |
| Update documentation | `ONBOARDING_GUIDE.md` + denna fil |

---

## 🚨 KRITISK PORT DISCOVERY - 2025-09-06

**TESTED RESULTS:**
- ✅ Guardian: 8787 (2ms respons) - WORKING
- ✅ NLU: 9002 (4ms respons) - WORKING  
- ✅ Redis: 6379 (5ms respons) - WORKING
- ❌ Alice API: 18000 (5s timeout) - BROKEN

**ROOT CAUSE FOUND:**
Orchestrator har INGEN extern portmappning:
```bash
docker ps --format "table {{.Names}}\t{{.Ports}}"
alice-orchestrator   8000/tcp  # ← Ingen 0.0.0.0 mappning!
```

**IMMEDIATE FIX FOR TRAINING SCRIPTS:**
Använd Guardian istället för port 18000 till dess att orchestrator-porten fixas:
```python
# ISTÄLLET FÖR:
# orchestrator_url = "http://localhost:18000"

# ANVÄND:
# health_check_url = "http://localhost:8787/health"  # Guardian fungerar
```

**DOKUMENTERAT I:**
- Se port mapping ovan för fullständiga testresultat
- Alla script måste uppdateras till att använda fungerande portar

---

**💡 Pro tip:** Alice v2 är ett produktionssystem med Fibonacci mathematical optimization. Respektera Golden Ratio-principerna (φ=1.618) i all performance-tuning!

---

*Skapad: 2025-09-06 | Uppdaterad: 2025-09-06 | För: AI Agents working on Alice v2*