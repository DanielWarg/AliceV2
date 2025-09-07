# services/rl/pipelines/dataset_schemas.py
from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, Optional

from pydantic import BaseModel, Field, validator


class RawEvent(BaseModel):
    timestamp: str
    session_id: str
    text: str = Field(..., min_length=1)
    intent: Optional[str] = None
    tool_called: Optional[str] = None
    tool_success: Optional[bool] = None
    latency_ms: Optional[int] = None
    energy_wh: Optional[float] = None
    policy_refusal: bool = False
    # valfritt extra, sparas i meta
    extra: Dict[str, Any] = Field(default_factory=dict)

    @validator("timestamp")
    def _ts_iso(cls, v: str) -> str:
        # mjukt ISO-krav (låter "2025-09-07T10:57:14Z" m.fl. passera)
        try:
            datetime.fromisoformat(v.replace("Z", "+00:00"))
        except Exception:
            raise ValueError("timestamp must be ISO 8601")
        return v


class State(BaseModel):
    intent: Optional[str]
    text: str
    features: Dict[str, Any] = Field(default_factory=dict)


class Action(BaseModel):
    tool: Optional[str]  # "calendar.create", "email.send", None


class Outcome(BaseModel):
    success: Optional[bool]
    latency_ms: Optional[int]
    energy_wh: Optional[float]


class RewardComponents(BaseModel):
    precision: Optional[float] = None  # φ^2 weighted
    latency: Optional[float] = None  # φ^1 weighted
    energy: Optional[float] = None  # φ^0 weighted
    safety: Optional[float] = None  # φ^-1 weighted
    total: Optional[float] = None


class Episode(BaseModel):
    state: State
    action: Action
    outcome: Outcome
    reward_components: RewardComponents
    meta: Dict[str, Any] = Field(default_factory=dict)
