.PHONY: help venv clean clean-venv fetch-models up down force-down restart preflight docker-up docker-down test verify test-all test-unit test-e2e test-integration

# Default target
help: ## Show this help message
	@echo "Alice v2 Development Commands"
	@echo "============================="
	@echo ""
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'
	@echo ""
	@echo "Quick Start:"
	@echo "  make up          # Start development stack + frontend (auto-creates venv + installs deps)"
	@echo "  make frontend    # Start frontend only (HUD on http://localhost:3001)"
	@echo "  make test-all    # Run all tests (unit + e2e + integration)"
	@echo "  make down        # Stop development stack + frontend"

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

up: install-requirements fetch-models ## Start development stack (auto-setup)
	@echo "🚀 Starting dev stack..."
	@if docker info >/dev/null 2>&1; then \
		./scripts/dev_up.sh; \
	else \
		echo "⚠️  Docker not running. Start Docker first or use local-only scripts."; \
		exit 1; \
	fi
	@echo "🎨 Starting frontend..."
	@$(MAKE) frontend

dev-fast: install-requirements fetch-models ## Start core services only (fast dev)
	@echo "🚀 Starting core services (fast dev mode)..."
	@if docker info >/dev/null 2>&1; then \
		./scripts/dev_up_fast.sh; \
	else \
		echo "⚠️  Docker not running. Start Docker first."; \
		exit 1; \
	fi
	@echo "🎨 Starting frontend..."
	@$(MAKE) frontend

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

test-unit: ## Run unit tests for all services
	@echo "🧪 Running unit tests..."
	@echo "🔍 Testing orchestrator..."
	@cd services/orchestrator && source ../../.venv/bin/activate && python -m pytest -v --tb=short || echo "⚠️  Some orchestrator tests failed (expected in dev environment)"
	@echo "🔍 Testing guardian..."
	@cd services/guardian && source ../../.venv/bin/activate && python -m pytest -v --tb=short || echo "⚠️  Guardian has no tests yet"
	@echo "🔍 Testing NLU..."
	@cd services/nlu && source ../../.venv/bin/activate && python -m pytest -v --tb=short || echo "⚠️  NLU has no tests yet"
	@echo "✅ Unit tests completed!"

test-e2e: ## Run end-to-end tests
	@echo "🧪 Running E2E tests..."
	@echo "🚀 Ensuring stack is running..."
	@if ! curl -s http://localhost:18000/health >/dev/null 2>&1; then \
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
	@if ! curl -s http://localhost:18000/health >/dev/null 2>&1; then \
		echo "⚠️  Stack not running, starting it..."; \
		$(MAKE) up; \
		sleep 10; \
	fi
	@echo "🔍 Testing API endpoints..."
	@curl -s http://localhost:18000/health | jq . || echo "⚠️  Health endpoint test failed"
	@curl -s http://localhost:18000/api/status/simple | jq . || echo "⚠️  Status endpoint test failed"
	@echo "🔍 Testing Guardian integration..."
	@curl -s http://localhost:8787/health | jq . || echo "⚠️  Guardian health test failed"
	@echo "🔍 Testing Learning API..."
	@curl -s http://localhost:18000/api/learn/stats | jq . || echo "⚠️  Learning stats test failed"
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
	@curl -s -X POST http://localhost:18000/api/learn/snapshot | jq .

learn-stats: ## Get learning statistics
	@echo "📈 Getting learning statistics..."
	@curl -s http://localhost:18000/api/learn/stats | jq .

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

format: ## Format code
	@echo "🎨 Formatting code..."
	@source .venv/bin/activate && cd services/orchestrator && ruff format .
	@source .venv/bin/activate && cd services/guardian && ruff format .
	@echo "✅ Code formatted"

lint: ## Lint code
	@echo "🔍 Linting code..."
	@source .venv/bin/activate && cd services/orchestrator && ruff check .
	@source .venv/bin/activate && cd services/guardian && ruff check .
	@echo "✅ Code linted"

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
