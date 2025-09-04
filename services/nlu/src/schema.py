from typing import Any, Dict, Optional

from pydantic import BaseModel, Field


class ParseRequest(BaseModel):
    v: str = Field(default="1")
    text: str
    lang: Optional[str] = "sv"
    session_id: Optional[str] = None


class ParseResponse(BaseModel):
    v: str
    lang: str
    intent: Dict[str, Any]
    slots: Dict[str, Any]
    route_hint: str
    timings_ms: Dict[str, float]
