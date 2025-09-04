#!/usr/bin/env bash
set -euo pipefail
export SLACK_WEBHOOK_URL="${SLACK_WEBHOOK_URL:-}"
export GITHUB_TOKEN="${GITHUB_TOKEN:-}"
docker compose -f docker-compose.yml -f docker-compose.watchdog.yml up -d --build watchdog
docker compose logs -f watchdog