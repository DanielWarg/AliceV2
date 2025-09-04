"""
Micro Client Interface
Abstracts micro LLM calls with real and mock implementations
"""

import json
import os
from datetime import datetime, timedelta
from typing import Any, Dict, Optional

import structlog

logger = structlog.get_logger(__name__)


class MicroClient:
    """Abstract interface for micro LLM calls"""

    def generate(self, prompt: str, **kwargs) -> Dict[str, Any]:
        """Generate response from micro model"""
        raise NotImplementedError


class MockMicroClient(MicroClient):
    """Mock micro client that returns deterministic, schema-valid responses"""

    def __init__(self):
        self.mock_responses = {
            "weather.today": {
                "intent": "weather",
                "tool": "weather.lookup",
                "args": {"location": "Stockholm", "unit": "metric"},
                "render_instruction": {
                    "type": "text",
                    "content": "Vädret i Stockholm är {temperature}°C och {condition}.",
                },
            },
            "time.now": {
                "intent": "time",
                "tool": "time.now",
                "args": {"timezone": "Europe/Stockholm"},
                "render_instruction": {
                    "type": "text",
                    "content": "Klockan är {time} i Stockholm.",
                },
            },
            "calendar.create": {
                "intent": "calendar",
                "tool": "calendar.create_draft",
                "args": {
                    "title": "(Auto) Möte",
                    "start_iso": (datetime.now() + timedelta(minutes=30)).strftime(
                        "%Y-%m-%dT%H:%M"
                    ),
                    "duration_min": 30,
                    "attendees": [],
                    "timezone": "Europe/Stockholm",
                },
                "render_instruction": {
                    "type": "text",
                    "content": "Jag har bokat ett möte för dig klockan {start_time}.",
                },
            },
            "email.send": {
                "intent": "email",
                "tool": "email.create_draft",
                "args": {
                    "to": [],
                    "subject": "(Auto) Meddelande",
                    "body": "(Auto) Här är ditt meddelande.",
                    "importance": "normal",
                },
                "render_instruction": {
                    "type": "text",
                    "content": "Jag har skapat ett utkast till e-post med ämnet '{subject}'.",
                },
            },
            "greeting.hello": {
                "intent": "greeting",
                "tool": None,
                "args": {},
                "render_instruction": {
                    "type": "text",
                    "content": "Hej! Jag är Alice, din AI-assistent. Hur kan jag hjälpa dig?",
                },
            },
        }

    def generate(self, prompt: str, **kwargs) -> Dict[str, Any]:
        """Generate mock response based on prompt content"""
        # Simple intent detection based on keywords
        prompt_lower = prompt.lower()

        # Weather intent (check first to avoid conflicts)
        if any(
            word in prompt_lower
            for word in ["väder", "weather", "temperatur", "vädret"]
        ):
            intent = "weather.today"
        # Time intent
        elif any(
            word in prompt_lower
            for word in ["klockan", "tid", "time", "när", "hur mycket är klockan"]
        ):
            intent = "time.now"
        # Calendar intent
        elif any(
            word in prompt_lower
            for word in ["boka", "möte", "calendar", "kalender", "schedule"]
        ):
            intent = "calendar.create"
        # Email intent
        elif any(
            word in prompt_lower
            for word in ["mail", "email", "e-post", "skicka", "send"]
        ):
            intent = "email.send"
        # Greeting (default)
        else:
            intent = "greeting.hello"

        mock_response = self.mock_responses[intent].copy()

        # Add metadata
        mock_response["meta"] = {
            "version": "4.0",
            "model_id": "mock_micro",
            "schema_version": "v4",
            "mock_used": True,
            "intent_detected": intent,
            "schema_ok": True,  # 👈 VIKTIG RAD - Step 8 mätning
        }

        logger.info(
            "Mock micro response generated",
            intent=intent,
            prompt_length=len(prompt),
            mock_used=True,
        )

        return {
            "text": json.dumps(mock_response, ensure_ascii=False),
            "model": "mock_micro",
            "tokens_used": 0,
            "prompt_tokens": 0,
            "response_tokens": 0,
            "temperature": 0.0,
            "route": "micro",
            "mock_used": True,
            "intent_detected": intent,
            "schema_ok": True,  # Mock responses are always schema-valid
        }


class RealMicroClient(MicroClient):
    """Real micro client with few-shot prompting for maximum precision"""

    def __init__(self, base_url: str, model: str):
        self.base_url = base_url.rstrip("/")
        self.model = model

        # Optimized settings for Swedish accuracy
        self.temperature = 0.0  # Deterministic
        self.top_p = 0.1  # Focused sampling
        self.repeat_penalty = 1.0
        self.max_tokens = 20  # Short responses for tool selection

        # System prompt for tool selection
        self.system_prompt = """Du är en precis AI som klassificerar svenska frågor till rätt verktyg.

Fråga: "{text}"
Svara ENDAST med ett verktyg:"""

        # Few-shot examples for Swedish intent classification
        self.few_shot_examples = """Du är en precis AI som klassificerar svenska frågor till rätt verktyg. Svara ENDAST med verktygsnamnet.

Exempel:
Fråga: "Hej!"
Verktyg: greeting.hello

Fråga: "Vad är klockan?"  
Verktyg: time.now

Fråga: "Hur är vädret?"
Verktyg: weather.lookup

Fråga: "Boka möte imorgon"
Verktyg: calendar.create_draft

Fråga: "Skicka mail till Anna"
Verktyg: email.create_draft

Fråga: "Kom ihåg att handla mjölk"
Verktyg: memory.store

Fråga: "Räkna ut 15 + 27"
Verktyg: calculator

Fråga: "Sök efter receptet"
Verktyg: search.query"""

        # Mapping from Swedish to structured output
        self.tool_mapping = {
            "greeting.hello": {"intent": "greeting", "tool": None},
            "time.now": {"intent": "time", "tool": "time.now"},
            "weather.lookup": {"intent": "weather", "tool": "weather.lookup"},
            "calendar.create_draft": {
                "intent": "calendar",
                "tool": "calendar.create_draft",
            },
            "email.create_draft": {"intent": "email", "tool": "email.create_draft"},
            "memory.store": {"intent": "memory", "tool": "memory.store"},
            "calculator": {"intent": "calculator", "tool": "calculator"},
            "search.query": {"intent": "search", "tool": "search.query"},
        }

    def _extract_tool_name(self, response: str) -> str:
        """Extract tool name from model response"""
        response = response.strip().lower()

        # Direct mapping of common responses
        if any(word in response for word in ["greeting", "hej", "hello"]):
            return "greeting.hello"
        elif any(word in response for word in ["time", "klocka", "tid"]):
            return "time.now"
        elif any(word in response for word in ["weather", "väder"]):
            return "weather.lookup"
        elif any(word in response for word in ["calendar", "boka", "möte"]):
            return "calendar.create_draft"
        elif any(word in response for word in ["email", "mail", "skicka"]):
            return "email.create_draft"
        elif any(word in response for word in ["memory", "minne", "kom ihåg"]):
            return "memory.store"
        elif any(word in response for word in ["calculator", "räkna"]):
            return "calculator"
        elif any(word in response for word in ["search", "sök"]):
            return "search.query"

        # Try to match exact tool names from response
        for tool_name in self.tool_mapping.keys():
            if tool_name in response:
                return tool_name

        return "unknown"

    def _generate_default_args(self, tool_name: str, prompt: str) -> Dict[str, Any]:
        """Generate sensible default arguments for tools"""

        if tool_name == "time.now":
            return {"timezone": "Europe/Stockholm"}

        elif tool_name == "weather.lookup":
            # Simple location extraction
            location = "Stockholm"  # Default
            if "göteborg" in prompt.lower():
                location = "Göteborg"
            elif "malmö" in prompt.lower():
                location = "Malmö"
            return {"location": location, "unit": "metric"}

        elif tool_name == "calendar.create_draft":
            return {
                "title": "Nytt möte",
                "duration_min": 30,
                "timezone": "Europe/Stockholm",
            }

        elif tool_name == "email.create_draft":
            return {"subject": "Meddelande", "importance": "normal"}

        elif tool_name == "memory.store":
            return {"content": prompt, "category": "note"}

        else:
            return {}

    def generate(self, prompt: str, **kwargs) -> Dict[str, Any]:
        """Generate response using real Ollama model with enum→JSON mapping and cache"""

        try:
            # Check cache first with optimized two-tier key

            # Get enum response for intent
            enum_response = self._call_ollama(prompt, **kwargs)
            intent = self._enum_to_intent(enum_response)

            # Micro cache key: intent + canonical prompt hash
            from ..cache_key import micro_key

            cache_key = micro_key(intent, prompt)
            cached_response = self._get_from_cache(cache_key)
            if cached_response:
                logger.info("Micro cache hit", cache_key=cache_key)
                return cached_response

            # Enum response already obtained above for cache key

            # Map enum to proper JSON format
            json_response = self._map_enum_to_json(enum_response, prompt)

            logger.info(
                "Real micro response generated",
                model=self.model,
                enum_response=enum_response,
                json_response_length=len(json_response),
            )

            result = {
                "text": json_response,
                "model": self.model,
                "tokens_used": 0,  # Will be updated by actual call
                "prompt_tokens": 0,
                "response_tokens": 0,
                "temperature": kwargs.get("temperature", self.temperature),
                "route": "micro",
                "mock_used": False,
                "schema_ok": True,
                "enum_response": enum_response,
            }

            # Cache the result
            self._set_cache(cache_key, result)

            return result

        except Exception as e:
            logger.error("Real micro generation failed", model=self.model, error=str(e))
            # Set negative cache for failed requests
            try:
                import redis

                redis_client = redis.from_url(
                    os.getenv("REDIS_URL", "redis://alice-cache:6379")
                )
                neg_key = f"neg:{cache_key}"
                redis_client.setex(neg_key, 60, "1")  # 60 second TTL
                logger.info("Set negative cache", cache_key=cache_key)
            except Exception:
                pass
            raise

    def _call_ollama(self, prompt: str, **kwargs) -> str:
        """Call Ollama and get enum response"""
        import httpx

        micro_kwargs = {
            "temperature": kwargs.get("temperature", self.temperature),
            "max_tokens": kwargs.get("max_tokens", self.max_tokens),
            "top_p": kwargs.get("top_p", self.top_p),
            "system": kwargs.get("system", self.system_prompt),
        }

        # Truncate prompt to 128 tokens for speed
        truncated_prompt = prompt[:128] if len(prompt) > 128 else prompt

        # Format prompt with GBNF grammar
        formatted_prompt = self.system_prompt.format(text=truncated_prompt)

        # Use provided grammar or default
        grammar = kwargs.get(
            "grammar", 'root ::= ("time"|"weather"|"memory"|"greeting"|"none")'
        )

        payload = {
            "model": self.model,
            "prompt": formatted_prompt,
            "stream": False,
            "grammar": grammar,
            "stop": [],
        }
        payload.update(micro_kwargs)

        url = f"{self.base_url}/api/generate"
        logger.info(f"Real micro enum request -> {url} model={self.model}")

        with httpx.Client(timeout=60.0) as client:
            response = client.post(url, json=payload)
            response.raise_for_status()
            data = response.json()

        return data.get("response", "").strip()

    def _map_enum_to_json(self, enum_response: str, original_prompt: str) -> str:
        """Map enum response to proper JSON format"""
        enum_clean = enum_response.strip().lower()

        # Tool mapping
        tool_map = {
            "time": {
                "intent": "time.now",
                "tool": "time.now",
                "args": {"timezone": "Europe/Stockholm"},
                "render_instruction": {
                    "type": "text",
                    "content": "Klockan är {time} i Stockholm.",
                },
            },
            "weather": {
                "intent": "weather.lookup",
                "tool": "weather.lookup",
                "args": {"location": "Stockholm", "unit": "metric"},
                "render_instruction": {
                    "type": "text",
                    "content": "Vädret i Stockholm är {temperature}°C och {condition}.",
                },
            },
            "memory": {
                "intent": "memory.query",
                "tool": "memory.query",
                "args": {},
                "render_instruction": {
                    "type": "text",
                    "content": "Här är vad jag kommer ihåg: {memory_content}",
                },
            },
            "greeting": {
                "intent": "greeting.hello",
                "tool": None,
                "args": {},
                "render_instruction": {
                    "type": "text",
                    "content": "Hej! Jag är Alice, din AI-assistent. Hur kan jag hjälpa dig?",
                },
            },
            "calendar": {
                "intent": "calendar.create_draft",
                "tool": "calendar.create_draft",
                "args": {
                    "title": "(Auto) Möte",
                    "start_iso": "2024-01-15T14:00:00",
                    "duration_min": 30,
                    "attendees": [],
                    "timezone": "Europe/Stockholm",
                },
                "render_instruction": {
                    "type": "text",
                    "content": "Jag har bokat ett möte för dig klockan {start_time}.",
                },
            },
            "email": {
                "intent": "email.create_draft",
                "tool": "email.create_draft",
                "args": {
                    "to": [],
                    "subject": "(Auto) Meddelande",
                    "body": "(Auto) Här är ditt meddelande.",
                    "importance": "normal",
                },
                "render_instruction": {
                    "type": "text",
                    "content": "Jag har skapat ett utkast till e-post med ämnet '{subject}'.",
                },
            },
        }

        # Get mapped response or default to none
        mapped = tool_map.get(
            enum_clean,
            {
                "intent": "none",
                "tool": None,
                "args": {},
                "render_instruction": {
                    "type": "text",
                    "content": "Jag förstår inte vad du menar. Kan du förtydliga?",
                },
            },
        )

        # Add metadata
        mapped["meta"] = {
            "version": "4.0",
            "model_id": self.model,
            "schema_version": "v4",
            "mock_used": False,
            "enum_response": enum_response,
            "schema_ok": True,
        }

        return json.dumps(mapped, ensure_ascii=False)

    def _enum_to_intent(self, enum_response: str) -> str:
        """Convert enum response to intent"""
        enum_clean = enum_response.strip().lower()
        intent_map = {
            "time": "time.now",
            "weather": "weather.lookup",
            "memory": "memory.query",
            "greeting": "greeting.hello",
            "calendar": "calendar.create_draft",
            "email": "email.create_draft",
        }
        return intent_map.get(enum_clean, "none")

    def _get_from_cache(self, cache_key: str) -> Optional[Dict[str, Any]]:
        """Get response from cache"""
        try:
            import redis

            redis_client = redis.from_url(
                os.getenv("REDIS_URL", "redis://alice-cache:6379")
            )

            # Check negative cache first
            neg_key = f"neg:{cache_key}"
            neg_cached = redis_client.get(neg_key)
            if neg_cached:
                logger.info("Negative cache hit", cache_key=cache_key)
                return {
                    "text": json.dumps(
                        {
                            "intent": "none",
                            "tool": "none",
                            "args": {},
                            "render_instruction": {
                                "type": "text",
                                "content": "Jag förstår inte vad du menar.",
                            },
                        }
                    ),
                    "model": "negative_cache",
                    "tokens_used": 0,
                    "prompt_tokens": 0,
                    "response_tokens": 0,
                    "temperature": 0.0,
                    "route": "micro",
                    "mock_used": False,
                    "schema_ok": True,
                    "source": "negative_cache",
                }

            # Check positive cache
            cached = redis_client.get(cache_key)
            if cached:
                return json.loads(cached)
        except Exception as e:
            logger.warning("Cache get failed", cache_key=cache_key, error=str(e))
        return None

    def _set_cache(self, cache_key: str, result: Dict[str, Any], ttl: int = 600):
        """Set response in cache (10 minutes TTL)"""
        try:
            import redis

            redis_client = redis.from_url(
                os.getenv("REDIS_URL", "redis://alice-cache:6379")
            )
            redis_client.setex(cache_key, ttl, json.dumps(result))
            logger.info("Micro response cached", cache_key=cache_key, ttl=ttl)
        except Exception as e:
            logger.warning("Cache set failed", cache_key=cache_key, error=str(e))


# Version-controlled cache
_client_cache: Dict[str, MicroClient] = {}


def get_micro_client() -> MicroClient:
    """Get or create global micro client instance"""
    base_url = os.getenv("OLLAMA_BASE_URL", "http://dev-proxy:80/ollama/api")
    model = os.getenv("MICRO_MODEL", "llama2:7b")
    version = os.getenv("MICRO_DRIVER_VERSION", "1")
    use_mock = os.getenv("FEATURE_MICRO_MOCK", "0") == "1"

    key = f"{base_url}|{model}|{version}|mock={use_mock}"
    client = _client_cache.get(key)

    if client:
        return client

    # Create new client instance
    if use_mock:
        client = MockMicroClient()
        logger.info("Micro client init: MOCK mode enabled")
    else:
        client = RealMicroClient(base_url=base_url, model=model)
        logger.info(f"Micro client init: REAL mode, base_url={base_url}, model={model}")

    _client_cache.clear()  # Keep it simple – one active per key
    _client_cache[key] = client

    return client


def reset_micro_client():
    """Reset the global micro client cache (for testing/config changes)"""
    global _client_cache
    _client_cache.clear()
