#!/usr/bin/env bash
set -euo pipefail

# Repo-rot
REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
mkdir -p "${REPO_DIR}/logs"

LINE="0 14 * * * cd ${REPO_DIR} && ./scripts/auto_verify.sh >> logs/auto_verify.log 2>&1"

# Installera cron-rad (ersätt ev. tidigare auto_verify-rader)
( crontab -l 2>/dev/null | grep -v "auto_verify.sh" ; echo "$LINE" ) | crontab -

echo "✅ Cron installerad: dagligen 14:00"
echo "   Kommandot: $LINE"
#!/bin/bash
# Setup script for Alice v2 automated testing cron jobs

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

echo "🕐 Setting up Alice v2 automated testing cron jobs"
echo "Project root: $PROJECT_ROOT"

# Create temporary crontab file
TEMP_CRON=$(mktemp)

# Get existing crontab (if any)
crontab -l 2>/dev/null > "$TEMP_CRON" || true

# Remove any existing Alice v2 entries
grep -v "Alice v2" "$TEMP_CRON" > "${TEMP_CRON}.clean" || true
mv "${TEMP_CRON}.clean" "$TEMP_CRON"

echo "Adding Alice v2 cron jobs..."

# Add Alice v2 cron jobs
cat >> "$TEMP_CRON" << EOF

# Alice v2 Automated Testing Schedule
# Generated on $(date)

# Daily auto-verify with docs update - runs at 14:00 every day
0 14 * * * cd "$PROJECT_ROOT" && ./scripts/auto_verify.sh >> "$PROJECT_ROOT/test-results/auto_verify.log" 2>&1

# Daily cleanup dry-run - runs at 14:30 every day
30 14 * * * cd "$PROJECT_ROOT" && DRY_RUN=true CLEANUP_CONFIRM=false bash ./scripts/cleanup.sh >> "$PROJECT_ROOT/logs/cleanup.log" 2>&1

# Weekly cleanup apply - runs at 03:30 on Sundays
30 3 * * 0 cd "$PROJECT_ROOT" && DRY_RUN=false CLEANUP_CONFIRM=true bash ./scripts/cleanup.sh >> "$PROJECT_ROOT/logs/cleanup.log" 2>&1

# Weekly comprehensive test - runs at 3:00 AM every Sunday  
0 3 * * 0 cd "$PROJECT_ROOT" && ./scripts/run-real-tests.sh --all --start-services >> "$PROJECT_ROOT/test-results/weekly.log" 2>&1

# Health check - runs every 4 hours during business days
0 */4 * * 1-5 cd "$PROJECT_ROOT" && curl -sf http://localhost:8000/health > /dev/null || echo "$(date): Orchestrator health check failed" >> "$PROJECT_ROOT/test-results/health.log"

EOF

# Install the crontab
if crontab "$TEMP_CRON"; then
    echo "✅ Cron jobs installed successfully"
else
    echo "❌ Failed to install cron jobs"
    exit 1
fi

# Cleanup
rm -f "$TEMP_CRON"

# Display installed cron jobs
echo ""
echo "📋 Installed cron jobs:"
echo "===================="
crontab -l | grep -A 10 "Alice v2"

echo ""
echo "🔧 Setup complete!"
echo ""
echo "Cron jobs configured:"
echo "  • Auto-verify: Every day at 14:00"
echo "  • Weekly comprehensive test: Every Sunday at 3:00 AM"  
echo "  • Health checks: Every 4 hours (business days)"
echo ""
echo "Log files:"
echo "  • Nightly: $PROJECT_ROOT/test-results/cron.log"
echo "  • Weekly: $PROJECT_ROOT/test-results/weekly.log"
echo "  • Health: $PROJECT_ROOT/test-results/health.log"
echo ""
echo "To remove Alice v2 cron jobs:"
echo "  crontab -e  # then delete Alice v2 section"
echo ""
echo "To view current cron jobs:"
echo "  crontab -l"