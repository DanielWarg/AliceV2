"""
Planner LLM driver for Qwen-MoE - structured planning with JSON output.
"""

import os
import json
import time
import structlog
from typing import Dict, Any, Optional, List
from pydantic import BaseModel, ValidationError
from .ollama_client import get_ollama_client

logger = structlog.get_logger(__name__)

# Pydantic schema for planner output
class ToolStep(BaseModel):
    tool: str
    args: Dict[str, Any]
    reason: str

class PlannerOutput(BaseModel):
    plan: str
    steps: List[ToolStep]
    response: str

class PlannerQwenDriver:
    """Planner LLM driver using Qwen-MoE for structured tool planning"""
    
    def __init__(self):
        self.model = os.getenv("LLM_PLANNER", "phi3:latest")
        self.client = get_ollama_client()
        
        # Robust planner settings for structured planning
        self.temperature = 0.0  # Strict deterministic output for JSON
        self.max_tokens = 300   # Reduced for faster response
        self.top_p = 0.8       # Focused sampling for structured output
        
        # Timeout settings
        self.planner_timeout_ms = 600  # 600ms for planner generation
        self.repair_timeout_ms = 150   # 150ms for JSON repair
        
        # Circuit breaker settings
        self.max_failures = 5
        self.failure_window_s = 30
        self.failure_count = 0
        self.last_failure_time = 0
        
        # Swedish system prompt for planner with strict JSON output
        self.system_prompt = """Du är Alice, en AI-assistent som planerar och utför åtgärder.
Du ska svara ENDAST med JSON-format för att strukturera dina planer och verktygsanrop.

Tillgängliga verktyg:
- calendar.create: Skapa kalenderhändelser
- email.draft: Skapa e-postutkast
- weather.get: Hämta väderinformation
- time.get: Hämta aktuell tid

Svara ALLTID med exakt detta JSON-format:
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
}

VIKTIGT: 
- Svara ENDAST med JSON, inga extra text
- Använd exakt format ovan
- Avsluta med "}" och inget mer"""
    
    def generate(self, prompt: str, **kwargs) -> Dict[str, Any]:
        """Generate structured plan using Qwen-MoE with robust error handling"""
        start_time = time.perf_counter()
        
        try:
            # Check circuit breaker
            if self._is_circuit_open():
                logger.warning("Circuit breaker open, using fallback")
                return self._fallback_response("circuit_breaker_open")
            
            # Override with planner-specific settings
            planner_kwargs = {
                "temperature": kwargs.get("temperature", self.temperature),
                "max_tokens": kwargs.get("max_tokens", self.max_tokens),
                "top_p": kwargs.get("top_p", self.top_p),
                "system": kwargs.get("system", self.system_prompt),
                "format": "json",  # Enforce JSON mode in Ollama
                "stop": ["```", "Human:", "Assistant:"]  # Stop tokens
            }
            
            logger.info("Generating planner response", model=self.model, prompt_length=len(prompt))
            
            # Generate with timeout
            response = self.client.generate(
                model=self.model,
                prompt=prompt,
                request_timeout_ms=self.planner_timeout_ms,
                **planner_kwargs
            )
            
            generation_time = (time.perf_counter() - start_time) * 1000
            
            # Check timeout
            if generation_time > self.planner_timeout_ms:
                logger.warning("Planner generation timeout", 
                              generation_time_ms=generation_time,
                              timeout_ms=self.planner_timeout_ms)
                return self._fallback_response("planner_timeout")
            
            # Extract response text
            response_text = response.get("response", "").strip()
            
            # Try to parse JSON from response
            parsed_json = self._parse_json_response(response_text)
            repair_used = False
            
            if parsed_json is None:
                # Try JSON repair with timeout
                repair_start = time.perf_counter()
                parsed_json = self._repair_json_response(response_text)
                repair_time = (time.perf_counter() - repair_start) * 1000
                
                if parsed_json is None or repair_time > self.repair_timeout_ms:
                    logger.warning("JSON repair failed or timeout", 
                                  repair_time_ms=repair_time,
                                  repair_timeout_ms=self.repair_timeout_ms)
                    self._record_failure()
                    return self._fallback_response("json_parse_failed")
                else:
                    repair_used = True
            
            # Validate with Pydantic schema
            try:
                validated_plan = PlannerOutput(**parsed_json)
                schema_ok = True
            except ValidationError as e:
                logger.warning("Schema validation failed", validation_errors=str(e))
                self._record_failure()
                return self._fallback_response("schema_validation_failed")
            
            # Success - reset failure count
            self._reset_failure_count()
            
            total_time = (time.perf_counter() - start_time) * 1000
            
            logger.info("Planner response generated successfully", 
                       model=self.model, 
                       response_length=len(response_text),
                       tokens_used=response.get("eval_count", 0),
                       generation_time_ms=generation_time,
                       total_time_ms=total_time,
                       json_valid=True,
                       schema_ok=True)
            
            return {
                "text": response_text,
                "model": self.model,
                "tokens_used": response.get("eval_count", 0),
                "prompt_tokens": response.get("prompt_eval_count", 0),
                "response_tokens": response.get("eval_count", 0),
                "temperature": planner_kwargs["temperature"],
                "route": "planner",
                "json_parsed": True,
                "schema_ok": True,
                "plan": validated_plan.dict(),
                "generation_time_ms": generation_time,
                "total_time_ms": total_time,
                "fallback_used": False,
                "fallback_reason": None,
                "repair_used": repair_used,
                "circuit_open": False
            }
            
        except Exception as e:
            logger.error("Planner generation failed", model=self.model, error=str(e))
            self._record_failure()
            return self._fallback_response("exception")
    
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
    
    def _repair_json_response(self, response_text: str) -> Optional[Dict[str, Any]]:
        """Attempt to repair malformed JSON with quick fixes"""
        try:
            # Common JSON repair patterns
            repaired = response_text
            
            # Fix missing quotes around keys
            import re
            repaired = re.sub(r'(\w+):', r'"\1":', repaired)
            
            # Fix trailing commas
            repaired = re.sub(r',(\s*[}\]])', r'\1', repaired)
            
            # Try to parse repaired JSON
            return json.loads(repaired)
            
        except (json.JSONDecodeError, ValueError):
            return None
    
    def _fallback_response(self, reason: str) -> Dict[str, Any]:
        """Generate fallback response when planner fails"""
        return {
            "text": "Jag kunde inte planera denna åtgärd just nu. Kan jag hjälpa dig på ett annat sätt?",
            "model": "fallback",
            "tokens_used": 0,
            "prompt_tokens": 0,
            "response_tokens": 0,
            "temperature": 0.0,
            "route": "fallback",
            "json_parsed": False,
            "schema_ok": False,
            "plan": None,
            "generation_time_ms": 0,
            "total_time_ms": 0,
            "fallback_used": True,
            "fallback_reason": reason
        }
    
    def _record_failure(self):
        """Record a failure for circuit breaker"""
        current_time = time.time()
        
        # Reset if outside window
        if current_time - self.last_failure_time > self.failure_window_s:
            self.failure_count = 0
        
        self.failure_count += 1
        self.last_failure_time = current_time
        
        logger.warning("Planner failure recorded", 
                      failure_count=self.failure_count,
                      max_failures=self.max_failures)
    
    def _reset_failure_count(self):
        """Reset failure count on success"""
        self.failure_count = 0
    
    def _is_circuit_open(self) -> bool:
        """Check if circuit breaker is open"""
        return self.failure_count >= self.max_failures
    
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
