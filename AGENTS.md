# Alice v2 Agent Status & Priorities
*Current project status, next priorities, and development context for AI agents*

## 🎯 **CURRENT STATUS: Step 8.5 IN PROGRESS**

### **📊 Live Metrics (Latest A-Z Test)**
- **Tool Precision**: 54.7% (target: ≥85%)
- **Latency P95**: 5448ms (target: ≤900ms)
- **Success Rate**: 83% (44/53 scenarios)
- **Schema OK**: 100% (perfect)
- **Cache Hit Rate**: ~10% (needs optimization)

### **🔴 CRITICAL BLOCKERS IDENTIFIED**

#### **1. NLU Service Down**
- **Problem**: `alice-nlu` service not running
- **Impact**: Blocks intent classification for entire system
- **Status**: 🔴 CRITICAL - Must fix first

#### **2. Micro Routing Overloaded**
- **Problem**: Micro gets 58% of requests (should be ≤20%)
- **Impact**: MICRO_MAX_SHARE=0.2 not working
- **Status**: 🔴 HIGH - Affects performance

#### **3. Cache System Ineffective**
- **Problem**: ~90% cache miss rate
- **Impact**: High latency (P95: 5448ms)
- **Status**: 🔴 HIGH - Major performance impact

#### **4. Cache Telemetry Missing**
- **Problem**: No cache_decision/reason logging
- **Impact**: Cannot analyze cache misses
- **Status**: 🟡 MEDIUM - Blocks optimization

### **🎯 NEXT IMMEDIATE PRIORITIES**

#### **Priority 1: Fix NLU (Blocker)**
1. **Start alice-nlu service**
2. **Verify healthcheck works**
3. **Test intent classification**
4. **Validate port configuration**

#### **Priority 2: Implement Cache Telemetry**
1. **Add cache_decision logging**
2. **Add cache reason analysis**
3. **Analyze why 90% miss rate**
4. **Implement cache optimization**

#### **Priority 3: Fix Micro Cap**
1. **Implement MICRO_MAX_SHARE correctly**
2. **Measure and log micro share**
3. **Ensure cap triggers properly**

#### **Priority 4: Cache Optimization**
1. **Implement canonical keys**
2. **Add time-bucket support**
3. **Two-tier cache system**
4. **Negative cache for failed requests**

### **📋 DEVELOPMENT CONTEXT**

#### **Current Architecture**
- **Orchestrator**: ✅ Healthy (200 OK)
- **Guardian**: ✅ Healthy (NORMAL state)
- **Cache**: ✅ Running (Redis healthy)
- **Ollama**: ✅ Running (models available)
- **NLU**: ❌ Not running (critical blocker)

#### **Intent-Guard Status**
- **Functioning**: ✅ Basic regex patterns work
- **Hits**: Simple cases ("vädret", "hej")
- **Misses**: Complex cases ("planera konferensresa")
- **Improvement**: 45.3% → 54.7% (+9.4%)

#### **Quality Gates Status**
- **Tool Precision**: 54.7% (target: ≥85%) - 🔄 Optimization needed
- **Latency P95**: 5448ms (target: ≤900ms) - 🔄 Cache optimization needed
- **Schema OK**: 100% (target: ≥95%) - ✅ Perfect
- **Success Rate**: 83% (target: ≥98%) - 🔄 Some scenarios failing

### **🔧 TECHNICAL DEBT**

#### **Documentation Issues**
- **AGENTS.md**: ✅ Created (this file)
- **ROADMAP.md SLO table**: 🔄 Needs updating
- **TESTING_STRATEGY.md**: 🔄 NLU status outdated
- **ALICE_SYSTEM_BLUEPRINT.md**: 🔄 Hybrid system status outdated

#### **Code Issues**
- **Cache telemetry**: Missing cache_decision/reason
- **Micro cap**: MICRO_MAX_SHARE not enforced
- **NLU healthcheck**: Port mismatch issues
- **Intent-guard**: Limited regex patterns

### **🚀 SUCCESS CRITERIA FOR STEP 8.5**

#### **Target Metrics**
- **Tool Precision**: ≥85% (current: 54.7%)
- **Latency P95**: ≤900ms (current: 5448ms)
- **Cache Hit Rate**: ≥60% (current: ~10%)
- **Success Rate**: ≥98% (current: 83%)

#### **Implementation Goals**
- **NLU Service**: Healthy and responding
- **Cache System**: Effective with telemetry
- **Micro Routing**: Properly capped at 20%
- **Intent-Guard**: Extended regex patterns

### **📈 PROGRESS TRACKING**

#### **Completed This Sprint**
- ✅ Intent-Guard basic implementation
- ✅ Cache key optimization (micro_key)
- ✅ Grammar-scoped micro constraints
- ✅ Negative cache implementation
- ✅ Healthcheck improvements

#### **In Progress**
- 🔄 NLU service restoration
- 🔄 Cache telemetry implementation
- 🔄 Micro cap enforcement
- 🔄 Intent-guard pattern expansion

#### **Next Sprint**
- 🎯 Cache optimization (canonical + time-bucket)
- 🎯 Two-tier cache system
- 🎯 In-flight deduplication
- 🎯 Step 9 - RL Loop preparation

---

**Last Updated**: 2025-09-04
**Next Review**: After NLU fix and cache telemetry implementation
