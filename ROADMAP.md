# Alice v2 Development Roadmap
*Professionell implementationsplan med mätbara milstolpar*

## 🎯 Övergripande Strategi

**Filosofi**: Dependency-driven development med tidiga säkerhetsnät och kontinuerlig mätning.

**Timeline**: 16 steg över 6-8 veckor med parallell utveckling i senare faser.

**🚀 CURRENT STATUS**: Phase 1 Steps 1-3 COMPLETED - Foundation & Safety system operational

---

## Phase 1: Foundation & Safety (Vecka 1-2) ✅ COMPLETED

### Step 1: Orchestrator Core (LangGraph) + API-kontrakt + klient-SDK ✅ DONE
**Varför**: Allt annat pluggar in här. Utan stabila kontrakt blir resten spagetti.

**Owner**: Backend Lead  
**Timeline**: 3-4 dagar  
**SLO Targets**:
- API response time P95 <100ms
- Contract stability 100%
- SDK type safety 100%

**Definition of Done**:
- [x] `/health`, `/run`, `/tools` endpoints fungerar
- [x] Events/loggar standardiserade (structured JSON)
- [x] Web-SDK pratar endast via detta (no direct service calls)
- [x] OpenAPI spec genererad och versionerad
- [x] Integration tests för alla endpoints

**Checklist**:
- [x] FastAPI server med auto-documentation
- [x] LangGraph router stub (returnerar "micro" always)
- [x] TypeScript SDK med Zod validation  
- [x] Structured logging med trace IDs
- [x] Health check med dependency status

---

### Step 2: Guardian (gatekeeper) + SLO-hooks + röd/gul/grön status ✅ DONE
**Varför**: Tidiga skyddsnät → sparar dig timmar av felsökning när moduler läggs på.

**Owner**: DevOps/Reliability  
**Timeline**: 2-3 dagar  
**SLO Targets**:
- State transition time <150ms
- Protection activation P99 <200ms
- Zero system crashes from overload

**Definition of Done**:
- [x] RAM/CPU-trösklar implementerade (80%/92%/70%)
- [x] Brownout/restore state machine fungerar
- [x] 429/503 responses med retry-after headers
- [x] Mänskliga UI-meddelanden definierade
- [x] Dashboard visar röd/gul/grön status

**Checklist**:
- [x] psutil system monitoring (1s interval)
- [x] State machine med hysteresis
- [x] Admission control middleware
- [x] Guardian API client i orchestrator
- [x] Frontend status component

---

### Step 3: Observability (metrics/logg/trace) + eval-harness v1 ✅ DONE
**Varför**: Du vill mäta innan du optimerar.

**Owner**: Platform Team  
**Timeline**: 2-3 dagar  
**SLO Targets**:
- Metrics collection latency <10ms
- Log ingestion 99.9% success rate
- Dashboard load time <2s

**Definition of Done**:
- [x] P50/P95 latency mätning per endpoint
- [x] RAM-peak, tool-felklass, energi loggas
- [x] Dashboard visar real-time metrics
- [x] Trace correlation fungerar mellan services
- [x] Eval-harness baseline tests kör

**Checklist**:
- [x] Prometheus metrics export
- [x] Structured JSON logging med correlation IDs
- [x] Streamlit dashboard med live graphs
- [x] Performance baseline tests
- [x] SLO alerting rules

**🎯 NEW FEATURES COMPLETED**:
- [x] **RAM-peak per turn**: Process och system memory tracking
- [x] **Energy per turn (Wh)**: Energikonsumtion med konfigurerbar baseline
- [x] **Tool error classification**: Timeout/5xx/429/schema/other kategorisering
- [x] **Autonomous E2E testing**: `scripts/auto_verify.sh` med 20 scenarier (micro/planner v1)
- [x] **SLO validation**: Automatisk P95 threshold checking med Node.js
- [x] **Real-time HUD**: Streamlit dashboard med comprehensive metrics

### Step 4: NLU v1 (svenska) – e5 + regex (✅ BASELINE LIVE)
- [x] `/api/nlu/parse` aktiv, P95 <80ms (CPU)
- [x] Orchestrator `/api/chat` sätter `X-Intent`/`X-Route-Hint` + `X-Route`
- [x] 20 scenarier i eval (micro/planner); pass-rate ≥80% (nu 100%)
- [ ] XNLI ONNX entailment vid låg marginal (nästa på tur)

---

## Phase 2: Language Understanding (Vecka 2-3) 🔄 IN PROGRESS

### Step 4: NLU (svenska) – multilingual-e5-small + xlm-roberta-xnli + regex (IN PROGRESS)
**Varför**: Intent/slots styr alla flöden.

**Owner**: ML Team  
**Timeline**: 4-5 dagar  
**SLO Targets**:
- Intent accuracy ≥92% på testsvit
- Latency P95 ≤80ms
- Memory usage <500MB

**Definition of Done**:
- [ ] Svenska intent classification fungerar (≥92%)
- [ ] Slot extraction för datum/tid/personer (ISO-normaliserat)
- [ ] Confidence scores kalibrerade, env-styrda thresholds
- [ ] Fallback till regelbaserad parsing
- [ ] Evaluation harness med svenska test cases

**Checklist**:
- [ ] multilingual-e5-small för embeddings
- [ ] xlm-roberta-xnli för intent classification
- [ ] Regex patterns för svenska datetime/entities
- [ ] Confidence threshold tuning
- [ ] 100 svenska test utterances

---

### Step 5: Micro-LLM (Phi-3.5-Mini via Ollama) – "snabbvägen"
**Varför**: Få end-to-end text→text svar ultrasnabbt.

**Owner**: AI/LLM Team  
**Timeline**: 2-3 dagar  
**SLO Targets**:
- Time to first token P95 <250ms
- Context window 4K tokens
- Memory usage <2GB

**Definition of Done**:
- [ ] Phi-3.5-Mini modell integrerad via Ollama
- [ ] Svenska prompt engineering optimerad
- [ ] Streaming responses implementerat
- [ ] Context management fungerar
- [ ] Guardian integration (brownout → model switch)

**Checklist**:
- [ ] Ollama server setup och health checks
- [ ] Streaming response handling
- [ ] Svenska prompt templates
- [ ] Context window management
- [ ] Brownout fallback logic

---

### Step 6: Minne (Redis TTL session + FAISS user memory)
**Varför**: Personalisering och kontext utan att spränga RAM.

**Owner**: Backend Team  
**Timeline**: 3-4 dagar  
**SLO Targets**:
- RAG top-3 hit-rate ≥80%
- Precision@1 ≥60%
- "Forget me" operation <1s

**Definition of Done**:
- [ ] Redis session storage med TTL (7 dagar)
- [ ] FAISS user memory med svenska embeddings
- [ ] Consent management för memory operations
- [ ] RAG retrieval med re-ranking
- [ ] Memory cleanup/forgetting funktioner

**Checklist**:
- [ ] Redis clustering för HA
- [ ] FAISS index management
- [ ] Swedish sentence-transformers
- [ ] Consent policy enforcement
- [ ] Memory analytics dashboard

---

## Phase 3: Advanced Reasoning (Vecka 3-4)

### Step 7: Planner-LLM (Qwen2.5-7B-MoE) + verktygslager (MCP) v1
**Varför**: Multisteg/verktyg gör Alice nyttig på riktigt.

**Owner**: AI/Integration Team  
**Timeline**: 5-6 dagar  
**SLO Targets**:
- Tool success rate ≥95%
- Planning latency P95 <2s
- Max 3 tools per conversation turn

**Definition of Done**:
- [ ] Qwen2.5-7B-MoE model deployment
- [ ] MCP tool registry implementerat
- [ ] 1-2 tool-calls per flow validerat
- [ ] Schema-validerat tool execution
- [ ] Tool fallback matrix implementerat

**Checklist**:
- [ ] Tool registry med health monitoring
- [ ] Email/calendar/weather tool implementations  
- [ ] Tool call planning och execution
- [ ] Error handling och retries
- [ ] Tool analytics och monitoring

---

### Step 8: Text E2E-hårdtest (snabb + planner) mot SLO
**Varför**: Lås kvalitet innan röst/vision.

**Owner**: QA/Test Team  
**Timeline**: 2-3 dagar  
**SLO Targets**:
- Snabb route P95 ≤250ms first token
- Planner route P95 ≤900ms first token / ≤1.5s full response
- Success rate ≥98% för test scenarios

**Definition of Done**:
- [x] Comprehensive E2E test suite (✅ COMPLETED)
- [x] Load testing för concurrent users (✅ COMPLETED)
- [x] SLO monitoring och alerting (✅ COMPLETED)
- [x] Performance regression testing (✅ COMPLETED)
- [ ] User acceptance criteria validated

**Checklist**:
- [x] 20+ E2E test scenarios (✅ COMPLETED)
- [x] Load testing med brownout validation (✅ COMPLETED)
- [x] Performance monitoring dashboard (✅ COMPLETED)
- [x] SLO breach alerting (✅ COMPLETED)
- [x] Test automation i CI/CD (✅ COMPLETED)

---

## Phase 4: Voice Pipeline (Vecka 4-5)

### Step 9: ASR (Whisper.cpp streaming + Silero-VAD)
**Varför**: Lägg på röst in när textkedjan håller.

**Owner**: Voice Team  
**Timeline**: 4-5 dagar  
**SLO Targets**:
- WER ≤7% rent audio / ≤11% background noise
- Partial transcription ≤300ms
- Final transcription ≤800ms efter silence

**Definition of Done**:
- [ ] Whisper.cpp streaming integration
- [ ] Silero-VAD för voice activity detection
- [ ] WebSocket audio streaming (20ms chunks)
- [ ] Svenska language model optimering
- [ ] Real-time partial transcript delivery

**Checklist**:
- [ ] Whisper.cpp compilation och integration
- [ ] WebSocket server för audio streaming
- [ ] VAD threshold tuning för svenska
- [ ] Audio format conversion (PCM 16kHz)
- [ ] Streaming transcript protocols

---

### Step 10: TTS (Piper/VITS) + cache + mood-hook
**Varför**: Slut på röstkedjan, med persona-känsla.

**Owner**: Voice Team  
**Timeline**: 3-4 dagar  
**SLO Targets**:
- Cached response ≤120ms
- Uncached response ≤800ms (≤40 characters)
- 3 voice presets operational

**Definition of Done**:
- [ ] Piper/VITS svenska voices integrerade
- [ ] Audio caching system implementerat
- [ ] Mood-driven voice selection (neutral/glad/empatisk)
- [ ] Audio streaming till frontend
- [ ] Voice quality metrics tracking

**Checklist**:
- [ ] Svenska voice models (3 personas)
- [ ] Redis audio cache med TTL
- [ ] Mood score → voice mapping
- [ ] Audio format optimization
- [ ] Voice synthesis monitoring

---

## Phase 5: Deep Reasoning (Vecka 5-6)

### Step 11: Deep-LLM (Llama-3.1-8B via Ollama)
**Varför**: Aktivera "djup" reasoning först när Guardian och SLO skyddar.

**Owner**: AI Team  
**Timeline**: 3-4 dagar  
**SLO Targets**:
- Time to first token P95 ≤1.8s
- Full response P95 ≤3.0s
- Max 1 concurrent deep job

**Definition of Done**:
- [ ] Llama-3.1-8B deployment och tuning
- [ ] Deep reasoning query classification
- [ ] Resource isolation (1 job limit)
- [ ] Guardian integration för memory protection
- [ ] Quality benchmarking vs simpler models

**Checklist**:
- [ ] Model deployment med resource limits
- [ ] Deep vs shallow routing logic
- [ ] Concurrent job management
- [ ] Memory usage monitoring
- [ ] Response quality evaluation

---

### Step 12: Vision (YOLOv8-nano + SAM2-tiny, RTSP) on-demand
**Varför**: Multimodal "wow" utan att störa basen.

**Owner**: Vision Team  
**Timeline**: 4-5 dagar  
**SLO Targets**:
- First detection ≤350ms stillbild
- Stream reconnect ≤2s
- Graceful degradation vid connection loss

**Definition of Done**:
- [ ] YOLOv8-nano object detection
- [ ] SAM2-tiny segmentation
- [ ] RTSP stream handling
- [ ] On-demand activation (ej continuous)
- [ ] Vision results integration i chat

**Checklist**:
- [ ] Vision model deployment
- [ ] RTSP client implementation
- [ ] Object detection pipeline
- [ ] Vision-to-text descriptions
- [ ] Vision analytics dashboard

---

## Phase 6: UX Polish & Intelligence (Vecka 6-7)

### Step 13: Guardian+UX polish (mänskliga degraderingsbudskap)
**Varför**: Användarupplevelse vid tryck är avgörande.

**Owner**: Frontend/UX Team  
**Timeline**: 2-3 dagar  
**SLO Targets**:
- State transition feedback ≤200ms
- User comprehension ≥90% för messages
- Zero confusion during brownouts

**Definition of Done**:
- [ ] Mänskliga degradation messages på svenska
- [ ] UI feature gating vid brownout states
- [ ] Smooth transitions mellan normal/degraded modes
- [ ] User education om system states
- [ ] Guardian status accessibility

**Checklist**:
- [ ] Svenska brownout messages
- [ ] Feature disable/enable animations
- [ ] Guardian state explanations
- [ ] User feedback collection
- [ ] Accessibility compliance

---

### Step 14: Reflektion (auto-critique) – actionables med explicit accept
**Varför**: Självlärning utan "silent drift".

**Owner**: AI/ML Team  
**Timeline**: 3-4 dagar  
**SLO Targets**:
- Suggestion generation latency ≤500ms
- User acceptance rate ≥30% för suggestions
- Zero unauthorized system changes

**Definition of Done**:
- [ ] Automated performance analysis
- [ ] Concrete optimization suggestions (cache, prewarm, RAG-K)
- [ ] Explicit user acceptance required
- [ ] Suggestion tracking och outcome measurement
- [ ] Learning från accepted/rejected suggestions

**Checklist**:
- [ ] Performance analysis automation
- [ ] Suggestion generation algorithms
- [ ] User acceptance UI
- [ ] Suggestion effectiveness tracking
- [ ] Learning loop implementation

---

### Step 15: Proaktivitet (Prophet/goals) + energimedveten schemaläggning
**Varför**: Gör Alice proaktiv och snäll mot batteri/termik.

**Owner**: AI/Platform Team  
**Timeline**: 4-5 dagar  
**SLO Targets**:
- Proactive suggestion accuracy ≥40%
- Energy consumption reduction 15%
- Heavy job scheduling efficiency +25%

**Definition of Done**:
- [ ] Prophet seasonal pattern learning
- [ ] Goal-based proactive suggestions
- [ ] Battery/temperature aware job scheduling
- [ ] Idle time optimization
- [ ] User schedule learning

**Checklist**:
- [ ] Prophet time series forecasting
- [ ] User activity pattern analysis
- [ ] Energy-aware job scheduler
- [ ] Proactive notification system
- [ ] Scheduling effectiveness metrics

---

### Step 16: UI-milstolpar (HUD→Chat/Tools→Vision/Guardian) via SDK
**Varför**: Flytta frontend stegvis utan att bryta kontrakt.

**Owner**: Frontend Team  
**Timeline**: 3-4 dagar per milstolpe  
**SLO Targets**:
- Lighthouse score ≥90
- Playwright tests 100% pass rate
- SLO compliance 99.9%

**Definition of Done**:
- [x] HUD: Status dashboard med real-time metrics (✅ COMPLETED)
- [ ] Chat/Tools: Conversational interface med tool integration
- [ ] Vision: Multimodal interface med image/video
- [ ] Guardian: System health visualization
- [ ] SDK: All interactions via TypeScript SDK

**Checklist**:
- [x] Component library consistency (✅ COMPLETED)
- [x] Real-time data binding (✅ COMPLETED)
- [ ] Tool interaction UI
- [ ] Vision result display
- [x] Guardian status visualization (✅ COMPLETED)

---

## Phase 7: Scale & Advanced Features (Vecka 7-8)

### Step 17: vLLM (endast om throughput behövs) + Flower (för fler noder)
**Varför**: Skala först när du bevisat behovet.

**Owner**: Infrastructure Team  
**Timeline**: 5-6 dagar  
**SLO Targets**:
- Tokens/second increase 3x
- Multi-node deployment success
- Zero RAM/SLO regression

**Definition of Done**:
- [ ] vLLM deployment och benchmarking
- [ ] Flower federated learning setup (if needed)
- [ ] Multi-node orchestration
- [ ] Performance comparison vs Ollama
- [ ] Scaling decision framework

**Checklist**:
- [ ] vLLM server deployment
- [ ] Load balancing configuration
- [ ] Performance benchmarking
- [ ] Resource scaling policies
- [ ] Cost analysis för scaling options

---

## 📊 Success Metrics Dashboard

### Technical SLOs
| Metric | Target | Current | Status |
|--------|--------|---------|--------|
| Guardian Response Time | <150ms | ✅ | 🟢 |
| API Response Time P95 | <100ms | ✅ | 🟢 |
| Metrics Collection Latency | <10ms | ✅ | 🟢 |
| Dashboard Load Time | <2s | ✅ | 🟢 |
| E2E Test Success Rate | ≥80% | 30% | 🟡 |
| Voice E2E Latency (P95) | <2000ms | - | 🔴 |
| Intent Accuracy | ≥92% | - | 🔴 |
| Tool Success Rate | ≥95% | - | 🔴 |
| System Availability | ≥99.5% | ✅ | 🟢 |

### Business Metrics
| Metric | Target | Current | Status |
|--------|--------|---------|--------|
| User Task Completion | ≥85% | - | 🔴 |
| Voice Command Accuracy | ≥90% | - | 🔴 |
| User Satisfaction | ≥4.2/5 | - | 🔴 |
| System Uptime | ≥99% | ✅ | 🟢 |

---

## 🎯 Checkpoint Reviews

### Weekly Reviews
- **Måndag**: Sprint planning och priority review
- **Onsdag**: Mid-week progress check och blockers
- **Fredag**: Demo och retrospective

### Milestone Gates
- **Phase 1**: Foundation stability gate ✅ COMPLETED
- **Phase 2**: Language understanding gate 🔄 IN PROGRESS
- **Phase 3**: Text E2E performance gate
- **Phase 4**: Voice pipeline quality gate
- **Phase 5**: Advanced features integration gate
- **Phase 6**: User experience validation gate

---

## 🚀 **NEXT IMMEDIATE PRIORITIES**

### **HIGH PRIORITY (Ready for Next AI Agent)**

1. **🔌 Real LLM Integration** 
   - **Current**: Orchestrator returnerar mock responses
   - **Next**: Integrera faktiska LLM calls (OpenAI, Anthropic, lokala modeller)
   - **Location**: `services/orchestrator/src/routers/orchestrator.py`
   - **Validation**: Använd `./scripts/auto_verify.sh` för att validera integration

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

---

**Alice v2 Roadmap - Professional Implementation Plan 🚀**

*This roadmap represents a disciplined, measurable approach to building production-grade AI assistance. Phase 1 COMPLETED with comprehensive observability and autonomous E2E testing.*