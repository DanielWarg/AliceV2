#!/bin/bash
# Quick deployment script för Alice RL pipeline

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}🚀 Alice RL Quick Deploy${NC}"
echo "=========================="

# Check if we're in the right directory
if [ ! -f "services/orchestrator/src/router/policy.py" ]; then
    echo -e "${RED}❌ Error: Must run from alice-v2 root directory${NC}"
    exit 1
fi

# Check for telemetry data
TELEMETRY_FILE="services/orchestrator/telemetry.jsonl"
if [ ! -f "$TELEMETRY_FILE" ]; then
    echo -e "${YELLOW}⚠️  Warning: No telemetry file found at $TELEMETRY_FILE${NC}"
    echo "Creating dummy telemetry for demo..."
    
    # Create minimal telemetry for demo
    mkdir -p services/orchestrator
    cat > "$TELEMETRY_FILE" << 'EOF'
{"timestamp": "2024-09-04T10:00:00Z", "intent": "greeting", "route": "micro", "tool": "none", "success": 1, "latency_ms": 120, "cost_usd": 0.001, "cache_hit": 0, "guardian_state": "NORMAL", "lang": "sv"}
{"timestamp": "2024-09-04T10:01:00Z", "intent": "weather", "route": "planner", "tool": "weather.lookup", "success": 1, "latency_ms": 450, "cost_usd": 0.003, "cache_hit": 0, "guardian_state": "NORMAL", "lang": "sv"}
{"timestamp": "2024-09-04T10:02:00Z", "intent": "calculation", "route": "deep", "tool": "calculator", "success": 1, "latency_ms": 800, "cost_usd": 0.005, "cache_hit": 1, "guardian_state": "NORMAL", "lang": "sv"}
{"timestamp": "2024-09-04T10:03:00Z", "intent": "complex_query", "route": "planner", "tool": "search", "success": 1, "latency_ms": 650, "cost_usd": 0.004, "cache_hit": 0, "guardian_state": "ALERT", "lang": "sv"}
{"timestamp": "2024-09-04T10:04:00Z", "intent": "greeting", "route": "micro", "tool": "none", "success": 1, "latency_ms": 90, "cost_usd": 0.001, "cache_hit": 1, "guardian_state": "NORMAL", "lang": "sv"}
EOF
    echo -e "${GREEN}✅ Demo telemetry created${NC}"
fi

# Move to RL directory
cd services/rl

echo -e "${BLUE}📊 Step 1: Building dataset...${NC}"
python automate_rl_pipeline.py --step dataset

echo -e "${BLUE}🧠 Step 2-4: Training models...${NC}" 
python automate_rl_pipeline.py --step routing
python automate_rl_pipeline.py --step tools  
python automate_rl_pipeline.py --step cache

echo -e "${BLUE}🔍 Step 5: Offline evaluation...${NC}"
python automate_rl_pipeline.py --step eval

echo -e "${BLUE}📦 Step 6: Packaging policies...${NC}"
python automate_rl_pipeline.py --step package

# Find the latest package
LATEST_PACKAGE=$(ls -t deploy/policy_pack_*.json 2>/dev/null | head -1)

if [ -z "$LATEST_PACKAGE" ]; then
    echo -e "${RED}❌ No policy package found${NC}"
    exit 1
fi

echo -e "${GREEN}📦 Package created: $(basename "$LATEST_PACKAGE")${NC}"

echo -e "${BLUE}🕯️  Step 7: Deploying to canary...${NC}"
python deploy/promote.py --stage canary --pack "$LATEST_PACKAGE" --destination "../../services/orchestrator/src/policies/live"

echo -e "${YELLOW}⏳ Waiting 30 seconds for canary stability...${NC}"
sleep 30

echo -e "${BLUE}🚀 Step 8: Deploying to production...${NC}"
python deploy/promote.py --stage prod --pack "$LATEST_PACKAGE" --destination "../../services/orchestrator/src/policies/live" --skip-stability-check

echo ""
echo -e "${GREEN}🎉 RL DEPLOYMENT COMPLETE! 🎉${NC}"
echo -e "${GREEN}Alice is now powered by RL policies!${NC}"
echo ""
echo -e "${BLUE}Next steps:${NC}"
echo "1. Restart orchestrator: docker-compose restart orchestrator"  
echo "2. Monitor performance in production"
echo "3. Collect more telemetry and retrain as needed"
echo ""
echo -e "${YELLOW}Policy files location:${NC}"
echo "services/orchestrator/src/policies/live/"