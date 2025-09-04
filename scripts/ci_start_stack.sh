#!/usr/bin/env bash
set -euo pipefail

echo "🐳 CI start stack..."

# Hårda timeouts så CI inte hänger
export COMPOSE_HTTP_TIMEOUT=300

# Bygg med cache om möjligt (GitHub Actions tar hand om docker layer cache)
docker compose -f docker-compose.yml -f docker-compose.ci.yml up -d --build

echo "⌛ Väntar in health..."
# 60s grace med exponential backoff
for i in {1..30}; do
  ok=0
  set +e
  curl -fsS http://localhost:18000/health >/dev/null && ok=$((ok+1))
  curl -fsS http://localhost:8787/health >/dev/null && ok=$((ok+1))
  # NLU ligger ofta sist – ge den tid:
  curl -fsS http://localhost:9002/health >/dev/null && ok=$((ok+1))
  set -e
  if [ "$ok" -ge 3 ]; then
    echo "✅ Alla health endpoints svarar."
    exit 0
  fi
  sleep 2
done

echo "❌ Health timeout – dumpar loggar."
docker compose -f docker-compose.yml -f docker-compose.ci.yml ps
docker compose -f docker-compose.yml -f docker-compose.ci.yml logs --since=10m || true
exit 1