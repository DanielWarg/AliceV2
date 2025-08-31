# Alice v2 AI Assistant
*Production-ready AI assistant with Guardian safety system and real-time brownout testing*

> **🚀 Production Status**: Core system completed with Guardian, SLO monitoring, load testing, and observability. Ready for deployment and operation.

## 🎯 Project Overview

Alice v2 is a robust, production-ready AI assistant featuring:

- **🛡️ Guardian Safety System** - Real-time health monitoring with NORMAL/BROWNOUT/EMERGENCY states
- **📊 SLO Monitoring** - P50/P95 latency tracking, error budget management, production-tight thresholds
- **⚡ Brownout Load Testing** - Complete stress testing suite validating ≤150ms trigger, ≤60s recovery
- **📈 Real-time Observability** - Streamlit HUD, JSONL logging, Guardian state visualization
- **🧪 Production Testing** - 20 realistic test scenarios, nightly validation, chaos engineering
- **🐳 Docker Orchestration** - Complete deployment stack with health checks and monitoring

## 🏗️ Architecture

```
alice-v2/
├── services/           # Backend services (Python FastAPI)
│   ├── orchestrator/   # ✅ LLM routing & API gateway  
│   ├── guardian/       # ✅ System health & admission control
│   └── loadgen/        # ✅ Brownout testing & SLO validation
├── monitoring/         # ✅ Streamlit HUD & observability
├── data/               # ✅ Telemetry & structured logging
├── scripts/            # ✅ Automation & deployment tools
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

# Run brownout load test
docker compose run --rm loadgen

# Start monitoring HUD
cd monitoring && ./start_hud.sh
# Dashboard available at: http://localhost:8501
```

## 📊 Production Features

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

### Observability & Monitoring
- **Real-time HUD**: Guardian state timeline, latency trends, error budget burn
- **Structured logging**: JSONL telemetry with PII masking
- **Nightly validation**: Automated testing with trend analysis
- **Status API**: `/api/status/simple`, `/api/status/routes`, `/api/status/guardian`

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

### Testing Strategy
- **Real integration tests** (no mocks) with 80-95% success rate expectations
- **Nightly validation** with 20 production scenarios
- **Chaos engineering** for resilience validation
- **SLO compliance tracking** with automatic alerting

## 📈 Monitoring & Operations

### Key Metrics
- **Guardian State**: NORMAL (green), BROWNOUT (yellow), EMERGENCY (red)
- **Route Latency**: P95 per micro/planner/deep routes
- **Error Budget**: 5xx rate, 429 rate over 5-minute windows
- **System Health**: RAM %, CPU %, temperature, battery

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

# Run load test validation
docker compose run --rm loadgen
```

## 📋 System Status

✅ **Guardian Safety System** - Production-ready with 5-point sliding window  
✅ **SLO Monitoring** - Real P50/P95 tracking with error budgets  
✅ **Brownout Testing** - Complete load generation suite  
✅ **Observability** - Streamlit HUD with real-time metrics  
✅ **Testing Framework** - 20 scenarios + nightly validation  
✅ **Docker Orchestration** - Health checks and dependencies  

## 🔗 Documentation

- **[AGENTS.md](AGENTS.md)** - AI coding agent context & development tips
- **[TESTING_STRATEGY.md](TESTING_STRATEGY.md)** - Comprehensive testing approach
- **[ALICE_SYSTEM_BLUEPRINT.md](ALICE_SYSTEM_BLUEPRINT.md)** - System architecture
- **[ROADMAP.md](ROADMAP.md)** - Future development plans
- **[monitoring/README.md](monitoring/README.md)** - HUD setup and usage

## 🤝 Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for development guidelines and [SECURITY.md](SECURITY.md) for security practices.

---

**Alice v2** - From prototype to production-ready AI assistant with comprehensive safety, monitoring, and validation. 🤖✨