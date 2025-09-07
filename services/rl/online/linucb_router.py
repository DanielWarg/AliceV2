# services/rl/online/linucb_router.py
"""
LinUCB Router för intelligent route-val baserat på kontext
"""

from __future__ import annotations

import os
from typing import Any, Dict, List, Optional

import numpy as np

from services.rl.persistence.bandit_store import (
    LinUCBArm,
    init_empty_linucb,
    load_linucb,
    save_linucb,
)

# Configuration från environment
DEFAULT_ALPHA = float(os.getenv("RL_BANDIT_ALPHA", "0.8"))
DEFAULT_ACTIONS = ["micro", "planner", "deep"]
FEATURE_DIM = 6  # intent_conf, len_chars, has_question, cache_hint, guardian_level, prev_tool_error


class LinUCBRouter:
    """LinUCB-based routing decision maker"""

    def __init__(
        self,
        actions: Optional[List[str]] = None,
        alpha: Optional[float] = None,
        dim: int = FEATURE_DIM,
    ):
        self.actions = actions or DEFAULT_ACTIONS
        self.alpha = alpha or DEFAULT_ALPHA
        self.dim = dim
        self.update_count = 0

        # Try to load existing state
        self.state = load_linucb()
        if self.state is None:
            # Initialize empty state
            self.state = init_empty_linucb(self.actions, dim, self.alpha)
            print(f"Initialized new LinUCB router with {len(self.actions)} actions")
        else:
            print(
                f"Loaded LinUCB router with {len(self.state.arms)} arms, {self._total_pulls()} total pulls"
            )

    def _total_pulls(self) -> int:
        """Get total number of pulls across all arms"""
        return sum(arm.pulls for arm in self.state.arms.values())

    def _extract_features(self, context: Dict[str, Any]) -> np.ndarray:
        """Extract features from context for LinUCB"""
        # Extrahera och normalisera features
        intent_conf = float(context.get("intent_conf", 0.5))  # 0..1
        len_chars = min(
            float(context.get("len_chars", 0)) / 500.0, 1.0
        )  # normalize to 0..1
        has_question = 1.0 if context.get("has_question", False) else 0.0
        cache_hint = 1.0 if context.get("cache_hint", False) else 0.0

        # Guardian state as numeric: NORMAL=1, BROWNOUT=0.5, EMERGENCY=0
        guardian_state = context.get("guardian_state", "NORMAL")
        if guardian_state == "NORMAL":
            guardian_level = 1.0
        elif guardian_state == "BROWNOUT":
            guardian_level = 0.5
        else:  # EMERGENCY
            guardian_level = 0.0

        prev_tool_error = 1.0 if context.get("prev_tool_error", False) else 0.0

        return np.array(
            [
                1.0,  # bias term
                intent_conf,  # confidence from NLU
                len_chars,  # normalized text length
                has_question,  # has question mark
                cache_hint,  # cache hit likely
                guardian_level,  # system health
                prev_tool_error,  # previous tool failed
            ][: self.dim]
        )  # Clip to actual dimension

    def _compute_ucb(self, arm: LinUCBArm, context: np.ndarray) -> float:
        """Compute upper confidence bound for an arm"""
        A = np.array(arm.A)
        b = np.array(arm.b)

        try:
            A_inv = np.linalg.inv(A)
        except np.linalg.LinAlgError:
            # Use pseudo-inverse if singular
            A_inv = np.linalg.pinv(A)

        theta = A_inv @ b
        mean_reward = theta @ context

        # Confidence width
        confidence = self.state.alpha * np.sqrt(context.T @ A_inv @ context)

        return mean_reward + confidence

    def select(self, context: Dict[str, Any]) -> str:
        """Select best action using LinUCB"""
        features = self._extract_features(context)

        # Special case: Emergency guardian state -> force micro
        if context.get("guardian_state") == "EMERGENCY":
            return "micro"

        # Compute UCB for each arm
        ucb_values = {}
        for action_name, arm in self.state.arms.items():
            ucb_values[action_name] = self._compute_ucb(arm, features)

        # Select action with highest UCB
        best_action = max(ucb_values.items(), key=lambda x: x[1])[0]

        return best_action

    def update(self, context: Dict[str, Any], action: str, reward: float) -> None:
        """Update LinUCB parameters after observing reward"""
        if action not in self.state.arms:
            print(f"Warning: Unknown action {action}, ignoring update")
            return

        # Clip reward to [0, 1]
        reward = max(0.0, min(1.0, float(reward)))

        features = self._extract_features(context).reshape(-1, 1)
        arm = self.state.arms[action]

        # Update A and b matrices
        A = np.array(arm.A) + (features @ features.T)
        b = np.array(arm.b) + (reward * features.flatten())

        # Store back as lists
        arm.A = A.tolist()
        arm.b = b.tolist()
        arm.pulls += 1
        arm.reward_sum += reward

        self.update_count += 1

        # Adaptive alpha: reduce exploration as we get more confident
        if self.update_count > 100:
            self.state.alpha = max(
                0.1, DEFAULT_ALPHA * np.exp(-self.update_count / 1000)
            )

    def get_stats(self) -> Dict[str, Any]:
        """Get router statistics"""
        stats = {
            "total_updates": self.update_count,
            "alpha": self.state.alpha,
            "arms": {},
        }

        for name, arm in self.state.arms.items():
            avg_reward = arm.reward_sum / max(1, arm.pulls)
            stats["arms"][name] = {
                "pulls": arm.pulls,
                "avg_reward": avg_reward,
                "total_reward": arm.reward_sum,
            }

        return stats

    def save(self) -> bool:
        """Save current state to disk"""
        return save_linucb(self.state)

    def get_action_probabilities(
        self, context: Dict[str, Any], temperature: float = 1.0
    ) -> Dict[str, float]:
        """Get softmax probabilities over actions (for monitoring)"""
        features = self._extract_features(context)

        # Get UCB values
        ucb_values = []
        action_names = []
        for action_name, arm in self.state.arms.items():
            ucb_values.append(self._compute_ucb(arm, features))
            action_names.append(action_name)

        ucb_values = np.array(ucb_values)

        # Apply temperature and softmax
        if temperature > 0:
            scaled_values = ucb_values / temperature
            exp_values = np.exp(
                scaled_values - np.max(scaled_values)
            )  # numerical stability
            probs = exp_values / np.sum(exp_values)
        else:
            # Greedy selection
            probs = np.zeros_like(ucb_values)
            probs[np.argmax(ucb_values)] = 1.0

        return {name: prob for name, prob in zip(action_names, probs)}


# Test router if run directly
if __name__ == "__main__":
    print("Testing LinUCB Router...")

    router = LinUCBRouter()

    # Test context
    context = {
        "intent_conf": 0.9,
        "len_chars": 25,
        "has_question": True,
        "cache_hint": False,
        "guardian_state": "NORMAL",
        "prev_tool_error": False,
    }

    print(f"Initial stats: {router.get_stats()}")

    # Make some decisions and updates
    for i in range(10):
        action = router.select(context)
        reward = 0.8 if action == "micro" else 0.6  # micro is better for this context
        router.update(context, action, reward)
        print(f"Step {i}: selected {action}, reward {reward}")

    print(f"Final stats: {router.get_stats()}")

    # Test probabilities
    probs = router.get_action_probabilities(context)
    print(f"Action probabilities: {probs}")

    # Save state
    router.save()
    print("Router state saved!")
