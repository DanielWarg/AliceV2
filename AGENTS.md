# Alice v2 AGENTS.md
*Instructions and context for AI coding agents working on Alice AI Assistant*

## 📋 Project Overview
Alice v2 is a modular AI assistant with deterministic safety (Guardian), real-time voice pipeline (ASR→NLU→TTS), and intelligent LLM routing. Built as monorepo with clean architecture: services/ (Python FastAPI), apps/ (Next.js), packages/ (shared TypeScript).

**Current Status**: Architecture complete, ready for step-by-step implementation following ROADMAP.md

## 🛠️ Dev Environment Tips

### Project Navigation
- Use `find v2 -name "package.json" | head -10` to see monorepo structure
- Jump to services: `cd v2/services/{orchestrator|guardian|voice}`  
- Jump to packages: `cd v2/packages/{api|types|ui}`
- Check service status: `curl http://localhost:{8000|8787|8001}/health`

## 🔧 Strict Development Discipline

### Virtual Environment - MANDATORY
**NEVER work without .venv - this prevents dependency conflicts and ensures reproducible builds**

```bash
# ALWAYS create and activate .venv for each Python service
cd services/{orchestrator|guardian|voice}
python -m venv .venv
source .venv/bin/activate  # Linux/Mac ONLY - Never use Windows activate

# Verify isolation before installing anything
which python  # Should show .venv/bin/python
which pip     # Should show .venv/bin/pip

# Install dependencies in isolated environment
pip install -r requirements.txt

# Deactivate when switching projects
deactivate
```

### Port Management - Kill Before Start
**Alice v2 Standard Ports:**
- **8000**: Orchestrator (main API)
- **8787**: Guardian (system safety)  
- **8001**: Voice Service (ASR/TTS)
- **8501**: Dashboard (Streamlit observability)
- **3000**: Web Frontend (Next.js)
- **6379**: Redis (cache/sessions)
- **11434**: Ollama (LLM server)

```bash
# ALWAYS kill existing processes before starting services
# This prevents port conflicts and zombie processes
lsof -ti:8000,8787,8001,8501,3000 | xargs kill -9 2>/dev/null || true

# Start services in dependency order
# 1. Infrastructure first
docker compose up -d redis ollama

# 2. Core services
cd services/guardian && source .venv/bin/activate && uvicorn main:app --reload --port 8787 &
sleep 2  # Let Guardian stabilize

cd services/orchestrator && source .venv/bin/activate && uvicorn main:app --reload --port 8000 &
sleep 2

cd services/voice && source .venv/bin/activate && uvicorn main:app --reload --port 8001 &

# 3. Frontend last
pnpm --filter web dev &
```

### Testing During Development - MANDATORY
**Before every commit, ALL these checks must pass:**

```bash
# 1. Service health checks
curl -f http://localhost:8000/health || echo "❌ Orchestrator down"
curl -f http://localhost:8787/guardian/health || echo "❌ Guardian down"  
curl -f http://localhost:8001/health || echo "❌ Voice Service down"

# 2. Unit tests with coverage
cd services/orchestrator && pytest tests/ -v --cov=src
cd services/guardian && pytest tests/ -v --cov=src  
cd services/voice && pytest tests/ -v --cov=src

# 3. Integration tests
python tests/integration/test_health_endpoints.py
python tests/integration/test_guardian_admission.py

# 4. E2E tests (requires all services running)
pnpm test:e2e

# 5. Performance validation
python tests/performance/test_guardian_sla.py  # Must be <150ms
```

### Development Commands
```bash
# Install all dependencies (respects .venv isolation)
pnpm install:all

# Start infrastructure only
docker compose up -d redis ollama

# Development workflow (with automatic port cleanup)
./scripts/dev-start.sh  # Custom script that kills processes + starts services

# Quick health check all services
./scripts/health-check.sh
```

### Python Services Setup - Strict Process
```bash
# 1. Navigate to service directory
cd services/{orchestrator|guardian|voice}

# 2. ALWAYS create isolated environment
python -m venv .venv
source .venv/bin/activate

# 3. Verify isolation
python -c "import sys; print('✅' if '.venv' in sys.executable else '❌ Not in venv!')"

# 4. Install dependencies
pip install -r requirements.txt

# 5. Run with hot-reload on correct port
uvicorn main:app --reload --host 127.0.0.1 --port {8000|8787|8001}
```

### TypeScript Packages Setup
```bash
# Build shared packages in dependency order
pnpm --filter @alice/types build
pnpm --filter @alice/api build
pnpm --filter @alice/ui build

# Then start consuming applications
pnpm --filter web dev
```

## 🧪 Testing Instructions

### Testing Hierarchy
1. **Unit Tests**: Each service/package tests its own logic
2. **Integration Tests**: Cross-service communication via HTTP/WebSocket
3. **E2E Tests**: Full voice pipeline with Playwright
4. **Performance Tests**: SLO validation (latency P95, Guardian response time)

### Python Service Testing
```bash
cd services/{orchestrator|guardian|voice}
pytest tests/ -v --cov=src

# Specific test patterns
pytest tests/test_guardian_state_machine.py -v
pytest -k "test_health" -v

# With coverage report
pytest --cov=src --cov-report=html
open htmlcov/index.html
```

### TypeScript Package Testing
```bash
# Individual package tests
pnpm --filter @alice/api test
pnpm --filter web test

# All tests
pnpm test

# E2E tests (requires services running)
pnpm test:e2e
```

### Integration Testing Flow
```bash
# 1. Start all services
pnpm dev:services &
sleep 10

# 2. Test service communication
python tests/integration/test_health_endpoints.py
python tests/integration/test_guardian_admission.py
python tests/integration/test_voice_websocket.py

# 3. E2E voice flow
playwright test tests/e2e/voice-flow.spec.ts --headed
```

### Performance & SLO Testing
```bash
# Guardian response time (target: <150ms)
python tests/performance/test_guardian_sla.py

# Voice pipeline latency (target: P95 <2000ms)  
python tests/performance/test_voice_latency.py

# Load testing
locust -f tests/performance/locustfile.py --host http://localhost:8000
```

## 📤 PR Instructions

### PR Title Format
`[component] Description`

Examples:
- `[guardian] Add hysteresis to prevent state oscillation`
- `[voice] Implement Whisper.cpp streaming ASR`  
- `[orchestrator] Add model routing based on intent complexity`
- `[web] Add Guardian status HUD component`

### Pre-commit Validation
**ALWAYS run before committing:**
```bash
# Linting & formatting
pnpm lint
pnpm format

# Type checking
pnpm type-check

# Python quality
cd services/{service} && ruff check . && ruff format . && mypy .

# Tests must pass
pnpm test
pytest services/*/tests/

# Build verification
pnpm build
```

### Implementation Guidelines

#### Guardian Safety Rules
- **NEVER** modify Guardian thresholds without extensive testing
- Guardian logic must be deterministic (no AI in safety loop)
- State transitions must complete in <150ms
- Always test brownout/recovery scenarios

#### Voice Pipeline Requirements  
- ASR partial transcripts required (<300ms)
- TTS responses must be cached for common phrases
- WebSocket reconnection logic mandatory
- Svenska language support prioriterad

#### API Contract Stability
- All payloads must include `"v":"1"` for versioning
- Breaking changes require new version endpoints
- Backward compatibility required for 2 major versions
- OpenAPI spec must be kept updated

#### Memory & Privacy
- User consent required before memory writes
- PII masking in logs (automatic detection)
- Redis TTL for session data (7 days max)
- FAISS memory operations must be <1s

### Code Quality Standards
- **TypeScript**: Strict mode, ESLint + Prettier, JSDoc for public APIs
- **Python**: Type hints required, ruff formatting, 80% test coverage minimum
- **Architecture**: Clean separation, dependency injection, error boundaries
- **Performance**: Meet SLO targets (documented in ROADMAP.md)

### Review Expectations
- Two maintainer approvals required
- All CI checks must pass (linting, tests, security scans)
- Performance regression tests for critical paths
- Documentation updated for user-facing changes

## 🚀 Implementation Roadmap

### Phase 1: Core Foundation (1-2 weeks)
**Priority**: Critical foundation components

1. **Package Dependencies**
   - Create package.json for all services/packages
   - Install core dependencies (FastAPI, Next.js, etc.)
   - Configure TypeScript build chain

2. **Guardian Service Implementation**
   - Complete Python implementation with psutil monitoring
   - API server with FastAPI (:8787)
   - State machine with hysteresis logic
   - Integration tests

3. **Voice Service Skeleton**
   - FastAPI server structure (:8001)
   - ASR endpoint placeholder (Whisper.cpp integration)
   - TTS endpoint placeholder (Piper integration)
   - WebSocket handler for real-time audio

### Phase 2: Voice Pipeline (2-3 weeks)
**Priority**: Core user experience

1. **ASR Integration**
   - Whisper.cpp Python bindings
   - VAD (Voice Activity Detection) implementation
   - Swedish language optimization
   - WebSocket streaming (20ms chunks)

2. **NLU Implementation**
   - Intent classification (hybrid rule/LLM)
   - Swedish language patterns
   - Mood detection integration
   - Context awareness

3. **TTS Integration**
   - Piper voice synthesis
   - Swedish voice models
   - Mood-driven persona selection
   - Audio caching system

### Phase 3: Frontend & Integration (1-2 weeks)
**Priority**: User interface and system integration

1. **Next.js Frontend**
   - Voice interface with audio visualizer
   - Guardian status HUD
   - Real-time WebSocket communication
   - Responsive design (desktop/mobile)

2. **System Integration**
   - End-to-end voice pipeline testing
   - Guardian integration with brownout UX
   - Performance monitoring dashboard
   - Error handling and fallbacks

### Phase 4: Advanced Features (2-3 weeks)
**Priority**: Enhanced functionality

1. **LLM Orchestrator**
   - Model routing logic (Micro/Planner/Deep)
   - Resource-aware model selection
   - Tool registry with MCP integration
   - Fallback matrix implementation

2. **Memory & RAG**
   - FAISS vector store integration
   - Redis session management
   - Consent management system
   - Privacy-aware memory updates

3. **Tool Ecosystem**
   - Email integration (MCP)
   - Calendar management
   - Home Assistant connector
   - Vision pipeline (YOLO/SAM)

## 🛠️ Technical Debt & Missing Components

### Critical Missing Items
1. **Dependencies Management**
   - No package.json files in services/packages
   - Missing requirements.txt for Python services
   - No Docker configuration

2. **Implementation Files**
   - Guardian has structure but needs actual psutil integration
   - Voice service is completely missing
   - Frontend application doesn't exist

3. **Testing Infrastructure**
   - No test files or configuration
   - E2E test plan exists but no implementation
   - Missing CI/CD pipeline

4. **Development Environment**
   - No development scripts
   - Missing hot reload configuration
   - No debugging setup

### Environment Setup Blockers
```bash
# Current issues preventing startup:
1. Missing Python virtual environments
2. No npm/pnpm workspace dependencies installed  
3. Missing Whisper.cpp binary compilation
4. No Ollama model configuration
5. Missing Redis/database setup
```

## 🔧 Immediate Next Steps

### Step 1: Development Environment (Priority 1)
- [ ] Create Python virtual environments for each service
- [ ] Generate package.json with proper dependencies
- [ ] Install and configure development tools
- [ ] Set up hot reload for all services

### Step 2: Guardian Implementation (Priority 1)
- [ ] Complete psutil system monitoring
- [ ] Implement state machine with real thresholds
- [ ] Add graceful Ollama kill sequence
- [ ] Create health check endpoints

### Step 3: Voice Service Foundation (Priority 2)  
- [ ] FastAPI server with WebSocket support
- [ ] Placeholder endpoints for ASR/TTS
- [ ] Audio streaming infrastructure
- [ ] Integration with Guardian admission control

## 💡 Development Strategy

### Recommended Approach
1. **Incremental Implementation**: Start with skeleton services, add functionality gradually
2. **Test-Driven**: Implement E2E voice tests alongside development
3. **Guardian-First**: Ensure system safety before adding resource-intensive features
4. **Swedish Optimization**: Prioritize Swedish language support throughout

### Risk Mitigation
- Keep v1 system running during v2 development
- Implement circuit breakers and fallbacks early
- Monitor resource usage during development
- Maintain comprehensive documentation

## 🎯 Success Metrics

### Technical Metrics
- [ ] Voice pipeline E2E latency <2000ms
- [ ] Guardian prevents system crashes (0 incidents)
- [ ] All services start successfully with single command
- [ ] Frontend responsive on desktop/mobile

### User Experience Metrics  
- [ ] Swedish ASR accuracy >90%
- [ ] Natural voice synthesis with mood adaptation
- [ ] Graceful degradation during system stress
- [ ] Intuitive brownout feedback to users

---

**Alice v2 är redo för implementation! 🚀**

*Systemarkitekturen är komplett, nu behöver vi bara bygga komponenterna enligt blueprinten.*