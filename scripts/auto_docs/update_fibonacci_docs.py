#!/usr/bin/env python3
"""
Auto-sync Fibonacci Configuration Documentation
Automatically updates documentation when Fibonacci constants change.
"""

import ast
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List

# Add the parent directory to sys.path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))


class FibonacciDocUpdater:
    """Updates documentation based on Fibonacci configuration changes."""

    def __init__(self, project_root: str):
        self.project_root = Path(project_root)
        self.fibonacci_config_path = (
            self.project_root
            / "services"
            / "orchestrator"
            / "src"
            / "config"
            / "fibonacci.py"
        )
        self.doc_files = [
            self.project_root / "README.md",
            self.project_root / "ALICE_SYSTEM_BLUEPRINT.md",
            self.project_root / "CACHE.md",
            self.project_root / "docs" / "architecture.md",
            self.project_root / "docs" / "api" / "orchestrator.md",
        ]

    def extract_fibonacci_constants(self) -> Dict:
        """Extract all Fibonacci constants from the configuration file."""
        if not self.fibonacci_config_path.exists():
            print(
                f"Warning: Fibonacci config not found at {self.fibonacci_config_path}"
            )
            return {}

        try:
            with open(self.fibonacci_config_path, "r") as f:
                content = f.read()

            tree = ast.parse(content)
            constants = {}

            for node in ast.walk(tree):
                if isinstance(node, ast.Assign):
                    # Handle simple assignments like GOLDEN_RATIO = ...
                    for target in node.targets:
                        if isinstance(target, ast.Name):
                            try:
                                value = ast.literal_eval(node.value)
                                constants[target.id] = value
                            except (ValueError, TypeError):
                                # Handle complex expressions
                                constants[target.id] = ast.unparse(node.value)

                elif isinstance(node, ast.ClassDef) and node.name == "FibonacciConfig":
                    # Extract class constants
                    for class_node in node.body:
                        if isinstance(class_node, ast.Assign):
                            for target in class_node.targets:
                                if isinstance(target, ast.Name):
                                    try:
                                        value = ast.literal_eval(class_node.value)
                                        constants[f"FibonacciConfig.{target.id}"] = (
                                            value
                                        )
                                    except (ValueError, TypeError):
                                        constants[f"FibonacciConfig.{target.id}"] = (
                                            ast.unparse(class_node.value)
                                        )

            return constants

        except Exception as e:
            print(f"Error extracting Fibonacci constants: {e}")
            return {}

    def generate_constants_table(self, constants: Dict) -> str:
        """Generate a markdown table of Fibonacci constants."""
        if not constants:
            return "<!-- No Fibonacci constants found -->"

        table = (
            "| Constant | Value | Description |\n|----------|-------|-------------|\n"
        )

        # Group constants by type
        groups = {
            "Core Values": ["FIBONACCI_SEQUENCE", "GOLDEN_RATIO"],
            "Routing Weights": ["FibonacciConfig.ROUTING_WEIGHTS"],
            "Cache TTL": ["FibonacciConfig.CACHE_TTL"],
            "Retry Configuration": ["FibonacciConfig.RETRY_CONFIG"],
            "Memory Windows": ["FibonacciConfig.MEMORY_WINDOWS"],
            "Resource Ratios": ["FibonacciConfig.RESOURCE_RATIOS"],
            "ML Cycles": ["FibonacciConfig.ML_CYCLES"],
            "Sampling Rates": ["FibonacciConfig.SAMPLING_RATES"],
        }

        for group_name, group_keys in groups.items():
            table += f"| **{group_name}** | | |\n"
            for key in group_keys:
                if key in constants:
                    value = str(constants[key])
                    # Truncate very long values
                    if len(value) > 100:
                        value = value[:97] + "..."
                    # Clean up the key name
                    clean_key = key.replace("FibonacciConfig.", "")
                    table += (
                        f"| `{clean_key}` | `{value}` | Auto-generated from config |\n"
                    )

        return table

    def update_doc_section(
        self, content: str, section_marker: str, new_content: str
    ) -> str:
        """Update a specific section in documentation."""
        # Pattern to match section between markers
        start_pattern = f"<!-- {section_marker} START -->"
        end_pattern = f"<!-- {section_marker} END -->"

        start_idx = content.find(start_pattern)
        end_idx = content.find(end_pattern)

        if start_idx == -1 or end_idx == -1:
            # If markers don't exist, append them at the end
            return content + f"\n\n{start_pattern}\n{new_content}\n{end_pattern}\n"

        # Replace content between markers
        return (
            content[: start_idx + len(start_pattern)]
            + f"\n{new_content}\n"
            + content[end_idx:]
        )

    def update_fibonacci_references(self, content: str, constants: Dict) -> str:
        """Update inline Fibonacci references in documentation."""
        # Update golden ratio references
        if "GOLDEN_RATIO" in constants:
            golden_ratio = constants["GOLDEN_RATIO"]
            # Update patterns like "φ ≈ 1.618" or "Golden Ratio: 1.618"
            patterns = [
                (r"φ\s*≈\s*[\d\.]+", f"φ ≈ {golden_ratio:.6f}"),
                (r"Golden Ratio:\s*[\d\.]+", f"Golden Ratio: {golden_ratio:.6f}"),
                (r"golden ratio.*?≈.*?[\d\.]+", f"golden ratio ≈ {golden_ratio:.6f}"),
            ]

            for pattern, replacement in patterns:
                content = re.sub(pattern, replacement, content, flags=re.IGNORECASE)

        # Update Fibonacci sequence references
        if "FIBONACCI_SEQUENCE" in constants:
            fib_seq = constants["FIBONACCI_SEQUENCE"]
            if isinstance(fib_seq, list):
                seq_str = ", ".join(map(str, fib_seq[:10]))  # Show first 10 numbers
                if len(fib_seq) > 10:
                    seq_str += "..."

                # Update patterns like "Fibonacci sequence: 1, 1, 2, 3, 5..."
                pattern = (
                    r"Fibonacci sequence:.*?\d+(?:,\s*\d+)*(?:\.\.\.)?(?:\]|\)|\s|$)"
                )
                replacement = f"Fibonacci sequence: {seq_str}"
                content = re.sub(pattern, replacement, content, flags=re.IGNORECASE)

        return content

    def add_timestamp_comment(self, content: str) -> str:
        """Add timestamp comment to show when docs were last updated."""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S UTC")
        comment = f"<!-- Auto-updated by Fibonacci doc sync on {timestamp} -->"

        # Add at the beginning if not present
        if "Auto-updated by Fibonacci doc sync" not in content:
            return comment + "\n\n" + content

        # Update existing timestamp
        pattern = r"<!-- Auto-updated by Fibonacci doc sync on .*? -->"
        return re.sub(pattern, comment, content)

    def update_documentation(self) -> List[str]:
        """Update all documentation files with current Fibonacci constants."""
        constants = self.extract_fibonacci_constants()
        if not constants:
            print("No Fibonacci constants found - skipping documentation update")
            return []

        updated_files = []

        for doc_file in self.doc_files:
            if not doc_file.exists():
                print(f"Documentation file not found: {doc_file}")
                continue

            try:
                with open(doc_file, "r", encoding="utf-8") as f:
                    content = f.read()

                original_content = content

                # Update Fibonacci constants table
                constants_table = self.generate_constants_table(constants)
                content = self.update_doc_section(
                    content, "FIBONACCI_CONSTANTS", constants_table
                )

                # Update inline Fibonacci references
                content = self.update_fibonacci_references(content, constants)

                # Add timestamp
                content = self.add_timestamp_comment(content)

                # Only write if content changed
                if content != original_content:
                    with open(doc_file, "w", encoding="utf-8") as f:
                        f.write(content)
                    updated_files.append(str(doc_file))
                    print(f"Updated: {doc_file.name}")
                else:
                    print(f"No changes needed: {doc_file.name}")

            except Exception as e:
                print(f"Error updating {doc_file}: {e}")

        return updated_files

    def generate_fibonacci_summary(self) -> str:
        """Generate a summary of current Fibonacci configuration."""
        constants = self.extract_fibonacci_constants()

        summary = "# Fibonacci Configuration Summary\n\n"
        summary += (
            f"Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}\n\n"
        )

        if "GOLDEN_RATIO" in constants:
            summary += f"**Golden Ratio (φ):** {constants['GOLDEN_RATIO']}\n\n"

        if "FIBONACCI_SEQUENCE" in constants:
            fib_seq = constants["FIBONACCI_SEQUENCE"]
            if isinstance(fib_seq, list):
                summary += f"**Fibonacci Sequence:** {', '.join(map(str, fib_seq))}\n\n"

        # Add configuration summaries
        config_keys = [k for k in constants.keys() if k.startswith("FibonacciConfig.")]
        if config_keys:
            summary += "## Configuration Categories\n\n"
            for key in config_keys:
                clean_key = key.replace("FibonacciConfig.", "")
                summary += f"- **{clean_key}**\n"

        return summary


def main():
    """Main execution function."""
    # Find project root
    current_dir = Path(__file__).parent
    project_root = current_dir.parent.parent

    print("Fibonacci Documentation Updater")
    print(f"Project root: {project_root}")
    print("Starting auto-documentation sync...")

    updater = FibonacciDocUpdater(str(project_root))

    # Update documentation
    updated_files = updater.update_documentation()

    if updated_files:
        print(f"\nSuccessfully updated {len(updated_files)} documentation files:")
        for file_path in updated_files:
            print(f"  - {file_path}")
    else:
        print("\nNo documentation files needed updates.")

    # Generate summary
    summary = updater.generate_fibonacci_summary()
    summary_path = project_root / "scripts" / "auto_docs" / "fibonacci_summary.md"

    with open(summary_path, "w", encoding="utf-8") as f:
        f.write(summary)
    print(f"\nGenerated Fibonacci summary: {summary_path}")

    return len(updated_files)


if __name__ == "__main__":
    exit_code = main()
    sys.exit(0 if exit_code >= 0 else 1)
