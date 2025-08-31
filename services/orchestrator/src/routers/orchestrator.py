"""
Orchestrator API Router
Handles LLM routing and ingestion requests
"""

from fastapi import APIRouter, HTTPException, Request, Depends
import structlog
import time
from typing import Dict, Any

from ..models.api import IngestRequest, IngestResponse, APIError, ModelType
from ..services.guardian_client import GuardianClient
from ..middleware.logging import get_logger_with_trace

router = APIRouter()

# Global Guardian client (will be injected)
guardian_client = GuardianClient()

async def get_guardian_client() -> GuardianClient:
    """Dependency to get Guardian client"""
    return guardian_client

def route_request(request: IngestRequest) -> ModelType:
    """
    Phase 1 routing logic: Always return micro model
    
    Future phases will implement sophisticated routing based on:
    - Message complexity analysis
    - Available system resources
    - Guardian system state
    - User preferences and history
    
    Args:
        request: Ingestion request to route
        
    Returns:
        Model to use for processing
    """
    # Phase 1: Always route to micro model as specified
    return ModelType.MICRO

def estimate_latency(model: ModelType, text_length: int) -> int:
    """
    Estimate processing latency based on model and input length
    
    Args:
        model: Target model
        text_length: Input text length
        
    Returns:
        Estimated latency in milliseconds
    """
    base_latency = {
        ModelType.MICRO: 100,    # 100ms base
        ModelType.PLANNER: 500,  # 500ms base
        ModelType.DEEP: 1500     # 1.5s base
    }
    
    # Add ~1ms per character for longer texts
    text_penalty = min(text_length, 1000) // 10
    
    return base_latency.get(model, 100) + text_penalty

def calculate_priority(request: IngestRequest, guardian_health: Dict[str, Any]) -> int:
    """
    Calculate request priority (1-10, where 10 is highest)
    
    Args:
        request: Ingestion request
        guardian_health: Guardian system health data
        
    Returns:
        Priority score 1-10
    """
    base_priority = 5  # Default priority
    
    # Adjust based on Guardian state
    state = guardian_health.get("state", "NORMAL")
    if state == "NORMAL":
        priority_modifier = 0
    elif state == "BROWNOUT":
        priority_modifier = -1
    elif state == "DEGRADED":
        priority_modifier = -2
    else:
        priority_modifier = -3
    
    # Shorter messages get slight priority boost
    if len(request.text) < 100:
        priority_modifier += 1
    
    return max(1, min(10, base_priority + priority_modifier))

@router.post("/ingest", response_model=IngestResponse)
async def orchestrator_ingest(
    request: Request,
    ingest_request: IngestRequest,
    guardian: GuardianClient = Depends(get_guardian_client)
) -> IngestResponse:
    """
    Main orchestrator ingestion endpoint
    
    Performs routing decisions and admission control for LLM requests.
    Phase 1: Always routes to micro model with Guardian protection.
    """
    logger = get_logger_with_trace(request, __name__)
    start_time = time.time()
    
    logger.info(
        "Orchestrator ingest request",
        session_id=ingest_request.session_id,
        text_length=len(ingest_request.text),
        lang=ingest_request.lang,
        intent=ingest_request.intent
    )
    
    try:
        # Get Guardian health status
        guardian_health = await guardian.get_health()
        
        # Check admission control
        admitted = await guardian.check_admission({
            "type": "ingest",
            "session_id": ingest_request.session_id,
            "text_length": len(ingest_request.text),
            "lang": ingest_request.lang
        })
        
        if not admitted:
            retry_after = guardian.get_retry_after_seconds(guardian_health)
            
            logger.warning(
                "Ingest request blocked by Guardian",
                session_id=ingest_request.session_id,
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
        
        # Perform routing decision
        routed_model = route_request(ingest_request)
        
        # Calculate request priority
        priority = calculate_priority(ingest_request, guardian_health)
        
        # Estimate processing latency
        estimated_latency = estimate_latency(routed_model, len(ingest_request.text))
        
        # Generate routing reason
        routing_reason = f"Phase 1 routing: always micro model (Guardian: {guardian_health.get('state', 'UNKNOWN')})"
        
        # Calculate response latency
        response_latency_ms = int((time.time() - start_time) * 1000)
        
        logger.info(
            "Orchestrator routing decision",
            session_id=ingest_request.session_id,
            routed_model=routed_model,
            priority=priority,
            estimated_latency_ms=estimated_latency,
            response_latency_ms=response_latency_ms,
            guardian_state=guardian_health.get("state")
        )
        
        # Report metrics to Guardian
        await guardian.report_request_metrics({
            "type": "ingest",
            "routed_model": routed_model,
            "latency_ms": response_latency_ms,
            "text_length": len(ingest_request.text),
            "priority": priority,
            "success": True
        })
        
        return IngestResponse(
            session_id=ingest_request.session_id,
            accepted=True,
            model=routed_model,
            priority=priority,
            estimated_latency_ms=estimated_latency,
            reason=routing_reason,
            trace_id=getattr(request.state, "trace_id", None)
        )
        
    except HTTPException:
        raise
    except Exception as e:
        response_latency_ms = int((time.time() - start_time) * 1000)
        
        logger.error(
            "Orchestrator ingest failed",
            session_id=ingest_request.session_id,
            error=str(e),
            response_latency_ms=response_latency_ms,
            exc_info=True
        )
        
        # Report error metrics to Guardian
        await guardian.report_request_metrics({
            "type": "ingest",
            "routed_model": "unknown",
            "latency_ms": response_latency_ms,
            "text_length": len(ingest_request.text),
            "success": False,
            "error": str(e)
        })
        
        raise HTTPException(
            status_code=500,
            detail=APIError.create(
                code="INTERNAL_ERROR",
                message="An internal error occurred while processing routing request",
                details=str(e) if str(e) else "Unknown error",
                trace_id=getattr(request.state, "trace_id", None)
            ).model_dump()
        )

@router.get("/health")
async def orchestrator_health(
    guardian: GuardianClient = Depends(get_guardian_client)
):
    """Orchestrator service health check with routing capability status"""
    try:
        guardian_health = await guardian.get_health()
        
        return {
            "service": "orchestrator",
            "status": "healthy",
            "routing": {
                "phase": "1",
                "available_models": ["micro"],
                "routing_logic": "always_micro",
                "guardian_integration": True
            },
            "guardian_status": guardian_health.get("state", "unknown"),
            "features": {
                "admission_control": True,
                "priority_calculation": True,
                "latency_estimation": True,
                "metrics_reporting": True
            }
        }
    except Exception as e:
        return {
            "service": "orchestrator", 
            "status": "degraded",
            "error": str(e),
            "guardian_status": "error"
        }