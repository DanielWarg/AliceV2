#!/usr/bin/env bash
# T4 - Dataset Building Script
# Called by CI to build and validate dataset
set -euo pipefail

echo "🏗️  Building Alice vNext Dataset v1"
echo "📂 Working directory: $(pwd)"
echo "🐍 Python version: $(python3 --version)"
echo

# Build dataset with default parameters
echo "📊 Running dataset pipeline..."
PYTHONPATH=. python3 services/rl/pipelines/build_dataset.py \
    --src data/telemetry \
    --out data/rl/v1 \
    --val_ratio 0.1 \
    --test_ratio 0.1 \
    --max_latency_ok 900

echo
echo "📋 Dataset build complete"
echo "📁 Output files:"
ls -la data/rl/v1/

echo
echo "📊 Quality report summary:"
if [ -f "data/rl/v1/report.json" ]; then
    python3 -c "
import json
with open('data/rl/v1/report.json') as f:
    report = json.load(f)
    print(f\"   Episodes: {report.get('total_episodes', 'N/A')}\")
    print(f\"   Quality Index: {report.get('quality_index', 'N/A'):.3f}\")
    print(f\"   Status: {report.get('quality_requirements', {}).get('status', 'UNKNOWN')}\")
"
else
    echo "   ❌ No report.json found"
fi

echo
echo "✅ Dataset build script completed"