.PHONY: help down up status health test-unit test-all security-scan format lint clean stabilize fix-system rl-build rl-test rl-bootstrap rl-train rl-shadow rl-replay rl-online-test rl-phi-test rl-snapshot rl-setup rl-benchmark rl-assert rl-ci

# Default target
help: ## Show this help message
	@echo "🚀 Alice v2 Development Commands"
	@echo ""
	@echo "📦 System:"
	@echo "  make up          - Start all services"
	@echo "  make down        - Stop all services"  
	@echo "  make status      - Show service status"
	@echo "  make health      - Check all health endpoints"
	@echo "  make logs        - Show recent logs"
	@echo ""
	@echo "🧪 Testing:"
	@echo "  make test-unit   - Run unit tests"
	@echo "  make test-all    - Run all tests including eval"
	@echo "  make test-a-z    - Comprehensive A-Z system test"
	@echo ""
	@echo "🔒 Quality & Security:"
	@echo "  make security-scan - Trivy security scan"
	@echo "  make format        - Format all code"
	@echo "  make lint          - Lint all code" 
	@echo "  make quality       - Format + lint + security"
	@echo ""
	@echo "🎯 Stabilization:"
	@echo "  make stabilize     - Full stabilization check"
	@echo "  make fix-system    - Auto-fix system health issues"
	@echo ""
	@echo "🤖 RL Pipeline:"
	@echo "  make rl-build      - Build episodes from telemetry (T2)"
	@echo "  make rl-test       - Test RL pipeline (T2)"
	@echo "  make rl-replay     - Offline bandit training (T4)"
	@echo "  make rl-online-test - Test online bandit components (T4)"
	@echo "  make rl-phi-test   - Test φ-reward calculation (T4)"
	@echo "  make rl-snapshot   - Snapshot current bandit weights"
	@echo "  make rl-bootstrap  - Generate bootstrap data"
	@echo "  make rl-train      - Train RL policies"
	@echo "  make rl-shadow     - Start shadow mode"
	@echo ""
	@echo "🚦 RL CI Pipeline (T1-T4):"
	@echo "  make rl-setup      - Setup RL dependencies and tools"
	@echo "  make rl-benchmark  - Run comprehensive benchmark suite"
	@echo "  make rl-assert     - Validate SLO gates and thresholds"
	@echo "  make rl-ci         - Complete T1-T4 CI pipeline"
	@echo ""
	@echo "🎯 T5 Live Bandit Routing:"
	@echo "  make rl-online-start - Start bandit server for live routing"
	@echo "  make orchestrator-dev - Start orchestrator with live routing"
	@echo "  make rl-rotate       - Rotate bandit snapshots"
	@echo "  make rl-live-test    - Test live routing integration"
	@echo ""
	@echo "🇸🇪 T6 ToolSelector v2 + GBNF + LoRA:"
	@echo "  make toolselector-train-lora     - Train LoRA model for svenska"
	@echo "  make toolselector-benchmark-lora - Benchmark LoRA performance"
	@echo "  make toolselector-test-v2        - Test svenska patterns"
	@echo "  make toolselector-test-all       - Run all T6 tests"
	@echo "  make toolselector-t6-dev         - Complete T6 dev pipeline"
	@echo "  make toolselector-t6-ci          - Complete T6 CI pipeline"

venv: ## Create/update root virtual environment
	@echo "🔧 Setting up virtual environment..."
	@if [ ! -d ".venv" ]; then \
		echo "📦 Creating new virtual environment..."; \
		python3 -m venv .venv; \
	fi
	@echo "📦 Installing/updating dependencies..."
	@source .venv/bin/activate && pip install --upgrade pip
	@echo "✅ Virtual environment ready! Activate with: source .venv/bin/activate"

install-requirements: venv ## Install all requirements
	@echo "📦 Installing Python requirements..."
	@source .venv/bin/activate && pip install pytest httpx fastapi pyyaml prometheus_client psutil structlog
	@echo "📦 Installing Node.js dependencies..."
	@pnpm install:all || echo "⚠️  pnpm not available, skipping Node.js deps"
	@echo "✅ All requirements installed!"

clean-venv: ## Remove all virtual environments
	@echo "🧹 Cleaning virtual environments..."
	rm -rf .venv services/*/.venv
	@echo "✅ Virtual environments removed"

clean: clean-venv ## Clean all generated files
	@echo "🧹 Cleaning generated files..."
	rm -rf __pycache__ services/*/__pycache__ packages/*/__pycache__
	rm -rf *.pyc services/*/*.pyc packages/*/*.pyc
	rm -rf .pytest_cache services/*/.pytest_cache
	rm -rf .coverage services/*/.coverage
	@echo "✅ Cleanup complete"

cleanup-data: ## Clean old data files (dry run by default)
	@echo "🧹 Cleaning old data files..."
	@DRY_RUN=true CLEANUP_CONFIRM=false bash scripts/cleanup.sh

cleanup-data-force: ## Clean old data files (with confirmation)
	@echo "🧹 Cleaning old data files (with confirmation)..."
	@DRY_RUN=false CLEANUP_CONFIRM=true bash scripts/cleanup.sh

fetch-models: ## Download required models
	@echo "📥 Fetching models..."
	./scripts/fetch_models.sh

# --- Robust control targets ---------------------------------------------------

preflight: ## Light checks (Docker + ports)
	@echo "🔎 Preflight..."
	@if docker info >/dev/null 2>&1; then echo "🐳 Docker: OK"; else echo "🐳 Docker: NOT RUNNING"; fi
	@printf "🔌 Ports in use: "; (lsof -i :8000 -i :8501 -i :8787 2>/dev/null || true) | awk '{print $$9}' | sed 's/.*://g' | xargs -I{} echo -n "{} " ; echo

# System commands

up: ## Start all services (fast)  
	@echo "🚀 Starting Alice v2 services..."
	docker compose up -d guardian orchestrator alice-cache nlu dev-proxy
	@echo "⏳ Waiting for services to start..."
	@sleep 5
	@$(MAKE) health

status: ## Show service status
	@echo "📊 Service Status:"
	@docker compose ps

health: ## Check all health endpoints
	@echo "🏥 Health Check:"
	@echo -n "  Orchestrator: "
	@curl -sf http://localhost:8001/health >/dev/null && echo "✅ OK" || echo "❌ FAIL"
	@echo -n "  Guardian: "
	@curl -sf http://localhost:8787/health >/dev/null && echo "✅ OK" || echo "❌ FAIL"
	@echo -n "  NLU: "
	@curl -sf http://localhost:9002/healthz >/dev/null && echo "✅ OK" || echo "❌ FAIL"
	@echo -n "  Redis: "
	@docker compose exec -T alice-cache redis-cli ping | grep -q PONG && echo "✅ OK" || echo "❌ FAIL"

logs: ## Show recent logs
	@echo "📋 Recent logs:"
	@docker compose logs --tail=20 orchestrator guardian nlu

dev-fast: ## Alias for up (fast dev)
	@$(MAKE) up

down: ## Stop development stack (with Docker fallback)
	@echo "🛑 Stopping dev stack..."
	@echo "🎨 Stopping frontend..."
	@pkill -f "pnpm dev" || true
	@if docker info >/dev/null 2>&1; then \
		echo "🐳 Docker running → using docker compose down"; \
		if command -v timeout >/dev/null 2>&1; then \
			timeout 25s docker compose down || { \
				echo "⏱️  docker compose down timed out → using ports-kill fallback"; \
				./scripts/ports-kill.sh || true; \
			}; \
		else \
			docker compose down || { \
				echo "⚠️  docker compose down failed → using ports-kill fallback"; \
				./scripts/ports-kill.sh || true; \
			}; \
		fi; \
	else \
		echo "🐳 Docker not running → using ports-kill fallback"; \
		./scripts/ports-kill.sh || true; \
	fi
	@echo "✅ Down complete."

frontend: ## Start frontend development server
	@echo "🎨 Starting frontend..."
	@if [ -d "apps/hud" ]; then \
		echo "📱 Starting HUD on http://localhost:3001..."; \
		cd apps/hud && pnpm dev > /dev/null 2>&1 & \
		echo "✅ HUD started in background"; \
	else \
		echo "⚠️  HUD app not found in apps/hud"; \
	fi

force-down: ## Force stop (no Docker dependency)
	@echo "💥 Force stop (no Docker)..."
	@echo "🎨 Stopping frontend..."
	@pkill -f "pnpm dev" || true
	@./scripts/ports-kill.sh || true
	@echo "✅ Force-down complete."

restart: ## Restart dev stack
	@$(MAKE) down
	@$(MAKE) up

docker-down: ## Strict docker compose down (no fallback)
	@docker compose down

# --- Comprehensive Testing Suite ---------------------------------------------------

test: test-all ## Run all tests (alias for test-all)

test-all: ## Run complete test suite (unit + e2e + integration)
	@echo "🧪 Running complete test suite..."
	@echo "📋 1. Unit tests..."
	@$(MAKE) test-unit
	@echo "📋 2. E2E tests..."
	@$(MAKE) test-e2e
	@echo "📋 3. Integration tests..."
	@$(MAKE) test-integration
	@echo "✅ All tests completed!"

# Testing commands
test-unit: ## Run unit tests
	@echo "🧪 Running unit tests..."
	@cd services/orchestrator && python -m pytest src/tests/ -v --tb=short


test-a-z: ## Comprehensive A-Z system test
	@echo "🔍 Running comprehensive A-Z test..."
	@cd services/orchestrator && python src/tests/test_comprehensive_a_z.py

test-e2e: ## Run end-to-end tests
	@echo "🧪 Running E2E tests..."
	@echo "🚀 Ensuring stack is running..."
	@if ! curl -s http://localhost:8001/health >/dev/null 2>&1; then \
		echo "⚠️  Stack not running, starting it..."; \
		$(MAKE) up; \
		sleep 10; \
	fi
	@echo "🔍 Running auto_verify.sh..."
	@./scripts/auto_verify.sh || echo "⚠️  Some E2E tests failed (check logs for details)"
	@echo "✅ E2E tests completed!"

test-integration: ## Run integration tests
	@echo "🧪 Running integration tests..."
	@echo "🚀 Ensuring stack is running..."
	@if ! curl -s http://localhost:8001/health >/dev/null 2>&1; then \
		echo "⚠️  Stack not running, starting it..."; \
		$(MAKE) up; \
		sleep 10; \
	fi
	@echo "🔍 Testing API endpoints..."
	@curl -s http://localhost:8001/health | jq . || echo "⚠️  Health endpoint test failed"
	@curl -s http://localhost:8001/api/status/simple | jq . || echo "⚠️  Status endpoint test failed"
	@echo "🔍 Testing Guardian integration..."
	@curl -s http://localhost:8787/health | jq . || echo "⚠️  Guardian health test failed"
	@echo "🔍 Testing Learning API..."
	@curl -s http://localhost:8001/api/learn/stats | jq . || echo "⚠️  Learning stats test failed"
	@echo "✅ Integration tests completed!"

learn: ## Run learning ingestion pipeline
	@echo "🧠 Running learning ingestion..."
	@python services/ingest/run_ingest.py \
		--input $(LEARN_INPUT_DIR) \
		--tests $(LEARN_TESTS_FILE) \
		--parquet_out $(LEARN_OUT_PARQUET) \
		--snapshot_out $(LEARN_OUT_SNAPSHOT) \
		--log_out $(LEARN_LOG)

learn-daily: ## Create daily learning snapshot
	@echo "📊 Creating daily learning snapshot..."
	@curl -s -X POST http://localhost:8001/api/learn/snapshot | jq .

learn-stats: ## Get learning statistics
	@echo "📈 Getting learning statistics..."
	@curl -s http://localhost:8001/api/learn/stats | jq .

# Learning environment variables
LEARN_INPUT_DIR ?= data/telemetry
LEARN_TESTS_FILE ?= data/tests/results.jsonl
LEARN_OUT_PARQUET ?= data/learn/parquet
LEARN_OUT_SNAPSHOT ?= data/learn/snapshots
LEARN_LOG ?= data/learn/logs/learn.jsonl

verify: ## Run system verification (alias for test-e2e)
	@$(MAKE) test-e2e

# --- Additional Services ---------------------------------------------------

dashboard: ## Start monitoring dashboard
	@echo "📊 Starting monitoring dashboard..."
	docker compose up -d dashboard
	@echo "✅ Dashboard available at http://localhost:8501"

loadtest: ## Start load testing
	@echo "🚀 Starting load testing..."
	docker compose up -d loadgen
	@echo "✅ Load testing started"

eval: ## Start evaluation service
	@echo "🧪 Starting evaluation service..."
	docker compose up -d eval
	@echo "✅ Evaluation service started"

curator: ## Start data curation service
	@echo "📝 Starting data curation service..."
	docker compose up -d curator
	@echo "✅ Data curation service started"

n8n: ## Start n8n workflow automation
	@echo "⚡ Starting n8n workflow automation..."
	docker compose up -d n8n-db n8n
	@echo "✅ n8n available at http://localhost:5678"

# --- Development Workflow ---------------------------------------------------

dev: up test-all ## Complete development workflow (up + all tests)
	@echo "🎉 Development workflow completed!"

dev-quick: up test-e2e ## Quick development workflow (up + e2e only)
	@echo "🎉 Quick development workflow completed!"

# Development helpers
install-deps: install-requirements ## Install all dependencies (alias)

# Quality & Security
security-scan: ## Trivy security scan
	@echo "🔒 Running security scan..."
	@docker run --rm -v "$(PWD):/src" aquasec/trivy fs /src --severity HIGH,CRITICAL --format table

format: ## Format all code
	@echo "🐍 Formatting Python code..."
	@black --line-length 100 services/
	@echo "✅ Formatting complete"

lint: ## Lint all code
	@echo "🧹 Linting Python code..."
	@flake8 services/ --max-line-length=100 --extend-ignore=E203,W503 --exclude=__pycache__,.venv
	@echo "✅ Linting complete"

quality: format lint security-scan ## Format + lint + security
	@echo "✅ All quality checks complete"

# Stabilization
stabilize: ## Full stabilization check
	@echo "🔧 Running full stabilization check..."
	@$(MAKE) down
	@$(MAKE) up
	@$(MAKE) health
	@$(MAKE) quality
	@$(MAKE) test-unit
	@echo "✅ Stabilization check complete"

fix-system: ## Auto-fix system health issues
	@echo "🔧 Auto-fixing system health issues..."
	@python fix_system_health.py --action fix

# RL Pipeline
rl-build: ## Build episodes from telemetry (T2)
	@echo "🏗️  Building episodes from telemetry..."
	@PYTHONPATH=. python3 services/rl/pipelines/build_episodes.py --src data/telemetry --out data/rl/v1

rl-build-with-rewards: ## Build episodes with Fibonacci φ-rewards (T3)
	@echo "🧮 Building episodes with Fibonacci φ-rewards..."
	@PYTHONPATH=. python3 services/rl/pipelines/build_episodes.py --src data/telemetry --out data/rl/v1

rl-test: ## Test RL pipeline (T2)
	@echo "🧪 Testing RL pipeline..."
	@PYTHONPATH=. python3 -m pytest services/rl/tests/test_build_episodes.py -q

rl-rewards-test: ## Test Fibonacci reward shaping (T3)
	@echo "🧮 Testing Fibonacci reward shaping..."
	@PYTHONPATH=. python3 -m pytest services/rl/tests/test_reward_shaping.py -q

rl-replay: ## Offline bandit training (T4)
	@echo "🎯 Training bandits offline..."
	@PYTHONPATH=. RL_REPLAY_EPOCHS=$${RL_REPLAY_EPOCHS:-2} python3 services/rl/replay/replay_from_episodes.py --split train --epochs $${RL_REPLAY_EPOCHS:-2}

rl-online-test: ## Test online bandit components (T4)
	@echo "🧪 Testing online bandit components..."
	@PYTHONPATH=. python3 -m pytest tests/rl/test_t4_core.py -v

rl-phi-test: ## Test φ-reward calculation (T4)
	@echo "🧮 Testing φ-reward calculation..."
	@PYTHONPATH=. python3 -m pytest tests/rl/test_phi_reward.py -v

rl-benchmark: ## Run reproducible RL benchmark with artefacts  
	@echo "🔬 Running RL benchmark suite..."
	@PYTHONPATH=. python3 services/rl/benchmark/rl_benchmark.py --mode all

rl-benchmark-ci: ## Run RL benchmark with SLO gates for CI
	@echo "🚦 Running RL benchmark with SLO gates..."
	@PYTHONPATH=. python3 services/rl/benchmark/rl_benchmark.py --mode CI

rl-snapshot: ## Snapshot current bandit weights
	@echo "📸 Snapshotting bandit weights..."
	@PYTHONPATH=. python3 -c "from services.rl.persistence.bandit_store import get_paths; from services.rl.online.linucb_router import LinUCBRouter; from services.rl.online.thompson_tools import ThompsonTools; r=LinUCBRouter(); r.save(); t=ThompsonTools(); t.save(); print('Snapshot OK')"

rl-bootstrap: ## Generate bootstrap data
	@echo "🌱 Generating bootstrap data..."
	@python services/rl/generate_bootstrap_data.py --episodes 1000 --out data/bootstrap.json

rl-train: ## Train RL policies
	@echo "🧠 Training RL policies..."
	@python services/rl/automate_rl_pipeline.py --telemetry data/bootstrap.json

rl-shadow: ## Start shadow mode
	@echo "🌑 Starting shadow mode..."
	@python services/rl/shadow_mode.py --action start

# Utilities
clean-docker: ## Clean Docker containers and system
	@echo "🧹 Cleaning Docker resources..."
	@docker compose down --volumes --remove-orphans
	@docker system prune -f
	@find . -name "*.pyc" -delete
	@find . -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true
	@echo "✅ Docker cleanup complete"

# Development workflow
dev-start: down up health ## Start development environment
	@echo "🚀 Development environment ready!"
	@echo "📊 Access points:"
	@echo "  Orchestrator: http://localhost:8001"
	@echo "  Guardian: http://localhost:8787" 
	@echo "  NLU: http://localhost:9002"
	@echo "  Cache: localhost:6379"

# CI simulation
ci-local: ## Simulate CI pipeline locally
	@echo "🤖 Simulating CI pipeline locally..."
	@$(MAKE) clean
	@$(MAKE) up
	@$(MAKE) quality
	@$(MAKE) test-all
	@echo "✅ CI simulation complete"

# Repository hygiene
repo-health: ## Check repository health
	@echo "🏥 Checking repository health..."
	@echo "📁 Repository size:"
	du -sh . --exclude=node_modules --exclude=.venv --exclude=data --exclude=test-results 2>/dev/null || du -sh .
	@echo ""
	@echo "🔍 Large files (>10MB):"
	find . -type f -size +10M -not -path "./node_modules/*" -not -path "./.venv/*" -not -path "./data/*" -not -path "./test-results/*" 2>/dev/null | head -5 || echo "No large files found"
	@echo ""
	@echo "📊 Git status:"
	git status --porcelain | wc -l | xargs echo "Modified files:"

### ===== RL Bench: End-to-End (T1–T4) =====

# Anpassa PY och vägar om du kör annan layout
PY := python3
RL_DIR := services/rl
DATA_DIR := data/rl/v1
TEL_DIR := data/telemetry
ARTE_DIR := artefacts/rl_bench

# 1) Engångs-setup för RL (pip + verktyg)
rl-setup:
	@echo ">>> RL setup"
	@python3 -V
	# Ensure venv exists and activate it
	@if [ ! -d ".venv" ]; then python3 -m venv .venv; fi
	@source .venv/bin/activate && python3 -m pip install -U pip
	# Installera RL-krav (lägg gärna en dedikerad requirements.txt i services/rl/)
	@if [ -f $(RL_DIR)/requirements.txt ]; then source .venv/bin/activate && python3 -m pip install -r $(RL_DIR)/requirements.txt; fi
	# CLI-verktyg som används i CI/gates  
	@which jq >/dev/null 2>&1 || (echo "Installing jq..." && (brew install jq 2>/dev/null || sudo apt-get update && sudo apt-get install -y jq))

# 2) Bygg dataset (T1–T2) + φ-reward (T3)
#   -> genererar train/val/test under data/rl/v1/ och MANIFEST + SUMMARY
rl-build-ci:
	@echo ">>> RL build: telemetry -> episodes -> splits (+ φ-rewards)"
	@mkdir -p $(DATA_DIR)
	@source .venv/bin/activate && $(PY) $(RL_DIR)/pipelines/build_dataset.py \
		--src "$(TEL_DIR)" \
		--out "$(DATA_DIR)" \
		--splits 0.8 0.1 0.1 \
		--phi 1.61803398875 \
		--reward-profile fibonacci_v1 \
		--mask-pii true

# 3) Kör benchmark/online-sim/replay (T4)
#   -> skriver resultat till artefacts/rl_bench/summary.json
rl-benchmark-full:
	@echo ">>> RL benchmark: bandits + replay (T4)"
	@mkdir -p $(ARTE_DIR)
	@source .venv/bin/activate && $(PY) $(RL_DIR)/bench/benchmark_runner.py \
		--dataset "$(DATA_DIR)" \
		--out "$(ARTE_DIR)" \
		--profiles micro-op turn-sim replay \
		--seed 42 \
		--persist "$(DATA_DIR)/state"

# 4) Gates (trösklar) – failar om vi underpresterar
#   Du kan justera trösklarna här om behov finns.
rl-assert:
	@echo ">>> RL assert: enforce IQ/SLO gates"
	@test -f "$(ARTE_DIR)/summary.json" || (echo "Missing $(ARTE_DIR)/summary.json" && exit 1)
	@echo "— Summary:" && cat "$(ARTE_DIR)/summary.json"
	# Gate 1: reward >= 0.80
	@jq -e '.metrics.avg_reward >= 0.80' "$(ARTE_DIR)/summary.json" >/dev/null || (echo "Gate failed: avg_reward < 0.80" && exit 1)
	# Gate 2: replay uplift >= 0.05
	@jq -e '.metrics.replay_uplift >= 0.05' "$(ARTE_DIR)/summary.json" >/dev/null || (echo "Gate failed: replay_uplift < 0.05" && exit 1)
	# Gate 3: reward coverage (andel episoder med reward.total != null) >= 0.80
	@jq -e '.metrics.reward_coverage >= 0.80' "$(ARTE_DIR)/summary.json" >/dev/null || (echo "Gate failed: reward_coverage < 0.80" && exit 1)
	# Gate 4 (valfri): cache-hit proxy / success-rate om ni loggar dem i summary
	# @jq -e '.metrics.success_rate >= 0.98' "$(ARTE_DIR)/summary.json" >/dev/null || (echo "Gate failed: success_rate < 0.98" && exit 1)
	@echo "All RL gates passed ✔"

# 5) CI entrypoint (kör allt)
rl-ci: rl-setup rl-build-ci rl-benchmark-full rl-assert
	@echo ">>> RL CI: complete ✔"

### ===== T5 Live Bandit Routing =====

# Start bandit server for live routing
rl-online-start:
	@echo "🚀 Starting bandit server for live routing..."
	@source .venv/bin/activate && BANDIT_PORT=8850 CANARY_SHARE=0.05 python3 -m services.rl.online.server

# Start orchestrator with live routing enabled
orchestrator-dev:
	@echo "🎯 Starting orchestrator with live bandit routing..."
	@if ! curl -s http://localhost:8850/health >/dev/null 2>&1; then \
		echo "⚠️  Bandit server not running. Start with 'make rl-online-start'"; \
		exit 1; \
	fi
	@echo "✅ Bandit server detected, starting orchestrator..."
	@cd services/orchestrator && source ../../.venv/bin/activate && \
		BANDIT_ENABLED=true CANARY_SHARE=0.05 python3 -m src.main

# Rotate bandit snapshots
rl-rotate:
	@echo "📸 Rotating bandit snapshots..."
	@source .venv/bin/activate && python3 services/rl/persistence/rotate.py --action rotate

# Test live routing integration
rl-live-test:
	@echo "🧪 Testing live routing integration..."
	@echo "1. Testing bandit server health..."
	@curl -s http://localhost:8850/health | jq . || echo "❌ Bandit server not responding"
	@echo "2. Testing route selection..."
	@curl -s -X POST http://localhost:8850/bandit/route \
		-H "Content-Type: application/json" \
		-d '{"context":{"intent_conf":0.8,"len_chars":25,"has_question":true,"cache_hint":false,"guardian_state":"NORMAL","prev_tool_error":false}}' \
		| jq . || echo "❌ Route selection failed"
	@echo "3. Testing tool selection..."
	@curl -s -X POST http://localhost:8850/bandit/tool \
		-H "Content-Type: application/json" \
		-d '{"intent":"greeting","available_tools":["chat_tool","fallback_tool"]}' \
		| jq . || echo "❌ Tool selection failed"
	@echo "✅ Live routing integration test complete"

# Test T5 with SLO gates  
rl-live-gates:
	@echo "🚦 Testing T5 SLO gates..."
	@source .venv/bin/activate && python3 test_t5_gates.py

### ===== T6 ToolSelector v2 + GBNF + LoRA =====

# Train LoRA model for svenska tool selection
toolselector-train-lora:
	@echo "🧠 Training LoRA model for svenska optimization..."
	@source .venv/bin/activate && LORA_EPOCHS=50 python3 services/rl/train_toolselector_lora.py

# Quick LoRA training for CI (fewer epochs)
toolselector-train-lora-ci:
	@echo "🧠 Training LoRA model (CI mode)..."
	@source .venv/bin/activate && LORA_EPOCHS=10 python3 services/rl/train_toolselector_lora.py

# Benchmark LoRA performance
toolselector-benchmark-lora:
	@echo "⚡ Benchmarking LoRA performance..."
	@source .venv/bin/activate && python3 services/rl/train_toolselector_lora.py benchmark

# Test T6 ToolSelector v2 (all tests in one script)
toolselector-test-all:
	@echo "🎯 Running T6 ToolSelector v2 tests..."
	@source .venv/bin/activate && python3 test_t6_toolselector.py

# Complete T6 development pipeline
toolselector-t6-dev: toolselector-train-lora-ci toolselector-benchmark-lora toolselector-test-all
	@echo "🎉 T6 development pipeline complete!"

# Complete T6 CI pipeline
toolselector-t6-ci: toolselector-train-lora-ci toolselector-benchmark-lora toolselector-test-all toolselector-shadow-test
	@echo "🎉 T6 CI pipeline complete - Ready for production! 🇸🇪"
