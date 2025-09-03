#!/usr/bin/env bash
set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

check_port () {
  local p=$1
  if lsof -nP -iTCP:$p -sTCP:LISTEN >/dev/null 2>&1; then
    log_warn "Port $p is occupied – run scripts/dev_down.sh or scripts/ports-kill.sh first."
    exit 1
  fi
}

# Only exposed port in dev
PORT=18000
check_port $PORT

# Check if models exist, fetch if needed
log_info "Checking required models..."
if [[ ! -f "models/e5-small.onnx" ]] || [[ ! -f "models/e5-tokenizer.json" ]]; then
    log_warn "Required models not found. Fetching models..."
    if ! ./scripts/fetch_models.sh; then
        log_error "Failed to fetch models. Please run: make fetch-models"
        exit 1
    fi
else
    log_info "Required models found ✓"
fi

# Check Ollama models
log_info "Checking Ollama models..."
if ! ollama list | grep -q "qwen2.5:3b"; then
    log_warn "Ollama model qwen2.5:3b not found. Pulling..."
    ollama pull qwen2.5:3b || log_warn "Failed to pull qwen2.5:3b - some features may not work"
fi
if ! ollama list | grep -q "phi3:mini"; then
    log_warn "Ollama model phi3:mini not found. Pulling..."
    ollama pull phi3:mini || log_warn "Failed to pull phi3:mini - some features may not work"
fi

log_info "Cleaning old containers (if any)..."
docker compose down --remove-orphans >/dev/null 2>&1 || true

log_info "Starting core services only (guardian, orchestrator, nlu, dev-proxy)..."
docker compose up -d --build guardian orchestrator nlu dev-proxy || true

log_info "Waiting for core services to be ready..."
for i in {1..60}; do
  if curl -fsS http://localhost:$PORT/health >/dev/null 2>&1; then
    log_info "✅ Up: http://localhost:$PORT"
    log_info "🚀 Alice v2 core services ready!"
    log_info "📊 HUD: http://localhost:3001"
    log_info "🔍 Health: http://localhost:$PORT/health"
    log_info "⚠️  Note: Memory and Voice services not started (use 'make up' for full stack)"
    exit 0
  fi
  sleep 1
done

log_error "❌ Proxy not responding in time. Check logs: docker compose logs -f dev-proxy"
exit 1
