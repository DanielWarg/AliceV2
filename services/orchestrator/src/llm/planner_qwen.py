"""
Planner LLM driver using Qwen model with minimal tool-based schema.
"""

import json
import os
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

import structlog
from pydantic import ValidationError

from ..planner.schema import PlannerOutput
from .ollama_client import get_ollama_client
from .planner_classifier import get_planner_classifier

logger = structlog.get_logger(__name__)


class PlannerQwenDriver:
    """Planner driver using Qwen model with minimal tool selection"""

    def __init__(self):
        self.model = os.getenv("LLM_PLANNER", "llama3.2:1b-instruct-q4_K_M")
        self.client = get_ollama_client()
        self.classifier = get_planner_classifier()

        # Robust debug settings - can never crash
        self.debug_dump = os.getenv("PLANNER_DEBUG_DUMP", "0") not in (
            "0",
            "",
            "false",
            "False",
        )
        self.debug_dir = Path(
            os.getenv("PLANNER_DEBUG_DIR", "data/telemetry/planner_raw")
        )
        self.no_fallback = os.getenv("PLANNER_NO_FALLBACK", "0") not in (
            "0",
            "",
            "false",
            "False",
        )

        # Enhanced system prompt with few-shots and strict JSON enforcement
        self.system_prompt = """Du är en tool-selector. Svara med EN enda rad JSON som följer exakt schemat.
Absolut inget annat (ingen text, ingen kodblock, inga nya rader).
Schema: {"version":1,"tool":"<enum>","reason":"<kort svensk motivering>"}
Tillåtna "tool": ["none","email.create_draft","calendar.create_draft","weather.lookup","memory.query"].
Vid tydliga e-post/mötesfraser ska verktyg väljas, 'none' bara vid oklarheter.
Svara alltid på svenska.

Exempel:
Fråga: "Skicka email till Anna"
Svar: {"version":1,"tool":"email.create_draft","reason":"Skicka email till Anna"}

Fråga: "Boka möte imorgon kl 14:00"
Svar: {"version":1,"tool":"calendar.create_draft","reason":"Boka möte imorgon kl 14:00"}

Fråga: "Vad är vädret i Stockholm?"
Svar: {"version":1,"tool":"weather.lookup","reason":"Kolla vädret i Stockholm"}

Fråga: "Kommer du ihåg vad vi sa igår?"
Svar: {"version":1,"tool":"memory.query","reason":"Sök i minnet efter igår"}

Fråga: "Hej, hur mår du?"
Svar: {"version":1,"tool":"none","reason":"Enkel hälsning, inget verktyg behövs"}

Fråga: "Tack för hjälpen"
Svar: {"version":1,"tool":"none","reason":"Tack, inget verktyg behövs"}"""

        # Generation parameters optimized for strict JSON output
        self.generation_params = {
            "format": "json",
            "temperature": 0.0,  # Deterministic output
            "top_p": 0.1,  # Very focused sampling
            "mirostat": 0,
            "num_ctx": 1024,  # Reduced context for speed
            "num_predict": 64,  # Short responses
            "stream": False,
            "repeat_penalty": 1.05,  # Prevent repetition
            "stop": ["\n", "```", " Human:", " Assistant:"],  # Stop tokens
        }

        # Circuit breaker settings
        self.max_failures = 3
        self.failure_window_s = 60
        self.failure_count = 0
        self.last_failure_time = 0
        self.circuit_open = False
        self.circuit_open_time = 0
        self.cool_down_s = 30

    def _safe_dump(self, text: str) -> None:
        """Safe dump function that can never crash the flow"""
        if not getattr(self, "debug_dump", False):
            return
        try:
            self.debug_dir.mkdir(parents=True, exist_ok=True)
            p = self.debug_dir / f"{datetime.utcnow().isoformat()}Z.txt"
            p.write_text(text or "", encoding="utf-8")
            logger.info("planner.raw_dump", path=str(p), bytes=len(text or ""))
        except Exception as e:
            # Never throw - dump must never crash the flow
            logger.warning("planner.raw_dump_failed", err=str(e))

    def _post_process_json(self, text: str) -> str:
        """Post-process and repair JSON if needed"""
        if not text:
            return text

        # Trim whitespace and remove code block markers
        text = text.strip()
        text = text.replace("```json", "").replace("```", "")

        # Fix <enum> placeholders
        text = text.replace('"<enum>"', '"none"')
        text = text.replace("'<enum>'", '"none"')

        # Quick repair: balance braces and quotes if exactly one is missing
        if text.count("{") == text.count("}") - 1:
            text += "}"
        elif text.count("{") == text.count("}") + 1:
            text = "{" + text

        if text.count('"') % 2 == 1:
            text += '"'

        return text

    def generate(self, prompt: str, **kwargs) -> Dict[str, Any]:
        """Generate minimal tool selection using Qwen model with classifier pre-filter"""
        start_time = time.perf_counter()

        try:
            # Check circuit breaker
            if self._is_circuit_open():
                logger.warning("Circuit breaker open, using fallback")
                return self._fallback_response("circuit_breaker_open")

            # Pre-classify with regex patterns
            classification = self.classifier.classify(prompt)
            logger.info(
                "Planner classification",
                tool=classification.tool,
                confidence=classification.confidence,
                use_llm=classification.use_llm,
                reason=classification.reason,
            )

            # If high confidence classification, skip LLM
            if not classification.use_llm:
                logger.info("Using classifier result, skipping LLM")

                # Create schema v4 compatible output

                # Map tool to intent
                intent_map = {
                    "weather.lookup": "weather",
                    "calendar.create_draft": "calendar",
                    "email.create_draft": "email",
                    "memory.query": "memory",
                    "none": "greeting",
                }

                intent = intent_map.get(classification.tool, "greeting")
                tool = classification.tool if classification.tool != "none" else None

                # Create schema v4 output
                schema_v4_output = {
                    "intent": intent,
                    "tool": tool,
                    "args": {},
                    "render_instruction": "none",
                    "meta": {
                        "version": "4.0",
                        "model_id": "classifier_v2",
                        "schema_version": "v4",
                        "classifier_used": True,
                        "confidence": classification.confidence,
                    },
                }

                return {
                    "text": json.dumps(schema_v4_output, ensure_ascii=False),
                    "model": "classifier",
                    "tokens_used": 0,
                    "temperature": 0.0,
                    "route": "planner",
                    "json_parsed": True,
                    "schema_ok": True,
                    "tool": classification.tool,
                    "reason": classification.reason,
                    "generation_time_ms": 0,
                    "total_time_ms": (time.perf_counter() - start_time) * 1000,
                    "fallback_used": False,
                    "fallback_reason": None,
                    "circuit_open": False,
                    "classifier_used": True,
                }

            # Use generation parameters
            gen_params = {**self.generation_params, **kwargs}

            logger.info(
                "Generating planner response",
                model=self.model,
                prompt_length=len(prompt),
            )

            # Load GBNF grammar for strict JSON output
            grammar_path = Path(__file__).parent / "planner_grammar.gbnf"
            grammar = None
            if grammar_path.exists():
                grammar = grammar_path.read_text(encoding="utf-8")

            # Generate with timeout and grammar
            response = self.client.generate(
                model=self.model,
                prompt=prompt,
                system=self.system_prompt,
                request_timeout_ms=8000,  # 8s timeout
                grammar=grammar,  # Use GBNF grammar for strict output
                **gen_params,
            )

            # Extract response text safely
            resp_txt = ""
            try:
                resp_txt = (
                    response.get("response", "")
                    if isinstance(response, dict)
                    else str(response)
                )
            except Exception:
                # Last defense line
                resp_txt = str(response)

            # Post-process JSON response
            processed_text = self._post_process_json(resp_txt)

            # UNCONDITIONAL raw dump before parsing
            self._safe_dump(processed_text)

            generation_time = (time.perf_counter() - start_time) * 1000

            # Log raw response for debugging
            logger.info(
                "Raw planner response",
                response_text=processed_text[:500],  # First 500 chars
                response_length=len(processed_text),
            )

            # JSON parse with retry logic
            parsed_json = None
            parse_error = None

            for attempt in range(2):  # Try twice
                try:
                    parsed_json = json.loads(processed_text)
                    break
                except json.JSONDecodeError as e:
                    parse_error = e
                    if (
                        attempt == 0
                    ):  # First attempt failed, try one more time with same prompt
                        logger.warning(
                            "planner.json_decode_error_retry",
                            attempt=attempt,
                            pos=e.pos,
                            msg=str(e),
                            sample=(processed_text or "")[:200],
                        )
                        # Retry with same prompt (no changes)
                        continue
                    else:  # Second attempt also failed
                        logger.warning(
                            "planner.json_decode_error_final",
                            pos=e.pos,
                            lineno=getattr(e, "lineno", "unknown"),
                            colno=getattr(e, "colno", "unknown"),
                            msg=str(e),
                            sample=(processed_text or "")[:200],
                        )
                        if self.no_fallback:
                            # Force visible error in debug mode
                            raise
                        self._record_failure()
                        return self._fallback_response("json_decode_error")

            # Validate with minimal schema
            try:
                validated_output = PlannerOutput(**parsed_json)
                schema_ok = True
            except ValidationError as e:
                logger.warning(
                    "planner.schema_validation_failed", err=str(e), obj=parsed_json
                )
                if self.no_fallback:
                    raise
                self._record_failure()
                return self._fallback_response("schema_validation_failed")

            # Success - reset failure count
            self._reset_failure_count()

            total_time = (time.perf_counter() - start_time) * 1000

            logger.info(
                "Planner response generated successfully",
                model=self.model,
                tool=validated_output.tool,
                generation_time_ms=generation_time,
                total_time_ms=total_time,
                schema_ok=True,
            )

            return {
                "text": processed_text,
                "model": self.model,
                "tokens_used": response.get("eval_count", 0),
                "temperature": gen_params["temperature"],
                "route": "planner",
                "json_parsed": True,
                "schema_ok": True,
                "tool": validated_output.tool,
                "reason": validated_output.reason,
                "generation_time_ms": generation_time,
                "total_time_ms": total_time,
                "fallback_used": False,
                "fallback_reason": None,
                "circuit_open": False,
                "level": (
                    getattr(classification_result, "level", "medium")
                    if "classification_result" in locals()
                    else "medium"
                ),
            }

        except Exception as e:
            logger.error(
                "Planner generation failed",
                model=self.model,
                error=str(e),
                error_type=type(e).__name__,
            )
            if self.no_fallback:
                raise e
            self._record_failure()
            return self._fallback_response("exception")

    def _fallback_response(self, reason: str) -> Dict[str, Any]:
        """Generate fallback response when planner fails"""
        return {
            "text": "Jag kunde inte planera denna åtgärd just nu. Kan jag hjälpa dig på ett annat sätt?",
            "model": "planner_fallback",
            "tokens_used": 0,
            "temperature": 0.0,
            "route": "planner",
            "json_parsed": False,
            "schema_ok": False,
            "tool": "none",
            "reason": None,
            "generation_time_ms": 0,
            "total_time_ms": 0,
            "fallback_used": True,
            "fallback_reason": reason,
            "level": "medium",
        }

    def _record_failure(self):
        """Record a failure for circuit breaker"""
        current_time = time.time()

        # Reset if outside window
        if current_time - self.last_failure_time > self.failure_window_s:
            self.failure_count = 0

        self.failure_count += 1
        self.last_failure_time = current_time

        logger.warning(
            "Planner failure recorded",
            failure_count=self.failure_count,
            max_failures=self.max_failures,
        )

    def _reset_failure_count(self):
        """Reset failure count on success"""
        self.failure_count = 0

    def _is_circuit_open(self) -> bool:
        """Check if circuit breaker is open"""
        current_time = time.time()

        # Check if we should close the circuit
        if (
            self.circuit_open
            and (current_time - self.circuit_open_time) > self.cool_down_s
        ):
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
            logger.warning(
                "Planner health check failed", model=self.model, error=str(e)
            )
            return False


# Global planner driver instance
_planner_driver: Optional[PlannerQwenDriver] = None


def get_planner_driver() -> PlannerQwenDriver:
    """Get or create global planner driver instance"""
    global _planner_driver
    if _planner_driver is None:
        _planner_driver = PlannerQwenDriver()
    return _planner_driver
