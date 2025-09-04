"""
NLU Client with Circuit Breaker protection and fallback logic.
Handles intent classification with graceful degradation.
"""

import os
from typing import Any, Dict, Optional

import httpx
import structlog

from ..utils.circuit_breaker import (
    CircuitBreakerConfig,
    CircuitOpenError,
    get_circuit_breaker,
)

logger = structlog.get_logger(__name__)


class NLUResult:
    """NLU parsing result with fallback handling"""

    def __init__(
        self,
        intent: str,
        confidence: float,
        slots: Dict[str, Any] = None,
        route_hint: str = "planner",
        source: str = "nlu",
        validated: bool = False,
    ):
        self.intent = intent
        self.confidence = confidence
        self.slots = slots or {}
        self.route_hint = route_hint
        self.source = source  # "nlu", "fallback", "cache"
        self.validated = validated


class NLUClient:
    """NLU client with circuit breaker and fallback logic"""

    def __init__(self, base_url: str = None):
        self.base_url = base_url or os.getenv("NLU_URL", "http://alice-nlu:9002")
        self.timeout = float(os.getenv("NLU_TIMEOUT_MS", "1000")) / 1000.0

        # Circuit breaker configuration - more lenient for NLU
        cb_config = CircuitBreakerConfig(
            failure_threshold=3,  # 3 failures before opening
            recovery_timeout=30.0,  # Try again after 30 seconds
            success_threshold=2,  # 2 successes to close
            timeout=self.timeout,
        )

        self.circuit_breaker = get_circuit_breaker("nlu_service", cb_config)

        # Fallback patterns for when NLU is unavailable
        self.fallback_patterns = {
            # Greetings - route to micro
            ("hej", "hello", "hi", "tjena", "hallå", "god morgon", "god dag"): (
                "greeting.hello",
                "micro",
                0.9,
            ),
            # Time queries - route to micro
            ("klockan", "tid", "time", "när är det", "vad är klockan"): (
                "time.now",
                "micro",
                0.9,
            ),
            # Weather - route to micro
            ("väder", "vädret", "weather", "temperatur", "regn", "sol"): (
                "weather.lookup",
                "micro",
                0.8,
            ),
            # Calendar/booking - route to planner
            ("boka", "möte", "kalender", "schedule", "planera"): (
                "calendar.create",
                "planner",
                0.7,
            ),
            # Email - route to planner
            ("mail", "email", "e-post", "skicka", "meddelande"): (
                "email.create",
                "planner",
                0.7,
            ),
            # Memory operations - route to planner
            ("kom ihåg", "minne", "spara", "anteckna", "note"): (
                "memory.store",
                "planner",
                0.7,
            ),
            # Search operations - route to planner
            ("hitta", "sök", "search", "leta", "finn"): (
                "search.query",
                "planner",
                0.6,
            ),
        }

    async def parse(self, text: str, lang: str = "sv") -> NLUResult:
        """Parse text with NLU service, fallback on failure"""

        try:
            # Try NLU service with circuit breaker protection
            result = self.circuit_breaker.call(self._call_nlu_service, text, lang)
            return result

        except CircuitOpenError:
            logger.warn("NLU circuit breaker open - using fallback", text=text[:50])
            return self._fallback_parse(text)

        except Exception as e:
            logger.warn(
                "NLU service call failed - using fallback", error=str(e), text=text[:50]
            )
            return self._fallback_parse(text)

    def _call_nlu_service(self, text: str, lang: str) -> NLUResult:
        """Call actual NLU service (protected by circuit breaker)"""

        payload = {"text": text, "lang": lang, "version": "1"}

        with httpx.Client(timeout=self.timeout) as client:
            response = client.post(f"{self.base_url}/api/nlu/parse", json=payload)
            response.raise_for_status()

            data = response.json()

            return NLUResult(
                intent=data["intent"]["label"],
                confidence=data["intent"]["confidence"],
                slots=data.get("slots", {}),
                route_hint=data.get("route_hint", "planner"),
                source="nlu",
                validated=data["intent"].get("validated", False),
            )

    def _fallback_parse(self, text: str) -> NLUResult:
        """Simple keyword-based fallback when NLU unavailable"""

        text_lower = text.lower()

        # Check fallback patterns
        for keywords, (
            intent,
            route_hint,
            confidence,
        ) in self.fallback_patterns.items():
            if any(keyword in text_lower for keyword in keywords):
                logger.info(
                    "Fallback NLU match",
                    intent=intent,
                    route_hint=route_hint,
                    confidence=confidence,
                )

                return NLUResult(
                    intent=intent,
                    confidence=confidence,
                    slots={},  # No slot extraction in fallback
                    route_hint=route_hint,
                    source="fallback",
                )

        # Default fallback - route to planner for complex handling
        logger.info("No fallback match - routing to planner", text=text[:50])

        return NLUResult(
            intent="general.query",
            confidence=0.5,
            slots={},
            route_hint="planner",
            source="fallback",
        )

    async def health_check(self) -> Dict[str, Any]:
        """Check NLU service health"""

        try:
            with httpx.Client(timeout=2.0) as client:
                response = client.get(f"{self.base_url}/healthz")
                response.raise_for_status()

                return {
                    "status": "healthy",
                    "circuit_breaker": self.circuit_breaker.get_stats(),
                    "response_time_ms": response.elapsed.total_seconds() * 1000,
                }

        except Exception as e:
            return {
                "status": "unhealthy",
                "error": str(e),
                "circuit_breaker": self.circuit_breaker.get_stats(),
            }


# Global NLU client instance
_nlu_client: Optional[NLUClient] = None


def get_nlu_client() -> NLUClient:
    """Get or create global NLU client"""
    global _nlu_client
    if _nlu_client is None:
        _nlu_client = NLUClient()
    return _nlu_client
