#!/usr/bin/env bash
set -euo pipefail

echo "🛑 Stoppar alla containers…"
docker compose down -v --remove-orphans || true
echo "✅ Stoppat."


