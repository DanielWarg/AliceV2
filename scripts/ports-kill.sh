#!/usr/bin/env bash
set -euo pipefail

echo "🧹 Städar portar 8000, 8787, 8501..."

PORTS=("8000" "8787" "8501")
for p in "${PORTS[@]}"; do
  echo "→ städar port $p"
  
  # döda lokala lyssnare
  PIDS=$(lsof -t -iTCP:$p -sTCP:LISTEN 2>/dev/null || true)
  if [ -n "${PIDS}" ]; then
    echo "  - hittade PIDs: $PIDS"
    kill -TERM $PIDS 2>/dev/null || true
    sleep 1
    PIDS=$(lsof -t -iTCP:$p -sTCP:LISTEN 2>/dev/null || true)
    if [ -n "${PIDS}" ]; then
      echo "  - tvingar kill på: $PIDS"
      kill -KILL $PIDS 2>/dev/null || true
    fi
  else
    echo "  - inga processer på port $p"
  fi
  
  # stoppa containers på porten
  CIDS=$(docker ps --filter "publish=$p" -q 2>/dev/null || true)
  if [ -n "${CIDS}" ]; then
    echo "  - stoppar containers: $CIDS"
    docker stop $CIDS >/dev/null 2>&1 || true
  fi
done

# Stoppa alla compose services
echo "→ stoppar docker compose"
docker compose down --remove-orphans 2>/dev/null || true

# Döda alla kvarhängande uvicorn/python processer
echo "→ dödar kvarhängande processer"
pkill -f "uvicorn|gunicorn|streamlit|services\.orchestrator|services\.guardian" 2>/dev/null || true

echo "✅ Klart! Alla portar är nu fria."
