#!/usr/bin/env bash
# Daily learning ingestion cron script
# Run at 14:00 daily: 0 14 * * * cd /path/to/repo && ./scripts/learn_cron.sh

set -euo pipefail

# Change to repository root
cd "$(dirname "$0")/.."

# Log file
LOG_FILE="logs/learn.log"
mkdir -p logs

# Log start
echo "$(date): Starting daily learning ingestion" >> "$LOG_FILE"

# Run learning ingestion
if make learn >> "$LOG_FILE" 2>&1; then
    echo "$(date): Learning ingestion completed successfully" >> "$LOG_FILE"
    
    # Create daily snapshot
    if curl -s -X POST http://localhost:18000/api/learn/snapshot >/dev/null 2>&1; then
        echo "$(date): Daily snapshot created successfully" >> "$LOG_FILE"
    else
        echo "$(date): Warning: Failed to create daily snapshot" >> "$LOG_FILE"
    fi
else
    echo "$(date): Error: Learning ingestion failed" >> "$LOG_FILE"
    exit 1
fi

# Log completion
echo "$(date): Daily learning ingestion completed" >> "$LOG_FILE"
