# Alice v2 Status Report
*Current development status and achievements*

## 🎯 **Current Status: Step 7 COMPLETED - Shadow Mode + Canary Routing LIVE**

### **✅ Major Achievements (Latest Sprint)**

#### **🎯 Shadow Mode + Canary Routing**
- **Shadow Mode**: 100% traffic comparison between planner v1 and v2
- **Canary Routing**: 5% live traffic via planner v2 with strict guardrails
- **Level-gating**: EASY+MEDIUM scenarios only (HARD excluded for safety)
- **Auto-rollback**: Automatic fallback if quality gates are breached

#### **📋 Schema v4 Implementation**
- **Strict Pydantic models**: Enum-only validation with `extra='forbid'`
- **Canonicalizer**: Automatic arg normalization with defaults
- **Auto-repair**: Enum value fixing and schema validation
- **Timezone handling**: Europe/Stockholm defaults
- **5-minute rounding**: ISO time normalization

#### **📊 Live Metrics (Current)**
- **Schema OK Rate**: 97.5% (EASY+MEDIUM)
- **Intent Match Rate**: 95% (EASY+MEDIUM)
- **Tool Match Rate**: 100% (EASY+MEDIUM)
- **Latency Delta**: -34.9ms (v2 faster than v1)
- **Canary Eligible**: 6/120 requests (5%)
- **Canary Routed**: 6/120 requests (5%)

### **🚀 Technical Implementation**

#### **Planner v2 Enhancements**
- **System prompt**: Strict JSON-only output with enum examples
- **Generation params**: `temperature=0.1`, `top_p=0.3`, `top_k=1`
- **GBNF grammar**: Strict enum alternation for intent/tool/render_instruction
- **Auto-repair**: `<enum>` placeholder replacement and synonym mapping

#### **Shadow Evaluator**
- **Intent derivation**: Primary intent derived from tool for accurate comparison
- **Canonical args**: Normalized arguments for comparison
- **Level extraction**: Complexity level from classifier results
- **Rollback analysis**: Detailed rollback reason tracking

#### **Canary Router**
- **Quality gates**: Schema OK ≥98%, Intent Match ≥95%, Latency ≤150ms
- **Level gating**: EASY+MEDIUM only, HARD excluded
- **Hash-based selection**: Deterministic session routing
- **Auto-rollback**: Automatic fallback on gate breach

### **📈 Performance Improvements**

#### **Before Shadow Mode**
- Schema OK: ~80% (inconsistent)
- Intent Match: ~70% (poor)
- Tool Match: ~85% (acceptable)

#### **After Shadow Mode + Canary**
- Schema OK: 97.5% (significant improvement)
- Intent Match: 95% (major improvement)
- Tool Match: 100% (perfect)
- Latency: -34.9ms delta (v2 faster)

### **🔧 Development Workflow**

#### **Docker Cache Lessons**
- **Problem**: Code changes not reflected in containers
- **Solution**: `make down && make up` for code changes
- **Fast dev**: `make dev-fast` for core services only (2min vs 5min)
- **Documentation**: `docs/development/docker_cache_lessons.md`

#### **Testing Improvements**
- **Script fixes**: Fixed `planner_stress_test.py` endpoint and argument parsing
- **Real testing**: Shadow mode provides real production data
- **Metrics**: Live monitoring via HUD at `http://localhost:18000/hud`

### **🎯 Next Steps**

#### **Immediate (Next Sprint)**
1. **Step 8 - Text E2E hard test**: Load testing and SLO validation
2. **HARD scenarios**: Implement two-pass pipeline (Decomposer + Arg-builder)
3. **Deterministic Planner-DAG**: Retries and circuit breakers

#### **Medium Term**
1. **Voice pipeline**: ASR + TTS integration
2. **Vision**: YOLOv8 + SAM2 integration
3. **Deep reasoning**: Llama-3.1-8B integration

### **📊 Success Metrics**

#### **Technical SLOs**
| Metric | Target | Current | Status |
|--------|--------|---------|--------|
| Schema OK Rate | ≥98% | 97.5% | 🟡 |
| Intent Match Rate | ≥95% | 95% | ✅ |
| Tool Match Rate | ≥95% | 100% | ✅ |
| Latency Delta | ≤150ms | -34.9ms | ✅ |
| Canary Success | ≥90% | 100% | ✅ |

#### **Business Impact**
- **Risk reduction**: Canary routing prevents production issues
- **Quality improvement**: 97.5% schema OK vs previous 80%
- **Performance**: v2 faster than v1 by 34.9ms
- **Observability**: Real-time metrics and rollback analysis

### **🏆 Key Learnings**

1. **Shadow mode is powerful**: 100% traffic comparison without risk
2. **Canary routing works**: 5% live traffic with strict guardrails
3. **Schema validation is critical**: Auto-repair prevents failures
4. **Docker caching is tricky**: Full rebuild often faster than debugging
5. **Real metrics matter**: Production data beats synthetic tests

---

**Last Updated**: 2025-09-03  
**Next Review**: 2025-09-10  
**Status**: 🟢 ON TRACK
