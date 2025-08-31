# Alice v2 AI Assistant
*Production-ready AI assistant with Guardian safety system, real-time observability, and autonomous E2E testing*

> **🚀 Production Status**: Complete observability + eval-harness v1 system with autonomous E2E testing, RAM/energy tracking, tool error classification, and comprehensive monitoring. Ready for production deployment.

## 🎯 Project Overview

Alice v2 is a robust, production-ready AI assistant featuring:

- **🛡️ Guardian Safety System** - Real-time health monitoring with NORMAL/BROWNOUT/EMERGENCY states
- **📊 Complete Observability** - RAM-peak per turn, energy tracking, tool error classification, structured JSONL logging
- **🧪 Autonomous E2E Testing** - Self-contained test suite with 20 scenarios, SLO validation, and automatic failure detection
- **📈 Real-time Monitoring** - Streamlit HUD with comprehensive metrics visualization
- **⚡ Brownout Load Testing** - Complete stress testing suite validating ≤150ms trigger, ≤60s recovery
- **🐳 Docker Orchestration** - Complete deployment stack with health checks and monitoring

## 🏗️ Architecture

```
alice-v2/
├── services/           # Backend services (Python FastAPI)
│   ├── orchestrator/   # ✅ LLM routing & API gateway with observability
│   ├── guardian/       # ✅ System health & admission control
│   ├── eval/           # ✅ Autonomous E2E testing harness
│   └── loadgen/        # ✅ Brownout testing & SLO validation
├── monitoring/         # ✅ Streamlit HUD & observability dashboard
├── data/               # ✅ Telemetry & structured logging
├── scripts/            # ✅ Autonomous E2E test automation
└── test-results/       # ✅ Nightly validation & trends
```

## 🚀 Quick Start

### Prerequisites
- Docker & Docker Compose
- Python 3.11+ (for local development)

### Deploy Full Stack
```bash
# Clone and enter directory
git clone <repository>
cd alice-v2

# Start core services
docker compose up -d guardian orchestrator

# Verify system health
curl http://localhost:8000/api/status/simple
curl http://localhost:8787/health

# Run autonomous E2E test (validates everything)
./scripts/auto_verify.sh

# Start monitoring HUD
cd monitoring && ./start_hud.sh
# Dashboard available at: http://localhost:8501
```

## 📊 Production Features

### Complete Observability System
- **RAM-peak per turn**: Process and system memory tracking in every turn event
- **Energy per turn (Wh)**: Energy consumption measurement with configurable baseline
- **Tool error classification**: Timeout/5xx/429/schema/other categorization with Prometheus metrics
- **Structured turn events**: Comprehensive JSONL logging with all metrics and metadata
- **Real-time dashboard**: Streamlit HUD showing RAM, energy, latency, tool errors, and Guardian status

### Autonomous E2E Testing
- **Self-contained validation**: `scripts/auto_verify.sh` runs complete system validation
- **20 realistic scenarios**: Swedish conversation patterns covering micro/planner/deep routes
- **SLO validation**: Automatic P95 threshold checking with Node.js integration
- **Failure detection**: Exits with code 1 on SLO breaches or <80% pass rate
- **Artifact preservation**: All test results saved to `data/tests/` and `test-results/`

### Guardian Safety System
- **5-point sliding window** monitoring RAM/CPU with 80%/92% soft/hard triggers
- **60-second recovery hysteresis** preventing oscillation
- **State machine**: NORMAL → BROWNOUT → EMERGENCY → NORMAL
- **Admission control** protecting system during resource pressure

### SLO Monitoring & Validation
- **Real-time metrics**: P50/P95 latency per route (micro/planner/deep)
- **Error budget tracking**: 5xx/429 rates over 5-minute sliding windows
- **Production thresholds**: 250ms/1.5s/3s P95 budgets by route complexity
- **Brownout SLO**: ≤150ms trigger latency, ≤60s recovery time

### Load Testing & Chaos Engineering
- **5 stress modules**: Deep-LLM, Memory balloon, CPU spin, Tool storm, Vision RTSP
- **Real brownout validation**: Measure actual trigger/recovery against SLO
- **Chaos engineering**: Network partitions, resource exhaustion, gradual degradation
- **20 production scenarios**: Realistic Swedish conversation patterns

## 🔧 Development

### Local Development
```bash
# Install dependencies
cd services/orchestrator && python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# Run tests
pytest src/tests/ -v

# Start local development
uvicorn main:app --reload --port 8000
```

### Autonomous Testing
```bash
# Run complete E2E validation
./scripts/auto_verify.sh

# Run eval harness only
cd services/eval && source .venv/bin/activate && python eval.py

# Start mini-HUD for monitoring
cd monitoring && streamlit run mini_hud.py
```

### Testing Strategy
- **Real integration tests** (no mocks) with 80-95% success rate expectations
- **Autonomous E2E validation** with 20 production scenarios
- **SLO compliance tracking** with automatic alerting
- **Chaos engineering** for resilience validation

## 📈 Monitoring & Operations

### Key Metrics
- **Guardian State**: NORMAL (green), BROWNOUT (yellow), EMERGENCY (red)
- **Route Latency**: P95 per micro/planner/deep routes
- **RAM Peak**: Per-turn memory usage tracking
- **Energy Consumption**: Wh per turn with baseline calibration
- **Tool Errors**: Classified error rates (timeout/5xx/429/schema/other)
- **Error Budget**: 5xx rate, 429 rate over 5-minute windows

### Production Endpoints
- **Health**: `GET /health` - Service status
- **Metrics**: `GET /api/status/simple` - Complete system snapshot
- **Guardian**: `GET /api/status/guardian` - Current safety status
- **Routes**: `GET /api/status/routes` - Latency breakdown by route

### Deployment
```bash
# Production deployment
docker compose up -d

# Scale services (if needed)
docker compose up --scale orchestrator=3

# Monitor logs
docker compose logs -f guardian orchestrator

# Run autonomous validation
./scripts/auto_verify.sh
```

## 📋 System Status

✅ **Complete Observability** - RAM-peak, energy tracking, tool error classification  
✅ **Autonomous E2E Testing** - Self-contained validation with 20 scenarios  
✅ **Guardian Safety System** - Production-ready with 5-point sliding window  
✅ **SLO Monitoring** - Real P50/P95 tracking with error budgets  
✅ **Brownout Testing** - Complete load generation suite  
✅ **Real-time HUD** - Streamlit dashboard with comprehensive metrics  
✅ **Structured Logging** - JSONL telemetry with PII masking  
✅ **Docker Orchestration** - Health checks and dependencies  

## 🔗 Documentation

- **[AGENTS.md](AGENTS.md)** - AI coding agent context & development tips
- **[TESTING_STRATEGY.md](TESTING_STRATEGY.md)** - Comprehensive testing approach
- **[ALICE_SYSTEM_BLUEPRINT.md](ALICE_SYSTEM_BLUEPRINT.md)** - System architecture
- **[ROADMAP.md](ROADMAP.md)** - Future development plans
- **[LOOSE_THREADS.md](LOOSE_THREADS.md)** - Operational polish and production readiness
- **[monitoring/README.md](monitoring/README.md)** - HUD setup and usage

## 🤝 Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for development guidelines and [SECURITY.md](SECURITY.md) for security practices.

---

**Alice v2** - From prototype to production-ready AI assistant with comprehensive safety, monitoring, validation, and autonomous testing. 🤖✨