# 🧮 FIBONACCI SYSTEM STACK - Alice v2 Architecture

**Version:** Fibonacci-Optimized v2  
**Status:** DEPLOYED & OPERATIONAL  
**Mathematical Foundation:** Golden Ratio (φ = 1.618) + Fibonacci Sequences  

---

## 🧱 RUNTIME SERVICES (ACTIVE)

```ascii
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│  alice-dev-     │    │   guardian      │    │   alice-nlu     │
│  proxy (18000)  │───▶│   (8787)        │───▶│   (9002)        │
│  Caddy reverse  │    │  Security &     │    │  Swedish NLU    │  
│  proxy          │    │  Guardrails     │    │  + Fibo CB      │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────────┐
│                    alice-orchestrator (8000)                       │
│                     FIBONACCI ENGINE CORE                          │  
│  ┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐     │
│  │   Middleware    │ │     Routers     │ │   Fibonacci     │     │
│  │  • Auth         │ │  • chat         │ │  • Cache L1-L10 │     │
│  │  • Logging      │ │  • feedback     │ │  • Spiral Match │     │
│  │  • Idempotency  │ │  • optimized_   │ │  • φ-Balancer   │     │
│  │  • PII          │ │    orchestrator │ │  • CB Retries   │     │
│  └─────────────────┘ └─────────────────┘ └─────────────────┘     │
└─────────────────────────────────────────────────────────────────────┘
                                │
                                ▼
                    ┌─────────────────────┐
                    │   alice-cache       │
                    │   Redis (6379)      │
                    │   🧮 L1-L10 Fibo    │
                    │   TTL Hierarchy     │
                    └─────────────────────┘
```

### **Service Details:**
- **alice-orchestrator (8000):** API hub + Fibonacci router engine
- **guardian (8787):** Security policies + guardrails  
- **alice-nlu (9002):** Swedish NLU med Fibonacci circuit breaker
- **alice-cache (Redis 6379):** Fibonacci cache hierarchy L1-L10
- **alice-dev-proxy (Caddy 18000):** Development reverse proxy

### **Disabled Services (Step 8.5):**
🔕 `alice-memory`, `alice-voice`, `alice-n8n`, `alice-ollama`

---

## 🌀 FIBONACCI KOMPONENTER (MATHEMATICAL CORE)

### **1. Cache Hierarchy System**
```python
# L1-L10 TTL Progression (Fibonacci Hours)  
CACHE_TIERS = {
    "L1": {"ttl": "1h",  "purpose": "immediate_cache"},      # Hot path
    "L2": {"ttl": "2h",  "purpose": "recent_patterns"},     # Active session  
    "L3": {"ttl": "3h",  "purpose": "frequent_queries"},    # Common requests
    "L4": {"ttl": "5h",  "purpose": "established_patterns"}, # User habits
    "L5": {"ttl": "8h",  "purpose": "stable_responses"},    # Work day cycle
    "L6": {"ttl": "13h", "purpose": "extended_patterns"},   # Half-day patterns
    "L7": {"ttl": "21h", "purpose": "daily_cycles"},        # Daily routines
    "L8": {"ttl": "34h", "purpose": "multi_day_patterns"},  # Day/night cycles
    "L9": {"ttl": "55h", "purpose": "weekly_patterns"},     # Work week cycles
    "L10":{"ttl": "89h", "purpose": "long_term_patterns"}   # Extended memory
}

# Key Pattern: "micro:none:*", "planner:*", "tool:*"
# Target Hit Rate: >70% (current: ~6.3% during warm-up)
```

### **2. Semantic Spiral Matching**
```python
# 512-dimensional embeddings → 89 spiral points (Fibonacci)
SPIRAL_CONFIG = {
    "dimensions": 512,           # Feature vector space
    "spiral_points": 89,         # Fibonacci number for natural curves
    "golden_angle": 2π/φ²,       # Golden spiral angle in radians  
    "similarity_threshold": φ⁻¹,  # 0.618 similarity for cache hits
    "coordinate_cache": True     # Cache spiral calculations
}
```

### **3. Golden Ratio Routing & Budgets**
```python  
FIBONACCI_ROUTING = {
    "micro_budget_ms": [13, 21, 34],        # Progressive timeouts
    "tool_calls_max": [1, 2, 3],            # Fibonacci call limits
    "rag_topk_steps": [1, 2, 3, 5],         # Iterative expansion  
    "timeout_phases_sec": [1, 2, 5, 8],     # Abort sequence
    "circuit_breaker_delays": [1, 2, 3, 5, 8, 13]  # Backoff progression
}
```

### **4. φ-Load Balancer (Golden Ratio Distribution)**
```python
PHI_LOAD_BALANCER = {
    "enabled": False,                    # Feature flag (pending activation)
    "service_weights": {
        "primary": φ,                    # 1.618 weight  
        "secondary": φ⁻¹,               # 0.618 weight
        "tertiary": φ⁻²                 # 0.382 weight
    },
    "natural_distribution": True,        # Organic traffic flow
    "endpoint": "/api/orchestrator/load-balancer"
}
```

---

## 🔄 REQUEST LIFECYCLE (E2E FIBONACCI FLOW)

```ascii
1. API Request → alice-dev-proxy (18000)
                        │
                        ▼
2. Route to orchestrator (8000) + Request ID generation
                        │  
                        ▼
3. Middleware Pipeline:
   ┌─────────────────────────────────────────────────────────┐
   │ Auth → Logging → Idempotency → PII Filtering           │
   └─────────────────────────────────────────────────────────┘
                        │
                        ▼ 
4. Security Check → Guardian (8787)
   ┌─────────────────────────────────────────────────────────┐
   │ Policy Engine + Tool Gates + Rate Limiting             │
   └─────────────────────────────────────────────────────────┘
                        │
                        ▼
5. 🧮 FIBONACCI CACHE LOOKUP (L1→L10):
   ┌─────┬─────┬─────┬─────┬─────┬─────┬─────┬─────┬─────┬─────┐
   │ L1  │ L2  │ L3  │ L4  │ L5  │ L6  │ L7  │ L8  │ L9  │L10  │
   │ 1h  │ 2h  │ 3h  │ 5h  │ 8h  │13h  │21h  │34h  │55h  │89h  │
   └─────┴─────┴─────┴─────┴─────┴─────┴─────┴─────┴─────┴─────┘
                    Cache HIT? → Return sub-ms response
                    Cache MISS? ↓
6. Semantic Spiral Matching (89 points):
   ┌─────────────────────────────────────────────────────────┐
   │ 512D → Spiral Coordinates → Nearest Neighbor Search    │  
   │ φ-based similarity scoring → Potential cache matches   │
   └─────────────────────────────────────────────────────────┘
                    Similar query found? → Adapted response
                    No match? ↓
7. Routing Decision (Fibonacci Heuristics):
   ┌─────────────┐  ┌─────────────┐  ┌─────────────┐
   │   MICRO     │  │    TOOL     │  │   PLANNER   │
   │  (13-21ms)  │  │ (Direct)    │  │ (Complex)   │  
   │ Simple Q&A  │  │ Calculator  │  │ Multi-step  │
   └─────────────┘  └─────────────┘  └─────────────┘
                        │
                        ▼
8. NLU Processing → alice-nlu (9002) 
   ┌─────────────────────────────────────────────────────────┐
   │ Swedish NLU + Intent Classification                     │
   │ Circuit Breaker: 1s→2s→3s→5s→8s→13s backoff           │
   └─────────────────────────────────────────────────────────┘
                        │
                        ▼
9. LLM Processing (Fibonacci-optimized):
   ┌─────────────────────────────────────────────────────────┐
   │ Model: qwen2.5:3b (production) / qwen2.5:0.5b (training)│
   │ Max Tool Calls: 1→2→3 (progressive)                    │  
   │ RAG Top-K: 1→2→3→5 (iterative expansion)              │
   └─────────────────────────────────────────────────────────┘
                        │
                        ▼
10. Cache Write-Back (Fibonacci Layer Assignment):
    ┌─────────────────────────────────────────────────────────┐
    │ Frequency Analysis → Assign to appropriate L1-L10      │
    │ Pattern Maturity → Higher layers for stable responses  │
    └─────────────────────────────────────────────────────────┘
                        │
                        ▼
11. Response + Metrics Emission:
    ┌─────────────────────────────────────────────────────────┐
    │ Latency Buckets: 1/2/3/5/8/13... ms buckets           │  
    │ Cache Hit Rate, Route Type, Tool Calls Used            │
    └─────────────────────────────────────────────────────────┘
```

---

## ⚙️ CONFIGURATION (ENVIRONMENT)

### **Environment Variables (.env)**
```bash
# Fibonacci Router Configuration
FIB_ROUTER_MICRO_BUDGET_MS=13
FIB_ROUTER_PLANNER_TIMEOUT_MS=800  
FIB_ROUTER_MAX_TOOL_CALLS=3

# RAG & Search
FIB_RAG_TOPK_STEPS=1,2,3,5

# Timeout Phases  
FIB_TIMEOUT_PHASES=1,2,5,8

# Circuit Breaker & Retries
FIB_RETRY_DELAYS=1,2,3,5,8,13

# Cache Hierarchy
FIB_CACHE_TTLS_H=1,2,3,5,8,13,21,34,55,89

# Semantic Spiral
FIB_SPIRAL_POINTS=89
FIB_SPIRAL_DIMENSIONS=512

# Golden Ratio Load Balancer
ENABLE_PHI_LOAD_BALANCER=false
PHI_PRIMARY_WEIGHT=1.618
PHI_SECONDARY_WEIGHT=0.618

# Training Optimization  
TRAINING_MODE=false
LLM_MODEL_TRAINING=qwen2.5:0.5b
LLM_MODEL_PRODUCTION=qwen2.5:3b
```

### **Python Configuration (orchestrator/config.py)**
```python
from src.config.fibonacci import FIBONACCI_SEQUENCE, GOLDEN_RATIO

FIBONACCI_CONFIG = {
    "router": {
        "micro_budget_ms": FIBONACCI_SEQUENCE[7],        # 13ms
        "planner_timeout_ms": 800,  
        "max_tool_calls": FIBONACCI_SEQUENCE[4]          # 3 calls
    },
    "rag": {
        "topk_steps": FIBONACCI_SEQUENCE[1:6]            # [1,1,2,3,5]
    },
    "timeouts": {
        "phases_sec": [1, 2, 5, 8]                       # Fibonacci progression
    },
    "retries": {
        "delays_sec": FIBONACCI_SEQUENCE[1:7]            # [1,1,2,3,5,8]  
    },
    "cache": {
        "ttls_h": FIBONACCI_SEQUENCE[1:11],              # [1,1,2,3,5,8,13,21,34,55,89]
        "similarity_threshold": 1/GOLDEN_RATIO           # φ^-1 ≈ 0.618
    },
    "spiral": {
        "points": FIBONACCI_SEQUENCE[11],                # 89 points
        "dimensions": 512,
        "golden_angle": 2 * math.pi / (GOLDEN_RATIO**2)
    },
    "phi_lb": {
        "enabled": False,                                # Feature flag
        "primary_weight": GOLDEN_RATIO,                  # 1.618
        "secondary_weight": 1/GOLDEN_RATIO               # 0.618  
    }
}
```

---

## 🧪 OBSERVABILITY (FIBONACCI METRICS)

### **Latency Histogram Buckets**
```python
FIBONACCI_BUCKETS = [
    1, 2, 3, 5, 8, 13, 21, 34, 55, 89, 144, 233, 377, 610, 987  # milliseconds
]

# Percentile Targets:
# p50: <21ms, p90: <89ms, p95: <144ms, p99: <377ms  
```

### **Cache Performance Metrics**
```python
CACHE_METRICS = {
    "hit_rate_total": "target >70%",
    "hit_rate_by_tier": {
        "L1": "target >40%",    # Hot path
        "L2": "target >25%",    # Recent  
        "L3": "target >20%",    # Frequent
        "L4-L10": "target >15%" # Long-term patterns
    },
    "spiral_matches": "semantic similarity hits",  
    "cache_warming_progress": "pattern maturity over time"
}
```

### **Alert Thresholds (Fibonacci Progression)**  
```yaml
alerts:
  response_time_p95:
    warning: 144ms    # Fibonacci threshold
    critical: 377ms   # Higher Fibonacci threshold
  
  cache_hit_rate:
    warning: <50%     # Below optimization target
    critical: <25%    # System degradation
  
  error_rate_incidents:
    levels: [3, 5, 8] # Fibonacci escalation per hour
```

---

## ✅ SYSTEM VALIDATION CHECKLIST

### **Active Components** ✅
- [x] alice-orchestrator: HEALTHY (Fibonacci engine loaded)
- [x] alice-cache: HEALTHY (L1-L10 hierarchy active) 
- [x] alice-nlu: HEALTHY (Circuit breaker functional)
- [x] guardian: HEALTHY (Security policies active)
- [x] alice-dev-proxy: ACTIVE (Development routing)

### **Fibonacci Features** 🧮
- [x] Cache hierarchy: L1-L10 tiers implemented
- [x] Spiral matching: 89-point algorithm deployed  
- [x] Circuit breaker: Fibonacci backoff active
- [x] Routing budgets: 13→21→34ms progression
- [ ] φ-Load balancer: Code deployed, endpoint pending
- [x] Mathematical foundation: φ = 1.618 throughout system

### **Performance Metrics** 📊
- Current: 417ms average (warm-up phase)
- Target: 35.9ms average (38.2% improvement over 58.125ms baseline)
- Cache Hit Rate: 6.3% → 70%+ target
- Resource Usage: Optimized (123.6MB memory, 0.26% CPU)

---

## 🧭 NEXT STEPS (FIBONACCI OPTIMIZATION ROADMAP)

### **Phase 1: Cache Warming (24h)** 
1. **Activate φ-load balancer** behind feature flag (1%→2%→5% traffic)
2. **Cache warming protocol:** Top-100/500 queries → L1-L3 population  
3. **Pattern maturation:** Let frequently accessed items migrate to higher tiers

### **Phase 2: Performance Optimization (48h)**
1. **Cache spiral results** per fingerprint → reduce CPU overhead
2. **Verify thresholds:** micro_budget 13→21ms, RAG top-k 1→2→3→5
3. **Target achievement:** p95 <144ms, cache hit rate >70%

### **Phase 3: Advanced Features (1 week)**
1. **Predictive scaling:** Fibonacci resource prediction engine
2. **Health monitoring:** Real-time Fibonacci metrics dashboard
3. **Connection pooling:** Database connections with Fibonacci sizing

---

## 🎯 SUCCESS CRITERIA 

**Mathematical Perfection Achieved When:**
- Response Time: 35.9ms average (38.2% improvement) ✅ Target
- Cache Hit Rate: >70% across L1-L10 hierarchy ✅ Target  
- System Stability: All services healthy + predictable scaling ✅ Current
- Resource Efficiency: CPU <1%, Memory optimized ✅ Current
- Golden Ratio Harmony: φ-based optimization throughout stack ✅ Implementation

---

*🧮 Fibonacci System Stack v2.0 - Mathematical perfection through golden ratio architecture*  
*Generated from VERKLIG Alice v2 live system analysis*