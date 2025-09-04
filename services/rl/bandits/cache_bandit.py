"""
Cache optimization bandit for Alice smart cache.

Auto-tunes cache parameters (semantic similarity thresholds, TTL settings, etc.)
to maximize cache hit rate while maintaining response quality.
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


class CacheBandit:
    """
    Multi-armed bandit for cache parameter optimization.

    Optimizes cache parameters like similarity thresholds and TTL values
    to maximize cache hit rate without degrading response quality.
    """

    def __init__(
        self,
        param_name: str = "semantic_threshold",
        candidates: Optional[List[float]] = None,
        success_weight: float = 0.7,
        cache_weight: float = 0.3,
    ):
        """
        Initialize cache bandit.

        Args:
            param_name: Parameter to optimize (e.g., "semantic_threshold", "ttl_seconds")
            candidates: List of candidate parameter values to test
            success_weight: Weight for response success in optimization
            cache_weight: Weight for cache hit rate in optimization
        """
        self.param_name = param_name
        self.success_weight = success_weight
        self.cache_weight = cache_weight

        # Default candidates based on parameter type
        if candidates is None:
            if param_name == "semantic_threshold":
                candidates = [0.70, 0.75, 0.80, 0.85, 0.90, 0.95]
            elif param_name == "ttl_seconds":
                candidates = [300, 600, 1800, 3600, 7200, 14400]  # 5min to 4hrs
            elif param_name == "max_cache_size":
                candidates = [1000, 2000, 5000, 10000, 20000]
            else:
                candidates = [0.1, 0.3, 0.5, 0.7, 0.9]  # Generic

        self.candidates = candidates

        # Performance tracking per candidate
        self.candidate_stats: Dict[float, Dict[str, float]] = {}

        for candidate in self.candidates:
            self.candidate_stats[candidate] = {
                "total_requests": 0,
                "cache_hits": 0,
                "successes": 0,
                "total_latency": 0.0,
                "score": 0.0,
                "confidence": 0.0,
            }

        logger.info(
            "Cache bandit initialized",
            param=param_name,
            candidates=candidates,
            success_weight=success_weight,
            cache_weight=cache_weight,
        )

    def evaluate_candidate(
        self, candidate: float, episodes: List[Dict[str, Any]]
    ) -> Dict[str, float]:
        """
        Evaluate a candidate parameter value on episode data.

        This is a simulation - in practice, different cache parameters
        would be A/B tested in production to get real performance data.

        Args:
            candidate: Parameter value to evaluate
            episodes: Episode data for evaluation

        Returns:
            Performance metrics dict
        """
        if not episodes:
            return {"score": 0.0, "cache_hit_rate": 0.0, "success_rate": 0.0}

        # Simulate cache behavior for this parameter value
        # In reality, this would come from actual A/B test data

        total_requests = len(episodes)
        cache_hits = 0
        successes = 0
        total_latency = 0.0

        for episode in episodes:
            # Simulate cache hit based on parameter
            if self.param_name == "semantic_threshold":
                # Higher threshold = fewer but more accurate cache hits
                base_hit_prob = episode.get("cache_hit", False)
                if base_hit_prob:
                    # Adjust hit probability based on threshold
                    hit_prob = min(1.0, base_hit_prob * (candidate / 0.85))
                    cache_hit = np.random.random() < hit_prob
                else:
                    cache_hit = False
            else:
                # For other parameters, use existing cache_hit data
                cache_hit = bool(episode.get("cache_hit", False))

            if cache_hit:
                cache_hits += 1

            # Success tracking
            if episode.get("success", False):
                successes += 1

            total_latency += float(episode.get("latency_ms", 0))

        # Calculate metrics
        cache_hit_rate = cache_hits / total_requests if total_requests > 0 else 0.0
        success_rate = successes / total_requests if total_requests > 0 else 0.0
        avg_latency = total_latency / total_requests if total_requests > 0 else 0.0

        # Combined score: weighted combination of cache performance and quality
        score = self.cache_weight * cache_hit_rate + self.success_weight * success_rate

        # Penalty for very high latency (cache misses should be fast)
        if avg_latency > 1000:  # > 1 second
            score *= 0.9

        return {
            "score": score,
            "cache_hit_rate": cache_hit_rate,
            "success_rate": success_rate,
            "avg_latency_ms": avg_latency,
            "total_requests": total_requests,
            "cache_hits": cache_hits,
            "successes": successes,
        }

    def fit(self, episodes: List[Dict[str, Any]]) -> None:
        """
        Fit cache bandit on episode data.

        Args:
            episodes: List of episode dicts with cache and performance data
        """
        if not episodes:
            raise ValueError("No episodes provided")

        logger.info(
            "Fitting cache bandit", episodes=len(episodes), param=self.param_name
        )

        # Evaluate each candidate
        for candidate in self.candidates:
            metrics = self.evaluate_candidate(candidate, episodes)

            self.candidate_stats[candidate] = {
                "total_requests": metrics["total_requests"],
                "cache_hits": metrics["cache_hits"],
                "successes": metrics["successes"],
                "total_latency": metrics["avg_latency_ms"] * metrics["total_requests"],
                "score": metrics["score"],
                "cache_hit_rate": metrics["cache_hit_rate"],
                "success_rate": metrics["success_rate"],
                "confidence": self._calculate_confidence(metrics["total_requests"]),
            }

            logger.debug(
                "Evaluated candidate",
                candidate=candidate,
                score=metrics["score"],
                cache_hit_rate=metrics["cache_hit_rate"],
                success_rate=metrics["success_rate"],
            )

    def _calculate_confidence(self, sample_size: int) -> float:
        """Calculate confidence in score based on sample size."""
        # Simple confidence based on sample size
        # More samples = higher confidence
        min_samples = 100
        max_confidence = 1.0

        if sample_size < min_samples:
            return sample_size / min_samples
        else:
            return max_confidence

    def get_best_candidate(
        self, min_confidence: float = 0.5
    ) -> Tuple[float, Dict[str, float]]:
        """
        Get best candidate parameter value.

        Args:
            min_confidence: Minimum confidence required for selection

        Returns:
            (best_candidate, stats)
        """
        if not self.candidate_stats:
            raise ValueError("Model not fitted yet")

        # Filter candidates by minimum confidence
        confident_candidates = {
            candidate: stats
            for candidate, stats in self.candidate_stats.items()
            if stats["confidence"] >= min_confidence
        }

        if not confident_candidates:
            logger.warning(
                "No candidates meet confidence threshold",
                min_confidence=min_confidence,
                available_candidates=len(self.candidate_stats),
            )
            # Fall back to all candidates
            confident_candidates = self.candidate_stats

        # Select candidate with highest score
        best_candidate = max(
            confident_candidates.keys(), key=lambda c: confident_candidates[c]["score"]
        )

        best_stats = confident_candidates[best_candidate]

        logger.info(
            "Selected best candidate",
            param=self.param_name,
            value=best_candidate,
            score=best_stats["score"],
            cache_hit_rate=best_stats["cache_hit_rate"],
            confidence=best_stats["confidence"],
        )

        return best_candidate, best_stats

    def get_ranking(self) -> List[Tuple[float, float, Dict[str, float]]]:
        """
        Get all candidates ranked by score.

        Returns:
            List of (candidate, score, full_stats) tuples sorted by score
        """
        if not self.candidate_stats:
            return []

        ranking = []
        for candidate, stats in self.candidate_stats.items():
            ranking.append((candidate, stats["score"], stats))

        # Sort by score descending
        ranking.sort(key=lambda x: x[1], reverse=True)

        return ranking

    def update_online(
        self, candidate: float, cache_hit: bool, success: bool, latency_ms: float
    ) -> None:
        """
        Update candidate statistics with online feedback.

        Args:
            candidate: Parameter value being tested
            cache_hit: Whether request was cache hit
            success: Whether request was successful
            latency_ms: Request latency
        """
        if candidate not in self.candidate_stats:
            logger.warning("Unknown candidate for online update", candidate=candidate)
            return

        stats = self.candidate_stats[candidate]

        # Update counters
        stats["total_requests"] += 1
        if cache_hit:
            stats["cache_hits"] += 1
        if success:
            stats["successes"] += 1
        stats["total_latency"] += latency_ms

        # Recalculate derived metrics
        total = stats["total_requests"]
        stats["cache_hit_rate"] = stats["cache_hits"] / total
        stats["success_rate"] = stats["successes"] / total
        stats["score"] = (
            self.cache_weight * stats["cache_hit_rate"]
            + self.success_weight * stats["success_rate"]
        )
        stats["confidence"] = self._calculate_confidence(total)

        logger.debug(
            "Updated candidate online",
            candidate=candidate,
            total_requests=total,
            new_score=stats["score"],
        )

    def get_statistics(self) -> Dict[str, Any]:
        """Get comprehensive statistics."""
        if not self.candidate_stats:
            return {"error": "Model not fitted"}

        ranking = self.get_ranking()

        stats = {
            "param_name": self.param_name,
            "num_candidates": len(self.candidates),
            "success_weight": self.success_weight,
            "cache_weight": self.cache_weight,
            "best_candidate": ranking[0][0] if ranking else None,
            "best_score": ranking[0][1] if ranking else 0.0,
            "candidate_ranking": [
                {
                    "candidate": candidate,
                    "score": score,
                    "cache_hit_rate": full_stats["cache_hit_rate"],
                    "success_rate": full_stats["success_rate"],
                    "confidence": full_stats["confidence"],
                    "requests": full_stats["total_requests"],
                }
                for candidate, score, full_stats in ranking
            ],
        }

        return stats

    def to_dict(self) -> Dict[str, Any]:
        """Serialize bandit to dictionary."""
        return {
            "version": "1.0",
            "algorithm": "cache_bandit",
            "param_name": self.param_name,
            "candidates": self.candidates,
            "success_weight": self.success_weight,
            "cache_weight": self.cache_weight,
            "candidate_stats": self.candidate_stats,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "CacheBandit":
        """Deserialize bandit from dictionary."""
        bandit = cls(
            param_name=data["param_name"],
            candidates=data["candidates"],
            success_weight=data["success_weight"],
            cache_weight=data["cache_weight"],
        )
        bandit.candidate_stats = data["candidate_stats"]
        return bandit


def load_cache_episodes(episodes_path: str) -> List[Dict[str, Any]]:
    """Load episodes with cache performance data."""
    logger.info("Loading cache episodes", path=episodes_path)

    if episodes_path.endswith(".parquet"):
        df = pd.read_parquet(episodes_path)
    else:
        df = pd.read_csv(episodes_path)

    # Focus on episodes with cache information
    cache_episodes = df[df["cache_hit"].notna()].to_dict("records")

    logger.info(
        "Loaded cache episodes",
        total=len(cache_episodes),
        cache_hits=sum(1 for ep in cache_episodes if ep.get("cache_hit")),
        hit_rate=(
            sum(1 for ep in cache_episodes if ep.get("cache_hit")) / len(cache_episodes)
            if cache_episodes
            else 0
        ),
    )

    return cache_episodes


def main():
    """Main training script."""
    parser = argparse.ArgumentParser(description="Train cache optimization bandit")
    parser.add_argument(
        "--episodes", required=True, help="Path to episodes parquet/CSV"
    )
    parser.add_argument("--out", required=True, help="Output policy JSON file")
    parser.add_argument(
        "--param", default="semantic_threshold", help="Parameter to optimize"
    )
    parser.add_argument(
        "--candidates", nargs="*", type=float, help="Candidate parameter values"
    )
    parser.add_argument(
        "--success-weight",
        type=float,
        default=0.7,
        help="Weight for success rate in scoring",
    )
    parser.add_argument(
        "--cache-weight",
        type=float,
        default=0.3,
        help="Weight for cache hit rate in scoring",
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
        # Load data
        episodes = load_cache_episodes(args.episodes)

        if not episodes:
            raise ValueError("No cache episodes found")

        # Create bandit
        bandit = CacheBandit(
            param_name=args.param,
            candidates=args.candidates,
            success_weight=args.success_weight,
            cache_weight=args.cache_weight,
        )

        # Fit bandit
        bandit.fit(episodes)

        # Get best candidate
        best_candidate, best_stats = bandit.get_best_candidate()

        # Get statistics
        stats = bandit.get_statistics()
        logger.info("Cache optimization complete", **stats)

        # Save policy
        output_path = pathlib.Path(args.out)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        policy_data = {
            "cache_policy": {args.param: best_candidate},
            "bandit_model": bandit.to_dict(),
            "training_info": {
                "episodes_path": args.episodes,
                "episodes_count": len(episodes),
                "param_optimized": args.param,
                "best_candidate": best_candidate,
                "best_score": best_stats["score"],
                "success_weight": args.success_weight,
                "cache_weight": args.cache_weight,
                "seed": args.seed,
            },
            "statistics": stats,
        }

        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(policy_data, f, indent=2)

        logger.info(
            "Cache policy saved",
            path=output_path,
            best_param=f"{args.param}={best_candidate}",
        )

    except Exception as e:
        logger.error("Training failed", error=str(e))
        raise


if __name__ == "__main__":
    main()
