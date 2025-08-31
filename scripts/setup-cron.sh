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

# Nightly validation suite - runs at 2:00 AM every day
0 2 * * * cd "$PROJECT_ROOT" && ./scripts/nightly-validation.sh >> "$PROJECT_ROOT/test-results/cron.log" 2>&1

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
echo "  • Nightly validation: Every day at 2:00 AM"
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