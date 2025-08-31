#!/bin/bash
# Alice v2 Real Integration Test Runner
# Runs tests against actual running services

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}🚀 Alice v2 Real Integration Test Runner${NC}"
echo "=================================================="

# Function to check if service is running
check_service() {
    local service_name=$1
    local service_url=$2
    local required=$3
    
    echo -e "🔍 Checking ${service_name}..."
    
    if curl -s --fail --connect-timeout 3 "${service_url}" >/dev/null 2>&1; then
        echo -e "${GREEN}✅ ${service_name} is running${NC}"
        return 0
    else
        if [ "$required" = "true" ]; then
            echo -e "${RED}❌ ${service_name} is NOT running (REQUIRED)${NC}"
            return 1
        else
            echo -e "${YELLOW}⚠️  ${service_name} is not running (optional)${NC}"
            return 0
        fi
    fi
}

# Function to start services if needed
start_services() {
    echo -e "\n${YELLOW}🔧 Starting required services...${NC}"
    
    cd "$(dirname "$0")/.." # Go to project root
    
    # Start orchestrator service
    echo "Starting Orchestrator service..."
    cd services/orchestrator
    
    # Check if virtual environment exists
    if [ ! -d ".venv" ]; then
        echo -e "${RED}❌ Virtual environment not found. Run: python -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt${NC}"
        exit 1
    fi
    
    # Activate venv and start service in background
    source .venv/bin/activate
    
    # Check if already running
    if ! curl -s --fail --connect-timeout 1 "http://localhost:8000/" >/dev/null 2>&1; then
        echo "🚀 Starting Orchestrator on port 8000..."
        nohup uvicorn main:app --host 0.0.0.0 --port 8000 > orchestrator.log 2>&1 &
        ORCHESTRATOR_PID=$!
        echo $ORCHESTRATOR_PID > orchestrator.pid
        
        # Wait for service to start
        echo "⏳ Waiting for Orchestrator to start..."
        for i in {1..30}; do
            if curl -s --fail --connect-timeout 1 "http://localhost:8000/" >/dev/null 2>&1; then
                echo -e "${GREEN}✅ Orchestrator started successfully${NC}"
                break
            fi
            sleep 1
        done
        
        if [ $i -eq 30 ]; then
            echo -e "${RED}❌ Orchestrator failed to start${NC}"
            cat orchestrator.log
            exit 1
        fi
    else
        echo -e "${GREEN}✅ Orchestrator already running${NC}"
    fi
    
    cd ../..
}

# Function to stop services
stop_services() {
    echo -e "\n${YELLOW}🛑 Stopping services...${NC}"
    
    # Stop orchestrator if we started it
    if [ -f "services/orchestrator/orchestrator.pid" ]; then
        PID=$(cat services/orchestrator/orchestrator.pid)
        if kill -0 $PID 2>/dev/null; then
            echo "Stopping Orchestrator (PID: $PID)..."
            kill $PID
            rm services/orchestrator/orchestrator.pid
        fi
    fi
}

# Function to run test suite
run_test_suite() {
    local test_type=$1
    echo -e "\n${BLUE}🧪 Running ${test_type} tests...${NC}"
    echo "=================================================="
    
    cd services/orchestrator
    source .venv/bin/activate
    
    case $test_type in
        "unit")
            pytest src/tests/test_integration.py -v
            ;;
        "real")
            pytest src/tests/test_real_integration.py -v --tb=short
            ;;
        "chaos")
            pytest src/tests/test_chaos_engineering.py -v --tb=short
            ;;
        "all")
            echo -e "${BLUE}Running all test suites...${NC}"
            pytest src/tests/test_integration.py src/tests/test_real_integration.py -v --tb=short
            ;;
        *)
            echo -e "${RED}❌ Unknown test type: $test_type${NC}"
            exit 1
            ;;
    esac
    
    cd ../..
}

# Parse command line arguments
TEST_TYPE="real"
START_SERVICES="false"
STOP_AFTER="true"

while [[ $# -gt 0 ]]; do
    case $1 in
        --unit)
            TEST_TYPE="unit"
            shift
            ;;
        --real)
            TEST_TYPE="real"
            shift
            ;;
        --chaos)
            TEST_TYPE="chaos"
            shift
            ;;
        --all)
            TEST_TYPE="all"
            shift
            ;;
        --start-services)
            START_SERVICES="true"
            shift
            ;;
        --no-stop)
            STOP_AFTER="false"
            shift
            ;;
        --help)
            echo "Alice v2 Real Integration Test Runner"
            echo ""
            echo "Usage: $0 [OPTIONS]"
            echo ""
            echo "Options:"
            echo "  --unit           Run unit tests (with mocks)"
            echo "  --real           Run real integration tests (default)"
            echo "  --chaos          Run chaos engineering tests"
            echo "  --all            Run all test suites"
            echo "  --start-services Start required services automatically"
            echo "  --no-stop        Don't stop services after tests"
            echo "  --help           Show this help message"
            echo ""
            echo "Examples:"
            echo "  $0 --real                    # Run real tests (requires services running)"
            echo "  $0 --chaos --start-services  # Start services and run chaos tests"
            echo "  $0 --all --start-services    # Start services and run all tests"
            exit 0
            ;;
        *)
            echo -e "${RED}❌ Unknown option: $1${NC}"
            echo "Use --help for usage information"
            exit 1
            ;;
    esac
done

# Main execution flow
echo -e "${BLUE}Test Configuration:${NC}"
echo "  Test Type: $TEST_TYPE"
echo "  Start Services: $START_SERVICES"
echo "  Stop After: $STOP_AFTER"
echo ""

# Trap to cleanup services on exit
if [ "$START_SERVICES" = "true" ] && [ "$STOP_AFTER" = "true" ]; then
    trap stop_services EXIT
fi

# Check service status
echo -e "${BLUE}📋 Service Status Check${NC}"
echo "=================================================="

# Always check orchestrator (required)
if ! check_service "Orchestrator" "http://localhost:8000/" "true"; then
    if [ "$START_SERVICES" = "true" ]; then
        start_services
    else
        echo -e "${RED}❌ Orchestrator is required but not running.${NC}"
        echo "Either start it manually or use --start-services flag"
        exit 1
    fi
fi

# Check Guardian (optional for some tests)
check_service "Guardian" "http://localhost:8787/health" "false"

# Check Redis (optional)
check_service "Redis" "http://localhost:6379/" "false" || echo -e "${YELLOW}⚠️  Redis connection not tested (may be running)${NC}"

echo ""

# Run the tests
run_test_suite $TEST_TYPE

# Test results summary
TEST_EXIT_CODE=$?

echo ""
echo "=================================================="
if [ $TEST_EXIT_CODE -eq 0 ]; then
    echo -e "${GREEN}🎉 All tests passed!${NC}"
else
    echo -e "${RED}❌ Some tests failed (exit code: $TEST_EXIT_CODE)${NC}"
fi

echo -e "${BLUE}📊 Check test results in:${NC}"
echo "  - test-results/raw-logs/"
echo "  - test-results/summaries/"
echo "  - test-results/alice-learning-report.json"
echo ""

exit $TEST_EXIT_CODE