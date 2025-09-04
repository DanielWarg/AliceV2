"""
Provider Manager for Hybrid Planner - OpenAI primary + local fallback
"""

import os
import time
from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict

import structlog

logger = structlog.get_logger(__name__)


class ProviderType(Enum):
    OPENAI = "openai"
    OLLAMA = "ollama"


@dataclass
class ProviderConfig:
    """Configuration for a provider"""

    type: ProviderType
    name: str
    timeout_ms: int
    max_retries: int
    cost_per_1k_tokens: float = 0.0
    enabled: bool = True


class ProviderManager:
    """Manages provider switching for hybrid planner"""

    def __init__(self):
        self.providers = {
            ProviderType.OPENAI: ProviderConfig(
                type=ProviderType.OPENAI,
                name="OpenAI GPT-4o-mini",
                timeout_ms=600,
                max_retries=2,
                cost_per_1k_tokens=0.00015,  # $0.00015 per 1K tokens
                enabled=os.getenv("OPENAI_API_KEY") is not None,
            ),
            ProviderType.OLLAMA: ProviderConfig(
                type=ProviderType.OLLAMA,
                name="Local Ollama",
                timeout_ms=1200,
                max_retries=1,
                cost_per_1k_tokens=0.0,
                enabled=True,
            ),
        }

        # Circuit breaker settings
        self.circuit_breaker_failures = 5
        self.circuit_breaker_window_s = 30
        self.provider_failures = {pt: 0 for pt in ProviderType}
        self.provider_last_failure = {pt: 0 for pt in ProviderType}

        # Cost tracking
        self.total_cost = 0.0
        self.cost_budget = float(os.getenv("OPENAI_COST_BUDGET", "3.0"))  # $3 default

        # User opt-in for cloud processing
        self.cloud_ok = os.getenv("CLOUD_OK", "false").lower() == "true"

        logger.info(
            "Provider manager initialized",
            openai_enabled=self.providers[ProviderType.OPENAI].enabled,
            cloud_ok=self.cloud_ok,
            cost_budget=self.cost_budget,
        )

    def get_primary_provider(self) -> ProviderType:
        """Get primary provider (OpenAI if available and user opted in)"""
        if (
            self.providers[ProviderType.OPENAI].enabled
            and self.cloud_ok
            and not self._is_circuit_open(ProviderType.OPENAI)
            and self.total_cost < self.cost_budget
        ):
            return ProviderType.OPENAI
        return ProviderType.OLLAMA

    def get_fallback_provider(self, primary: ProviderType) -> ProviderType:
        """Get fallback provider"""
        if primary == ProviderType.OPENAI:
            return ProviderType.OLLAMA
        return ProviderType.OPENAI

    def _is_circuit_open(self, provider: ProviderType) -> bool:
        """Check if circuit breaker is open for provider"""
        now = time.time()
        last_failure = self.provider_last_failure[provider]

        # Reset if window has passed
        if now - last_failure > self.circuit_breaker_window_s:
            self.provider_failures[provider] = 0
            return False

        return self.provider_failures[provider] >= self.circuit_breaker_failures

    def record_provider_failure(self, provider: ProviderType):
        """Record a provider failure"""
        now = time.time()
        self.provider_failures[provider] += 1
        self.provider_last_failure[provider] = now

        logger.warning(
            "Provider failure recorded",
            provider=provider.value,
            failures=self.provider_failures[provider],
            circuit_open=self._is_circuit_open(provider),
        )

    def record_provider_success(self, provider: ProviderType):
        """Record a provider success (reset failure count)"""
        self.provider_failures[provider] = 0
        self.provider_last_failure[provider] = 0

    def record_cost(self, provider: ProviderType, tokens_used: int):
        """Record cost for provider usage"""
        if provider == ProviderType.OPENAI:
            cost = (tokens_used / 1000) * self.providers[provider].cost_per_1k_tokens
            self.total_cost += cost
            logger.info(
                "Cost recorded",
                provider=provider.value,
                tokens_used=tokens_used,
                cost=cost,
                total_cost=self.total_cost,
            )

    def get_provider_stats(self) -> Dict[str, Any]:
        """Get provider statistics"""
        return {
            "primary_provider": self.get_primary_provider().value,
            "cloud_ok": self.cloud_ok,
            "total_cost": self.total_cost,
            "cost_budget": self.cost_budget,
            "providers": {
                pt.value: {
                    "enabled": config.enabled,
                    "failures": self.provider_failures[pt],
                    "circuit_open": self._is_circuit_open(pt),
                    "last_failure": self.provider_last_failure[pt],
                }
                for pt, config in self.providers.items()
            },
        }


# Global provider manager instance
_provider_manager = None


def get_provider_manager() -> ProviderManager:
    """Get global provider manager instance"""
    global _provider_manager
    if _provider_manager is None:
        _provider_manager = ProviderManager()
    return _provider_manager
