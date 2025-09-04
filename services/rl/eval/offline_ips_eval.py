"""
Offline evaluation using Inverse Propensity Scoring (IPS).

Safely evaluates RL policies using logged data without needing to deploy them.
Uses propensity scores to correct for distribution shift between logging and evaluation policies.
"""

from __future__ import annotations

import argparse
import json
import pathlib
from typing import Any, Dict, List, Optional, Tuple

import structlog

try:
    import numpy as np
    import pandas as pd
except ImportError as e:
    raise ImportError(
        f"Required packages missing: {e}. Run: pip install numpy pandas"
    ) from e

from rl.bandits.routing_linucb import LinUCBRouting
from rl.bandits.tool_thompson import ThompsonSamplingTools
from rl.utils.features import FeatureMaker

logger = structlog.get_logger(__name__)


class IPSEvaluator:
    """
    Inverse Propensity Scoring evaluator for offline policy evaluation.

    Estimates the performance of a new policy using logged data from a different policy,
    correcting for the distribution shift using importance weighting.
    """

    def __init__(
        self,
        self_normalized: bool = True,
        clip_weights: bool = True,
        max_weight: float = 100.0,
        min_propensity: float = 1e-6,
    ):
        """
        Initialize IPS evaluator.

        Args:
            self_normalized: Use self-normalized IPS (more stable)
            clip_weights: Clip extreme importance weights
            max_weight: Maximum allowed importance weight
            min_propensity: Minimum propensity score (prevents division by zero)
        """
        self.self_normalized = self_normalized
        self.clip_weights = clip_weights
        self.max_weight = max_weight
        self.min_propensity = min_propensity

        logger.info(
            "IPS evaluator initialized",
            self_normalized=self_normalized,
            clip_weights=clip_weights,
            max_weight=max_weight,
        )

    def evaluate_routing_policy(
        self,
        policy: LinUCBRouting,
        feature_maker: FeatureMaker,
        episodes: List[Dict[str, Any]],
    ) -> Dict[str, float]:
        """
        Evaluate routing policy using IPS.

        Args:
            policy: Routing policy to evaluate
            feature_maker: Feature transformation
            episodes: Logged episodes with propensity scores

        Returns:
            Evaluation metrics dict
        """
        if not episodes:
            return {"error": "No episodes provided"}

        logger.info("Evaluating routing policy with IPS", episodes=len(episodes))

        # Collect IPS data
        rewards = []
        weights = []
        policy_actions = []
        logged_actions = []

        for episode in episodes:
            # Extract features and transform
            features = feature_maker.transform(episode)
            x = np.array(features)

            # Get policy's action
            policy_action, _ = policy.select_arm(
                x, mode="mean"
            )  # Greedy for evaluation
            policy_actions.append(policy_action)

            # Get logged action
            logged_action = episode.get("route", "micro")
            logged_actions.append(logged_action)

            # Check if actions match (only include matching episodes in IPS)
            if policy_action == logged_action:
                # Get importance weight
                propensity = max(
                    episode.get("route_propensity", 1.0), self.min_propensity
                )
                weight = 1.0 / propensity

                # Clip weight if requested
                if self.clip_weights:
                    weight = min(weight, self.max_weight)

                weights.append(weight)
                rewards.append(episode.get("reward", 0.0))

        if not weights:
            logger.warning("No matching actions found for IPS evaluation")
            return {
                "error": "No matching actions",
                "policy_actions": len(set(policy_actions)),
                "logged_actions": len(set(logged_actions)),
                "overlap": 0,
            }

        weights = np.array(weights)
        rewards = np.array(rewards)

        # Calculate IPS estimate
        if self.self_normalized:
            # Self-normalized IPS: more stable, less biased
            weight_sum = weights.sum()
            if weight_sum > 0:
                normalized_weights = weights / weight_sum
                ips_estimate = (normalized_weights * rewards).sum()
            else:
                ips_estimate = 0.0
        else:
            # Standard IPS
            ips_estimate = (weights * rewards).mean()

        # Calculate effective sample size (measure of estimation quality)
        ess = (weights.sum() ** 2) / (weights**2).sum() if len(weights) > 0 else 0

        # Additional metrics
        weight_stats = {
            "mean_weight": weights.mean(),
            "max_weight": weights.max(),
            "min_weight": weights.min(),
            "weight_variance": weights.var(),
            "effective_sample_size": ess,
            "coverage": len(weights) / len(episodes),  # Fraction of episodes used
        }

        # Policy distribution analysis
        policy_dist = {}
        logged_dist = {}

        for action in set(policy_actions + logged_actions):
            policy_dist[action] = policy_actions.count(action) / len(policy_actions)
            logged_dist[action] = logged_actions.count(action) / len(logged_actions)

        results = {
            "ips_estimate": float(ips_estimate),
            "episodes_used": len(weights),
            "total_episodes": len(episodes),
            "weight_stats": weight_stats,
            "policy_distribution": policy_dist,
            "logged_distribution": logged_dist,
            "evaluation_method": (
                "self_normalized_ips" if self.self_normalized else "standard_ips"
            ),
        }

        logger.info(
            "Routing policy IPS evaluation complete",
            ips_estimate=ips_estimate,
            episodes_used=len(weights),
            effective_sample_size=ess,
        )

        return results

    def evaluate_tool_policy(
        self, policy: ThompsonSamplingTools, episodes: List[Dict[str, Any]]
    ) -> Dict[str, float]:
        """
        Evaluate tool policy using IPS.

        Args:
            policy: Tool policy to evaluate
            episodes: Logged episodes with tool propensity scores

        Returns:
            Evaluation metrics dict
        """
        if not episodes:
            return {"error": "No episodes provided"}

        logger.info("Evaluating tool policy with IPS", episodes=len(episodes))

        # Collect IPS data per intent
        intent_results = {}
        overall_rewards = []
        overall_weights = []

        # Group by intent for better analysis
        intent_episodes = {}
        for episode in episodes:
            intent = episode.get("intent", "unknown")
            if intent not in intent_episodes:
                intent_episodes[intent] = []
            intent_episodes[intent].append(episode)

        for intent, intent_eps in intent_episodes.items():
            rewards = []
            weights = []
            policy_tools = []
            logged_tools = []

            for episode in intent_eps:
                # Get policy's tool recommendation (greedy)
                rankings = policy.get_tool_ranking(intent)
                if rankings:
                    policy_tool = rankings[0][0]  # Top ranked tool
                else:
                    policy_tool = "none"

                policy_tools.append(policy_tool)

                # Get logged tool
                logged_tool = episode.get("tool_primary", "none")
                logged_tools.append(logged_tool)

                # Check if tools match
                if policy_tool == logged_tool:
                    # Get importance weight for tool decision
                    propensity = max(
                        episode.get("tool_propensity", 1.0), self.min_propensity
                    )
                    weight = 1.0 / propensity

                    if self.clip_weights:
                        weight = min(weight, self.max_weight)

                    weights.append(weight)

                    # Use tool success as reward (0/1)
                    tool_reward = 1.0 if episode.get("tool_ok", False) else 0.0
                    rewards.append(tool_reward)

            if weights:
                weights = np.array(weights)
                rewards = np.array(rewards)

                # Calculate intent-specific IPS estimate
                if self.self_normalized and weights.sum() > 0:
                    normalized_weights = weights / weights.sum()
                    intent_ips = (normalized_weights * rewards).sum()
                else:
                    intent_ips = (weights * rewards).mean() if len(weights) > 0 else 0.0

                intent_results[intent] = {
                    "ips_estimate": float(intent_ips),
                    "episodes_used": len(weights),
                    "total_episodes": len(intent_eps),
                    "coverage": len(weights) / len(intent_eps),
                    "avg_weight": weights.mean(),
                    "policy_tools": list(set(policy_tools)),
                    "logged_tools": list(set(logged_tools)),
                }

                # Add to overall calculation
                overall_rewards.extend(rewards)
                overall_weights.extend(weights)

        # Overall IPS estimate
        if overall_weights:
            overall_weights = np.array(overall_weights)
            overall_rewards = np.array(overall_rewards)

            if self.self_normalized and overall_weights.sum() > 0:
                overall_normalized_weights = overall_weights / overall_weights.sum()
                overall_ips = (overall_normalized_weights * overall_rewards).sum()
            else:
                overall_ips = (overall_weights * overall_rewards).mean()
        else:
            overall_ips = 0.0

        results = {
            "overall_ips_estimate": float(overall_ips),
            "total_episodes_used": len(overall_weights),
            "total_episodes": len(episodes),
            "intents_evaluated": len(intent_results),
            "per_intent_results": intent_results,
            "evaluation_method": (
                "self_normalized_ips" if self.self_normalized else "standard_ips"
            ),
        }

        logger.info(
            "Tool policy IPS evaluation complete",
            overall_ips=overall_ips,
            intents=len(intent_results),
            episodes_used=len(overall_weights),
        )

        return results

    def compare_policies(
        self, baseline_results: Dict[str, float], candidate_results: Dict[str, float]
    ) -> Dict[str, Any]:
        """
        Compare two policy evaluation results.

        Args:
            baseline_results: IPS results for baseline policy
            candidate_results: IPS results for candidate policy

        Returns:
            Comparison metrics
        """
        if "error" in baseline_results or "error" in candidate_results:
            return {"error": "Cannot compare policies with evaluation errors"}

        baseline_ips = baseline_results.get("ips_estimate", 0.0)
        candidate_ips = candidate_results.get("ips_estimate", 0.0)

        # Calculate improvement
        improvement = candidate_ips - baseline_ips
        relative_improvement = (
            (improvement / baseline_ips) if baseline_ips != 0 else float("inf")
        )

        # Effective sample sizes for confidence assessment
        baseline_ess = baseline_results.get("weight_stats", {}).get(
            "effective_sample_size", 0
        )
        candidate_ess = candidate_results.get("weight_stats", {}).get(
            "effective_sample_size", 0
        )

        # Simple confidence assessment (more sophisticated methods exist)
        min_ess_for_confidence = 100
        reliable_comparison = (
            baseline_ess >= min_ess_for_confidence
            and candidate_ess >= min_ess_for_confidence
        )

        comparison = {
            "baseline_ips": baseline_ips,
            "candidate_ips": candidate_ips,
            "improvement": improvement,
            "relative_improvement": relative_improvement,
            "improvement_percentage": relative_improvement * 100,
            "baseline_ess": baseline_ess,
            "candidate_ess": candidate_ess,
            "reliable_comparison": reliable_comparison,
            "recommendation": self._make_recommendation(
                improvement, relative_improvement, reliable_comparison
            ),
        }

        return comparison

    def _make_recommendation(
        self, improvement: float, relative_improvement: float, reliable: bool
    ) -> str:
        """Make deployment recommendation based on comparison."""
        if not reliable:
            return "INSUFFICIENT_DATA - Need more episodes for reliable comparison"

        if relative_improvement > 0.05:  # >5% improvement
            return "DEPLOY - Significant improvement detected"
        elif relative_improvement > 0.01:  # 1-5% improvement
            return "CAUTIOUS_DEPLOY - Modest improvement, monitor closely"
        elif abs(relative_improvement) <= 0.01:  # <1% change
            return "NEUTRAL - No significant change"
        else:  # Negative improvement
            return "DO_NOT_DEPLOY - Performance regression detected"


def load_policies(
    routing_path: str, tool_path: str
) -> Tuple[
    Optional[LinUCBRouting], Optional[FeatureMaker], Optional[ThompsonSamplingTools]
]:
    """Load trained policies for evaluation."""
    routing_policy = None
    feature_maker = None
    tool_policy = None

    # Load routing policy
    if routing_path and pathlib.Path(routing_path).exists():
        logger.info("Loading routing policy", path=routing_path)
        with open(routing_path, "r", encoding="utf-8") as f:
            routing_data = json.load(f)

        routing_policy = LinUCBRouting.from_dict(routing_data["routing_policy"])
        feature_maker = FeatureMaker.from_dict(routing_data["feature_maker"])

    # Load tool policy
    if tool_path and pathlib.Path(tool_path).exists():
        logger.info("Loading tool policy", path=tool_path)
        with open(tool_path, "r", encoding="utf-8") as f:
            tool_data = json.load(f)

        tool_policy = ThompsonSamplingTools.from_dict(tool_data["tool_policy"])

    return routing_policy, feature_maker, tool_policy


def main():
    """Main evaluation script."""
    parser = argparse.ArgumentParser(
        description="Offline IPS evaluation of RL policies"
    )
    parser.add_argument("--episodes", required=True, help="Path to evaluation episodes")
    parser.add_argument("--routing", help="Path to routing policy JSON")
    parser.add_argument("--tools", help="Path to tool policy JSON")
    parser.add_argument(
        "--baseline-routing", help="Path to baseline routing policy for comparison"
    )
    parser.add_argument(
        "--baseline-tools", help="Path to baseline tool policy for comparison"
    )
    parser.add_argument("--out", help="Output results JSON file")
    parser.add_argument(
        "--max-weight", type=float, default=100.0, help="Max importance weight"
    )
    parser.add_argument(
        "--min-propensity", type=float, default=1e-6, help="Min propensity score"
    )
    parser.add_argument(
        "--no-self-normalize",
        action="store_true",
        help="Use standard IPS (not self-normalized)",
    )
    parser.add_argument(
        "--no-clip", action="store_true", help="Don't clip importance weights"
    )

    args = parser.parse_args()

    # Setup logging
    structlog.configure(
        processors=[structlog.dev.ConsoleRenderer()],
        logger_factory=structlog.stdlib.LoggerFactory(),
    )

    try:
        # Load episodes
        logger.info("Loading episodes", path=args.episodes)
        if args.episodes.endswith(".parquet"):
            df = pd.read_parquet(args.episodes)
        else:
            df = pd.read_csv(args.episodes)

        episodes = df.to_dict("records")
        logger.info("Loaded episodes", count=len(episodes))

        # Initialize evaluator
        evaluator = IPSEvaluator(
            self_normalized=not args.no_self_normalize,
            clip_weights=not args.no_clip,
            max_weight=args.max_weight,
            min_propensity=args.min_propensity,
        )

        results = {
            "evaluation_config": {
                "self_normalized": not args.no_self_normalize,
                "clip_weights": not args.no_clip,
                "max_weight": args.max_weight,
                "min_propensity": args.min_propensity,
                "episodes_count": len(episodes),
            }
        }

        # Evaluate candidate policies
        routing_policy, feature_maker, tool_policy = load_policies(
            args.routing, args.tools
        )

        if routing_policy and feature_maker:
            logger.info("Evaluating candidate routing policy")
            routing_results = evaluator.evaluate_routing_policy(
                routing_policy, feature_maker, episodes
            )
            results["candidate_routing"] = routing_results

        if tool_policy:
            logger.info("Evaluating candidate tool policy")
            tool_results = evaluator.evaluate_tool_policy(tool_policy, episodes)
            results["candidate_tools"] = tool_results

        # Evaluate baseline policies for comparison
        if args.baseline_routing or args.baseline_tools:
            baseline_routing, baseline_fm, baseline_tools = load_policies(
                args.baseline_routing, args.baseline_tools
            )

            if baseline_routing and baseline_fm and routing_policy:
                baseline_routing_results = evaluator.evaluate_routing_policy(
                    baseline_routing, baseline_fm, episodes
                )
                results["baseline_routing"] = baseline_routing_results

                # Compare policies
                routing_comparison = evaluator.compare_policies(
                    baseline_routing_results, routing_results
                )
                results["routing_comparison"] = routing_comparison

                logger.info(
                    "Routing policy comparison",
                    improvement=routing_comparison["improvement"],
                    recommendation=routing_comparison["recommendation"],
                )

            if baseline_tools and tool_policy:
                baseline_tool_results = evaluator.evaluate_tool_policy(
                    baseline_tools, episodes
                )
                results["baseline_tools"] = baseline_tool_results

                # Compare policies
                tool_comparison = evaluator.compare_policies(
                    baseline_tool_results, tool_results
                )
                results["tool_comparison"] = tool_comparison

                logger.info(
                    "Tool policy comparison",
                    improvement=tool_comparison["improvement"],
                    recommendation=tool_comparison["recommendation"],
                )

        # Print results
        print(json.dumps(results, indent=2))

        # Save results if requested
        if args.out:
            output_path = pathlib.Path(args.out)
            output_path.parent.mkdir(parents=True, exist_ok=True)

            with open(output_path, "w", encoding="utf-8") as f:
                json.dump(results, f, indent=2)

            logger.info("Results saved", path=output_path)

    except Exception as e:
        logger.error("Evaluation failed", error=str(e))
        raise


if __name__ == "__main__":
    main()
