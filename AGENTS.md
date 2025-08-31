# Alice v2 AGENTS.md
*Instructions and context for AI coding agents working on Alice AI Assistant*

---

## 🚀 **CURRENT PROJECT STATUS (Updated 2025-08-31)**

### **✅ COMPLETED - LLM Integration v1 + Complete Observability System**

Alice v2 har transformerats från prototyp till **robust, production-ready platform** med komplett LLM-integration, säkerhets-, övervaknings-, testramverk och **autonom E2E-validering**:

**🤖 LLM Integration v1:**
- ✅ **Intelligent routing**: Micro (Phi-mini), Planner (Qwen-MoE), Deep (Llama-3.1) med pattern matching
- ✅ **LLM drivers**: Ollama integration med proper timeouts och error handling
- ✅ **Planner execution**: JSON schema validation och tool execution med fallback matrix
- ✅ **Guardian-aware**: Deep blocked i brownout, planner degraded under resurstryck
- ✅ **Fallback system**: LLM + tool fallback med max 1 kedja per turn
- ✅ **SLO compliance**: Fast ≤250ms, planner ≤1500ms, deep ≤3000ms

Alice v2 har transformerats från prototyp till **robust, production-ready platform** med komplett säkerhets-, övervaknings-, testramverk och **autonom E2E-validering**:

**🛡️ Guardian Safety System:**
- ✅ Real-time health monitoring med NORMAL/BROWNOUT/EMERGENCY states
- ✅ 5-punkts sliding window RAM/CPU monitoring (80%/92% trösklar)
- ✅ 60-sekunds recovery hysteresis för stabil tillståndshantering
- ✅ Admission control som skyddar systemet under resurstryck

**📊 Complete Observability System:**
- ✅ **RAM-peak per turn**: Process och system memory tracking i varje turn event
- ✅ **Energy per turn (Wh)**: Energikonsumtion med konfigurerbar baseline
- ✅ **Tool error classification**: Timeout/5xx/429/schema/other kategorisering med Prometheus metrics
- ✅ **Structured turn events**: Komplett JSONL logging med alla metrics och metadata
- ✅ **Real-time dashboard**: Streamlit HUD visar RAM, energi, latens, tool-fel och Guardian status

**🧪 Autonomous E2E Testing:**
- ✅ **Self-contained validation**: `scripts/auto_verify.sh` kör komplett systemvalidering
- ✅ **20 realistiska scenarier**: Svenska samtal som täcker micro/planner/deep routes
- ✅ **SLO validation**: Automatisk P95 threshold checking med Node.js integration
- ✅ **Failure detection**: Exit kode 1 vid SLO-brott eller <80% pass rate
- ✅ **Artifact preservation**: Alla testresultat sparas till `data/tests/` och `test-results/`

**📈 Production Observability:**
- ✅ Streamlit HUD med real-time Guardian timeline (röd/gul/grön)
- ✅ Route latency trends, error budget burn rates, SLO compliance tracking
- ✅ JSONL observability logging till `/data/telemetry` med PII masking
- ✅ Auto-refresh monitoring lämpligt för DevOps-team

**⚡ Complete Brownout Load Testing:**
- ✅ 5 stress test modules: Deep-LLM, Memory balloon, CPU spin, Tool storm, Vision RTSP
- ✅ SLO validation: ≤150ms brownout trigger, ≤60s recovery measurement
- ✅ Real brownout trigger/recovery testing med Guardian state monitoring
- ✅ Structured JSONL telemetry för trendanalys

**🐳 Production Deployment:**
- ✅ Docker Compose orchestration med health checks och dependencies
- ✅ Environment-driven konfiguration med production-safe defaults
- ✅ Komplett dokumentation och setup scripts

---

## 📋 **WHAT WE BUILT - Technical Deep Dive**

### **Core Services Architecture**

```
alice-v2/
├── services/
│   ├── orchestrator/    # ✅ LLM routing & API gateway med LLM integration v1
│   │   ├── src/llm/ollama_client.py   # Ollama client med timeouts
│   │   ├── src/llm/micro_phi.py       # Phi-mini driver för snabba svar
│   │   ├── src/llm/planner_qwen.py    # Qwen-MoE driver med JSON output
│   │   ├── src/llm/deep_llama.py      # Llama-3.1 driver med Guardian integration
│   │   ├── src/router/policy.py       # Intelligent routing med pattern matching
│   │   ├── src/planner/schema.py      # JSON schema för tool execution
│   │   ├── src/planner/execute.py     # Plan execution med fallback matrix
│   │   ├── src/utils/ram_peak.py      # RAM-peak per turn tracking
│   │   ├── src/utils/energy.py        # Energy per turn measurement
│   │   ├── src/utils/tool_errors.py   # Tool error classification
│   │   ├── src/metrics.py             # Real P50/P95 tracking
│   │   ├── src/mw_metrics.py          # ASGI latency middleware  
│   │   ├── src/guardian_client.py     # Guardian integration
│   │   ├── src/status_router.py        # Status API endpoints
│   │   └── src/routers/orchestrator.py # LLM integration + turn logging
│   │
│   ├── guardian/        # ✅ 5-point sliding window safety
│   │   └── main.py      # NORMAL→BROWNOUT→EMERGENCY state machine
│   │
│   ├── eval/            # ✅ Autonomous E2E testing harness
│   │   ├── eval.py       # 20 scenarios, SLO validation
│   │   ├── scenarios.json # Test cases covering all routes
│   │   └── requirements.txt # Dependencies
│   │
│   └── loadgen/         # ✅ Complete brownout testing suite
│       ├── main.py      # Orchestrates stress + measures SLO
│       ├── watchers.py  # Mäter brownout trigger/recovery latency
│       └── burners/     # 5 stress test modules
│
├── monitoring/          # ✅ Streamlit production HUD
│   ├── alice_hud.py     # Real-time Guardian + metrics visualization
│   └── mini_hud.py      # Lightweight dashboard för eval results
│
├── scripts/             # ✅ Autonomous E2E test automation + port management
│   ├── auto_verify.sh   # Complete system validation script
│   ├── ports-kill.sh    # Port cleanup script
│   └── start-llm-test.sh # LLM integration test script
│
├── data/telemetry/      # ✅ Structured JSONL logging
├── data/tests/          # ✅ E2E test artifacts
└── test-results/        # ✅ Nightly validation trends
```

### **Key Technical Implementations**

**LLM Integration v1 (services/orchestrator/src/routers/orchestrator.py):**
```python
# Route to appropriate model using LLM Integration v1
route = route_request(chat_request)
logger.info("Route selected", route=route)

# Generate response based on route
if route == "micro":
    micro_driver = get_micro_driver()
    llm_response = micro_driver.generate(chat_request.message)
elif route == "planner":
    planner_driver = get_planner_driver()
    llm_response = planner_driver.generate(chat_request.message)
    # Execute plan if JSON was parsed successfully
    if llm_response.get("json_parsed") and llm_response.get("plan"):
        planner_executor = get_planner_executor()
        plan = planner_executor.validate_plan(llm_response["plan"])
        if plan:
            planner_execution = planner_executor.execute_plan(plan)
elif route == "deep":
    deep_driver = get_deep_driver()
    llm_response = deep_driver.generate(chat_request.message)
```

**Turn Event Logging (services/orchestrator/src/routers/orchestrator.py):**
```python
def log_turn_event(trace_id: str, session_id: str, route: str, 
                   e2e_first_ms: float, e2e_full_ms: float,
                   ram_peak_mb: Dict[str, float], energy_wh: float,
                   tool_calls: List[Dict], guardian_state: str):
    """Logga komplett turn event med alla metrics"""
    event = {
        "v": "1", "ts": datetime.utcnow().isoformat() + "Z",
        "trace_id": trace_id, "session_id": session_id, "route": route,
        "e2e_first_ms": e2e_first_ms, "e2e_full_ms": e2e_full_ms,
        "ram_peak_mb": ram_peak_mb, "energy_wh": energy_wh,
        "tool_calls": tool_calls, "guardian_state": guardian_state
    }
    # Skriv till JSONL fil
```

**Autonomous E2E Testing (scripts/auto_verify.sh):**
```bash
#!/usr/bin/env bash
# Startar tjänster, väntar på hälsa, kör eval, validerar SLO
docker compose up -d orchestrator guardian
# Väntar på hälsa...
./services/eval/eval.py  # Kör 20 scenarier
# Node.js SLO validation...
# Exit 1 vid SLO-brott eller <80% pass rate
```

**Eval Harness (services/eval/eval.py):**
```python
def run_chat(text, session="eval"):
    payload = {"v":"1","session_id":f"{session}-{uuid.uuid4().hex[:6]}",
               "lang":"sv","text":text}
    t0 = time.perf_counter()
    with httpx.Client(timeout=10) as c:
        r = c.post(f"{API}/api/chat", json=payload)
    dt = (time.perf_counter()-t0)*1000
    return r, dt
```

---

## 🎯 **NEXT PRIORITIES - Where to Go From Here**

### **HIGH PRIORITY (Ready for Next AI Agent)**

1. **🎤 Voice Pipeline Implementation**
   - **Current**: Arkitektur klar, services stubbed
   - **Next**: ASR→NLU→TTS pipeline med WebSocket connections  
   - **Location**: `services/voice/` (needs implementation)
   - **Swedish Focus**: Whisper ASR, svenska språkmodeller
   - **Testing**: Utöka `services/eval/scenarios.json` med voice scenarios

2. **🌐 Web Frontend Integration**
   - **Current**: Next.js app structure i `apps/web/`
   - **Next**: Koppla frontend till Orchestrator API
   - **Features**: Chat UI, Guardian status display, voice controls
   - **Validation**: Integrera frontend i `auto_verify.sh` E2E test

2. **🎤 Voice Pipeline Implementation**
   - **Current**: Arkitektur klar, services stubbed
   - **Next**: ASR→NLU→TTS pipeline med WebSocket connections  
   - **Location**: `services/voice/` (needs implementation)
   - **Swedish Focus**: Whisper ASR, svenska språkmodeller
   - **Testing**: Utöka `services/eval/scenarios.json` med voice scenarios

3. **🌐 Web Frontend Integration**
   - **Current**: Next.js app structure i `apps/web/`
   - **Next**: Koppla frontend till Orchestrator API
   - **Features**: Chat UI, Guardian status display, voice controls
   - **Validation**: Integrera frontend i `auto_verify.sh` E2E test

### **MEDIUM PRIORITY**

4. **📦 Package System Completion**
   - **Current**: TypeScript packages i `packages/`
   - **Next**: Komplettera API client, types, UI components
   - **Purpose**: Shared kod mellan services och frontend

5. **🔧 Advanced Monitoring**  
   - **Current**: Streamlit HUD med comprehensive metrics
   - **Next**: Prometheus/Grafana integration, alerting
   - **Location**: Utöka `monitoring/` med metrics exporters

### **LOW PRIORITY (Future Iterations)**

6. **🤖 Advanced AI Features**
   - Multi-modal processing (text + voice + vision)
   - Context retention across sessions
   - Learning från user interactions

7. **⚡ Performance Optimization**
   - LLM response caching
   - Load balancing för multiple instances
   - Database integration för persistent state

---

## 🛠️ **DEVELOPMENT CONTEXT FOR NEXT AI**

### **How We Work - Proven Approach**

**✅ Autonomous E2E Testing:**
```bash
# Komplett systemvalidering med en kommand
./scripts/auto_verify.sh
# Startar tjänster, kör eval, validerar SLO, sparar artifacts
```

**✅ Real Integration Testing (No Mocks):**
```bash
# Vi testar mot riktiga services med realistiska förväntningar
pytest src/tests/test_real_integration.py -v
# Success rate: 80-95% (inte 100% perfectionism)
```

**✅ Production-Tight Development:**
```bash  
# Starta hela stacken för development
docker compose up -d guardian orchestrator

# Kör autonom validering
./scripts/auto_verify.sh

# Övervaka i realtid  
cd monitoring && streamlit run mini_hud.py
```

**✅ Structured Development Workflow:**
1. **Plan**: Använd TodoWrite för att tracka tasks
2. **Implement**: Real integration från början (inga mocks)
3. **Test**: Kör `./scripts/auto_verify.sh` för komplett validering
4. **Monitor**: Använd HUD för att se impact i realtid
5. **Validate**: SLO compliance via autonomous testing

### **Architecture Principles to Follow**

- **Safety First**: Guardian ska alltid vara första prioritet
- **Real Data**: Mät verkliga metrics, inte mocks eller estimates
- **Production Ready**: Allt ska vara deployment-ready från dag 1
- **Observable**: Logga structured data för debugging och ML training
- **Autonomous Testing**: Alla features ska valideras via `auto_verify.sh`
- **Swedish Focus**: Alice är optimerad för svenska användare

### **Code Conventions Established**

- **Python Services**: FastAPI + Pydantic, strukturerad logging med structlog
- **Testing**: pytest med realistic expectations (80-95% success rates)  
- **E2E Testing**: `scripts/auto_verify.sh` för komplett validering
- **Monitoring**: JSONL för structured logging, Streamlit för dashboards
- **Docker**: Health checks, proper dependencies, environment-driven config
- **Git**: Descriptive commits med 🤖 Claude Code signature

### **Files You Should Read First**

1. **`README.md`** - Production deployment guide
2. **`ALICE_SYSTEM_BLUEPRINT.md`** - System architecture  
3. **`TESTING_STRATEGY.md`** - Our proven testing approach
4. **`scripts/auto_verify.sh`** - Autonomous E2E testing
5. **`services/eval/eval.py`** - Eval harness implementation
6. **`services/orchestrator/main.py`** - Current integration points
7. **`monitoring/mini_hud.py`** - Real-time system visibility

### **Key Environment Setup**

```bash
# Repository navigation
cd alice-v2

# Start production stack
docker compose up -d guardian orchestrator

# Development environment  
cd services/orchestrator
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# Test everything works
curl http://localhost:8000/api/status/simple
curl http://localhost:8787/health

# Run autonomous validation
./scripts/auto_verify.sh

# Start monitoring
cd monitoring && streamlit run mini_hud.py
```

---

## 🔮 **STRATEGIC DIRECTION**

Alice v2 har gått från prototyp till **production-ready platform med komplett observability och autonom E2E-testing**. Nästa AI agent kan fokusera på **actual LLM integration** och **voice pipeline** medan hela safety/monitoring/test infrastrukturen redan är robust.

**Key Success Factors:**
- Guardian säkerhetsystem ger trygg LLM experimentation 
- Complete observability ger immediate feedback på förändringar
- Autonomous E2E testing validerar att nya features inte bryter SLO
- HUD dashboard ger visual confirmation att allt fungerar

**Philosophy**: Vi bygger inte bara en AI assistant - vi bygger en **robust, observable, säker plattform** som kan utvecklas iterativt utan att kompromissa på kvalitet eller säkerhet, med autonom validering av alla förändringar.

---

**🤖 Status Updated by Claude Code - Alice v2 observability + eval-harness v1 complete! Ready for LLM integration! 🚀**

---

## ⚡ NEXT AI QUICKSTART (Dev-Proxy - No Mocks)

Snabbstart för nästa AI-agent – allt via dev-proxy på port 18000.

### 1) Starta stacken
```bash
scripts/dev_up.sh
# eller
docker compose up -d guardian orchestrator nlu dashboard dev-proxy
```

### 2) Sanity via proxy
```bash
curl -s http://localhost:18000/health | jq .
curl -s http://localhost:18000/api/status/routes | jq .
```

### 3) NLU sanity (svenska)
```bash
curl -s -X POST http://localhost:18000/api/nlu/parse \
  -H 'Content-Type: application/json' \
  -d '{"v":"1","lang":"sv","text":"Boka möte med Anna imorgon kl 14","session_id":"nlu-sanity"}' | jq .
```

### 4) E2E verify (autonomt)
```bash
./scripts/auto_verify.sh || (echo "FAIL – se data/tests/summary.json" && exit 1)
cat data/tests/summary.json | jq .
open http://localhost:18000/hud
```

### 5) NLU v1 – DoD (nästa steg)
- `/api/nlu/parse` P95 ≤ 80 ms (5 min fönster)
- Intent-accuracy ≥ 92% (svensk svit)
- Slots: ISO för uttryck som “imorgon 14:00”
- Orchestrator sätter `X-Route-Hint` → route syns i P95 per route
