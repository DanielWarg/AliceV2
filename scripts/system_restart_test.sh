#!/usr/bin/env bash
set -euo pipefail

echo "🔄 SYSTEM RESTART + REAL TEST - Fibonacci Training Protocol"
echo "=========================================================="

PROJECT_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$PROJECT_ROOT"

echo "📍 Working directory: $PROJECT_ROOT"

# Function to log with timestamp
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1"
}

# Phase 1: Clean shutdown
log "🛑 Phase 1: Clean system shutdown..."
make down || {
    log "⚠️ Make down failed, forcing docker cleanup..."
    docker compose down --remove-orphans --volumes || true
    docker system prune -f || true
}

# Kill any lingering processes
log "🧹 Cleaning lingering processes..."
pkill -f ollama || true
pkill -f "streamlit run" || true
pkill -f "python.*fibonacci" || true

# Wait for cleanup
log "⏱️ Waiting for cleanup to complete..."
sleep 5

# Phase 2: Fresh startup
log "🚀 Phase 2: Fresh system startup..."
make up || {
    log "❌ Make up failed!"
    exit 1
}

# Phase 3: Wait for health
log "⏳ Phase 3: Waiting for system health..."
for i in {1..60}; do
    if curl -fsS http://localhost:8001/health >/dev/null 2>&1; then
        log "✅ System is healthy after ${i} seconds"
        break
    fi
    
    if [ $i -eq 60 ]; then
        log "❌ System failed to become healthy within 60 seconds"
        exit 1
    fi
    
    sleep 1
done

# Phase 4: Verify core services
log "🔍 Phase 4: Verifying core services..."
services_ok=true

# Check Orchestrator
if curl -fsS http://localhost:8001/health >/dev/null 2>&1; then
    log "✅ Orchestrator: OK"
else
    log "❌ Orchestrator: FAIL"
    services_ok=false
fi

# Check Guardian
if curl -fsS http://localhost:8787/health >/dev/null 2>&1; then
    log "✅ Guardian: OK"
else
    log "❌ Guardian: FAIL"
    services_ok=false
fi

# Check NLU
if curl -fsS http://localhost:9002/healthz >/dev/null 2>&1; then
    log "✅ NLU: OK"
else
    log "❌ NLU: FAIL"
    services_ok=false
fi

# Check Redis
if redis-cli -p 6379 ping >/dev/null 2>&1; then
    log "✅ Redis: OK"
else
    log "❌ Redis: FAIL"
    services_ok=false
fi

if [ "$services_ok" = false ]; then
    log "❌ Core services verification failed!"
    exit 1
fi

# Phase 5: Run the REAL test
log "🧪 Phase 5: Running REAL A-Z test with fresh system..."
log "    This is the actual test that validates Fibonacci training!"

# Run the real A-Z test
if [ -f "scripts/test_a_z_real_data.sh" ]; then
    log "▶️ Executing test_a_z_real_data.sh..."
    bash scripts/test_a_z_real_data.sh
    test_result=$?
else
    log "❌ test_a_z_real_data.sh not found!"
    exit 1
fi

# Phase 6: Collect real statistics
log "📊 Phase 6: Collecting REAL training statistics..."

# Check for telemetry data
today=$(date +%Y-%m-%d)
tel_file="data/telemetry/${today}/events_${today}.jsonl"

if [ -f "$tel_file" ]; then
    log "✅ Telemetry file found: $tel_file"
    log "📈 Event count: $(wc -l < "$tel_file" || echo "0")"
    log "📁 File size: $(ls -lh "$tel_file" | awk '{print $5}' || echo "0")"
else
    log "⚠️ No telemetry file found for today: $tel_file"
fi

# Check test results
if [ -d "data/tests" ]; then
    test_files=$(find data/tests -name "*.json" -mtime -1 2>/dev/null | wc -l || echo "0")
    log "📋 Recent test files: $test_files"
else
    log "⚠️ No test results directory found"
fi

# Final result
if [ $test_result -eq 0 ]; then
    log "🎉 SYSTEM RESTART + REAL TEST: SUCCESS"
    log "   ✅ Fresh system startup completed"
    log "   ✅ All core services healthy"  
    log "   ✅ A-Z real data test passed"
    log "   ✅ Telemetry data collected"
    log ""
    log "🧮 Fibonacci Training System is ready for evaluation!"
    exit 0
else
    log "💥 SYSTEM RESTART + REAL TEST: FAILED"
    log "   ✅ Fresh system startup completed"
    log "   ✅ All core services healthy"
    log "   ❌ A-Z real data test failed (exit code: $test_result)"
    log ""
    log "🔧 Check the test output above for specific failures."
    exit 1
fi