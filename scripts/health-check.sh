#!/bin/bash
# Alice v2 Comprehensive Health Check
# Validates all services, SLO compliance, and system resources

set -e

# Color codes
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Service endpoints
ORCHESTRATOR_URL="http://localhost:8000"
GUARDIAN_URL="http://localhost:8787"  
VOICE_URL="http://localhost:8001"
FRONTEND_URL="http://localhost:3000"
DASHBOARD_URL="http://localhost:8501"

# SLO targets
MAX_RESPONSE_TIME_MS=500
MAX_RAM_USAGE_PCT=75
MIN_DISK_FREE_GB=5

echo "🔍 Alice v2 Comprehensive Health Check"
echo "======================================"

# Function to check HTTP endpoint with timing
check_endpoint() {
    local url=$1
    local service_name=$2
    local expected_status=${3:-200}
    
    echo -n "  Checking $service_name... "
    
    # Measure response time
    start_time=$(date +%s%N)
    if response=$(curl -s -w "%{http_code}" -o /tmp/response.json "$url" 2>/dev/null); then
        end_time=$(date +%s%N)
        response_time_ms=$(( (end_time - start_time) / 1000000 ))
        
        if [[ "$response" == "$expected_status" ]]; then
            if [[ $response_time_ms -le $MAX_RESPONSE_TIME_MS ]]; then
                echo -e "${GREEN}✅ OK (${response_time_ms}ms)${NC}"
                return 0
            else
                echo -e "${YELLOW}⚠️  SLOW (${response_time_ms}ms > ${MAX_RESPONSE_TIME_MS}ms)${NC}"
                return 1
            fi
        else
            echo -e "${RED}❌ HTTP $response${NC}"
            return 1
        fi
    else
        echo -e "${RED}❌ UNREACHABLE${NC}"
        return 1
    fi
}

# Function to check Guardian-specific health
check_guardian_detailed() {
    echo -e "${BLUE}🛡️  Guardian System Analysis:${NC}"
    
    if curl -s "$GUARDIAN_URL/guardian/health" -o /tmp/guardian.json 2>/dev/null; then
        local state=$(jq -r '.state // "UNKNOWN"' /tmp/guardian.json)
        local ram_pct=$(jq -r '.ram_pct // 0' /tmp/guardian.json)
        local cpu_pct=$(jq -r '.cpu_pct // 0' /tmp/guardian.json)
        local brownout_level=$(jq -r '.brownout_level // "NONE"' /tmp/guardian.json)
        local uptime_s=$(jq -r '.uptime_s // 0' /tmp/guardian.json)
        
        echo "  State: $state"
        echo "  RAM Usage: ${ram_pct}%"
        echo "  CPU Usage: ${cpu_pct}%"
        echo "  Brownout Level: $brownout_level"
        echo "  Uptime: ${uptime_s}s"
        
        # Validate Guardian state
        if [[ "$state" == "NORMAL" ]]; then
            echo -e "  Status: ${GREEN}✅ HEALTHY${NC}"
            return 0
        elif [[ "$state" == "BROWNOUT" ]]; then
            echo -e "  Status: ${YELLOW}⚠️  DEGRADED${NC}"
            return 1
        else
            echo -e "  Status: ${RED}❌ UNHEALTHY${NC}"
            return 1
        fi
    else
        echo -e "  Status: ${RED}❌ UNABLE TO CONNECT${NC}"
        return 1
    fi
}

# Function to test voice pipeline functionality  
test_voice_pipeline() {
    echo -e "${BLUE}🎤 Voice Pipeline Functional Test:${NC}"
    
    # Test TTS endpoint with sample text
    echo -n "  Testing TTS endpoint... "
    local tts_payload='{"v":"1","lang":"sv","text":"Hej Alice, detta är ett test","voice":"alice_neutral"}'
    
    if tts_response=$(curl -s -X POST -H "Content-Type: application/json" \
        -d "$tts_payload" "$VOICE_URL/api/tts" 2>/dev/null); then
        
        local tts_latency=$(echo "$tts_response" | jq -r '.latency_ms // 0')
        local cache_status=$(echo "$tts_response" | jq -r '.cache_status // "UNKNOWN"')
        
        if [[ $tts_latency -gt 0 ]]; then
            echo -e "${GREEN}✅ OK (${tts_latency}ms, $cache_status)${NC}"
        else
            echo -e "${RED}❌ INVALID RESPONSE${NC}"
        fi
    else
        echo -e "${RED}❌ FAILED${NC}"
    fi
    
    # Test WebSocket availability (connection test only)
    echo -n "  Testing WebSocket endpoint... "
    if timeout 3 wscat -c "ws://localhost:8001/ws/asr" -x '{"type":"ping"}' >/dev/null 2>&1; then
        echo -e "${GREEN}✅ OK${NC}"
    else
        echo -e "${YELLOW}⚠️  CONNECTION ISSUES${NC}"
    fi
}

# Function to test orchestrator functionality
test_orchestrator() {
    echo -e "${BLUE}🎯 Orchestrator Functional Test:${NC}"
    
    # Test chat endpoint
    echo -n "  Testing chat endpoint... "
    local chat_payload='{"v":"1","session_id":"health-check","message":"Hej Alice"}'
    
    if chat_response=$(curl -s -X POST -H "Content-Type: application/json" \
        -d "$chat_payload" "$ORCHESTRATOR_URL/api/chat" 2>/dev/null); then
        
        local response_text=$(echo "$chat_response" | jq -r '.response // ""')
        if [[ -n "$response_text" ]]; then
            echo -e "${GREEN}✅ OK${NC}"
        else
            echo -e "${RED}❌ EMPTY RESPONSE${NC}"
        fi
    else
        echo -e "${RED}❌ FAILED${NC}"
    fi
    
    # Test Guardian integration
    echo -n "  Testing Guardian integration... "
    if ingest_response=$(curl -s -X POST -H "Content-Type: application/json" \
        -d '{"v":"1","session_id":"test","lang":"sv","text":"test"}' \
        "$ORCHESTRATOR_URL/api/orchestrator/ingest" 2>/dev/null); then
        
        local accepted=$(echo "$ingest_response" | jq -r '.accepted // false')
        if [[ "$accepted" == "true" ]]; then
            echo -e "${GREEN}✅ OK${NC}"
        else
            echo -e "${YELLOW}⚠️  REQUEST BLOCKED${NC}"
        fi
    else
        echo -e "${RED}❌ FAILED${NC}"
    fi
}

# Function to check system resources
check_system_resources() {
    echo -e "${BLUE}💻 System Resource Analysis:${NC}"
    
    # RAM usage
    if command -v python3 >/dev/null; then
        local ram_usage=$(python3 -c "import psutil; print(f'{psutil.virtual_memory().percent:.1f}')")
        echo -n "  RAM Usage: ${ram_usage}%"
        
        if (( $(echo "$ram_usage > $MAX_RAM_USAGE_PCT" | bc -l) )); then
            echo -e " ${RED}❌ HIGH${NC}"
        else
            echo -e " ${GREEN}✅ OK${NC}"
        fi
    fi
    
    # Disk usage  
    local disk_free=$(df -h . | awk 'NR==2{print $4}' | sed 's/G.*//')
    echo -n "  Free Disk Space: ${disk_free}GB"
    
    if (( $(echo "$disk_free < $MIN_DISK_FREE_GB" | bc -l) )); then
        echo -e " ${RED}❌ LOW${NC}"
    else
        echo -e " ${GREEN}✅ OK${NC}"
    fi
    
    # Load average
    local load_avg=$(uptime | awk -F'load average:' '{print $2}' | cut -d',' -f1 | xargs)
    echo "  Load Average: $load_avg"
    
    # Check for Alice processes
    echo "  Active Alice processes:"
    ps aux | grep -E "(uvicorn|ollama|pnpm.*dev)" | grep -v grep | while read -r line; do
        local process_name=$(echo "$line" | awk '{for(i=11;i<=NF;i++) printf "%s ", $i}')
        local cpu_usage=$(echo "$line" | awk '{print $3}')
        local mem_usage=$(echo "$line" | awk '{print $4}')
        echo "    - $process_name (CPU: ${cpu_usage}%, MEM: ${mem_usage}%)"
    done
}

# Function to check Docker services
check_docker_services() {
    echo -e "${BLUE}🐳 Docker Services Status:${NC}"
    
    if command -v docker >/dev/null; then
        # Check if Docker is running
        if docker info >/dev/null 2>&1; then
            # List Alice-related containers
            docker ps --filter "name=alice" --filter "name=redis" --filter "name=ollama" \
                --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}" | while read -r line; do
                if [[ "$line" != "NAMES"* ]]; then
                    echo "    $line"
                fi
            done
            
            # Check for any unhealthy containers
            local unhealthy=$(docker ps --filter "health=unhealthy" --format "{{.Names}}")
            if [[ -n "$unhealthy" ]]; then
                echo -e "  ${RED}❌ Unhealthy containers: $unhealthy${NC}"
            fi
            
        else
            echo -e "  ${YELLOW}⚠️  Docker daemon not running${NC}"
        fi
    else
        echo -e "  ${YELLOW}⚠️  Docker not installed${NC}"
    fi
}

# Function to run E2E connectivity test
test_e2e_connectivity() {
    echo -e "${BLUE}🔗 End-to-End Connectivity Test:${NC}"
    
    # Test full request flow: Frontend -> Orchestrator -> Guardian
    echo -n "  Testing request flow... "
    
    # Simulate a request that would go through the full stack
    local test_payload='{"v":"1","session_id":"e2e-test","message":"System health check"}'
    
    start_time=$(date +%s%N)
    if response=$(curl -s -X POST -H "Content-Type: application/json" \
        -d "$test_payload" "$ORCHESTRATOR_URL/api/chat" 2>/dev/null); then
        end_time=$(date +%s%N)
        e2e_time_ms=$(( (end_time - start_time) / 1000000 ))
        
        local response_received=$(echo "$response" | jq -r '.response // ""')
        if [[ -n "$response_received" ]]; then
            echo -e "${GREEN}✅ OK (${e2e_time_ms}ms)${NC}"
        else
            echo -e "${RED}❌ NO RESPONSE${NC}"
        fi
    else
        echo -e "${RED}❌ FAILED${NC}"
    fi
}

# Main health check execution
main() {
    local overall_status=0
    
    echo -e "${BLUE}📊 Basic Service Health:${NC}"
    
    # Check core services
    check_endpoint "$ORCHESTRATOR_URL/health" "Orchestrator" || overall_status=1
    check_endpoint "$GUARDIAN_URL/guardian/health" "Guardian" || overall_status=1
    check_endpoint "$VOICE_URL/health" "Voice Service" || overall_status=1
    check_endpoint "$FRONTEND_URL" "Frontend" || overall_status=1
    
    echo ""
    
    # Detailed checks
    check_guardian_detailed || overall_status=1
    echo ""
    
    test_orchestrator || overall_status=1
    echo ""
    
    test_voice_pipeline || overall_status=1
    echo ""
    
    test_e2e_connectivity || overall_status=1
    echo ""
    
    check_system_resources
    echo ""
    
    check_docker_services
    echo ""
    
    # Final summary
    echo "======================================"
    if [[ $overall_status -eq 0 ]]; then
        echo -e "${GREEN}🎉 All health checks passed! Alice v2 is ready.${NC}"
    else
        echo -e "${YELLOW}⚠️  Some health checks failed. Review issues above.${NC}"
    fi
    
    echo ""
    echo -e "${BLUE}💡 Next steps:${NC}"
    echo "  • Run integration tests: pnpm test:e2e"
    echo "  • Start autonomous testing: ./scripts/dev-start.sh --with-testing"
    echo "  • Monitor performance: open http://localhost:8501"
    echo "  • View Guardian status: watch -n1 'curl -s localhost:8787/guardian/health | jq'"
    
    return $overall_status
}

# Check dependencies
if ! command -v curl >/dev/null; then
    echo -e "${RED}❌ curl is required but not installed${NC}"
    exit 1
fi

if ! command -v jq >/dev/null; then
    echo -e "${RED}❌ jq is required but not installed${NC}"
    exit 1
fi

# Run main health check
main