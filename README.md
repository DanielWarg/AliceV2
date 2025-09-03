# Alice v2 AI Assistant
*Production-ready AI assistant with Guardian safety system, real-time observability, and autonomous E2E testing*

> **🚀 Production Status**: Auto-verify PASS 100% | P95 fast=81ms planner=224ms | Step 7: Hybrid Planner (OpenAI + Local)

## 🎯 Project Overview

Alice v2 is a robust, production-ready AI assistant featuring:

- **🛡️ Guardian Safety System** - Real-time health monitoring with NORMAL/BROWNOUT/EMERGENCY states
- **📊 Complete Observability** - RAM-peak per turn, energy tracking, tool error classification, structured JSONL logging
- **🧪 Autonomous E2E Testing** - Self-contained test suite with 20 scenarios, SLO validation, and automatic failure detection
- **🧠 NLU v1 (Swedish)** - e5-embeddings + heuristics, `/api/nlu/parse`, headers `X-Intent`/`X-Route-Hint`
- **📈 Real-time Monitoring** - Streamlit HUD with comprehensive metrics visualization
- **⚡ Brownout Load Testing** - Complete stress testing suite validating ≤150ms trigger, ≤60s recovery
- **🐳 Docker Orchestration** - Complete deployment stack with health checks and monitoring
- **🔧 Automated Setup** - One-command setup with `make up` including venv, dependencies, models, and testing

## 📚 Index (Solo Edition)
- Solo Quickstart – see below
- Demo Guide – see below
- Roadmap – `ROADMAP.md`
- Architecture – `ALICE_SYSTEM_BLUEPRINT.md`
- Rules/specs – `.cursor/rules/` (PRD, ADR, workflow, types, structured-outputs, toolselector, n8n)

## 🏗️ Architecture

```
alice-v2/
├── services/           # Backend services (Python FastAPI)
│   ├── orchestrator/   # ✅ LLM routing & API gateway with observability
│   ├── guardian/       # ✅ System health & admission control
│   ├── eval/           # ✅ Autonomous E2E testing harness
│   └── loadgen/        # ✅ Brownout testing & SLO validation
├── monitoring/         # ✅ Observability tools (Streamlit scripts)
├── data/               # ✅ Telemetry & structured logging
├── scripts/            # ✅ Autonomous E2E test automation
└── test-results/       # ✅ Nightly validation & trends
```

### Architecture at a glance (Solo Edition)
- Fast-route for time/weather/memory/smalltalk (utan LLM i loopen)
- Hybrid Planner: OpenAI primary + local ToolSelector fallback
- Tool enum-only schema: model väljer verktyg, args byggs deterministiskt i kod
- n8n för tunga/asynkrona jobb via säkrade webhooks
- Guardian skyddar med brownout/circuit‑breakers + OpenAI policies (rate limit, cost budget)
- User opt-in för cloud processing (cloud_ok flag)

## 🚀 Quick Start

### Prerequisites
- Docker Desktop (installed and running)
- Python 3.11+ (for local development)
- pnpm (for frontend: `npm install -g pnpm`)
- Ollama (for local models: https://ollama.ai)

### 🚀 First Time Setup

**For new users - run this ONCE:**

```bash
# 1. Install prerequisites
brew install python@3.11 pnpm  # macOS
# or: sudo apt install python3.11 pnpm  # Ubuntu

# 2. Install Docker Desktop
# Download from: https://www.docker.com/products/docker-desktop/

# 3. Install Ollama
curl -fsSL https://ollama.ai/install.sh | sh

# 4. Start Docker Desktop and Ollama
# Docker Desktop: Start the app
# Ollama: ollama serve (runs automatically on macOS)

# 5. Clone the project
git clone https://github.com/your-repo/alice-v2.git
cd alice-v2

# 6. Set environment variables (optional)
export N8N_ENCRYPTION_KEY=change-me
export OPENAI_API_KEY=sk-your-key-here  # When we implement OpenAI

# 7. Start everything!
make up
```

**After the first time, just run:**
```bash
git pull
make up
```

### 🎯 One-Command Setup (Recommended)
```bash
# Clone and enter directory
git clone <repository>
cd alice-v2

# Start everything automatically (venv + deps + models + stack + tests)
make up

# Run all tests to verify everything works
make test-all

# Access HUD
open http://localhost:3001
```

## ⚡ Solo Quickstart (Local Lite)
```bash
# 1) Start kärnorna
docker compose up -d guardian orchestrator nlu dev-proxy ollama n8n-db n8n

# 2) Sanity via proxy
curl -s http://localhost:18000/health | jq .
curl -s http://localhost:18000/api/status/routes | jq .

# 3) N8N UI (aktivera flöden: email_draft, calendar_draft, batch_rag)
open http://localhost:5678

# 4) Snabb test (fast-route)
curl -s -X POST http://localhost:18000/api/chat \
  -H 'Content-Type: application/json' -H 'Authorization: Bearer test-key-123' \
  -d '{"v":"1","session_id":"fast-1","lang":"sv","message":"Vad är klockan?"}' | jq .

# 5) Email draft via webhook (efter att flow aktiverats)
curl -s -u alice:secret -H 'Content-Type: application/json' \
  -d '{"request_id":"t1","subject":"Demo","to":["anna@example.com"]}' \
  http://localhost:18000/webhook/email_draft | jq .
```

### n8n – Import & Troubleshooting

```bash
# Login (first time):
#   UI: http://localhost:5678
#   Create account with email (Basic Auth disabled)
#   After setup: import flows and activate

# Import flows in UI
# 1) Open UI → Workflows → Import from file → select:
#    services/n8n/flows/email_draft.json
#    services/n8n/flows/calendar_draft.json
#    services/n8n/flows/batch_rag.json
# 2) Activate each workflow (toggle: Active)

# Verify REST (lists workflows)
curl -s -u alice:secret http://localhost:5678/rest/workflows | jq .

# Quick health check of n8n
curl -s http://localhost:5678/healthz

# Troubleshooting (ERR_CONNECTION_REFUSED):
# - Ensure port mapping in docker-compose (ports: "5678:5678")
# - Restart service: docker compose up -d n8n
# - Read logs: docker logs alice-n8n --tail 200
# - Check env in container: docker inspect alice-n8n
#   (N8N_HOST=localhost, N8N_PROTOCOL=http, N8N_EDITOR_BASE_URL=http://localhost:5678)
```

### 🔧 Troubleshooting

**Common problems and solutions:**

```bash
# Port 18000 already in use
./scripts/ports-kill.sh

# Docker containers won't start
docker compose down --remove-orphans
docker compose up -d

# Ollama models missing
ollama pull qwen2.5:3b
ollama pull phi3:mini

# n8n UI not accessible
# Check if n8n container is running:
docker compose ps n8n
# If not: docker compose up -d n8n

# Frontend (HUD) won't start
cd apps/hud && pnpm install && pnpm dev

# All tests fail
make down
make up
sleep 30  # Wait for everything to be healthy
make test-all
```

**Logs and debugging:**
```bash
# View all logs
docker compose logs -f

# View specific service
docker compose logs -f orchestrator

# HUD (real-time monitoring)
open http://localhost:3001
```

### 🔧 Manual Setup (Alternative)
```bash
# Clone and enter directory
git clone <repository>
cd alice-v2

# Start core services via proxy
docker compose up -d guardian orchestrator nlu dev-proxy

# Verify via proxy
curl http://localhost:18000/health
curl http://localhost:18000/api/status/simple

# Run autonomous E2E test (validates everything)
./scripts/auto_verify.sh

# HUD
open http://localhost:3001
```

### 🧪 Development Workflow
```bash
# Complete development workflow (up + all tests)
make dev

# Quick development workflow (up + e2e only)
make dev-quick

# Run specific test suites
make test-unit      # Unit tests only
make test-e2e       # E2E tests only
make test-integration # Integration tests only
```

### 🛠️ Available Commands
```bash
make help           # Show all available commands
make up             # Start development stack (auto-setup)
make down           # Stop development stack
make restart        # Restart development stack
make test-all       # Run complete test suite
make clean          # Clean generated files
make fetch-models   # Download required models
```

## 🎯 Solo Edition (Local Lite)

- Fast-route: time/weather/memory/smalltalk utan LLM i loopen
- Hybrid Planner: OpenAI primary + local ToolSelector fallback
- Tool enum-only schema: model väljer verktyg, args byggs deterministiskt i kod
- n8n för tunga jobb (email_draft, calendar_draft, scrape_and_summarize, batch_rag) via säkrade webhooks
- Röst: Whisper.cpp (STT) + Piper (sv‑SE) för TTS
- SLO (solo): fast-route p95 ≤ 250 ms; planner p95 ≤ 900 ms; n8n email_draft p95 ≤ 10 s
- Cost budget: ≤$3/day för OpenAI; user opt-in för cloud processing

## 🎬 Demo Guide (3 scenarier)
1) Boka möte i morgon 14:00
   - Förväntan: confirmation‑kort (JSON‑plan), därefter n8n `calendar_draft` svar
2) Vad sa vi om leveransen?
   - Förväntan: memory.query + kort RAG‑citat i svaret
3) Läs upp det
   - Förväntan: TTS via Piper (svenska)

### Daily Automation (14:00)
```bash
# Install cron job to run auto-verify daily at 14:00 and log to logs/auto_verify.log
chmod +x scripts/setup-cron.sh
./scripts/setup-cron.sh
crontab -l | grep auto_verify
```

## ✅ Quick checklist (daily)

### Completed

- [x] Observability + eval-harness v1
- [x] Security v1 (baseline)
- [x] NLU v1 (Swedish, embeddings)
- [x] **Automated setup with `make up`**
- [x] **Comprehensive test suite with `make test-all`**
- [x] **Repository hygiene and cleanup**

### Next steps

#### Step 4 – NLU + XNLI
- [ ] Export XNLI to ONNX (int8) → `models/xnli/`
- [ ] Connect entailment for low margin in NLU
- [ ] Add 4–6 challenging test scenarios to eval-harness
- [ ] Intent accuracy ≥92%, P95 ≤80ms

#### Step 5 – Micro-LLM (Phi-3.5-mini via Ollama)
- [ ] Enable micro-driver in `/api/chat`
- [ ] Set `X-Route=micro` for simple intents
- [ ] Measure P95 <250ms (first token)

#### Step 6 – Memory (Redis TTL + FAISS user memory)
- [ ] Session memory TTL=7 days
- [ ] FAISS hot/cold index config (HNSW+ondisk)
- [ ] "Forget me" <1s tested in eval

#### Step 7 – Planner-LLM (Qwen 7B-MoE + MCP tools)
- [ ] Tool schema (pydantic) + tool-firewall
- [ ] Eval with 1–2 tool-calls/flow
- [ ] Tool success ≥95%

#### Step 8 – Text E2E hard test
- [ ] Fast: P95 ≤250ms
- [ ] Planner: P95 ≤900ms (first) / ≤1.5s (full)

## 🔧 Development
## 📦 Release Tags

- `v2.7.0-planner-hardening`: Deterministic JSON planner via Ollama (format=json), strict budgets (600/400/150/1500ms), circuit breakers, fast fallback; telemetry gating and per-route SLOs added to auto_verify; docs updated from artifacts.


### Local Development
```bash
# Start services
docker compose up -d guardian orchestrator

# Development environment
cd services/orchestrator
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# Test
curl http://localhost:8000/api/status/simple
curl http://localhost:8787/health

# Run validation
./scripts/auto_verify.sh

# Monitor
cd monitoring && streamlit run mini_hud.py
```

### Testing Strategy
- **E2E Testing**: `./scripts/auto_verify.sh` - Complete system validation
- **Unit Testing**: `pytest` with realistic expectations (80-95% success rates)
- **Load Testing**: `services/loadgen/main.py` - Brownout validation
- **Monitoring**: Real-time HUD with comprehensive metrics

## 📊 Monitoring & Observability

### Real-time Dashboard
```bash
# Start HUD
cd monitoring && streamlit run mini_hud.py

# Or via proxy
open http://localhost:18000/hud
```

### Key Metrics
- **Performance**: P50/P95 latency per route, RAM peak per turn
- **Reliability**: Guardian state, error rates, SLO compliance
- **Security**: Injection attempts, tool denials, security mode
- **Quality**: Intent accuracy, tool success rates, eval pass rates

### Data Collection
- **Telemetry**: Structured JSONL logging under `data/telemetry/`
- **Test Results**: E2E validation artifacts under `data/tests/`
- **Trends**: Nightly validation trends under `test-results/`

## 🛡️ Security Features

- **Guardian System**: Real-time health monitoring with automatic brownout
- **Injection Detection**: Pattern-based injection attempt detection
- **Tool Firewall**: Configurable tool access control
- **Security Policy**: YAML-based security configuration

## 📚 Documentation

- **`ROADMAP.md`** - Live milestone tracker with test gates
- **`ALICE_SYSTEM_BLUEPRINT.md`** - System architecture and design decisions
- **`AGENTS.md`** - Instructions for AI coding agents
- **`TESTING_STRATEGY.md`** - Comprehensive testing approach
- **`SECURITY.md`** - Security architecture and policies

## 🤝 Contributing

See `CONTRIBUTING.md` for development guidelines and contribution process.

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

---

**🤖 Built with Claude Code - Alice v2 observability + eval-harness v1 complete! 🚀**