"""
JSON schema for planner output validation.
"""

from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field

class ToolStep(BaseModel):
    """A single step in a plan that uses a tool"""
    tool: str = Field(..., description="Name of the tool to use")
    args: Dict[str, Any] = Field(default_factory=dict, description="Arguments for the tool")
    reason: str = Field(..., description="Why this step is needed")
    timeout_ms: Optional[int] = Field(3000, description="Timeout for this tool call in milliseconds")

class Plan(BaseModel):
    """Complete plan with steps and response"""
    plan: str = Field(..., description="Description of the overall plan")
    steps: List[ToolStep] = Field(default_factory=list, description="List of tool steps to execute")
    response: str = Field(..., description="Response to give to the user")
    guardrails: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Safety guardrails")

# JSON schema for validation
PLANNER_SCHEMA = {
    "type": "object",
    "properties": {
        "plan": {
            "type": "string",
            "description": "Description of the overall plan"
        },
        "steps": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "tool": {
                        "type": "string",
                        "description": "Name of the tool to use"
                    },
                    "args": {
                        "type": "object",
                        "description": "Arguments for the tool"
                    },
                    "reason": {
                        "type": "string",
                        "description": "Why this step is needed"
                    },
                    "timeout_ms": {
                        "type": "integer",
                        "description": "Timeout for this tool call in milliseconds"
                    }
                },
                "required": ["tool", "reason"]
            }
        },
        "response": {
            "type": "string",
            "description": "Response to give to the user"
        },
        "guardrails": {
            "type": "object",
            "description": "Safety guardrails"
        }
    },
    "required": ["plan", "response"]
}
