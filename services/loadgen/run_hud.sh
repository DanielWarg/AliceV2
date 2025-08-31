#!/bin/bash
# Run Loadgen HUD - Real-time brownout testing dashboard
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Find latest loadgen run if no directory specified
if [ -z "$1" ]; then
    TELEMETRY_DIR="/data/telemetry"
    if [ -d "$TELEMETRY_DIR" ]; then
        LATEST_RUN=$(ls -1t "$TELEMETRY_DIR"/loadgen_* 2>/dev/null | head -1)
        if [ -n "$LATEST_RUN" ]; then
            echo "📊 Using latest run: $(basename "$LATEST_RUN")"
            RUN_DIR="$LATEST_RUN"
        else
            echo "❌ No loadgen runs found in $TELEMETRY_DIR"
            exit 1
        fi
    else
        echo "❌ Telemetry directory not found: $TELEMETRY_DIR"
        exit 1
    fi
else
    RUN_DIR="$1"
    if [ ! -d "$RUN_DIR" ]; then
        echo "❌ Run directory not found: $RUN_DIR"
        exit 1
    fi
fi

echo "🚀 Starting Loadgen HUD..."
echo "📁 Run directory: $RUN_DIR"
echo "🌐 Dashboard will open at: http://localhost:8501"
echo ""

# Run Streamlit with the run directory
streamlit run hud.py -- --run-dir "$RUN_DIR"