#!/usr/bin/env bash
set -euo pipefail

check_port () {
  local p=$1
  if lsof -nP -iTCP:$p -sTCP:LISTEN >/dev/null 2>&1; then
    echo "⚠️ Port $p är upptagen – kör scripts/dev_down.sh eller scripts/ports-kill.sh först."
    exit 1
  fi
}

# Enda exponerade porten i dev
PORT=18000
check_port $PORT

echo "🧹 Rensar gamla containers (om några)…"
docker compose down --remove-orphans >/dev/null 2>&1 || true

echo "🐳 Startar guardian, orchestrator, nlu, dashboard, dev-proxy…"
docker compose up -d --build guardian orchestrator nlu dashboard dev-proxy || true

echo "ℹ️  Startar scheduler (om bild finns)…"
docker compose up -d scheduler || true

echo "⏳ Väntar på dev-proxy på http://localhost:$PORT/health …"
for i in {1..60}; do
  if curl -fsS http://localhost:$PORT/health >/dev/null 2>&1; then
    echo "✅ Uppe: http://localhost:$PORT"
    exit 0
  fi
  sleep 1
done

echo "❌ Proxy svarar inte i tid. Kolla loggar: docker compose logs -f dev-proxy"
exit 1


