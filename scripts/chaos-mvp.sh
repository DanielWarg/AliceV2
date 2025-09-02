#!/usr/bin/env bash
set -euo pipefail

# Minimal chaos monkey: kill a random target, then run auto_verify.
# Opt-in usage: ./scripts/chaos-mvp.sh

TARGETS=("memory" "n8n" "orchestrator" "ollama" "nlu")
KILL_COUNT=${KILL_COUNT:-1}
SLEEP_BETWEEN=${SLEEP_BETWEEN:-5}

for i in $(seq 1 $KILL_COUNT); do
  t=${TARGETS[$RANDOM % ${#TARGETS[@]}]}
  echo "[chaos] Killing container: $t"
  docker compose kill "$t" || true
  sleep "$SLEEP_BETWEEN"
done

echo "[chaos] Running auto_verify after chaos..."
./scripts/auto_verify.sh || true
echo "[chaos] Done."

