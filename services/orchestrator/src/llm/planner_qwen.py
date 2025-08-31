"""
Planner LLM driver for Qwen-MoE - structured planning with JSON output.
"""

import os
import json
import structlog
from typing import Dict, Any, Optional, List
from .ollama_client import get_ollama_client

logger = structlog.get_logger(__name__)

class PlannerQwenDriver:
    """Planner LLM driver using Qwen-MoE for structured tool planning"""
    
    def __init__(self):
        self.model = os.getenv("LLM_PLANNER", "qwen2.5:7b-moe")
        self.client = get_ollama_client()
        
        # Planner-specific settings for structured planning
        self.temperature = 0.1  # Very low temperature for consistent JSON output
        self.max_tokens = 500   # Allow longer responses for planning
        self.top_p = 0.8       # Focused sampling for structured output
        
        # Swedish system prompt for planner with JSON output
        self.system_prompt = """Du är Alice, en AI-assistent som planerar och utför åtgärder.
Du ska svara med JSON-format för att strukturera dina planer och verktygsanrop.

Tillgängliga verktyg:
- calendar.create: Skapa kalenderhändelser
- email.draft: Skapa e-postutkast
- weather.get: Hämta väderinformation
- time.get: Hämta aktuell tid

Svara alltid med JSON-format:
{
  "plan": "Beskrivning av planen",
  "steps": [
    {
      "tool": "verktygsnamn",
      "args": {"param1": "värde1"},
      "reason": "Varför detta steg behövs"
    }
  ],
  "response": "Kort svar till användaren"
}"""
    
    def generate(self, prompt: str, **kwargs) -> Dict[str, Any]:
        """Generate structured plan using Qwen-MoE"""
        try:
            # Override with planner-specific settings
            planner_kwargs = {
                "temperature": kwargs.get("temperature", self.temperature),
                "max_tokens": kwargs.get("max_tokens", self.max_tokens),
                "top_p": kwargs.get("top_p", self.top_p),
                "system": kwargs.get("system", self.system_prompt)
            }
            
            logger.info("Generating planner response", model=self.model, prompt_length=len(prompt))
            
            response = self.client.generate(
                model=self.model,
                prompt=prompt,
                **planner_kwargs
            )
            
            # Extract response text
            response_text = response.get("response", "").strip()
            
            # Try to parse JSON from response
            parsed_json = self._parse_json_response(response_text)
            
            logger.info("Planner response generated", 
                       model=self.model, 
                       response_length=len(response_text),
                       tokens_used=response.get("eval_count", 0),
                       json_valid=parsed_json is not None)
            
            return {
                "text": response_text,
                "model": self.model,
                "tokens_used": response.get("eval_count", 0),
                "prompt_tokens": response.get("prompt_eval_count", 0),
                "response_tokens": response.get("eval_count", 0),
                "temperature": planner_kwargs["temperature"],
                "route": "planner",
                "json_parsed": parsed_json is not None,
                "plan": parsed_json
            }
            
        except Exception as e:
            logger.error("Planner generation failed", model=self.model, error=str(e))
            raise
    
    def _parse_json_response(self, response_text: str) -> Optional[Dict[str, Any]]:
        """Parse JSON from response text, handling common formatting issues"""
        try:
            # Try to extract JSON from the response
            # Look for JSON between ```json and ``` markers
            if "```json" in response_text and "```" in response_text:
                start = response_text.find("```json") + 7
                end = response_text.find("```", start)
                json_text = response_text[start:end].strip()
            else:
                # Try to find JSON object in the text
                start = response_text.find("{")
                end = response_text.rfind("}") + 1
                if start >= 0 and end > start:
                    json_text = response_text[start:end]
                else:
                    return None
            
            return json.loads(json_text)
            
        except (json.JSONDecodeError, ValueError) as e:
            logger.warning("Failed to parse JSON from planner response", error=str(e))
            return None
    
    def health_check(self) -> bool:
        """Check if planner model is available"""
        try:
            models = self.client.list_models()
            return self.model in models
        except Exception as e:
            logger.warning("Planner health check failed", model=self.model, error=str(e))
            return False

# Global planner driver instance
_planner_driver: Optional[PlannerQwenDriver] = None

def get_planner_driver() -> PlannerQwenDriver:
    """Get or create global planner driver instance"""
    global _planner_driver
    if _planner_driver is None:
        _planner_driver = PlannerQwenDriver()
    return _planner_driver
