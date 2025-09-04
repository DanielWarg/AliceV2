"""
Reward function for Alice RL system.

Balances multiple objectives:
- Success and tool correctness (primary)
- Latency and cost efficiency
- Cache utilization
- Security compliance (guardian flags)

Weights are tunable based on A/B test results.
"""

from __future__ import annotations

from typing import Any, Dict, Optional

import structlog

logger = structlog.get_logger(__name__)

# Default reward weights - can be tuned based on A/B results
DEFAULT_WEIGHTS = {
    "success": 2.0,  # Main objective: successful responses
    "tool_ok": 1.0,  # Tool calls work correctly
    "latency": -0.001,  # Penalty per ms (small but accumulates)
    "cost": -0.5,  # Penalty per USD (significant)
    "cache_hit": 0.4,  # Bonus for cache efficiency
    "guard_flag": -0.7,  # Penalty for security violations
}


def turn_reward(
    success: bool,
    tool_ok: bool,
    latency_ms: float,
    cost_usd: float,
    cache_hit: bool,
    guard_flag: bool,
    weights: Optional[Dict[str, float]] = None,
) -> float:
    """
    Calculate reward for a single turn/episode.

    Args:
        success: Whether the response was successful (schema valid, complete)
        tool_ok: Whether tool calls succeeded and had valid schema
        latency_ms: Total response latency in milliseconds
        cost_usd: Cost of the request in USD (LLM API costs)
        cache_hit: Whether response was served from cache
        guard_flag: Whether guardian flagged this as problematic
        weights: Custom weight dict (uses defaults if None)

    Returns:
        Float reward value (higher = better)
    """
    if weights is None:
        weights = DEFAULT_WEIGHTS

    # Sanitize inputs with defensive defaults
    success = bool(success) if success is not None else False
    tool_ok = bool(tool_ok) if tool_ok is not None else False
    cache_hit = bool(cache_hit) if cache_hit is not None else False
    guard_flag = bool(guard_flag) if guard_flag is not None else False

    latency_ms = max(0.0, float(latency_ms or 0.0))
    cost_usd = max(0.0, float(cost_usd or 0.0))

    # Calculate component rewards
    r_success = weights["success"] * (1.0 if success else 0.0)
    r_tool = weights["tool_ok"] * (1.0 if tool_ok else 0.0)
    r_latency = weights["latency"] * latency_ms
    r_cost = weights["cost"] * cost_usd
    r_cache = weights["cache_hit"] * (1.0 if cache_hit else 0.0)
    r_guard = weights["guard_flag"] * (1.0 if guard_flag else 0.0)

    total_reward = r_success + r_tool + r_latency + r_cost + r_cache + r_guard

    # Log detailed breakdown for debugging (sample 1% of calls)
    import random

    if random.random() < 0.01:
        logger.debug(
            "Reward breakdown",
            total=total_reward,
            success=r_success,
            tool=r_tool,
            latency=r_latency,
            cost=r_cost,
            cache=r_cache,
            guard=r_guard,
            inputs={
                "success": success,
                "tool_ok": tool_ok,
                "latency_ms": latency_ms,
                "cost_usd": cost_usd,
                "cache_hit": cache_hit,
                "guard_flag": guard_flag,
            },
        )

    return float(total_reward)


def batch_rewards(
    episodes: list[Dict[str, Any]], weights: Optional[Dict[str, float]] = None
) -> list[float]:
    """
    Calculate rewards for a batch of episodes efficiently.

    Args:
        episodes: List of episode dicts with reward fields
        weights: Custom weight dict

    Returns:
        List of reward values matching episode order
    """
    rewards = []
    for episode in episodes:
        reward = turn_reward(
            success=episode.get("success"),
            tool_ok=episode.get("tool_ok"),
            latency_ms=episode.get("latency_ms"),
            cost_usd=episode.get("cost_usd"),
            cache_hit=episode.get("cache_hit"),
            guard_flag=episode.get("guard_flag"),
            weights=weights,
        )
        rewards.append(reward)

    return rewards


def analyze_rewards(
    episodes: list[Dict[str, Any]], weights: Optional[Dict[str, float]] = None
) -> Dict[str, float]:
    """
    Analyze reward distribution and component contributions.

    Args:
        episodes: List of episode dicts
        weights: Custom weight dict

    Returns:
        Dict with reward statistics
    """
    if not episodes:
        return {"error": "No episodes provided"}

    rewards = batch_rewards(episodes, weights)

    import statistics

    stats = {
        "mean_reward": statistics.mean(rewards),
        "median_reward": statistics.median(rewards),
        "stdev_reward": statistics.pstdev(rewards) if len(rewards) > 1 else 0.0,
        "min_reward": min(rewards),
        "max_reward": max(rewards),
        "total_episodes": len(episodes),
    }

    # Component analysis
    success_rate = sum(1 for ep in episodes if ep.get("success")) / len(episodes)
    tool_ok_rate = sum(1 for ep in episodes if ep.get("tool_ok")) / len(episodes)
    cache_hit_rate = sum(1 for ep in episodes if ep.get("cache_hit")) / len(episodes)
    guard_flag_rate = sum(1 for ep in episodes if ep.get("guard_flag")) / len(episodes)

    avg_latency = statistics.mean([ep.get("latency_ms", 0) for ep in episodes])
    avg_cost = statistics.mean([ep.get("cost_usd", 0) for ep in episodes])

    stats.update(
        {
            "success_rate": success_rate,
            "tool_ok_rate": tool_ok_rate,
            "cache_hit_rate": cache_hit_rate,
            "guard_flag_rate": guard_flag_rate,
            "avg_latency_ms": avg_latency,
            "avg_cost_usd": avg_cost,
        }
    )

    return stats


# Weight presets for different optimization scenarios
WEIGHT_PRESETS = {
    "balanced": DEFAULT_WEIGHTS,
    "speed_focused": {
        "success": 2.0,
        "tool_ok": 1.0,
        "latency": -0.002,  # Double latency penalty
        "cost": -0.3,  # Lower cost penalty
        "cache_hit": 0.6,  # Higher cache bonus
        "guard_flag": -0.7,
    },
    "cost_focused": {
        "success": 2.0,
        "tool_ok": 1.0,
        "latency": -0.0005,  # Lower latency penalty
        "cost": -1.0,  # Double cost penalty
        "cache_hit": 0.8,  # Higher cache bonus (saves cost)
        "guard_flag": -0.7,
    },
    "quality_focused": {
        "success": 3.0,  # Higher success reward
        "tool_ok": 2.0,  # Higher tool quality reward
        "latency": -0.0005,  # Lower latency penalty
        "cost": -0.3,  # Lower cost penalty
        "cache_hit": 0.2,  # Lower cache bonus (quality over speed)
        "guard_flag": -1.0,  # Higher safety penalty
    },
}


def get_weights(preset: str = "balanced") -> Dict[str, float]:
    """Get reward weights for a specific optimization preset."""
    return WEIGHT_PRESETS.get(preset, DEFAULT_WEIGHTS).copy()
