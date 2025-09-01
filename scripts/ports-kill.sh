#!/usr/bin/env bash
set -euo pipefail

PORTS=("8000" "8501" "8787" "11434" "18000")
echo "🔪 Killing processes on ports: ${PORTS[*]}"

for p in "${PORTS[@]}"; do
  if command -v lsof >/dev/null 2>&1; then
    PIDS=$(lsof -ti tcp:"$p" 2>/dev/null || true)
  else
    # macOS fallback: netstat + awk
    PIDS=$(netstat -vanp tcp 2>/dev/null | awk -v port=".$p" '$4 ~ port {print $9}' 2>/dev/null || true)
  fi

  if [ -n "${PIDS}" ]; then
    echo "  • Port $p → PIDs: $PIDS → SIGTERM"
    echo "$PIDS" | xargs kill 2>/dev/null || true
    sleep 0.5
    # hard kill if still alive
    for pid in $PIDS; do
      if kill -0 "$pid" 2>/dev/null; then
        echo "    ↳ still alive → SIGKILL"
        kill -9 "$pid" 2>/dev/null || true
      fi
    done
  else
    echo "  • Port $p free"
  fi
done

# Stop any remaining Docker containers (if Docker is available)
if command -v docker >/dev/null 2>&1 && docker info >/dev/null 2>&1; then
    echo "🐳 Stopping remaining Docker containers..."
    docker compose down --remove-orphans 2>/dev/null || true
fi

# Kill any remaining Python processes
echo "🐍 Killing remaining Python processes..."
pkill -f "uvicorn|gunicorn|streamlit|services\.orchestrator|services\.guardian" 2>/dev/null || true

echo "✅ Ports cleared."
