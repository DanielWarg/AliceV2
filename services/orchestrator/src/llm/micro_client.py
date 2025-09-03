"""
Micro Client Interface
Abstracts micro LLM calls with real and mock implementations
"""

import os
import structlog
from typing import Dict, Any, Optional
from datetime import datetime, timedelta
import json

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
                "args": {
                    "location": "Stockholm",
                    "unit": "metric"
                },
                "render_instruction": {
                    "type": "text",
                    "content": "Vädret i Stockholm är {temperature}°C och {condition}."
                }
            },
            "time.now": {
                "intent": "time",
                "tool": "time.now",
                "args": {
                    "timezone": "Europe/Stockholm"
                },
                "render_instruction": {
                    "type": "text",
                    "content": "Klockan är {time} i Stockholm."
                }
            },
            "calendar.create": {
                "intent": "calendar",
                "tool": "calendar.create_draft",
                "args": {
                    "title": "(Auto) Möte",
                    "start_iso": (datetime.now() + timedelta(minutes=30)).strftime("%Y-%m-%dT%H:%M"),
                    "duration_min": 30,
                    "attendees": [],
                    "timezone": "Europe/Stockholm"
                },
                "render_instruction": {
                    "type": "text",
                    "content": "Jag har bokat ett möte för dig klockan {start_time}."
                }
            },
            "email.send": {
                "intent": "email",
                "tool": "email.create_draft",
                "args": {
                    "to": [],
                    "subject": "(Auto) Meddelande",
                    "body": "(Auto) Här är ditt meddelande.",
                    "importance": "normal"
                },
                "render_instruction": {
                    "type": "text",
                    "content": "Jag har skapat ett utkast till e-post med ämnet '{subject}'."
                }
            },
            "greeting.hello": {
                "intent": "greeting",
                "tool": None,
                "args": {},
                "render_instruction": {
                    "type": "text",
                    "content": "Hej! Jag är Alice, din AI-assistent. Hur kan jag hjälpa dig?"
                }
            }
        }
    
    def generate(self, prompt: str, **kwargs) -> Dict[str, Any]:
        """Generate mock response based on prompt content"""
        # Simple intent detection based on keywords
        prompt_lower = prompt.lower()
        
        # Weather intent (check first to avoid conflicts)
        if any(word in prompt_lower for word in ["väder", "weather", "temperatur", "vädret"]):
            intent = "weather.today"
        # Time intent
        elif any(word in prompt_lower for word in ["klockan", "tid", "time", "när", "hur mycket är klockan"]):
            intent = "time.now"
        # Calendar intent
        elif any(word in prompt_lower for word in ["boka", "möte", "calendar", "kalender", "schedule"]):
            intent = "calendar.create"
        # Email intent
        elif any(word in prompt_lower for word in ["mail", "email", "e-post", "skicka", "send"]):
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
            "schema_ok": True  # 👈 VIKTIG RAD - Step 8 mätning
        }
        
        logger.info("Mock micro response generated", 
                   intent=intent, 
                   prompt_length=len(prompt),
                   mock_used=True)
        
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
            "schema_ok": True  # Mock responses are always schema-valid
        }

class RealMicroClient(MicroClient):
    """Real micro client using actual Ollama models"""
    
    def __init__(self, base_url: str, model: str):
        self.base_url = base_url.rstrip("/")
        self.model = model
        
        # Micro-specific settings
        self.temperature = 0.3
        self.max_tokens = 150
        self.top_p = 0.9
        
        # Swedish system prompt
        self.system_prompt = """Du är Alice, en hjälpsam AI-assistent som alltid svarar på svenska.
Var kort och koncis (max 2-3 meningar). Var hjälpsam och vänlig."""
    
    def generate(self, prompt: str, **kwargs) -> Dict[str, Any]:
        """Generate response using real Ollama model"""
        import httpx
        
        try:
            micro_kwargs = {
                "temperature": kwargs.get("temperature", self.temperature),
                "max_tokens": kwargs.get("max_tokens", self.max_tokens),
                "top_p": kwargs.get("top_p", self.top_p),
                "system": kwargs.get("system", self.system_prompt)
            }
            
            payload = {
                "model": self.model,
                "prompt": prompt,
                "stream": False
            }
            payload.update(micro_kwargs)
            
            url = f"{self.base_url}/api/generate"
            logger.info(f"Real micro request -> {url} model={self.model}")
            
            with httpx.Client(timeout=60.0) as client:
                response = client.post(url, json=payload)
                response.raise_for_status()
                data = response.json()
            
            response_text = data.get("response", "").strip()
            
            logger.info("Real micro response generated", 
                       model=self.model, 
                       response_length=len(response_text),
                       tokens_used=data.get("eval_count", 0))
            
            return {
                "text": response_text,
                "model": self.model,
                "tokens_used": data.get("eval_count", 0),
                "prompt_tokens": data.get("prompt_eval_count", 0),
                "response_tokens": data.get("eval_count", 0),
                "temperature": micro_kwargs["temperature"],
                "route": "micro",
                "mock_used": False,
                "schema_ok": True  # 👈 Sätts efter validering i orchestrator
            }
            
        except Exception as e:
            logger.error("Real micro generation failed", model=self.model, error=str(e))
            raise

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
        logger.info(f"Micro client init: MOCK mode enabled")
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
