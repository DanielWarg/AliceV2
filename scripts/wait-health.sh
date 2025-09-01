#!/usr/bin/env bash
set -euo pipefail
URL="${1:?health URL}"; SECS="${2:-30}"
for i in $(seq 1 "$SECS"); do
  code=$(curl -s -o /dev/null -w "%{http_code}" "$URL" || true)
  if [ "$code" = "200" ]; then echo "OK after $i s"; exit 0; fi
  sleep 1
done
echo "Health never reached 200 after ${SECS}s" >&2
exit 1
