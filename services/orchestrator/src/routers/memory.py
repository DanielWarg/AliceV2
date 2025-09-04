"""
Memory endpoints for orchestrator
"""

import time
from typing import Any, Dict, List, Optional

import structlog
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from ..clients.memory_client import MemoryClient, get_memory_client
from ..routers.orchestrator import log_turn_event
from ..services.guardian_client import GuardianClient
from ..utils.energy import EnergyMeter
from ..utils.ram_peak import ram_peak_mb
from ..utils.tool_errors import classify_tool_error, record_tool_call

logger = structlog.get_logger(__name__)
router = APIRouter(prefix="/api/memory", tags=["memory"])

# Guardian client instance
guardian_client = GuardianClient()


async def get_guardian_client() -> GuardianClient:
    """Dependency to get Guardian client"""
    return guardian_client


# Pydantic models
class StoreMemoryRequest(BaseModel):
    user_id: str = Field(..., description="User identifier")
    session_id: str = Field(..., description="Session identifier")
    text: str = Field(..., description="Text to store")
    metadata: Dict[str, Any] = Field(
        default_factory=dict, description="Additional metadata"
    )
    consent_scopes: List[str] = Field(
        default_factory=lambda: ["basic_logging"], description="Consent scopes"
    )


class QueryMemoryRequest(BaseModel):
    user_id: str = Field(..., description="User identifier")
    query: str = Field(..., description="Query text")
    top_k: int = Field(default=3, description="Number of top results to return")
    min_score: float = Field(default=0.6, description="Minimum similarity score")


class ForgetMemoryRequest(BaseModel):
    user_id: str = Field(..., description="User identifier")
    session_id: Optional[str] = Field(
        None, description="Specific session to forget (optional)"
    )


class MemoryResponse(BaseModel):
    success: bool = Field(..., description="Operation success status")
    data: Dict[str, Any] = Field(..., description="Response data")
    query_time_ms: float = Field(
        ..., description="Query execution time in milliseconds"
    )


@router.post("/store", response_model=MemoryResponse)
async def store_memory(
    request: StoreMemoryRequest,
    memory_client: MemoryClient = Depends(get_memory_client),
    guardian: GuardianClient = Depends(get_guardian_client),
):
    """Store a memory chunk"""
    start_time = time.time()
    trace_id = f"memory-store-{int(start_time * 1000)}"
    energy_meter = EnergyMeter()
    tool_calls = []

    try:
        # Store memory
        result = await memory_client.store_memory(
            user_id=request.user_id,
            session_id=request.session_id,
            text=request.text,
            metadata=request.metadata,
            consent_scopes=request.consent_scopes,
        )

        # Calculate metrics
        query_time = (time.time() - start_time) * 1000
        ram_peak = ram_peak_mb()
        energy_wh = energy_meter.stop()

        # Record tool call
        tool_call_result = record_tool_call(
            tool_name="memory.store",
            success=True,
            error_class=None,
            latency_ms=query_time,
        )
        tool_calls.append(tool_call_result)

        # Log turn event
        try:
            log_turn_event(
                trace_id=trace_id,
                session_id=request.session_id,
                route="memory",
                e2e_first_ms=query_time,
                e2e_full_ms=query_time,
                ram_peak=ram_peak,
                tool_calls=tool_calls,
                energy_wh=energy_wh,
                guardian_state="NORMAL",
                pii_masked=True,
                consent_scopes=request.consent_scopes,
                rag_data={
                    "top_k": 0,
                    "hits": 0,
                    "llm_model": "memory",
                    "planner_schema_ok": False,
                    "fallback_used": False,
                    "blocked_by_guardian": False,
                    "tokens_used": 0,
                },
                input_text=request.text,
                output_text="Memory stored successfully",
                lang="sv",
            )
        except Exception as log_error:
            logger.error("Failed to log turn event", error=str(log_error))

        logger.info(
            "Memory store completed",
            user_id=request.user_id,
            session_id=request.session_id,
            chunk_id=result.get("chunk_id"),
            query_time_ms=query_time,
        )

        return MemoryResponse(success=True, data=result, query_time_ms=query_time)

    except Exception as e:
        query_time = (time.time() - start_time) * 1000
        energy_wh = energy_meter.stop()

        # Record error as tool call
        error_class = classify_tool_error(None, e)
        tool_call_result = record_tool_call(
            tool_name="memory.store",
            success=False,
            error_class=error_class,
            latency_ms=query_time,
        )
        tool_calls.append(tool_call_result)

        logger.error(
            "Memory store failed",
            user_id=request.user_id,
            session_id=request.session_id,
            error=str(e),
            query_time_ms=query_time,
        )

        raise HTTPException(status_code=500, detail=f"Failed to store memory: {str(e)}")


@router.post("/query", response_model=MemoryResponse)
async def query_memory(
    request: QueryMemoryRequest,
    memory_client: MemoryClient = Depends(get_memory_client),
    guardian: GuardianClient = Depends(get_guardian_client),
):
    """Query memory using semantic search"""
    start_time = time.time()
    trace_id = f"memory-query-{int(start_time * 1000)}"
    energy_meter = EnergyMeter()
    tool_calls = []

    try:
        # Query memory
        result = await memory_client.query_memory(
            user_id=request.user_id,
            query=request.query,
            top_k=request.top_k,
            min_score=request.min_score,
        )

        # Calculate metrics
        query_time = (time.time() - start_time) * 1000
        ram_peak = ram_peak_mb()
        energy_wh = energy_meter.stop()

        # Record tool call
        tool_call_result = record_tool_call(
            tool_name="memory.query",
            success=True,
            error_class=None,
            latency_ms=query_time,
        )
        tool_calls.append(tool_call_result)

        # Log turn event
        try:
            log_turn_event(
                trace_id=trace_id,
                session_id=request.user_id,  # Use user_id as session_id for memory queries
                route="memory",
                e2e_first_ms=query_time,
                e2e_full_ms=query_time,
                ram_peak=ram_peak,
                tool_calls=tool_calls,
                energy_wh=energy_wh,
                guardian_state="NORMAL",
                pii_masked=True,
                consent_scopes=["basic_logging"],
                rag_data={
                    "top_k": result.get("total_hits", 0),
                    "hits": result.get("total_hits", 0),
                    "llm_model": "memory",
                    "planner_schema_ok": False,
                    "fallback_used": False,
                    "blocked_by_guardian": False,
                    "tokens_used": 0,
                },
                input_text=request.query,
                output_text=f"Found {result.get('total_hits', 0)} memory chunks",
                lang="sv",
            )
        except Exception as log_error:
            logger.error("Failed to log turn event", error=str(log_error))

        logger.info(
            "Memory query completed",
            user_id=request.user_id,
            query=request.query,
            total_hits=result.get("total_hits", 0),
            query_time_ms=query_time,
        )

        return MemoryResponse(success=True, data=result, query_time_ms=query_time)

    except Exception as e:
        query_time = (time.time() - start_time) * 1000
        energy_wh = energy_meter.stop()

        # Record error as tool call
        error_class = classify_tool_error(None, e)
        tool_call_result = record_tool_call(
            tool_name="memory.query",
            success=False,
            error_class=error_class,
            latency_ms=query_time,
        )
        tool_calls.append(tool_call_result)

        logger.error(
            "Memory query failed",
            user_id=request.user_id,
            query=request.query,
            error=str(e),
            query_time_ms=query_time,
        )

        raise HTTPException(status_code=500, detail=f"Failed to query memory: {str(e)}")


@router.post("/forget", response_model=MemoryResponse)
async def forget_memory(
    request: ForgetMemoryRequest,
    memory_client: MemoryClient = Depends(get_memory_client),
    guardian: GuardianClient = Depends(get_guardian_client),
):
    """Forget user memory (GDPR compliance)"""
    start_time = time.time()
    trace_id = f"memory-forget-{int(start_time * 1000)}"
    energy_meter = EnergyMeter()
    tool_calls = []

    try:
        # Forget memory
        result = await memory_client.forget_memory(
            user_id=request.user_id, session_id=request.session_id
        )

        # Calculate metrics
        query_time = (time.time() - start_time) * 1000
        ram_peak = ram_peak_mb()
        energy_wh = energy_meter.stop()

        # Record tool call
        tool_call_result = record_tool_call(
            tool_name="memory.forget",
            success=True,
            error_class=None,
            latency_ms=query_time,
        )
        tool_calls.append(tool_call_result)

        # Log turn event
        try:
            log_turn_event(
                trace_id=trace_id,
                session_id=request.user_id,  # Use user_id as session_id for memory operations
                route="memory",
                e2e_first_ms=query_time,
                e2e_full_ms=query_time,
                ram_peak=ram_peak,
                tool_calls=tool_calls,
                energy_wh=energy_wh,
                guardian_state="NORMAL",
                pii_masked=True,
                consent_scopes=["basic_logging"],
                rag_data={
                    "top_k": 0,
                    "hits": 0,
                    "llm_model": "memory",
                    "planner_schema_ok": False,
                    "fallback_used": False,
                    "blocked_by_guardian": False,
                    "tokens_used": 0,
                },
                input_text=f"Forget memory for user {request.user_id}",
                output_text=f"Forgot {result.get('deleted_count', 0)} memory chunks",
                lang="sv",
            )
        except Exception as log_error:
            logger.error("Failed to log turn event", error=str(log_error))

        logger.info(
            "Memory forget completed",
            user_id=request.user_id,
            session_id=request.session_id,
            deleted_count=result.get("deleted_count", 0),
            query_time_ms=query_time,
        )

        return MemoryResponse(success=True, data=result, query_time_ms=query_time)

    except Exception as e:
        query_time = (time.time() - start_time) * 1000
        energy_wh = energy_meter.stop()

        # Record error as tool call
        error_class = classify_tool_error(None, e)
        tool_call_result = record_tool_call(
            tool_name="memory.forget",
            success=False,
            error_class=error_class,
            latency_ms=query_time,
        )
        tool_calls.append(tool_call_result)

        logger.error(
            "Memory forget failed",
            user_id=request.user_id,
            session_id=request.session_id,
            error=str(e),
            query_time_ms=query_time,
        )

        raise HTTPException(
            status_code=500, detail=f"Failed to forget memory: {str(e)}"
        )


@router.get("/stats")
async def get_memory_stats(memory_client: MemoryClient = Depends(get_memory_client)):
    """Get memory service statistics"""
    try:
        stats = await memory_client.get_stats()

        logger.info(
            "Memory stats retrieved",
            total_chunks=stats.get("total_chunks", 0),
            users=stats.get("users", 0),
        )

        return {"success": True, "data": stats}

    except Exception as e:
        logger.error("Failed to get memory stats", error=str(e))
        raise HTTPException(
            status_code=500, detail=f"Failed to get memory stats: {str(e)}"
        )


@router.get("/health")
async def memory_health_check(memory_client: MemoryClient = Depends(get_memory_client)):
    """Check memory service health"""
    try:
        is_healthy = await memory_client.health_check()

        if is_healthy:
            return {"status": "healthy", "service": "memory"}
        else:
            raise HTTPException(status_code=503, detail="Memory service unhealthy")

    except Exception as e:
        logger.error("Memory health check failed", error=str(e))
        raise HTTPException(
            status_code=503, detail=f"Memory service health check failed: {str(e)}"
        )
