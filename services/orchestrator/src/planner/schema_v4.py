"""
Planner Schema v4 - Strict validation for shadow mode
"""

from pydantic import BaseModel, Field, validator
from typing import Dict, Any, Union, Literal
from enum import Enum
from datetime import datetime, timedelta
import re

class IntentType(str, Enum):
    """Available intent types"""
    EMAIL = "email"
    CALENDAR = "calendar" 
    WEATHER = "weather"
    MEMORY = "memory"
    NONE = "none"

class ToolType(str, Enum):
    """Available tool types"""
    EMAIL_CREATE_DRAFT = "email.create_draft"
    CALENDAR_CREATE_DRAFT = "calendar.create_draft"
    WEATHER_LOOKUP = "weather.lookup"
    MEMORY_QUERY = "memory.query"
    NONE = "none"

class RenderInstruction(str, Enum):
    """Available render instructions"""
    CHART = "chart"
    MAP = "map"
    SCENE = "scene"
    NONE = "none"

class PlanOut(BaseModel):
    """Strict planner output schema v4"""
    
    # Core fields
    intent: IntentType = Field(..., description="Detected intent")
    tool: ToolType = Field(..., description="Selected tool")
    args: Dict[str, Any] = Field(default_factory=dict, description="Tool arguments")
    render_instruction: RenderInstruction = Field(default=RenderInstruction.NONE, description="Render instruction")
    
    # Metadata
    meta: Dict[str, Any] = Field(
        default_factory=lambda: {
            "version": "4.0",
            "model_id": "planner_v2",
            "schema_version": "v4"
        },
        description="Metadata"
    )
    
    # Validation
    @validator('args')
    def validate_args(cls, v):
        """Ensure args is a valid dict"""
        if not isinstance(v, dict):
            raise ValueError("args must be a dictionary")
        return v
    
    @validator('meta')
    def validate_meta(cls, v):
        """Ensure meta has required fields"""
        if not isinstance(v, dict):
            raise ValueError("meta must be a dictionary")
        return v
    
    class Config:
        """Pydantic configuration"""
        use_enum_values = True
        validate_assignment = True
        extra = "forbid"  # No extra fields allowed

    @classmethod
    def canonicalize_args(cls, tool: str, args: Dict[str, Any]) -> Dict[str, Any]:
        """Canonicalize args with defaults and timezone handling"""
        canonical = args.copy() if isinstance(args, dict) else {}
        
        # Add defaults based on tool
        if tool == "calendar.create_draft":
            if "title" not in canonical:
                canonical["title"] = ""
            if "start_iso" not in canonical:
                # Default to 30 minutes from now
                now = datetime.now()
                start_time = now + timedelta(minutes=30)
                canonical["start_iso"] = start_time.strftime("%Y-%m-%dT%H:%M")
            if "duration_min" not in canonical:
                canonical["duration_min"] = 30
            if "attendees" not in canonical:
                canonical["attendees"] = []
            if "timezone" not in canonical:
                canonical["timezone"] = "Europe/Stockholm"
            
            # Round start_iso to 5-minute intervals
            if "start_iso" in canonical and canonical["start_iso"]:
                try:
                    dt = datetime.fromisoformat(canonical["start_iso"].replace("Z", "+00:00"))
                    # Round to nearest 5 minutes
                    minutes = (dt.minute // 5) * 5
                    dt = dt.replace(minute=minutes, second=0, microsecond=0)
                    canonical["start_iso"] = dt.strftime("%Y-%m-%dT%H:%M")
                except:
                    pass  # Keep original if parsing fails
        
        elif tool == "weather.lookup":
            if "location" not in canonical:
                canonical["location"] = "Stenungsund"
            if "unit" not in canonical:
                canonical["unit"] = "metric"
        
        elif tool == "email.create_draft":
            if "to" not in canonical:
                canonical["to"] = []
            if "subject" not in canonical:
                canonical["subject"] = ""
            if "body" not in canonical:
                canonical["body"] = ""
            if "importance" not in canonical:
                canonical["importance"] = "normal"
        
        # Remove None values and sort keys
        canonical = {k: v for k, v in canonical.items() if v is not None}
        return dict(sorted(canonical.items()))

# Backward compatibility
PlannerOutput = PlanOut
