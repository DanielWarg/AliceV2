"""
Chat API Router
Handles chat completion requests with model routing
"""

from fastapi import APIRouter, HTTPException, Request, Response, Depends
from fastapi.responses import StreamingResponse
import structlog
import time
import asyncio
from typing import Dict, Any
import httpx

from ..models.api import ChatRequest, ChatResponse, APIError, ModelType
from ..services.guardian_client import GuardianClient
from ..middleware.logging import get_logger_with_trace
import os
from ..security.sanitiser import detect_injection
from ..security.metrics import injection_suspected_total, set_mode
from ..utils.ram_peak import ram_peak_mb
from ..utils.energy import EnergyMeter
from .orchestrator import log_turn_event

router = APIRouter()

# Global Guardian client (will be injected)
guardian_client = GuardianClient()

async def get_guardian_client() -> GuardianClient:
    """Dependency to get Guardian client"""
    return guardian_client

@router.post("/chat", response_model=ChatResponse)
async def chat_completion(
    request: Request,
    response: Response,
    chat_request: ChatRequest,
    guardian: GuardianClient = Depends(get_guardian_client)
) -> ChatResponse:
    """
    Handle chat completion request with Guardian protection
    
    Phase 1: Always routes to micro model, provides mock responses
    """
    logger = get_logger_with_trace(request, __name__)
    start_time = time.time()
    energy_meter = EnergyMeter(); energy_meter.start()
    
    logger.info(
        "Chat request received",
        session_id=chat_request.session_id,
        message_length=len(chat_request.message),
        requested_model=chat_request.model
    )
    
    try:
        # Security: injection detection (user-only for v1)
        inj_score = detect_injection(chat_request.message, "")
        policy = getattr(request.app.state, "security_policy", {}) or {}
        threshold = float(((policy.get("risk") or {}).get("injection_threshold")) or 0.62)
        high_risk = set(((policy.get("risk") or {}).get("high_risk_intents")) or [])
        enforce = os.getenv("SECURITY_ENFORCE", "false").lower() == "true"
        security_mode = "NORMAL"
        if inj_score >= threshold:
            injection_suspected_total.inc()
            security_mode = "STRICT"
            try:
                set_mode("STRICT")
            except Exception:
                pass
        # --- NLU pre-parse (fail-open) ---
        route_hint = None
        try:
            nlu_payload = {
                "v": "1",
                "text": chat_request.message,
                "lang": getattr(chat_request, "lang", "sv"),
                "session_id": chat_request.session_id,
            }
            with httpx.Client(timeout=0.08) as client:
                nlu_resp = client.post("http://nlu:9002/api/nlu/parse", json=nlu_payload)
                if nlu_resp.status_code == 200:
                    nlu_json = nlu_resp.json()
                    intent = (nlu_json.get("intent") or {})
                    route_hint = nlu_json.get("route_hint")
                    if intent.get("label"):
                        response.headers["X-Intent"] = intent["label"]
                        if intent.get("confidence") is not None:
                            response.headers["X-Intent-Confidence"] = str(intent["confidence"])
                    if route_hint:
                        response.headers["X-Route-Hint"] = route_hint
        except Exception:
            pass
        # Decide route early so middleware can capture per-route latency
        # Respect force_route parameter if provided
        if hasattr(chat_request, 'force_route') and chat_request.force_route:
            route = chat_request.force_route
        else:
            route = route_hint if route_hint in {"micro", "planner", "deep"} else "micro"
        response.headers["X-Route"] = route
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
        
        # Degrade deep in brownout/emergency
        guardian_state = (await guardian.get_health()).get("state", "UNKNOWN")
        blocked_by_guardian = guardian_state in ["BROWNOUT", "EMERGENCY"] and route == "deep"
        if blocked_by_guardian:
            route = "planner"
            response.headers["X-Route"] = route

        # Enforcement: block high-risk until confirmation
        if enforce and inj_score >= threshold:
            intent_label = response.headers.get("X-Intent")
            if intent_label and intent_label in high_risk:
                # Return intent card-style info in metadata
                latency_ms = int((time.time() - start_time) * 1000)
                ram = ram_peak_mb()
                energy_wh = energy_meter.stop()
                # Log event
                try:
                    log_turn_event(
                        trace_id=getattr(request.state, "trace_id", None) or "unknown",
                        session_id=chat_request.session_id,
                        route=route,
                        e2e_first_ms=latency_ms,
                        e2e_full_ms=latency_ms,
                        ram_peak=ram,
                        tool_calls=[],
                        energy_wh=energy_wh,
                        guardian_state=guardian_state,
                        pii_masked=True,
                        consent_scopes=["basic_logging"],
                        rag_data={
                            "top_k": 0,
                            "hits": 0,
                            "llm_model": "mock",
                            "planner_schema_ok": False,
                            "fallback_used": False,
                            "blocked_by_guardian": False,
                            "tokens_used": 0
                        },
                        input_text=chat_request.message,
                        output_text="SECURITY: Intent requires confirmation",
                        lang=getattr(chat_request, "lang", "sv"),
                    )
                except Exception:
                    pass
                return ChatResponse(
                    session_id=chat_request.session_id,
                    response="Säkerhet: Åtgärden kräver bekräftelse i UI (intent-card).",
                    model_used=ModelType.MICRO,
                    latency_ms=latency_ms,
                    trace_id=getattr(request.state, "trace_id", None),
                    metadata={
                        "phase": "1",
                        "mock_response": True,
                        "guardian_state": guardian_state,
                        "route": route,
                        "type": "intent_card",
                        "requires_confirmation": True,
                        "security": {"mode": security_mode, "inj": round(inj_score,2)}
                    }
                )

        # Choose mock model based on route for metadata/latency
        actual_model = ModelType.PLANNER if route == "planner" else (ModelType.DEEP if route == "deep" else ModelType.MICRO)
        
        logger.info(
            "Model routing decision",
            session_id=chat_request.session_id,
            requested_model=chat_request.model,
            recommended_model=recommended_model,
            actual_model=actual_model
        )
        
        # Call orchestrator for real LLM processing
        try:
            logger.info("Attempting to call orchestrator", session_id=chat_request.session_id)
            from .orchestrator import orchestrator_chat
            logger.info("Import successful, calling orchestrator", session_id=chat_request.session_id)
            # Call orchestrator endpoint directly with correct signature
            orchestrator_response = await orchestrator_chat(request, response, chat_request, guardian)
            logger.info("Orchestrator call successful", session_id=chat_request.session_id)
            response_text = orchestrator_response.response
            actual_model = orchestrator_response.model_used
        except Exception as e:
            logger.warning("Orchestrator call failed, falling back to mock", error=str(e), session_id=chat_request.session_id)
            # Fallback to mock response
            response_text = await generate_mock_response(chat_request.message, actual_model)
        
        # Calculate latency
        latency_ms = int((time.time() - start_time) * 1000)
        ram = ram_peak_mb()
        energy_wh = energy_meter.stop()
        
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
            response_length=len(response_text),
            ram_peak_mb=ram,
            energy_wh=energy_wh
        )

        # Turn event logging (observability JSONL)
        try:
            log_turn_event(
                trace_id=getattr(request.state, "trace_id", None) or "unknown",
                session_id=chat_request.session_id,
                route=route,
                e2e_first_ms=latency_ms,
                e2e_full_ms=latency_ms,
                ram_peak=ram,
                tool_calls=[],
                energy_wh=energy_wh,
                guardian_state=guardian_state,
                pii_masked=True,
                consent_scopes=["basic_logging"],
                rag_data={
                    "top_k": 0,
                    "hits": 0,
                    "llm_model": actual_model,
                    "planner_schema_ok": False,
                    "fallback_used": False,
                    "blocked_by_guardian": False,
                    "tokens_used": 0
                },
                input_text=chat_request.message,
                output_text=response_text,
                lang=getattr(chat_request, "lang", "sv"),
            )
        except Exception:
            pass
        
        return ChatResponse(
            session_id=chat_request.session_id,
            response=response_text,
            model_used=actual_model,
            latency_ms=latency_ms,
            trace_id=getattr(request.state, "trace_id", None),
            metadata={
                "phase": "2",
                "mock_response": False,
                "guardian_state": guardian_state,
                "route": route,
                "security": {"mode": security_mode, "inj": round(inj_score,2)}
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