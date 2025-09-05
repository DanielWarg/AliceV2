#!/usr/bin/env python3
"""
Predictive Assistant API Endpoints
REST API for proactive suggestions and predictive intelligence
"""

from typing import Dict, List, Optional

import structlog
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from ..predictive.proactive_assistant import get_proactive_assistant

logger = structlog.get_logger(__name__)
router = APIRouter()


# Pydantic models for API
class SuggestionFeedback(BaseModel):
    suggestion_id: str = Field(..., description="ID of the suggestion")
    action: str = Field(..., description="User action: accepted, dismissed, executed")
    context: Optional[Dict] = Field(None, description="Additional context")


class ProactiveSuggestionResponse(BaseModel):
    id: str
    type: str
    intent: str
    message: str
    confidence: float
    urgency: str
    reasoning: str
    suggested_at: str
    expires_at: str
    action: Dict
    display: Dict
    context: Dict
    historical_frequency: float


class ProactiveStatsResponse(BaseModel):
    is_enabled: bool
    learning_mode: bool
    model_trained: bool
    last_training: Optional[str]
    active_suggestions_count: int
    suggestion_cooldown_minutes: int
    last_suggestion_time: Optional[str]
    total_logged_events: int
    unique_sessions: int
    db_size_mb: float
    avg_latency_ms: float
    top_predictive_features: Dict[str, float]


class InteractionLogRequest(BaseModel):
    event_type: str = Field(..., description="Type of interaction")
    intent: Optional[str] = Field(None, description="Detected intent")
    session_id: Optional[str] = Field(None, description="Session ID")
    context: Optional[Dict] = Field(None, description="Interaction context")
    response_latency_ms: Optional[float] = Field(
        None, description="Response latency in ms"
    )
    tool_used: Optional[str] = Field(None, description="Tool used")
    success: bool = Field(True, description="Whether interaction was successful")


@router.get(
    "/api/predictive/suggestions", response_model=List[ProactiveSuggestionResponse]
)
async def get_proactive_suggestions(
    max_suggestions: int = Query(
        default=2, ge=1, le=5, description="Maximum number of suggestions"
    ),
    context: Optional[str] = Query(None, description="JSON context string"),
):
    """Get proactive suggestions from the predictive engine"""

    try:
        assistant = get_proactive_assistant()

        # Parse context if provided
        context_dict = {}
        if context:
            import json

            try:
                context_dict = json.loads(context)
            except json.JSONDecodeError:
                logger.warn("Invalid context JSON provided", context=context)

        # Get suggestions
        suggestions = await assistant.get_proactive_suggestions(
            context=context_dict, max_suggestions=max_suggestions
        )

        logger.info(f"API: Retrieved {len(suggestions)} proactive suggestions")

        return suggestions

    except Exception as e:
        logger.error("Failed to get proactive suggestions via API", error=str(e))
        raise HTTPException(
            status_code=500, detail=f"Failed to get suggestions: {str(e)}"
        )


@router.post("/api/predictive/feedback")
async def handle_suggestion_feedback(feedback: SuggestionFeedback):
    """Handle user feedback on proactive suggestions"""

    try:
        assistant = get_proactive_assistant()

        await assistant.handle_suggestion_feedback(
            suggestion_id=feedback.suggestion_id,
            action=feedback.action,
            context=feedback.context,
        )

        logger.info(
            "API: Processed suggestion feedback",
            suggestion_id=feedback.suggestion_id,
            action=feedback.action,
        )

        return {"status": "success", "message": "Feedback processed"}

    except Exception as e:
        logger.error("Failed to handle suggestion feedback", error=str(e))
        raise HTTPException(
            status_code=500, detail=f"Failed to process feedback: {str(e)}"
        )


@router.post("/api/predictive/log_interaction")
async def log_user_interaction(request: InteractionLogRequest):
    """Log a user interaction for predictive learning"""

    try:
        assistant = get_proactive_assistant()

        await assistant.log_user_interaction(
            event_type=request.event_type,
            intent=request.intent,
            session_id=request.session_id,
            context=request.context,
            response_latency_ms=request.response_latency_ms,
            tool_used=request.tool_used,
            success=request.success,
        )

        logger.info(
            "API: Logged user interaction",
            event_type=request.event_type,
            intent=request.intent,
        )

        return {"status": "success", "message": "Interaction logged"}

    except Exception as e:
        logger.error("Failed to log user interaction", error=str(e))
        raise HTTPException(
            status_code=500, detail=f"Failed to log interaction: {str(e)}"
        )


@router.get("/api/predictive/stats", response_model=ProactiveStatsResponse)
async def get_predictive_stats():
    """Get predictive assistant statistics and status"""

    try:
        assistant = get_proactive_assistant()
        stats = assistant.get_stats()

        logger.info("API: Retrieved predictive assistant stats")

        return stats

    except Exception as e:
        logger.error("Failed to get predictive stats", error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to get stats: {str(e)}")


@router.post("/api/predictive/train")
async def trigger_model_training():
    """Manually trigger model training (admin endpoint)"""

    try:
        assistant = get_proactive_assistant()

        # Train model
        success = assistant.prediction_engine.train()

        if success:
            logger.info("API: Model training completed successfully")
            return {"status": "success", "message": "Model training completed"}
        else:
            logger.warn("API: Model training failed")
            raise HTTPException(
                status_code=400, detail="Model training failed - insufficient data"
            )

    except Exception as e:
        logger.error("Failed to train model via API", error=str(e))
        raise HTTPException(status_code=500, detail=f"Training failed: {str(e)}")


@router.post("/api/predictive/cleanup")
async def cleanup_old_data():
    """Cleanup old predictive data (admin endpoint)"""

    try:
        assistant = get_proactive_assistant()
        await assistant.cleanup_old_data()

        logger.info("API: Predictive data cleanup completed")
        return {"status": "success", "message": "Data cleanup completed"}

    except Exception as e:
        logger.error("Failed to cleanup predictive data", error=str(e))
        raise HTTPException(status_code=500, detail=f"Cleanup failed: {str(e)}")


@router.get("/api/predictive/health")
async def predictive_health_check():
    """Health check for predictive assistant"""

    try:
        assistant = get_proactive_assistant()
        stats = assistant.get_stats()

        # Basic health checks
        health_status = "healthy"
        issues = []

        if not stats["model_trained"]:
            issues.append("Model not trained")
            health_status = "warning"

        if stats["total_logged_events"] < 10:
            issues.append("Insufficient training data")
            health_status = "warning"

        if stats["db_size_mb"] > 100:  # Large database
            issues.append("Database size growing large")
            health_status = "warning"

        return {
            "status": health_status,
            "issues": issues,
            "stats": {
                "model_trained": stats["model_trained"],
                "total_events": stats["total_logged_events"],
                "db_size_mb": round(stats["db_size_mb"], 2),
                "learning_mode": stats["learning_mode"],
            },
        }

    except Exception as e:
        logger.error("Predictive health check failed", error=str(e))
        return {
            "status": "unhealthy",
            "issues": [f"Health check error: {str(e)}"],
            "stats": {},
        }
