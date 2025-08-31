"""
Chat API Router
Handles chat completion requests with model routing
"""

from fastapi import APIRouter, HTTPException, Request, Depends
from fastapi.responses import StreamingResponse
import structlog
import time
import asyncio
from typing import Dict, Any

from ..models.api import ChatRequest, ChatResponse, APIError, ModelType
from ..services.guardian_client import GuardianClient
from ..middleware.logging import get_logger_with_trace

router = APIRouter()

# Global Guardian client (will be injected)
guardian_client = GuardianClient()

async def get_guardian_client() -> GuardianClient:
    """Dependency to get Guardian client"""
    return guardian_client

@router.post("/chat", response_model=ChatResponse)
async def chat_completion(
    request: Request,
    chat_request: ChatRequest,
    guardian: GuardianClient = Depends(get_guardian_client)
) -> ChatResponse:
    """
    Handle chat completion request with Guardian protection
    
    Phase 1: Always routes to micro model, provides mock responses
    """
    logger = get_logger_with_trace(request, __name__)
    start_time = time.time()
    
    logger.info(
        "Chat request received",
        session_id=chat_request.session_id,
        message_length=len(chat_request.message),
        requested_model=chat_request.model
    )
    
    try:
        # Check Guardian admission control
        admitted = await guardian.check_admission({
            "type": "chat",
            "session_id": chat_request.session_id,
            "message_length": len(chat_request.message)
        })
        
        if not admitted:
            guardian_health = await guardian.get_health()
            retry_after = guardian.get_retry_after_seconds(guardian_health)
            
            logger.warning(
                "Request blocked by Guardian",
                session_id=chat_request.session_id,
                guardian_state=guardian_health.get("state"),
                retry_after=retry_after
            )
            
            raise HTTPException(
                status_code=503,
                detail=APIError.create(
                    code="SERVICE_OVERLOADED",
                    message="System is currently overloaded, please try again later",
                    retry_after=retry_after,
                    trace_id=getattr(request.state, "trace_id", None)
                ).model_dump()
            )
        
        # Get Guardian health for context
        guardian_health = await guardian.get_health()
        
        # Get Guardian's recommended model (Phase 1: always micro)
        recommended_model = await guardian.get_recommended_model({
            "message": chat_request.message,
            "session_id": chat_request.session_id
        })
        
        # Override with request preference if valid (Phase 1: ignore for now)
        actual_model = ModelType.MICRO  # Phase 1: Always use micro
        
        logger.info(
            "Model routing decision",
            session_id=chat_request.session_id,
            requested_model=chat_request.model,
            recommended_model=recommended_model,
            actual_model=actual_model
        )
        
        # Generate mock response (Phase 1 implementation)
        response_text = await generate_mock_response(chat_request.message, actual_model)
        
        # Calculate latency
        latency_ms = int((time.time() - start_time) * 1000)
        
        # Report metrics to Guardian
        await guardian.report_request_metrics({
            "type": "chat",
            "model": actual_model,
            "latency_ms": latency_ms,
            "message_length": len(chat_request.message),
            "response_length": len(response_text),
            "success": True
        })
        
        logger.info(
            "Chat request completed",
            session_id=chat_request.session_id,
            model_used=actual_model,
            latency_ms=latency_ms,
            response_length=len(response_text)
        )
        
        return ChatResponse(
            session_id=chat_request.session_id,
            response=response_text,
            model_used=actual_model,
            latency_ms=latency_ms,
            trace_id=getattr(request.state, "trace_id", None),
            metadata={
                "phase": "1",
                "mock_response": True,
                "guardian_state": guardian_health.get("state", "unknown")
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        latency_ms = int((time.time() - start_time) * 1000)
        
        logger.error(
            "Chat request failed",
            session_id=chat_request.session_id,
            error=str(e),
            latency_ms=latency_ms,
            exc_info=True
        )
        
        # Report error metrics to Guardian
        await guardian.report_request_metrics({
            "type": "chat",
            "model": "unknown",
            "latency_ms": latency_ms,
            "message_length": len(chat_request.message),
            "success": False,
            "error": str(e)
        })
        
        raise HTTPException(
            status_code=500,
            detail=APIError.create(
                code="INTERNAL_ERROR",
                message="An internal error occurred while processing your request",
                details=str(e) if str(e) else "Unknown error",
                trace_id=getattr(request.state, "trace_id", None)
            ).model_dump()
        )

async def generate_mock_response(message: str, model: ModelType) -> str:
    """
    Generate mock response for Phase 1
    
    Args:
        message: User message
        model: Model type to simulate
        
    Returns:
        Mock response string
    """
    # Simulate processing delay based on model
    delay_map = {
        ModelType.MICRO: 0.05,   # 50ms
        ModelType.PLANNER: 0.2,  # 200ms  
        ModelType.DEEP: 0.5      # 500ms
    }
    
    await asyncio.sleep(delay_map.get(model, 0.05))
    
    # Generate contextual mock response
    message_lower = message.lower()
    
    if "hej" in message_lower or "hejsan" in message_lower:
        return "Hej! Jag är Alice, din AI-assistent. Hur kan jag hjälpa dig idag?"
    elif "tack" in message_lower:
        return "Varsågod! Är det något mer jag kan hjälpa dig med?"
    elif "vem är du" in message_lower or "vad är du" in message_lower:
        return "Jag är Alice, en AI-assistent som kan hjälpa dig med olika uppgifter. Jag kan svara på frågor, hjälpa med planering och mycket mer."
    elif "?" in message:
        return f"Det är en intressant fråga om '{message[:50]}...'. I Phase 1 av Alice v2 ger jag mock-svar medan systemet byggs upp."
    else:
        return f"Jag förstår att du säger: '{message[:100]}...'. Detta är ett mock-svar från Alice v2 Phase 1."

# Health check for chat service
@router.get("/chat/health")
async def chat_health():
    """Chat service health check"""
    return {
        "service": "chat",
        "status": "healthy",
        "features": {
            "mock_responses": True,
            "guardian_integration": True,
            "model_routing": "phase_1"
        }
    }