.PHONY: help venv clean clean-venv fetch-models up down force-down restart preflight docker-up docker-down test verify

# Default target
help: ## Show this help message
	@echo "Alice v2 Development Commands"
	@echo "============================="
	@echo ""
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'
	@echo ""
	@echo "Quick Start:"
	@echo "  make venv        # Create/update root virtual environment"
	@echo "  make fetch-models # Download required models"
	@echo "  make up          # Start development stack"
	@echo "  make down        # Stop development stack"

venv: ## Create/update root virtual environment
	@echo "🔧 Setting up virtual environment..."
	python3 -m venv .venv
	@echo "📦 Installing dependencies..."
	. .venv/bin/activate && pip install --upgrade pip
	@echo "✅ Virtual environment ready! Activate with: source .venv/bin/activate"

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

fetch-models: ## Download required models
	@echo "📥 Fetching models..."
	./scripts/fetch_models.sh

# --- Robust control targets ---------------------------------------------------

preflight: ## Light checks (Docker + ports)
	@echo "🔎 Preflight..."
	@if docker info >/dev/null 2>&1; then echo "🐳 Docker: OK"; else echo "🐳 Docker: NOT RUNNING"; fi
	@printf "🔌 Ports in use: "; (lsof -i :8000 -i :8501 -i :8787 2>/dev/null || true) | awk '{print $$9}' | sed 's/.*://g' | xargs -I{} echo -n "{} " ; echo

up: ## Start development stack (safe)
	@echo "🚀 Starting dev stack..."
	@if docker info >/dev/null 2>&1; then \
		./scripts/dev_up.sh; \
	else \
		echo "⚠️  Docker not running. Start Docker first or use local-only scripts."; \
		exit 1; \
	fi

down: ## Stop development stack (with Docker fallback)
	@echo "🛑 Stopping dev stack..."
	@if docker info >/dev/null 2>&1; then \
		./scripts/dev-stop.sh || true; \
	else \
		echo "🐳 Docker not running → using ports-kill fallback"; \
		./scripts/ports-kill.sh || true; \
	fi
	@echo "✅ Down complete."

force-down: ## Force stop (no Docker dependency)
	@echo "💥 Force stop (no Docker)..."
	@./scripts/ports-kill.sh || true
	@echo "✅ Force-down complete."

restart: ## Restart dev stack
	@$(MAKE) down
	@$(MAKE) up

docker-down: ## Strict docker compose down (no fallback)
	@docker compose down

test: ## Run all tests
	@echo "🧪 Running tests..."
	./scripts/auto_verify.sh

verify: ## Run system verification
	@echo "✅ Verifying system..."
	./scripts/auto_verify.sh

# Development helpers
install-deps: ## Install all dependencies
	@echo "📦 Installing dependencies..."
	pnpm install:all
	@echo "✅ Dependencies installed"

format: ## Format code
	@echo "🎨 Formatting code..."
	cd services/orchestrator && source .venv/bin/activate && ruff format .
	cd services/guardian && source .venv/bin/activate && ruff format .
	@echo "✅ Code formatted"

lint: ## Lint code
	@echo "🔍 Linting code..."
	cd services/orchestrator && source .venv/bin/activate && ruff check .
	cd services/guardian && source .venv/bin/activate && ruff check .
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
