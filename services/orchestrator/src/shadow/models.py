"""
Shadow mode data models
"""

from pydantic import BaseModel, Field
from typing import Dict, Any, Optional
from datetime import datetime
import uuid

class ShadowRequest(BaseModel):
    """Request for shadow evaluation"""
    session_id: str = Field(..., description="Session ID")
    message: str = Field(..., description="User message")
    primary_route: str = Field(..., description="Primary route (planner_v1)")
    shadow_route: str = Field(..., description="Shadow route (planner_v2)")
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    trace_id: Optional[str] = Field(default=None, description="Trace ID")

class ShadowResponse(BaseModel):
    """Response from shadow evaluation"""
    session_id: str
    trace_id: str
    primary_result: Dict[str, Any]
    shadow_result: Dict[str, Any]
    comparison: Dict[str, Any]
    canary_eligible: bool = Field(default=False, description="Whether response is eligible for canary")
    canary_routed: bool = Field(default=False, description="Whether response was actually routed via canary")
    
class CanaryConfig(BaseModel):
    """Canary configuration"""
    enabled: bool = Field(default=False, description="Whether canary is enabled")
    percentage: float = Field(default=5.0, description="Canary percentage (0-100)")
    min_schema_ok: float = Field(default=0.95, description="Minimum schema_ok rate for canary")
    min_intent_match: float = Field(default=0.90, description="Minimum intent match rate for canary")
    evaluation_window_hours: int = Field(default=24, description="Evaluation window in hours")
    allowed_levels: list[str] = Field(default=["easy", "medium"], description="Levels eligible for canary")
    max_latency_delta_ms: float = Field(default=150.0, description="Maximum latency increase allowed")

class PlannerComparison(BaseModel):
    """Comparison between primary and shadow planners"""
    intent_match: bool = Field(description="Whether both planners chose same intent")
    schema_ok_both: bool = Field(description="Whether both planners had valid schema")
    tool_choice_same: bool = Field(description="Whether both planners chose same tool")
    latency_delta_ms: float = Field(description="Latency difference (shadow - primary)")
    response_similarity: float = Field(description="Response similarity score (0-1)")
    level: str = Field(description="Complexity level (easy/medium/hard)")
    canary_eligible: bool = Field(description="Whether request is eligible for canary")
    canary_routed: bool = Field(description="Whether request was actually routed via canary")
    rollback_reason: Optional[str] = Field(default=None, description="Reason for rollback if any")
    
class ShadowEvent(BaseModel):
    """Event logged to shadow evaluation store"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    session_id: str
    trace_id: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    primary_result: Dict[str, Any]
    shadow_result: Dict[str, Any]
    comparison: PlannerComparison
    canary_eligible: bool
    canary_routed: bool
    metadata: Dict[str, Any] = Field(default_factory=dict)
