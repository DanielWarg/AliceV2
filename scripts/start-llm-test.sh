#!/usr/bin/env bash
set -euo pipefail

echo "🚀 Startar LLM Integration v1 test..."

# Städa portar först
echo "🧹 Städar portar..."
./scripts/ports-kill.sh

# Starta Guardian
echo "🛡️ Startar Guardian..."
cd services/guardian
source .venv/bin/activate
python main.py &
GUARDIAN_PID=$!
cd ../..

# Vänta på Guardian
echo "⏳ Väntar på Guardian..."
sleep 3

# Starta Orchestrator
echo "🎯 Startar Orchestrator..."
cd services/orchestrator
source .venv/bin/activate
uvicorn main:app --reload --port 8000 &
ORCHESTRATOR_PID=$!
cd ../..

# Vänta på Orchestrator
echo "⏳ Väntar på Orchestrator..."
sleep 5

# Testa LLM integration
echo "🧪 Testar LLM integration..."
curl -s -X POST http://localhost:8000/api/orchestrator/chat \
  -H 'Content-Type: application/json' \
  -d '{"v":"1","session_id":"test","lang":"sv","message":"Hej Alice, vad är klockan?"}' \
  | jq .

echo "✅ Test klart!"
echo "PID: Guardian=$GUARDIAN_PID, Orchestrator=$ORCHESTRATOR_PID"
