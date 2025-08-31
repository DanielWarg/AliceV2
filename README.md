# Alice v2 AI Assistant
*Next-generation AI assistant with deterministic safety and real-time voice pipeline*

> **⚠️ Development Status**: This is a development repository. Components are under active development and not production-ready until all modules are complete.

## 🎯 Project Overview

Alice v2 is a modular AI assistant built with safety-first architecture featuring:

- **Deterministic Safety** - Guardian system with predictable state management
- **Real-time Voice** - ASR→NLU→LLM→TTS pipeline with Swedish language support  
- **Intelligent Routing** - Multi-model LLM orchestration based on system resources
- **Type-safe APIs** - Full TypeScript SDK with runtime validation
- **Professional Architecture** - Clean separation of concerns, monorepo structure

## 🏗️ Architecture

```
alice-v2/
├── services/           # Backend services (Python FastAPI)
│   ├── orchestrator/   # ✅ LLM routing & API gateway (Step 1 Complete)
│   ├── guardian/       # ✅ Safety system & resource monitoring  
│   └── voice/          # 🚧 ASR/TTS pipeline (Future)
├── packages/           # Shared TypeScript libraries
│   ├── types/          # ✅ API contracts & Zod schemas
│   ├── api/            # ✅ SDK with retry logic & circuit breaker
│   └── ui/             # 🚧 Design system (Future)
├── apps/               # Frontend applications
│   └── web/            # 🚧 Next.js interface (Future)
└── scripts/            # Development automation
```

## 🚀 Current Status

### ✅ Completed (Step 1/17)
- **Orchestrator Core** - FastAPI service with Guardian integration
- **TypeScript SDK** - Robust API client with error handling  
- **Shared Types** - Versioned contracts with Zod validation
- **Integration Tests** - 15 tests covering all endpoints
- **Development Scripts** - Automated startup/health checks

### 🚧 In Development  
- Following [17-step roadmap](ROADMAP.md) for systematic implementation
- Next: Step 2 (Guardian gatekeeper) + Step 3 (Observability)

## 🛠️ Quick Start

### Prerequisites
- Python 3.11+
- Node.js 18+ 
- pnpm 8+
- Docker & Docker Compose

### Development Setup

```bash
# Clone repository
git clone <repo-url>
cd alice-v2

# Install dependencies  
pnpm install

# Start infrastructure
docker compose up -d redis ollama

# Start Alice services
./scripts/dev-start.sh

# Verify health
./scripts/health-check.sh
```

### Service URLs
- **Orchestrator**: http://localhost:8000
- **Guardian**: http://localhost:8787  
- **API Docs**: http://localhost:8000/docs

## 📋 Development Workflow

### Required Before Every Commit
```bash
# Run all health checks
./scripts/health-check.sh

# Run integration tests
cd services/orchestrator && pytest src/tests/ -v

# Type checking
pnpm typecheck

# Build validation
pnpm build
```

### Development Commands
```bash
# Start all services
./scripts/dev-start.sh

# Health monitoring  
./scripts/health-check.sh

# Clean shutdown
./scripts/dev-stop.sh

# Run specific service
cd services/orchestrator
source .venv/bin/activate
uvicorn main:app --reload --port 8000
```

## 🔒 Safety & Guidelines

### Guardian System
- **Never** bypass Guardian admission control
- **Always** respect brownout/emergency states  
- **Monitor** resource usage in development
- **Test** failure scenarios regularly

### Code Standards
- **Strict TypeScript** - Zero tolerance for `any` types
- **Comprehensive Testing** - Unit + integration + E2E coverage
- **Structured Logging** - JSON format with trace correlation
- **API Versioning** - All requests include `"v": "1"` field

## 📊 System Metrics

### Performance Targets (Phase 1)
| Metric | Target | Status |
|--------|--------|--------|
| API Response Time (P95) | <100ms | ✅ ~60ms |
| Guardian Response | <150ms | ✅ ~80ms |
| Integration Test Success | 100% | ✅ 15/15 |
| Type Safety | 100% | ✅ Zero errors |

## 📚 Documentation

- **[Development Guide](AGENTS.md)** - Instructions for AI agents & developers
- **[Implementation Roadmap](ROADMAP.md)** - 17-step development plan  
- **[System Blueprint](ALICE_SYSTEM_BLUEPRINT.md)** - Complete architecture
- **[Testing Strategy](TESTING_STRATEGY.md)** - RealOps testing approach

## 🔧 Technology Stack

### Backend Services
- **FastAPI** - High-performance Python web framework
- **Pydantic** - Data validation and settings management
- **structlog** - Structured logging with JSON output
- **httpx** - Async HTTP client for service communication
- **pytest** - Testing framework with async support

### TypeScript SDK
- **Zod** - Runtime type validation
- **tsup** - Build tooling
- **Vitest** - Testing framework

### Infrastructure  
- **Docker Compose** - Service orchestration
- **Redis** - Session storage and caching
- **Ollama** - Local LLM server
- **Turbo** - Monorepo build system

## 🤝 Contributing

### Setup Development Environment
1. Follow Quick Start guide above
2. Read [AGENTS.md](AGENTS.md) for development guidelines
3. Ensure all tests pass before making changes
4. Use conventional commit messages

### Pull Request Process
1. Create feature branch from `main`
2. Implement changes with full test coverage
3. Run `./scripts/health-check.sh` and fix any issues
4. Submit PR with clear description

## 📜 License

This project is private and proprietary. Not licensed for public use.

## 🏃‍♀️ Next Steps

1. **Step 2**: Guardian gatekeeper with SLO hooks
2. **Step 3**: Observability with metrics and tracing
3. **Step 4**: NLU with Swedish language support
4. **Step 5**: Micro-LLM integration (Phi-3.5-Mini)

---

**Alice v2 - Building the future of AI assistance with safety and reliability first. 🤖**