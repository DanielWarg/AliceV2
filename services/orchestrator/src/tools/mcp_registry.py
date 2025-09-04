"""
MCP (Modular Component Protocol) Tool Registry
Defines available tools with schemas and implementations for Step 7.
"""

import time
from datetime import datetime, timedelta
from typing import Any, Dict, Optional

import httpx
import structlog

logger = structlog.get_logger(__name__)

# Tool schemas
EMAIL_TOOL_SCHEMA = {
    "name": "email.draft",
    "description": "Create email draft",
    "parameters": {
        "type": "object",
        "properties": {
            "to": {"type": "string", "description": "Recipient email address"},
            "subject": {"type": "string", "description": "Email subject"},
            "body": {"type": "string", "description": "Email body content"},
            "priority": {
                "type": "string",
                "enum": ["low", "normal", "high"],
                "default": "normal",
            },
        },
        "required": ["to", "subject", "body"],
    },
}

CALENDAR_TOOL_SCHEMA = {
    "name": "calendar.create",
    "description": "Create calendar event",
    "parameters": {
        "type": "object",
        "properties": {
            "title": {"type": "string", "description": "Event title"},
            "start_time": {"type": "string", "description": "Start time (ISO format)"},
            "end_time": {"type": "string", "description": "End time (ISO format)"},
            "description": {"type": "string", "description": "Event description"},
            "attendees": {
                "type": "array",
                "items": {"type": "string"},
                "description": "List of attendee emails",
            },
        },
        "required": ["title", "start_time"],
    },
}

WEATHER_TOOL_SCHEMA = {
    "name": "weather.get",
    "description": "Get weather information",
    "parameters": {
        "type": "object",
        "properties": {
            "location": {"type": "string", "description": "City name or coordinates"},
            "units": {
                "type": "string",
                "enum": ["celsius", "fahrenheit"],
                "default": "celsius",
            },
        },
        "required": ["location"],
    },
}

TIME_TOOL_SCHEMA = {
    "name": "time.get",
    "description": "Get current time and date",
    "parameters": {
        "type": "object",
        "properties": {
            "timezone": {
                "type": "string",
                "description": "Timezone (e.g., 'Europe/Stockholm')",
                "default": "Europe/Stockholm",
            }
        },
    },
}

N8N_TOOL_SCHEMA = {
    "name": "n8n.run",
    "description": "Execute n8n workflow via webhook",
    "parameters": {
        "type": "object",
        "properties": {
            "workflow": {
                "type": "string",
                "description": "Workflow name (email_draft, calendar_draft, batch_rag)",
                "enum": ["email_draft", "calendar_draft", "batch_rag"],
            },
            "request_id": {
                "type": "string",
                "description": "Unique request identifier",
            },
            "subject": {"type": "string", "description": "Subject/title for the task"},
            "to": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Recipient list (for email_draft)",
            },
            "body": {"type": "string", "description": "Content/description"},
            "start_time": {
                "type": "string",
                "description": "Start time (ISO format, for calendar_draft)",
            },
            "end_time": {
                "type": "string",
                "description": "End time (ISO format, for calendar_draft)",
            },
            "attendees": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Attendee list (for calendar_draft)",
            },
            "query": {"type": "string", "description": "Search query (for batch_rag)"},
        },
        "required": ["workflow", "request_id"],
    },
}


class MCPToolRegistry:
    """MCP Tool Registry with real tool implementations"""

    def __init__(self):
        self.tools = {
            "email.draft": {
                "schema": EMAIL_TOOL_SCHEMA,
                "handler": self._handle_email_draft,
                "fallback": None,
            },
            "calendar.create": {
                "schema": CALENDAR_TOOL_SCHEMA,
                "handler": self._handle_calendar_create,
                "fallback": "email.draft",
            },
            "weather.get": {
                "schema": WEATHER_TOOL_SCHEMA,
                "handler": self._handle_weather_get,
                "fallback": None,
            },
            "time.get": {
                "schema": TIME_TOOL_SCHEMA,
                "handler": self._handle_time_get,
                "fallback": None,
            },
            "n8n.run": {
                "schema": N8N_TOOL_SCHEMA,
                "handler": self._handle_n8n_run,
                "fallback": None,
            },
        }

    def get_tool_schema(self, tool_name: str) -> Optional[Dict[str, Any]]:
        """Get tool schema"""
        return self.tools.get(tool_name, {}).get("schema")

    def get_tool_fallback(self, tool_name: str) -> Optional[str]:
        """Get tool fallback"""
        return self.tools.get(tool_name, {}).get("fallback")

    def execute_tool(self, tool_name: str, args: Dict[str, Any]) -> Dict[str, Any]:
        """Execute tool with arguments"""
        if tool_name not in self.tools:
            return {
                "success": False,
                "error": f"Tool {tool_name} not found",
                "data": None,
            }

        try:
            handler = self.tools[tool_name]["handler"]
            return handler(args)
        except Exception as e:
            logger.error("Tool execution failed", tool=tool_name, error=str(e))
            return {"success": False, "error": str(e), "data": None}

    def _handle_email_draft(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Handle email draft creation"""
        try:
            # Validate required fields
            required = ["to", "subject", "body"]
            for field in required:
                if field not in args:
                    return {
                        "success": False,
                        "error": f"Missing required field: {field}",
                        "data": None,
                    }

            # Create email draft (mock implementation)
            draft_id = f"draft_{int(time.time())}"

            result = {
                "draft_id": draft_id,
                "to": args["to"],
                "subject": args["subject"],
                "body": args["body"],
                "priority": args.get("priority", "normal"),
                "created_at": datetime.now().isoformat(),
                "status": "draft",
            }

            logger.info("Email draft created", draft_id=draft_id, to=args["to"])

            return {"success": True, "data": result, "error": None}

        except Exception as e:
            return {"success": False, "error": str(e), "data": None}

    def _handle_calendar_create(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Handle calendar event creation"""
        try:
            # Validate required fields
            if "title" not in args:
                return {
                    "success": False,
                    "error": "Missing required field: title",
                    "data": None,
                }

            # Parse start time
            start_time = args.get("start_time")
            if not start_time:
                # Default to tomorrow at 10:00
                start_time = (
                    (datetime.now() + timedelta(days=1))
                    .replace(hour=10, minute=0)
                    .isoformat()
                )

            # Parse end time
            end_time = args.get("end_time")
            if not end_time:
                # Default to 1 hour after start
                start_dt = datetime.fromisoformat(start_time.replace("Z", "+00:00"))
                end_dt = start_dt + timedelta(hours=1)
                end_time = end_dt.isoformat()

            # Create calendar event (mock implementation)
            event_id = f"evt_{int(time.time())}"

            result = {
                "event_id": event_id,
                "title": args["title"],
                "start_time": start_time,
                "end_time": end_time,
                "description": args.get("description", ""),
                "attendees": args.get("attendees", []),
                "created_at": datetime.now().isoformat(),
                "status": "created",
            }

            logger.info(
                "Calendar event created", event_id=event_id, title=args["title"]
            )

            return {"success": True, "data": result, "error": None}

        except Exception as e:
            return {"success": False, "error": str(e), "data": None}

    def _handle_weather_get(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Handle weather information retrieval"""
        try:
            location = args.get("location", "Stockholm")
            units = args.get("units", "celsius")

            # Mock weather data (in real implementation, call weather API)
            weather_data = {
                "location": location,
                "temperature": 22 if units == "celsius" else 72,
                "condition": "sunny",
                "humidity": 65,
                "wind_speed": 12,
                "units": units,
                "timestamp": datetime.now().isoformat(),
            }

            logger.info("Weather data retrieved", location=location)

            return {"success": True, "data": weather_data, "error": None}

        except Exception as e:
            return {"success": False, "error": str(e), "data": None}

    def _handle_time_get(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Handle current time retrieval"""
        try:
            timezone = args.get("timezone", "Europe/Stockholm")

            # Get current time (mock implementation)
            now = datetime.now()

            result = {
                "time": now.strftime("%H:%M:%S"),
                "date": now.strftime("%Y-%m-%d"),
                "timezone": timezone,
                "timestamp": now.isoformat(),
                "day_of_week": now.strftime("%A"),
            }

            logger.info("Time data retrieved", timezone=timezone)

            return {"success": True, "data": result, "error": None}

        except Exception as e:
            return {"success": False, "error": str(e), "data": None}

    def _handle_n8n_run(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Handle n8n workflow execution via webhook"""
        try:
            # Validate required fields
            if "workflow" not in args:
                return {
                    "success": False,
                    "error": "Missing required field: workflow",
                    "data": None,
                }

            if "request_id" not in args:
                return {
                    "success": False,
                    "error": "Missing required field: request_id",
                    "data": None,
                }

            workflow = args["workflow"]
            request_id = args["request_id"]

            # Validate workflow name
            valid_workflows = ["email_draft", "calendar_draft", "batch_rag"]
            if workflow not in valid_workflows:
                return {
                    "success": False,
                    "error": f"Invalid workflow: {workflow}. Valid workflows: {valid_workflows}",
                    "data": None,
                }

            # Prepare payload based on workflow type
            payload = {
                "request_id": request_id,
                "metadata": {
                    "source": "alice_v2",
                    "timestamp": datetime.now().isoformat(),
                },
            }

            # Add workflow-specific fields
            if workflow == "email_draft":
                if "subject" not in args:
                    return {
                        "success": False,
                        "error": "Missing required field: subject for email_draft",
                        "data": None,
                    }
                if "to" not in args:
                    return {
                        "success": False,
                        "error": "Missing required field: to for email_draft",
                        "data": None,
                    }

                payload.update(
                    {
                        "subject": args["subject"],
                        "to": args["to"],
                        "body": args.get("body", ""),
                    }
                )

            elif workflow == "calendar_draft":
                if "subject" not in args:
                    return {
                        "success": False,
                        "error": "Missing required field: subject for calendar_draft",
                        "data": None,
                    }

                payload.update(
                    {
                        "subject": args["subject"],
                        "start_time": args.get("start_time"),
                        "end_time": args.get("end_time"),
                        "attendees": args.get("attendees", []),
                        "body": args.get("body", ""),
                    }
                )

            elif workflow == "batch_rag":
                if "query" not in args:
                    return {
                        "success": False,
                        "error": "Missing required field: query for batch_rag",
                        "data": None,
                    }

                payload.update({"query": args["query"], "body": args.get("body", "")})

            # Call n8n webhook
            n8n_url = f"http://n8n:5678/webhook/{workflow}"

            try:
                with httpx.Client(timeout=10.0) as client:
                    response = client.post(
                        n8n_url,
                        json=payload,
                        headers={"Content-Type": "application/json"},
                    )

                    if response.status_code == 200:
                        result = {
                            "workflow": workflow,
                            "request_id": request_id,
                            "status": "started",
                            "n8n_response": response.text,
                            "timestamp": datetime.now().isoformat(),
                        }

                        logger.info(
                            "n8n workflow started",
                            workflow=workflow,
                            request_id=request_id,
                        )

                        return {"success": True, "data": result, "error": None}
                    else:
                        return {
                            "success": False,
                            "error": f"n8n webhook failed: {response.status_code} - {response.text}",
                            "data": None,
                        }

            except Exception as e:
                return {
                    "success": False,
                    "error": f"n8n webhook call failed: {str(e)}",
                    "data": None,
                }

        except Exception as e:
            return {"success": False, "error": str(e), "data": None}


# Global MCP registry instance
_mcp_registry: Optional[MCPToolRegistry] = None


def get_mcp_registry() -> MCPToolRegistry:
    """Get or create global MCP registry instance"""
    global _mcp_registry
    if _mcp_registry is None:
        _mcp_registry = MCPToolRegistry()
    return _mcp_registry
