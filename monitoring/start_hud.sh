#!/bin/bash
# Start Alice v2 Production HUD
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "🤖 Starting Alice v2 Production HUD..."
echo ""

# Check if streamlit is installed
if ! command -v streamlit &> /dev/null; then
    echo "📦 Installing dependencies..."
    pip install -r requirements.txt
fi

# Create data directories if they don't exist
mkdir -p /data/telemetry /data/tests

echo "🌐 Starting HUD on http://localhost:8501"
echo "📊 Dashboard will show:"
echo "  • Guardian state timeline (GREEN/YELLOW/RED)"
echo "  • Route latency trends (P50/P95)"
echo "  • Error budget burn rates"
echo "  • Test success rates over time"
echo ""
echo "💡 Make sure Guardian and Orchestrator are running:"
echo "   docker compose up -d guardian orchestrator"
echo ""

# Start Streamlit
streamlit run alice_hud.py --server.port 8501 --server.address localhost