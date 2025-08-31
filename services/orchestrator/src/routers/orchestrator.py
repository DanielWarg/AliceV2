"""
Orchestrator API Router
Handles LLM routing and ingestion requests with LLM integration v1
"""

from fastapi import APIRouter, HTTPException, Request, Response, Depends
import httpx
import structlog
import time
import json
import os
from typing import Dict, Any, List
from datetime import datetime

from ..models.api import IngestRequest, IngestResponse, APIError, ModelType, ChatRequest, ChatResponse
from ..services.guardian_client import GuardianClient
from ..middleware.logging import get_logger_with_trace
from ..utils.ram_peak import ram_peak_mb
from ..utils.energy import EnergyMeter
from ..utils.tool_errors import record_tool_call, classify_tool_error

# LLM Integration v1 imports
from ..llm import get_micro_driver, get_planner_driver, get_deep_driver
from ..router import get_router_policy
from ..planner import get_planner_executor

router = APIRouter()

# Global Guardian client (will be injected)
guardian_client = GuardianClient()

async def get_guardian_client() -> GuardianClient:
    """Dependency to get Guardian client"""
    return guardian_client

def log_turn_event(
    trace_id: str,
    session_id: str,
    route: str,
    e2e_first_ms: int,
    e2e_full_ms: int,
    ram_peak: Dict[str, float],
    tool_calls: List[Dict[str, Any]],
    energy_wh: float,
    guardian_state: str,
    pii_masked: bool = True,
    consent_scopes: List[str] = None,
    rag_data: Dict[str, Any] = None,
    input_text: str | None = None,
    output_text: str | None = None,
    lang: str | None = None,
) -> None:
    """Logga komplett turn event enligt observability standard"""
    
    logger = structlog.get_logger(__name__)
    logger.info("log_turn_event called", trace_id=trace_id, session_id=session_id)
    
    turn_event = {
        "v": "1",
        "ts": datetime.utcnow().isoformat() + "Z",
        "trace_id": trace_id,
        "session_id": session_id,
        "route": route,
        "e2e_first_ms": e2e_first_ms,
        "e2e_full_ms": e2e_full_ms,
        "ram_peak_mb": ram_peak,
        "tool_calls": tool_calls,
        "rag": rag_data or {"top_k": 0, "hits": 0},
        "energy_wh": energy_wh,
        "guardian_state": guardian_state,
        "pii_masked": pii_masked,
        "consent_scopes": consent_scopes or ["basic_logging"],
        "input_text": input_text,
        "output_text": output_text,
        "lang": lang or "sv",
    }
    
    # Skriv till JSONL fil
    try:
        # Använd konfigurerad katalog (monteras i Docker via LOG_DIR)
        telemetry_dir = os.getenv("LOG_DIR", "/data/telemetry")
        logger.info("Telemetry dir", telemetry_dir=telemetry_dir)
        os.makedirs(telemetry_dir, exist_ok=True)
        
        today = datetime.utcnow().strftime("%Y-%m-%d")
        filename = os.path.join(telemetry_dir, f"events_{today}.jsonl")
        logger.info("Writing to file", filename=filename)
        
        with open(filename, "a", encoding="utf-8") as f:
            f.write(json.dumps(turn_event) + "\n")
        
        logger.info("Turn event written successfully")
            
    except Exception as e:
        # Fallback till logging om filskrivning misslyckas
        logger.error("Failed to write turn event to JSONL", error=str(e), turn_event=turn_event)

def route_request(request) -> str:
    """
    LLM Integration v1 routing logic: Choose between micro, planner, deep
    
    Routes based on:
    - Text analysis and pattern matching
    - Guardian system state
    - Message complexity and length
    
    Args:
        request: IngestRequest or ChatRequest to route
        
    Returns:
        Route string: "micro", "planner", or "deep"
    """
    # Handle both IngestRequest (text) and ChatRequest (message)
    text = getattr(request, 'text', None) or getattr(request, 'message', '')
    
    router_policy = get_router_policy()
    route_decision = router_policy.decide_route(text)
    
    # Log routing decision if enabled
    if os.getenv("ROUTER_LOG_DECISION", "true").lower() == "true":
        logger = structlog.get_logger(__name__)
        logger.info("Route decision", 
                   route=route_decision.route,
                   confidence=route_decision.confidence,
                   reason=route_decision.reason,
                   text_length=len(text))
    
    return route_decision.route

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

def calculate_priority(request, guardian_health: Dict[str, Any]) -> int:
    """
    Calculate request priority (1-10, where 10 is highest)
    
    Args:
        request: IngestRequest or ChatRequest
        guardian_health: Guardian system health data
        
    Returns:
        Priority score 1-10
    """
    base_priority = 5  # Default priority
    
    # Handle both IngestRequest (text) and ChatRequest (message)
    text = getattr(request, 'text', None) or getattr(request, 'message', '')
    
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
    if len(text) < 100:
        priority_modifier += 1
    
    return max(1, min(10, base_priority + priority_modifier))

@router.post("/ingest", response_model=IngestResponse)
async def orchestrator_ingest(
    request: Request,
    response: Response,
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
        
        # Set route header for metrics middleware
        route_name = {
            ModelType.MICRO: "micro",
            ModelType.PLANNER: "planner", 
            ModelType.DEEP: "deep"
        }.get(routed_model, "other")
        
        response.headers["X-Route"] = route_name
        
        # Build response
        response_data = IngestResponse(
            session_id=ingest_request.session_id,
            accepted=True,
            model=routed_model,
            priority=priority,
            estimated_latency_ms=estimated_latency,
            reason=routing_reason,
            trace_id=getattr(request.state, "trace_id", None)
        )
        
        return response_data
        
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
                "phase": "llm_integration_v1",
                "available_models": ["micro", "planner", "deep"],
                "routing_logic": "intelligent_routing",
                "guardian_integration": True,
                "llm_drivers": {
                    "micro": "phi3.5:mini",
                    "planner": "qwen2.5:7b-moe", 
                    "deep": "llama3.1:8b"
                }
            },
            "guardian_status": guardian_health.get("state", "unknown"),
            "features": {
                "admission_control": True,
                "priority_calculation": True,
                "latency_estimation": True,
                "metrics_reporting": True,
                "llm_integration": True,
                "planner_execution": True,
                "fallback_matrix": True
            }
        }
    except Exception as e:
        return {
            "service": "orchestrator", 
            "status": "degraded",
            "error": str(e),
            "guardian_status": "error"
        }

@router.post("/chat")
async def orchestrator_chat(
    request: Request,
    response: Response,
    chat_request: ChatRequest,
    guardian: GuardianClient = Depends(get_guardian_client)
) -> ChatResponse:
    """
    Chat completion endpoint
    
    Processes chat messages and returns AI responses.
    Phase 1: Always routes to micro model with Guardian protection.
    """
    logger = get_logger_with_trace(request, __name__)
    start_time = time.time()
    
    # Start energy meter
    energy_meter = EnergyMeter()
    energy_meter.start()
    
    # Get trace ID for observability
    trace_id = getattr(request.state, "trace_id", "unknown")
    
    logger.info(
        "Orchestrator chat request",
        session_id=chat_request.session_id,
        message_length=len(chat_request.message),
        preferred_model=chat_request.model,
        trace_id=trace_id
    )
    
    # Track tool calls
    tool_calls: List[Dict[str, Any]] = []
    
    try:
        # --- NLU pre-parse (fail-open) ---
        nlu_route_hint = None
        nlu_intent_label = None
        nlu_slots = None
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
                    nlu_route_hint = nlu_json.get("route_hint")
                    intent = (nlu_json.get("intent") or {})
                    nlu_intent_label = intent.get("label")
                    nlu_slots = nlu_json.get("slots") or {}
                    if nlu_intent_label:
                        response.headers["X-Intent"] = nlu_intent_label
                    if nlu_route_hint:
                        response.headers["X-Route-Hint"] = nlu_route_hint
        except Exception as nlu_err:
            logger.warning("NLU parse failed or timed out", error=str(nlu_err))
        # Get Guardian health status
        try:
            guardian_health = await guardian.get_health()
            guardian_state = guardian_health.get("state", "UNKNOWN")
            logger.info("Guardian health received", state=guardian_state)
        except Exception as e:
            logger.error("Guardian health check failed", error=str(e))
            guardian_health = {"state": "ERROR"}
            guardian_state = "ERROR"
        
        # Check admission control
        try:
            admitted = await guardian.check_admission({
                "type": "chat",
                "session_id": chat_request.session_id,
                "message_length": len(chat_request.message),
                "preferred_model": chat_request.model
            })
        except Exception as e:
            logger.error("Admission control failed", error=str(e))
            admitted = True  # Fail-open
        
        if not admitted:
            retry_after = guardian.get_retry_after_seconds(guardian_health)
            
            logger.warning(
                "Chat request blocked by Guardian",
                session_id=chat_request.session_id,
                guardian_state=guardian_state,
                retry_after=retry_after
            )
            
            raise HTTPException(
                status_code=429,
                detail=APIError.create(
                    code="RATE_LIMITED",
                    message="Too many requests, please try again later",
                    retry_after=retry_after,
                    trace_id=trace_id
                ).model_dump(),
                headers={"Retry-After": str(retry_after)}
            )
        
        # Route to appropriate model using LLM Integration v1 (+ NLU hint)
        route = route_request(chat_request)
        if nlu_route_hint in {"micro", "planner", "deep"}:
            route = nlu_route_hint
        logger.info("Route selected", route=route)
        
        # Generate response based on route
        llm_response = None
        planner_execution = None
        fallback_used = False
        blocked_by_guardian = False
        
        try:
            if route == "micro":
                micro_driver = get_micro_driver()
                llm_response = micro_driver.generate(chat_request.message)
                model_used = llm_response["model"]
                
            elif route == "planner":
                planner_driver = get_planner_driver()
                llm_response = planner_driver.generate(chat_request.message)
                model_used = llm_response["model"]
                
                # Execute plan if JSON was parsed successfully
                if llm_response.get("json_parsed") and llm_response.get("plan"):
                    planner_executor = get_planner_executor()
                    plan = planner_executor.validate_plan(llm_response["plan"])
                    if plan:
                        planner_execution = planner_executor.execute_plan(plan)
                        fallback_used = planner_execution.get("fallback_used", False)
                        
                        # Record tool calls from plan execution
                        for step_result in planner_execution.get("executed_steps", []):
                            tool_call_result = record_tool_call(
                                tool_name=step_result["tool"],
                                success=step_result["success"],
                                error_class=step_result.get("klass"),
                                latency_ms=step_result["latency_ms"]
                            )
                            tool_calls.append(tool_call_result)
                
            elif route == "deep":
                deep_driver = get_deep_driver()
                llm_response = deep_driver.generate(chat_request.message)
                model_used = llm_response["model"]
                blocked_by_guardian = llm_response.get("blocked_by_guardian", False)
                fallback_used = llm_response.get("fallback_used", False)
                
            else:
                # Fallback to micro for unknown routes
                micro_driver = get_micro_driver()
                llm_response = micro_driver.generate(chat_request.message)
                model_used = llm_response["model"]
                fallback_used = True
                
        except Exception as llm_error:
            logger.error("LLM generation failed", route=route, error=str(llm_error))
            # Fallback to micro
            try:
                micro_driver = get_micro_driver()
                llm_response = micro_driver.generate(chat_request.message)
                model_used = llm_response["model"]
                fallback_used = True
            except Exception as fallback_error:
                logger.error("Fallback to micro also failed", error=str(fallback_error))
                raise llm_error
        
        # Get RAM peak and energy consumption
        ram_peak = ram_peak_mb()
        energy_wh = energy_meter.stop()
        
        # Calculate response latency
        response_latency_ms = int((time.time() - start_time) * 1000)
        
        logger.info(
            "Orchestrator chat completed",
            session_id=chat_request.session_id,
            model_used=model_used,
            response_latency_ms=response_latency_ms,
            ram_peak_mb=ram_peak,
            energy_wh=energy_wh,
            tool_calls_count=len(tool_calls),
            guardian_state=guardian_state
        )
        
        # Log turn event for observability with LLM integration data
        logger.info("About to log turn event", session_id=chat_request.session_id)
        log_turn_event(
            trace_id=trace_id,
            session_id=chat_request.session_id,
            route=route,
            e2e_first_ms=response_latency_ms,
            e2e_full_ms=response_latency_ms,
            ram_peak_mb=ram_peak,
            tool_calls=tool_calls,
            energy_wh=energy_wh,
            guardian_state=guardian_state,
            pii_masked=True,
            consent_scopes=["basic_logging"],
            rag_data={
                "top_k": 0,
                "hits": 0,
                "llm_model": model_used,
                "planner_schema_ok": llm_response.get("json_parsed", False) if llm_response else False,
                "fallback_used": fallback_used,
                "blocked_by_guardian": blocked_by_guardian,
                "tokens_used": llm_response.get("tokens_used", 0) if llm_response else 0
            },
            input_text=chat_request.message,
            output_text=(llm_response or {}).get("text", ""),
            lang=(getattr(chat_request, "lang", None) or "sv"),
        )
        logger.info("Turn event logged successfully", trace_id=trace_id)
        
        # Set route header for metrics middleware
        response.headers["X-Route"] = route
        
        # Build response with LLM integration
        if llm_response:
            response_text = llm_response["text"]
        else:
            response_text = f"LLM response not available for route {route}"
        
        # Add metadata for observability
        metadata = {
            "route": route,
            "llm_model": model_used,
            "planner_schema_ok": llm_response.get("json_parsed", False) if llm_response else False,
            "fallback_used": fallback_used,
            "blocked_by_guardian": blocked_by_guardian,
            "tokens_used": llm_response.get("tokens_used", 0) if llm_response else 0,
            "planner_execution": planner_execution,
            "nlu": {"intent": nlu_intent_label, "slots": nlu_slots} if (nlu_intent_label or nlu_slots) else None,
        }
        
        response_data = ChatResponse(
            session_id=chat_request.session_id,
            timestamp=int(time.time() * 1000),
            trace_id=trace_id,
            response=response_text,
            model_used=model_used,
            latency_ms=response_latency_ms,
            metadata=metadata
        )
        
        return response_data
        
    except HTTPException:
        raise
    except Exception as e:
        energy_wh = energy_meter.stop()
        response_latency_ms = int((time.time() - start_time) * 1000)
        
        # Record error as tool call
        error_class = classify_tool_error(None, e)
        tool_call_result = record_tool_call(
            tool_name="orchestrator.chat",
            success=False,
            error_class=error_class,
            latency_ms=response_latency_ms
        )
        tool_calls.append(tool_call_result)
        
        # Log turn event even on error
        try:
            log_turn_event(
                trace_id=trace_id,
                session_id=chat_request.session_id,
                route="error",
                e2e_first_ms=response_latency_ms,
                e2e_full_ms=response_latency_ms,
                ram_peak_mb=ram_peak_mb(),
                tool_calls=tool_calls,
                energy_wh=energy_wh,
                guardian_state=guardian_state
            )
        except Exception as log_error:
            logger.error("Failed to log turn event on error", error=str(log_error))
        
        logger.error(
            "Orchestrator chat failed",
            session_id=chat_request.session_id,
            error=str(e),
            response_latency_ms=response_latency_ms,
            exc_info=True
        )
        
        raise HTTPException(
            status_code=500,
            detail=APIError.create(
                code="INTERNAL_ERROR",
                message="An internal error occurred while processing chat request",
                details=str(e) if str(e) else "Unknown error",
                trace_id=trace_id
            ).model_dump()
        )

@router.post("/run")
async def orchestrator_run(
    request: Request,
    response: Response,
    ingest_request: IngestRequest,
    guardian: GuardianClient = Depends(get_guardian_client)
) -> IngestResponse:
    """
    Run endpoint - alias for /ingest for compatibility
    
    This endpoint provides the same functionality as /ingest
    but with a more intuitive name for execution requests.
    """
    # Delegate to the main ingest endpoint
    return await orchestrator_ingest(request, response, ingest_request, guardian)

@router.get("/tools")
async def orchestrator_tools(
    guardian: GuardianClient = Depends(get_guardian_client)
):
    """
    Get available tools and their status
    
    Returns information about available tools, their health,
    and current capabilities based on Guardian state.
    """
    try:
        guardian_health = await guardian.get_health()
        
        # Phase 1: Basic tool registry
        available_tools = {
            "micro_llm": {
                "name": "Micro LLM",
                "type": "text_generation",
                "status": "available",
                "model": "phi-3.5-mini",
                "capabilities": ["simple_qa", "basic_conversation", "swedish_support"],
                "guardian_restrictions": []
            },
            "planner_llm": {
                "name": "Planner LLM", 
                "type": "text_generation",
                "status": "planned",
                "model": "qwen2.5-moe",
                "capabilities": ["planning", "tool_use", "complex_reasoning"],
                "guardian_restrictions": ["requires_normal_state"]
            },
            "deep_llm": {
                "name": "Deep LLM",
                "type": "text_generation", 
                "status": "planned",
                "model": "llama-3.1",
                "capabilities": ["deep_analysis", "research", "creative_writing"],
                "guardian_restrictions": ["requires_normal_state", "low_memory_usage"]
            }
        }
        
        # Apply Guardian state restrictions
        guardian_state = guardian_health.get("state", "NORMAL")
        if guardian_state in ["BROWNOUT", "EMERGENCY"]:
            # Restrict to micro only during resource pressure
            available_tools["planner_llm"]["status"] = "restricted"
            available_tools["deep_llm"]["status"] = "restricted"
            available_tools["micro_llm"]["guardian_restrictions"].append("only_available_model")
        
        return {
            "service": "orchestrator",
            "status": "healthy",
            "guardian_state": guardian_state,
            "available_tools": available_tools,
            "phase": "1",
            "total_tools": len(available_tools)
        }
        
    except Exception as e:
        return {
            "service": "orchestrator",
            "status": "degraded", 
            "error": str(e),
            "available_tools": {},
            "guardian_state": "unknown"
        }