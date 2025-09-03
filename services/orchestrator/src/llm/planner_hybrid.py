"""
Hybrid Planner - Routes EASY/MEDIUM to local model, HARD to OpenAI API
"""

import os
import time
import structlog
from typing import Dict, Any, Optional
from pathlib import Path
from datetime import datetime
import openai
from .planner_qwen import PlannerQwenDriver
from .planner_classifier import get_planner_classifier, ClassificationResult
from ..planner.schema import PlannerOutput

logger = structlog.get_logger(__name__)

class PlannerHybridDriver:
    """Hybrid planner with local model for EASY/MEDIUM, OpenAI for HARD"""
    
    def __init__(self):
        self.local_driver = PlannerQwenDriver()
        self.classifier = get_planner_classifier()
        
        # OpenAI configuration
        self.openai_client = None
        self.openai_model = os.getenv("OPENAI_PLANNER_MODEL", "gpt-4o-mini")
        self.openai_api_key = os.getenv("OPENAI_API_KEY")
        
        if self.openai_api_key:
            self.openai_client = openai.OpenAI(api_key=self.openai_api_key)
            logger.info("OpenAI client initialized", model=self.openai_model)
        else:
            logger.warning("OpenAI API key not found, HARD scenarios will use local model")
        
        # Complexity thresholds
        self.hard_threshold = 0.6  # Confidence threshold for HARD classification
        
        # Debug settings
        self.debug_dump = os.getenv("PLANNER_DEBUG_DUMP", "0") not in ("0", "", "false", "False")
        self.debug_dir = Path(os.getenv("PLANNER_DEBUG_DIR", "data/telemetry/planner_raw"))
        self.no_fallback = os.getenv("PLANNER_NO_FALLBACK", "0") not in ("0", "", "false", "False")
    
    def _classify_complexity(self, text: str) -> str:
        """Classify text complexity (EASY, MEDIUM, HARD)"""
        # Simple heuristics for complexity
        words = text.split()
        word_count = len(words)
        
        # Check for complex patterns
        complex_patterns = [
            r"om.*så.*annars",  # Conditional logic
            r"baserat på.*och.*",  # Context-heavy
            r"analysera.*och.*skapa",  # Multi-step
            r"prioritera.*baserat på",  # Complex reasoning
            r"utveckla.*strategi",  # Strategy development
            r"utvärdera.*risk",  # Risk assessment
            r"optimera.*med hänsyn till",  # Optimization
            r"sammanfatta.*och.*",  # Complex summarization
        ]
        
        import re
        complexity_score = 0
        
        # Word count factor
        if word_count > 20:
            complexity_score += 0.3
        elif word_count > 15:
            complexity_score += 0.2
        elif word_count > 10:
            complexity_score += 0.1
        
        # Pattern matching
        for pattern in complex_patterns:
            if re.search(pattern, text, re.IGNORECASE):
                complexity_score += 0.4
        
        # Determine complexity level
        if complexity_score >= self.hard_threshold:
            return "HARD"
        elif complexity_score >= 0.3:
            return "MEDIUM"
        else:
            return "EASY"
    
    def _call_openai(self, prompt: str) -> Dict[str, Any]:
        """Call OpenAI API for HARD scenarios"""
        if not self.openai_client:
            logger.warning("OpenAI client not available, falling back to local model")
            return self.local_driver.generate(prompt)
        
        try:
            start_time = time.perf_counter()
            
            response = self.openai_client.chat.completions.create(
                model=self.openai_model,
                messages=[
                    {
                        "role": "system",
                        "content": """Du är en tool-selector. Svara med EN enda rad JSON som följer exakt schemat.
Absolut inget annat (ingen text, ingen kodblock, inga nya rader).
Schema: {"version":1,"tool":"<enum>","reason":"<kort svensk motivering>"}
Tillåtna "tool": ["none","email.create_draft","calendar.create_draft","weather.lookup","memory.query"].
Vid tydliga e-post/mötesfraser ska verktyg väljas, 'none' bara vid oklarheter.
Svara alltid på svenska."""
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=0.0,
                max_tokens=64,
                response_format={"type": "json_object"}
            )
            
            generation_time = (time.perf_counter() - start_time) * 1000
            
            # Extract response
            response_text = response.choices[0].message.content
            
            # Parse JSON
            import json
            parsed_json = json.loads(response_text)
            
            # Validate with schema
            validated_output = PlannerOutput(**parsed_json)
            
            logger.info("OpenAI planner response generated", 
                       model=self.openai_model,
                       tool=validated_output.tool,
                       generation_time_ms=generation_time)
            
            return {
                "text": response_text,
                "model": f"openai:{self.openai_model}",
                "tokens_used": response.usage.total_tokens,
                "temperature": 0.0,
                "route": "planner",
                "json_parsed": True,
                "schema_ok": True,
                "tool": validated_output.tool,
                "reason": validated_output.reason,
                "generation_time_ms": generation_time,
                "total_time_ms": generation_time,
                "fallback_used": False,
                "fallback_reason": None,
                "circuit_open": False,
                "openai_used": True
            }
            
        except Exception as e:
            logger.error("OpenAI call failed", error=str(e))
            if self.no_fallback:
                raise
            return self.local_driver.generate(prompt)
    
    def generate(self, prompt: str, **kwargs) -> Dict[str, Any]:
        """Generate tool selection with hybrid routing"""
        start_time = time.perf_counter()
        
        try:
            # Classify complexity
            complexity = self._classify_complexity(prompt)
            logger.info("Planner complexity classification", 
                       complexity=complexity,
                       prompt_length=len(prompt))
            
            # Route based on complexity
            if complexity == "HARD" and self.openai_client:
                logger.info("Routing HARD scenario to OpenAI")
                result = self._call_openai(prompt)
                result["complexity"] = complexity
                result["total_time_ms"] = (time.perf_counter() - start_time) * 1000
                return result
            else:
                logger.info(f"Routing {complexity} scenario to local model")
                result = self.local_driver.generate(prompt, **kwargs)
                result["complexity"] = complexity
                result["total_time_ms"] = (time.perf_counter() - start_time) * 1000
                return result
                
        except Exception as e:
            logger.error("Hybrid planner generation failed", error=str(e))
            if self.no_fallback:
                raise
            return self.local_driver.generate(prompt, **kwargs)

# Global hybrid driver instance
_hybrid_driver: Optional[PlannerHybridDriver] = None

def get_hybrid_planner_driver() -> PlannerHybridDriver:
    """Get or create global hybrid planner driver instance"""
    global _hybrid_driver
    if _hybrid_driver is None:
        _hybrid_driver = PlannerHybridDriver()
    return _hybrid_driver
