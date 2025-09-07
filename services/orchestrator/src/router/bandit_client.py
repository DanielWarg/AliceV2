#!/usr/bin/env python3
"""
Bandit Client för Orchestrator
Kommunicerar med bandit server för live routing decisions
"""

import os
import time
from typing import Any, Dict, List, Optional, Tuple

import httpx
import structlog

logger = structlog.get_logger()

# Configuration
BANDIT_BASE_URL = os.getenv("BANDIT_BASE_URL", "http://localhost:8850")
BANDIT_TIMEOUT_MS = int(os.getenv("BANDIT_TIMEOUT_MS", "40"))
CANARY_SHARE = float(os.getenv("CANARY_SHARE", "0.05"))
BANDIT_ENABLED = os.getenv("BANDIT_ENABLED", "true").lower() in ("1", "true", "yes")


class BanditClient:
    """HTTP client for bandit server"""

    def __init__(self):
        self.client = httpx.AsyncClient(
            base_url=BANDIT_BASE_URL, timeout=BANDIT_TIMEOUT_MS / 1000.0
        )
        self.enabled = BANDIT_ENABLED
        self.canary_share = CANARY_SHARE

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.client.aclose()

    def _should_use_bandit(self, session_id: str) -> bool:
        """Determine if this request should use bandit (canary logic)"""
        if not self.enabled:
            return False

        # Simple hash-based canary assignment
        hash_val = hash(session_id) % 100
        return hash_val < (self.canary_share * 100)

    async def select_route(
        self,
        context: Dict[str, Any],
        session_id: str = "",
        available_routes: Optional[List[str]] = None,
    ) -> Tuple[str, Dict[str, Any]]:
        """
        Select routing arm
        Returns: (selected_route, metadata)
        """
        start_time = time.time()

        # Check if should use bandit
        use_bandit = self._should_use_bandit(session_id)

        metadata = {
            "method": "unknown",
            "confidence": 0.0,
            "latency_ms": 0.0,
            "canary": use_bandit,
            "error": None,
        }

        if not use_bandit:
            # Fallback to static routing logic
            route = self._static_route_fallback(context)
            metadata.update({"method": "static_fallback", "confidence": 0.8})
            return route, metadata

        try:
            # Call bandit server
            response = await self.client.post(
                "/bandit/route",
                json={"context": context, "available_routes": available_routes},
            )
            response.raise_for_status()

            result = response.json()

            metadata.update(
                {
                    "method": result.get("method", "bandit"),
                    "confidence": result.get("confidence", 0.0),
                    "latency_ms": (time.time() - start_time) * 1000,
                }
            )

            selected_route = result.get("arm", "micro")

            logger.info(
                "bandit_route_selected",
                route=selected_route,
                method=metadata["method"],
                confidence=metadata["confidence"],
                latency_ms=metadata["latency_ms"],
            )

            return selected_route, metadata

        except Exception as e:
            # Fallback on error
            route = self._static_route_fallback(context)
            metadata.update(
                {
                    "method": "error_fallback",
                    "confidence": 0.0,
                    "latency_ms": (time.time() - start_time) * 1000,
                    "error": str(e),
                }
            )

            logger.warning(
                "bandit_route_fallback",
                error=str(e),
                fallback_route=route,
                latency_ms=metadata["latency_ms"],
            )

            return route, metadata

    async def select_tool(
        self,
        intent: str,
        session_id: str = "",
        available_tools: Optional[List[str]] = None,
    ) -> Tuple[Optional[str], Dict[str, Any]]:
        """
        Select tool for intent
        Returns: (selected_tool, metadata)
        """
        start_time = time.time()

        use_bandit = self._should_use_bandit(session_id)

        metadata = {
            "method": "unknown",
            "confidence": 0.0,
            "latency_ms": 0.0,
            "canary": use_bandit,
            "error": None,
        }

        if not use_bandit:
            # Fallback to static tool selection
            tool = self._static_tool_fallback(intent, available_tools)
            metadata.update({"method": "static_fallback", "confidence": 0.7})
            return tool, metadata

        try:
            response = await self.client.post(
                "/bandit/tool",
                json={"intent": intent, "available_tools": available_tools},
            )
            response.raise_for_status()

            result = response.json()

            metadata.update(
                {
                    "method": result.get("method", "bandit"),
                    "confidence": result.get("confidence", 0.0),
                    "latency_ms": (time.time() - start_time) * 1000,
                }
            )

            selected_tool = result.get("arm")

            logger.info(
                "bandit_tool_selected",
                intent=intent,
                tool=selected_tool,
                method=metadata["method"],
                confidence=metadata["confidence"],
                latency_ms=metadata["latency_ms"],
            )

            return selected_tool, metadata

        except Exception as e:
            tool = self._static_tool_fallback(intent, available_tools)
            metadata.update(
                {
                    "method": "error_fallback",
                    "confidence": 0.0,
                    "latency_ms": (time.time() - start_time) * 1000,
                    "error": str(e),
                }
            )

            logger.warning(
                "bandit_tool_fallback",
                intent=intent,
                error=str(e),
                fallback_tool=tool,
                latency_ms=metadata["latency_ms"],
            )

            return tool, metadata

    async def update_reward(
        self,
        decision_type: str,
        arm: str,
        reward: float,
        context: Optional[Dict[str, Any]] = None,
        intent: Optional[str] = None,
    ):
        """Update bandit with reward feedback"""
        if not self.enabled:
            return

        try:
            await self.client.post(
                "/bandit/update",
                json={
                    "decision_type": decision_type,
                    "context": context,
                    "intent": intent,
                    "arm": arm,
                    "reward": reward,
                },
            )

            logger.debug(
                "bandit_reward_updated",
                decision_type=decision_type,
                arm=arm,
                reward=reward,
            )

        except Exception as e:
            logger.warning(
                "bandit_update_failed",
                error=str(e),
                decision_type=decision_type,
                arm=arm,
                reward=reward,
            )

    def _static_route_fallback(self, context: Dict[str, Any]) -> str:
        """Static fallback routing logic"""
        guardian_state = context.get("guardian_state", "NORMAL")
        intent_conf = context.get("intent_conf", 0.0)
        len_chars = context.get("len_chars", 0)

        # Emergency -> micro
        if guardian_state == "EMERGENCY":
            return "micro"

        # Brownout -> micro for simple queries
        if guardian_state == "BROWNOUT":
            if len_chars < 50 and intent_conf > 0.8:
                return "micro"

        # High confidence, short -> micro
        if intent_conf > 0.9 and len_chars < 30:
            return "micro"

        # Complex queries -> planner
        if len_chars > 100 or intent_conf < 0.5:
            return "planner"

        # Default to micro for safety
        return "micro"

    def _static_tool_fallback(
        self, intent: str, available_tools: Optional[List[str]] = None
    ) -> Optional[str]:
        """Static fallback tool selection"""
        # Simple mapping for common intents
        static_mapping = {
            "time_query": "time_tool",
            "weather_query": "weather_tool",
            "calculation": "calculator_tool",
            "greeting": "chat_tool",
            "goodbye": "chat_tool",
        }

        preferred = static_mapping.get(intent, "fallback_tool")

        if available_tools:
            if preferred in available_tools:
                return preferred
            elif "fallback_tool" in available_tools:
                return "fallback_tool"
            elif available_tools:
                return available_tools[0]

        return preferred

    async def health_check(self) -> Dict[str, Any]:
        """Check bandit server health"""
        try:
            response = await self.client.get("/health")
            response.raise_for_status()
            return response.json()
        except Exception as e:
            return {"status": "unhealthy", "error": str(e)}
