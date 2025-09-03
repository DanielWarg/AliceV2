#!/usr/bin/env bash
set -euo pipefail

CONF=${1:-config/retention_policy.yaml}
DRY_RUN=${DRY_RUN:-true}
CONFIRM=${CLEANUP_CONFIRM:-false}
LOG_FILE=${LOG_FILE:-logs/cleanup.log}

# Safety checks
if [[ "$CONFIRM" == "true" && "$DRY_RUN" != "true" ]]; then
    echo "⚠️  WARNING: Running cleanup with CONFIRM=true and DRY_RUN=false"
    echo "   This will permanently delete files!"
    echo "   Press Ctrl+C to abort or wait 10 seconds to continue..."
    sleep 10
fi

# Ensure we're in the right directory
if [[ ! -f "README.md" ]]; then
    echo "❌ Error: Must run from Alice v2 project root" | tee -a "$LOG_FILE"
    exit 1
fi

mkdir -p "$(dirname "$LOG_FILE")"

if ! command -v yq >/dev/null 2>&1; then
  echo "yq krävs (https://github.com/mikefarah/yq)" | tee -a "$LOG_FILE"
  exit 1
fi

ALLOWLIST=( $(yq '.allowlist[]' "$CONF") )

echo "Cleanup start: dry_run=$DRY_RUN confirm=$CONFIRM" | tee -a "$LOG_FILE"

# Create backup if not dry run
if [[ "$DRY_RUN" != "true" && "$CONFIRM" == "true" ]]; then
    BACKUP_DIR="data/cleanup_backup/$(date +%Y%m%d_%H%M%S)"
    echo "📦 Creating backup in $BACKUP_DIR..." | tee -a "$LOG_FILE"
    mkdir -p "$BACKUP_DIR"
    
    # Backup files that will be deleted
    for allowlist_path in "${ALLOWLIST[@]}"; do
        if [[ -d "$allowlist_path" ]]; then
            echo "   Backing up $allowlist_path..." | tee -a "$LOG_FILE"
            cp -r "$allowlist_path" "$BACKUP_DIR/" 2>/dev/null || true
        fi
    done
fi

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

# Summary
echo "" | tee -a "$LOG_FILE"
echo "Cleanup done" | tee -a "$LOG_FILE"
if [[ "$DRY_RUN" != "true" && "$CONFIRM" == "true" && -n "${BACKUP_DIR:-}" ]]; then
    echo "📦 Backup created: $BACKUP_DIR" | tee -a "$LOG_FILE"
    echo "   To restore: cp -r $BACKUP_DIR/* ./" | tee -a "$LOG_FILE"
fi

