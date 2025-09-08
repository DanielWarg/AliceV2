#!/usr/bin/env python3
"""
Apply Suggestions: tar förslag från overnight optimizer och intent tuner
och skapar patch-filer för säker granskning innan de appliceras på prod-config
"""

import argparse
import json
from datetime import UTC, datetime
from pathlib import Path

import yaml


def load_suggestions():
    """Ladda alla suggestions från ops/suggestions/"""
    sug_dir = Path("ops/suggestions")
    if not sug_dir.exists():
        return {}

    suggestions = {}

    # Intent regex suggestions
    intent_file = sug_dir / "intent_regex_suggestions.yaml"
    if intent_file.exists():
        with open(intent_file, "r", encoding="utf-8") as f:
            suggestions["intent_regex"] = yaml.safe_load(f) or {}

    # Intent tuning results
    tuning_file = sug_dir / "intent_tuning.json"
    if tuning_file.exists():
        with open(tuning_file, "r", encoding="utf-8") as f:
            suggestions["intent_tuning"] = json.load(f)

    # Morning report
    report_file = sug_dir / "morning_report.json"
    if report_file.exists():
        with open(report_file, "r", encoding="utf-8") as f:
            suggestions["morning_report"] = json.load(f)

    return suggestions


def generate_config_patch(suggestions, dry_run=True):
    """Generera patch för telemetry_sources.yaml baserat på suggestions"""
    config_path = Path("ops/config/telemetry_sources.yaml")

    if not config_path.exists():
        print(f"❌ Config file not found: {config_path}")
        return None

    # Ladda nuvarande config
    with open(config_path, "r", encoding="utf-8") as f:
        current_config = yaml.safe_load(f) or {}

    # Skapa kopia för modifikation
    new_config = yaml.safe_load(yaml.dump(current_config)) or {}

    # Applicera intent regex suggestions
    if "intent_regex" in suggestions:
        intent_suggestions = suggestions["intent_regex"]

        # Uppdatera intent_regexes sektion
        if "intent_regexes" not in new_config:
            new_config["intent_regexes"] = {}

        for intent_name, patterns in intent_suggestions.items():
            if patterns:  # Only add non-empty patterns
                new_config["intent_regexes"][intent_name] = patterns
                print(f"✅ Added/updated {intent_name}: {len(patterns)} patterns")

    # Applicera andra suggestions från morning report
    if "morning_report" in suggestions:
        report = suggestions["morning_report"]
        if "config_suggestions" in report:
            for key, value in report["config_suggestions"].items():
                if key in ["psi_threshold", "ks_threshold", "verifier_fail_threshold"]:
                    if "thresholds" not in new_config:
                        new_config["thresholds"] = {}
                    new_config["thresholds"][key] = value
                    print(f"✅ Updated threshold {key}: {value}")

    # Generera patch-fil
    timestamp = datetime.now(UTC).isoformat().replace(":", "-")

    if dry_run:
        # Skriv ny config som patch för granskning
        patch_path = Path(f"ops/suggestions/config_patch_{timestamp}.yaml")

        # Skapa diff-liknande format
        diff_content = f"""# Configuration Patch - {timestamp}
# Generated from suggestions in ops/suggestions/
# 
# TO APPLY: copy relevant sections to ops/config/telemetry_sources.yaml
# 
# CURRENT CONFIG: ops/config/telemetry_sources.yaml
# SUGGESTED CHANGES:

"""
        diff_content += yaml.dump(
            new_config, default_flow_style=False, allow_unicode=True
        )

        with open(patch_path, "w", encoding="utf-8") as f:
            f.write(diff_content)

        print(f"📄 Dry-run patch created: {patch_path}")
        print("🔍 Review the patch before applying to production")
        return patch_path
    else:
        # Backup original
        backup_path = config_path.with_suffix(f".yaml.backup.{timestamp}")
        with open(backup_path, "w", encoding="utf-8") as f:
            yaml.dump(current_config, f, default_flow_style=False, allow_unicode=True)

        # Write new config
        with open(config_path, "w", encoding="utf-8") as f:
            yaml.dump(new_config, f, default_flow_style=False, allow_unicode=True)

        print(f"✅ Config updated: {config_path}")
        print(f"💾 Backup saved: {backup_path}")
        return config_path


def show_impact_summary(suggestions):
    """Visa sammanfattning av förväntad impact"""
    print("\n📊 IMPACT SUMMARY:")

    if "intent_tuning" in suggestions:
        tuning = suggestions["intent_tuning"]
        psi_now = tuning.get("psi_now", 0)
        psi_sim = tuning.get("psi_sim", 0)
        delta = tuning.get("delta", 0)

        print(f"   PSI Now:       {psi_now:.6f}")
        print(f"   PSI Simulated: {psi_sim:.6f}")
        print(f"   Delta:         {delta:+.6f}")

        if delta < -0.5:
            print("   🎯 EXCELLENT: Significant PSI improvement expected")
        elif delta < -0.1:
            print("   ✅ GOOD: Moderate PSI improvement expected")
        elif delta < 0:
            print("   📉 MINOR: Small PSI improvement expected")
        else:
            print("   ⚠️ WARNING: No PSI improvement expected")

    if "intent_regex" in suggestions:
        regex_count = sum(
            len(patterns) for patterns in suggestions["intent_regex"].values()
        )
        print(f"   Intent patterns: {regex_count} new/updated")

    if "morning_report" in suggestions:
        print("   Additional config changes from overnight optimizer")


def main():
    ap = argparse.ArgumentParser(description="Apply suggestions to production config")
    ap.add_argument(
        "--dry-run",
        action="store_true",
        default=True,
        help="Create patch file for review (default)",
    )
    ap.add_argument(
        "--apply",
        action="store_true",
        help="Actually apply changes to production config",
    )
    ap.add_argument("--summary", action="store_true", help="Show impact summary only")

    args = ap.parse_args()

    suggestions = load_suggestions()

    if not suggestions:
        print("❌ No suggestions found in ops/suggestions/")
        print("💡 Run: make overnight-8h && make intent-simulate")
        return

    if args.summary:
        show_impact_summary(suggestions)
        return

    # Show summary first
    show_impact_summary(suggestions)
    print()

    if args.apply:
        print("🚨 APPLYING CHANGES TO PRODUCTION CONFIG...")
        patch_path = generate_config_patch(suggestions, dry_run=False)
    else:
        print("🔍 DRY-RUN MODE: Creating patch for review...")
        patch_path = generate_config_patch(suggestions, dry_run=True)

    if patch_path:
        print(f"\n✅ Done: {patch_path}")
        if args.dry_run:
            print("💡 To apply: python ops/scripts/apply_suggestions.py --apply")


if __name__ == "__main__":
    main()
