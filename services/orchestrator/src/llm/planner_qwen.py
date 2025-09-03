"""
Planner LLM driver using Qwen model with minimal tool-based schema.
"""

import os
import json
import time
import structlog
from typing import Dict, Any, Optional
from pydantic import ValidationError
from .ollama_client import get_ollama_client
from ..planner.schema import PlannerOutput

logger = structlog.get_logger(__name__)

class PlannerQwenDriver:
    """Planner driver using Qwen model with minimal tool selection"""
    
    def __init__(self):
        self.model = os.getenv("LLM_PLANNER", "llama3.2:1b-instruct-q4_K_M")
        self.client = get_ollama_client()
        
        # Minimal system prompt for tool selection
        self.system_prompt = """Du är en planeringsmotor. Svara ENBART med giltig JSON, ingen text.
Schema: {"tool":"<enum>","args":{}}.
Tillåtna tool: ["calendar.create","email.draft","memory.query","none"].
Om du är osäker använd {"tool":"none","args":{}}."""
        
        # Generation parameters optimized for JSON output
        self.generation_params = {
            "format": "json",
            "temperature": 0.1,
            "top_p": 0.9,
            "num_ctx": 4096,
            "num_predict": 256,
            "stop": ["```", "Human:", "Assistant:", "\n\n"]
        }
        
        # Circuit breaker settings
        self.max_failures = 3
        self.failure_window_s = 60
        self.failure_count = 0
        self.last_failure_time = 0
        self.circuit_open = False
        self.circuit_open_time = 0
        self.cool_down_s = 30
    
    def generate(self, prompt: str, **kwargs) -> Dict[str, Any]:
        """Generate minimal tool selection using Qwen model"""
        start_time = time.perf_counter()
        
        try:
            # Check circuit breaker
            if self._is_circuit_open():
                logger.warning("Circuit breaker open, using fallback")
                return self._fallback_response("circuit_breaker_open")
            
            # Use generation parameters
            gen_params = {**self.generation_params, **kwargs}
            
            logger.info("Generating planner response", model=self.model, prompt_length=len(prompt))
            
            # Generate with timeout
            response = self.client.generate(
                model=self.model,
                prompt=prompt,
                system=self.system_prompt,
                request_timeout_ms=6000,  # 6s timeout
                **gen_params
            )
            
            generation_time = (time.perf_counter() - start_time) * 1000
            
            # Extract response text
            response_text = response.get("response", "").strip()
            
            # Log raw response for debugging
            logger.info("Raw planner response", 
                       response_text=response_text[:200],  # First 200 chars
                       response_length=len(response_text))
            
            # Try to parse JSON from response
            parsed_json = self._parse_json_response(response_text)
            repair_used = False
            
            if parsed_json is None:
                # Try JSON repair
                parsed_json = self._repair_json_response(response_text)
                if parsed_json is None:
                    logger.warning("JSON parse failed")
                    self._record_failure()
                    return self._fallback_response("json_parse_failed")
                else:
                    repair_used = True
            
            # Validate with minimal schema
            try:
                validated_output = PlannerOutput(**parsed_json)
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
                       tool=validated_output.tool,
                       generation_time_ms=generation_time,
                       total_time_ms=total_time,
                       schema_ok=True)
            
            return {
                "text": response_text,
                "model": self.model,
                "tokens_used": response.get("eval_count", 0),
                "temperature": gen_params["temperature"],
                "route": "planner",
                "json_parsed": True,
                "schema_ok": True,
                "tool": validated_output.tool,
                "args": validated_output.args,
                "generation_time_ms": generation_time,
                "total_time_ms": total_time,
                "fallback_used": False,
                "fallback_reason": None,
                "repair_used": repair_used,
                "circuit_open": False
            }
            
        except Exception as e:
            logger.error("Planner generation failed", model=self.model, error=str(e), error_type=type(e).__name__)
            self._record_failure()
            return self._fallback_response("exception")
    
    def _parse_json_response(self, response_text: str) -> Optional[Dict[str, Any]]:
        """Parse JSON from response text"""
        try:
            # Try to find JSON object in the text
            start = response_text.find("{")
            end = response_text.rfind("}") + 1
            if start >= 0 and end > start:
                json_text = response_text[start:end]
                return json.loads(json_text)
            return None
        except (json.JSONDecodeError, ValueError) as e:
            logger.warning("Failed to parse JSON from planner response", error=str(e))
            return None
    
    def _repair_json_response(self, response_text: str) -> Optional[Dict[str, Any]]:
        """Attempt to repair malformed JSON"""
        try:
            # Simple repair: strip to last complete JSON
            repaired = response_text
            if "}" in repaired:
                last_brace = repaired.rfind("}")
                repaired = repaired[:last_brace + 1]
            
            return json.loads(repaired)
        except (json.JSONDecodeError, ValueError):
            return None
    
    def _fallback_response(self, reason: str) -> Dict[str, Any]:
        """Generate fallback response when planner fails"""
        return {
            "text": "Jag kunde inte planera denna åtgärd just nu. Kan jag hjälpa dig på ett annat sätt?",
            "model": "fallback",
            "tokens_used": 0,
            "temperature": 0.0,
            "route": "fallback",
            "json_parsed": False,
            "schema_ok": False,
            "tool": "none",
            "args": {},
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
        current_time = time.time()
        
        # Check if we should close the circuit
        if self.circuit_open and (current_time - self.circuit_open_time) > self.cool_down_s:
            self.circuit_open = False
            self.failure_count = 0
            logger.info("Circuit breaker closed after cool-down")
        
        # Check if we should open the circuit
        if self.failure_count >= self.max_failures and not self.circuit_open:
            self.circuit_open = True
            self.circuit_open_time = current_time
            logger.warning("Circuit breaker opened", failure_count=self.failure_count)
        
        return self.circuit_open
    
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
