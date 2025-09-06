#!/usr/bin/env python3
"""
Auto Update Manager
Orchestrates automated documentation updates based on code changes and CI triggers.
"""

import json
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import structlog
import yaml


@dataclass
class UpdateTrigger:
    """Configuration for when to trigger documentation updates."""

    file_patterns: List[str]
    update_scripts: List[str]
    description: str
    priority: str  # "high", "medium", "low"


class AutoUpdateManager:
    """Manages automated documentation updates across the project."""

    def __init__(self, project_root: str):
        self.project_root = Path(project_root)
        self.scripts_dir = self.project_root / "scripts" / "auto_docs"
        self.docs_dir = self.project_root / "docs"
        self.logger = structlog.get_logger(__name__)

        # Load update configuration
        self.config = self._load_update_config()

    def _load_update_config(self) -> Dict[str, Any]:
        """Load documentation update configuration."""
        config_file = self.project_root / ".docs-config.yml"

        # Default configuration
        default_config = {
            "update_triggers": {
                "api_changes": UpdateTrigger(
                    file_patterns=["services/**/*.py", "packages/**/*.py"],
                    update_scripts=["generate_api_docs.py"],
                    description="API code changes detected",
                    priority="high",
                ),
                "fibonacci_changes": UpdateTrigger(
                    file_patterns=[
                        "**/fibonacci*.py",
                        "services/orchestrator/src/config/fibonacci.py",
                    ],
                    update_scripts=["update_fibonacci_docs.py"],
                    description="Fibonacci optimization changes",
                    priority="high",
                ),
                "cache_changes": UpdateTrigger(
                    file_patterns=["services/**/cache*.py", "CACHE.md"],
                    update_scripts=["update_cache_docs.py"],
                    description="Cache system changes",
                    priority="medium",
                ),
                "config_changes": UpdateTrigger(
                    file_patterns=[
                        "*.yml",
                        "*.yaml",
                        "*.json",
                        "Dockerfile*",
                        "docker-compose*.yml",
                    ],
                    update_scripts=["mkdocs_config_generator.py"],
                    description="Configuration file changes",
                    priority="medium",
                ),
                "readme_changes": UpdateTrigger(
                    file_patterns=["README.md", "**/README.md"],
                    update_scripts=["mkdocs_config_generator.py"],
                    description="README file changes",
                    priority="low",
                ),
            },
            "validation": {
                "run_on_update": True,
                "fail_on_error": False,
                "skip_external_links": False,
            },
            "deployment": {
                "auto_deploy": False,
                "deploy_branch": "gh-pages",
                "deploy_on_main": True,
            },
            "notifications": {
                "slack_webhook": None,
                "email_recipients": [],
                "github_issues": False,
            },
        }

        if config_file.exists():
            try:
                with open(config_file, "r") as f:
                    user_config = yaml.safe_load(f)
                    # Merge with defaults
                    default_config.update(user_config)
            except Exception as e:
                self.logger.warning(f"Failed to load config file: {e}")

        return default_config

    def detect_changes(
        self, changed_files: Optional[List[str]] = None
    ) -> List[UpdateTrigger]:
        """Detect what documentation updates are needed based on file changes."""
        if changed_files is None:
            changed_files = self._get_changed_files_from_git()

        triggered_updates = []

        for trigger_name, trigger in self.config["update_triggers"].items():
            if self._files_match_patterns(changed_files, trigger.file_patterns):
                self.logger.info(
                    f"Trigger activated: {trigger_name}",
                    description=trigger.description,
                    files=changed_files,
                )
                triggered_updates.append(trigger)

        # Sort by priority
        priority_order = {"high": 0, "medium": 1, "low": 2}
        triggered_updates.sort(key=lambda x: priority_order.get(x.priority, 3))

        return triggered_updates

    def _get_changed_files_from_git(self) -> List[str]:
        """Get list of changed files from git."""
        try:
            # Get files changed in last commit
            result = subprocess.run(
                ["git", "diff", "--name-only", "HEAD~1", "HEAD"],
                cwd=self.project_root,
                capture_output=True,
                text=True,
            )

            if result.returncode == 0:
                return [f.strip() for f in result.stdout.split("\n") if f.strip()]
            else:
                # Fallback to staged files
                result = subprocess.run(
                    ["git", "diff", "--name-only", "--cached"],
                    cwd=self.project_root,
                    capture_output=True,
                    text=True,
                )
                return [f.strip() for f in result.stdout.split("\n") if f.strip()]

        except Exception as e:
            self.logger.warning(f"Failed to get changed files from git: {e}")
            return []

    def _files_match_patterns(self, files: List[str], patterns: List[str]) -> bool:
        """Check if any files match the given patterns."""
        from fnmatch import fnmatch

        for file in files:
            for pattern in patterns:
                if fnmatch(file, pattern):
                    return True
        return False

    def run_update_scripts(self, triggers: List[UpdateTrigger]) -> Dict[str, Any]:
        """Run the update scripts for triggered changes."""
        results = {
            "timestamp": datetime.now().isoformat(),
            "triggers": [],
            "scripts_run": [],
            "errors": [],
            "success": True,
        }

        scripts_to_run = set()

        # Collect all scripts to run
        for trigger in triggers:
            results["triggers"].append(
                {
                    "description": trigger.description,
                    "priority": trigger.priority,
                    "scripts": trigger.update_scripts,
                }
            )
            scripts_to_run.update(trigger.update_scripts)

        # Run each script
        for script_name in scripts_to_run:
            script_path = self.scripts_dir / script_name

            if not script_path.exists():
                error_msg = f"Update script not found: {script_name}"
                self.logger.error(error_msg)
                results["errors"].append(error_msg)
                results["success"] = False
                continue

            try:
                self.logger.info(f"Running update script: {script_name}")

                result = subprocess.run(
                    [sys.executable, str(script_path)],
                    cwd=self.project_root,
                    capture_output=True,
                    text=True,
                    timeout=300,  # 5 minute timeout
                )

                script_result = {
                    "script": script_name,
                    "exit_code": result.returncode,
                    "stdout": result.stdout,
                    "stderr": result.stderr,
                    "duration": "N/A",  # Could track this if needed
                }

                results["scripts_run"].append(script_result)

                if result.returncode != 0:
                    error_msg = f"Script {script_name} failed with exit code {result.returncode}"
                    self.logger.error(error_msg, stderr=result.stderr)
                    results["errors"].append(error_msg)
                    results["success"] = False
                else:
                    self.logger.info(f"Script {script_name} completed successfully")

            except subprocess.TimeoutExpired:
                error_msg = f"Script {script_name} timed out after 5 minutes"
                self.logger.error(error_msg)
                results["errors"].append(error_msg)
                results["success"] = False

            except Exception as e:
                error_msg = f"Failed to run script {script_name}: {e}"
                self.logger.error(error_msg)
                results["errors"].append(error_msg)
                results["success"] = False

        return results

    def validate_documentation(self) -> bool:
        """Run documentation validation after updates."""
        if not self.config["validation"]["run_on_update"]:
            return True

        try:
            validator_script = self.scripts_dir / "documentation_validator.py"
            if not validator_script.exists():
                self.logger.warning(
                    "Documentation validator not found, skipping validation"
                )
                return True

            cmd = [sys.executable, str(validator_script)]
            if self.config["validation"]["fail_on_error"]:
                cmd.append("--fail-on-error")

            result = subprocess.run(
                cmd, cwd=self.project_root, capture_output=True, text=True
            )

            if result.returncode == 0:
                self.logger.info("Documentation validation passed")
                return True
            else:
                self.logger.error(
                    "Documentation validation failed",
                    stderr=result.stderr,
                    stdout=result.stdout,
                )
                return not self.config["validation"]["fail_on_error"]

        except Exception as e:
            self.logger.error(f"Failed to run documentation validation: {e}")
            return not self.config["validation"]["fail_on_error"]

    def deploy_documentation(self) -> bool:
        """Deploy documentation if configured to do so."""
        if not self.config["deployment"]["auto_deploy"]:
            return True

        try:
            # Check if we're on the right branch
            if self.config["deployment"]["deploy_on_main"]:
                result = subprocess.run(
                    ["git", "branch", "--show-current"],
                    cwd=self.project_root,
                    capture_output=True,
                    text=True,
                )

                current_branch = result.stdout.strip()
                if current_branch not in ["main", "master"]:
                    self.logger.info(
                        f"Not on main branch ({current_branch}), skipping deployment"
                    )
                    return True

            # Deploy using MkDocs
            self.logger.info("Deploying documentation...")

            result = subprocess.run(
                ["mkdocs", "gh-deploy", "--clean", "--force"],
                cwd=self.project_root,
                capture_output=True,
                text=True,
            )

            if result.returncode == 0:
                self.logger.info("Documentation deployed successfully")
                return True
            else:
                self.logger.error(
                    "Documentation deployment failed", stderr=result.stderr
                )
                return False

        except Exception as e:
            self.logger.error(f"Failed to deploy documentation: {e}")
            return False

    def send_notifications(self, results: Dict[str, Any]):
        """Send notifications about update results."""
        if not any(
            [
                self.config["notifications"]["slack_webhook"],
                self.config["notifications"]["email_recipients"],
                self.config["notifications"]["github_issues"],
            ]
        ):
            return

        message = self._format_notification_message(results)

        # Slack notification
        if self.config["notifications"]["slack_webhook"]:
            self._send_slack_notification(message, results["success"])

        # Email notification (would need email configuration)
        if self.config["notifications"]["email_recipients"]:
            self.logger.info("Email notifications configured but not implemented")

        # GitHub issue creation (would need GitHub API setup)
        if self.config["notifications"]["github_issues"] and not results["success"]:
            self.logger.info(
                "GitHub issue notifications configured but not implemented"
            )

    def _format_notification_message(self, results: Dict[str, Any]) -> str:
        """Format notification message."""
        status = "✅ SUCCESS" if results["success"] else "❌ FAILED"

        message = f"🧮 Alice v2 Documentation Update {status}\n\n"
        message += f"Timestamp: {results['timestamp']}\n"
        message += f"Scripts run: {len(results['scripts_run'])}\n"
        message += f"Errors: {len(results['errors'])}\n\n"

        if results["triggers"]:
            message += "Triggered by:\n"
            for trigger in results["triggers"]:
                message += (
                    f"  • {trigger['description']} ({trigger['priority']} priority)\n"
                )
            message += "\n"

        if results["errors"]:
            message += "Errors encountered:\n"
            for error in results["errors"]:
                message += f"  • {error}\n"

        return message

    def _send_slack_notification(self, message: str, success: bool):
        """Send Slack notification."""
        webhook_url = self.config["notifications"]["slack_webhook"]
        if not webhook_url:
            return

        try:
            import requests

            color = "good" if success else "danger"
            payload = {
                "attachments": [
                    {
                        "color": color,
                        "title": "Alice v2 Documentation Update",
                        "text": message,
                        "ts": datetime.now().timestamp(),
                    }
                ]
            }

            response = requests.post(webhook_url, json=payload, timeout=10)
            if response.status_code == 200:
                self.logger.info("Slack notification sent successfully")
            else:
                self.logger.error(
                    f"Failed to send Slack notification: {response.status_code}"
                )

        except Exception as e:
            self.logger.error(f"Failed to send Slack notification: {e}")

    def run_full_update(
        self, changed_files: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """Run complete documentation update pipeline."""
        self.logger.info("🚀 Starting documentation update pipeline")

        # Detect changes
        triggers = self.detect_changes(changed_files)

        if not triggers:
            self.logger.info("No documentation updates needed")
            return {
                "timestamp": datetime.now().isoformat(),
                "triggers": [],
                "scripts_run": [],
                "errors": [],
                "success": True,
                "message": "No updates needed",
            }

        # Run update scripts
        results = self.run_update_scripts(triggers)

        # Validate documentation
        if results["success"]:
            validation_passed = self.validate_documentation()
            if not validation_passed:
                results["success"] = False
                results["errors"].append("Documentation validation failed")

        # Deploy documentation
        if results["success"]:
            deployment_success = self.deploy_documentation()
            if not deployment_success:
                results["success"] = False
                results["errors"].append("Documentation deployment failed")

        # Send notifications
        self.send_notifications(results)

        # Log final status
        if results["success"]:
            self.logger.info("✅ Documentation update pipeline completed successfully")
        else:
            self.logger.error(
                "❌ Documentation update pipeline failed", errors=results["errors"]
            )

        return results

    def save_update_report(
        self, results: Dict[str, Any], output_file: str = "docs_update_report.json"
    ):
        """Save update report to file."""
        output_path = self.project_root / output_file

        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(results, f, indent=2, ensure_ascii=False)

        self.logger.info(f"Update report saved to: {output_path}")


def main():
    """Main function to run documentation updates."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Manage automated documentation updates"
    )
    parser.add_argument("--project-root", default=".", help="Project root directory")
    parser.add_argument("--files", nargs="*", help="Specific files that changed")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be updated without running",
    )
    parser.add_argument(
        "--output", default="docs_update_report.json", help="Output report file"
    )

    args = parser.parse_args()

    # Setup logging
    structlog.configure(
        processors=[
            structlog.stdlib.add_log_level,
            structlog.stdlib.PositionalArgumentsFormatter(),
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.stdlib.BoundLogger,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )

    manager = AutoUpdateManager(args.project_root)

    if args.dry_run:
        triggers = manager.detect_changes(args.files)
        print(f"🔍 Detected {len(triggers)} documentation update triggers:")
        for trigger in triggers:
            print(f"  📝 {trigger.description} ({trigger.priority} priority)")
            print(f"     Scripts: {', '.join(trigger.update_scripts)}")
        return

    results = manager.run_full_update(args.files)
    manager.save_update_report(results, args.output)

    # Exit with appropriate code
    sys.exit(0 if results["success"] else 1)


if __name__ == "__main__":
    main()
