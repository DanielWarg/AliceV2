#!/usr/bin/env bash
set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo "🏥 Waiting for Alice v2 stack to be healthy..."

# Health endpoints to check
declare -a ENDPOINTS=(
  "http://localhost:18000/health:Orchestrator"
  "http://localhost:8787/health:Guardian"
  "http://localhost:9002/healthz:NLU"
)

# Redis check function
check_redis() {
  if command -v docker >/dev/null 2>&1; then
    docker compose exec -T alice-cache redis-cli ping 2>/dev/null | grep -q PONG
  else
    # Fallback if docker not available
    redis-cli -p 6379 ping 2>/dev/null | grep -q PONG
  fi
}

# Wait for each service with timeout
TOTAL_TIMEOUT=${STACK_TIMEOUT:-300}  # 5 minutes default
POLL_INTERVAL=${POLL_INTERVAL:-2}     # 2 seconds between checks

start_time=$(date +%s)

for endpoint_info in "${ENDPOINTS[@]}"; do
  IFS=':' read -r url service_name <<< "$endpoint_info"
  
  printf "  ${YELLOW}⏳${NC} Waiting for $service_name ($url)..."
  
  waited=0
  while [ $waited -lt $TOTAL_TIMEOUT ]; do
    current_time=$(date +%s)
    elapsed=$((current_time - start_time))
    
    if [ $elapsed -ge $TOTAL_TIMEOUT ]; then
      printf "\n  ${RED}❌${NC} Global timeout reached after ${TOTAL_TIMEOUT}s\n"
      exit 1
    fi
    
    if curl -fsS --connect-timeout 5 --max-time 10 "$url" >/dev/null 2>&1; then
      printf " ${GREEN}✅${NC}\n"
      break
    fi
    
    sleep $POLL_INTERVAL
    waited=$((waited + POLL_INTERVAL))
    printf "."
  done
  
  if [ $waited -ge $TOTAL_TIMEOUT ]; then
    printf "\n  ${RED}❌${NC} $service_name failed health check after ${TOTAL_TIMEOUT}s\n"
    echo "  Last curl attempt:"
    curl -v "$url" || true
    exit 1
  fi
done

# Check Redis separately
printf "  ${YELLOW}⏳${NC} Waiting for Redis..."
redis_waited=0
while [ $redis_waited -lt $TOTAL_TIMEOUT ]; do
  if check_redis; then
    printf " ${GREEN}✅${NC}\n"
    break
  fi
  
  sleep $POLL_INTERVAL  
  redis_waited=$((redis_waited + POLL_INTERVAL))
  printf "."
done

if [ $redis_waited -ge $TOTAL_TIMEOUT ]; then
  printf "\n  ${RED}❌${NC} Redis failed health check\n"
  exit 1
fi

total_elapsed=$(($(date +%s) - start_time))
echo "🎉 All services healthy in ${total_elapsed}s!"

# Optional: run a quick smoke test
if [ "${SMOKE_TEST:-}" = "true" ]; then
  echo "🧪 Running smoke test..."
  
  # Test orchestrator chat endpoint
  if curl -fsS -X POST http://localhost:18000/api/chat \
    -H 'Content-Type: application/json' \
    -d '{"message":"hej","session_id":"smoke"}' >/dev/null 2>&1; then
    echo "  ✅ Chat endpoint responding"
  else
    echo "  ⚠️  Chat endpoint not responding (may be normal)"
  fi
  
  # Test NLU parse
  if curl -fsS -X POST http://localhost:9002/api/nlu/parse \
    -H 'Content-Type: application/json' \
    -d '{"v":"1","lang":"sv","text":"hej","session_id":"smoke"}' >/dev/null 2>&1; then
    echo "  ✅ NLU parse responding"
  else
    echo "  ⚠️  NLU parse not responding"
  fi
fi

echo "✅ Stack is ready for testing!"