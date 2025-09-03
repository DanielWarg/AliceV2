"""
Micro LLM driver for fast responses via Ollama with version-controlled cache.
"""

import os
import structlog
import httpx
from typing import Dict, Any, Optional

logger = structlog.get_logger(__name__)

class MicroPhiDriver:
    """Micro LLM driver using Ollama for fast, simple responses"""
    
    def __init__(self, base_url: str, model: str):
        self._base_url = base_url.rstrip("/")
        self._model = model
        
        # Fail-fast: säkerställ att /tags svarar innan vi kör generate
        try:
            with httpx.Client(timeout=3.0) as client:
                r = client.get(f"{self._base_url}/api/tags")
                r.raise_for_status()
                logger.info(f"MicroLLM healthcheck OK at {self._base_url}/tags")
        except Exception as e:
            logger.error(f"MicroLLM healthcheck failed at {self._base_url}/tags: {e}")
            raise
        
        # Micro-specific settings for fast, concise responses
        self.temperature = 0.3  # Low temperature for consistent, short answers
        self.max_tokens = 150   # Limit response length for speed
        self.top_p = 0.9       # Slightly focused sampling
        
        # Swedish system prompt for micro responses
        self.system_prompt = """Du är Alice, en hjälpsam AI-assistent som alltid svarar på svenska.
Var kort och koncis (max 2-3 meningar). Var hjälpsam och vänlig."""
    
    @property
    def model(self) -> str:
        return self._model
    
    @property
    def base_url(self) -> str:
        return self._base_url
    
    def generate(self, prompt: str, **kwargs) -> Dict[str, Any]:
        """Generate fast response using Ollama model"""
        try:
            # Override with micro-specific settings
            micro_kwargs = {
                "temperature": kwargs.get("temperature", self.temperature),
                "max_tokens": kwargs.get("max_tokens", self.max_tokens),
                "top_p": kwargs.get("top_p", self.top_p),
                "system": kwargs.get("system", self.system_prompt)
            }
            
            payload = {
                "model": self._model,
                "prompt": prompt,
                "stream": False
            }
            payload.update(micro_kwargs)
            
            url = f"{self._base_url}/generate"
            logger.info(f"MicroLLM request -> {url} model={self._model}")
            
            with httpx.Client(timeout=60.0) as client:
                response = client.post(url, json=payload)
                response.raise_for_status()
                data = response.json()
            
            # Extract response text
            response_text = data.get("response", "").strip()
            
            logger.info("Micro response generated", 
                       model=self._model, 
                       response_length=len(response_text),
                       tokens_used=data.get("eval_count", 0))
            
            return {
                "text": response_text,
                "model": self._model,
                "tokens_used": data.get("eval_count", 0),
                "prompt_tokens": data.get("prompt_eval_count", 0),
                "response_tokens": data.get("eval_count", 0),
                "temperature": micro_kwargs["temperature"],
                "route": "micro"
            }
            
        except Exception as e:
            logger.error("Micro generation failed", model=self._model, error=str(e))
            raise
    
    def health_check(self) -> bool:
        """Check if micro model is available"""
        try:
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
