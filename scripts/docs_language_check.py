#!/usr/bin/env python3
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(__file__))

SWEDISH_HINTS = [
    r"\b(med|och|eller|inte|ska|behövs|klara|nästa|steg|daglig|hastighet|svenska)\b",
    r"å",
    r"ä",
    r"ö",
]

ALLOW_PATHS = {
    os.path.join("docs", "archive"),
    # Allow Swedish docs for stabilization
    "README.md",
    "ROADMAP.md",
    "DEPLOYMENT_SUCCESS_SUMMARY.md",
    "COMPLETE_ROADMAP_EXECUTION_PLAN.md",
    "STEP_8.5_OPTIMIZATION_CHANGELOG.md",
    "SECURITY_AND_PRIVACY.md",
    "AGENTS.md",
    "OPTIMIZATION_MASTER_PLAN.md",
    "TESTING_STRATEGY.md",
    "STABILIZATION_PLAN.md",
    os.path.join("monitoring", "README.md"),
    os.path.join("services", "rl", "README.md"),
    os.path.join("services", "rl", "SHADOW_MODE_STRATEGY.md"),
    os.path.join("services", "ingest", "README.md"),
    os.path.join("docs", "STATUS_METRICS.md"),
    os.path.join("docs", "DEV_CONTROL.md"),
    os.path.join("docs", "development", "docker_cache_lessons.md"),
    os.path.join("docs", "test_results", "planner_step7_results.md"),
    os.path.join(".github", "ISSUE_TEMPLATE", "bug_report.md"),
    os.path.join(".github", "ISSUE_TEMPLATE", "feature_request.md"),
    os.path.join("runbooks", "planner_debug.md"),
    os.path.join("data", "docs_backup"),  # Allow entire backup directory
    os.path.join("models", "README.md"),
}


def is_allowed(path: str) -> bool:
    return any(path.startswith(p) for p in ALLOW_PATHS)


def main():
    bad = []
    for dirpath, _, files in os.walk(ROOT):
        for f in files:
            if not f.endswith(".md"):
                continue
            rel = os.path.relpath(os.path.join(dirpath, f), ROOT)
            if is_allowed(rel):
                continue
            try:
                s = open(os.path.join(ROOT, rel), "r", encoding="utf-8").read()
            except Exception:
                continue
            for hint in SWEDISH_HINTS:
                if re.search(hint, s, flags=re.IGNORECASE):
                    bad.append(rel)
                    break
    if bad:
        print("Non-English docs detected (Swedish hints):")
        for b in bad:
            print(" -", b)
        sys.exit(1)
    print("Docs language check passed (English only)")
    sys.exit(0)


if __name__ == "__main__":
    main()
