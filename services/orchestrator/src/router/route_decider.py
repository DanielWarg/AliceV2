# services/orchestrator/src/router/route_decider.py
"""
Route Decider med live bandit integration
Väljer route (micro/planner/deep) baserat på context features
"""

from __future__ import annotations

import os
import time
from typing import Any, Dict, Optional, Tuple

import structlog

from .bandit_client import BanditClient

logger = structlog.get_logger()

# Configuration
CANARY_SHARE = float(os.getenv("CANARY_SHARE", "0.05"))  # 5% canary traffic
ENABLE_LEARNING = os.getenv("ENABLE_RL_ROUTING", "true").lower() in ("1", "true", "yes")


class RouteDecider:
    """Route decision maker with bandit integration"""

    def __init__(self):
        self.bandit_client = BanditClient()
        self.total_decisions = 0
        self.canary_decisions = 0
        self.learning_enabled = ENABLE_LEARNING

        print(
            f"RouteDecider initialized: RL={'enabled' if self.learning_enabled else 'disabled'}, canary={CANARY_SHARE}"
        )

    async def decide_route(
        self,
        message: str,
        session_id: str,
        intent: Optional[str] = None,
        intent_confidence: float = 0.0,
        guardian_state: str = "NORMAL",
        context: Optional[Dict[str, Any]] = None,
    ) -> Tuple[str, Dict[str, Any]]:
        """
        Decide which route to use for processing

        Returns: (route_name, decision_metadata)
        """
        start_time = time.time()
        self.total_decisions += 1

        # Extract context features for bandit
        features = self._extract_features(
            message=message,
            intent=intent,
            intent_confidence=intent_confidence,
            guardian_state=guardian_state,
            context=context or {},
        )

        # Use bandit to select route
        selected_route, bandit_metadata = await self.bandit_client.select_route(
            context=features,
            session_id=session_id,
            available_routes=["micro", "planner", "deep"],
        )

        if bandit_metadata.get("canary", False):
            self.canary_decisions += 1

        # Compile decision metadata
        decision_metadata = {
            "route": selected_route,
            "features": features,
            "bandit": bandit_metadata,
            "decision_time_ms": (time.time() - start_time) * 1000,
            "timestamp": time.time(),
        }

        logger.info(
            "route_decided",
            route=selected_route,
            method=bandit_metadata.get("method", "unknown"),
            confidence=bandit_metadata.get("confidence", 0.0),
            canary=bandit_metadata.get("canary", False),
            guardian_state=guardian_state,
            intent=intent,
            intent_conf=intent_confidence,
        )

        return selected_route, decision_metadata

    async def update_route_reward(
        self,
        decision_metadata: Dict[str, Any],
        success: bool,
        latency_ms: float,
        energy_wh: Optional[float] = None,
        safety_ok: bool = True,
    ):
        """Update bandit with route performance feedback"""

        # Calculate φ-weighted reward
        from services.rl.rewards.phi_reward import compute_phi_total

        reward_components = compute_phi_total(
            latency_ms=latency_ms,
            energy_wh=energy_wh,
            safety_ok=safety_ok,
            tool_success=success,
            schema_ok=True,  # Route-level always schema ok
        )

        total_reward = reward_components.get("total", 0.0)

        if total_reward is not None:
            await self.bandit_client.update_reward(
                decision_type="route",
                arm=decision_metadata["route"],
                reward=total_reward,
                context=decision_metadata.get("features"),
            )

            logger.debug(
                "route_reward_updated",
                route=decision_metadata["route"],
                reward=total_reward,
                success=success,
                latency_ms=latency_ms,
                components=reward_components,
            )

    def _extract_features(
        self,
        message: str,
        intent: Optional[str],
        intent_confidence: float,
        guardian_state: str,
        context: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Extract context features for bandit decision"""

        # Basic text features
        len_chars = len(message)
        has_question = any(
            q in message for q in ["?", "vad", "hur", "när", "var", "vilken"]
        )

        # Cache hint (simplified)
        cache_hint = any(
            word in message.lower() for word in ["cache", "minns", "kommer du ihåg"]
        )

        # Previous tool error (from context)
        prev_tool_error = context.get("prev_tool_error", False)

        return {
            "intent_conf": min(1.0, max(0.0, intent_confidence)),
            "len_chars": min(500, len_chars),  # Cap at 500 for feature stability
            "has_question": has_question,
            "cache_hint": cache_hint,
            "guardian_state": guardian_state,
            "prev_tool_error": prev_tool_error,
        }

    def _baseline_route(self, intent: str, guardian_state: str, text_len: int) -> str:
        """Rule-based baseline routing logic"""

        # Emergency: always micro
        if guardian_state == "EMERGENCY":
            return "micro"

        # Simple/fast intents -> micro
        if intent in ["time.info", "weather.info", "smalltalk", "greeting"]:
            return "micro"

        # Long text or complex intents -> deep
        if text_len > 200 or intent in ["analysis", "complex", "research"]:
            # But not during brownout
            if guardian_state == "BROWNOUT":
                return "planner"
            return "deep"

        # Default: planner for most cases
        return "planner"

    def _should_use_canary(self) -> bool:
        """Decide if this request should use canary routing"""
        import random

        return random.random() < CANARY_SHARE

    def update_from_turn(self, decision: Dict[str, Any], reward: float) -> None:
        """Update router from turn result (legacy compatibility)"""
        # This is now handled by update_route_reward
        pass

    async def health_check(self) -> Dict[str, Any]:
        """Check route decider health including bandit connectivity"""
        health = {"status": "healthy", "timestamp": time.time()}

        # Check bandit health
        try:
            bandit_health = await self.bandit_client.health_check()
            health["bandit"] = bandit_health
        except Exception as e:
            health["bandit"] = {"status": "unhealthy", "error": str(e)}
            health["status"] = "degraded"

        return health

    def get_stats(self) -> Dict[str, Any]:
        """Get routing statistics"""
        stats = {
            "total_decisions": self.total_decisions,
            "canary_decisions": self.canary_decisions,
            "canary_rate": self.canary_decisions / max(1, self.total_decisions),
            "learning_enabled": self.learning_enabled,
            "canary_share_target": CANARY_SHARE,
        }

        return stats

    def save_state(self) -> bool:
        """Save router state"""
        # State is now managed by bandit server
        return True


# Convenience function for backward compatibility
async def decide_route(
    message: str,
    session_id: str = "",
    intent: Optional[str] = None,
    intent_confidence: float = 0.0,
    guardian_state: str = "NORMAL",
    context: Optional[Dict[str, Any]] = None,
) -> Tuple[str, Dict[str, Any]]:
    """Standalone route decision function"""
    decider = RouteDecider()
    return await decider.decide_route(
        message=message,
        session_id=session_id,
        intent=intent,
        intent_confidence=intent_confidence,
        guardian_state=guardian_state,
        context=context,
    )
