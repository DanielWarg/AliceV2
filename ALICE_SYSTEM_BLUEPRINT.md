# Alice v2 System Blueprint & Architecture
*Complete system blueprint for Alice AI Assistant with clean architecture*

## 🎯 Overview

Alice v2 is a modular AI assistant with deterministic security control, intelligent resource management, and proactive user experience. The system combines microservices, clean architecture, and enterprise-grade observability.

**🚀 CURRENT STATUS**: Complete observability + eval-harness v1 system operational with autonomous E2E testing

> Note: For current delivery status, next steps, and live test‑gates, see `ROADMAP.md` → "🚦 Live Milestone Tracker". No milestones are checked off without a green gate via `./scripts/auto_verify.sh` and saved artifacts in `data/tests/` and `data/telemetry/`.

## 🏗️ System Architecture

```mermaid
graph TB
    User[🧑‍💻 User<br/>Swedish speech] --> ASR[ASR<br/>Whisper.cpp+VAD]
    ASR --> NLU[NLU<br/>sv-intent/slots/mood]
    NLU --> Guardian[Guardian Gate<br/>admission control<br/>RAM/CPU/temp/battery]
    
    Guardian --> Orchestrator[Orchestrator<br/>LangGraph Router + policies<br/>Router Phi-mini<br/>Policies/SLO + Tool registry MCP<br/>Event-bus & tracing<br/>RAM-peak, energy, tool error tracking]
    
    Orchestrator --> Micro[Micro-LLM<br/>simple answers<br/>Phi-3.5-Mini]
    Orchestrator --> Planner[Planner<br/>OpenAI GPT-4o-mini<br/>function-calling<br/>fallback: Local ToolSelector 3B]
    Orchestrator --> Deep[Deep Reasoning<br/>deep analysis<br/>Llama-3.1 on-dmd]
    Orchestrator --> Vision[Vision/Sensors<br/>YOLO/SAM/RTSP<br/>events→router]
    
    Micro --> Memory[Memory RAG<br/>FAISS user mem<br/>Redis TTL session]
    Planner --> Tools[Tools/APIs<br/>Mail, Calendar<br/>Home Assistant]
    Deep --> Tools
    Tools --> Memory
    
    Guardian --> GuardianDaemon[Guardian Daemon<br/>psutil/energy<br/>state machine]
    
    Memory --> TTS[TTS<br/>VITS/Piper + cache]
    TTS --> Speakers[Speakers]
    
    Orchestrator --> HUD[Dashboard/HUD<br/>events+metrics<br/>P50/P95, RAM, tool errors<br/>RAG-hit, energy]
    
    Proactivity[Proactivity<br/>Prophet/Goal Scheduler] --> Orchestrator
    Reflection[Reflection<br/>logs+metrics → suggestions<br/>cache, RAG-K, prewarm] --> Orchestrator
    
    %% Budget and cost tracking
    Cost[Cost Tracking<br/>OpenAI tokens & cost<br/>daily/weekly budget<br/>auto-switch on breach] --> Orchestrator
    
    style User fill:#e1f5fe
    style Guardian fill:#fff3e0
    style Orchestrator fill:#f3e5f5
    style Memory fill:#e8f5e8
    style Tools fill:#fff8e1
    style HUD fill:#fce4ec
    style Cost fill:#ffebee
```

## 🔧 Component Overview

### 1. **Hybrid Planner System** 🔄 IN PROGRESS
```
services/orchestrator/src/planner/
├── provider_manager.py      # OpenAI + local switching
├── openai_planner.py        # GPT-4o-mini driver
├── toolselector.py          # Local fallback (enum-only)
└── arg_builder.py           # Deterministic argument building
```

**Features:**
- **Primary**: OpenAI GPT-4o-mini with function-calling
- **Fallback**: Local ToolSelector (3B model, enum-only schema)
- **Cost Control**: Daily/weekly budget with auto-switch
- **User Opt-in**: `cloud_ok` flag for cloud processing
- **Arg Building**: Deterministic argument construction with error taxonomy

**SLO Targets:**
- OpenAI: schema_ok ≥ 99%, p95 ≤ 900ms
- Local fallback: schema_ok ≥ 95%, p95 ≤ 1200ms
- Arg building: success ≥ 95%

### 2. **Frontend Layer (Web/Mobile)** ✅ IMPLEMENTED
```typescript
apps/web/                    # Next.js frontend app
├── src/components/
│   ├── AliceHUD.tsx        # Main interface
│   ├── VoiceInterface.tsx  # Voice interaction
│   └── GuardianBanner.tsx  # System status
```

**Features:**
- Real-time WebSocket communication
- Voice interface with audio visualizer
- Guardian-aware UX (brownout feedback)
- Performance HUD and system metrics
- Responsive design for desktop/mobile

### 2. **Voice Pipeline** 🔄 IN PROGRESS
```
User ──▶ Browser Audio API ──▶ WebSocket ──▶ ASR Server
```

**Components:**
- **ASR (Whisper.cpp)**: Swedish speech-to-text
- **VAD (Voice Activity Detection)**: Intelligent audio segmentation  
- **NLU**: Intent classification with Swedish language understanding
- **TTS (Piper/VITS)**: Text-to-speech with cache

#### **TTS-Persona (Mood-Driven)**
```python
mood_score ∈ [0..1] → voice preset
0.00–0.33: empathetic_alice
0.34–0.66: neutral_alice  
0.67–1.00: happy_alice
Brownout != NONE → forced neutral_alice
```

**SLO Targets:**
- First partial: <200ms
- Final transcript: <1000ms  
- End-to-end: <2000ms

### 4. **Cost Management & Security** 🔄 IN PROGRESS
```
services/orchestrator/src/security/
├── cost_tracker.py          # OpenAI token/cost tracking
├── budget_gate.py           # Daily/weekly budget enforcement
├── n8n_security.py          # HMAC + replay protection
└── cloud_optin.py           # User opt-in management
```

**Features:**
- **Cost Tracking**: OpenAI tokens and cost per turn
- **Budget Gates**: Daily ($1) and weekly ($3) limits with auto-switch
- **n8n Security**: HMAC-SHA256 + timestamp verification
- **Replay Protection**: Guardian prevents duplicate webhook execution
- **User Opt-in**: `cloud_ok` flag with audit logging

**Security Requirements:**
- n8n webhooks require HMAC-SHA256 + timestamp
- Guardian verifies ±300s window and prevents replay
- Cost budget breach triggers automatic local fallback

### 5. **Guardian System (Resource Protection)** ✅ IMPLEMENTED
```
services/guardian/
├── src/core/
│   ├── guardian.py          # Main daemon
│   ├── brownout_manager.py  # Intelligent degradation
│   └── kill_sequence.py     # Graceful shutdown
```

**State Machine:**

```mermaid
stateDiagram-v2
    [*] --> NORMAL
    NORMAL --> BROWNOUT : 80% RAM
    BROWNOUT --> EMERGENCY : 92% RAM
    BROWNOUT --> DEGRADED : degradation
    EMERGENCY --> DEGRADED : cooldown
    DEGRADED --> NORMAL : 45s recovery
    DEGRADED --> LOCKDOWN : max kills
    LOCKDOWN --> NORMAL : 1h timeout
```

#### **Guardian Thresholds (Environment Variables)**
```bash
GUARD_RAM_SOFT=0.80
GUARD_RAM_HARD=0.92
GUARD_RECOVER_RAM=0.70
GUARD_CPU_SOFT=0.80
GUARD_TEMP_C_HARD=85
GUARD_BATTERY_PCT_HARD=25
GUARD_BROWNOUT_LEVEL=LIGHT|MODERATE|HEAVY  # auto
```

**Actions:**
- **Brownout**: Model switch (20b→7b), context reduction, tool disable
- **Emergency**: Graceful Ollama kill + restart
- **Lockdown**: Manual intervention required

### 4. **LLM Orchestrator** ✅ IMPLEMENTED WITH OBSERVABILITY
```
Micro-LLM (Phi-3.5-Mini)     # Simple answers, quick response
     │
Planner-LLM (Qwen2.5-MoE)    # Tool calls, planning  
     │
Deep Reasoning (Llama-3.1)   # Complex analysis (on-demand)
```

**Router Logic:**
- Intent classification → Model selection
- Resource awareness → Degradation handling
- SLO enforcement → Timeout/fallback

**🎯 NEW FEATURES:**
- **RAM-peak per turn**: Process and system memory tracking
- **Energy per turn (Wh)**: Energy consumption with configurable baseline
- **Tool error classification**: Timeout/5xx/429/schema/other categorization
- **Structured turn events**: Complete JSONL logging with all metrics

### 5. **Tool Integration (MCP)** 🔄 IN PROGRESS
```
packages/tools/
├── mail/           # Email integration
├── calendar/       # Calendar management  
├── home/          # Home Assistant
└── vision/        # YOLO/SAM integration
```

#### **Tool Registry + Fallback Matrix**
```json
// GET /tools/registry
{
  "v":"1",
  "tools":[
    {
      "name":"calendar.create",
      "schema":{"type":"object","properties":{"when":{"type":"string"},"with":{"type":"string"}},"required":["when","with"]},
      "latency_budget_ms":600,
      "safety_class":"user-data",
      "health":{"status":"green","p95_ms":220,"error_rate":0.01}
    }
  ]
}
```

**Fallback Matrix** (intent → primary → fallback1 → fallback2 → user-feedback):
- `GREETING`: micro → — → — → *"✔ Quick response."*
- `TIME.BOOK`: planner → email.draft → todo.create → *"Calendar locked—add a todo."*
- `COMM.EMAIL.SEND`: planner → email.draft → — → *"SMTP failed—saved as draft."*
- `INFO.SUMMARIZE (long)`: deep → planner → micro → *"Running lighter summary."*
- `VISION.DETECT`: vision → snapshot → — → *"Stream broke—showing still image."*

**Tool Registry:**
- Health monitoring per tool
- Latency classification (fast/slow/heavy)
- Automatic disable at brownout
- **Vision Pre-warm**: Orchestrator pre-warms Vision 2s for likely events

### 6. **Memory & RAG** 🔄 IN PROGRESS
```
Memory Layer:
├── FAISS Vector Store    # User memory, long-term
├── Redis TTL Cache      # Session memory, short-term  
└── Consent Manager      # Privacy-aware updates
```

#### **Consent & Memory Policy**
**Memory Scopes:**
- **Session memory**: Redis (TTL=7d, AOF on). Contains transients, contextual turns
- **User memory**: FAISS + embeddings. Requires consent scope

**Consent Scopes:**
- `memory:read` | `memory:write` | `email:metadata` | `email:full` | `calendar:read` | `calendar:write`

**User Control:**
- `POST /memory/forget {id}` → <1s deletion (embeddings + index)
- **Memory diff**: After new storage, Alice returns: *"I saved X – do you want to keep it?"*

**RAG Pipeline:**
- Embedding: sentence-transformers Swedish
- Retrieval: top_k with brownout awareness
- Re-ranking: relevance scoring

### 7. **Observability & Metrics** ✅ IMPLEMENTED
```
Metrics Collection:
├── Performance: P50/P95 latency per endpoint
├── Resource: RAM/CPU/temp/energy usage
├── Business: Tool success rate, cache hit ratio
└── User: Session duration, command frequency
```

#### **Observability & Retention Policy** ✅ COMPLETED
**Event Types:**
- `start`, `tool_call`, `cache_hit`, `rag_hit`, `degrade_on`, `degrade_off`
- `brownout_on`, `brownout_off`, `error_{net|tool|model|validate}`

**Retention:**
- Session logs: 7d
- Energy/aggregate: 30d  
- Audio_out: not persisted (only test runs)

**PII:** Mask e-mail/phone/SSN in logs

**Rate Limits:**
- 10 req/min per session
- Max 1 deep-job simultaneously

**Dashboard Components:** ✅ IMPLEMENTED
- Real-time system health
- Guardian state visualization
- Voice pipeline metrics
- Tool performance tracking
- **NEW**: RAM-peak, energy consumption, tool error classification

**🧪 Autonomous E2E Testing:** ✅ IMPLEMENTED
- `scripts/auto_verify.sh`: Complete system validation
- `services/eval/`: 20 realistic scenarios
- SLO validation with Node.js integration
- Automatic failure detection and artifact preservation

## 📦 Monorepo Structure

```
v2/
├── apps/
│   └── web/                 # Next.js frontend
├── services/  
│   ├── guardian/           # Guardian daemon (Python) ✅
│   ├── voice/             # ASR/TTS pipeline 🔄
│   ├── orchestrator/      # LLM routing ✅
│   └── eval/             # E2E testing harness ✅
├── packages/
│   ├── api/               # HTTP/WS clients
│   ├── ui/                # Design system
│   ├── types/             # Shared TypeScript types
│   └── tools/             # MCP tool implementations
├── monitoring/            # Streamlit HUD ✅
├── scripts/              # Autonomous E2E testing ✅
└── infrastructure/
    ├── docker/            # Container definitions
    └── k8s/               # Kubernetes manifests
```

## 🔧 Environment Configuration

### Hybrid Planner Environment Variables
```bash
# Provider Configuration
PLANNER_PROVIDER=openai|local          # Primary planner provider
PLANNER_ARGS_FROM_MODEL=false          # Use deterministic arg building
PLANNER_TIMEOUT_MS=1200                # Planner timeout

# OpenAI Configuration
OPENAI_API_KEY=sk-...                  # OpenAI API key
OPENAI_DAILY_BUDGET_USD=1.00          # Daily cost limit
OPENAI_WEEKLY_BUDGET_USD=3.00         # Weekly cost limit

# User Opt-in
CLOUD_OK=false                         # User opt-in for cloud processing

# n8n Security
N8N_WEBHOOK_SECRET=your-secret         # HMAC signing secret
N8N_REPLAY_WINDOW_S=300                # Replay protection window
```

## 🚀 Deployment Architecture

### Development
```bash
# Frontend
pnpm run dev                 # Next.js :3000

# Backend Services  
pnpm run guardian:start      # Guardian :8787
pnpm run voice:start         # Voice :8001
pnpm run orchestrator:start  # LLM :8002

# Autonomous E2E Testing
./scripts/auto_verify.sh     # Complete system validation
```

### Production (Docker Compose)
```yaml
services:
  alice-web:
    ports: ["3000:3000"]
    
  alice-guardian:
    ports: ["8787:8787"]
    deploy:
      resources:
        limits: { memory: 512M }
        
  alice-voice:
    ports: ["8001:8001"]  
    volumes: ["./models:/models"]
    
  alice-orchestrator:
    ports: ["8002:8002"]
    volumes: ["./ollama:/ollama"]
    
  alice-eval:
    profiles: ["eval"]
    volumes: ["./data/tests:/data/tests"]
    
  alice-dashboard:
    ports: ["8501:8501"]
    volumes: ["./data:/data"]
    profiles: ["dashboard"]
```

## 🔄 Data Flow

### 1. Voice Command Flow
```
1. User speaks → Browser captures audio
2. WebSocket → Voice service (ASR)
3. NLU → Intent classification  
4. Guardian Gate → Admission control
5. Orchestrator → Model selection
6. LLM → Response generation
7. TTS → Audio synthesis
8. WebSocket → Browser playback
```

### 2. Guardian Protection Flow
```
1. System metrics collected (1s interval)
2. Threshold evaluation (hysteresis)
3. State transition (NORMAL→BROWNOUT→EMERGENCY)
4. Brownout activation (model switch, tool disable)
5. Kill sequence (graceful Ollama shutdown)
6. Recovery monitoring (health gates)
```

### 3. Tool Integration Flow
```
1. User intent → Tool classification
2. MCP tool selection → Health check
3. Guardian approval → Resource check  
4. Tool execution → Result capture
5. Response integration → User feedback
```

### 4. **NEW: Observability Flow** ✅ IMPLEMENTED
```
1. Turn event initiated → Energy meter starts
2. RAM peak measured → Process and system memory
3. Tool calls executed → Error classification (timeout/5xx/429/schema/other)
4. Turn completed → Energy consumption calculated
5. Event logged → JSONL with all metrics and metadata
6. Dashboard updated → Real-time visualization
7. E2E validation → Autonomous testing with SLO validation
```

## 📊 Service Level Objectives (SLO)

### Voice Pipeline
- **Availability**: 99.5% uptime
- **Latency**: P95 < 2000ms end-to-end
- **Accuracy**: >90% intent classification

### Guardian System
- **Protection**: 0 system crashes from overload
- **Recovery**: <60s from emergency to normal
- **Brownout**: Gradual degradation, not total outage

### Tool Integration  
- **Fast Tools**: <500ms (weather, time)
- **Normal Tools**: <2000ms (email, calendar)
- **Heavy Tools**: <10000ms (vision, complex search)

### **NEW: Observability SLO** ✅ IMPLEMENTED
- **Metrics Collection**: <10ms overhead per turn
- **Dashboard Load**: <2s for complete HUD
- **E2E Test Success**: ≥80% pass rate for 20 scenarios
- **SLO Validation**: Automatic P95 threshold checking

## 🔒 Security & Privacy

### Guardian Protection
- **Deterministic**: No AI decisions in security loop
- **Rate Limiting**: Max 3 kills/30min
- **Hysteresis**: Anti-flapping protection
- **Lockdown**: Manual intervention on violation

### Data Privacy
- **Consent Management**: Explicit approval for memory updates
- **PII Masking**: Automatic detection and masking
- **Session Isolation**: Redis TTL for temporary data
- **Local Processing**: Sensitive data does not leave the device

## 🎯 Proactivity & Reflection

### Goal Scheduler
```python
# Example: Proactive weather warning
if morning_routine_detected() and weather_alert():
    schedule_notification("Rain expected, bring umbrella")
```

### Reflection Loop
```python
# Example: Cache optimization suggestion  
if cache_hit_rate < 0.7:
    suggest_prewarming(["weather", "calendar", "email"])
```

### Learning Pipeline
- **Prophet**: Seasonal patterns in user activity
- **Performance**: Tool latency trends
- **Usage**: Command frequency analysis
- **Optimization**: Automatic model/cache tuning

## 💡 Innovation Highlights

### 1. **Guardian-Aware UX**
- User receives human-understandable feedback during brownout
- "I'm switching to lighter mode for faster responses"
- Gradual degradation instead of system crash

### 2. **Intelligent Model Routing**  
- Micro-LLM for simple answers (quick)
- Planner-LLM for tool calls (balanced)
- Deep reasoning for complex analysis (on-demand)

### 3. **Proactive Resource Management**
- Predictive brownout activation
- Seasonal model prewarming  
- Energy-aware scheduling

### 4. **Swedish-First Design**
- Native Swedish in voice pipeline
- Cultural context in NLU
- Local privacy requirements

### 5. **NEW: Complete Observability** ✅ IMPLEMENTED
- **RAM-peak per turn**: Process and system memory tracking
- **Energy per turn (Wh)**: Energy consumption with configurable baseline
- **Tool error classification**: Timeout/5xx/429/schema/other categorization
- **Autonomous E2E testing**: Self-contained validation with 20 scenarios
- **Real-time HUD**: Streamlit dashboard with comprehensive metrics

## 🔮 Future Development

### Phase 1: Core Stability (Q1) ✅ COMPLETED
- Guardian system hardening ✅
- Voice pipeline optimization 🔄
- Basic tool integration 🔄
- **NEW**: Complete observability system ✅

### Phase 2: Intelligence (Q2)  
- Advanced NLU with emotion detection
- Proactive scheduling implementation
- Performance optimization AI

### Phase 3: Ecosystem (Q3)
- Home Assistant deep integration
- Mobile app development
- Third-party tool marketplace

### Phase 4: Enterprise (Q4)
- Kubernetes deployment
- Enterprise security features  
- Multi-tenant architecture

## ✅ Deployment Checklist

**Environment Validation:**
- [x] Guardian env for temp/battery is set and visible in `/guardian/health` ✅
- [x] MCP-registry exposed and fallback matrix is checked ✅
- [x] NLU→Orchestrator payload includes `v:"1"`, `mood_score` and `session_id` ✅
- [x] TTS response logs cache: `HIT|MISS` and HUD shows TTS P95 ✅
- [x] Memory-scopes are documented and `/memory/forget` takes <1s ✅
- [x] HUD shows red/yellow/green + P50/P95, RAM-peak, tool error classification, RAG-hit, energy ✅
- [x] **NEW**: RAM-peak per turn logged in each turn event ✅
- [x] **NEW**: Energy per turn (Wh) tracked and logged ✅
- [x] **NEW**: Tool error classification works with Prometheus metrics ✅
- [x] **NEW**: Autonomous E2E testing with 20 scenarios ✅
- [x] **NEW**: SLO validation with automatic failure detection ✅

**Contract Versioning:**
- All payloads include `"v":"1"` for future compatibility
- API endpoints support version headers
- Graceful degradation on version mismatch

---

**Alice v2 Blueprint** represents the next generation of AI assistants with a focus on security, performance, and user experience. The system combines cutting-edge AI with robust engineering for production-ready deployment.

🚀 **Ready for the future of AI assistance! Complete observability + eval-harness v1 operational!**

---

## 📋 Updated Project Plan – with improvements (baseline → next step)

### Orchestrator-core (LangGraph) + API-contract + client-SDK
- Ready when: /health, /run, /tools; structured events; web‑SDK only via API
- Improvement: Hash `system_prompt_sha256` in `/health` + per turn‑event

### Guardian (gatekeeper) + SLO‑hooks + red/yellow/green
- Ready when: RAM/CPU‑thresholds, brownout/restore, 429/503 + UI‑texts
- Improvements:
  - mTLS + allowlist + audit‑log for risk‑endpoints
  - Mapping Guardian→Security: NORMAL→NORMAL, BROWNOUT→STRICT, EMERGENCY→LOCKDOWN
  - Kill/lockdown rate‑limit ≥5 min

### Observability + eval‑harness v1
- Ready when: P50/P95, RAM‑peak, tool error classification, energy in HUD; `auto_verify` 14:00
- Improvements: Redis eviction HUD + alert; `ollama_ready_ms`, `whisper_checksum_mismatch_total`

### NLU (Swedish) – e5 + XNLI (+ regex)
- Ready when: Intent‑accuracy ≥92%, P95 ≤80 ms
- Improvements: Intent‑card UX (idempotency: intent_id, nonce, expiry); Swedish security messages in policy

### Micro‑LLM (Phi‑3.5‑Mini via Ollama)
- Ready when: <250 ms to first character (P95)
- Improvement: Warm‑slot (micro/planner resident; deep gated)

### Memory (Redis TTL + FAISS user memory)
- Ready when: RAG top‑3 hit‑rate ≥80%, P@1 ≥60%, "forget me" <1 s
- Improvements: FAISS hot/cold split (HNSW i RAM/ondisk kall); Redis eviction policy + HUD; forget <500 ms

### Planner‑LLM (Qwen‑7B‑MoE) + tool layer (MCP) v1
- Ready when: 1–2 tool‑calls/flow, tool‑success ≥95%
- Improvements: Signed manifests + schema‑validation in CI; tool‑quota (5 calls/5 min per session)

### Text E2E‑hardtest (quick + planner) against SLO
- Ready when: Quick ≤250 ms; Planner ≤900 ms / ≤1.5 s; `auto_verify` green
- Improvements: A/B framework (TTS/intent‑cards); 8–10 red‑team scenarios in enforce mode

### ASR (Whisper.cpp + Silero‑VAD)
- Ready when: WER ≤7%/≤11%; partial ≤300 ms; final ≤800 ms
- Improvement: Model‑checksum vid startup; dual‑slot fallback

### TTS (Piper/VITS) + cache + mood‑hook
- Ready when: Cached ≤120 ms; uncached ≤800 ms; 3 presets linked to mood_score
- Improvement: A/B experiment for voice variants

### Deep‑LLM (Llama‑3.1‑8B via Ollama)
- Ready when: ≤1.8 s / 3.0 s; max 1 concurrent; Guardian gate protects

### Vision (YOLOv8‑nano + SAM2‑tiny, RTSP) on‑demand
- Ready when: First‑box ≤350 ms; reconnect ≤2 s; degrade gracefully

### Guardian+UX polish / Reflection / Proactivity / UI milestones / vLLM+Flower
- Same structure as in ROADMAP, with above improvements woven into respective steps
