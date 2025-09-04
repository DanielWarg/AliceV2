"""
Deep LLM driver for Llama-3.1 - on-demand loading with Guardian integration.
"""

import os
import time
from typing import Any, Dict, Optional

import structlog

from .ollama_client import get_ollama_client

logger = structlog.get_logger(__name__)


class DeepLlamaDriver:
    """Deep LLM driver using Llama-3.1 for complex reasoning (on-demand)"""

    def __init__(self):
        self.model = os.getenv("LLM_DEEP", "llama3.1:8b")
        self.client = get_ollama_client()

        # Deep-specific settings for complex reasoning
        self.temperature = 0.2  # Balanced creativity for complex tasks
        self.max_tokens = 1000  # Allow longer responses for analysis
        self.top_p = 0.9  # More creative sampling for complex reasoning

        # Swedish system prompt for deep reasoning
        self.system_prompt = """Du är Alice, en AI-assistent för djup analys och komplexa uppgifter.
Du är specialiserad på utförliga svar, analyser och sammanfattningar på svenska.
Ge detaljerade, välstrukturerade svar för komplexa frågor."""

        # On-demand loading state
        self._initialized = False
        self._last_used = 0
        self._keep_alive_timeout = 120  # 2 minutes

    def _ensure_initialized(self):
        """Ensure deep model is loaded (lazy initialization)"""
        if not self._initialized:
            logger.info("Initializing deep model", model=self.model)
            try:
                # Check if model is available
                models = self.client.list_models()
                if self.model not in models:
                    logger.warning(
                        "Deep model not available, will use fallback", model=self.model
                    )
                    return False

                self._initialized = True
                self._last_used = time.time()
                logger.info("Deep model initialized", model=self.model)
                return True

            except Exception as e:
                logger.error(
                    "Failed to initialize deep model", model=self.model, error=str(e)
                )
                return False

        # Update last used time
        self._last_used = time.time()
        return True

    def _check_guardian_allowance(self) -> bool:
        """Check if Guardian allows deep model usage"""
        try:
            # Import here to avoid circular imports
            from ..guardian_client import GuardianClient

            guardian = GuardianClient()
            health = guardian.get_health()

            # Block deep model if Guardian is not in NORMAL state
            if health.get("state") != "NORMAL":
                logger.warning(
                    "Deep model blocked by Guardian", guardian_state=health.get("state")
                )
                return False

            return True

        except Exception as e:
            logger.warning(
                "Could not check Guardian state, allowing deep model", error=str(e)
            )
            return True

    def generate(self, prompt: str, **kwargs) -> Dict[str, Any]:
        """Generate deep response using Llama-3.1"""
        try:
            # Check Guardian allowance first
            if not self._check_guardian_allowance():
                return {
                    "text": "Jag kan inte utföra denna komplexa analys just nu på grund av systembelastning. Försök igen senare.",
                    "model": self.model,
                    "route": "deep",
                    "blocked_by_guardian": True,
                    "fallback_used": True,
                }

            # Ensure model is initialized
            if not self._ensure_initialized():
                return {
                    "text": "Jag kan inte utföra denna komplexa analys just nu. Försök igen senare.",
                    "model": self.model,
                    "route": "deep",
                    "model_unavailable": True,
                    "fallback_used": True,
                }

            # Override with deep-specific settings
            deep_kwargs = {
                "temperature": kwargs.get("temperature", self.temperature),
                "max_tokens": kwargs.get("max_tokens", self.max_tokens),
                "top_p": kwargs.get("top_p", self.top_p),
                "system": kwargs.get("system", self.system_prompt),
            }

            logger.info(
                "Generating deep response", model=self.model, prompt_length=len(prompt)
            )

            response = self.client.generate(
                model=self.model, prompt=prompt, **deep_kwargs
            )

            # Extract response text
            response_text = response.get("response", "").strip()

            logger.info(
                "Deep response generated",
                model=self.model,
                response_length=len(response_text),
                tokens_used=response.get("eval_count", 0),
            )

            return {
                "text": response_text,
                "model": self.model,
                "tokens_used": response.get("eval_count", 0),
                "prompt_tokens": response.get("prompt_eval_count", 0),
                "response_tokens": response.get("eval_count", 0),
                "temperature": deep_kwargs["temperature"],
                "route": "deep",
                "blocked_by_guardian": False,
                "fallback_used": False,
            }

        except Exception as e:
            logger.error("Deep generation failed", model=self.model, error=str(e))
            raise

    def health_check(self) -> bool:
        """Check if deep model is available"""
        try:
            models = self.client.list_models()
            return self.model in models
        except Exception as e:
            logger.warning("Deep health check failed", model=self.model, error=str(e))
            return False

    def is_idle(self) -> bool:
        """Check if model has been idle for too long"""
        if not self._initialized:
            return True

        idle_time = time.time() - self._last_used
        return idle_time > self._keep_alive_timeout


# Global deep driver instance
_deep_driver: Optional[DeepLlamaDriver] = None


def get_deep_driver() -> DeepLlamaDriver:
    """Get or create global deep driver instance"""
    global _deep_driver
    if _deep_driver is None:
        _deep_driver = DeepLlamaDriver()
    return _deep_driver
