#!/bin/bash
# Demo script för RL CI pipeline (T1-T4)

set -e
echo "🚀 Running RL CI Pipeline Demo (T1-T4)"
echo "======================================"

echo ""
echo "📦 Step 1: RL Setup"
echo "-------------------"
make rl-setup

echo ""
echo "🏗️  Step 2: Build Dataset (simulated - using existing data)"  
echo "----------------------------------------------------------"
# Skapa några dummy telemetry filer för demo
mkdir -p data/telemetry
if [ ! -f "data/telemetry/sample.jsonl" ]; then
    echo '{"timestamp":"2025-09-07T16:00:00Z","session_id":"demo1","message":"Hej Alice","intent":"greeting","tool_success":true,"latency_ms":245,"energy_wh":0.003,"safety_ok":true}' > data/telemetry/sample.jsonl
    echo '{"timestamp":"2025-09-07T16:00:30Z","session_id":"demo2","message":"Vad är klockan?","intent":"time_query","tool_success":true,"latency_ms":123,"energy_wh":0.002,"safety_ok":true}' >> data/telemetry/sample.jsonl
    echo "📝 Created sample telemetry data"
fi

# Kör dataset build (eller simulera det)
if [ -f "services/rl/pipelines/build_dataset.py" ]; then
    echo "🔧 Running real dataset build..."
    make rl-build-ci || echo "⚠️  Dataset build failed, continuing with demo..."
else
    echo "📋 Simulating dataset build (T1-T2)..."
    mkdir -p data/rl/v1
    echo '{"stats":{"total_episodes":2,"avg_reward_total":0.85,"reward_coverage":0.9},"source":"data/telemetry","created":"2025-09-07T16:00:00Z"}' > data/rl/v1/MANIFEST.json
fi

echo ""  
echo "🔬 Step 3: Run Benchmark Suite (T4)"
echo "-----------------------------------"
make rl-benchmark-full

echo ""
echo "🚦 Step 4: Validate SLO Gates"
echo "-----------------------------"
make rl-assert

echo ""
echo "🎉 SUCCESS: RL CI Pipeline Complete!"
echo "===================================="
echo ""
echo "📊 Results summary:"
if [ -f "artefacts/rl_bench/summary.json" ]; then
    echo "📁 Artifacts: artefacts/rl_bench/summary.json"
    echo "📋 Key metrics:"
    jq -r '.metrics | to_entries[] | "  \(.key): \(.value)"' artefacts/rl_bench/summary.json
else
    echo "⚠️  No summary.json found"
fi

echo ""
echo "✅ This demonstrates the complete T1-T4 pipeline that runs in GitHub Actions!"
echo "🔄 In CI, this pipeline runs on every PR to validate RL performance."