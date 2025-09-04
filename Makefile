.PHONY: help down up status health test-unit test-all security-scan format lint clean stabilize fix-system rl-bootstrap rl-train rl-shadow

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
	@echo "  make rl-bootstrap  - Generate bootstrap data"
	@echo "  make rl-train      - Train RL policies"
	@echo "  make rl-shadow     - Start shadow mode"

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

up: ## Start all services  
	@echo "🚀 Starting Alice v2 services..."
	docker compose up -d guardian orchestrator alice-cache nlu
	@echo "⏳ Waiting for services to start..."
	@sleep 10
	@$(MAKE) health

status: ## Show service status
	@echo "📊 Service Status:"
	@docker compose ps

health: ## Check all health endpoints
	@echo "🏥 Health Check:"
	@echo -n "  Orchestrator: "
	@curl -sf http://localhost:18000/health >/dev/null && echo "✅ OK" || echo "❌ FAIL"
	@echo -n "  Guardian: "
	@curl -sf http://localhost:8787/health >/dev/null && echo "✅ OK" || echo "❌ FAIL"
	@echo -n "  NLU: "
	@curl -sf http://localhost:9002/healthz >/dev/null && echo "✅ OK" || echo "❌ FAIL"
	@echo -n "  Redis: "
	@docker compose exec -T alice-cache redis-cli ping | grep -q PONG && echo "✅ OK" || echo "❌ FAIL"

logs: ## Show recent logs
	@echo "📋 Recent logs:"
	@docker compose logs --tail=20 orchestrator guardian nlu

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
	@echo "  Orchestrator: http://localhost:18000"
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
