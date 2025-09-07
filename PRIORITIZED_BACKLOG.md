# 📋 ALICE V2 PRIORITIZED BACKLOG
*Complete priority-ordered list of unfinished work excluding Alice AI training*

**Updated**: 2025-09-07  
**Status**: Alice first training completed ✅ (95% accuracy), system stable, ready for sprint work

---

## 🎯 **CURRENT STATUS:**
- **Alice AI Training**: ✅ First LoRA training complete (95% accuracy on Swedish tool selection)
- **Night Test**: ✅ 240 episodes, 168ms average response time, system stable 
- **System Health**: ✅ 8-hour continuous operation validated
- **Next Phase**: Fix critical infrastructure issues while Alice continues self-training

---

## 🔥 **CRITICAL ISSUES (Must Fix Immediately)**

### **1. Ollama Service Health** ❌ **PRIO 1 - BLOCKING**
**Problem**: Port 11434 unhealthy, model loaded but not responding  
**Impact**: Local LLM non-functional → forced cloud fallback  
**Root Cause**: qwen2.5:3b model (1.9GB) loaded but API endpoints failing  
**Tasks**:
- [ ] Debug Ollama health check endpoint `/health`
- [ ] Test model completion: `curl -X POST http://localhost:11434/api/generate`  
- [ ] Verify qwen2.5:3b model responds to basic prompts
- [ ] Check Ollama service logs for errors
- [ ] Restart Ollama service if needed: `ollama serve`

### **2. Voice Service Restart Loop** ❌ **PRIO 2 - BLOCKING**  
**Problem**: STT/TTS pipeline continuously crashing (Port 8001)  
**Impact**: Voice interaction completely broken  
**Root Cause**: Dependency issues or resource conflicts in audio pipeline  
**Tasks**:
- [ ] Check voice service logs: `docker logs alice-voice`
- [ ] Verify audio device access permissions
- [ ] Test Whisper STT dependency loading
- [ ] Validate TTS pipeline initialization
- [ ] Implement service restart with exponential backoff
- [ ] Add voice service health endpoint

### **3. E2E Chat Flow Verification** ❌ **PRIO 3 - VALIDATION**
**Problem**: No verified end-to-end conversation flow  
**Impact**: Uncertain if complete system works as intended  
**Root Cause**: Missing comprehensive integration test  
**Tasks**:
- [ ] Test basic flow: "Hej Alice" → NLU → Orchestrator → Response
- [ ] Verify Swedish conversation handling
- [ ] Test tool calling integration end-to-end  
- [ ] Validate error handling in conversation chain
- [ ] Create automated E2E test suite for chat flow

---

## ⚡ **DEVELOPMENT ROADMAP (From README.md)**

### **4. NLU + XNLI Enhancement** 🔄 **PRIO 4**
**Goal**: Improve Swedish intent classification accuracy and performance  
**Current**: 88%+ accuracy, needs XNLI integration  
**Tasks**:
- [ ] Export XNLI to ONNX (int8) → `models/xnli/`
- [ ] Connect entailment for low confidence margins in NLU
- [ ] Add 4–6 challenging test scenarios to eval harness  
- [ ] **Target**: Intent accuracy ≥92%, P95 ≤80ms

### **5. Micro-LLM Integration** 🔄 **PRIO 5**
**Goal**: Fast response path for simple queries  
**Current**: Framework ready, needs activation  
**Tasks**:
- [ ] Enable micro-driver in `/api/chat` endpoint
- [ ] Implement `X-Route=micro` header handling for simple intents
- [ ] Configure Phi-3.5-mini model routing
- [ ] **Target**: P95 <250ms (first token)

### **6. Memory System Enhancement** 🔄 **PRIO 6**
**Goal**: Persistent conversation context and user memory  
**Current**: FAISS + Redis basic integration working  
**Tasks**:
- [ ] Implement session memory TTL=7 days
- [ ] Configure FAISS hot/cold index (HNSW+ondisk)
- [ ] Add "Forget me" functionality with <1s response time
- [ ] Test memory persistence across service restarts

### **7. Planner Production Hardening** 🔄 **PRIO 7**
**Goal**: Robust, secure, deterministic tool execution  
**Current**: Basic planner working, needs production features  
**Tasks**:
- [ ] Implement enum-only tool schema with deterministic arg-builders
- [ ] Add OpenAI rate limiting + circuit breaker + budget guard
- [ ] Implement `cloud_ok` per-session opt-in with audit logging
- [ ] Secure n8n webhooks with HMAC-SHA256 + replay-guard
- [ ] Add comprehensive tool error taxonomy
- [ ] **Target**: Tool success rate ≥95%

### **8. Performance SLO Validation** 🔄 **PRIO 8**
**Goal**: Meet production performance requirements  
**Current**: Variable performance across endpoints  
**Tasks**:
- [ ] Validate fast route: P95 ≤250ms
- [ ] Validate planner route: P95 ≤900ms (first) / ≤1.5s (full)
- [ ] Implement automated SLO monitoring in CI/CD
- [ ] Add performance regression detection

---

## 📊 **OPTIMIZATION & PERFORMANCE**

### **9. Cache Hit Rate Improvement** 🔄 **PRIO 9**
**Goal**: Dramatically improve response caching  
**Current**: ~10% hit rate (very low)  
**Target**: >40% improvement (50%+ hit rate)  
**Tasks**:
- [ ] Analyze current cache miss patterns in telemetry
- [ ] Implement semantic similarity caching with embeddings
- [ ] Add negative caching for failed requests
- [ ] Implement cache warming strategies
- [ ] Add cache performance metrics dashboard

### **10. Response Time Optimization** 🔄 **PRIO 10**
**Goal**: Consistent sub-900ms response times  
**Current**: Varies significantly per endpoint  
**Target**: P95 < 900ms across all routes  
**Tasks**:
- [ ] Profile slow endpoints with detailed timing
- [ ] Optimize NLU embedding generation (currently 70ms)
- [ ] Streamline orchestrator routing logic
- [ ] Implement request/response compression
- [ ] Add connection pooling and keep-alive optimization

---

## 🎨 **FRONTEND & USER EXPERIENCE**

### **11. Modern Web Frontend** 📋 **PRIO 11**
**Goal**: Production-ready web interface  
**Current**: Basic Streamlit HUD for monitoring  
**Target**: Modern React/Next.js application  
**Tasks**:
- [ ] Implement Next.js frontend with TypeScript
- [ ] Add mobile-responsive design
- [ ] Implement WebSocket real-time communication
- [ ] Create voice interface with audio visualizer
- [ ] Add interactive tool management interface
- [ ] Implement user authentication and sessions

### **12. Voice Pipeline Enhancement** 🔄 **PRIO 12**
**Goal**: High-quality Swedish voice interaction  
**Current**: Framework implemented but disabled for stability  
**Target**: Production-ready Swedish voice pipeline  
**Tasks**:
- [ ] Implement Swedish-optimized TTS/STT models
- [ ] Improve audio quality and noise reduction
- [ ] Add real-time voice processing capabilities
- [ ] Implement Voice Activity Detection (VAD)
- [ ] Add accent and dialect recognition
- [ ] Optimize for low-latency voice responses

---

## 🔧 **INFRASTRUCTURE & OPERATIONS**

### **13. Production Deployment** 📋 **PRIO 13**
**Goal**: Scalable, reliable production deployment  
**Current**: Docker Compose development setup  
**Target**: Enterprise-grade deployment platform  
**Tasks**:
- [ ] Convert Docker Compose to Kubernetes manifests
- [ ] Implement horizontal auto-scaling policies
- [ ] Add service mesh (Istio) for advanced networking
- [ ] Implement blue-green deployment strategy
- [ ] Add comprehensive monitoring (Grafana/Prometheus)
- [ ] Set up automated alerting and incident response

### **14. Advanced Tools Integration** 📋 **PRIO 14**
**Goal**: Rich ecosystem of integrated tools and services  
**Current**: Basic MCP registry with core tools  
**Target**: Comprehensive tool ecosystem  
**Tasks**:
- [ ] Integrate Home Assistant for smart home control
- [ ] Add Calendar integration (Google, Outlook, CalDAV)
- [ ] Implement Email integration (IMAP/SMTP, Gmail API)
- [ ] Expand n8n workflow automation with security
- [ ] Add document processing and analysis tools
- [ ] Implement secure API key management

---

## 🧠 **ADVANCED AI CAPABILITIES**

### **15. Proactivity Engine** 📋 **PRIO 15**
**Goal**: Intelligent, predictive AI assistant behavior  
**Current**: Reactive response-only system  
**Target**: Proactive assistance with goal awareness  
**Tasks**:
- [ ] Implement goal scheduler with Prophet forecasting
- [ ] Add user preference learning and adaptation
- [ ] Create contextual suggestion engine
- [ ] Implement mood-driven response adaptation
- [ ] Add behavior pattern recognition
- [ ] Create proactive notification system

### **16. Multimodal Capabilities** 📋 **PRIO 16**
**Goal**: Advanced visual and multimodal processing  
**Current**: Text and voice only  
**Target**: Full multimodal AI assistant  
**Tasks**:
- [ ] Implement vision system with YOLO/SAM integration
- [ ] Add image analysis and description capabilities
- [ ] Create document processing pipeline (OCR, PDF parsing)
- [ ] Add visual context understanding for conversations
- [ ] Implement image generation capabilities
- [ ] Create rich media response formatting

---

## 🎯 **SPRINT PLANNING**

### **Sprint 1 (1-2 weeks): CRITICAL FIXES**
**Goal**: Fix blocking issues and validate core functionality  
**Success Criteria**: All services healthy, E2E chat working  
1. ✅ Fix Ollama service health (PRIO 1)
2. ✅ Stabilize voice service (PRIO 2)  
3. ✅ Verify E2E chat flow (PRIO 3)
4. ✅ NLU XNLI enhancement (PRIO 4)

### **Sprint 2 (2-3 weeks): PERFORMANCE & CORE FEATURES**
**Goal**: Optimize performance and enhance core capabilities  
**Success Criteria**: <900ms P95, >40% cache hit, stable memory  
5. ✅ Micro-LLM integration (PRIO 5)
6. ✅ Memory system enhancement (PRIO 6)
7. ✅ Cache hit rate improvement (PRIO 9)
8. ✅ Response time optimization (PRIO 10)

### **Sprint 3 (3-4 weeks): PRODUCTION READINESS**
**Goal**: Prepare for production deployment  
**Success Criteria**: Production SLOs met, modern UI, stable voice  
9. ✅ Planner production hardening (PRIO 7)
10. ✅ Performance SLO validation (PRIO 8)
11. ✅ Modern web frontend (PRIO 11)
12. ✅ Voice pipeline enhancement (PRIO 12)

### **Sprint 4+ (1-2 months): ADVANCED FEATURES**
**Goal**: Advanced AI capabilities and ecosystem expansion  
**Success Criteria**: Production deployment, proactive features, multimodal  
13. ✅ Production deployment (PRIO 13)
14. ✅ Advanced tools integration (PRIO 14)
15. ✅ Proactivity engine (PRIO 15)
16. ✅ Multimodal capabilities (PRIO 16)

---

## 📈 **SUCCESS METRICS**

### **Current Baseline:**
- **Services**: 8/11 healthy (Alice AI training running successfully ✅)
- **NLU Accuracy**: 88%+ on Swedish queries
- **Cache Hit Rate**: ~10% (very low, needs major improvement)
- **E2E Chat**: Not verified (major risk)
- **Response Time**: Variable (needs optimization)
- **Alice Training**: 95% accuracy on tool selection ✅

### **Sprint 1 Target:**
- **Services**: 11/11 healthy (100% uptime)
- **E2E Chat**: >95% success rate on basic conversations
- **Ollama**: Fully operational local LLM
- **Voice Pipeline**: Stable, no restart loops
- **Documentation**: All systems documented and up-to-date

### **Sprint 3 Target (Production Ready):**
- **Response Time**: P95 < 900ms across all routes
- **Cache Hit Rate**: >50% (5x improvement)
- **Tool Success**: >95% reliable execution
- **Frontend**: Modern web interface deployed
- **Voice**: High-quality Swedish voice interaction
- **Deployment**: Production-ready infrastructure

---

## 🔄 **CONTINUOUS IMPROVEMENT**

### **Parallel Alice AI Development:**
While working through this backlog, Alice continues her autonomous evolution:
- **ToolSelector LoRA**: ✅ 95% accuracy achieved
- **Parallel Evolution Engine**: Running 6 components simultaneously
- **Continuous Learning**: From every interaction and telemetry event
- **Fibonacci Optimization**: Golden ratio performance tuning active

### **Weekly Review Process:**
- **Every Friday**: Update backlog priorities based on progress
- **Every Sprint**: Review success metrics and adjust timeline
- **Monthly**: Strategic review of Alice AI advancement vs infrastructure needs

---

## 💡 **KEY PRINCIPLES**

1. **Fix Blocking Issues First**: Can't build on unstable foundation
2. **Measure Everything**: Data-driven decisions on priorities
3. **Alice AI Parallel**: Don't block Alice's self-improvement
4. **Production Quality**: Every feature must meet SLO requirements
5. **Swedish Excellence**: Maintain focus on Swedish language optimization
6. **Security First**: No shortcuts on privacy and security features

---

*This backlog represents a complete prioritized development plan excluding Alice's autonomous AI training, which continues in parallel. Focus on critical fixes first, then systematic enhancement of performance and capabilities.*

**Next Action**: Start Sprint 1 with Ollama service health fix.