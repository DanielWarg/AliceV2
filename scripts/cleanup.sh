#!/usr/bin/env bash
set -euo pipefail

CONF=${1:-config/retention_policy.yaml}
DRY_RUN=${DRY_RUN:-true}
CONFIRM=${CLEANUP_CONFIRM:-false}
LOG_FILE=${LOG_FILE:-logs/cleanup.log}

mkdir -p "$(dirname "$LOG_FILE")"

if ! command -v yq >/dev/null 2>&1; then
  echo "yq krävs (https://github.com/mikefarah/yq)" | tee -a "$LOG_FILE"
  exit 1
fi

ALLOWLIST=( $(yq '.allowlist[]' "$CONF") )

echo "Cleanup start: dry_run=$DRY_RUN confirm=$CONFIRM" | tee -a "$LOG_FILE"

now=$(date +%s)
len=${#ALLOWLIST[@]}
for ((i=0;i<len;i++)); do
  path=$(yq ".rules[$i].path" "$CONF")
  keep_days=$(yq ".rules[$i].keep_days" "$CONF")
  compress_days=$(yq ".rules[$i].compress_after_days" "$CONF")
  mapfile -t patterns < <(yq -r ".rules[$i].patterns[]" "$CONF")
  [[ -z "$path" ]] && continue
  for pat in "${patterns[@]}"; do
    while IFS= read -r -d '' f; do
      mtime=$(stat -f %m "$f" 2>/dev/null || stat -c %Y "$f" 2>/dev/null || echo "$now")
      age_days=$(( (now - mtime)/86400 ))
      if (( age_days >= compress_days )) && [[ ! "$f" =~ \.gz$ ]]; then
        echo "compress: $f (age ${age_days}d)" | tee -a "$LOG_FILE"
        if [[ "$DRY_RUN" != "true" ]]; then
          gzip -f "$f" || true
        fi
      fi
      if (( age_days >= keep_days )); then
        echo "delete: $f (age ${age_days}d)" | tee -a "$LOG_FILE"
        if [[ "$DRY_RUN" != "true" && "$CONFIRM" == "true" ]]; then
          rm -f "$f" || true
        fi
      fi
    done < <(find "$path" -type f -name "${pat##*/}" -print0 2>/dev/null)
  done
done

echo "Cleanup done" | tee -a "$LOG_FILE"

