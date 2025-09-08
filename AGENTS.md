# 🤖 AI Agent Orientation - Alice v2

**For AI agents starting work on Alice v2 project - ACTUAL STATUS 2025-09-08**

## 🚨 CURRENT REALITY CHECK - POST HUD/FRONTEND CLEANSING

**WHAT JUST HAPPENED (Sep 8, 2025):**
- ✅ Complete HUD/frontend cleansing operation completed
- ✅ All legacy frontend references eliminated from codebase
- ✅ Documentation poltergeist cleansing completed
- ❌ Frontend completely removed - MUST BUILD NEW React/Next.js interface

## 📚 MANDATORY READING - THESE FILES ACTUALLY EXIST

### Step 1: System Understanding (5 min)
```text
README.md                    # System overview + current status  
ALICE_SYSTEM_BLUEPRINT.md    # Complete architecture + service ports
PROJECT_STATUS.md            # Current development phase status
PRIORITIZED_BACKLOG.md       # What needs to be built next
```

### Step 2: Current Development Context (10 min)
```text
ROADMAP.md                   # Post-T8/T9 development roadmap
TRAINING_HUD.md              # AI training monitoring (LEGITIMATE)  
CONTRIBUTING.md              # Development workflow
TESTING_STRATEGY.md          # How we test systems
```

### Step 3: Technical Rules & Configuration (5 min)
```text  
.cursor/rules/workflow.mdc   # Development workflow rules
.cursor/rules/PRD.mdc        # Product requirements  
.cursor/rules/ADR.mdc        # Architecture decisions
SECURITY_AND_PRIVACY.md     # Security policies
```

## 🎯 CURRENT ACCURATE SYSTEM STATUS

**✅ ENTERPRISE-GRADE AI SYSTEM (T1-T9 Complete):**
- **Orchestrator (LangGraph)**: Port 8001 ✅ - Enterprise AI routing med T1-T9 RL optimization, schema-validering, cost/telemetri
- **Guardian System**: Port 8787 ✅ - Brownout/EMERGENCY protection, kill-sequence, energi/RAM/CPU/temp monitoring  
- **NLU Svenska**: Port 9002 ✅ - E5-embeddings + XNLI fallback, 88%+ accuracy, P95 ≤80ms route-hints
- **Smart Cache (L1/L2/L3)**: Port 6379 ✅ - Exact + semantic + negative cache, telemetri, hit-rate optimization
- **Memory/RAG System**: ✅ - Redis (session) + FAISS (user), consent-policy, `forget` <1s
- **Security/Middleware**: ✅ - Auth, idempotency, PII-masking, policy-motor, rate-limits, HMAC-webhooks
- **RL/ML Intelligence**: ✅ - LinUCB router + Thompson Sampling, φ-belöning, GBNF-tvingad JSON, canary deployment
- **Observability**: Port 8501 ✅ - P50/P95 metrics, RAM-peak, Wh/turn, tool-error classification, auto-verify E2E
- **Load Testing**: ✅ - Multi-vector stress tests (CPU/memory/tool/vision), 20+ scenarios, SLO gates

**❌ BROKEN SERVICES (HIGH PRIORITY FIXES NEEDED):**
- **Voice Service**: Port 8002 ❌ - Restart loop, needs urgent debugging

**✅ RECENTLY FIXED:**
- **Ollama Local LLM**: Port 11434 ✅ - Working with qwen2.5:3b and multiple models

**❌ COMPLETELY MISSING (MUST BUILD FROM SCRATCH):**
- **Frontend Web UI**: No longer exists - Need React/Next.js interface
- **User Interface**: Only Streamlit monitoring available

## 🚀 CURRENT DEVELOPMENT PHASE: USER INTERFACE COMPLETION

**Why This Phase:** Alice v2 enterprise-grade AI system är 90%+ complete med självförbättrande intelligens, RL optimization, Guardian protection, och full observability. **Missing only**: User interface components för att exponera det magiska systemet.

**HIGHEST PRIORITY TASKS:**
1. **Build New Frontend** - React/Next.js web interface (apps/hud was obliterated)
2. **Fix Voice Service** - Complete rebuild required (see [VOICE_REACTIVATION_GUIDE.md](VOICE_REACTIVATION_GUIDE.md))

## 🏆 COMPLETED ENTERPRISE SYSTEMS (T1-T9 Complete)

**T1-T3: Foundation & φ-Belöning Complete**
- Telemetri → episoder med PII-mask processing
- Fibonacci-viktad reward system (precision/latens/energi/säkerhet)  
- Production-ready data pipeline med quality control

**T4-T6: RL/ML Optimization Complete**
- LinUCB Router med contextual bandits (50,374 ops/sec - 10x over SLO)
- Thompson Sampling för tool selection med Beta-distributioner
- φ-Reward System (Golden Ratio optimization φ=1.618)
- GBNF Schema enforcement (100% JSON compliance)
- ToolSelector v2 med GBNF-forced JSON, 75% rule coverage, <5ms P95
- Live bandit-routing med canary 5%, guardian-override, auto-fallback

**T7: Preference Optimization Complete**  
- DPO/ORPO training med self-correction
- Response verifier med PII masking
- Canary deployment system (5% → 100%)
- Win rate: 100% (3/3 pairs)

**T8: Stabilization Infrastructure Complete**
- FormatGuard pre-processing för Swedish text
- Overnight Auto-Stabilizer (8-timmars autonom optimering)
- Drift detection (PSI/KS metrics)
- Intent classification tuning system

**T9: Multi-Agent Optimization Complete**  
- Borda ranking + Bradley-Terry aggregation
- PII-safe real data adapter
- Synthetic data generation (1000 triples)
- Judge orchestrator för preference comparison

**Enterprise Infrastructure Complete**
- Guardian brownout/EMERGENCY protection med kill-sequence
- Smart Cache L1/L2/L3 med semantic matching
- Security/Middleware med auth, PII-masking, policy-motor
- Full observability med P50/P95, RAM-peak, Wh/turn tracking
- Load testing suite med multi-vector stress tests
- Tool Registry (MCP) med health/latency classification

## 🔌 CURRENT PORT MAPPING (Verified 2025-09-08)

**✅ WORKING SERVICES:**
```bash
curl http://localhost:8001/health  # Orchestrator API
curl http://localhost:8787/health  # Guardian monitoring  
curl http://localhost:9002/health  # NLU Swedish processing
curl http://localhost:6379         # Redis cache (redis-cli ping)
open http://localhost:8501         # Streamlit dashboard
```

**❌ BROKEN SERVICES:**
```bash  
curl http://localhost:8002/health  # Voice service (will fail)
curl http://localhost:11434/api/tags # Ollama LLM (will fail)
curl http://localhost:3000         # Frontend (DOES NOT EXIST)
```

## 📋 CRITICAL RULES FOR AI AGENTS

### ✅ DO (Follow These Rules)

1. **Read actual files** - Only reference files that exist in the codebase
2. **Use correct ports** - 8001 for API, 8501 for monitoring UI 
3. **Build frontend NEW** - Don't look for existing React/HUD components
4. **Update documentation** when making changes
5. **Use TodoWrite tool** to track progress on complex tasks
6. **Follow conventional commits** (`feat:`, `fix:`, `docs:`)
7. **Test with real data** - Use `./scripts/test_a_z_real_data.sh`

### ❌ DON'T (Avoid These Mistakes)

1. **Reference non-existent files** - Many old docs reference removed files
2. **Assume frontend exists** - It was completely removed during cleansing
3. **Use broken ports** - Port 18000 doesn't work, use 8001
4. **Commit secrets** - Never commit API keys or tokens
5. **Skip documentation updates** - Keep docs aligned with reality
6. **Work without TodoWrite** on multi-step tasks

## 🛠️ QUICK START FOR DEVELOPMENT

```bash
# Start all services
make up

# Verify core services are working
curl http://localhost:8001/health && echo "✅ Alice API" 
curl http://localhost:8787/health && echo "✅ Guardian"
curl http://localhost:9002/health && echo "✅ NLU"
open http://localhost:8501 && echo "✅ Monitoring Dashboard"

# Run comprehensive tests
./scripts/test_a_z_real_data.sh

# View current system status  
open http://localhost:8501  # Only working UI currently
```

## 🎯 IMMEDIATE NEXT STEPS

**For AI agents joining the project:**

1. **Read the mandatory files above** (don't skip this!)
2. **Understand current phase** - We're building frontend from scratch
3. **Check service health** with the curl commands above
4. **Start with highest priority** - Frontend development or voice service fix
5. **Use TodoWrite for complex tasks** to track progress

## 🔗 CURSOR RULES INTEGRATION

**Key .cursor/rules/ files to follow:**
- `workflow.mdc` - Development workflow requirements
- `PRD.mdc` - Product requirements and constraints  
- `ADR.mdc` - Architecture decision documentation
- `types.mdc` - TypeScript type definitions
- `structured-outputs.mdc` - Response formatting rules

**Integration with development:**
- These rules are enforced during code review
- Follow patterns established in these files
- Update rules when making architectural changes

## 🧹 POST-CLEANSING REALITY

**What was removed:**
- All legacy HUD/frontend components  
- apps/hud directory completely deleted
- Frontend references in all documentation
- Broken port mappings and invalid service references

**What was preserved:**
- Core AI systems (T4-T9) - fully operational
- Legitimate monitoring dashboards (Streamlit)  
- Training HUD for AI optimization
- All backend services and APIs

**What needs to be built:**
- Modern React/Next.js web interface
- Voice service debugging and restart
- Ollama service health check fixes

---

**💡 Remember:** Alice v2 is an **enterprise-grade, självförbättrande AI-assistent** med T1-T9 complete systems. Don't reinvent the advanced AI architecture - build the missing UI layer to expose the magic!

*Updated: 2025-09-08 | Post HUD/Frontend Cleansing | Current Phase: Frontend Development*