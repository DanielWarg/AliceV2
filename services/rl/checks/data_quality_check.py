#!/usr/bin/env python3
"""
T4 - Data Quality Check (IQ Gate)
Validates dataset quality before allowing CI to pass
"""

import json
import sys
from pathlib import Path
from typing import Any, Dict, List


def load_report(report_path: Path) -> Dict[str, Any]:
    """Load the dataset report"""
    if not report_path.exists():
        raise FileNotFoundError(f"Report not found: {report_path}")

    with report_path.open("r") as f:
        return json.load(f)


def check_files_exist(dataset_dir: Path) -> List[str]:
    """Check that required dataset files exist"""
    errors = []
    required_files = ["train.jsonl", "val.jsonl", "test.jsonl", "report.json"]

    for filename in required_files:
        filepath = dataset_dir / filename
        if not filepath.exists():
            errors.append(f"Missing required file: {filename}")

    return errors


def validate_quality_requirements(report: Dict[str, Any]) -> List[str]:
    """Validate quality requirements from the report"""
    errors = []

    # Check quality index
    quality_index = report.get("quality_index", 0.0)
    min_quality = 0.8
    if quality_index < min_quality:
        errors.append(f"Quality index {quality_index:.3f} below minimum {min_quality}")

    # Check minimum episodes
    total_episodes = report.get("total_episodes", 0)
    if total_episodes < 1:
        errors.append(f"No episodes found (total: {total_episodes})")

    # Check train/val/test splits exist
    splits = report.get("splits", {})
    train_count = splits.get("train", 0)
    if train_count < 1:
        errors.append(f"No training episodes (train: {train_count})")

    # Check intent coverage
    intent_dist = report.get("intent_distribution", {})
    if len(intent_dist) < 1:
        errors.append("No intent coverage found")

    # Check for reasonable latency data
    latency_dist = report.get("latency_distribution_ms", {})
    latency_count = latency_dist.get("count", 0)
    if latency_count < 1:
        errors.append("No latency data available")

    return errors


def validate_data_completeness(dataset_dir: Path) -> List[str]:
    """Validate actual data files are not empty"""
    errors = []

    # Check train.jsonl has content
    train_file = dataset_dir / "train.jsonl"
    if train_file.exists():
        try:
            with train_file.open("r") as f:
                first_line = f.readline().strip()
                if not first_line:
                    errors.append("train.jsonl is empty")
                else:
                    # Validate it's valid JSON
                    json.loads(first_line)
        except json.JSONDecodeError as e:
            errors.append(f"Invalid JSON in train.jsonl: {e}")
        except Exception as e:
            errors.append(f"Error reading train.jsonl: {e}")

    return errors


def main():
    """Main data quality check function"""
    dataset_dir = Path("data/rl/v1")
    report_path = dataset_dir / "report.json"

    print("🛡️  Data Quality Check (IQ Gate)")
    print(f"📁 Dataset directory: {dataset_dir}")
    print()

    errors = []

    # Check 1: Files exist
    print("📋 Checking required files...")
    file_errors = check_files_exist(dataset_dir)
    errors.extend(file_errors)

    if file_errors:
        for error in file_errors:
            print(f"   ❌ {error}")
    else:
        print("   ✅ All required files found")

    # Check 2: Load and validate report
    print("\n📊 Validating quality report...")
    try:
        report = load_report(report_path)
        quality_errors = validate_quality_requirements(report)
        errors.extend(quality_errors)

        if quality_errors:
            for error in quality_errors:
                print(f"   ❌ {error}")
        else:
            print("   ✅ Quality requirements met")
            print(f"   📈 Quality Index: {report.get('quality_index', 0):.3f}")
            print(f"   📊 Total Episodes: {report.get('total_episodes', 0)}")

    except Exception as e:
        error_msg = f"Failed to load report: {e}"
        errors.append(error_msg)
        print(f"   ❌ {error_msg}")

    # Check 3: Validate data completeness
    print("\n🔍 Validating data completeness...")
    completeness_errors = validate_data_completeness(dataset_dir)
    errors.extend(completeness_errors)

    if completeness_errors:
        for error in completeness_errors:
            print(f"   ❌ {error}")
    else:
        print("   ✅ Data files are complete and valid")

    # Final verdict
    print(f"\n{'='*50}")

    if errors:
        print("🚨 DATA QUALITY CHECK FAILED")
        print(f"📋 Found {len(errors)} issue(s):")
        for i, error in enumerate(errors, 1):
            print(f"   {i}. {error}")
        print()
        print("🔧 Fix these issues and rebuild the dataset:")
        print(
            "   python services/rl/pipelines/build_dataset.py --src data/telemetry --out data/rl/v1"
        )
        sys.exit(1)
    else:
        print("✅ DATA QUALITY CHECK PASSED")
        print("🎯 Dataset meets all quality requirements")
        print("🚀 Safe to proceed with training")
        sys.exit(0)


if __name__ == "__main__":
    main()
