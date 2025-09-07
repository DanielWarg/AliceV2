#!/usr/bin/env python3
"""
🛡️ SLO Gates - Säkerhetsgrindar för RL-träning
Säkerställer att träning inte saboterar produktionsprestation
"""

import json
import logging
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Tuple

import numpy as np

logger = logging.getLogger(__name__)


@dataclass
class SLOThresholds:
    """SLO-trösklar som träning INTE får bryta"""

    # Performance thresholds
    tool_precision_min: float = 0.85  # 85% verktygsval korrekt
    success_rate_min: float = 0.98  # 98% lyckade svar
    p95_latency_fast_ms: float = 250  # P95 snabba svar
    p95_latency_planner_ms: float = 900  # P95 planeringsintensiva

    # Cache efficiency
    cache_hit_rate_min: float = 0.30  # 30% cache träffar

    # Safety bounds
    guard_flag_rate_max: float = 0.05  # Max 5% Guardian flags
    error_rate_max: float = 0.02  # Max 2% systemfel

    # Fibonacci optimization targets
    fibonacci_ratio_target: float = 1.618  # Golden ratio
    energy_efficiency_min: float = 0.80  # 80% energieffektivitet


class SLOGate:
    """Implementerar SLO-kontroller för säker RL-träning"""

    def __init__(self, thresholds: SLOThresholds):
        self.thresholds = thresholds

    def evaluate_episodes(self, episodes: List[Dict]) -> Tuple[bool, Dict]:
        """Evaluera episodes mot SLO-trösklar"""

        if not episodes:
            return False, {"error": "No episodes to evaluate"}

        metrics = self._calculate_metrics(episodes)
        violations = []

        # Check each SLO threshold
        if metrics["tool_precision"] < self.thresholds.tool_precision_min:
            violations.append(
                f"Tool precision {metrics['tool_precision']:.3f} < {self.thresholds.tool_precision_min}"
            )

        if metrics["success_rate"] < self.thresholds.success_rate_min:
            violations.append(
                f"Success rate {metrics['success_rate']:.3f} < {self.thresholds.success_rate_min}"
            )

        if metrics["p95_latency_ms"] > self.thresholds.p95_latency_planner_ms:
            violations.append(
                f"P95 latency {metrics['p95_latency_ms']:.0f}ms > {self.thresholds.p95_latency_planner_ms}ms"
            )

        if metrics["cache_hit_rate"] < self.thresholds.cache_hit_rate_min:
            violations.append(
                f"Cache hit rate {metrics['cache_hit_rate']:.3f} < {self.thresholds.cache_hit_rate_min}"
            )

        if metrics["guard_flag_rate"] > self.thresholds.guard_flag_rate_max:
            violations.append(
                f"Guard flag rate {metrics['guard_flag_rate']:.3f} > {self.thresholds.guard_flag_rate_max}"
            )

        # SLO check result
        slo_passed = len(violations) == 0

        result = {
            "slo_passed": slo_passed,
            "violations": violations,
            "metrics": metrics,
            "evaluated_episodes": len(episodes),
            "evaluation_timestamp": datetime.now().isoformat(),
        }

        return slo_passed, result

    def _calculate_metrics(self, episodes: List[Dict]) -> Dict[str, float]:
        """Beräkna prestandametriker från episodes"""

        total_episodes = len(episodes)
        if total_episodes == 0:
            return {}

        # Success metrics
        successful = sum(1 for ep in episodes if ep.get("success", False))
        tool_correct = sum(1 for ep in episodes if ep.get("tool_ok", False))

        # Performance metrics
        latencies = [
            ep.get("latency_ms", 0) for ep in episodes if ep.get("latency_ms", 0) > 0
        ]
        p95_latency = np.percentile(latencies, 95) if latencies else 0.0

        # Cache metrics
        cache_hits = sum(1 for ep in episodes if ep.get("cache_hit", False))

        # Safety metrics
        guard_flags = sum(1 for ep in episodes if ep.get("guard_flag", False))

        # Fibonacci optimization metrics
        fibonacci_optimized = sum(
            1 for ep in episodes if ep.get("fibonacci_optimized", False)
        )

        return {
            "success_rate": successful / total_episodes,
            "tool_precision": tool_correct / total_episodes,
            "p95_latency_ms": p95_latency,
            "avg_latency_ms": np.mean(latencies) if latencies else 0.0,
            "cache_hit_rate": cache_hits / total_episodes,
            "guard_flag_rate": guard_flags / total_episodes,
            "fibonacci_optimization_rate": fibonacci_optimized / total_episodes,
            "total_episodes": total_episodes,
        }


def run_pre_training_slo_check(telemetry_path: Path) -> bool:
    """Kör SLO-check innan träning startar"""

    logger.info("🛡️ Running pre-training SLO check...")

    # Load recent telemetry
    if not telemetry_path.exists():
        logger.error(f"Telemetry path not found: {telemetry_path}")
        return False

    episodes = []
    with open(telemetry_path, "r") as f:
        for line in f:
            if line.strip():
                episodes.append(json.loads(line))

    if not episodes:
        logger.error("No episodes found for SLO check")
        return False

    # Run SLO evaluation
    gate = SLOGate(SLOThresholds())
    slo_passed, result = gate.evaluate_episodes(episodes)

    if slo_passed:
        logger.info("✅ Pre-training SLO check PASSED")
        logger.info(f"Evaluated {result['evaluated_episodes']} episodes")
        logger.info(f"Success rate: {result['metrics']['success_rate']:.3f}")
        logger.info(f"Tool precision: {result['metrics']['tool_precision']:.3f}")
        logger.info(f"P95 latency: {result['metrics']['p95_latency_ms']:.0f}ms")
    else:
        logger.error("❌ Pre-training SLO check FAILED")
        logger.error("SLO violations:")
        for violation in result["violations"]:
            logger.error(f"  - {violation}")

        # Save violation report
        violation_report_path = Path("slo_violation_report.json")
        with open(violation_report_path, "w") as f:
            json.dump(result, f, indent=2)
        logger.error(f"Violation report saved to: {violation_report_path}")

    return slo_passed


def run_post_training_slo_check(
    baseline_episodes: List[Dict], new_episodes: List[Dict]
) -> bool:
    """Jämför prestanda innan vs efter träning"""

    logger.info("🛡️ Running post-training SLO check...")

    gate = SLOGate(SLOThresholds())

    # Evaluate baseline
    baseline_passed, baseline_result = gate.evaluate_episodes(baseline_episodes)

    # Evaluate new model
    new_passed, new_result = gate.evaluate_episodes(new_episodes)

    # Compare key metrics
    regressions = []

    baseline_metrics = baseline_result.get("metrics", {})
    new_metrics = new_result.get("metrics", {})

    # Check for regressions (allowable degradation thresholds)
    regression_thresholds = {
        "success_rate": 0.02,  # Max 2% degradation
        "tool_precision": 0.05,  # Max 5% degradation
        "p95_latency_ms": 100,  # Max 100ms increase
        "cache_hit_rate": 0.10,  # Max 10% degradation
    }

    for metric, threshold in regression_thresholds.items():
        baseline_val = baseline_metrics.get(metric, 0)
        new_val = new_metrics.get(metric, 0)

        if metric == "p95_latency_ms":
            # Higher latency = worse
            if new_val > baseline_val + threshold:
                regressions.append(
                    f"{metric}: {new_val:.1f} vs {baseline_val:.1f} (+{new_val-baseline_val:.1f})"
                )
        else:
            # Lower value = worse
            if new_val < baseline_val - threshold:
                regressions.append(
                    f"{metric}: {new_val:.3f} vs {baseline_val:.3f} ({new_val-baseline_val:+.3f})"
                )

    # Overall result
    post_training_passed = new_passed and len(regressions) == 0

    if post_training_passed:
        logger.info("✅ Post-training SLO check PASSED")
        logger.info("New model maintains baseline performance")

        # Log improvements
        for metric in ["success_rate", "tool_precision"]:
            baseline_val = baseline_metrics.get(metric, 0)
            new_val = new_metrics.get(metric, 0)
            if new_val > baseline_val:
                logger.info(f"📈 Improved {metric}: {baseline_val:.3f} → {new_val:.3f}")

    else:
        logger.error("❌ Post-training SLO check FAILED")

        if not new_passed:
            logger.error("New model violates absolute SLO thresholds:")
            for violation in new_result.get("violations", []):
                logger.error(f"  - {violation}")

        if regressions:
            logger.error("Performance regressions detected:")
            for regression in regressions:
                logger.error(f"  - {regression}")

    # Save comparison report
    comparison_report = {
        "post_training_passed": post_training_passed,
        "baseline_metrics": baseline_metrics,
        "new_metrics": new_metrics,
        "regressions": regressions,
        "absolute_slo_violations": new_result.get("violations", []),
        "evaluation_timestamp": datetime.now().isoformat(),
    }

    report_path = Path("post_training_slo_report.json")
    with open(report_path, "w") as f:
        json.dump(comparison_report, f, indent=2)

    logger.info(f"Post-training SLO report saved to: {report_path}")

    return post_training_passed


def create_slo_ci_check():
    """Skapa CI-check för SLO gates"""

    ci_script = """#!/bin/bash
# SLO CI Check - Runs in CI pipeline before model deployment

set -euo pipefail

echo "🛡️ Running SLO Gates CI Check"

# Check for required files
if [ ! -f "data/rl/baseline_episodes.jsonl" ]; then
    echo "❌ Missing baseline episodes file"
    exit 1
fi

if [ ! -f "data/rl/candidate_episodes.jsonl" ]; then
    echo "❌ Missing candidate episodes file"  
    exit 1
fi

# Run SLO check
python3 services/rl/slo_gates.py \\
    --baseline data/rl/baseline_episodes.jsonl \\
    --candidate data/rl/candidate_episodes.jsonl \\
    --output slo_check_result.json

# Check result
if [ $? -eq 0 ]; then
    echo "✅ SLO Gates PASSED - Safe to deploy"
    exit 0
else
    echo "❌ SLO Gates FAILED - Blocking deployment"
    
    # Post failure report (if in CI)
    if [ ! -z "${GITHUB_ACTIONS:-}" ]; then
        echo "::error::SLO Gates failed - model does not meet performance thresholds"
        
        # Optionally post to Slack/Discord
        # curl -X POST "$SLACK_WEBHOOK" -d "SLO violation in $GITHUB_REPOSITORY"
    fi
    
    exit 1
fi
"""

    ci_script_path = Path("scripts/slo_ci_check.sh")
    ci_script_path.parent.mkdir(exist_ok=True)

    with open(ci_script_path, "w") as f:
        f.write(ci_script)

    ci_script_path.chmod(0o755)  # Make executable

    logger.info(f"SLO CI check script created: {ci_script_path}")


def main():
    """CLI för SLO gates"""

    import argparse

    parser = argparse.ArgumentParser(description="SLO Gates för säker RL-träning")
    parser.add_argument("--baseline", help="Baseline episodes JSONL file")
    parser.add_argument("--candidate", help="Candidate episodes JSONL file")
    parser.add_argument("--pre-check", help="Pre-training SLO check on telemetry file")
    parser.add_argument("--output", help="Output report JSON file")
    parser.add_argument(
        "--create-ci", action="store_true", help="Create CI check script"
    )

    args = parser.parse_args()

    # Setup logging
    logging.basicConfig(level=logging.INFO)

    if args.create_ci:
        create_slo_ci_check()
        return

    if args.pre_check:
        passed = run_pre_training_slo_check(Path(args.pre_check))
        exit(0 if passed else 1)

    if args.baseline and args.candidate:
        # Load episodes
        baseline_episodes = []
        with open(args.baseline, "r") as f:
            for line in f:
                if line.strip():
                    baseline_episodes.append(json.loads(line))

        candidate_episodes = []
        with open(args.candidate, "r") as f:
            for line in f:
                if line.strip():
                    candidate_episodes.append(json.loads(line))

        passed = run_post_training_slo_check(baseline_episodes, candidate_episodes)

        if args.output:
            # Output file already created by the check function
            logger.info(f"Report written to {args.output}")

        exit(0 if passed else 1)

    parser.print_help()


if __name__ == "__main__":
    main()
