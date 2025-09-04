"""
Micro LLM driver for fast responses via Ollama with version-controlled cache.
Now uses MicroClient interface for mock/real abstraction.
"""

import os
from typing import Any, Dict

import structlog

logger = structlog.get_logger(__name__)


class MicroPhiDriver:
    """Micro LLM driver using MicroClient interface"""

    def __init__(self, base_url: str, model: str):
        self._base_url = base_url.rstrip("/")
        self._model = model

        # Import here to avoid circular imports
        from .micro_client import get_micro_client

        self._client = get_micro_client()

        # Micro-specific settings for fast, concise responses
        self.temperature = 0.3  # Low temperature for consistent, short answers
        self.max_tokens = 150  # Limit response length for speed
        self.top_p = 0.9  # Slightly focused sampling

    @property
    def model(self) -> str:
        return self._model

    @property
    def base_url(self) -> str:
        return self._base_url

    def generate(self, prompt: str, **kwargs) -> Dict[str, Any]:
        """Generate fast response using MicroClient interface"""
        try:
            # Override with micro-specific settings
            micro_kwargs = {
                "temperature": kwargs.get("temperature", self.temperature),
                "max_tokens": kwargs.get("max_tokens", self.max_tokens),
                "top_p": kwargs.get("top_p", self.top_p),
            }

            # Use MicroClient interface
            result = self._client.generate(prompt, **micro_kwargs)

            # Add route info
            result["route"] = "micro"

            logger.info(
                "Micro response generated",
                model=result["model"],
                response_length=len(result["text"]),
                tokens_used=result["tokens_used"],
                mock_used=result.get("mock_used", False),
            )

            return result

        except Exception as e:
            logger.error("Micro generation failed", model=self._model, error=str(e))
            raise

    def health_check(self) -> bool:
        """Check if micro model is available"""
        try:
            # For mock mode, always return True
            if hasattr(self._client, "mock_used") and self._client.mock_used:
                return True

            # For real mode, check Ollama
            import httpx

            with httpx.Client(timeout=3.0) as client:
                response = client.get(f"{self._base_url}/api/tags")
                response.raise_for_status()
                data = response.json()
                models = [model["name"] for model in data.get("models", [])]
                return self._model in models
        except Exception as e:
            logger.warning("Micro health check failed", model=self._model, error=str(e))
            return False


# Version-controlled cache
_driver_cache: Dict[str, MicroPhiDriver] = {}


def get_micro_driver() -> MicroPhiDriver:
    """Get or create global micro driver instance with version-controlled cache"""
    base_url = os.getenv("OLLAMA_BASE_URL", "http://dev-proxy:80/ollama/api")
    model = os.getenv("MICRO_MODEL", "llama2:7b")
    version = os.getenv("MICRO_DRIVER_VERSION", "1")

    key = f"{base_url}|{model}|{version}"
    drv = _driver_cache.get(key)

    if drv and drv.base_url == base_url and drv.model == model:
        return drv

    # Create new driver instance
    drv = MicroPhiDriver(base_url=base_url, model=model)
    _driver_cache.clear()  # Keep it simple – one active per key
    _driver_cache[key] = drv

    logger.info(f"MicroLLM init: base_url={base_url}, model={model}, version={version}")
    return drv


def reset_micro_driver():
    """Reset the global micro driver cache (for testing/config changes)"""
    global _driver_cache
    _driver_cache.clear()
