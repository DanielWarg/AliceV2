#!/usr/bin/env bash
set -euo pipefail

echo "🔥 A-Z REAL DATA TEST - ELIMINATING STUPID ASSUMPTIONS"
echo "======================================================"

# Configuration
ORCHESTRATOR_URL="http://localhost:8001"
GUARDIAN_URL="http://localhost:8787"
NLU_URL="http://localhost:9002"
REDIS_URL="localhost:6379"

# Test data - REAL Swedish queries, not fake shit
REAL_QUERIES=(
  "Vad är klockan nu?"
  "Vilken dag är det idag?"
  "Kan du hjälpa mig med mitt schema för imorgon?"
  "Sänd ett mail till marcus@företag.se om mötet"
  "Vad blir 1234 plus 5678?"
  "Vilken temperatur är det ute?"
  "Skapa en påminnelse för lunch kl 12"
  "Visa mig mina avslutade uppgifter"
  "Berätta en rolig historia"
  "Stäng av lamporna i vardagsrummet"
)

# Results tracking
PASSED=0
FAILED=0
ERRORS=()

# Utility functions
timestamp() {
  date '+%Y-%m-%d %H:%M:%S'
}

log() {
  echo "[$(timestamp)] $1"
}

test_health_endpoint() {
  local name=$1
  local url=$2
  log "🏥 Testing health endpoint: $name"
  
  if curl -fsS "$url" > /dev/null; then
    log "✅ $name health OK"
    return 0
  else
    log "❌ $name health FAILED"
    ERRORS+=("$name health endpoint failed")
    return 1
  fi
}

test_real_query() {
  local query=$1
  local test_num=$2
  log "🧪 Test $test_num: '$query'"
  
  # Make actual request to orchestrator
  local response
  response=$(curl -s -X POST "$ORCHESTRATOR_URL/api/orchestrator/chat" \
    -H "Content-Type: application/json" \
    -d "{
      \"v\": \"1\",
      \"session_id\": \"a-z-test-$test_num\",
      \"message\": \"$query\"
    }" 2>/dev/null || echo '{"error": "request failed"}')
  
  # Parse response
  if echo "$response" | jq -e '.error' > /dev/null 2>&1; then
    log "❌ Test $test_num FAILED: Request error"
    ERRORS+=("Query '$query' failed with request error")
    ((FAILED++))
    return 1
  fi
  
  # Check for valid response structure
  if echo "$response" | jq -e '.response // .message // .result' > /dev/null 2>&1; then
    log "✅ Test $test_num PASSED: Valid response received"
    ((PASSED++))
    return 0
  else
    log "❌ Test $test_num FAILED: Invalid response structure"
    log "Response: $response"
    ERRORS+=("Query '$query' returned invalid response structure")
    ((FAILED++))
    return 1
  fi
}

test_performance_assumptions() {
  log "⚡ Testing performance assumptions"
  
  # Test P95 latency assumption
  local start_time=$(python3 -c "import time; print(int(time.time() * 1000))")
  curl -s -X POST "$ORCHESTRATOR_URL/api/orchestrator/chat" \
    -H "Content-Type: application/json" \
    -d '{"v":"1","session_id":"perf-test","message":"Hej"}' > /dev/null
  local end_time=$(python3 -c "import time; print(int(time.time() * 1000))")
  local latency=$((end_time - start_time))
  
  log "🕐 Response time: ${latency}ms"
  
  if [ "$latency" -lt 900 ]; then
    log "✅ Performance assumption VALID: ${latency}ms < 900ms"
  else
    log "❌ Performance assumption VIOLATED: ${latency}ms >= 900ms"
    ERRORS+=("Performance assumption violated: ${latency}ms latency")
  fi
}

test_data_assumptions() {
  log "📊 Testing data format assumptions"
  
  # Test that we get consistent JSON structure
  local response
  response=$(curl -s -X POST "$ORCHESTRATOR_URL/api/orchestrator/chat" \
    -H "Content-Type: application/json" \
    -d '{"v":"1","session_id":"data-test","message":"Test"}')
  
  # Check required fields exist
  local required_fields=("timestamp" "session_id")
  for field in "${required_fields[@]}"; do
    if echo "$response" | jq -e ".$field" > /dev/null 2>&1; then
      log "✅ Required field '$field' present"
    else
      log "❌ Required field '$field' MISSING"
      ERRORS+=("Missing required response field: $field")
    fi
  done
}

test_stupid_assumptions() {
  log "🧠 Checking for STUPID ASSUMPTIONS in code"
  
  # Check for hardcoded assumptions that need fixing
  local stupid_patterns=(
    "localhost:11434"  # Ollama should be configurable
    "fake-key"         # Should not appear in real configs
    "TODO"             # Unfinished work
    "FIXME"            # Known issues
    "HACK"             # Temporary solutions
    "DUMMY"            # Fake data
  )
  
  for pattern in "${stupid_patterns[@]}"; do
    if grep -r "$pattern" services/ 2>/dev/null | head -5; then
      log "❌ STUPID ASSUMPTION FOUND: $pattern"
      ERRORS+=("Stupid assumption found: $pattern")
    fi
  done
}

# Main execution
main() {
  log "🚀 Starting A-Z Real Data Test"
  
  # 1. Health checks
  test_health_endpoint "Orchestrator" "$ORCHESTRATOR_URL/health"
  test_health_endpoint "Guardian" "$GUARDIAN_URL/health"
  test_health_endpoint "NLU" "$NLU_URL/healthz"
  
  # 2. Real query testing
  for i in "${!REAL_QUERIES[@]}"; do
    test_real_query "${REAL_QUERIES[$i]}" "$((i+1))"
    sleep 1  # Be nice to the system
  done
  
  # 3. Performance testing
  test_performance_assumptions
  
  # 4. Data format testing
  test_data_assumptions
  
  # 5. Stupid assumptions hunting
  test_stupid_assumptions
  
  # Results
  log "📊 TEST RESULTS"
  log "==============="
  log "✅ Passed: $PASSED"
  log "❌ Failed: $FAILED"
  log "🔥 Total: $((PASSED + FAILED))"
  
  if [ ${#ERRORS[@]} -gt 0 ]; then
    log ""
    log "🚨 ERRORS FOUND:"
    for error in "${ERRORS[@]}"; do
      log "  - $error"
    done
  fi
  
  # Exit with failure if any tests failed
  if [ $FAILED -gt 0 ] || [ ${#ERRORS[@]} -gt 0 ]; then
    log ""
    log "💥 A-Z TEST FAILED - FIX THE STUPID SHIT ABOVE!"
    exit 1
  else
    log ""
    log "🎉 A-Z TEST PASSED - SYSTEM IS SOLID!"
    exit 0
  fi
}

# Run if called directly
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
  main "$@"
fi