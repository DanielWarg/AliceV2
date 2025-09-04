#!/bin/bash
# Alice v2 Development Startup Script
# Strict development workflow with port cleanup and service ordering

set -e

echo "🚀 Alice v2 Development Startup"
echo "==============================="

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Alice v2 Standard Ports
ORCHESTRATOR_PORT=8000
GUARDIAN_PORT=8787
VOICE_PORT=8001
DASHBOARD_PORT=8501
WEB_PORT=3000

# Function to check if port is in use
check_port() {
    local port=$1
    if lsof -ti:$port >/dev/null 2>&1; then
        return 0  # Port is in use
    else
        return 1  # Port is free
    fi
}

# Function to kill processes on specific ports
kill_port_processes() {
    local ports=$1
    echo -e "${YELLOW}🧹 Cleaning up existing processes on ports: $ports${NC}"
    
    for port in $(echo $ports | tr ',' ' '); do
        if check_port $port; then
            echo "  - Killing processes on port $port"
            lsof -ti:$port | xargs kill -9 2>/dev/null || true
            sleep 1
        fi
    done
    
    echo -e "${GREEN}✅ Port cleanup complete${NC}"
}

# Function to verify Python virtual environment
check_venv() {
    local service_dir=$1
    
    if [[ ! -d "$service_dir/.venv" ]]; then
        echo -e "${YELLOW}⚠️  No virtual environment found in $service_dir${NC}"
        echo -e "${BLUE}Creating virtual environment...${NC}"
        cd $service_dir
        python -m venv .venv
        source .venv/bin/activate
        pip install -r requirements.txt
        cd - > /dev/null
    fi
    
    # Verify virtual environment activation
    cd $service_dir
    source .venv/bin/activate
    
    if [[ "$VIRTUAL_ENV" != *"$service_dir/.venv"* ]]; then
        echo -e "${RED}❌ Virtual environment not properly activated in $service_dir${NC}"
        exit 1
    fi
    
    echo -e "${GREEN}✅ Virtual environment active: $(basename $VIRTUAL_ENV)${NC}"
    cd - > /dev/null
}

# Function to check if service is healthy
check_service_health() {
    local url=$1
    local service_name=$2
    local max_attempts=30
    local attempt=1
    
    while [ $attempt -le $max_attempts ]; do
        if curl -f -s $url >/dev/null 2>&1; then
            echo -e "${GREEN}✅ $service_name is healthy${NC}"
            return 0
        fi
        
        if [ $attempt -eq 1 ]; then
            echo -e "${BLUE}⏳ Waiting for $service_name to start...${NC}"
        fi
        
        sleep 2
        ((attempt++))
    done
    
    echo -e "${RED}❌ $service_name failed to start after ${max_attempts} attempts${NC}"
    return 1
}

# Main execution
main() {
    # Check if we're in the right directory
    if [[ ! -f "package.json" ]] || [[ ! -d "services" ]]; then
        echo -e "${RED}❌ Please run this script from the Alice v2 root directory${NC}"
        exit 1
    fi
    
    # Step 1: Clean up existing processes
    kill_port_processes "$ORCHESTRATOR_PORT,$GUARDIAN_PORT,$VOICE_PORT,$DASHBOARD_PORT,$WEB_PORT"
    
    # Step 2: Check system resources
    echo -e "${BLUE}📊 Checking system resources...${NC}"
    RAM_USAGE=$(python3 -c "import psutil; print(f'{psutil.virtual_memory().percent:.1f}')")
    echo "  RAM Usage: ${RAM_USAGE}%"
    
    if (( $(echo "$RAM_USAGE > 75.0" | bc -l) )); then
        echo -e "${YELLOW}⚠️  High RAM usage detected. Consider restarting system.${NC}"
    fi
    
    # Step 3: Start infrastructure services (Redis only - Ollama runs on host)
    echo -e "${BLUE}🐳 Starting infrastructure services...${NC}"
    docker compose up -d redis
    sleep 5
    
    # Step 4: Start Python services in dependency order
    
    # Guardian first (system safety)
    echo -e "${BLUE}🛡️  Starting Guardian service...${NC}"
    check_venv "services/guardian"
    cd services/guardian
    source .venv/bin/activate
    uvicorn main:app --reload --host 127.0.0.1 --port $GUARDIAN_PORT &
    GUARDIAN_PID=$!
    cd - > /dev/null
    
    # Wait for Guardian to be healthy
    if ! check_service_health "http://localhost:$GUARDIAN_PORT/guardian/health" "Guardian"; then
        echo -e "${RED}❌ Cannot start without Guardian protection${NC}"
        exit 1
    fi
    
    # Orchestrator second (main API)
    echo -e "${BLUE}🎯 Starting Orchestrator service...${NC}"
    check_venv "services/orchestrator" 
    cd services/orchestrator
    source .venv/bin/activate
    uvicorn main:app --reload --host 127.0.0.1 --port $ORCHESTRATOR_PORT &
    ORCHESTRATOR_PID=$!
    cd - > /dev/null
    
    # Wait for Orchestrator
    check_service_health "http://localhost:$ORCHESTRATOR_PORT/health" "Orchestrator"
    
    # Voice service third
    echo -e "${BLUE}🎤 Starting Voice service...${NC}"
    check_venv "services/voice"
    cd services/voice  
    source .venv/bin/activate
    uvicorn main:app --reload --host 127.0.0.1 --port $VOICE_PORT &
    VOICE_PID=$!
    cd - > /dev/null
    
    # Wait for Voice service
    check_service_health "http://localhost:$VOICE_PORT/health" "Voice Service"
    
    # Step 5: Start frontend
    echo -e "${BLUE}🌐 Starting frontend...${NC}"
    pnpm --filter web dev &
    WEB_PID=$!
    
    # Wait for frontend
    check_service_health "http://localhost:$WEB_PORT" "Frontend"
    
    # Step 6: Optional services
    if [[ "$1" == "--with-testing" ]]; then
        echo -e "${BLUE}🧪 Starting autonomous testing system...${NC}"
        docker compose up -d tester
    fi
    
    if [[ "$1" == "--with-dashboard" ]]; then
        echo -e "${BLUE}📊 Starting observability dashboard...${NC}"
        docker compose up -d dashboard
    fi
    
    # Step 7: Final health check
    echo -e "${BLUE}🔍 Final system health check...${NC}"
    
    services_status=()
    
    if check_service_health "http://localhost:$GUARDIAN_PORT/guardian/health" "Guardian" >/dev/null; then
        services_status+=("Guardian:✅")
    else
        services_status+=("Guardian:❌")
    fi
    
    if check_service_health "http://localhost:$ORCHESTRATOR_PORT/health" "Orchestrator" >/dev/null; then
        services_status+=("Orchestrator:✅")
    else
        services_status+=("Orchestrator:❌")
    fi
    
    if check_service_health "http://localhost:$VOICE_PORT/health" "Voice" >/dev/null; then
        services_status+=("Voice:✅")
    else
        services_status+=("Voice:❌")
    fi
    
    if check_service_health "http://localhost:$WEB_PORT" "Frontend" >/dev/null; then
        services_status+=("Frontend:✅")
    else
        services_status+=("Frontend:❌")
    fi
    
    # Step 8: Display summary
    echo ""
    echo -e "${GREEN}🎉 Alice v2 Development Environment Ready!${NC}"
    echo "=============================================="
    
    for status in "${services_status[@]}"; do
        echo -e "  $status"
    done
    
    echo ""
    echo -e "${BLUE}📍 Service URLs:${NC}"
    echo "  • Frontend:      http://localhost:$WEB_PORT"
    echo "  • Orchestrator:  http://localhost:$ORCHESTRATOR_PORT"
    echo "  • Guardian:      http://localhost:$GUARDIAN_PORT/guardian/health"
    echo "  • Voice Service: http://localhost:$VOICE_PORT"
    
    if [[ "$1" == "--with-dashboard" ]]; then
        echo "  • Dashboard:     http://localhost:$DASHBOARD_PORT"
    fi
    
    echo ""
    echo -e "${YELLOW}💡 Tips:${NC}"
    echo "  • Run './scripts/health-check.sh' to verify all services"
    echo "  • Run './scripts/dev-stop.sh' to cleanly shutdown"
    echo "  • View logs: docker compose logs -f [service]"
    echo "  • Monitor Guardian: watch -n1 'curl -s localhost:$GUARDIAN_PORT/guardian/health | jq'"
    
    echo ""
    echo -e "${BLUE}⌨️  Press Ctrl+C to stop all services${NC}"
    
    # Keep script running and handle shutdown
    trap 'echo -e "\n${YELLOW}🛑 Shutting down Alice v2 development environment...${NC}"; ./scripts/dev-stop.sh; exit 0' INT
    
    # Keep alive
    wait
}

# Parse command line arguments
case "$1" in
    --help|-h)
        echo "Alice v2 Development Startup Script"
        echo ""
        echo "Usage: $0 [OPTIONS]"
        echo ""
        echo "Options:"
        echo "  --with-testing    Start with autonomous testing system"
        echo "  --with-dashboard  Start with observability dashboard"  
        echo "  --help, -h        Show this help message"
        echo ""
        echo "Examples:"
        echo "  $0                     # Start core services only"
        echo "  $0 --with-testing      # Start with testing system"
        echo "  $0 --with-dashboard    # Start with dashboard"
        exit 0
        ;;
esac

# Run main function
main "$@"