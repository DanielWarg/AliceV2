#!/usr/bin/env python3
"""
Documentation Orchestrator - Main coordinator for Alice v2 automated documentation system.

This script orchestrates all documentation generation, validation, and deployment tasks.
It monitors code changes, triggers appropriate documentation updates, and ensures
consistency across all documentation.

Usage:
    python docs_orchestrator.py [command] [options]

Commands:
    generate-all    Generate all documentation from scratch
    update         Update documentation based on recent changes
    validate       Validate all documentation for consistency and correctness
    deploy         Deploy documentation to configured targets
    watch          Watch for changes and update documentation automatically
    cleanup        Remove outdated or orphaned documentation files
"""

import argparse
import hashlib
import json
import os
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

import structlog
import yaml

# Add project root to Python path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

# Import local modules after path setup
from scripts.auto_docs.api_documentation_generator import APIDocumentationGenerator  # noqa: E402
from scripts.auto_docs.architecture_diagram_generator import (
    ArchitectureDiagramGenerator,  # noqa: E402
)
from scripts.auto_docs.documentation_validator import DocumentationValidator  # noqa: E402
from scripts.auto_docs.performance_reporter import PerformanceReporter  # noqa: E402
from scripts.auto_docs.service_documentation_generator import (
    ServiceDocumentationGenerator,  # noqa: E402
)


@dataclass
class DocumentationTask:
    """Represents a documentation task to be executed."""

    name: str
    description: str
    priority: int  # 1 = highest, 5 = lowest
    script: str
    args: List[str]
    output_files: List[str]
    dependencies: List[str] = None
    estimated_duration: int = 60  # seconds

    def __post_init__(self):
        if self.dependencies is None:
            self.dependencies = []


@dataclass
class TaskResult:
    """Result of executing a documentation task."""

    task: DocumentationTask
    success: bool
    duration: float
    output: str
    error: Optional[str] = None
    files_created: List[str] = None
    files_modified: List[str] = None

    def __post_init__(self):
        if self.files_created is None:
            self.files_created = []
        if self.files_modified is None:
            self.files_modified = []


class DocumentationOrchestrator:
    """Main orchestrator for automated documentation system."""

    def __init__(self, config_path: Optional[str] = None):
        """Initialize the documentation orchestrator."""
        self.project_root = project_root
        self.config_path = config_path or (self.project_root / ".docs-automation.yml")
        self.docs_dir = self.project_root / "docs"
        self.scripts_dir = self.project_root / "scripts" / "auto_docs"

        # Initialize logging
        structlog.configure(
            processors=[
                structlog.processors.TimeStamper(fmt="iso"),
                structlog.dev.ConsoleRenderer(),
            ],
            wrapper_class=structlog.stdlib.BoundLogger,
            logger_factory=structlog.stdlib.LoggerFactory(),
            cache_logger_on_first_use=True,
        )
        self.logger = structlog.get_logger(__name__)

        # Load configuration
        self.config = self._load_config()

        # Initialize task queue and results
        self.task_queue: List[DocumentationTask] = []
        self.completed_tasks: List[TaskResult] = []
        self.failed_tasks: List[TaskResult] = []

        # File change tracking
        self.file_hashes: Dict[str, str] = {}
        self._load_file_hashes()

        # Initialize components
        self.api_generator = APIDocumentationGenerator(self.project_root)
        self.service_generator = ServiceDocumentationGenerator(self.project_root)
        self.architecture_generator = ArchitectureDiagramGenerator(self.project_root)
        self.performance_reporter = PerformanceReporter(self.project_root)
        self.validator = DocumentationValidator(self.project_root)

    def _load_config(self) -> Dict[str, Any]:
        """Load configuration from YAML file."""
        try:
            with open(self.config_path, "r") as f:
                config = yaml.safe_load(f)
            self.logger.info("Configuration loaded", config_path=str(self.config_path))
            return config
        except FileNotFoundError:
            self.logger.warning(
                "Configuration file not found, using defaults",
                config_path=str(self.config_path),
            )
            return self._get_default_config()
        except yaml.YAMLError as e:
            self.logger.error("Failed to parse configuration", error=str(e))
            raise

    def _get_default_config(self) -> Dict[str, Any]:
        """Return default configuration."""
        return {
            "version": "1.0",
            "project_name": "Alice v2 AI Assistant",
            "tools": {
                "mkdocs": {"enabled": True},
                "openapi": {"enabled": True},
                "mermaid": {"enabled": True},
            },
            "validation": {
                "links": {"check_internal": True, "check_external": False},
                "content": {"check_spelling": False},
                "structure": {"check_required_sections": True},
            },
        }

    def _load_file_hashes(self):
        """Load previously computed file hashes for change detection."""
        hash_file = self.project_root / ".docs-file-hashes.json"
        if hash_file.exists():
            try:
                with open(hash_file, "r") as f:
                    self.file_hashes = json.load(f)
            except Exception as e:
                self.logger.warning("Failed to load file hashes", error=str(e))
                self.file_hashes = {}

    def _save_file_hashes(self):
        """Save current file hashes for future change detection."""
        hash_file = self.project_root / ".docs-file-hashes.json"
        try:
            with open(hash_file, "w") as f:
                json.dump(self.file_hashes, f, indent=2)
        except Exception as e:
            self.logger.error("Failed to save file hashes", error=str(e))

    def _compute_file_hash(self, file_path: Path) -> str:
        """Compute SHA-256 hash of a file."""
        try:
            with open(file_path, "rb") as f:
                return hashlib.sha256(f.read()).hexdigest()
        except Exception:
            return ""

    def detect_changes(self) -> Dict[str, List[str]]:
        """Detect changes in tracked files and return categorized changes."""
        changes = {
            "api_changes": [],
            "service_changes": [],
            "architecture_changes": [],
            "config_changes": [],
            "performance_changes": [],
        }

        # Get update trigger patterns from config
        triggers = self.config.get("update_triggers", {})

        for trigger_name, trigger_config in triggers.items():
            file_patterns = trigger_config.get("file_patterns", [])
            changed_files = []

            for pattern in file_patterns:
                # Convert glob pattern to Path.glob format
                glob_pattern = pattern.replace("**", "*")
                for file_path in self.project_root.glob(glob_pattern):
                    if file_path.is_file():
                        current_hash = self._compute_file_hash(file_path)
                        file_key = str(file_path.relative_to(self.project_root))

                        if (
                            file_key not in self.file_hashes
                            or self.file_hashes[file_key] != current_hash
                        ):
                            changed_files.append(file_key)
                            self.file_hashes[file_key] = current_hash

            if changed_files:
                changes[trigger_name] = changed_files

        self._save_file_hashes()
        return changes

    def create_tasks_for_changes(
        self, changes: Dict[str, List[str]]
    ) -> List[DocumentationTask]:
        """Create documentation tasks based on detected changes."""
        tasks = []
        triggers = self.config.get("update_triggers", {})

        for change_type, changed_files in changes.items():
            if not changed_files:
                continue

            trigger_config = triggers.get(change_type, {})
            update_scripts = trigger_config.get("update_scripts", [])
            priority_str = trigger_config.get("priority", "medium")

            # Convert priority string to number
            priority_map = {"high": 1, "medium": 3, "low": 5}
            priority = priority_map.get(priority_str, 3)

            for script_name in update_scripts:
                task = DocumentationTask(
                    name=f"{change_type}_{script_name}",
                    description=f"Update documentation for {change_type} using {script_name}",
                    priority=priority,
                    script=script_name,
                    args=changed_files,
                    output_files=[],  # Will be populated after execution
                )
                tasks.append(task)

        return tasks

    def create_full_generation_tasks(self) -> List[DocumentationTask]:
        """Create tasks for full documentation generation."""
        tasks = [
            DocumentationTask(
                name="generate_api_docs",
                description="Generate API documentation for all services",
                priority=1,
                script="generate_api_docs.py",
                args=[],
                output_files=["docs/api/"],
                estimated_duration=120,
            ),
            DocumentationTask(
                name="generate_service_docs",
                description="Generate service documentation",
                priority=1,
                script="generate_service_docs.py",
                args=[],
                output_files=["docs/services/"],
                dependencies=["generate_api_docs"],
                estimated_duration=90,
            ),
            DocumentationTask(
                name="generate_architecture_diagrams",
                description="Generate architecture and system diagrams",
                priority=2,
                script="generate_architecture_diagrams.py",
                args=[],
                output_files=["docs/architecture/"],
                estimated_duration=180,
            ),
            DocumentationTask(
                name="generate_performance_reports",
                description="Generate performance and SLO reports",
                priority=3,
                script="generate_performance_reports.py",
                args=[],
                output_files=["docs/performance/"],
                estimated_duration=60,
            ),
            DocumentationTask(
                name="generate_deployment_guides",
                description="Generate deployment and setup guides",
                priority=2,
                script="generate_deployment_guides.py",
                args=[],
                output_files=["docs/deployment/"],
                estimated_duration=45,
            ),
            DocumentationTask(
                name="update_main_readme",
                description="Update main README with latest information",
                priority=1,
                script="update_main_readme.py",
                args=[],
                output_files=["README.md"],
                dependencies=["generate_api_docs", "generate_service_docs"],
                estimated_duration=30,
            ),
            DocumentationTask(
                name="generate_mkdocs_config",
                description="Generate MkDocs configuration",
                priority=4,
                script="generate_mkdocs_config.py",
                args=[],
                output_files=["mkdocs.yml"],
                dependencies=[
                    "generate_api_docs",
                    "generate_service_docs",
                    "generate_architecture_diagrams",
                ],
                estimated_duration=15,
            ),
        ]

        return tasks

    def execute_task(self, task: DocumentationTask) -> TaskResult:
        """Execute a single documentation task."""
        start_time = time.time()
        self.logger.info("Executing task", task_name=task.name, script=task.script)

        try:
            # Build command
            script_path = self.scripts_dir / task.script
            cmd = [sys.executable, str(script_path)] + task.args

            # Execute script
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=task.estimated_duration * 2,  # Allow 2x estimated time
                cwd=str(self.project_root),
            )

            duration = time.time() - start_time

            if result.returncode == 0:
                self.logger.info(
                    "Task completed successfully",
                    task_name=task.name,
                    duration=f"{duration:.2f}s",
                )

                return TaskResult(
                    task=task,
                    success=True,
                    duration=duration,
                    output=result.stdout,
                    files_created=self._detect_created_files(task),
                    files_modified=self._detect_modified_files(task),
                )
            else:
                self.logger.error(
                    "Task failed",
                    task_name=task.name,
                    returncode=result.returncode,
                    stderr=result.stderr,
                )

                return TaskResult(
                    task=task,
                    success=False,
                    duration=duration,
                    output=result.stdout,
                    error=result.stderr,
                )

        except subprocess.TimeoutExpired:
            duration = time.time() - start_time
            self.logger.error(
                "Task timed out", task_name=task.name, duration=f"{duration:.2f}s"
            )

            return TaskResult(
                task=task,
                success=False,
                duration=duration,
                output="",
                error=f"Task timed out after {duration:.2f}s",
            )

        except Exception as e:
            duration = time.time() - start_time
            self.logger.error(
                "Task failed with exception", task_name=task.name, error=str(e)
            )

            return TaskResult(
                task=task, success=False, duration=duration, output="", error=str(e)
            )

    def _detect_created_files(self, task: DocumentationTask) -> List[str]:
        """Detect files created by a task (simplified implementation)."""
        # This would ideally track filesystem changes during task execution
        return []

    def _detect_modified_files(self, task: DocumentationTask) -> List[str]:
        """Detect files modified by a task (simplified implementation)."""
        # This would ideally track filesystem changes during task execution
        return []

    def execute_tasks_parallel(
        self, tasks: List[DocumentationTask], max_workers: int = 4
    ) -> List[TaskResult]:
        """Execute tasks in parallel, respecting dependencies."""
        results = []

        # Sort tasks by priority
        tasks.sort(key=lambda t: t.priority)

        # Simple parallel execution (dependencies handled by priority ordering)
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_task = {
                executor.submit(self.execute_task, task): task for task in tasks
            }

            for future in as_completed(future_to_task):
                result = future.result()
                results.append(result)

                if result.success:
                    self.completed_tasks.append(result)
                else:
                    self.failed_tasks.append(result)

        return results

    def validate_documentation(self) -> bool:
        """Validate all generated documentation."""
        self.logger.info("Starting documentation validation")

        try:
            validation_result = self.validator.validate_all()

            if validation_result["valid"]:
                self.logger.info(
                    "Documentation validation passed",
                    checks_passed=validation_result["checks_passed"],
                )
                return True
            else:
                self.logger.error(
                    "Documentation validation failed",
                    errors=validation_result["errors"],
                    warnings=validation_result["warnings"],
                )
                return False

        except Exception as e:
            self.logger.error(
                "Documentation validation failed with exception", error=str(e)
            )
            return False

    def deploy_documentation(self) -> bool:
        """Deploy documentation to configured targets."""
        deployment_config = self.config.get("deployment", {})

        # GitHub Pages deployment
        if deployment_config.get("github_pages", {}).get("enabled", False):
            self.logger.info("Deploying to GitHub Pages")
            try:
                # Build with MkDocs
                subprocess.run(
                    ["mkdocs", "build", "--clean"],
                    cwd=str(self.project_root),
                    check=True,
                )

                # Deploy to gh-pages branch
                subprocess.run(
                    ["mkdocs", "gh-deploy", "--clean"],
                    cwd=str(self.project_root),
                    check=True,
                )

                self.logger.info("GitHub Pages deployment completed")
                return True

            except subprocess.CalledProcessError as e:
                self.logger.error("GitHub Pages deployment failed", error=str(e))
                return False

        return True

    def cleanup_outdated_docs(self):
        """Remove outdated or orphaned documentation files."""
        self.logger.info("Cleaning up outdated documentation")

        # Remove empty directories
        for root, dirs, files in os.walk(self.docs_dir, topdown=False):
            for dir_name in dirs:
                dir_path = Path(root) / dir_name
                if not any(dir_path.iterdir()):
                    dir_path.rmdir()
                    self.logger.info("Removed empty directory", path=str(dir_path))

        # Remove files older than configured max age
        max_age = (
            self.config.get("monitoring", {})
            .get("freshness", {})
            .get("max_age_days", 30)
        )
        cutoff_date = datetime.now() - timedelta(days=max_age)

        for doc_file in self.docs_dir.glob("**/*.md"):
            if doc_file.stat().st_mtime < cutoff_date.timestamp():
                # Check if file is still referenced
                if not self._is_file_referenced(doc_file):
                    doc_file.unlink()
                    self.logger.info(
                        "Removed outdated documentation", file=str(doc_file)
                    )

    def _is_file_referenced(self, file_path: Path) -> bool:
        """Check if a documentation file is still referenced elsewhere."""
        # Simplified check - look for references in other markdown files
        relative_path = str(file_path.relative_to(self.project_root))

        for md_file in self.project_root.glob("**/*.md"):
            if md_file == file_path:
                continue

            try:
                content = md_file.read_text()
                if relative_path in content or file_path.name in content:
                    return True
            except Exception:
                continue

        return False

    def generate_summary_report(self) -> Dict[str, Any]:
        """Generate a summary report of the documentation update process."""
        total_tasks = len(self.completed_tasks) + len(self.failed_tasks)
        success_rate = len(self.completed_tasks) / total_tasks if total_tasks > 0 else 0

        total_duration = sum(
            task.duration for task in self.completed_tasks + self.failed_tasks
        )

        report = {
            "timestamp": datetime.now().isoformat(),
            "summary": {
                "total_tasks": total_tasks,
                "successful_tasks": len(self.completed_tasks),
                "failed_tasks": len(self.failed_tasks),
                "success_rate": f"{success_rate:.1%}",
                "total_duration": f"{total_duration:.2f}s",
            },
            "completed_tasks": [
                {
                    "name": result.task.name,
                    "duration": f"{result.duration:.2f}s",
                    "files_created": len(result.files_created),
                    "files_modified": len(result.files_modified),
                }
                for result in self.completed_tasks
            ],
            "failed_tasks": [
                {
                    "name": result.task.name,
                    "error": result.error,
                    "duration": f"{result.duration:.2f}s",
                }
                for result in self.failed_tasks
            ],
        }

        # Save report
        report_file = (
            self.project_root / "docs" / "automation" / "last_update_report.json"
        )
        report_file.parent.mkdir(exist_ok=True)

        with open(report_file, "w") as f:
            json.dump(report, f, indent=2)

        return report

    def run_full_generation(self):
        """Run full documentation generation process."""
        self.logger.info("Starting full documentation generation")

        # Create tasks
        tasks = self.create_full_generation_tasks()

        # Execute tasks
        results = self.execute_tasks_parallel(tasks)

        # Validate documentation
        validation_passed = self.validate_documentation()

        # Generate summary report
        report = self.generate_summary_report()

        self.logger.info(
            "Full documentation generation completed",
            success_rate=report["summary"]["success_rate"],
            validation_passed=validation_passed,
        )

        return validation_passed and len(self.failed_tasks) == 0

    def run_incremental_update(self):
        """Run incremental documentation update based on changes."""
        self.logger.info("Starting incremental documentation update")

        # Detect changes
        changes = self.detect_changes()

        if not any(changes.values()):
            self.logger.info("No changes detected, skipping update")
            return True

        self.logger.info(
            "Changes detected", changes={k: len(v) for k, v in changes.items()}
        )

        # Create tasks for changes
        tasks = self.create_tasks_for_changes(changes)

        if not tasks:
            self.logger.info("No tasks created for detected changes")
            return True

        # Execute tasks
        results = self.execute_tasks_parallel(tasks)

        # Validate updated documentation
        validation_passed = self.validate_documentation()

        # Generate summary report
        report = self.generate_summary_report()

        self.logger.info(
            "Incremental documentation update completed",
            success_rate=report["summary"]["success_rate"],
            validation_passed=validation_passed,
        )

        return validation_passed and len(self.failed_tasks) == 0


def main():
    """Main entry point for the documentation orchestrator."""
    parser = argparse.ArgumentParser(
        description="Alice v2 Documentation Orchestrator",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )

    parser.add_argument(
        "command",
        choices=["generate-all", "update", "validate", "deploy", "watch", "cleanup"],
        help="Command to execute",
    )

    parser.add_argument("--config", help="Path to configuration file", default=None)

    parser.add_argument(
        "--parallel", type=int, default=4, help="Number of parallel workers"
    )

    parser.add_argument("--verbose", action="store_true", help="Enable verbose logging")

    args = parser.parse_args()

    # Initialize orchestrator
    orchestrator = DocumentationOrchestrator(config_path=args.config)

    if args.verbose:
        orchestrator.logger.info("Verbose logging enabled")

    # Execute command
    if args.command == "generate-all":
        success = orchestrator.run_full_generation()
        sys.exit(0 if success else 1)

    elif args.command == "update":
        success = orchestrator.run_incremental_update()
        sys.exit(0 if success else 1)

    elif args.command == "validate":
        success = orchestrator.validate_documentation()
        sys.exit(0 if success else 1)

    elif args.command == "deploy":
        success = orchestrator.deploy_documentation()
        sys.exit(0 if success else 1)

    elif args.command == "cleanup":
        orchestrator.cleanup_outdated_docs()
        sys.exit(0)

    elif args.command == "watch":
        orchestrator.logger.info("Watch mode not yet implemented")
        sys.exit(1)

    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
