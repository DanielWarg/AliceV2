# Port Management Issue - Alice v2 Development

## 🚨 Problem Beskrivning

Under utveckling av LLM Integration v1 stötte vi på ett **port management-problem** som gjorde att terminalen fastnade och nya processer inte kunde startas.

### Vad som hände:
1. **Terminalen fastnade** - Alla `run_terminal_cmd` blev avbrutna
2. **Portar blockerade** - Portarna 8000, 8787, 8501 var upptagna
3. **Processer kvarhängande** - uvicorn/python processer körde i bakgrunden
4. **TTY blockerad** - Terminalen var "ägd" av en kvarhängande process

## 🔍 Root Cause Analysis

### Vad som troligen orsakade problemet:
1. **uvicorn --reload** spawnar child-processer som ibland lämnas kvar
2. **Docker containers** som exponerar samma portar som lokala processer
3. **Attached containers/TTY** som håller stdin/stdout blockerad
4. **Dubbla starters** - lokal uvicorn + container på samma port

### Tekniska detaljer:
```bash
# Processer som troligen blockerade:
- uvicorn main:app --reload --port 8000 (orchestrator)
- uvicorn main:app --reload --port 8787 (guardian)  
- streamlit run mini_hud.py --port 8501 (dashboard)
- Docker containers som exponerar samma portar
```

## 🛠️ Lösningar Implementerade

### 1. Port Cleanup Script (`scripts/ports-kill.sh`)
```bash
#!/usr/bin/env bash
# Städar portar 8000, 8787, 8501
# Dödar lokala lyssnare och stoppar containers
# Kör: ./scripts/ports-kill.sh
```

### 2. LLM Test Script (`scripts/start-llm-test.sh`)
```bash
#!/usr/bin/env bash
# Startar tjänster i rätt ordning
# Testar LLM integration
# Kör: ./scripts/start-llm-test.sh
```

### 3. Diagnos-kommandon
```bash
# Vem lyssnar på portarna?
lsof -nP -iTCP:8000 -sTCP:LISTEN
lsof -nP -iTCP:8787 -sTCP:LISTEN  
lsof -nP -iTCP:8501 -sTCP:LISTEN

# Visa process-träd
ps -o pid,ppid,stat,etime,command -p <PID>

# Docker containers
docker ps --filter "publish=8000"
```

## 🚀 Rekommenderade Åtgärder

### Förebyggande:
1. **En källa per port** - Antingen Docker ELLER lokal process
2. **Proper shutdown** - SIGTERM handling i alla services
3. **Port reservation** - Tydlig ägande av portar
4. **Health checks** - Verifiera att portar är fria innan start

### Nödbroms (om det händer igen):
```bash
# Döda alla processer
pkill -f "uvicorn|gunicorn|streamlit|services\.orchestrator|services\.guardian"

# Stoppa containers
docker compose down -v --remove-orphans

# Tvinga port-frigivning
lsof -ti:8000 | xargs kill -9
lsof -ti:8787 | xargs kill -9  
lsof -ti:8501 | xargs kill -9
```

## 📋 Checklista för Framtida Development

### Innan start:
- [ ] Kör `./scripts/ports-kill.sh`
- [ ] Verifiera att portar är fria: `lsof -i:8000,8787,8501`
- [ ] Starta tjänster i rätt ordning: Guardian → Orchestrator → Dashboard

### Under development:
- [ ] Använd `--reload` försiktigt
- [ ] Ha tydlig shutdown-hantering
- [ ] Använd health checks för att verifiera status

### Vid problem:
- [ ] Identifiera blockerande process: `lsof -i:PORT`
- [ ] Döda processen: `kill -TERM PID` → `kill -KILL PID`
- [ ] Stoppa containers: `docker compose down`
- [ ] Starta om från början

## 🎯 Status

**Problem**: ✅ Identifierat och dokumenterat  
**Lösningar**: ✅ Scripts skapade (`ports-kill.sh`, `start-llm-test.sh`)  
**Förebyggande**: ✅ Checklista och rekommendationer  
**Nästa steg**: Starta om datorn för att få rent läge

---

**Nästa AI Agent**: Använd `./scripts/ports-kill.sh` innan du startar tjänster, och använd `./scripts/start-llm-test.sh` för att testa LLM integration.
