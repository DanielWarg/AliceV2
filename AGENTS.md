# Alice v2 AGENTS.md
*Instructions and context for AI coding agents working on the Alice AI Assistant*

> **⚠️ IMPORTANT**: This file is for AI coding agents only and should NOT be committed to Git. All project documentation must be in English.

## 🌐 Documentation Language Policy

**REQUIRED**: All `.md` files in this repository must be written in English only.
- **CI Guard**: GitHub Actions automatically checks for Swedish text in documentation
- **Exclusions**: Only `docs/archive/` directory may contain non-English content
- **Purpose**: Ensure international accessibility and maintain professional standards

**Files to translate**: `README.md`, `ROADMAP.md`, `ALICE_SYSTEM_BLUEPRINT.md`, `TESTING_STRATEGY.md`, `SECURITY.md`, `CONTRIBUTING.md`, `GITHUB_SETUP.md`, and all service README files.

---

## 🚀 CURRENT PROJECT STATUS (Updated 2025-09-01)

### ✅ COMPLETED – Observability + Eval Harness v1, Routing v1 ready

Alice v2 is a robust, production‑ready platform with complete safety, observability, autonomous E2E testing and an initial LLM routing stack. Next agents can focus on real LLM integration and the voice pipeline while the guardrails are already in place.

---

## 🚦 Live Milestone Tracker (read first)
- See `ROADMAP.md` → section "🚦 Live Milestone Tracker" for current status, next step and live test‑gates.
- Policy: Do not check off a step until `./scripts/auto_verify.sh` is green and artifacts exist in `data/tests/` and `data/telemetry/`.

---

## 📋 WHAT WE BUILT – Technical Deep Dive

### Core Services Architecture

```
alice-v2/
├── services/
│   ├── orchestrator/    # ✅ LLM routing & API gateway with LLM integration v1
│   │   ├── src/llm/ollama_client.py   # Ollama client with timeouts
│   │   ├── src/llm/micro_phi.py       # Phi-mini driver for fast replies
│   │   ├── src/llm/planner_qwen.py    # Qwen-MoE driver with JSON output
│   │   ├── src/llm/deep_llama.py      # Llama-3.1 driver with Guardian integration
│   │   ├── src/router/policy.py       # Intelligent routing with pattern matching
│   │   ├── src/planner/schema.py      # JSON schema for tool execution
│   │   ├── src/planner/execute.py     # Plan execution with fallback matrix
│   │   ├── src/utils/ram_peak.py      # RAM-peak per turn tracking
│   │   ├── src/utils/energy.py        # Energy per turn measurement
│   │   ├── src/utils/tool_errors.py   # Tool error classification
│   │   ├── src/metrics.py             # Real P50/P95 tracking
│   │   ├── src/mw_metrics.py          # ASGI latency middleware
│   │   ├── src/guardian_client.py     # Guardian integration
│   │   ├── src/status_router.py       # Status API endpoints
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
│   └── loadgen/         # ✅ Brownout testing suite
│       ├── main.py      # Orchestrates stress + measures SLO
│       ├── watchers.py  # Brownout trigger/recovery latency
│       └── burners/     # 5 stress test modules
│
├── monitoring/          # ✅ Streamlit production HUD
│   ├── alice_hud.py     # Real-time Guardian + metrics visualization
│   └── mini_hud.py      # Lightweight dashboard for eval results
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

### Key Technical Implementations

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

**Turn Event Logging (services/orchestrator/src/routers/orchestrator.py & chat.py):**
```python
def log_turn_event(trace_id: str, session_id: str, route: str,
                   e2e_first_ms: float, e2e_full_ms: float,
                   ram_peak_mb: Dict[str, float], energy_wh: float,
                   tool_calls: List[Dict], guardian_state: str):
    """Log full turn event with all metrics"""
    event = {
        "v": "1", "ts": datetime.utcnow().isoformat() + "Z",
        "trace_id": trace_id, "session_id": session_id, "route": route,
        "e2e_first_ms": e2e_first_ms, "e2e_full_ms": e2e_full_ms,
        "ram_peak_mb": ram_peak_mb, "energy_wh": energy_wh,
        "tool_calls": tool_calls, "guardian_state": guardian_state
    }
    # Write to JSONL file under data/telemetry/YYYY-MM-DD/events_YYYY-MM-DD.jsonl
```

**Autonomous E2E Testing (scripts/auto_verify.sh):**
```bash
#!/usr/bin/env bash
# Starts services, waits for health, runs eval, validates SLO
docker compose up -d orchestrator guardian
# Wait for health…
./services/eval/eval.py  # Runs 20 scenarios
# Node.js SLO validation…
# Exit 1 on SLO breach or <80% pass rate
```

**Eval Harness (services/eval/eval.py):**
```python
def run_chat(text, session="eval"):
    payload = {"session_id": f"{session}-{uuid.uuid4().hex[:6]}", "message": text}
    t0 = time.perf_counter()
    with httpx.Client(timeout=10) as c:
        r = c.post(f"{API}/api/chat", json=payload, headers={"Authorization": "Bearer test-key-123"})
    dt = (time.perf_counter() - t0) * 1000
    return r, dt
```

---

## 🎯 NEXT PRIORITIES – Where to go from here

### HIGH PRIORITY (Ready for the next AI agent)
1. **🎤 Voice Pipeline Implementation**
   - **Current**: Architecture ready, services stubbed
   - **Next**: ASR→NLU→TTS pipeline with WebSocket connections  
   - **Location**: `services/voice/` (needs implementation)
   - **Swedish Focus**: Whisper ASR, Swedish language models
   - **Testing**: Extend `services/eval/scenarios.json` with voice scenarios

2. **🌐 Web Frontend Integration**
   - **Current**: Next.js app structure in `apps/web/`
   - **Next**: Connect frontend to Orchestrator API
   - **Features**: Chat UI, Guardian status display, voice controls
   - **Validation**: Integrate frontend into `auto_verify.sh` E2E test

3. **NLU XNLI enablement** (place ONNX in `./models`, set `NLU_XNLI_ENABLE=true`, update eval with challenging scenarios)

### MEDIUM PRIORITY

4. **📦 Package System Completion**
   - **Current**: TypeScript packages in `packages/`
   - **Next**: Complete API client, types, UI components
   - **Purpose**: Shared code between services and frontend

5. **🔧 Advanced Monitoring**  
   - **Current**: Streamlit HUD with comprehensive metrics
   - **Next**: Prometheus/Grafana integration, alerting
   - **Location**: Extend `monitoring/` with metrics exporters

### LOW PRIORITY (Future Iterations)

6. **🤖 Advanced AI Features**
   - Multi-modal processing (text + voice + vision)
   - Context retention across sessions
   - Learning from user interactions

7. **⚡ Performance Optimization**
   - LLM response caching
   - Load balancing for multiple instances
   - Database integration for persistent state

---

## 🛠️ DEVELOPMENT CONTEXT FOR NEXT AI

### How We Work - Proven Approach

**✅ Autonomous E2E Testing:**
```bash
# Complete system validation with one command
./scripts/auto_verify.sh
# Starts services, runs eval, validates SLO, saves artifacts
```

**✅ Real Integration Testing (No Mocks):**
```bash
# We test against real services with realistic expectations
pytest src/tests/test_real_integration.py -v
# Success rate: 80-95% (not 100% perfectionism)
```

**✅ Production-Tight Development:**
```bash  
# Start the entire stack for development
docker compose up -d guardian orchestrator

# Run autonomous validation
./scripts/auto_verify.sh

# Monitor in real time  
cd monitoring && streamlit run mini_hud.py
```

**✅ Structured Development Workflow:**
1. **Plan**: Use Todo tracking for task management
2. **Implement**: Real integration from the start (no mocks)
3. **Test**: Run `./scripts/auto_verify.sh` for complete validation
4. **Monitor**: Use HUD to see impact in real time
5. **Validate**: SLO compliance via autonomous testing

### Architecture Principles to Follow

- **Safety First**: Guardian should always be first priority
- **Real Data**: Measure real metrics, not mocks or estimates
- **Production Ready**: Everything should be deployment-ready from day 1
- **Observable**: Log structured data for debugging and ML training
- **Autonomous Testing**: All features should be validated via `auto_verify.sh`
- **Swedish Focus**: Alice is optimized for Swedish users

### Code Conventions Established

- **Python Services**: FastAPI + Pydantic, structured logging with structlog
- **Testing**: pytest with realistic expectations (80-95% success rates)  
- **E2E Testing**: `scripts/auto_verify.sh` for complete validation
- **Monitoring**: JSONL for structured logging, Streamlit for dashboards
- **Docker**: Health checks, proper dependencies, environment-driven config
- **Git**: Descriptive commits with 🤖 Claude Code signature

### Files You Should Read First

1. **`README.md`** - Production deployment guide
2. **`ALICE_SYSTEM_BLUEPRINT.md`** - System architecture  
3. **`TESTING_STRATEGY.md`** - Our proven testing approach
4. **`scripts/auto_verify.sh`** - Autonomous E2E testing
5. **`services/eval/eval.py`** - Eval harness implementation
6. **`services/orchestrator/main.py`** - Current integration points
7. **`monitoring/mini_hud.py`** - Real-time system visibility

### Key Environment Setup

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

## 🔮 STRATEGIC DIRECTION

Alice v2 has moved from prototype to a **production-ready platform with complete observability and autonomous E2E testing**. The next AI agent can focus on **actual LLM integration** and **voice pipeline** while the entire safety/monitoring/test infrastructure is already robust.

**Key Success Factors:**
- Guardian safety system enables safe LLM experimentation 
- Complete observability gives immediate feedback on changes
- Autonomous E2E testing validates that new features don't break SLOs
- HUD dashboard provides visual confirmation that everything works

**Philosophy**: We're not just building an AI assistant - we're building a **robust, observable, secure platform** that can be developed iteratively without compromising quality or security, with autonomous validation of all changes.

---

**🤖 Status Updated by Claude Code - Alice v2 observability + eval-harness v1 complete! Ready for LLM integration! 🚀**

---

## ⚡ NEXT AI QUICKSTART (Dev-Proxy - No Mocks)

Quickstart for the next AI agent – everything via dev-proxy on port 18000.

### 1) Start the stack
```bash
scripts/dev_up.sh
# or
docker compose up -d guardian orchestrator nlu dashboard dev-proxy
```

### 2) Sanity via proxy
```bash
curl -s http://localhost:18000/health | jq .
curl -s http://localhost:18000/api/status/routes | jq .
```

### 3) NLU sanity (Swedish)
```bash
curl -s -X POST http://localhost:18000/api/nlu/parse \
  -H 'Content-Type: application/json' \
  -d '{"v":"1","lang":"sv","text":"Schedule meeting with Anna tomorrow at 14:00","session_id":"nlu-sanity"}' | jq .
```

### 4) E2E verify (autonomous)
```bash
./scripts/auto_verify.sh || (echo "FAIL – see data/tests/summary.json" && exit 1)
cat data/tests/summary.json | jq .
open http://localhost:18000/hud
```

### 5) NLU v1 – DoD (next step)
- `/api/nlu/parse` P95 ≤ 80 ms (5 min window)
- Intent accuracy ≥ 92% (Swedish suite)
- Slots: ISO formatting for expressions like "tomorrow 14:00"
- Orchestrator sets `X-Route-Hint` → route visible in P95 per route

---

## 🔐 Security & Enforcement (for agents)
- Orchestrator ENV: `SECURITY_ENFORCE=true`, `SECURITY_POLICY_PATH=config/security_policy.yaml`
- HUD: Security panel in `monitoring/alice_hud.py` (mode, injection suspects, tool denials)
- Metrics: `alice_injection_suspected_total`, `alice_tool_denied_total{reason=...}`, `alice_security_mode{mode=...}`
- Gate: For high risk, return an intent‑card (requires confirmation) and log turn‑event security fields
