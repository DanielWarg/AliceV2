# 🔗 Alice v2 System Integration Guide
*How All Enterprise Components Connect and Communicate*

## 🎯 Overview

Alice v2 är **inte en samling av separata services** - det är en **integrerad, självförbättrande AI-ecosystem** där varje komponent kommunicerar med och förbättrar de andra. Detta dokument visar hur alla T1-T9 system hänger ihop.

---

## 🏗️ Complete System Architecture

```
                     ┌─────────────────────────────────────────────────────────┐
                     │                    FRONTEND LAYER                       │
                     │  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐  │
                     │  │    Web UI   │    │    Voice    │    │   Mobile    │  │
                     │  │ (React/WS)  │    │   (8001)    │    │    App      │  │
                     │  └─────────────┘    └─────────────┘    └─────────────┘  │
                     └─────────────────────────┬───────────────────────────────┘
                                               │
                     ┌─────────────────────────┼───────────────────────────────┐
                     │                ORCHESTRATOR (8001)                     │
                     │         LangGraph Router + Schema Validation            │
                     │                         │                               │
        ┌────────────┼─────────────────────────┼─────────────────────────┬─────┼─────┐
        │            │                         │                         │     │     │
        ▼            │                         ▼                         ▼     │     ▼
┌─────────────┐      │              ┌─────────────────┐         ┌─────────────┐│ ┌─────────────┐
│ GUARDIAN    │      │              │   NLU SVENSKA   │         │ SMART CACHE ││ │  SECURITY   │
│ (8787)      │◄─────┼──────────────┤     (9002)      │◄────────┤ L1/L2/L3    ││ │  POLICIES   │
│ Brownout    │      │              │ E5+XNLI+Intent  │         │   (6379)    ││ │ PII Masking │
│ Protection  │      │              └─────────────────┘         └─────────────┘│ └─────────────┘
└─────────────┘      │                        │                                │
        │            │                        │                                │
        ▼            │                        ▼                                │
┌─────────────┐      │              ┌─────────────────┐                        │
│ LOAD BALANCER      │              │  RL/ML SYSTEM   │                        │
│ Kill Sequence│      │              │                 │                        │
│ Emergency   │      │              │ LinUCB Router   │                        │
└─────────────┘      │              │ Thompson Sample │                        │
                     │              │ φ-Optimization  │                        │
                     │              └─────────────────┘                        │
                     │                        │                                │
        ┌────────────┼────────────────────────┼────────────────────────────────┼──┐
        │            │                        │                                │  │
        ▼            │                        ▼                                ▼  │
┌─────────────┐      │              ┌─────────────────┐         ┌─────────────┐   │
│ MEMORY/RAG  │      │              │   TOOL REGISTRY │         │ TELEMETRY   │   │
│ FAISS+Redis │◄─────┼──────────────┤   MCP + Health  │◄────────┤ P50/P95     │   │
│ User Memory │      │              │   Latency Class │         │ Energy/RAM  │   │
└─────────────┘      │              └─────────────────┘         └─────────────┘   │
                     │                        │                         │       │
                     │                        ▼                         ▼       │
                     │              ┌─────────────────┐         ┌─────────────┐   │
                     │              │     OLLAMA      │         │   N8N       │   │
                     │              │  Local Models   │         │ Workflows   │   │
                     │              │ qwen2.5 + Llama │         │ (5678)      │   │
                     │              │   (11434)       │         └─────────────┘   │
                     │              └─────────────────┘                           │
                     └─────────────────────────────────────────────────────────────┘
```

---

## 🔄 System Communication Flow

### 1. User Request Processing
```
User Input → Frontend → Orchestrator → Guardian Check → NLU Processing → 
RL Routing → Tool Selection → Execution → Cache Update → Telemetry → Response
```

### 2. Voice Integration Flow
```
Audio Input → Voice Service → ASR → NLU Svenska → Orchestrator → 
Guardian Protection → RL Router → Tool Execution → TTS → Audio Output
```

### 3. Guardian Protection Flow
```
All Requests → Guardian Monitor → System State Check → 
[NORMAL/BROWNOUT/EMERGENCY] → Service Routing/Throttling/Kill
```

---

## 🧠 T1-T9 System Interactions

### T1-T3: Foundation Data Flow
- **Telemetry Ingestion**: All services → Telemetry collector → Episode generation
- **PII Processing**: Security layer masks sensitive data before storage
- **φ-Reward Calculation**: Precision/latency/energy/safety metrics weighted by Fibonacci ratios

### T4-T6: RL/ML Intelligence Loop
- **LinUCB Router**: Uses contextual bandits to route requests (micro/planner/deep)
- **Thompson Sampling**: Beta distributions for tool selection optimization  
- **Live Learning**: Every request updates bandit models in real-time
- **Canary System**: 5% production traffic tests new models automatically

### T7: Preference Optimization
- **DPO Training**: Self-correction based on response quality
- **Verifier System**: Anti-hallucination checks with PII protection
- **Rollout Control**: Automatic promotion/rollback based on win rates

### T8: Stabilization
- **FormatGuard**: Swedish text pre-processing before NLU
- **Overnight Optimizer**: 8-hour autonomous improvement cycles
- **Drift Detection**: PSI/KS metrics monitor model performance
- **Intent Tuning**: Continuous Swedish language optimization

### T9: Multi-Agent Orchestration
- **Judge System**: Multiple agents vote on response quality
- **Preference Aggregation**: Borda + Bradley-Terry ranking
- **Synthetic Data**: 1000+ training triples generated automatically

---

## 📊 Integration Monitoring

### Health Check Chain
```bash
# All services must report healthy to Guardian
curl http://localhost:8787/health    # Guardian master health
curl http://localhost:8001/health    # Orchestrator + routing
curl http://localhost:9002/health    # NLU Swedish processing  
curl http://localhost:6379           # Smart Cache (redis-cli ping)
curl http://localhost:8001/health    # Voice (when implemented)
curl http://localhost:11434/api/tags # Ollama local models
```

### Telemetry Flow
1. **Request Level**: Every API call logged with timing, success, energy usage
2. **Component Level**: Each service reports P50/P95, error rates, resource usage
3. **System Level**: Guardian aggregates all metrics for brownout decisions
4. **ML Level**: RL system ingests telemetry for continuous optimization

### Guardian State Management
```
NORMAL    → All services operating, full functionality
BROWNOUT  → High load detected, non-critical services throttled  
EMERGENCY → System overload, only essential services allowed
```

---

## 🔧 Service Dependencies

### Critical Dependencies (System fails without these)
- **Guardian** ← All services (health monitoring)
- **Orchestrator** ← Frontend, Voice (main API gateway)  
- **NLU** ← Orchestrator (Swedish language processing)
- **Smart Cache** ← Orchestrator (response optimization)

### Performance Dependencies (Degraded performance without these)
- **RL/ML System** ← Orchestrator (intelligent routing)
- **Memory/RAG** ← Orchestrator (context awareness)
- **Telemetry** ← All services (observability)
- **Security** ← All services (PII protection)

### Enhancement Dependencies (Advanced features)
- **Voice** ← NLU, Guardian (speech interface)
- **Ollama** ← Orchestrator (local model fallback)
- **N8N** ← Orchestrator (complex workflows)

---

## 🚀 Integration Testing

### System-Wide E2E Tests
```bash
# Test complete integration chain
./scripts/test_a_z_real_data.sh

# Test Guardian protection
./scripts/test_guardian_brownout.sh

# Test RL optimization
./scripts/test_bandit_routing.sh

# Test Swedish NLU accuracy  
./scripts/test_nlu_svenska.sh
```

### Performance Benchmarks
- **Full System**: Complete request <1.5s P95
- **NLU Processing**: <80ms P95 for Swedish text
- **RL Routing**: <5ms P95 for route decisions
- **Cache Hit Rate**: >80% for repeated queries
- **Guardian Response**: <10ms for protection decisions

---

## 💡 Integration Benefits

### Why Alice v2 is More Than Sum of Parts

1. **Self-Improving**: RL system learns from every interaction across all components
2. **Protective**: Guardian shields entire system from overload and failures  
3. **Intelligent**: NLU provides context that improves all downstream processing
4. **Efficient**: Smart caching reduces compute across all services
5. **Observable**: Complete telemetry enables system-wide optimization
6. **Secure**: Integrated PII protection across all data flows

### Enterprise-Grade Integration Features
- **Zero-downtime updates** via canary deployment
- **Automatic rollback** on performance degradation
- **Resource pooling** across services for efficiency
- **Unified monitoring** and alerting
- **Coordinated scaling** based on system load
- **Integrated security** with comprehensive audit trails

---

*System Integration Guide | Alice v2 Enterprise AI | Updated 2025-09-08*  
*Shows how T1-T9 systems create emergent intelligence through integration*