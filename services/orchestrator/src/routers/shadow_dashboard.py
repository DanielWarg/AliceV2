"""
Shadow mode dashboard endpoint
"""

import os
import json
import structlog
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Any, List
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/shadow", tags=["shadow"])

class ShadowStats(BaseModel):
    """Shadow evaluation statistics"""
    total_requests: int
    canary_eligible: int
    canary_routed: int
    intent_match_rate: float
    tool_choice_same_rate: float
    avg_latency_delta_ms: float
    schema_ok_rate: float
    # Level-specific metrics
    easy_medium_schema_ok_rate: float = 0.0
    easy_medium_intent_match_rate: float = 0.0
    easy_medium_tool_match_rate: float = 0.0
    hard_schema_ok_rate: float = 0.0
    hard_intent_match_rate: float = 0.0
    hard_tool_match_rate: float = 0.0
    # Rollback analysis
    top_rollback_reasons: Dict[str, int] = {}

@router.get("/stats")
async def get_shadow_stats(hours: int = 24) -> ShadowStats:
    """Get shadow evaluation statistics for the last N hours"""
    try:
        eval_dir = Path(os.getenv("SHADOW_EVAL_DIR", "data/shadow_eval"))
        if not eval_dir.exists():
            return ShadowStats(
                total_requests=0,
                canary_eligible=0,
                canary_routed=0,
                intent_match_rate=0.0,
                tool_choice_same_rate=0.0,
                avg_latency_delta_ms=0.0,
                schema_ok_rate=0.0
            )
        
        # Calculate time window
        cutoff_time = datetime.utcnow() - timedelta(hours=hours)
        
        # Collect events from JSONL files
        events = []
        for event_file in eval_dir.glob("shadow_events_*.jsonl"):
            try:
                with open(event_file, "r") as f:
                    for line in f:
                        try:
                            event = json.loads(line.strip())
                            event_time = datetime.fromisoformat(event["timestamp"].replace("Z", "+00:00"))
                            if event_time >= cutoff_time:
                                events.append(event)
                        except:
                            continue
            except:
                continue
        
        if not events:
            return ShadowStats(
                total_requests=0,
                canary_eligible=0,
                canary_routed=0,
                intent_match_rate=0.0,
                tool_choice_same_rate=0.0,
                avg_latency_delta_ms=0.0,
                schema_ok_rate=0.0
            )
        
        # Calculate statistics
        total_requests = len(events)
        canary_eligible = sum(1 for e in events if e.get("canary_eligible", False))
        canary_routed = sum(1 for e in events if e.get("canary_routed", False))
        
        intent_matches = sum(1 for e in events if e.get("comparison", {}).get("intent_match", False))
        tool_choice_same = sum(1 for e in events if e.get("comparison", {}).get("tool_choice_same", False))
        schema_ok_both = sum(1 for e in events if e.get("comparison", {}).get("schema_ok_both", False))
        
        latency_deltas = [e.get("comparison", {}).get("latency_delta_ms", 0) for e in events]
        avg_latency_delta = sum(latency_deltas) / len(latency_deltas) if latency_deltas else 0
        
        # Calculate level-specific metrics
        easy_medium_events = [e for e in events if e.get("comparison", {}).get("level", "medium") in ["easy", "medium"]]
        hard_events = [e for e in events if e.get("comparison", {}).get("level", "medium") == "hard"]
        
        easy_medium_requests = len(easy_medium_events)
        easy_medium_schema_ok = sum(1 for e in easy_medium_events if e.get("comparison", {}).get("schema_ok_both", False))
        easy_medium_intent_match = sum(1 for e in easy_medium_events if e.get("comparison", {}).get("intent_match", False))
        easy_medium_tool_match = sum(1 for e in easy_medium_events if e.get("comparison", {}).get("tool_choice_same", False))
        
        hard_requests = len(hard_events)
        hard_schema_ok = sum(1 for e in hard_events if e.get("comparison", {}).get("schema_ok_both", False))
        hard_intent_match = sum(1 for e in hard_events if e.get("comparison", {}).get("intent_match", False))
        hard_tool_match = sum(1 for e in hard_events if e.get("comparison", {}).get("tool_choice_same", False))
        
        # Count rollback reasons
        rollback_reasons = {}
        for e in events:
            reason = e.get("comparison", {}).get("rollback_reason")
            if reason:
                rollback_reasons[reason] = rollback_reasons.get(reason, 0) + 1
        
        return ShadowStats(
            total_requests=total_requests,
            canary_eligible=canary_eligible,
            canary_routed=canary_routed,
            intent_match_rate=round(intent_matches / total_requests, 3) if total_requests > 0 else 0.0,
            tool_choice_same_rate=round(tool_choice_same / total_requests, 3) if total_requests > 0 else 0.0,
            avg_latency_delta_ms=round(avg_latency_delta, 1),
            schema_ok_rate=round(schema_ok_both / total_requests, 3) if total_requests > 0 else 0.0,
            # Level-specific metrics
            easy_medium_schema_ok_rate=round(easy_medium_schema_ok / easy_medium_requests, 3) if easy_medium_requests > 0 else 0.0,
            easy_medium_intent_match_rate=round(easy_medium_intent_match / easy_medium_requests, 3) if easy_medium_requests > 0 else 0.0,
            easy_medium_tool_match_rate=round(easy_medium_tool_match / easy_medium_requests, 3) if easy_medium_requests > 0 else 0.0,
            hard_schema_ok_rate=round(hard_schema_ok / hard_requests, 3) if hard_requests > 0 else 0.0,
            hard_intent_match_rate=round(hard_intent_match / hard_requests, 3) if hard_requests > 0 else 0.0,
            hard_tool_match_rate=round(hard_tool_match / hard_requests, 3) if hard_requests > 0 else 0.0,
            # Rollback analysis
            top_rollback_reasons=rollback_reasons
        )
        
    except Exception as e:
        logger.error("Failed to get shadow stats", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to get shadow statistics")

@router.get("/events")
async def get_recent_events(limit: int = 50) -> List[Dict[str, Any]]:
    """Get recent shadow evaluation events"""
    try:
        eval_dir = Path(os.getenv("SHADOW_EVAL_DIR", "data/shadow_eval"))
        if not eval_dir.exists():
            return []
        
        events = []
        for event_file in sorted(eval_dir.glob("shadow_events_*.jsonl"), reverse=True):
            try:
                with open(event_file, "r") as f:
                    for line in f:
                        try:
                            event = json.loads(line.strip())
                            events.append(event)
                            if len(events) >= limit:
                                return events
                        except:
                            continue
            except:
                continue
        
        return events[:limit]
        
    except Exception as e:
        logger.error("Failed to get shadow events", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to get shadow events")

@router.get("/config")
async def get_canary_config() -> Dict[str, Any]:
    """Get current canary configuration"""
    return {
        "enabled": os.getenv("PLANNER_CANARY_ENABLED", "0") == "1",
        "percentage": float(os.getenv("PLANNER_CANARY_PERCENT", "5.0")),
        "min_schema_ok": float(os.getenv("PLANNER_CANARY_MIN_SCHEMA_OK", "0.95")),
        "min_intent_match": float(os.getenv("PLANNER_CANARY_MIN_INTENT_MATCH", "0.90")),
        "evaluation_window_hours": int(os.getenv("PLANNER_CANARY_EVAL_WINDOW_HOURS", "24"))
    }
