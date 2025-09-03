"""
Planner v2 - Enhanced version for shadow mode evaluation
"""

import os
import json
import time
import structlog
from typing import Dict, Any, Optional
from pydantic import ValidationError
from pathlib import Path
from datetime import datetime

from .ollama_client import get_ollama_client
from .planner_classifier import get_planner_classifier, ClassificationResult
from ..planner.schema_v4 import PlanOut, IntentType, ToolType

logger = structlog.get_logger(__name__)

class PlannerV2Driver:
    """Enhanced planner driver for shadow mode evaluation"""
    
    def __init__(self):
        self.model = os.getenv("LLM_PLANNER_V2", "llama3.2:1b-instruct-q4_K_M")
        self.client = get_ollama_client()
        self.classifier = get_planner_classifier()
        
        # Clean system prompt without placeholders
        self.system_prompt = """Du är en intelligent tool-selector som analyserar användarens intention och väljer det mest lämpliga verktyget.

Svara med EN enda rad JSON som följer exakt schemat:
{"intent":"email","tool":"email.create_draft","args":{},"render_instruction":"none","meta":{"version":"4.0","model_id":"planner_v2","schema_version":"v4"}}

Tillåtna intent: email, calendar, weather, memory, none
Tillåtna tool: email.create_draft, calendar.create_draft, weather.lookup, memory.query, none
Tillåtna render_instruction: chart, map, scene, none

Välj intent och tool baserat på:
- email: E-postrelaterade frågor (skicka, skriv, mail) → tool: email.create_draft
- calendar: Möten och schemaläggning (boka, möte, kalender) → tool: calendar.create_draft  
- weather: Väderfrågor (vädret, temperatur, regn) → tool: weather.lookup
- memory: Minnesfrågor (kommer du ihåg, vad sa vi) → tool: memory.query
- none: Allmänna frågor utan tydlig åtgärd → tool: none

Exempel:
"Skicka email till Anna" → {"intent":"email","tool":"email.create_draft","args":{},"render_instruction":"none","meta":{"version":"4.0","model_id":"planner_v2","schema_version":"v4"}}
"Boka möte imorgon kl 14:00" → {"intent":"calendar","tool":"calendar.create_draft","args":{},"render_instruction":"none","meta":{"version":"4.0","model_id":"planner_v2","schema_version":"v4"}}
"Vad är vädret i Stockholm?" → {"intent":"weather","tool":"weather.lookup","args":{},"render_instruction":"none","meta":{"version":"4.0","model_id":"planner_v2","schema_version":"v4"}}
"Kommer du ihåg vad vi sa igår?" → {"intent":"memory","tool":"memory.query","args":{},"render_instruction":"none","meta":{"version":"4.0","model_id":"planner_v2","schema_version":"v4"}}
"Hej, hur mår du?" → {"intent":"none","tool":"none","args":{},"render_instruction":"none","meta":{"version":"4.0","model_id":"planner_v2","schema_version":"v4"}}

VIKTIGT: Använd ENDAST giltiga enum-värden från listan ovan. Inga placeholders, inga vinkelparenteser, inga code fences.
Analysera noggrant och välj det mest lämpliga intent och tool. Svara ENDAST med JSON."""
        
        # Generation parameters for strict enum decoding
        self.generation_params = {
            "temperature": 0.1,  # Slightly higher for better reasoning
            "top_p": 0.3,        # Focused sampling
            "mirostat": 0,
            "num_ctx": 1024,
            "num_predict": 128,  # Sufficient for JSON
            "stream": False,
            "repeat_penalty": 1.1,
            "top_k": 1  # Only most likely token
        }
        
    def generate(self, prompt: str, **kwargs) -> Dict[str, Any]:
        """Generate tool selection using enhanced v2 model"""
        start_time = time.perf_counter()
        
        try:
            # Pre-classify with regex patterns
            classification = self.classifier.classify(prompt)
            logger.info("Planner v2 classification", 
                       tool=classification.tool,
                       confidence=classification.confidence,
                       use_llm=classification.use_llm,
                       reason=classification.reason)
            
            # If high confidence classification, skip LLM
            if not classification.use_llm:
                logger.info("Using classifier result for v2, skipping LLM")
                # Convert classifier result to v4 format with canonicalized args
                v4_result = {
                    "intent": classification.tool.split('.')[0] if '.' in classification.tool else "none",
                    "tool": classification.tool,
                    "args": PlanOut.canonicalize_args(classification.tool, {}),
                    "render_instruction": "none",
                    "meta": {
                        "version": "4.0",
                        "model_id": "classifier_v2",
                        "schema_version": "v4"
                    }
                }
                
                return {
                    "text": json.dumps(v4_result, separators=(',', ':'), ensure_ascii=False),
                    "model": "classifier_v2",
                    "tokens_used": 0,
                    "temperature": 0.0,
                    "route": "planner_v2",
                    "json_parsed": True,
                    "schema_ok": True,
                    "tool": classification.tool,
                    "intent": v4_result["intent"],
                    "generation_time_ms": 0,
                    "total_time_ms": (time.perf_counter() - start_time) * 1000,
                    "fallback_used": False,
                    "fallback_reason": None,
                    "circuit_open": False,
                    "classifier_used": True,
                    "version": "v2"
                }
            
            # Use generation parameters
            gen_params = {**self.generation_params, **kwargs}
            
            logger.info("Generating planner v2 response", model=self.model, prompt_length=len(prompt))
            
            # Load GBNF grammar for v4 schema
            grammar_path = Path(__file__).parent / "planner_grammar_v4.gbnf"
            grammar = None
            if grammar_path.exists():
                grammar = grammar_path.read_text(encoding="utf-8")
            
            # Generate with timeout and grammar
            response = self.client.generate(
                model=self.model,
                prompt=prompt,
                system=self.system_prompt,
                request_timeout_ms=8000,
                grammar=grammar,
                **gen_params
            )
            
            # Extract response text safely
            resp_txt = ""
            try:
                resp_txt = response.get("response", "") if isinstance(response, dict) else str(response)
            except Exception:
                resp_txt = str(response)
            
            # Post-process JSON response
            processed_text = self._post_process_json(resp_txt)
            
            generation_time = (time.perf_counter() - start_time) * 1000
            
            # Log raw response for debugging
            logger.info("Raw planner v2 response", 
                       response_text=processed_text[:500],
                       response_length=len(processed_text))
            
            # JSON parse with strict validation and auto-repair
            parsed_json = None
            parse_error = None
            auto_repaired = False
            
            for attempt in range(2):
                try:
                    parsed_json = json.loads(processed_text)
                    break
                except json.JSONDecodeError as e:
                    parse_error = e
                    if attempt == 0 and not auto_repaired:
                        # Auto-repair: remove trailing text after last }
                        last_brace = processed_text.rfind('}')
                        if last_brace > 0:
                            processed_text = processed_text[:last_brace + 1]
                            auto_repaired = True
                            logger.warning("planner_v2.auto_repair_applied", 
                                          pos=e.pos, 
                                          msg=str(e),
                                          sample=(processed_text or "")[:200])
                            continue
                    
                    logger.warning("planner_v2.json_decode_error_final", 
                                  pos=e.pos, 
                                  msg=str(e),
                                  sample=(processed_text or "")[:200])
                    return self._fallback_response("json_decode_error")
            
            # Validate with strict v4 schema and auto-repair
            try:
                # Canonicalize args before validation
                if "tool" in parsed_json and "args" in parsed_json:
                    parsed_json["args"] = PlanOut.canonicalize_args(parsed_json["tool"], parsed_json["args"])
                
                validated_output = PlanOut(**parsed_json)
                schema_ok = True
                
                # Convert to compact JSON without whitespace
                processed_text = json.dumps(validated_output.model_dump(), separators=(',', ':'), ensure_ascii=False)
                
            except ValidationError as e:
                logger.warning("planner_v2.schema_validation_failed", err=str(e), obj=parsed_json)
                
                # Auto-repair: fix enum values and canonicalize
                repaired_json = self._repair_enum_values(parsed_json)
                if "tool" in repaired_json and "args" in repaired_json:
                    repaired_json["args"] = PlanOut.canonicalize_args(repaired_json["tool"], repaired_json["args"])
                
                try:
                    validated_output = PlanOut(**repaired_json)
                    schema_ok = True
                    processed_text = json.dumps(validated_output.model_dump(), separators=(',', ':'), ensure_ascii=False)
                    logger.info("planner_v2.auto_repair_successful", repaired_json=repaired_json)
                except ValidationError as repair_error:
                    logger.warning("planner_v2.auto_repair_failed", err=str(repair_error), obj=repaired_json)
                    return self._fallback_response("schema_validation_failed")
            
            total_time = (time.perf_counter() - start_time) * 1000
            
            logger.info("Planner v2 response generated successfully", 
                       model=self.model, 
                       tool=validated_output.tool,
                       generation_time_ms=generation_time,
                       total_time_ms=total_time,
                       schema_ok=True)
            
            return {
                "text": processed_text,
                "model": self.model,
                "tokens_used": response.get("eval_count", 0),
                "temperature": gen_params["temperature"],
                "route": "planner_v2",
                "json_parsed": True,
                "schema_ok": True,
                "tool": validated_output.tool,
                "intent": validated_output.intent,
                "generation_time_ms": generation_time,
                "total_time_ms": total_time,
                "fallback_used": False,
                "fallback_reason": None,
                "circuit_open": False,
                "version": "v2",
                "level": classification_result.level if classification_result else "medium"
            }
            
        except Exception as e:
            logger.error("Planner v2 generation failed", model=self.model, error=str(e), error_type=type(e).__name__)
            return self._fallback_response("exception")
    
    def _post_process_json(self, text: str) -> str:
        """Post-process and repair JSON if needed"""
        if not text:
            return text
        
        # Trim whitespace and remove code block markers
        text = text.strip()
        text = text.replace("```json", "").replace("```", "")
        
        # Fix <enum> placeholders with default values
        text = text.replace('"<enum>"', '"none"')
        
        # Quick repair: balance braces and quotes if exactly one is missing
        if text.count("{") == text.count("}") - 1:
            text += "}"
        elif text.count("{") == text.count("}") + 1:
            text = "{" + text
        
        if text.count('"') % 2 == 1:
            text += '"'
        
        return text
    
    def _repair_enum_values(self, parsed_json: Dict[str, Any]) -> Dict[str, Any]:
        """Repair enum values deterministically"""
        repaired = parsed_json.copy()
        
        # Fix intent field
        intent = repaired.get("intent", "")
        if isinstance(intent, str):
            if "<" in intent or ">" in intent or intent == "<enum>":
                repaired["intent"] = "none"
            elif intent in ["create_calendar_draft", "calendar_draft", "cal"]:
                repaired["intent"] = "calendar"
            elif intent in ["create_email_draft", "email_draft", "mail"]:
                repaired["intent"] = "email"
            elif intent in ["weather_check", "weather_lookup", "temp"]:
                repaired["intent"] = "weather"
            elif intent in ["memory_check", "memory_lookup", "remember"]:
                repaired["intent"] = "memory"
            elif intent not in ["email", "calendar", "weather", "memory", "none"]:
                repaired["intent"] = "none"
        
        # Fix tool field
        tool = repaired.get("tool", "")
        if isinstance(tool, str):
            if "<" in tool or ">" in tool or tool == "<enum>":
                repaired["tool"] = "none"
            elif tool in ["create_calendar_draft", "calendar_draft", "cal"]:
                repaired["tool"] = "calendar.create_draft"
            elif tool in ["create_email_draft", "email_draft", "mail"]:
                repaired["tool"] = "email.create_draft"
            elif tool in ["weather_check", "weather_lookup", "temp"]:
                repaired["tool"] = "weather.lookup"
            elif tool in ["memory_check", "memory_lookup", "remember"]:
                repaired["tool"] = "memory.query"
            elif tool not in ["email.create_draft", "calendar.create_draft", "weather.lookup", "memory.query", "none"]:
                repaired["tool"] = "none"
        
        # Fix render_instruction field
        render_instruction = repaired.get("render_instruction", "")
        if isinstance(render_instruction, str):
            if "<" in render_instruction or ">" in render_instruction or render_instruction == "<enum>":
                repaired["render_instruction"] = "none"
            elif render_instruction not in ["chart", "map", "scene", "none"]:
                repaired["render_instruction"] = "none"
        
        # Ensure args is a dict
        if not isinstance(repaired.get("args"), dict):
            repaired["args"] = {}
        
        # Ensure meta has required fields
        meta = repaired.get("meta", {})
        if not isinstance(meta, dict):
            meta = {}
        meta["version"] = "4.0"
        meta["model_id"] = "planner_v2"
        meta["schema_version"] = "v4"
        repaired["meta"] = meta
        
        return repaired
    
    def _fallback_response(self, reason: str) -> Dict[str, Any]:
        """Generate fallback response when planner v2 fails"""
        fallback_json = {
            "intent": "none",
            "tool": "none",
            "args": {},
            "render_instruction": "none",
            "meta": {
                "version": "4.0",
                "model_id": "fallback_v2",
                "schema_version": "v4"
            }
        }
        
        return {
            "text": json.dumps(fallback_json, separators=(',', ':'), ensure_ascii=False),
            "model": "fallback_v2",
            "tokens_used": 0,
            "temperature": 0.0,
            "route": "planner_v2",
            "json_parsed": True,
            "schema_ok": True,
            "tool": "none",
            "intent": "none",
            "generation_time_ms": 0,
            "total_time_ms": 0,
            "fallback_used": True,
            "fallback_reason": reason,
            "circuit_open": False,
            "version": "v2",
            "level": "medium"
        }

def get_planner_v2_driver():
    """Factory function for planner v2 driver"""
    return PlannerV2Driver()
