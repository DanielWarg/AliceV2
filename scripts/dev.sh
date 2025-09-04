#!/usr/bin/env bash
set -euo pipefail

# Consolidated development script - replaces dev_up.sh, dev_up_fast.sh, dev_down.sh, dev-start.sh, dev-stop.sh

usage() {
    echo "Usage: $0 {up|down|restart|fast|logs|status}"
    echo ""
    echo "Commands:"
    echo "  up      - Start all services with health checks"
    echo "  down    - Stop all services and cleanup"
    echo "  restart - Stop then start all services"  
    echo "  fast    - Quick start without extensive health checks"
    echo "  logs    - Show logs from all services"
    echo "  status  - Show service status"
    exit 1
}

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

wait_for_health() {
    local service=$1
    local url=$2
    local max_attempts=30
    
    log_info "Waiting for $service health check..."
    for i in $(seq 1 $max_attempts); do
        if curl -fsS "$url" >/dev/null 2>&1; then
            log_info "$service is healthy"
            return 0
        fi
        sleep 2
    done
    
    log_error "$service health check failed after $max_attempts attempts"
    return 1
}

dev_up() {
    log_info "🚀 Starting Alice v2 development environment..."
    
    # Start services
    docker compose up -d --wait
    
    # Wait for health checks
    wait_for_health "Orchestrator" "http://localhost:18000/health"
    wait_for_health "Guardian" "http://localhost:8787/health"  
    wait_for_health "NLU" "http://localhost:9002/healthz"
    
    log_info "✅ All services are up and healthy!"
    echo ""
    echo "🌐 Service URLs:"
    echo "  Orchestrator: http://localhost:18000"
    echo "  Guardian: http://localhost:8787"
    echo "  NLU: http://localhost:9002"
    echo "  Redis: localhost:6379"
}

dev_down() {
    log_info "🛑 Stopping Alice v2 development environment..."
    docker compose down -v --remove-orphans || true
    log_info "✅ All services stopped and cleaned up"
}

dev_fast() {
    log_info "⚡ Quick starting Alice v2 (no health checks)..."
    docker compose up -d
    log_info "✅ Services started (use 'status' to check health)"
}

dev_logs() {
    log_info "📋 Showing logs from all services..."
    docker compose logs -f
}

dev_status() {
    log_info "📊 Service Status:"
    docker compose ps
    
    echo ""
    log_info "🏥 Health Checks:"
    
    # Check orchestrator
    if curl -fsS http://localhost:18000/health >/dev/null 2>&1; then
        echo "  ✅ Orchestrator: Healthy"
    else
        echo "  ❌ Orchestrator: Unhealthy"
    fi
    
    # Check guardian  
    if curl -fsS http://localhost:8787/health >/dev/null 2>&1; then
        echo "  ✅ Guardian: Healthy"
    else
        echo "  ❌ Guardian: Unhealthy"
    fi
    
    # Check NLU
    if curl -fsS http://localhost:9002/healthz >/dev/null 2>&1; then
        echo "  ✅ NLU: Healthy"
    else
        echo "  ❌ NLU: Unhealthy"
    fi
    
    # Check Redis
    if redis-cli -h localhost -p 6379 ping >/dev/null 2>&1; then
        echo "  ✅ Redis: Healthy"
    else
        echo "  ❌ Redis: Unhealthy"
    fi
}

# Main command processing
case "${1:-}" in
    up)
        dev_up
        ;;
    down)
        dev_down
        ;;
    restart)
        dev_down
        sleep 2
        dev_up
        ;;
    fast)
        dev_fast
        ;;
    logs)
        dev_logs
        ;;
    status)
        dev_status
        ;;
    *)
        usage
        ;;
esac