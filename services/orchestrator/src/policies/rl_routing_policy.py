"""
RL-based routing policy for Alice orchestrator runtime.

Integrates LinUCB routing bandit with existing router policy system
for intelligent route selection with fallback.
"""

from __future__ import annotations

from typing import Any, Dict, Optional, Tuple

import structlog

try:
    import numpy as np
except ImportError:
    np = None

from ..router.policy import RouteDecision

logger = structlog.get_logger(__name__)


class RLRoutingPolicy:
    """
    RL-based routing policy using LinUCB algorithm.

    Integrates with existing routing system and provides fallback
    to rule-based routing when RL policy is not available.
    """

    def __init__(
        self,
        rl_policy_data: Optional[Dict[str, Any]] = None,
        fallback_policy: Optional[object] = None,
        enable_exploration: bool = True,
        exploration_rate: float = 0.1,
    ):
        """
        Initialize RL routing policy.

        Args:
            rl_policy_data: RL policy data from trained model
            fallback_policy: Fallback to rule-based policy
            enable_exploration: Whether to use exploration in routing
            exploration_rate: Epsilon for epsilon-greedy exploration
        """
        self.fallback_policy = fallback_policy
        self.enable_exploration = enable_exploration
        self.exploration_rate = exploration_rate

        # RL model components
        self.rl_model: Optional[Dict[str, Any]] = None
        self.feature_maker: Optional[Dict[str, Any]] = None
        self.arms = ["micro", "planner", "deep"]

        # Load RL policy if provided
        if rl_policy_data:
            self.load_rl_policy(rl_policy_data)

        logger.info(
            "RL routing policy initialized",
            has_rl_model=self.rl_model is not None,
            has_fallback=fallback_policy is not None,
            exploration_enabled=enable_exploration,
        )

    def load_rl_policy(self, policy_data: Dict[str, Any]) -> bool:
        """
        Load RL policy from data.

        Args:
            policy_data: Policy data dict

        Returns:
            True if loaded successfully
        """
        try:
            if "routing_policy" in policy_data:
                self.rl_model = policy_data["routing_policy"]
                self.feature_maker = policy_data.get("feature_maker")

                logger.info(
                    "RL routing policy loaded",
                    algorithm=self.rl_model.get("algorithm"),
                    arms=self.rl_model.get("arms"),
                    feature_dim=self.rl_model.get("feature_dim"),
                )

                return True
            else:
                logger.warning("No routing_policy found in data")
                return False

        except Exception as e:
            logger.error("Failed to load RL policy", error=str(e))
            return False

    def _make_features(
        self, text: str, context: Dict[str, Any]
    ) -> Optional[np.ndarray]:
        """
        Create feature vector from text and context.

        Args:
            text: Input text
            context: Additional context information

        Returns:
            Feature vector or None if feature maker not available
        """
        if not self.feature_maker or not np:
            return None

        try:
            # Create episode-like dict for feature extraction
            episode = {
                "intent": context.get("intent", "unknown"),
                "lang": context.get("lang", "sv"),
                "text_len": len(text),
                "word_count": len(text.split()) if text else 0,
                "intent_confidence": context.get("intent_confidence", 0.0),
                "latency_ms": 0.0,  # Not available at decision time
                "cost_usd": 0.0,  # Not available at decision time
                "guardian_state": context.get("guardian_state", "NORMAL"),
                "timestamp": context.get("timestamp"),
            }

            # Transform using feature maker (simplified version)
            features = self._transform_features(episode)
            return np.array(features) if features else None

        except Exception as e:
            logger.error("Feature creation failed", error=str(e))
            return None

    def _transform_features(self, episode: Dict[str, Any]) -> Optional[list[float]]:
        """
        Transform episode to features (simplified FeatureMaker implementation).

        Args:
            episode: Episode dict

        Returns:
            Feature list or None
        """
        if not self.feature_maker:
            return None

        try:
            # Get feature configuration
            dim = self.feature_maker.get("dim", 64)
            numeric_keys = self.feature_maker.get("numeric_keys", [])
            categorical_keys = self.feature_maker.get("categorical_keys", [])
            means = self.feature_maker.get("means", {})
            stds = self.feature_maker.get("stds", {})

            # Create feature vector
            total_dim = dim + len(numeric_keys)
            features = [0.0] * total_dim

            # Categorical features (hashing trick - simplified)
            import hashlib

            for key in categorical_keys:
                val = str(episode.get(key, "")).lower()
                if val and val != "unknown":
                    # Simple hash to feature index
                    hash_val = int(
                        hashlib.md5(f"{key}={val}".encode()).hexdigest()[:8], 16
                    )
                    idx = hash_val % dim
                    features[idx] += 1.0 if (hash_val % 2 == 0) else -1.0

            # Numeric features (z-score normalization)
            for i, key in enumerate(numeric_keys):
                val = float(episode.get(key, 0.0) or 0.0)
                mean = means.get(key, 0.0)
                std = stds.get(key, 1.0)

                normalized = (val - mean) / std
                normalized = max(-10.0, min(10.0, normalized))  # Clip

                features[dim + i] = normalized

            return features

        except Exception as e:
            logger.error("Feature transformation failed", error=str(e))
            return None

    def _rl_predict(self, features: np.ndarray) -> Tuple[str, float, Dict[str, Any]]:
        """
        Make prediction using RL model.

        Args:
            features: Feature vector

        Returns:
            (selected_route, confidence, debug_info)
        """
        if not self.rl_model or not np:
            raise ValueError("RL model not available")

        try:
            alpha = self.rl_model.get("alpha", 0.5)
            arms = self.rl_model.get("arms", self.arms)
            models = self.rl_model.get("models", {})

            best_arm = arms[0]
            best_score = -float("inf")
            arm_scores = {}

            for arm in arms:
                if arm not in models:
                    continue

                model_data = models[arm]
                w = np.array(model_data["w"])
                A_inv = np.array(model_data["A_inv"])

                # Mean prediction
                mean_pred = float(features @ w)

                # UCB: confidence bound
                ucb = alpha * float(np.sqrt(features.T @ A_inv @ features))

                # Final score (exploration vs exploitation)
                if self.enable_exploration:
                    import random

                    if random.random() < self.exploration_rate:
                        # Random exploration
                        score = random.random()
                    else:
                        # UCB exploitation
                        score = mean_pred + ucb
                else:
                    # Pure exploitation (greedy)
                    score = mean_pred

                arm_scores[arm] = {"mean": mean_pred, "ucb": ucb, "score": score}

                if score > best_score:
                    best_score = score
                    best_arm = arm

            # Calculate confidence based on score separation
            sorted_scores = sorted(
                arm_scores.values(), key=lambda x: x["score"], reverse=True
            )
            if len(sorted_scores) >= 2:
                score_gap = sorted_scores[0]["score"] - sorted_scores[1]["score"]
                confidence = min(1.0, max(0.1, score_gap))
            else:
                confidence = 0.5

            debug_info = {
                "algorithm": "linucb_rl",
                "exploration_enabled": self.enable_exploration,
                "exploration_rate": self.exploration_rate,
                "arm_scores": arm_scores,
                "selected_arm": best_arm,
                "confidence": confidence,
            }

            return best_arm, confidence, debug_info

        except Exception as e:
            logger.error("RL prediction failed", error=str(e))
            raise

    def decide_route(
        self, text: str, context: Optional[Dict[str, Any]] = None
    ) -> RouteDecision:
        """
        Decide route using RL policy with fallback.

        Args:
            text: Input text
            context: Additional context

        Returns:
            Route decision
        """
        if context is None:
            context = {}

        # Try RL policy first
        if self.rl_model and np:
            try:
                features = self._make_features(text, context)

                if features is not None:
                    route, confidence, debug_info = self._rl_predict(features)

                    logger.debug(
                        "RL routing decision",
                        route=route,
                        confidence=confidence,
                        text_len=len(text),
                    )

                    return RouteDecision(
                        route=route,
                        confidence=confidence,
                        reason=f"RL LinUCB (conf: {confidence:.2f})",
                        features=debug_info,
                    )

            except Exception as e:
                logger.warning("RL routing failed, using fallback", error=str(e))

        # Fallback to rule-based policy
        if self.fallback_policy and hasattr(self.fallback_policy, "decide_route"):
            try:
                fallback_decision = self.fallback_policy.decide_route(text)

                # Add indication that this was a fallback
                fallback_decision.reason = f"Fallback: {fallback_decision.reason}"
                fallback_decision.features = fallback_decision.features or {}
                fallback_decision.features["fallback_used"] = True

                logger.debug(
                    "Used fallback routing",
                    route=fallback_decision.route,
                    reason=fallback_decision.reason,
                )

                return fallback_decision

            except Exception as e:
                logger.error("Fallback routing also failed", error=str(e))

        # Ultimate fallback - default to micro
        logger.warning("All routing methods failed, defaulting to micro")

        return RouteDecision(
            route="micro",
            confidence=0.1,
            reason="Emergency fallback - all routing failed",
            features={"emergency_fallback": True},
        )

    def update_policy(self, policy_data: Dict[str, Any]) -> bool:
        """
        Update RL policy with new data.

        Args:
            policy_data: New policy data

        Returns:
            True if update successful
        """
        logger.info("Updating RL routing policy")
        return self.load_rl_policy(policy_data)

    def get_status(self) -> Dict[str, Any]:
        """Get policy status for monitoring."""
        status = {
            "type": "rl_routing_policy",
            "has_rl_model": self.rl_model is not None,
            "has_fallback": self.fallback_policy is not None,
            "exploration_enabled": self.enable_exploration,
            "exploration_rate": self.exploration_rate,
            "arms": self.arms,
        }

        if self.rl_model:
            status.update(
                {
                    "algorithm": self.rl_model.get("algorithm"),
                    "feature_dim": self.rl_model.get("feature_dim"),
                    "model_arms": self.rl_model.get("arms"),
                    "alpha": self.rl_model.get("alpha"),
                }
            )

        return status
