"""
Hybrid Planner Implementation
Routes EASY/MEDIUM scenarios to local model, HARD to OpenAI API
"""

import os
import re
import time
from typing import Dict, Any, Optional
import structlog
from .planner_qwen import PlannerQwenDriver
from .planner_classifier import PlannerClassifier

logger = structlog.get_logger()

class PlannerHybridDriver:
    """Hybrid planner that routes based on complexity"""
    
    def __init__(self):
        self.local_driver = PlannerQwenDriver()
        self.classifier = PlannerClassifier()
        
        # OpenAI client
        self.openai_client = None
        self.openai_model = os.getenv("OPENAI_PLANNER_MODEL", "gpt-4o-mini")
        
        # Initialize OpenAI if API key is available
        api_key = os.getenv("OPENAI_API_KEY")
        if api_key:
            try:
                import openai
                self.openai_client = openai.OpenAI(api_key=api_key)
                logger.info("OpenAI client initialized", model=self.openai_model)
            except ImportError:
                logger.warning("OpenAI package not installed, falling back to local only")
        else:
            logger.warning("No OpenAI API key found, using local model only")
        
        # Complexity thresholds
        self.hard_threshold = 0.6
        self.medium_threshold = 0.3
    
    def _classify_complexity(self, text: str) -> str:
        """Classify text complexity (EASY, MEDIUM, HARD) using advanced heuristics"""
        words = text.split()
        word_count = len(words)
        
        hard_patterns = [
            r"analysera.*och.*föreslå",  # Analysis + recommendation
            r"utvärdera.*alternativ",  # Evaluate alternatives
            r"prioritera.*baserat på",  # Priority-based reasoning
            r"utveckla.*strategi",  # Strategy development
            r"optimera.*med hänsyn till",  # Optimization with constraints
            r"sammanfatta.*och.*",  # Complex summarization
            r"jämför.*och.*",  # Comparison and analysis
            r"planera.*schematiskt",  # Systematic planning
            r"koordinera.*mellan",  # Coordination tasks
            r"beräkna.*effektivitet",  # Efficiency calculations
        ]
        
        medium_patterns = [
            r"skapa.*för",  # Create for specific purpose
            r"hitta.*information",  # Information retrieval
            r"organisera.*",  # Organization tasks
            r"schemalägg.*",  # Scheduling
            r"sammanfatta.*",  # Simple summarization
            r"kontrollera.*",  # Verification tasks
        ]
        
        complexity_score = 0
        
        if word_count > 25:
            complexity_score += 0.4
        elif word_count > 20:
            complexity_score += 0.3
        elif word_count > 15:
            complexity_score += 0.2
        elif word_count > 10:
            complexity_score += 0.1
        
        for pattern in hard_patterns:
            if re.search(pattern, text, re.IGNORECASE):
                complexity_score += 0.5
                break
        
        for pattern in medium_patterns:
            if re.search(pattern, text, re.IGNORECASE):
                complexity_score += 0.2
        
        if re.search(r"om.*så.*annars", text, re.IGNORECASE):
            complexity_score += 0.3
        
        if re.search(r"baserat på.*och.*", text, re.IGNORECASE):
            complexity_score += 0.3
        
        if complexity_score >= self.hard_threshold:
            return "HARD"
        elif complexity_score >= self.medium_threshold:
            return "MEDIUM"
        else:
            return "EASY"
    
    def _call_openai(self, prompt: str) -> Dict[str, Any]:
        """Call OpenAI API for HARD scenarios"""
        if not self.openai_client:
            raise Exception("OpenAI client not available")
        
        start_time = time.time()
        
        try:
            response = self.openai_client.chat.completions.create(
                model=self.openai_model,
                messages=[
                    {"role": "system", "content": self.local_driver.system_prompt},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.0,
                max_tokens=150,
                response_format={"type": "json_object"}
            )
            
            generation_time = (time.time() - start_time) * 1000
            
            # Parse response
            content = response.choices[0].message.content
            try:
                import json
                result = json.loads(content)
                # Convert OpenAI response to local driver format
                result = {
                    "text": json.dumps(result),  # Convert back to JSON string
                    "model": f"openai:{self.openai_model}",
                    "tokens_used": response.usage.total_tokens if hasattr(response, 'usage') else 0,
                    "temperature": 0.0,
                    "route": "planner",
                    "json_parsed": True,
                    "schema_ok": True,
                    "tool": result.get("tool", "none"),
                    "reason": result.get("reason", ""),
                    "generation_time_ms": generation_time,
                    "total_time_ms": generation_time,
                    "fallback_used": False,
                    "fallback_reason": None,
                    "circuit_open": False,
                    "openai_used": True,
                    "complexity": "HARD"
                }
                
                logger.info(
                    "OpenAI planner response generated",
                    model=self.openai_model,
                    generation_time_ms=generation_time,
                    tool=result.get("tool", "unknown")
                )
                
                return result
                
            except json.JSONDecodeError:
                logger.error("Failed to parse OpenAI JSON response", content=content)
                raise
                
        except Exception as e:
            logger.error("OpenAI API call failed", error=str(e))
            raise
    
    def generate(self, prompt: str) -> Dict[str, Any]:
        """Generate planner response using hybrid routing"""
        start_time = time.time()
        
        # Classify complexity
        complexity = self._classify_complexity(prompt)
        logger.info(
            "Planner complexity classification",
            complexity=complexity,
            prompt_length=len(prompt)
        )
        
        try:
            if complexity == "HARD" and self.openai_client:
                logger.info("Routing HARD scenario to OpenAI")
                result = self._call_openai(prompt)
            else:
                # Use local model for EASY/MEDIUM or if OpenAI not available
                logger.info(f"Routing {complexity} scenario to local model")
                result = self.local_driver.generate(prompt)
                result["complexity"] = complexity
                result["openai_used"] = False
            
            # Add timing info
            total_time = (time.time() - start_time) * 1000
            result["total_time_ms"] = total_time
            
            return result
            
        except Exception as e:
            logger.error("Hybrid planner failed, falling back to local", error=str(e))
            # Fallback to local
            result = self.local_driver.generate(prompt)
            result["complexity"] = complexity
            result["openai_used"] = False
            result["fallback_reason"] = str(e)
            return result


def get_hybrid_planner_driver() -> PlannerHybridDriver:
    """Factory function for hybrid planner driver"""
    return PlannerHybridDriver()
