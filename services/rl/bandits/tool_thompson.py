"""
Thompson Sampling bandit for tool selection.

Implements Beta-Bernoulli Thompson Sampling for contextual tool selection.
Learns which tools work best for different intents based on success feedback.
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

logger = structlog.get_logger(__name__)


class ThompsonSamplingTools:
    """
    Thompson Sampling for tool selection per intent.

    Uses Beta-Bernoulli conjugate priors to model tool success rates.
    Each (intent, tool) combination has its own Beta distribution.
    """

    def __init__(
        self,
        alpha_prior: float = 1.0,
        beta_prior: float = 1.0,
        epsilon: float = 0.05,
        min_samples: int = 5,
    ):
        """
        Initialize Thompson Sampling tool policy.

        Args:
            alpha_prior: Prior successes (α₀)
            beta_prior: Prior failures (β₀)
            epsilon: Epsilon-greedy exploration rate
            min_samples: Minimum samples before using learned policy
        """
        self.alpha_prior = alpha_prior
        self.beta_prior = beta_prior
        self.epsilon = epsilon
        self.min_samples = min_samples

        # Beta parameters per (intent, tool)
        # Format: {intent: {tool: {"alpha": α, "beta": β, "samples": n}}}
        self.beta_params: Dict[str, Dict[str, Dict[str, float]]] = {}

        # Available tools per intent (learned from data)
        self.intent_tools: Dict[str, List[str]] = {}

        # Global tool popularity for cold start
        self.global_tools: Dict[str, int] = {}

        logger.info(
            "Thompson Sampling tools initialized",
            alpha_prior=alpha_prior,
            beta_prior=beta_prior,
            epsilon=epsilon,
            min_samples=min_samples,
        )

    def fit(self, episodes: List[Dict[str, Any]]) -> None:
        """
        Fit Thompson Sampling model on episode data.

        Args:
            episodes: List of episode dicts with intent, tool_primary, tool_ok
        """
        if not episodes:
            raise ValueError("No episodes provided")

        logger.info("Fitting Thompson Sampling model", episodes=len(episodes))

        # Reset parameters
        self.beta_params = {}
        self.intent_tools = {}
        self.global_tools = {}

        # Count successes and failures per (intent, tool)
        for episode in episodes:
            intent = str(episode.get("intent", "unknown")).lower()
            tool = str(episode.get("tool_primary", "none")).lower()
            success = bool(episode.get("tool_ok", False))

            # Skip invalid entries
            if not intent or not tool or tool == "unknown":
                continue

            # Initialize intent if new
            if intent not in self.beta_params:
                self.beta_params[intent] = {}
                self.intent_tools[intent] = []

            # Initialize tool for this intent if new
            if tool not in self.beta_params[intent]:
                self.beta_params[intent][tool] = {
                    "alpha": self.alpha_prior,
                    "beta": self.beta_prior,
                    "samples": 0,
                }
                self.intent_tools[intent].append(tool)

            # Update Beta parameters
            if success:
                self.beta_params[intent][tool]["alpha"] += 1
            else:
                self.beta_params[intent][tool]["beta"] += 1

            self.beta_params[intent][tool]["samples"] += 1

            # Track global tool usage
            self.global_tools[tool] = self.global_tools.get(tool, 0) + 1

        # Remove duplicates and sort by popularity
        for intent in self.intent_tools:
            tools = list(set(self.intent_tools[intent]))
            # Sort by number of samples (most experienced first)
            tools.sort(
                key=lambda t: self.beta_params[intent][t]["samples"], reverse=True
            )
            self.intent_tools[intent] = tools

        # Log summary statistics
        total_intents = len(self.beta_params)
        total_combinations = sum(len(tools) for tools in self.beta_params.values())

        logger.info(
            "Model fitted",
            intents=total_intents,
            intent_tool_combinations=total_combinations,
            global_tools=len(self.global_tools),
        )

        # Log top combinations
        top_combos = []
        for intent, tools in self.beta_params.items():
            for tool, params in tools.items():
                samples = params["samples"]
                success_rate = params["alpha"] / (params["alpha"] + params["beta"])
                if samples >= 3:  # Only show combinations with some data
                    top_combos.append((intent, tool, samples, success_rate))

        top_combos.sort(key=lambda x: x[2], reverse=True)  # Sort by sample count

        for intent, tool, samples, success_rate in top_combos[:10]:
            logger.debug(
                "Top combination",
                intent=intent,
                tool=tool,
                samples=samples,
                success_rate=f"{success_rate:.2f}",
            )

    def sample_tool(
        self, intent: str, available_tools: Optional[List[str]] = None
    ) -> Tuple[str, Dict[str, Any]]:
        """
        Sample best tool for given intent using Thompson Sampling.

        Args:
            intent: User intent
            available_tools: List of available tools (None = all learned tools)

        Returns:
            (selected_tool, debug_info)
        """
        intent = str(intent).lower()
        debug_info = {"intent": intent, "method": "thompson_sampling"}

        # Epsilon-greedy exploration
        if np.random.random() < self.epsilon:
            tools = available_tools or self._get_available_tools(intent)
            if tools:
                tool = np.random.choice(tools)
                debug_info.update(
                    {
                        "method": "epsilon_exploration",
                        "available_tools": tools,
                        "selected": tool,
                    }
                )
                return tool, debug_info
            else:
                # Fallback to global popular tool
                return self._cold_start_tool(debug_info)

        # Get tools for this intent
        if intent not in self.beta_params:
            return self._cold_start_tool(debug_info)

        intent_tools = self.beta_params[intent]

        # Filter by available tools if specified
        if available_tools:
            candidate_tools = {
                tool: params
                for tool, params in intent_tools.items()
                if tool in available_tools
            }
        else:
            candidate_tools = intent_tools

        if not candidate_tools:
            return self._cold_start_tool(debug_info)

        # Thompson Sampling: sample from Beta posterior for each tool
        tool_samples = {}
        tool_stats = {}

        for tool, params in candidate_tools.items():
            alpha = params["alpha"]
            beta = params["beta"]
            samples = params["samples"]

            # Only use learned policy if enough samples
            if samples >= self.min_samples:
                # Sample from Beta(α, β)
                sample = np.random.beta(alpha, beta)
            else:
                # Use uniform sampling for tools with few samples
                sample = np.random.random()

            tool_samples[tool] = sample
            tool_stats[tool] = {
                "alpha": alpha,
                "beta": beta,
                "samples": samples,
                "mean": alpha / (alpha + beta),
                "sample": sample,
            }

        # Select tool with highest sample
        best_tool = max(tool_samples.keys(), key=lambda t: tool_samples[t])

        debug_info.update(
            {
                "candidate_tools": list(candidate_tools.keys()),
                "tool_stats": tool_stats,
                "selected": best_tool,
                "selected_sample": tool_samples[best_tool],
                "selection_reason": "highest_beta_sample",
            }
        )

        return best_tool, debug_info

    def get_tool_ranking(
        self, intent: str, available_tools: Optional[List[str]] = None
    ) -> List[Tuple[str, float, int]]:
        """
        Get ranked list of tools for intent based on expected success rate.

        Args:
            intent: User intent
            available_tools: List of available tools

        Returns:
            List of (tool, success_rate, samples) tuples sorted by success rate
        """
        intent = str(intent).lower()

        if intent not in self.beta_params:
            return []

        intent_tools = self.beta_params[intent]

        # Filter by available tools if specified
        if available_tools:
            candidate_tools = {
                tool: params
                for tool, params in intent_tools.items()
                if tool in available_tools
            }
        else:
            candidate_tools = intent_tools

        # Calculate expected success rates
        rankings = []
        for tool, params in candidate_tools.items():
            alpha = params["alpha"]
            beta = params["beta"]
            samples = params["samples"]
            success_rate = alpha / (alpha + beta)
            rankings.append((tool, success_rate, samples))

        # Sort by success rate (descending)
        rankings.sort(key=lambda x: x[1], reverse=True)

        return rankings

    def update_feedback(self, intent: str, tool: str, success: bool) -> None:
        """
        Update model with new feedback.

        Args:
            intent: User intent
            tool: Tool used
            success: Whether tool succeeded
        """
        intent = str(intent).lower()
        tool = str(tool).lower()

        # Initialize if new
        if intent not in self.beta_params:
            self.beta_params[intent] = {}
            self.intent_tools[intent] = []

        if tool not in self.beta_params[intent]:
            self.beta_params[intent][tool] = {
                "alpha": self.alpha_prior,
                "beta": self.beta_prior,
                "samples": 0,
            }
            self.intent_tools[intent].append(tool)

        # Update Beta parameters
        if success:
            self.beta_params[intent][tool]["alpha"] += 1
        else:
            self.beta_params[intent][tool]["beta"] += 1

        self.beta_params[intent][tool]["samples"] += 1

        logger.debug(
            "Updated tool feedback",
            intent=intent,
            tool=tool,
            success=success,
            new_alpha=self.beta_params[intent][tool]["alpha"],
            new_beta=self.beta_params[intent][tool]["beta"],
        )

    def _get_available_tools(self, intent: str) -> List[str]:
        """Get available tools for intent."""
        return self.intent_tools.get(intent, list(self.global_tools.keys()))

    def _cold_start_tool(
        self, debug_info: Dict[str, Any]
    ) -> Tuple[str, Dict[str, Any]]:
        """Handle cold start for unknown intents."""
        if self.global_tools:
            # Select most popular global tool
            tool = max(self.global_tools.keys(), key=lambda t: self.global_tools[t])
            debug_info.update(
                {
                    "method": "cold_start_popular",
                    "global_tools": self.global_tools,
                    "selected": tool,
                }
            )
            return tool, debug_info
        else:
            # Ultimate fallback
            debug_info.update({"method": "ultimate_fallback", "selected": "none"})
            return "none", debug_info

    def get_statistics(self) -> Dict[str, Any]:
        """Get model statistics for monitoring."""
        if not self.beta_params:
            return {"error": "Model not fitted"}

        stats = {
            "total_intents": len(self.beta_params),
            "total_combinations": sum(
                len(tools) for tools in self.beta_params.values()
            ),
            "avg_tools_per_intent": np.mean(
                [len(tools) for tools in self.beta_params.values()]
            ),
        }

        # Per-intent statistics
        intent_stats = {}
        for intent, tools in self.beta_params.items():
            intent_samples = sum(params["samples"] for params in tools.values())
            intent_success_rate = np.mean(
                [
                    params["alpha"] / (params["alpha"] + params["beta"])
                    for params in tools.values()
                ]
            )

            intent_stats[intent] = {
                "tools": len(tools),
                "samples": intent_samples,
                "avg_success_rate": intent_success_rate,
                "top_tool": (
                    max(tools.keys(), key=lambda t: tools[t]["samples"])
                    if tools
                    else None
                ),
            }

        stats["per_intent"] = intent_stats

        return stats

    def to_dict(self) -> Dict[str, Any]:
        """Serialize model to dictionary."""
        return {
            "version": "1.0",
            "algorithm": "thompson_sampling",
            "alpha_prior": self.alpha_prior,
            "beta_prior": self.beta_prior,
            "epsilon": self.epsilon,
            "min_samples": self.min_samples,
            "beta_params": self.beta_params,
            "intent_tools": self.intent_tools,
            "global_tools": self.global_tools,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ThompsonSamplingTools":
        """Deserialize model from dictionary."""
        model = cls(
            alpha_prior=data["alpha_prior"],
            beta_prior=data["beta_prior"],
            epsilon=data.get("epsilon", 0.05),
            min_samples=data.get("min_samples", 5),
        )

        model.beta_params = data["beta_params"]
        model.intent_tools = data["intent_tools"]
        model.global_tools = data["global_tools"]

        return model


def load_episodes_for_tools(episodes_path: str) -> List[Dict[str, Any]]:
    """Load episodes data for tool training."""
    logger.info("Loading episodes for tool training", path=episodes_path)

    if episodes_path.endswith(".parquet"):
        df = pd.read_parquet(episodes_path)
    else:
        df = pd.read_csv(episodes_path)

    # Filter for episodes with tool information
    df = df.dropna(subset=["intent", "tool_primary"])
    df = df[df["tool_primary"] != "unknown"]

    logger.info(
        "Loaded tool episodes",
        total=len(df),
        unique_intents=df["intent"].nunique(),
        unique_tools=df["tool_primary"].nunique(),
    )

    return df.to_dict("records")


def evaluate_tool_policy(
    model: ThompsonSamplingTools, test_episodes: List[Dict[str, Any]]
) -> Dict[str, float]:
    """Evaluate tool selection policy."""
    if not test_episodes:
        return {"error": "No test episodes"}

    correct_predictions = 0
    total_predictions = 0

    for episode in test_episodes:
        intent = episode.get("intent")
        true_tool = episode.get("tool_primary")

        if not intent or not true_tool:
            continue

        # Get model's top recommendation (greedy)
        rankings = model.get_tool_ranking(intent)
        if rankings:
            predicted_tool = rankings[0][0]  # Top ranked tool

            if predicted_tool == true_tool:
                correct_predictions += 1
            total_predictions += 1

    accuracy = correct_predictions / total_predictions if total_predictions > 0 else 0.0

    return {
        "accuracy": accuracy,
        "correct": correct_predictions,
        "total": total_predictions,
    }


def main():
    """Main training script."""
    parser = argparse.ArgumentParser(description="Train Thompson Sampling tool policy")
    parser.add_argument(
        "--episodes", required=True, help="Path to episodes parquet/CSV"
    )
    parser.add_argument("--out", required=True, help="Output policy JSON file")
    parser.add_argument(
        "--alpha-prior", type=float, default=1.0, help="Beta prior alpha"
    )
    parser.add_argument("--beta-prior", type=float, default=1.0, help="Beta prior beta")
    parser.add_argument("--epsilon", type=float, default=0.05, help="Exploration rate")
    parser.add_argument(
        "--min-samples", type=int, default=5, help="Min samples for learned policy"
    )
    parser.add_argument(
        "--test-split", type=float, default=0.2, help="Test split ratio"
    )
    parser.add_argument("--seed", type=int, default=42, help="Random seed")

    args = parser.parse_args()

    # Setup
    structlog.configure(
        processors=[structlog.dev.ConsoleRenderer()],
        logger_factory=structlog.stdlib.LoggerFactory(),
    )
    np.random.seed(args.seed)

    try:
        # Load episodes
        episodes = load_episodes_for_tools(args.episodes)

        if not episodes:
            raise ValueError("No valid tool episodes found")

        # Train/test split
        n_episodes = len(episodes)
        n_test = int(n_episodes * args.test_split)

        indices = np.random.permutation(n_episodes)
        train_episodes = (
            [episodes[i] for i in indices[:-n_test]] if n_test > 0 else episodes
        )
        test_episodes = [episodes[i] for i in indices[-n_test:]] if n_test > 0 else []

        logger.info("Data split", train=len(train_episodes), test=len(test_episodes))

        # Train model
        model = ThompsonSamplingTools(
            alpha_prior=args.alpha_prior,
            beta_prior=args.beta_prior,
            epsilon=args.epsilon,
            min_samples=args.min_samples,
        )

        model.fit(train_episodes)

        # Evaluate
        if test_episodes:
            metrics = evaluate_tool_policy(model, test_episodes)
            logger.info("Evaluation metrics", **metrics)

        # Get statistics
        stats = model.get_statistics()
        logger.info("Model statistics", **stats)

        # Save policy
        output_path = pathlib.Path(args.out)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        policy_data = {
            "tool_policy": model.to_dict(),
            "training_info": {
                "episodes_path": args.episodes,
                "train_episodes": len(train_episodes),
                "test_episodes": len(test_episodes),
                "alpha_prior": args.alpha_prior,
                "beta_prior": args.beta_prior,
                "epsilon": args.epsilon,
                "min_samples": args.min_samples,
                "seed": args.seed,
            },
            "statistics": stats,
        }

        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(policy_data, f, indent=2)

        logger.info("Tool policy saved", path=output_path)

    except Exception as e:
        logger.error("Training failed", error=str(e))
        raise


if __name__ == "__main__":
    main()
