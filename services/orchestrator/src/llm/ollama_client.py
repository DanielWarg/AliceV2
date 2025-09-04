"""
Ollama client for LLM integration with proper timeouts and error handling.
"""

import os
import time
from dataclasses import dataclass
from typing import Any, Dict, Optional

import httpx
import structlog

logger = structlog.get_logger(__name__)


@dataclass
class OllamaConfig:
    """Configuration for Ollama client"""

    host: str = "http://ollama:11434"
    timeout_ms: int = 1500  # Reduced from 1800ms to 1500ms for SLO compliance
    keep_alive: int = 120
    max_retries: int = 2
    retry_delay: float = 0.5


class OllamaClient:
    """Client for Ollama LLM API with proper error handling and timeouts"""

    def __init__(self, config: Optional[OllamaConfig] = None):
        self.config = config or OllamaConfig()
        self.client = httpx.Client(
            timeout=httpx.Timeout(self.config.timeout_ms / 1000.0),
            limits=httpx.Limits(max_keepalive_connections=5, max_connections=10),
        )
        self._base_url = self.config.host.rstrip("/")

    def _make_request(self, endpoint: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Make request to Ollama API with retry logic"""
        url = f"{self._base_url}{endpoint}"
        logger.info(
            "Making Ollama request", url=url, endpoint=endpoint, base_url=self._base_url
        )

        for attempt in range(self.config.max_retries + 1):
            try:
                response = self.client.post(url, json=data)
                response.raise_for_status()
                return response.json()
            except httpx.TimeoutException:
                logger.warning(
                    f"Ollama timeout on attempt {attempt + 1}",
                    endpoint=endpoint,
                    attempt=attempt,
                )
                if attempt == self.config.max_retries:
                    raise
                time.sleep(self.config.retry_delay * (attempt + 1))
            except httpx.HTTPStatusError as e:
                logger.error(
                    f"Ollama HTTP error: {e.response.status_code}",
                    endpoint=endpoint,
                    status_code=e.response.status_code,
                )
                raise
            except Exception as e:
                logger.error("Ollama request failed", endpoint=endpoint, error=str(e))
                raise

    def generate(self, model: str, prompt: str, **kwargs) -> Dict[str, Any]:
        """Generate text using Ollama model"""
        data = {
            "model": model,
            "prompt": prompt,
            "stream": False,
            "keep_alive": f"{self.config.keep_alive}s",
        }

        # Add grammar if provided
        if "grammar" in kwargs:
            data["grammar"] = kwargs["grammar"]

        # Add optional parameters
        if "temperature" in kwargs:
            data["temperature"] = kwargs["temperature"]
        if "top_p" in kwargs:
            data["top_p"] = kwargs["top_p"]
        if "top_k" in kwargs:
            data["top_k"] = kwargs["top_k"]
        if "max_tokens" in kwargs:
            data["max_tokens"] = kwargs["max_tokens"]
        if "system" in kwargs:
            data["system"] = kwargs["system"]
        if "format" in kwargs:
            data["format"] = kwargs["format"]
        if "stop" in kwargs:
            data["stop"] = kwargs["stop"]

        # Collect advanced options into Ollama "options" map
        options: Dict[str, Any] = {}
        # Common low-footprint settings
        if "num_ctx" in kwargs:
            options["num_ctx"] = kwargs["num_ctx"]
        if "num_predict" in kwargs:
            options["num_predict"] = kwargs["num_predict"]
        # Duplicate core sampling into options for maximum compatibility
        if "temperature" in kwargs:
            options["temperature"] = kwargs["temperature"]
        if "top_p" in kwargs:
            options["top_p"] = kwargs["top_p"]
        if "top_k" in kwargs:
            options["top_k"] = kwargs["top_k"]
        if options:
            data["options"] = options

        return self._make_request("/api/generate", data)

    def health_check(self) -> bool:
        """Check if Ollama is healthy"""
        try:
            response = self.client.get(f"{self._base_url}/api/tags")
            return response.status_code == 200
        except Exception as e:
            logger.warning("Ollama health check failed", error=str(e))
            return False

    def list_models(self) -> list:
        """List available models"""
        try:
            response = self.client.get(f"{self._base_url}/api/tags")
            response.raise_for_status()
            data = response.json()
            return [model["name"] for model in data.get("models", [])]
        except Exception as e:
            logger.error("Failed to list Ollama models", error=str(e))
            return []

    def close(self):
        """Close the client"""
        self.client.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()


# Global client instance
_ollama_client: Optional[OllamaClient] = None


def get_ollama_client() -> OllamaClient:
    """Get or create global Ollama client instance"""
    global _ollama_client
    # Always create new client to ensure fresh config
    if _ollama_client is not None:
        _ollama_client.close()
        _ollama_client = None

    config = OllamaConfig(
        host=os.getenv("OLLAMA_HOST", "http://dev-proxy:80/ollama"),
        timeout_ms=int(
            os.getenv("LLM_TIMEOUT_MS", "1500")
        ),  # Reduced to 1500ms for SLO compliance
        keep_alive=int(os.getenv("LLM_KEEP_ALIVE", "120")),
    )
    _ollama_client = OllamaClient(config)
    return _ollama_client


def reset_ollama_client():
    """Reset the global Ollama client instance (for testing/config changes)"""
    global _ollama_client
    if _ollama_client is not None:
        _ollama_client.close()
        _ollama_client = None
