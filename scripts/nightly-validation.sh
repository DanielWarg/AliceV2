#!/bin/bash
# Alice v2 Nightly Validation Runner
# Automated testing for continuous validation and Alice training data collection

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
NC='\033[0m' # No Color

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
NIGHTLY_LOG_DIR="$PROJECT_ROOT/test-results/nightly"
TIMESTAMP=$(date +"%Y%m%d_%H%M")
RESULTS_FILE="$NIGHTLY_LOG_DIR/nightly_results_$TIMESTAMP.json"

echo -e "${PURPLE}🌙 Alice v2 Nightly Validation Suite${NC}"
echo -e "${PURPLE}=====================================${NC}"
echo "Timestamp: $(date '+%Y-%m-%d %H:%M:%S')"
echo "Results will be saved to: $RESULTS_FILE"
echo ""

# Create directories
mkdir -p "$NIGHTLY_LOG_DIR"

# Function to log with timestamp
log_with_time() {
    echo -e "$(date '+%H:%M:%S') $1"
}

# Function to check service health
check_service_health() {
    local service_name=$1
    local service_url=$2
    
    log_with_time "🔍 Checking ${service_name}..."
    
    if curl -s --fail --connect-timeout 5 "${service_url}" >/dev/null 2>&1; then
        log_with_time "${GREEN}✅ ${service_name} is healthy${NC}"
        return 0
    else
        log_with_time "${RED}❌ ${service_name} is not responding${NC}"
        return 1
    fi
}

# Function to start services if needed
ensure_services_running() {
    log_with_time "${BLUE}🔧 Ensuring services are running...${NC}"
    
    cd "$PROJECT_ROOT"
    
    # Check and start Orchestrator
    if ! check_service_health "Orchestrator" "http://localhost:8000/"; then
        log_with_time "🚀 Starting Orchestrator service..."
        
        cd services/orchestrator
        
        if [ ! -d ".venv" ]; then
            log_with_time "${RED}❌ Virtual environment not found. Setup required.${NC}"
            exit 1
        fi
        
        source .venv/bin/activate
        
        # Start orchestrator in background
        nohup uvicorn main:app --host 0.0.0.0 --port 8000 > "$NIGHTLY_LOG_DIR/orchestrator_$TIMESTAMP.log" 2>&1 &
        ORCHESTRATOR_PID=$!
        echo $ORCHESTRATOR_PID > "$NIGHTLY_LOG_DIR/orchestrator.pid"
        
        # Wait for service to be ready
        log_with_time "⏳ Waiting for Orchestrator to start..."
        for i in {1..60}; do
            if curl -s --fail --connect-timeout 1 "http://localhost:8000/" >/dev/null 2>&1; then
                log_with_time "${GREEN}✅ Orchestrator started successfully${NC}"
                break
            fi
            sleep 2
        done
        
        if [ $i -eq 60 ]; then
            log_with_time "${RED}❌ Orchestrator failed to start within timeout${NC}"
            cat "$NIGHTLY_LOG_DIR/orchestrator_$TIMESTAMP.log"
            exit 1
        fi
    fi
    
    # Check Guardian (optional)
    if check_service_health "Guardian" "http://localhost:8787/health"; then
        GUARDIAN_AVAILABLE=true
    else
        log_with_time "${YELLOW}⚠️  Guardian not available - some tests will be skipped${NC}"
        GUARDIAN_AVAILABLE=false
    fi
    
    cd "$PROJECT_ROOT"
}

# Function to run the nightly test suite
run_nightly_tests() {
    log_with_time "${BLUE}🧪 Running nightly test scenarios...${NC}"
    
    cd services/orchestrator
    source .venv/bin/activate
    
    # Set environment variables for data collection
    export LOG_DIR="$PROJECT_ROOT/test-results/telemetry"
    export NIGHTLY_RUN=true
    
    # Run nightly scenarios with detailed output
    local test_exit_code=0
    
    if pytest src/tests/test_nightly_scenarios.py -v \
           --tb=short \
           --junit-xml="$NIGHTLY_LOG_DIR/junit_results_$TIMESTAMP.xml" \
           > "$NIGHTLY_LOG_DIR/test_output_$TIMESTAMP.log" 2>&1; then
        log_with_time "${GREEN}✅ Nightly tests completed successfully${NC}"
    else
        test_exit_code=$?
        log_with_time "${YELLOW}⚠️  Nightly tests completed with some failures${NC}"
    fi
    
    # Create results file from JUnit XML if available
    if [ -f "$NIGHTLY_LOG_DIR/junit_results_$TIMESTAMP.xml" ]; then
        # Generate a basic JSON results file for analysis
        cat > "$RESULTS_FILE" << EOF
{
  "summary": {
    "total": $(grep -o 'tests="[0-9]*"' "$NIGHTLY_LOG_DIR/junit_results_$TIMESTAMP.xml" | cut -d'"' -f2 || echo "0"),
    "passed": $(grep -o 'passed="[0-9]*"' "$NIGHTLY_LOG_DIR/junit_results_$TIMESTAMP.xml" | cut -d'"' -f2 || echo "0"),
    "failed": $(grep -o 'failures="[0-9]*"' "$NIGHTLY_LOG_DIR/junit_results_$TIMESTAMP.xml" | cut -d'"' -f2 || echo "0"),
    "duration": $(grep -o 'time="[0-9.]*"' "$NIGHTLY_LOG_DIR/junit_results_$TIMESTAMP.xml" | cut -d'"' -f2 || echo "0")
  },
  "source": "junit_xml",
  "timestamp": "$(date -u +"%Y-%m-%dT%H:%M:%SZ")"
}
EOF
    fi
    
    cd "$PROJECT_ROOT"
    return $test_exit_code
}

# Function to process and analyze results
analyze_results() {
    log_with_time "${BLUE}📊 Analyzing test results...${NC}"
    
    if [ ! -f "$RESULTS_FILE" ]; then
        log_with_time "${RED}❌ Results file not found: $RESULTS_FILE${NC}"
        return 1
    fi
    
    # Extract key metrics using jq (if available)
    if command -v jq >/dev/null 2>&1; then
        local total_tests=$(jq -r '.summary.total // 0' "$RESULTS_FILE" 2>/dev/null || echo "0")
        local passed_tests=$(jq -r '.summary.passed // 0' "$RESULTS_FILE" 2>/dev/null || echo "0")
        local failed_tests=$(jq -r '.summary.failed // 0' "$RESULTS_FILE" 2>/dev/null || echo "0")
        local duration=$(jq -r '.summary.duration // 0' "$RESULTS_FILE" 2>/dev/null || echo "0")
        
        if [ "$total_tests" -gt 0 ]; then
            local success_rate=$(echo "scale=1; $passed_tests * 100 / $total_tests" | bc -l 2>/dev/null || echo "0.0")
            
            log_with_time "📈 Test Results Summary:"
            log_with_time "   Total Tests: $total_tests"
            log_with_time "   Passed: ${GREEN}$passed_tests${NC}"
            log_with_time "   Failed: ${RED}$failed_tests${NC}"
            log_with_time "   Success Rate: ${success_rate}%"
            log_with_time "   Duration: ${duration}s"
            
            # Check if results meet SLO thresholds
            local success_threshold=75.0
            if (( $(echo "$success_rate >= $success_threshold" | bc -l) )); then
                log_with_time "${GREEN}✅ Success rate meets SLO threshold (>=${success_threshold}%)${NC}"
                SLO_COMPLIANT=true
            else
                log_with_time "${RED}❌ Success rate below SLO threshold (<${success_threshold}%)${NC}"
                SLO_COMPLIANT=false
            fi
        fi
    else
        log_with_time "${YELLOW}⚠️  jq not available - limited result analysis${NC}"
        SLO_COMPLIANT=true
    fi
}

# Function to update trend data
update_trends() {
    log_with_time "${BLUE}📈 Updating trend data...${NC}"
    
    local trends_file="$PROJECT_ROOT/test-results/trends/nightly_trends.jsonl"
    mkdir -p "$(dirname "$trends_file")"
    
    # Create trend entry
    local trend_entry=$(cat <<EOF
{
  "timestamp": "$(date -u +"%Y-%m-%dT%H:%M:%SZ")",
  "date": "$(date +"%Y-%m-%d")",
  "time": "$(date +"%H:%M:%S")",
  "results_file": "$RESULTS_FILE",
  "guardian_available": $GUARDIAN_AVAILABLE,
  "slo_compliant": $SLO_COMPLIANT,
  "test_type": "nightly_validation"
}
EOF
)
    
    echo "$trend_entry" >> "$trends_file"
    log_with_time "📝 Trend data updated: $trends_file"
}

# Function to generate daily summary
generate_daily_summary() {
    log_with_time "${BLUE}📋 Generating daily summary...${NC}"
    
    local daily_summary_file="$PROJECT_ROOT/test-results/summaries/nightly/$(date +"%Y%m%d")_nightly_summary.md"
    mkdir -p "$(dirname "$daily_summary_file")"
    
    cat > "$daily_summary_file" << EOF
# Alice v2 Nightly Validation Summary
**Date**: $(date '+%Y-%m-%d %H:%M:%S')
**Run ID**: nightly_$TIMESTAMP

## 🎯 Test Results
$(if [ -f "$RESULTS_FILE" ] && command -v jq >/dev/null 2>&1; then
    total=$(jq -r '.summary.total // 0' "$RESULTS_FILE" 2>/dev/null || echo "0")
    passed=$(jq -r '.summary.passed // 0' "$RESULTS_FILE" 2>/dev/null || echo "0")
    failed=$(jq -r '.summary.failed // 0' "$RESULTS_FILE" 2>/dev/null || echo "0")
    duration=$(jq -r '.summary.duration // 0' "$RESULTS_FILE" 2>/dev/null || echo "0")
    
    if [ "$total" -gt 0 ]; then
        success_rate=$(echo "scale=1; $passed * 100 / $total" | bc -l 2>/dev/null || echo "0.0")
        echo "- **Total Scenarios**: $total"
        echo "- **Passed**: $passed"
        echo "- **Failed**: $failed" 
        echo "- **Success Rate**: ${success_rate}%"
        echo "- **Duration**: ${duration}s"
    else
        echo "- No test results available"
    fi
else
    echo "- Test analysis not available (missing jq or results file)"
fi)

## 🏥 System Health
- **Orchestrator**: ✅ Running
- **Guardian**: $(if [ "$GUARDIAN_AVAILABLE" = true ]; then echo "✅ Available"; else echo "⚠️ Not Available"; fi)

## 📊 SLO Compliance
- **Overall Success Rate**: $(if [ "$SLO_COMPLIANT" = true ]; then echo "✅ PASS"; else echo "❌ FAIL"; fi)

## 📁 Artifacts
- **Results File**: \`$RESULTS_FILE\`
- **Test Output**: \`$NIGHTLY_LOG_DIR/test_output_$TIMESTAMP.log\`
- **Service Logs**: \`$NIGHTLY_LOG_DIR/orchestrator_$TIMESTAMP.log\`

## 🔗 Alice Learning Data
All test interactions have been logged to the structured data collection system for Alice's continuous learning and improvement.

---
*Generated by Alice v2 Nightly Validation Suite*
EOF

    log_with_time "📄 Daily summary generated: $daily_summary_file"
}

# Function to cleanup services
cleanup_services() {
    log_with_time "${YELLOW}🧹 Cleaning up services...${NC}"
    
    # Stop orchestrator if we started it
    if [ -f "$NIGHTLY_LOG_DIR/orchestrator.pid" ]; then
        local pid=$(cat "$NIGHTLY_LOG_DIR/orchestrator.pid" 2>/dev/null || echo "")
        if [ -n "$pid" ] && kill -0 "$pid" 2>/dev/null; then
            log_with_time "Stopping Orchestrator (PID: $pid)..."
            kill "$pid"
            
            # Wait for graceful shutdown
            for i in {1..10}; do
                if ! kill -0 "$pid" 2>/dev/null; then
                    break
                fi
                sleep 1
            done
            
            # Force kill if still running
            if kill -0 "$pid" 2>/dev/null; then
                log_with_time "Force stopping Orchestrator..."
                kill -9 "$pid"
            fi
        fi
        rm -f "$NIGHTLY_LOG_DIR/orchestrator.pid"
    fi
}

# Function to send notifications (placeholder)
send_notifications() {
    log_with_time "${BLUE}📢 Processing notifications...${NC}"
    
    # Placeholder for notification system
    # You could integrate with Slack, Discord, email, etc.
    
    if [ "$SLO_COMPLIANT" != true ]; then
        log_with_time "${RED}🚨 SLO violation detected - notifications would be sent${NC}"
        # Example: curl -X POST $SLACK_WEBHOOK -d '{"text":"Alice v2 Nightly Tests: SLO violation detected"}'
    fi
}

# Main execution flow
main() {
    local overall_success=true
    
    # Set trap for cleanup
    trap cleanup_services EXIT
    
    # Initialize variables
    GUARDIAN_AVAILABLE=false
    SLO_COMPLIANT=true
    
    # Run validation steps
    if ensure_services_running; then
        log_with_time "${GREEN}✅ Services ready${NC}"
    else
        log_with_time "${RED}❌ Failed to start services${NC}"
        overall_success=false
    fi
    
    if [ "$overall_success" = true ]; then
        if run_nightly_tests; then
            log_with_time "${GREEN}✅ Tests completed${NC}"
        else
            log_with_time "${YELLOW}⚠️ Tests completed with issues${NC}"
            # Don't fail overall - tests might have expected failures
        fi
    fi
    
    # Always try to analyze results, even if tests failed
    analyze_results || true
    update_trends || true
    generate_daily_summary || true
    send_notifications || true
    
    # Final summary
    echo ""
    log_with_time "${PURPLE}🌙 Nightly Validation Complete${NC}"
    log_with_time "Results: $RESULTS_FILE"
    log_with_time "Guardian Available: $GUARDIAN_AVAILABLE"
    log_with_time "SLO Compliant: $SLO_COMPLIANT"
    
    if [ "$overall_success" = true ] && [ "$SLO_COMPLIANT" = true ]; then
        log_with_time "${GREEN}✅ Nightly validation successful${NC}"
        exit 0
    else
        log_with_time "${YELLOW}⚠️ Nightly validation completed with issues${NC}"
        exit 1
    fi
}

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --help)
            echo "Alice v2 Nightly Validation Runner"
            echo ""
            echo "Usage: $0 [OPTIONS]"
            echo ""
            echo "Options:"
            echo "  --help           Show this help message"
            echo "  --dry-run        Show what would be done without executing"
            echo ""
            echo "This script runs the complete nightly validation suite including:"
            echo "  - Service health checks and startup"
            echo "  - 20 production scenario tests"
            echo "  - SLO compliance analysis"
            echo "  - Trend tracking"
            echo "  - Daily summary generation"
            echo ""
            exit 0
            ;;
        --dry-run)
            echo "DRY RUN MODE - Would execute nightly validation"
            echo "Services would be checked and started if needed"
            echo "20 production scenarios would be tested"
            echo "Results would be saved to: $RESULTS_FILE"
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            echo "Use --help for usage information"
            exit 1
            ;;
    esac
done

# Run main function
main "$@"