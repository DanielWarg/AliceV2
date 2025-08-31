# Alice v2 System Blueprint & Architecture
*Komplett systemskiss för Alice AI Assistant med clean architecture*

## 🎯 Översikt

Alice v2 är en modulär AI-assistent med deterministisk säkerhetskontroll, intelligent resurshantering och proaktiv användarupplevelse. Systemet kombinerar mikroservices, clean architecture och enterprise-grade observability.

**🚀 CURRENT STATUS**: Complete observability + eval-harness v1 system operational with autonomous E2E testing

## 🏗️ Systemarkitektur

```
+--------------------------------------------------------------------------------------------------------------+
|  🧑‍💻 Användare (svenskt tal) ──WS──▶ ASR (Whisper.cpp+VAD) ──▶ NLU (sv-intent/slots/mood)                   |
|                                                                                                              |
|                              (JSON)                                                                          |
|                                     ┌──────────── Guardian Gate (admission control) ───────────┐             |
|                                     │     (RAM/CPU/temp/batteri → Brownout/Degrade)            │             |
|                                     └───────────────────────▲───────────────────────────────────┘             |
|                                                             │ (status/pubsub)                                |
|  ◀── AR/HUD & status ── WebSocket events ───────────────────┼───────────────────────────────────────────────▶ |
|                                                                                                              |
|                             Orkestrator (LangGraph Router + policies)                                        |
|                         ┌─────────────────────────────────────────────────────┐                              |
|                         │ - Router (Phi-mini)                                │                              |
|                         │ - Policies/SLO + Tool registry (MCP)               │                              |
|                         │ - Event-bus & tracing                              │                              |
|                         │ - RAM-peak, energy, tool error tracking            │                              |
|                         └───────────────┬───────────────┬────────────────────┘                              |
|                                         │               │                                                     |
|                ┌────────────────────────┘               └───────────────────────────┐                       |
|                v                                                                    v                       |
|      +-----------------+        +------------------+        +--------------------+        +-----------------+
|      | Micro-LLM       |        | Planner-LLM      |        | Deep Resonemang    |        | Vision/Sensorer |
|      | (enkla svar)    |        | (planering+tools)|        | (djup analys)      |        | (YOLO/SAM/RTSP) |
|      | Phi-3.5-Mini    |        | Qwen2.5-MoE      |        | Llama-3.1 (on-dmd) |        | events→router   |
|      +--------┬--------+        +---------┬--------+        +---------┬----------+        +---------┬-------+
|               │                         ┌─┴───────────────────────────┘                           │        |
|               │  (read)                 │ (tool calls, plans)                                      │        |
|     +---------▼----------+     +--------▼---------+                                      +---------▼-------+
|     | Minne (RAG)        |     | Verktyg/APIs     |                                      | Guardian Daemon |
|     | FAISS (user mem)   |◀──▶ | (Mail, Kalender, | ◀── health/latency class (MCP)       | psutil/energy   |
|     | Redis TTL (session)|     |  Home Assistant) |                                      | state machine   |
|     +---------┬----------+     +------------------+                                      +---------▲-------+
|               │   (write/update, consent)                                                        │ status   |
|               └───────────────────────────────────────────────────────────────────────────────────┘         |
|                                                                                                              |
|  Textsvar (eng) ─▶ TTS (VITS/Piper + cache) ─▶ Högtalare                                                     |
|                       │                                                                                      |
|  Dashboard/HUD ◀──────┼── events+metrics (P50/P95, RAM, tool-fel, RAG-hit, energi)                           |
|                       │                                                                                      |
|  Proaktivitet: Prophet/Goal Scheduler ──▶ Orkestrator (idle triggers, prewarm/defer)                         |
|  Reflektion: logg+metrics ──▶ förslag (cache, RAG-K, prewarm) ─▶ Orkestrator (explicit accept)               |
+--------------------------------------------------------------------------------------------------------------+
```

## 🔧 Komponentöversikt

### 1. **Frontend Layer (Web/Mobile)** ✅ IMPLEMENTED
```typescript
apps/web/                    # Next.js frontend app
├── src/components/
│   ├── AliceHUD.tsx        # Huvudgränssnitt
│   ├── VoiceInterface.tsx  # Röstinteraktion
│   └── GuardianBanner.tsx  # System status
```

**Funktioner:**
- Real-time WebSocket kommunikation
- Voice interface med audio visualizer
- Guardian-aware UX (brownout feedback)
- Performance HUD och system metrics
- Responsive design för desktop/mobil

### 2. **Voice Pipeline** 🔄 IN PROGRESS
```
Användare ──▶ Browser Audio API ──▶ WebSocket ──▶ ASR Server
```

**Komponenter:**
- **ASR (Whisper.cpp)**: Svensk speech-to-text
- **VAD (Voice Activity Detection)**: Intelligent audio segmentering  
- **NLU**: Intent classification med svensk språkförståelse
- **TTS (Piper/VITS)**: Text-to-speech med cache

#### **TTS-Persona (Mood-Driven)**
```python
mood_score ∈ [0..1] → voice preset
0.00–0.33: empatisk_alice
0.34–0.66: neutral_alice  
0.67–1.00: glad_alice
Brownout != NONE → forcerad neutral_alice
```

**SLO Targets:**
- First partial: <200ms
- Final transcript: <1000ms  
- End-to-end: <2000ms

### 3. **Guardian System (Säkerhet)** ✅ IMPLEMENTED
```
services/guardian/
├── src/core/
│   ├── guardian.py          # Main daemon
│   ├── brownout_manager.py  # Intelligent degradation
│   └── kill_sequence.py     # Graceful shutdown
```

**Tillståndsmaskin:**
```
NORMAL ──80% RAM──▶ BROWNOUT ──92% RAM──▶ EMERGENCY
  ▲                    │                     │
  │ 45s recovery        ▼ degradation        │
  └─────────────── DEGRADED ◄────cooldown────┘
                      │
                      ▼ max kills
                  LOCKDOWN (1h)
```

#### **Guardian Trösklar (Environment Variables)**
```bash
GUARD_RAM_SOFT=0.80
GUARD_RAM_HARD=0.92
GUARD_RECOVER_RAM=0.70
GUARD_CPU_SOFT=0.80
GUARD_TEMP_C_HARD=85
GUARD_BATTERY_PCT_HARD=25
GUARD_BROWNOUT_LEVEL=LIGHT|MODERATE|HEAVY  # auto
```

**Åtgärder:**
- **Brownout**: Model switch (20b→7b), context reduction, tool disable
- **Emergency**: Graceful Ollama kill + restart
- **Lockdown**: Manual intervention required

### 4. **LLM Orchestrator** ✅ IMPLEMENTED WITH OBSERVABILITY
```
Micro-LLM (Phi-3.5-Mini)     # Enkla svar, snabb respons
     │
Planner-LLM (Qwen2.5-MoE)    # Tool calls, planering  
     │
Deep Reasoning (Llama-3.1)   # Komplex analys (on-demand)
```

**Router Logic:**
- Intent classification → Model selection
- Resource awareness → Degradation handling
- SLO enforcement → Timeout/fallback

**🎯 NEW FEATURES:**
- **RAM-peak per turn**: Process och system memory tracking
- **Energy per turn (Wh)**: Energikonsumtion med konfigurerbar baseline
- **Tool error classification**: Timeout/5xx/429/schema/other kategorisering
- **Structured turn events**: Komplett JSONL logging med alla metrics

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

**Fallback Matrix** (intent → primär → fallback1 → fallback2 → user-feedback):
- `GREETING`: micro → — → — → *"✔ Snabbt svar."*
- `TIME.BOOK`: planner → email.draft → todo.create → *"Kalender låst—la till en todo."*
- `COMM.EMAIL.SEND`: planner → email.draft → — → *"SMTP segt—sparade som utkast."*
- `INFO.SUMMARIZE (lång)`: deep → planner → micro → *"Kör lättare sammanfattning."*
- `VISION.DETECT`: vision → snapshot → — → *"Ström bröt—visar stillbild."*

**Tool Registry:**
- Health monitoring per tool
- Latency classification (fast/slow/heavy)
- Automatic disable vid brownout
- **Vision Pre-warm**: Orkestrator förvärmer Vision 2s inför sannolika events

### 6. **Memory & RAG** 🔄 IN PROGRESS
```
Memory Layer:
├── FAISS Vector Store    # User memory, långsiktig
├── Redis TTL Cache      # Session memory, kortsiktig  
└── Consent Manager      # Privacy-aware updates
```

#### **Consent & Memory Policy**
**Memory Scopes:**
- **Session memory**: Redis (TTL=7d, AOF on). Innehåller transients, contextual turns
- **User memory**: FAISS + embeddings. Kräver consent scope

**Consent Scopes:**
- `memory:read` | `memory:write` | `email:metadata` | `email:full` | `calendar:read` | `calendar:write`

**User Control:**
- `POST /memory/forget {id}` → <1s radering (embeddings + index)
- **Memory diff**: Efter ny lagring returnerar Alice: *"Jag sparade X – vill du behålla det?"*

**RAG Pipeline:**
- Embedding: sentence-transformers svenska
- Retrieval: top_k med brownout awareness
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
**Eventtyper:**
- `start`, `tool_call`, `cache_hit`, `rag_hit`, `degrade_on`, `degrade_off`
- `brownout_on`, `brownout_off`, `error_{net|tool|model|validate}`

**Retention:**
- Session-loggar: 7d
- Energi/aggregat: 30d  
- Audio_out: ej persisterad (endast testkörningar)

**PII:** Maska e-post/telefon/personnummer i loggar

**Rate Limits:**
- 10 req/min per session
- Max 1 deep-jobb samtidigt

**Dashboard Components:** ✅ IMPLEMENTED
- Real-time system health
- Guardian state visualization
- Voice pipeline metrics
- Tool performance tracking
- **NEW**: RAM-peak, energy consumption, tool error classification

**🧪 Autonomous E2E Testing:** ✅ IMPLEMENTED
- `scripts/auto_verify.sh`: Komplett systemvalidering
- `services/eval/`: 20 realistiska scenarier
- SLO validation med Node.js integration
- Automatic failure detection och artifact preservation

## 📦 Monorepo Struktur

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
- **Protection**: 0 system crashes från överbelastning
- **Recovery**: <60s från emergency till normal
- **Brownout**: Gradvis degradation, inte total avbrott

### Tool Integration  
- **Fast Tools**: <500ms (weather, time)
- **Normal Tools**: <2000ms (email, calendar)
- **Heavy Tools**: <10000ms (vision, complex search)

### **NEW: Observability SLO** ✅ IMPLEMENTED
- **Metrics Collection**: <10ms overhead per turn
- **Dashboard Load**: <2s för komplett HUD
- **E2E Test Success**: ≥80% pass rate för 20 scenarier
- **SLO Validation**: Automatic P95 threshold checking

## 🔒 Säkerhet & Privacy

### Guardian Protection
- **Deterministisk**: Inga AI-beslut i säkerhetsloopen
- **Rate Limiting**: Max 3 kills/30min
- **Hysteresis**: Anti-flapping protection
- **Lockdown**: Manual intervention vid överträdelse

### Data Privacy
- **Consent Management**: Explicit approval för minnesuppdateringar
- **PII Masking**: Automatic detection och maskering
- **Session Isolation**: Redis TTL för temporär data
- **Local Processing**: Känslig data lämnar inte enheten

## 🎯 Proaktivitet & Reflektion

### Goal Scheduler
```python
# Exempel: Proaktiv vädervarning
if morning_routine_detected() and weather_alert():
    schedule_notification("Rain expected, bring umbrella")
```

### Reflection Loop
```python
# Exempel: Cache optimization förslag  
if cache_hit_rate < 0.7:
    suggest_prewarming(["weather", "calendar", "email"])
```

### Learning Pipeline
- **Prophet**: Seasonal patterns i användaraktivitet
- **Performance**: Tool latency trends
- **Usage**: Command frequency analysis
- **Optimization**: Automatic model/cache tuning

## 💡 Innovation Highlights

### 1. **Guardian-Aware UX**
- Användaren får mänskligt begriplig feedback vid brownout
- "I'm switching to lighter mode for faster responses"
- Gradvis degradation istället för systemkrasch

### 2. **Intelligent Model Routing**  
- Micro-LLM för enkla svar (snabb)
- Planner-LLM för tool calls (balanserad)
- Deep reasoning för komplex analys (on-demand)

### 3. **Proactive Resource Management**
- Predictive brownout activation
- Seasonal model prewarming  
- Energy-aware scheduling

### 4. **Swedish-First Design**
- Native svenska i voice pipeline
- Cultural context i NLU
- Local privacy requirements

### 5. **NEW: Complete Observability** ✅ IMPLEMENTED
- **RAM-peak per turn**: Process och system memory tracking
- **Energy per turn (Wh)**: Energikonsumtion med konfigurerbar baseline
- **Tool error classification**: Timeout/5xx/429/schema/other kategorisering
- **Autonomous E2E testing**: Self-contained validation med 20 scenarier
- **Real-time HUD**: Streamlit dashboard med comprehensive metrics

## 🔮 Framtida Utveckling

### Phase 1: Core Stability (Q1) ✅ COMPLETED
- Guardian system hardening ✅
- Voice pipeline optimization 🔄
- Basic tool integration 🔄
- **NEW**: Complete observability system ✅

### Phase 2: Intelligence (Q2)  
- Advanced NLU med emotion detection
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

## ✅ Deployment Checklista

**Miljövalidering:**
- [x] Guardian env för temp/batteri är satta och syns i `/guardian/health` ✅
- [x] MCP-registry exponeras och fallback-matrisen är incheckad ✅
- [x] NLU→Orkestrator-payload innehåller `v:"1"`, `mood_score` och `session_id` ✅
- [x] TTS svar loggar cache: `HIT|MISS` och HUD visar TTS P95 ✅
- [x] Memory-scopes är dokumenterade och `/memory/forget` tar <1s ✅
- [x] HUD visar red/yellow/green + P50/P95, RAM-peak, tool-felklass, RAG-hit, energi ✅
- [x] **NEW**: RAM-peak per turn loggas i varje turn event ✅
- [x] **NEW**: Energy per turn (Wh) spåras och loggas ✅
- [x] **NEW**: Tool error classification fungerar med Prometheus metrics ✅
- [x] **NEW**: Autonomous E2E testing med 20 scenarier ✅
- [x] **NEW**: SLO validation med automatic failure detection ✅

**Kontrakts-versionering:**
- Alla payloads innehåller `"v":"1"` för framtida kompatibilitet
- API endpoints stödjer version headers
- Graceful degradation vid version mismatch

---

**Alice v2 Blueprint** representerar nästa generation AI-assistenter med fokus på säkerhet, prestanda och användarupplevelse. Systemet kombinerar cutting-edge AI med robust engineering för produktion-redo deployment.

🚀 **Ready for the future of AI assistance! Complete observability + eval-harness v1 operational!**