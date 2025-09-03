"""
OpenAI Planner Driver - GPT-4o-mini with tool enum-only schema
"""

import os
import json
import time
import httpx
import structlog
from typing import Dict, Any, Optional
from .planner_base import PlannerDriver

logger = structlog.get_logger(__name__)

class OpenAIPlannerDriver(PlannerDriver):
    """OpenAI GPT-4o-mini planner driver with tool enum-only schema"""
    
    def __init__(self):
        super().__init__()
        self.api_key = os.getenv("OPENAI_API_KEY")
        self.api_base = "https://api.openai.com/v1"
        self.model = "gpt-4o-mini"
        
        # Tool enum-only schema
        self.system_prompt = """You are Alice, an AI assistant that plans and executes actions.
You must respond ONLY with JSON format to structure your plans and tool calls.

Available tools:
- calendar.create: Create calendar events
- email.draft: Create email drafts
- weather.get: Get weather information
- time.get: Get current time
- n8n.run: Run n8n workflows (email_draft, calendar_draft, batch_rag)

IMPORTANT: You must respond with EXACTLY this JSON format:
{
  "tool": "tool_name",
  "reason": "Brief reason in English"
}

Rules:
- Only select the tool name (enum)
- No arguments - they are built deterministically in code
- Keep reason short and clear
- Respond ONLY with JSON, no extra text
- End with "}" and nothing more"""

        if not self.api_key:
            raise ValueError("OPENAI_API_KEY environment variable required")
        
        logger.info("OpenAI planner driver initialized", model=self.model)
    
    def generate(self, message: str) -> Dict[str, Any]:
        """Generate tool selection using OpenAI"""
        start_time = time.perf_counter()
        
        try:
            # Prepare request
            payload = {
                "model": self.model,
                "messages": [
                    {"role": "system", "content": self.system_prompt},
                    {"role": "user", "content": message}
                ],
                "temperature": 0.0,
                "max_tokens": 100,
                "response_format": {"type": "json_object"}
            }
            
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            
            # Make API call
            with httpx.Client(timeout=10.0) as client:
                response = client.post(
                    f"{self.api_base}/chat/completions",
                    json=payload,
                    headers=headers
                )
                response.raise_for_status()
                
                data = response.json()
                content = data["choices"][0]["message"]["content"]
                
                # Parse JSON response
                try:
                    tool_selection = json.loads(content)
                    tool = tool_selection.get("tool")
                    reason = tool_selection.get("reason", "")
                    
                    # Validate tool enum
                    valid_tools = ["calendar.create", "email.draft", "weather.get", "time.get", "n8n.run"]
                    if tool not in valid_tools:
                        return {
                            "success": False,
                            "error": f"Invalid tool: {tool}",
                            "tool": None,
                            "reason": reason,
                            "latency_ms": (time.perf_counter() - start_time) * 1000,
                            "provider": "openai"
                        }
                    
                    # Calculate tokens (rough estimate)
                    input_tokens = len(self.system_prompt.split()) + len(message.split())
                    output_tokens = len(content.split())
                    total_tokens = input_tokens + output_tokens
                    
                    return {
                        "success": True,
                        "tool": tool,
                        "reason": reason,
                        "latency_ms": (time.perf_counter() - start_time) * 1000,
                        "provider": "openai",
                        "tokens_used": total_tokens,
                        "raw_response": content
                    }
                    
                except json.JSONDecodeError as e:
                    return {
                        "success": False,
                        "error": f"JSON parse error: {str(e)}",
                        "tool": None,
                        "reason": "",
                        "latency_ms": (time.perf_counter() - start_time) * 1000,
                        "provider": "openai",
                        "raw_response": content
                    }
                    
        except httpx.TimeoutException:
            return {
                "success": False,
                "error": "OpenAI API timeout",
                "tool": None,
                "reason": "",
                "latency_ms": (time.perf_counter() - start_time) * 1000,
                "provider": "openai"
            }
        except httpx.HTTPStatusError as e:
            return {
                "success": False,
                "error": f"OpenAI API error: {e.response.status_code}",
                "tool": None,
                "reason": "",
                "latency_ms": (time.perf_counter() - start_time) * 1000,
                "provider": "openai"
            }
        except Exception as e:
            return {
                "success": False,
                "error": f"OpenAI request failed: {str(e)}",
                "tool": None,
                "reason": "",
                "latency_ms": (time.perf_counter() - start_time) * 1000,
                "provider": "openai"
            }
