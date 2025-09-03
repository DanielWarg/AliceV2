"""
Alice v2 API Models
Pydantic models for request/response validation with versioning
"""

from pydantic import BaseModel, Field
from typing import Optional, Literal, Dict, Any, List
from enum import Enum
import time

# API Version
API_VERSION = "1"

class ModelType(str, Enum):
    """Available LLM models for routing"""
    AUTO = "auto"
    MICRO = "micro" 
    PLANNER = "planner"
    DEEP = "deep"

class GuardianState(str, Enum):
    """Guardian system states"""
    NORMAL = "NORMAL"
    BROWNOUT = "BROWNOUT"
    DEGRADED = "DEGRADED"
    EMERGENCY = "EMERGENCY"
    LOCKDOWN = "LOCKDOWN"

# Base request model with versioning
class BaseRequest(BaseModel):
    """Base request with required versioning"""
    v: Literal["1"] = Field(default=API_VERSION, description="API version")
    session_id: str = Field(..., min_length=1, description="Session identifier")
    timestamp: Optional[int] = Field(default_factory=lambda: int(time.time() * 1000), description="Request timestamp (ms)")

class BaseResponse(BaseModel):
    """Base response with versioning and metadata"""
    v: Literal["1"] = API_VERSION
    session_id: str
    timestamp: int = Field(default_factory=lambda: int(time.time() * 1000))
    trace_id: Optional[str] = None

# Chat API models
class ChatRequest(BaseRequest):
    """Chat completion request"""
    message: str = Field(..., min_length=1, max_length=10000, description="User message")
    model: Optional[ModelType] = Field(default=ModelType.AUTO, description="Preferred model")
    context: Optional[Dict[str, Any]] = Field(default=None, description="Additional context")
    force_route: Optional[str] = Field(default=None, description="Force specific route (micro, planner, deep)")

class ChatResponse(BaseResponse):
    """Chat completion response"""
    response: str = Field(..., description="AI response")
    model_used: ModelType = Field(..., description="Model that generated the response")
    latency_ms: int = Field(..., description="Response generation time in milliseconds")
    metadata: Optional[Dict[str, Any]] = Field(default=None, description="Additional response metadata")

# Orchestrator API models
class IngestRequest(BaseRequest):
    """Orchestrator ingestion request for routing"""
    text: str = Field(..., min_length=1, max_length=10000, description="Input text")
    lang: Optional[str] = Field(default="sv", description="Language code")
    intent: Optional[str] = Field(default=None, description="Detected intent (if known)")
    context: Optional[Dict[str, Any]] = Field(default=None, description="Request context")

class IngestResponse(BaseResponse):
    """Orchestrator routing decision response"""
    accepted: bool = Field(..., description="Whether request was accepted")
    model: ModelType = Field(..., description="Routed model")
    priority: int = Field(..., description="Request priority (1-10)")
    estimated_latency_ms: int = Field(..., description="Estimated processing time")
    reason: Optional[str] = Field(default=None, description="Routing reason")

# Error models
class APIError(BaseModel):
    """Standardized API error response"""
    error: Dict[str, Any] = Field(..., description="Error details")
    
    @classmethod
    def create(
        cls,
        code: str,
        message: str,
        details: Optional[Any] = None,
        trace_id: Optional[str] = None,
        retry_after: Optional[int] = None
    ) -> "APIError":
        """Create standardized error response"""
        error_dict = {
            "code": code,
            "message": message
        }
        
        if details:
            error_dict["details"] = details
        if trace_id:
            error_dict["trace_id"] = trace_id
        if retry_after:
            error_dict["retry_after"] = retry_after
            
        return cls(error=error_dict)

# Health check models
class DependencyHealth(BaseModel):
    """Dependency health status"""
    name: str
    status: str
    latency_ms: Optional[int] = None
    last_check: int = Field(default_factory=lambda: int(time.time() * 1000))

class HealthResponse(BaseModel):
    """Service health response"""
    status: Literal["healthy", "degraded", "unhealthy"]
    service: str
    version: str
    timestamp: int = Field(default_factory=lambda: int(time.time() * 1000))
    dependencies: Dict[str, Any] = Field(default_factory=dict)
    metrics: Optional[Dict[str, Any]] = Field(default=None)