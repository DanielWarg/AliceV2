#!/usr/bin/env python3
"""
Documentation Validator
Validates documentation quality, links, and consistency across the project.
"""

import json
import re
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

import markdown
import requests
import yaml


@dataclass
class ValidationResult:
    """Result of a validation check."""

    file_path: str
    check_name: str
    status: str  # "pass", "warning", "error"
    message: str
    line_number: Optional[int] = None


class DocumentationValidator:
    """Validates documentation quality and consistency."""

    def __init__(self, project_root: str):
        self.project_root = Path(project_root)
        self.results: List[ValidationResult] = []
        self.markdown_files: List[Path] = []
        self.links_cache: Dict[str, bool] = {}

        # Load validation rules
        self.rules = self._load_validation_rules()

    def _load_validation_rules(self) -> Dict:
        """Load validation rules configuration."""
        return {
            "max_line_length": 120,
            "required_sections": ["Overview", "Usage", "Installation"],
            "forbidden_words": ["TODO", "FIXME", "XXX"],
            "require_headers": True,
            "check_external_links": True,
            "check_internal_links": True,
            "markdown_extensions": [".md", ".markdown", ".mkd"],
            "ignore_patterns": [
                "node_modules/**",
                ".venv/**",
                "**/__pycache__/**",
                "**/test-results/**",
                "**/data/**",
            ],
        }

    def discover_markdown_files(self) -> List[Path]:
        """Discover all markdown files in the project."""
        markdown_files = []

        for ext in self.rules["markdown_extensions"]:
            for file_path in self.project_root.rglob(f"*{ext}"):
                # Check if file should be ignored
                should_ignore = False
                for pattern in self.rules["ignore_patterns"]:
                    if file_path.match(pattern):
                        should_ignore = True
                        break

                if not should_ignore:
                    markdown_files.append(file_path)

        return sorted(markdown_files)

    def validate_file_structure(self, file_path: Path) -> List[ValidationResult]:
        """Validate the structure of a markdown file."""
        results = []

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()
                lines = content.split("\n")
        except Exception as e:
            results.append(
                ValidationResult(
                    str(file_path), "file_read_error", "error", f"Cannot read file: {e}"
                )
            )
            return results

        # Check for headers
        if self.rules["require_headers"]:
            has_h1 = any(line.strip().startswith("# ") for line in lines)
            if not has_h1:
                results.append(
                    ValidationResult(
                        str(file_path),
                        "missing_h1_header",
                        "warning",
                        "File should have at least one H1 header (# )",
                    )
                )

        # Check line length
        for i, line in enumerate(lines, 1):
            if len(line) > self.rules["max_line_length"]:
                results.append(
                    ValidationResult(
                        str(file_path),
                        "line_too_long",
                        "warning",
                        f"Line exceeds {self.rules['max_line_length']} characters",
                        i,
                    )
                )

        # Check for forbidden words
        for i, line in enumerate(lines, 1):
            for word in self.rules["forbidden_words"]:
                if word in line.upper():
                    results.append(
                        ValidationResult(
                            str(file_path),
                            "forbidden_word",
                            "warning",
                            f"Contains potentially problematic word: {word}",
                            i,
                        )
                    )

        return results

    def validate_links(self, file_path: Path) -> List[ValidationResult]:
        """Validate all links in a markdown file."""
        results = []

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()
        except Exception as e:
            return [
                ValidationResult(
                    str(file_path), "file_read_error", "error", f"Cannot read file: {e}"
                )
            ]

        # Find all markdown links
        link_pattern = r"\[([^\]]*)\]\(([^)]+)\)"
        links = re.findall(link_pattern, content)

        for link_text, link_url in links:
            result = self._validate_single_link(file_path, link_text, link_url)
            if result:
                results.append(result)

        # Find all reference-style links
        ref_link_pattern = r"\[([^\]]*)\]:\s*([^\s]+)"
        ref_links = re.findall(ref_link_pattern, content)

        for ref_name, ref_url in ref_links:
            result = self._validate_single_link(file_path, ref_name, ref_url)
            if result:
                results.append(result)

        return results

    def _validate_single_link(
        self, file_path: Path, link_text: str, link_url: str
    ) -> Optional[ValidationResult]:
        """Validate a single link."""
        # Skip anchor links and mailto links
        if link_url.startswith("#") or link_url.startswith("mailto:"):
            return None

        # Check external links
        if link_url.startswith(("http://", "https://")):
            if self.rules["check_external_links"]:
                return self._validate_external_link(file_path, link_url)

        # Check internal links
        elif self.rules["check_internal_links"]:
            return self._validate_internal_link(file_path, link_url)

        return None

    def _validate_external_link(
        self, file_path: Path, url: str
    ) -> Optional[ValidationResult]:
        """Validate external link by making HTTP request."""
        if url in self.links_cache:
            if not self.links_cache[url]:
                return ValidationResult(
                    str(file_path),
                    "broken_external_link",
                    "error",
                    f"External link is broken: {url}",
                )
            return None

        try:
            response = requests.head(url, timeout=10, allow_redirects=True)
            is_valid = response.status_code < 400
            self.links_cache[url] = is_valid

            if not is_valid:
                return ValidationResult(
                    str(file_path),
                    "broken_external_link",
                    "error",
                    f"External link returns {response.status_code}: {url}",
                )
        except Exception as e:
            self.links_cache[url] = False
            return ValidationResult(
                str(file_path),
                "external_link_error",
                "warning",
                f"Cannot validate external link: {url} ({e})",
            )

        return None

    def _validate_internal_link(
        self, file_path: Path, link_url: str
    ) -> Optional[ValidationResult]:
        """Validate internal link by checking file existence."""
        # Handle relative paths
        if link_url.startswith("./") or link_url.startswith("../"):
            target_path = (file_path.parent / link_url).resolve()
        else:
            # Absolute path from project root
            target_path = (self.project_root / link_url.lstrip("/")).resolve()

        # Handle anchor links in files
        if "#" in link_url:
            file_part, anchor_part = link_url.split("#", 1)
            if file_part:
                if file_part.startswith("./") or file_part.startswith("../"):
                    target_path = (file_path.parent / file_part).resolve()
                else:
                    target_path = (self.project_root / file_part.lstrip("/")).resolve()

        if not target_path.exists():
            return ValidationResult(
                str(file_path),
                "broken_internal_link",
                "error",
                f"Internal link target does not exist: {link_url}",
            )

        return None

    def validate_markdown_syntax(self, file_path: Path) -> List[ValidationResult]:
        """Validate markdown syntax using markdown parser."""
        results = []

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()

            # Try to parse markdown
            md = markdown.Markdown(extensions=["toc", "tables", "fenced_code"])
            md.convert(content)

        except Exception as e:
            results.append(
                ValidationResult(
                    str(file_path),
                    "markdown_syntax_error",
                    "error",
                    f"Invalid markdown syntax: {e}",
                )
            )

        return results

    def validate_frontmatter(self, file_path: Path) -> List[ValidationResult]:
        """Validate YAML frontmatter if present."""
        results = []

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()
        except Exception:
            return results

        # Check for frontmatter
        if content.startswith("---\n"):
            try:
                # Extract frontmatter
                parts = content.split("---\n", 2)
                if len(parts) >= 3:
                    frontmatter = parts[1]
                    yaml.safe_load(frontmatter)
            except yaml.YAMLError as e:
                results.append(
                    ValidationResult(
                        str(file_path),
                        "invalid_frontmatter",
                        "error",
                        f"Invalid YAML frontmatter: {e}",
                    )
                )

        return results

    def check_documentation_coverage(self) -> List[ValidationResult]:
        """Check if key components have documentation."""
        results = []

        # Check if main services have documentation
        services_dir = self.project_root / "services"
        if services_dir.exists():
            for service_dir in services_dir.iterdir():
                if service_dir.is_dir() and not service_dir.name.startswith("."):
                    readme_path = service_dir / "README.md"
                    if not readme_path.exists():
                        results.append(
                            ValidationResult(
                                str(service_dir),
                                "missing_service_docs",
                                "warning",
                                f"Service '{service_dir.name}' is missing README.md",
                            )
                        )

        # Check if API endpoints are documented
        api_docs_dir = self.project_root / "docs" / "api"
        if not api_docs_dir.exists():
            results.append(
                ValidationResult(
                    str(self.project_root),
                    "missing_api_docs",
                    "warning",
                    "No API documentation directory found",
                )
            )

        return results

    def validate_all(self) -> Dict[str, any]:
        """Run all validation checks."""
        self.markdown_files = self.discover_markdown_files()
        self.results = []

        print(f"🔍 Validating {len(self.markdown_files)} markdown files...")

        # Validate each file
        for file_path in self.markdown_files:
            print(f"  📄 Validating: {file_path.relative_to(self.project_root)}")

            # Structure validation
            self.results.extend(self.validate_file_structure(file_path))

            # Link validation
            self.results.extend(self.validate_links(file_path))

            # Markdown syntax validation
            self.results.extend(self.validate_markdown_syntax(file_path))

            # Frontmatter validation
            self.results.extend(self.validate_frontmatter(file_path))

        # Global checks
        self.results.extend(self.check_documentation_coverage())

        return self.generate_report()

    def generate_report(self) -> Dict[str, any]:
        """Generate validation report."""
        # Count results by status
        status_counts = {"pass": 0, "warning": 0, "error": 0}
        for result in self.results:
            status_counts[result.status] += 1

        # Group results by file
        files_with_issues = {}
        for result in self.results:
            if result.file_path not in files_with_issues:
                files_with_issues[result.file_path] = []
            files_with_issues[result.file_path].append(result)

        report = {
            "timestamp": datetime.now().isoformat(),
            "summary": {
                "files_checked": len(self.markdown_files),
                "total_issues": len(self.results),
                "errors": status_counts["error"],
                "warnings": status_counts["warning"],
            },
            "files_with_issues": files_with_issues,
            "all_results": self.results,
        }

        return report

    def print_report(self, report: Dict[str, any]):
        """Print human-readable validation report."""
        summary = report["summary"]

        print("\n📊 Documentation Validation Report")
        print("=" * 50)
        print(f"Files checked: {summary['files_checked']}")
        print(f"Total issues: {summary['total_issues']}")
        print(f"Errors: {summary['errors']}")
        print(f"Warnings: {summary['warnings']}")

        if summary["total_issues"] == 0:
            print("\n✅ All documentation validation checks passed!")
            return

        print("\n📋 Issues by File:")
        print("-" * 30)

        for file_path, issues in report["files_with_issues"].items():
            print(f"\n📄 {Path(file_path).relative_to(self.project_root)}")

            for issue in issues:
                icon = "❌" if issue.status == "error" else "⚠️"
                line_info = f" (Line {issue.line_number})" if issue.line_number else ""
                print(f"  {icon} {issue.check_name}: {issue.message}{line_info}")

    def save_report(
        self, report: Dict[str, any], output_file: str = "docs_validation_report.json"
    ):
        """Save validation report to file."""
        output_path = self.project_root / output_file

        # Convert ValidationResult objects to dictionaries for JSON serialization
        serializable_report = dict(report)
        serializable_report["all_results"] = [
            {
                "file_path": result.file_path,
                "check_name": result.check_name,
                "status": result.status,
                "message": result.message,
                "line_number": result.line_number,
            }
            for result in report["all_results"]
        ]

        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(serializable_report, f, indent=2, ensure_ascii=False)

        print(f"💾 Validation report saved to: {output_path}")


def main():
    """Main function to run documentation validation."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Validate documentation quality and consistency"
    )
    parser.add_argument("--project-root", default=".", help="Project root directory")
    parser.add_argument(
        "--output", default="docs_validation_report.json", help="Output report file"
    )
    parser.add_argument(
        "--fail-on-error",
        action="store_true",
        help="Exit with error code if validation fails",
    )

    args = parser.parse_args()

    validator = DocumentationValidator(args.project_root)
    report = validator.validate_all()

    validator.print_report(report)
    validator.save_report(report, args.output)

    # Exit with error code if requested and there are errors
    if args.fail_on_error and report["summary"]["errors"] > 0:
        print(f"\n❌ Validation failed with {report['summary']['errors']} errors")
        sys.exit(1)

    print(f"\n✅ Validation completed! Check {args.output} for detailed results")


if __name__ == "__main__":
    main()
