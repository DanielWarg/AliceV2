#!/usr/bin/env python3
"""
Data Drift Monitoring for RL Episodes - T2 Hardening
Statistical drift detection with automated alerts
"""

from datetime import datetime
from typing import Any, Dict, List

import numpy as np
from scipy.stats import chi2_contingency, ks_2samp

from services.rl.pipelines.seed_config import ComponentSeed

# Drift detection thresholds
DRIFT_THRESHOLDS = {
    "critical": 0.01,  # p < 0.01 = critical drift
    "warning": 0.05,  # p < 0.05 = warning drift
    "acceptable": 0.1,  # p >= 0.1 = no drift
}


class DriftMonitor:
    """Monitor statistical drift in episode data"""

    def __init__(self):
        self.baseline_stats = None
        self.drift_history = []

    def establish_baseline(
        self, baseline_episodes: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Establish baseline statistics from reference episodes

        Returns:
            Baseline statistics for future comparisons
        """
        if not baseline_episodes:
            raise ValueError("Cannot establish baseline from empty episode list")

        # Extract key metrics for drift detection
        metrics = self._extract_metrics(baseline_episodes)

        self.baseline_stats = {
            "timestamp": datetime.now().isoformat(),
            "episode_count": len(baseline_episodes),
            "metrics": {
                "reward_distribution": {
                    "mean": np.mean(metrics["rewards"]),
                    "std": np.std(metrics["rewards"]),
                    "values": metrics["rewards"],  # Store for KS test
                },
                "latency_distribution": {
                    "mean": np.mean(metrics["latencies"]),
                    "std": np.std(metrics["latencies"]),
                    "values": metrics["latencies"],
                },
                "tool_distribution": {
                    "counts": metrics["tool_counts"],
                    "total": len(baseline_episodes),
                },
                "success_rate": {
                    "rate": np.mean(metrics["success_flags"]),
                    "count": sum(metrics["success_flags"]),
                    "total": len(metrics["success_flags"]),
                },
                "text_length_distribution": {
                    "mean": np.mean(metrics["text_lengths"]),
                    "std": np.std(metrics["text_lengths"]),
                    "values": metrics["text_lengths"],
                },
            },
        }

        return self.baseline_stats

    def detect_drift(self, current_episodes: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Detect drift between current episodes and baseline

        Returns:
            Drift detection results with p-values and severity
        """
        if not self.baseline_stats:
            raise ValueError(
                "No baseline established. Call establish_baseline() first."
            )

        if not current_episodes:
            return {"error": "No current episodes provided"}

        current_metrics = self._extract_metrics(current_episodes)
        baseline_metrics = self.baseline_stats["metrics"]

        drift_results = {
            "timestamp": datetime.now().isoformat(),
            "baseline_timestamp": self.baseline_stats["timestamp"],
            "current_episode_count": len(current_episodes),
            "baseline_episode_count": self.baseline_stats["episode_count"],
            "drift_tests": {},
            "overall_drift_severity": "acceptable",
        }

        # Test 1: Reward distribution drift (KS test)
        ks_stat, p_value = ks_2samp(
            baseline_metrics["reward_distribution"]["values"],
            current_metrics["rewards"],
        )
        drift_results["drift_tests"]["reward_distribution"] = {
            "test": "kolmogorov_smirnov",
            "statistic": float(ks_stat),
            "p_value": float(p_value),
            "severity": self._classify_drift(p_value),
            "baseline_mean": baseline_metrics["reward_distribution"]["mean"],
            "current_mean": float(np.mean(current_metrics["rewards"])),
        }

        # Test 2: Latency distribution drift
        ks_stat, p_value = ks_2samp(
            baseline_metrics["latency_distribution"]["values"],
            current_metrics["latencies"],
        )
        drift_results["drift_tests"]["latency_distribution"] = {
            "test": "kolmogorov_smirnov",
            "statistic": float(ks_stat),
            "p_value": float(p_value),
            "severity": self._classify_drift(p_value),
            "baseline_mean": baseline_metrics["latency_distribution"]["mean"],
            "current_mean": float(np.mean(current_metrics["latencies"])),
        }

        # Test 3: Tool usage distribution drift (Chi-square test)
        tool_drift = self._test_categorical_drift(
            baseline_metrics["tool_distribution"]["counts"],
            current_metrics["tool_counts"],
        )
        drift_results["drift_tests"]["tool_distribution"] = tool_drift

        # Test 4: Success rate drift (proportion test)
        baseline_rate = baseline_metrics["success_rate"]["rate"]
        current_rate = np.mean(current_metrics["success_flags"])

        # Z-test for proportions
        n1, n2 = self.baseline_stats["episode_count"], len(current_episodes)
        p_pooled = (
            baseline_metrics["success_rate"]["count"]
            + sum(current_metrics["success_flags"])
        ) / (n1 + n2)
        se = np.sqrt(p_pooled * (1 - p_pooled) * (1 / n1 + 1 / n2))
        z_stat = (current_rate - baseline_rate) / se if se > 0 else 0
        p_value = (
            2 * (1 - abs(z_stat)) if abs(z_stat) < 1 else 0.01
        )  # Rough approximation

        drift_results["drift_tests"]["success_rate"] = {
            "test": "proportion_z_test",
            "statistic": float(z_stat),
            "p_value": float(p_value),
            "severity": self._classify_drift(p_value),
            "baseline_rate": baseline_rate,
            "current_rate": float(current_rate),
        }

        # Test 5: Text length distribution drift
        ks_stat, p_value = ks_2samp(
            baseline_metrics["text_length_distribution"]["values"],
            current_metrics["text_lengths"],
        )
        drift_results["drift_tests"]["text_length_distribution"] = {
            "test": "kolmogorov_smirnov",
            "statistic": float(ks_stat),
            "p_value": float(p_value),
            "severity": self._classify_drift(p_value),
            "baseline_mean": baseline_metrics["text_length_distribution"]["mean"],
            "current_mean": float(np.mean(current_metrics["text_lengths"])),
        }

        # Determine overall drift severity
        severities = [
            test["severity"] for test in drift_results["drift_tests"].values()
        ]
        if "critical" in severities:
            drift_results["overall_drift_severity"] = "critical"
        elif "warning" in severities:
            drift_results["overall_drift_severity"] = "warning"

        # Store in history
        self.drift_history.append(drift_results)

        return drift_results

    def _extract_metrics(self, episodes: List[Dict[str, Any]]) -> Dict[str, List]:
        """Extract numerical metrics from episodes for drift testing"""
        rewards = []
        latencies = []
        tools = []
        success_flags = []
        text_lengths = []

        for episode in episodes:
            # Reward (total)
            reward = episode.get("reward_components", {}).get("total", 0.0)
            rewards.append(float(reward))

            # Latency
            latency = episode.get("outcome", {}).get("latency_ms", 0)
            latencies.append(float(latency) if latency else 0.0)

            # Tool used
            tool = episode.get("action", {}).get("tool", "none")
            tools.append(tool)

            # Success flag
            success = episode.get("outcome", {}).get("success", False)
            success_flags.append(bool(success))

            # Text length
            text = episode.get("state", {}).get("text", "")
            text_lengths.append(len(text))

        # Count tool usage
        tool_counts = {}
        for tool in tools:
            tool_counts[tool] = tool_counts.get(tool, 0) + 1

        return {
            "rewards": rewards,
            "latencies": latencies,
            "tool_counts": tool_counts,
            "success_flags": success_flags,
            "text_lengths": text_lengths,
        }

    def _test_categorical_drift(
        self, baseline_counts: Dict[str, int], current_counts: Dict[str, int]
    ) -> Dict[str, Any]:
        """Test drift in categorical distributions (like tool usage)"""

        # Align categories
        all_categories = set(baseline_counts.keys()) | set(current_counts.keys())

        baseline_array = [baseline_counts.get(cat, 0) for cat in sorted(all_categories)]
        current_array = [current_counts.get(cat, 0) for cat in sorted(all_categories)]

        # Chi-square test
        contingency_table = [baseline_array, current_array]

        try:
            chi2_stat, p_value, dof, expected = chi2_contingency(contingency_table)
        except ValueError:
            # Handle case where test cannot be performed
            return {
                "test": "chi_square",
                "statistic": 0.0,
                "p_value": 1.0,
                "severity": "acceptable",
                "error": "Insufficient data for chi-square test",
            }

        return {
            "test": "chi_square",
            "statistic": float(chi2_stat),
            "p_value": float(p_value),
            "severity": self._classify_drift(p_value),
            "degrees_of_freedom": int(dof),
            "baseline_distribution": dict(zip(sorted(all_categories), baseline_array)),
            "current_distribution": dict(zip(sorted(all_categories), current_array)),
        }

    def _classify_drift(self, p_value: float) -> str:
        """Classify drift severity based on p-value"""
        if p_value < DRIFT_THRESHOLDS["critical"]:
            return "critical"
        elif p_value < DRIFT_THRESHOLDS["warning"]:
            return "warning"
        else:
            return "acceptable"

    def get_drift_summary(self) -> Dict[str, Any]:
        """Get summary of all drift detections"""
        if not self.drift_history:
            return {"error": "No drift history available"}

        recent_drift = self.drift_history[-1]

        # Count severities over time
        severity_counts = {"critical": 0, "warning": 0, "acceptable": 0}
        for drift_result in self.drift_history:
            severity = drift_result["overall_drift_severity"]
            severity_counts[severity] += 1

        return {
            "total_drift_checks": len(self.drift_history),
            "severity_distribution": severity_counts,
            "latest_drift_severity": recent_drift["overall_drift_severity"],
            "latest_timestamp": recent_drift["timestamp"],
            "baseline_established": (
                self.baseline_stats["timestamp"] if self.baseline_stats else None
            ),
            "drift_trend": self._analyze_drift_trend(),
        }

    def _analyze_drift_trend(self) -> str:
        """Analyze drift trend over recent history"""
        if len(self.drift_history) < 3:
            return "insufficient_data"

        recent_severities = [
            result["overall_drift_severity"] for result in self.drift_history[-5:]
        ]

        severity_scores = {"acceptable": 0, "warning": 1, "critical": 2}
        scores = [severity_scores[sev] for sev in recent_severities]

        if len(scores) >= 3:
            if scores[-1] > scores[-2] > scores[-3]:
                return "worsening"
            elif scores[-1] < scores[-2] < scores[-3]:
                return "improving"
            elif scores[-1] == scores[-2] == scores[-3]:
                return "stable"

        return "variable"


if __name__ == "__main__":
    # Test drift monitoring
    with ComponentSeed("drift_test"):
        # Generate baseline data
        baseline_episodes = []
        for i in range(100):
            episode = {
                "reward_components": {"total": np.random.normal(0.7, 0.1)},
                "outcome": {
                    "latency_ms": int(np.random.normal(150, 30)),
                    "success": np.random.choice([True, False], p=[0.8, 0.2]),
                },
                "action": {"tool": np.random.choice(["email", "calendar", "search"])},
                "state": {"text": "test " * np.random.randint(5, 20)},
            }
            baseline_episodes.append(episode)

        # Generate drifted data (different distribution)
        current_episodes = []
        for i in range(100):
            episode = {
                "reward_components": {
                    "total": np.random.normal(0.5, 0.15)
                },  # Lower mean, higher variance
                "outcome": {
                    "latency_ms": int(np.random.normal(200, 50)),  # Higher latency
                    "success": np.random.choice(
                        [True, False], p=[0.6, 0.4]
                    ),  # Lower success rate
                },
                "action": {
                    "tool": np.random.choice(["email", "calendar"], p=[0.9, 0.1])
                },  # Different tool dist
                "state": {"text": "test " * np.random.randint(10, 30)},  # Longer texts
            }
            current_episodes.append(episode)

    # Test drift detection
    monitor = DriftMonitor()
    baseline_stats = monitor.establish_baseline(baseline_episodes)
    drift_results = monitor.detect_drift(current_episodes)

    print("Drift Detection Results:")
    print(f"Overall severity: {drift_results['overall_drift_severity']}")

    for test_name, test_result in drift_results["drift_tests"].items():
        print(f"\n{test_name}:")
        print(f"  P-value: {test_result['p_value']:.4f}")
        print(f"  Severity: {test_result['severity']}")

    summary = monitor.get_drift_summary()
    print("\nDrift Summary:")
    print(f"Latest severity: {summary['latest_drift_severity']}")
    print(f"Trend: {summary['drift_trend']}")
