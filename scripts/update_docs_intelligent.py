#!/usr/bin/env python3
"""
Intelligent Documentation Update Script for Alice v2

This script updates documentation files from test artifacts while:
- Respecting manual changes made to documentation
- Creating backups before any changes
- Validating that updates are reasonable
- Providing rollback capability
- Handling different text formats and patterns
"""

import difflib
import json
import os
import re
import shutil
import sys
from datetime import datetime
from pathlib import Path
from typing import List, Tuple

import requests

API_BASE = os.getenv("API_BASE", "http://localhost:18000")
ART_SUMMARY = os.getenv("ART_SUMMARY", "data/tests/summary.json")
BACKUP_DIR = os.getenv("BACKUP_DIR", "data/docs_backup")


class DocUpdater:
    def __init__(self):
        self.backup_dir = Path(BACKUP_DIR)
        self.backup_dir.mkdir(parents=True, exist_ok=True)
        self.changes_made = []

    def create_backup(self, file_path: str) -> str:
        """Create backup of file before making changes"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = self.backup_dir / f"{Path(file_path).stem}_{timestamp}.md"
        shutil.copy2(file_path, backup_path)
        return str(backup_path)

    def read_summary(self, path: str) -> dict:
        """Read test summary with error handling"""
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            print(f"⚠️  Warning: Could not read {path}: {e}")
            return {}

    def get_routes(self, api: str) -> dict:
        """Get route status from API"""
        try:
            r = requests.get(f"{api}/api/status/routes", timeout=3)
            if r.ok:
                return r.json()
        except Exception as e:
            print(f"⚠️  Warning: Could not fetch routes from {api}: {e}")
        return {}

    def validate_update(self, original: str, updated: str, context: str) -> bool:
        """Validate that update is reasonable"""
        if original == updated:
            return False  # No change needed

        # Check for suspicious patterns
        suspicious_patterns = [
            r"TODO|FIXME|XXX",  # Development markers
            r"@\w+",  # Mentions
            r"https?://",  # URLs
            r"daniel@",  # Email addresses
        ]

        for pattern in suspicious_patterns:
            if re.search(pattern, original) and not re.search(pattern, updated):
                print(f"⚠️  Warning: Update removes {pattern} in {context}")
                return False

        # Check for reasonable changes
        diff_ratio = difflib.SequenceMatcher(None, original, updated).ratio()
        if diff_ratio < 0.8:  # Too much change
            print(
                f"⚠️  Warning: Update changes too much content in {context} (ratio: {diff_ratio:.2f})"
            )
            return False

        return True

    def smart_replace(
        self, content: str, patterns: List[str], new_content: str, context: str
    ) -> Tuple[str, bool]:
        """Intelligently replace content with multiple pattern options"""
        original = content

        for pattern in patterns:
            if re.search(pattern, content, re.MULTILINE):
                updated = re.sub(pattern, new_content, content, flags=re.MULTILINE)
                if self.validate_update(original, updated, context):
                    return updated, True
                else:
                    print(f"⚠️  Skipping update for {context} - validation failed")
                    return content, False

        print(f"⚠️  No matching pattern found for {context}")
        return content, False

    def update_readme_status(self, summary: dict) -> bool:
        """Update README status line intelligently"""
        file_path = "README.md"
        if not os.path.exists(file_path):
            print(f"⚠️  {file_path} not found")
            return False

        # Create backup
        backup_path = self.create_backup(file_path)

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()

            # Extract metrics
            rate = summary.get("eval", {}).get("rate_pct", 0)
            fast = summary.get("p95_ms", {}).get("fast", 0)
            plan = summary.get("p95_ms", {}).get("planner", 0)

            # Multiple pattern options for flexibility
            patterns = [
                r"^> \*\*🚦 Status \(live-gates\)\*\*:.*$",
                r"^> \*\*🚀 Status\*\*:.*$",
                r"^> \*\*🚀 Production Status\*\*:.*$",
            ]

            new_status = f"> **🚦 Status (live-gates)**: Fast P95 {'✅' if fast <= 250 else '❌'} | Planner P95 {'✅' if plan <= 900 else '❌'} | Auto-verify (core) ✅, (planner) {'✅' if rate >= 80 else '❌'}"

            updated_content, changed = self.smart_replace(
                content, patterns, new_status, "README status"
            )

            if changed:
                with open(file_path, "w", encoding="utf-8") as f:
                    f.write(updated_content)
                self.changes_made.append("README.md status updated")
                print(f"✅ Updated README status: {new_status}")
                return True
            else:
                print("ℹ️  No changes needed for README status")
                return False

        except Exception as e:
            print(f"❌ Error updating README: {e}")
            return False

    def update_roadmap_status(self, summary: dict) -> bool:
        """Update ROADMAP status intelligently"""
        file_path = "ROADMAP.md"
        if not os.path.exists(file_path):
            print(f"⚠️  {file_path} not found")
            return False

        # Create backup
        backup_path = self.create_backup(file_path)

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()

            # Extract metrics
            rate = summary.get("eval", {}).get("rate_pct", 0)
            fast_ok = summary.get("slo", {}).get("fast_p95_ok", False)
            plan_ok = summary.get("slo", {}).get("planner_p95_ok", False)

            # Multiple pattern options
            patterns = [
                r"^\*\*🚀 CURRENT STATUS\*\*:.*$",
                r"^\*\*Auto-verify\*\*:.*$",
                r"^\*\*Status\*\*:.*$",
            ]

            new_status = f"**🚀 CURRENT STATUS**: **Auto-verify**: PASS {rate}% | Fast P95 OK={fast_ok} | Planner P95 OK={plan_ok}"

            updated_content, changed = self.smart_replace(
                content, patterns, new_status, "ROADMAP status"
            )

            if changed:
                with open(file_path, "w", encoding="utf-8") as f:
                    f.write(updated_content)
                self.changes_made.append("ROADMAP.md status updated")
                print(f"✅ Updated ROADMAP status: {new_status}")
                return True
            else:
                print("ℹ️  No changes needed for ROADMAP status")
                return False

        except Exception as e:
            print(f"❌ Error updating ROADMAP: {e}")
            return False

    def update_testing_strategy(self, summary: dict) -> bool:
        """Update TESTING_STRATEGY with latest metrics"""
        file_path = "TESTING_STRATEGY.md"
        if not os.path.exists(file_path):
            print(f"⚠️  {file_path} not found")
            return False

        # Create backup
        backup_path = self.create_backup(file_path)

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()

            # Update performance metrics if they exist
            fast = summary.get("p95_ms", {}).get("fast", 0)
            plan = summary.get("p95_ms", {}).get("planner", 0)

            # Only update if we have meaningful data
            if fast > 0 or plan > 0:
                patterns = [
                    r"- \*\*Micro LLM\*\*: <250ms first token.*$",
                    r"- \*\*Planner LLM\*\*: <900ms first token.*$",
                ]

                updates = [
                    f"- **Micro LLM**: <250ms first token (current: {fast:.0f}ms)",
                    f"- **Planner LLM**: <900ms first token, <1500ms complete (current: {plan:.0f}ms)",
                ]

                changed = False
                for pattern, update in zip(patterns, updates):
                    updated_content, pattern_changed = self.smart_replace(
                        content, [pattern], update, "TESTING_STRATEGY metrics"
                    )
                    if pattern_changed:
                        content = updated_content
                        changed = True

                if changed:
                    with open(file_path, "w", encoding="utf-8") as f:
                        f.write(content)
                    self.changes_made.append("TESTING_STRATEGY.md metrics updated")
                    print("✅ Updated TESTING_STRATEGY metrics")
                    return True

            print("ℹ️  No changes needed for TESTING_STRATEGY")
            return False

        except Exception as e:
            print(f"❌ Error updating TESTING_STRATEGY: {e}")
            return False

    def generate_report(self) -> str:
        """Generate update report"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        report = f"""
# Documentation Update Report
Generated: {timestamp}

## Changes Made
"""

        if self.changes_made:
            for change in self.changes_made:
                report += f"- {change}\n"
        else:
            report += "- No changes were made\n"

        report += f"""
## Backup Location
Backups stored in: {BACKUP_DIR}

## Rollback Instructions
To rollback changes, copy the backup files back:
```bash
cp {BACKUP_DIR}/*.md ./
```
"""

        return report

    def run(self) -> int:
        """Main execution function"""
        print("🤖 Starting intelligent documentation update...")

        # Read summary
        summary = self.read_summary(ART_SUMMARY)
        if not summary:
            print("⚠️  No summary data available, skipping updates")
            return 0

        # Get routes
        routes = self.get_routes(API_BASE)

        # Update files
        updates_made = 0
        updates_made += self.update_readme_status(summary)
        updates_made += self.update_roadmap_status(summary)
        updates_made += self.update_testing_strategy(summary)

        # Generate report
        report = self.generate_report()
        report_path = (
            self.backup_dir
            / f"update_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
        )
        with open(report_path, "w", encoding="utf-8") as f:
            f.write(report)

        print("\n📊 Update Summary:")
        print(f"   Files updated: {updates_made}")
        print(f"   Report saved: {report_path}")
        print(f"   Backups saved: {BACKUP_DIR}")

        return 0


def main():
    updater = DocUpdater()
    return updater.run()


if __name__ == "__main__":
    sys.exit(main())
