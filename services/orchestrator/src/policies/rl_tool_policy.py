"""
RL-based tool selection policy for Alice orchestrator runtime.

Integrates Thompson Sampling tool bandit for intelligent tool selection
based on intent with fallback to rule-based selection.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

import structlog

try:
    import numpy as np
except ImportError:
    np = None

logger = structlog.get_logger(__name__)


class RLToolPolicy:
    """
    RL-based tool selection policy using Thompson Sampling.

    Learns which tools work best for different intents and provides
    intelligent tool recommendations with confidence scores.
    """

    def __init__(
        self,
        rl_policy_data: Optional[Dict[str, Any]] = None,
        fallback_tools: Optional[List[str]] = None,
        enable_exploration: bool = True,
        exploration_rate: float = 0.05,
    ):
        """
        Initialize RL tool policy.

        Args:
            rl_policy_data: RL policy data from trained Thompson Sampling model
            fallback_tools: Default tools to fall back to
            enable_exploration: Whether to use epsilon-greedy exploration
            exploration_rate: Epsilon for exploration
        """
        self.fallback_tools = fallback_tools or ["none"]
        self.enable_exploration = enable_exploration
        self.exploration_rate = exploration_rate

        # Thompson Sampling model components
        self.beta_params: Optional[Dict[str, Dict[str, Dict[str, float]]]] = None
        self.intent_tools: Optional[Dict[str, List[str]]] = None
        self.global_tools: Optional[Dict[str, int]] = None
        self.alpha_prior: float = 1.0
        self.beta_prior: float = 1.0
        self.min_samples: int = 5

        # Load RL policy if provided
        if rl_policy_data:
            self.load_rl_policy(rl_policy_data)

        logger.info(
            "RL tool policy initialized",
            has_rl_model=self.beta_params is not None,
            exploration_enabled=enable_exploration,
            fallback_tools=fallback_tools,
        )

    def load_rl_policy(self, policy_data: Dict[str, Any]) -> bool:
        """
        Load RL policy from Thompson Sampling data.

        Args:
            policy_data: Policy data dict

        Returns:
            True if loaded successfully
        """
        try:
            if "tool_policy" in policy_data:
                tool_policy = policy_data["tool_policy"]

                self.beta_params = tool_policy.get("beta_params", {})
                self.intent_tools = tool_policy.get("intent_tools", {})
                self.global_tools = tool_policy.get("global_tools", {})
                self.alpha_prior = tool_policy.get("alpha_prior", 1.0)
                self.beta_prior = tool_policy.get("beta_prior", 1.0)
                self.min_samples = tool_policy.get("min_samples", 5)

                intents = len(self.beta_params)
                total_combinations = sum(
                    len(tools) for tools in self.beta_params.values()
                )

                logger.info(
                    "RL tool policy loaded",
                    algorithm=tool_policy.get("algorithm"),
                    intents=intents,
                    intent_tool_combinations=total_combinations,
                )

                return True
            else:
                logger.warning("No tool_policy found in data")
                return False

        except Exception as e:
            logger.error("Failed to load RL tool policy", error=str(e))
            return False

    def select_tool(
        self,
        intent: str,
        available_tools: Optional[List[str]] = None,
        context: Optional[Dict[str, Any]] = None,
    ) -> Tuple[str, Dict[str, Any]]:
        """
        Select best tool for given intent using Thompson Sampling.

        Args:
            intent: User intent
            available_tools: List of available tools (None = all learned tools)
            context: Additional context information

        Returns:
            (selected_tool, debug_info)
        """
        if context is None:
            context = {}

        intent = str(intent).lower()
        debug_info = {"intent": intent, "method": "rl_thompson_sampling"}

        # Try RL policy first
        if self.beta_params and np:
            try:
                tool, rl_debug = self._rl_select_tool(intent, available_tools)
                debug_info.update(rl_debug)

                logger.debug(
                    "RL tool selection",
                    intent=intent,
                    selected_tool=tool,
                    method=rl_debug.get("method"),
                )

                return tool, debug_info

            except Exception as e:
                logger.warning(
                    "RL tool selection failed, using fallback",
                    intent=intent,
                    error=str(e),
                )
                debug_info["rl_error"] = str(e)

        # Fallback to simple selection
        tool = self._fallback_select_tool(intent, available_tools)
        debug_info.update(
            {"method": "fallback", "selected_tool": tool, "fallback_used": True}
        )

        logger.debug("Fallback tool selection", intent=intent, selected_tool=tool)

        return tool, debug_info

    def _rl_select_tool(
        self, intent: str, available_tools: Optional[List[str]]
    ) -> Tuple[str, Dict[str, Any]]:
        """
        Select tool using Thompson Sampling RL model.

        Args:
            intent: User intent
            available_tools: Available tools

        Returns:
            (selected_tool, debug_info)
        """
        debug_info = {"method": "thompson_sampling"}

        # Epsilon-greedy exploration
        if self.enable_exploration and np.random.random() < self.exploration_rate:
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
    ) -> List[Tuple[str, float, int, Dict[str, Any]]]:
        """
        Get ranked list of tools for intent based on expected success rate.

        Args:
            intent: User intent
            available_tools: List of available tools

        Returns:
            List of (tool, success_rate, samples, stats) tuples sorted by success rate
        """
        intent = str(intent).lower()

        if not self.beta_params or intent not in self.beta_params:
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

            stats = {
                "alpha": alpha,
                "beta": beta,
                "confidence_interval": self._beta_confidence_interval(alpha, beta),
                "sufficient_samples": samples >= self.min_samples,
            }

            rankings.append((tool, success_rate, samples, stats))

        # Sort by success rate (descending)
        rankings.sort(key=lambda x: x[1], reverse=True)

        return rankings

    def _beta_confidence_interval(
        self, alpha: float, beta: float, confidence: float = 0.95
    ) -> Tuple[float, float]:
        """Calculate confidence interval for Beta distribution."""
        try:
            from scipy.stats import beta as beta_dist

            lower = beta_dist.ppf((1 - confidence) / 2, alpha, beta)
            upper = beta_dist.ppf(1 - (1 - confidence) / 2, alpha, beta)
            return (lower, upper)
        except ImportError:
            # Fallback to simple approximation
            mean = alpha / (alpha + beta)
            var = (alpha * beta) / ((alpha + beta) ** 2 * (alpha + beta + 1))
            std = var**0.5
            margin = 1.96 * std  # Approximate 95% CI
            return (max(0, mean - margin), min(1, mean + margin))

    def _get_available_tools(self, intent: str) -> List[str]:
        """Get available tools for intent."""
        if self.intent_tools and intent in self.intent_tools:
            return self.intent_tools[intent]
        elif self.global_tools:
            return list(self.global_tools.keys())
        else:
            return self.fallback_tools

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
            tool = self.fallback_tools[0] if self.fallback_tools else "none"
            debug_info.update(
                {
                    "method": "ultimate_fallback",
                    "selected": tool,
                    "fallback_tools": self.fallback_tools,
                }
            )
            return tool, debug_info

    def _fallback_select_tool(
        self, intent: str, available_tools: Optional[List[str]]
    ) -> str:
        """Simple fallback tool selection."""
        # Use available tools or fallback tools
        candidates = available_tools or self.fallback_tools

        if not candidates:
            return "none"

        # Simple intent-based heuristics
        intent_lower = intent.lower()

        if "greeting" in intent_lower or "hello" in intent_lower:
            return "none"  # Greetings don't need tools
        elif "weather" in intent_lower:
            return "weather.lookup" if "weather.lookup" in candidates else candidates[0]
        elif "calc" in intent_lower or "math" in intent_lower:
            return "calculator" if "calculator" in candidates else candidates[0]
        elif "search" in intent_lower or "find" in intent_lower:
            return "search" if "search" in candidates else candidates[0]
        else:
            return candidates[0]  # Default to first available tool

    def update_feedback(self, intent: str, tool: str, success: bool) -> None:
        """
        Update model with new feedback (online learning).

        Args:
            intent: User intent
            tool: Tool used
            success: Whether tool succeeded
        """
        if not self.beta_params:
            logger.warning("Cannot update feedback - no RL model loaded")
            return

        intent = str(intent).lower()
        tool = str(tool).lower()

        # Initialize if new
        if intent not in self.beta_params:
            self.beta_params[intent] = {}
            if self.intent_tools:
                self.intent_tools[intent] = []

        if tool not in self.beta_params[intent]:
            self.beta_params[intent][tool] = {
                "alpha": self.alpha_prior,
                "beta": self.beta_prior,
                "samples": 0,
            }
            if self.intent_tools and intent in self.intent_tools:
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

    def update_policy(self, policy_data: Dict[str, Any]) -> bool:
        """
        Update RL policy with new data.

        Args:
            policy_data: New policy data

        Returns:
            True if update successful
        """
        logger.info("Updating RL tool policy")
        return self.load_rl_policy(policy_data)

    def get_status(self) -> Dict[str, Any]:
        """Get policy status for monitoring."""
        status = {
            "type": "rl_tool_policy",
            "has_rl_model": self.beta_params is not None,
            "exploration_enabled": self.enable_exploration,
            "exploration_rate": self.exploration_rate,
            "fallback_tools": self.fallback_tools,
            "alpha_prior": self.alpha_prior,
            "beta_prior": self.beta_prior,
            "min_samples": self.min_samples,
        }

        if self.beta_params:
            status.update(
                {
                    "intents_learned": len(self.beta_params),
                    "total_combinations": sum(
                        len(tools) for tools in self.beta_params.values()
                    ),
                    "global_tools": (
                        list(self.global_tools.keys()) if self.global_tools else []
                    ),
                    "avg_tools_per_intent": (
                        sum(len(tools) for tools in self.beta_params.values())
                        / len(self.beta_params)
                        if self.beta_params
                        else 0
                    ),
                }
            )

        return status
