"""
Micro LLM driver for Phi-mini - fast responses for simple queries.
"""

import os
import structlog
from typing import Dict, Any, Optional
from .ollama_client import get_ollama_client

logger = structlog.get_logger(__name__)

class MicroPhiDriver:
    """Micro LLM driver using Phi-mini for fast, simple responses"""
    
    def __init__(self):
        self.model = os.getenv("LLM_MICRO", "phi3.5:mini")
        self.client = get_ollama_client()
        
        # Micro-specific settings for fast, concise responses
        self.temperature = 0.3  # Low temperature for consistent, short answers
        self.max_tokens = 150   # Limit response length for speed
        self.top_p = 0.9       # Slightly focused sampling
        
        # Swedish system prompt for micro responses
        self.system_prompt = """Du är Alice, en hjälpsam AI-assistent. 
Ge korta, snabba svar på svenska. Var koncis och direkt.
För enkla frågor som tid, väder, hälsningar - ge snabba, faktiska svar."""
    
    def generate(self, prompt: str, **kwargs) -> Dict[str, Any]:
        """Generate fast response using Phi-mini"""
        try:
            # Override with micro-specific settings
            micro_kwargs = {
                "temperature": kwargs.get("temperature", self.temperature),
                "max_tokens": kwargs.get("max_tokens", self.max_tokens),
                "top_p": kwargs.get("top_p", self.top_p),
                "system": kwargs.get("system", self.system_prompt)
            }
            
            logger.info("Generating micro response", model=self.model, prompt_length=len(prompt))
            
            response = self.client.generate(
                model=self.model,
                prompt=prompt,
                **micro_kwargs
            )
            
            # Extract response text
            response_text = response.get("response", "").strip()
            
            logger.info("Micro response generated", 
                       model=self.model, 
                       response_length=len(response_text),
                       tokens_used=response.get("eval_count", 0))
            
            return {
                "text": response_text,
                "model": self.model,
                "tokens_used": response.get("eval_count", 0),
                "prompt_tokens": response.get("prompt_eval_count", 0),
                "response_tokens": response.get("eval_count", 0),
                "temperature": micro_kwargs["temperature"],
                "route": "micro"
            }
            
        except Exception as e:
            logger.error("Micro generation failed", model=self.model, error=str(e))
            raise
    
    def health_check(self) -> bool:
        """Check if micro model is available"""
        try:
            models = self.client.list_models()
            return self.model in models
        except Exception as e:
            logger.warning("Micro health check failed", model=self.model, error=str(e))
            return False

# Global micro driver instance
_micro_driver: Optional[MicroPhiDriver] = None

def get_micro_driver() -> MicroPhiDriver:
    """Get or create global micro driver instance"""
    global _micro_driver
    if _micro_driver is None:
        _micro_driver = MicroPhiDriver()
    return _micro_driver
