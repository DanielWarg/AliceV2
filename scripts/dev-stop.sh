#!/bin/bash
# Alice v2 Development Cleanup Script  
# Graceful shutdown of all services with resource cleanup

set -e

# Color codes
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Alice v2 Standard Ports
PORTS="8000,8787,8001,8501,3000"

echo -e "${BLUE}🛑 Alice v2 Development Cleanup${NC}"
echo "==============================="

# Function to gracefully stop services
stop_services() {
    echo -e "${YELLOW}📋 Stopping Alice v2 services...${NC}"
    
    # Stop Docker services first
    echo "  Stopping Docker containers..."
    docker compose down 2>/dev/null || true
    
    # Stop individual processes on our ports
    echo "  Stopping processes on ports: $PORTS"
    
    for port in $(echo $PORTS | tr ',' ' '); do
        if lsof -ti:$port >/dev/null 2>&1; then
            echo "    - Port $port: $(lsof -ti:$port | wc -l) processes"
            
            # Try graceful shutdown first (SIGTERM)
            lsof -ti:$port | xargs kill -TERM 2>/dev/null || true
            sleep 2
            
            # Force kill if still running (SIGKILL)  
            if lsof -ti:$port >/dev/null 2>&1; then
                echo "      Forcing shutdown..."
                lsof -ti:$port | xargs kill -9 2>/dev/null || true
            fi
        fi
    done
    
    echo -e "${GREEN}✅ Services stopped${NC}"
}

# Function to clean up development artifacts
cleanup_artifacts() {
    echo -e "${YELLOW}🧹 Cleaning up development artifacts...${NC}"
    
    # Clean up Python cache files
    find . -name "*.pyc" -delete 2>/dev/null || true
    find . -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true
    
    # Clean up Node.js artifacts  
    find . -name ".next" -type d -exec rm -rf {} + 2>/dev/null || true
    
    # Clean up temporary test files
    if [[ -d "services/tester/temp" ]]; then
        rm -rf services/tester/temp/* 2>/dev/null || true
    fi
    
    # Clean up old log files (keep last 5 days)
    if [[ -d "services/tester/runs" ]]; then
        find services/tester/runs -name "20*" -type d -mtime +5 -exec rm -rf {} + 2>/dev/null || true
    fi
    
    echo -e "${GREEN}✅ Artifacts cleaned${NC}"
}

# Function to deactivate Python virtual environments
deactivate_venvs() {
    echo -e "${YELLOW}🐍 Deactivating Python virtual environments...${NC}"
    
    # Deactivate current virtual environment if active
    if [[ -n "$VIRTUAL_ENV" ]]; then
        echo "  Deactivating: $(basename $VIRTUAL_ENV)"
        deactivate 2>/dev/null || true
    fi
    
    echo -e "${GREEN}✅ Virtual environments deactivated${NC}"
}

# Function to check final cleanup
verify_cleanup() {
    echo -e "${YELLOW}🔍 Verifying cleanup...${NC}"
    
    local still_running=()
    
    for port in $(echo $PORTS | tr ',' ' '); do
        if lsof -ti:$port >/dev/null 2>&1; then
            still_running+=($port)
        fi
    done
    
    if [[ ${#still_running[@]} -eq 0 ]]; then
        echo -e "${GREEN}✅ All ports are clean${NC}"
    else
        echo -e "${YELLOW}⚠️  Some processes still running on ports: ${still_running[*]}${NC}"
        echo "  Run manually: lsof -ti:PORT | xargs kill -9"
    fi
    
    # Check Docker containers
    local alice_containers=$(docker ps --filter "name=alice" --filter "name=redis" --filter "name=ollama" --format "{{.Names}}" 2>/dev/null)
    
    if [[ -z "$alice_containers" ]]; then
        echo -e "${GREEN}✅ No Alice containers running${NC}"
    else
        echo -e "${YELLOW}⚠️  Some containers still running:${NC}"
        echo "$alice_containers"
    fi
}

# Function to show resource recovery
show_resource_status() {
    echo -e "${BLUE}💻 System Resource Status:${NC}"
    
    if command -v python3 >/dev/null; then
        local ram_usage=$(python3 -c "import psutil; print(f'{psutil.virtual_memory().percent:.1f}')")
        echo "  RAM Usage: ${ram_usage}%"
        
        local cpu_usage=$(python3 -c "import psutil; print(f'{psutil.cpu_percent(interval=1):.1f}')")
        echo "  CPU Usage: ${cpu_usage}%"
    fi
    
    local disk_free=$(df -h . | awk 'NR==2{print $4}')
    echo "  Free Disk: $disk_free"
    
    local load_avg=$(uptime | awk -F'load average:' '{print $2}' | cut -d',' -f1 | xargs)
    echo "  Load Average: $load_avg"
}

# Function to show cleanup summary
show_summary() {
    echo ""
    echo -e "${GREEN}🎉 Alice v2 Development Environment Cleaned${NC}"
    echo "=============================================="
    echo ""
    echo -e "${BLUE}What was cleaned:${NC}"
    echo "  ✅ All service processes stopped"
    echo "  ✅ Docker containers stopped"  
    echo "  ✅ Python cache files removed"
    echo "  ✅ Node.js build artifacts removed"
    echo "  ✅ Temporary test files cleaned"
    echo "  ✅ Virtual environments deactivated"
    echo ""
    echo -e "${BLUE}💡 To restart development:${NC}"
    echo "  ./scripts/dev-start.sh"
    echo ""
    echo -e "${BLUE}💡 For a completely fresh start:${NC}"
    echo "  ./scripts/dev-start.sh --clean"
    echo "  (This will rebuild virtual environments)"
}

# Main execution
main() {
    # Parse arguments
    local force_cleanup=false
    local keep_docker=false
    
    while [[ $# -gt 0 ]]; do
        case $1 in
            --force|-f)
                force_cleanup=true
                shift
                ;;
            --keep-docker)
                keep_docker=true
                shift
                ;;
            --help|-h)
                echo "Alice v2 Development Cleanup Script"
                echo ""
                echo "Usage: $0 [OPTIONS]"
                echo ""
                echo "Options:"
                echo "  --force, -f       Force cleanup without confirmation"
                echo "  --keep-docker     Keep Docker containers running"
                echo "  --help, -h        Show this help message"
                exit 0
                ;;
            *)
                echo -e "${RED}❌ Unknown option: $1${NC}"
                exit 1
                ;;
        esac
    done
    
    # Confirmation unless force
    if [[ "$force_cleanup" != true ]]; then
        echo -e "${YELLOW}⚠️  This will stop all Alice v2 services and clean up artifacts.${NC}"
        read -p "Continue? (y/N) " -n 1 -r
        echo
        
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            echo "Cleanup cancelled."
            exit 0
        fi
    fi
    
    # Execute cleanup steps
    stop_services
    echo ""
    
    deactivate_venvs
    echo ""
    
    cleanup_artifacts  
    echo ""
    
    verify_cleanup
    echo ""
    
    show_resource_status
    echo ""
    
    show_summary
}

# Trap Ctrl+C for graceful exit
trap 'echo -e "\n${YELLOW}Cleanup interrupted by user${NC}"; exit 1' INT

# Run main function with all arguments
main "$@"