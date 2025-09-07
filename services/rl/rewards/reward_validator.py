#!/usr/bin/env python3
"""
φ-Reward System Validator - T3 Hardening
Mathematical validation and outlier detection for golden ratio reward system
"""

from typing import Any, Dict, List, Tuple

import numpy as np

from services.rl.pipelines.seed_config import get_component_seed

# Golden ratio constants - FROZEN FOR T1-T6 HARDENING
PHI = 1.618033988749  # φ = (1 + √5) / 2
PHI_POWERS = {
    "precision": PHI**2,  # φ² = 2.618... (highest weight)
    "latency": PHI**1,  # φ¹ = 1.618... (medium weight)
    "energy": PHI**0,  # φ⁰ = 1.000... (baseline weight)
    "safety": PHI ** (-1),  # φ⁻¹ = 0.618... (lowest weight)
}

# Reward bounds for validation
REWARD_BOUNDS = {
    "precision": (0.0, 1.0),
    "latency": (0.0, 1.0),
    "energy": (0.0, 1.0),
    "safety": (0.0, 1.0),
    "total": (0.0, 10.0),  # Upper bound allows for φ-weighted sum
}

# Winsorization thresholds (robust outlier handling)
WINSORIZE_PERCENTILES = (1, 99)  # Clip to 1st-99th percentile range


class RewardValidator:
    """Validator for φ-weighted reward components"""

    def __init__(self):
        self.validation_history = []
        self.baseline_stats = None

    def validate_reward_components(
        self, reward_components: Dict[str, float]
    ) -> Dict[str, Any]:
        """
        Validate individual reward components and their φ-weighted total

        Returns:
            Validation results with errors, warnings, and corrected values
        """
        validation = {
            "valid": True,
            "errors": [],
            "warnings": [],
            "corrected_values": {},
            "phi_calculation": {},
            "mathematical_consistency": True,
        }

        # 1. Validate component bounds
        for component, value in reward_components.items():
            if component == "total":
                continue  # Validate total separately

            if component not in REWARD_BOUNDS:
                validation["errors"].append(f"Unknown reward component: {component}")
                validation["valid"] = False
                continue

            bounds = REWARD_BOUNDS[component]
            if not (bounds[0] <= value <= bounds[1]):
                validation["errors"].append(
                    f"{component} = {value} outside bounds {bounds}"
                )
                validation["valid"] = False
                # Clip to bounds
                validation["corrected_values"][component] = np.clip(
                    value, bounds[0], bounds[1]
                )

        # 2. Calculate expected φ-weighted total
        expected_total = self._calculate_phi_total(reward_components)
        validation["phi_calculation"] = {
            "expected_total": expected_total,
            "phi_weights": PHI_POWERS.copy(),
            "weighted_components": {},
        }

        # Store weighted components for analysis
        for component, weight in PHI_POWERS.items():
            if component in reward_components:
                weighted_value = reward_components[component] * weight
                validation["phi_calculation"]["weighted_components"][component] = {
                    "value": reward_components[component],
                    "weight": weight,
                    "weighted": weighted_value,
                }

        # 3. Validate total against φ-weighted calculation
        if "total" in reward_components:
            actual_total = reward_components["total"]
            tolerance = 0.001  # Allow small floating point errors

            if abs(actual_total - expected_total) > tolerance:
                validation["warnings"].append(
                    f"Total mismatch: actual={actual_total:.4f}, expected={expected_total:.4f}"
                )
                validation["mathematical_consistency"] = False
                validation["corrected_values"]["total"] = expected_total

        # 4. Check for mathematical impossibilities
        if expected_total > REWARD_BOUNDS["total"][1]:
            validation["errors"].append(
                f"φ-weighted total {expected_total:.4f} exceeds maximum {REWARD_BOUNDS['total'][1]}"
            )
            validation["valid"] = False

        # Store validation result
        self.validation_history.append(validation)

        return validation

    def winsorize_rewards(
        self, episodes: List[Dict[str, Any]], component: str = "total"
    ) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
        """
        Apply winsorization to reward components to handle outliers

        Args:
            episodes: List of episode dictionaries
            component: Which reward component to winsorize

        Returns:
            (winsorized_episodes, winsorization_stats)
        """
        if not episodes:
            return episodes, {"error": "No episodes provided"}

        # Extract reward values
        reward_values = []
        for episode in episodes:
            reward_comp = episode.get("reward_components", {})
            if component in reward_comp:
                reward_values.append(reward_comp[component])

        if not reward_values:
            return episodes, {"error": f"No {component} values found in episodes"}

        # Calculate winsorization bounds
        lower_bound = np.percentile(reward_values, WINSORIZE_PERCENTILES[0])
        upper_bound = np.percentile(reward_values, WINSORIZE_PERCENTILES[1])

        # Apply winsorization
        winsorized_episodes = []
        outliers_clipped = 0

        for episode in episodes:
            episode_copy = episode.copy()
            reward_comp = episode_copy.get("reward_components", {})

            if component in reward_comp:
                original_value = reward_comp[component]
                winsorized_value = np.clip(original_value, lower_bound, upper_bound)

                if original_value != winsorized_value:
                    outliers_clipped += 1
                    reward_comp[component] = winsorized_value

                    # Recalculate total if winsorizing component
                    if component != "total":
                        new_total = self._calculate_phi_total(reward_comp)
                        reward_comp["total"] = new_total

            winsorized_episodes.append(episode_copy)

        winsorization_stats = {
            "component": component,
            "original_count": len(episodes),
            "outliers_clipped": outliers_clipped,
            "outlier_rate": outliers_clipped / len(episodes),
            "bounds": {"lower": float(lower_bound), "upper": float(upper_bound)},
            "percentiles": WINSORIZE_PERCENTILES,
            "original_stats": {
                "min": float(min(reward_values)),
                "max": float(max(reward_values)),
                "mean": float(np.mean(reward_values)),
                "std": float(np.std(reward_values)),
            },
        }

        return winsorized_episodes, winsorization_stats

    def establish_reward_policies(
        self, episodes: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Establish φ-reward policies from baseline episodes

        Returns:
            Policy definitions with bounds, distributions, and enforcement rules
        """
        if not episodes:
            raise ValueError("Cannot establish policies from empty episode list")

        # Extract all reward components
        component_values = {comp: [] for comp in PHI_POWERS.keys()}
        total_values = []

        for episode in episodes:
            reward_comp = episode.get("reward_components", {})
            for component in PHI_POWERS.keys():
                if component in reward_comp:
                    component_values[component].append(reward_comp[component])

            if "total" in reward_comp:
                total_values.append(reward_comp["total"])

        # Calculate policy bounds and distributions
        policies = {
            "established_from": len(episodes),
            "phi_weights": PHI_POWERS.copy(),
            "component_policies": {},
            "total_policy": {},
            "enforcement_rules": {
                "bounds_checking": True,
                "phi_consistency": True,
                "outlier_detection": True,
                "winsorization": True,
            },
        }

        # Component-specific policies
        for component, values in component_values.items():
            if not values:
                continue

            values = np.array(values)
            policies["component_policies"][component] = {
                "count": len(values),
                "mean": float(np.mean(values)),
                "std": float(np.std(values)),
                "min": float(np.min(values)),
                "max": float(np.max(values)),
                "percentiles": {
                    "5th": float(np.percentile(values, 5)),
                    "25th": float(np.percentile(values, 25)),
                    "50th": float(np.percentile(values, 50)),
                    "75th": float(np.percentile(values, 75)),
                    "95th": float(np.percentile(values, 95)),
                },
                "phi_weight": PHI_POWERS[component],
                "expected_contribution": float(np.mean(values) * PHI_POWERS[component]),
            }

        # Total reward policy
        if total_values:
            total_values = np.array(total_values)
            policies["total_policy"] = {
                "count": len(total_values),
                "mean": float(np.mean(total_values)),
                "std": float(np.std(total_values)),
                "min": float(np.min(total_values)),
                "max": float(np.max(total_values)),
                "expected_mean": sum(
                    policies["component_policies"][comp]["expected_contribution"]
                    for comp in policies["component_policies"]
                ),
                "phi_consistency_score": self._calculate_phi_consistency(episodes),
            }

        self.baseline_stats = policies
        return policies

    def _calculate_phi_total(self, reward_components: Dict[str, float]) -> float:
        """Calculate φ-weighted total from components"""
        total = 0.0
        for component, weight in PHI_POWERS.items():
            if component in reward_components:
                total += reward_components[component] * weight
        return total

    def _calculate_phi_consistency(self, episodes: List[Dict[str, Any]]) -> float:
        """
        Calculate how consistently φ-weighting is applied across episodes

        Returns:
            Consistency score from 0.0 (inconsistent) to 1.0 (perfect)
        """
        consistency_scores = []

        for episode in episodes:
            reward_comp = episode.get("reward_components", {})
            if "total" not in reward_comp:
                continue

            expected_total = self._calculate_phi_total(reward_comp)
            actual_total = reward_comp["total"]

            if expected_total == 0:
                consistency_scores.append(1.0 if actual_total == 0 else 0.0)
            else:
                # Calculate relative error
                relative_error = abs(actual_total - expected_total) / expected_total
                consistency_score = max(0.0, 1.0 - relative_error)
                consistency_scores.append(consistency_score)

        return float(np.mean(consistency_scores)) if consistency_scores else 0.0

    def get_validation_summary(self) -> Dict[str, Any]:
        """Get summary of all reward validations performed"""
        if not self.validation_history:
            return {"error": "No validation history available"}

        valid_count = sum(1 for v in self.validation_history if v["valid"])
        error_count = sum(len(v["errors"]) for v in self.validation_history)
        warning_count = sum(len(v["warnings"]) for v in self.validation_history)

        # Mathematical consistency tracking
        consistent_count = sum(
            1 for v in self.validation_history if v["mathematical_consistency"]
        )

        return {
            "total_validations": len(self.validation_history),
            "valid_rewards": valid_count,
            "validation_rate": valid_count / len(self.validation_history),
            "total_errors": error_count,
            "total_warnings": warning_count,
            "mathematical_consistency_rate": consistent_count
            / len(self.validation_history),
            "phi_weights_used": PHI_POWERS.copy(),
            "policies_established": self.baseline_stats is not None,
        }


if __name__ == "__main__":
    # Test φ-reward validation
    validator = RewardValidator()

    # Test valid reward components
    valid_rewards = {
        "precision": 0.9,
        "latency": 0.7,
        "energy": 0.8,
        "safety": 0.95,
        "total": 0.9 * PHI**2 + 0.7 * PHI + 0.8 * 1.0 + 0.95 * PHI ** (-1),
    }

    print("Testing valid φ-reward components:")
    result = validator.validate_reward_components(valid_rewards)
    print(f"Valid: {result['valid']}")
    print(f"Expected total: {result['phi_calculation']['expected_total']:.4f}")
    print(f"Mathematical consistency: {result['mathematical_consistency']}")

    # Test invalid components
    invalid_rewards = {
        "precision": 1.5,  # Out of bounds
        "latency": 0.7,
        "energy": 0.8,
        "safety": 0.95,
        "total": 3.0,  # Wrong total
    }

    print("\nTesting invalid φ-reward components:")
    result = validator.validate_reward_components(invalid_rewards)
    print(f"Valid: {result['valid']}")
    print(f"Errors: {result['errors']}")
    print(f"Warnings: {result['warnings']}")
    print(f"Corrected values: {result['corrected_values']}")

    # Test winsorization
    print("\nTesting winsorization:")
    test_episodes = []
    np.random.seed(get_component_seed("reward_noise"))

    for i in range(100):
        # Most episodes have normal rewards
        if i < 90:
            total = np.random.normal(2.0, 0.3)
        else:
            # 10% are outliers
            total = np.random.normal(8.0, 1.0) if i % 2 else np.random.normal(-1.0, 0.5)

        episode = {"reward_components": {"total": total}, "episode_id": i}
        test_episodes.append(episode)

    winsorized_episodes, win_stats = validator.winsorize_rewards(test_episodes, "total")
    print(
        f"Outliers clipped: {win_stats['outliers_clipped']} / {win_stats['original_count']}"
    )
    print(f"Outlier rate: {win_stats['outlier_rate']:.2%}")
    print(
        f"Winsorization bounds: [{win_stats['bounds']['lower']:.3f}, {win_stats['bounds']['upper']:.3f}]"
    )
