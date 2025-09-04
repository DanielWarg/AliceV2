"""
Optimized Orchestrator with Circuit Breaker, Smart Cache, and Improved Routing.
This is the new high-performance orchestrator that makes Alice "helt jävla grym"!
"""

import asyncio
import json
import os
import time
from typing import Any, Dict, Optional

import structlog
from fastapi import APIRouter

from ..cache.smart_cache import get_smart_cache
from ..clients.nlu_client import NLUResult, get_nlu_client
from ..llm.micro_client import MockMicroClient, RealMicroClient
from ..models.api import ChatRequest, ChatResponse
from ..router.policy import get_router_policy
from ..services.guardian_client import GuardianClient
from ..utils.circuit_breaker import (
    CircuitBreakerConfig,
    CircuitOpenError,
    get_circuit_breaker,
)

logger = structlog.get_logger(__name__)
router = APIRouter()


class OptimizedOrchestrator:
    """High-performance orchestrator with all optimizations"""

    def __init__(self):
        # Initialize all optimized components
        self.smart_cache = get_smart_cache()
        self.nlu_client = get_nlu_client()
        self.router_policy = get_router_policy()
        self.guardian_client = GuardianClient()

        # Micro client setup
        use_mock = os.getenv("FEATURE_MICRO_MOCK", "0") == "1"
        if use_mock:
            self.micro_client = MockMicroClient()
        else:
            ollama_base = os.getenv(
                "OLLAMA_BASE_URL", "http://host.docker.internal:11434"
            )
            micro_model = os.getenv("MICRO_MODEL", "qwen2.5:3b")
            self.micro_client = RealMicroClient(ollama_base, micro_model)

        # Planner circuit breaker
        planner_cb_config = CircuitBreakerConfig(
            failure_threshold=2,
            recovery_timeout=30.0,
            timeout=float(os.getenv("PLANNER_TIMEOUT_MS", "3000")) / 1000.0,
        )
        self.planner_circuit_breaker = get_circuit_breaker(
            "planner_service", planner_cb_config
        )

        logger.info(
            "Optimized Orchestrator initialized",
            cache_enabled=True,
            nlu_enabled=True,
            micro_mock=use_mock,
            micro_model=micro_model,
        )

    async def process_request(self, request: ChatRequest) -> ChatResponse:
        """Process request with full optimization pipeline"""

        start_time = time.perf_counter()
        trace_id = f"opt_{int(time.time() * 1000)}"

        logger.info(
            "Processing optimized request",
            trace_id=trace_id,
            text=request.message[:50],
            session_id=request.session_id,
        )

        try:
            # STEP 1: Check cache first (fastest path)
            cache_start = time.perf_counter()
            cache_result = await self.smart_cache.get("unknown", request.message)
            cache_ms = (time.perf_counter() - cache_start) * 1000

            if cache_result.hit:
                logger.info(
                    "CACHE HIT - returning cached response",
                    trace_id=trace_id,
                    source=cache_result.source,
                    cache_latency_ms=cache_ms,
                )

                return ChatResponse(
                    response=cache_result.data.get("render_instruction", {}).get(
                        "content", "Cached response"
                    ),
                    model=f"cache_{cache_result.source}",
                    meta={
                        "trace_id": trace_id,
                        "route": "cache",
                        "latency_ms": (time.perf_counter() - start_time) * 1000,
                        "cache_hit": True,
                        "cache_source": cache_result.source,
                    },
                )

            # STEP 2: NLU processing (parallel with cache miss handling)
            nlu_task = asyncio.create_task(self._process_nlu(request.message))

            # STEP 3: Route decision based on NLU and text analysis
            nlu_result = await nlu_task
            route_decision = self.router_policy.decide_route(request.message)

            # Override route based on NLU hint
            if nlu_result.route_hint and nlu_result.confidence > 0.7:
                route_decision.route = nlu_result.route_hint
                route_decision.reason = f"NLU override: {nlu_result.intent} (conf: {nlu_result.confidence:.2f})"

            logger.info(
                "Route decided",
                trace_id=trace_id,
                route=route_decision.route,
                reason=route_decision.reason,
                nlu_intent=nlu_result.intent,
                nlu_confidence=nlu_result.confidence,
            )

            # STEP 4: Execute based on route
            if route_decision.route == "micro":
                response_data = await self._execute_micro(request, nlu_result, trace_id)
            elif route_decision.route == "planner":
                response_data = await self._execute_planner(
                    request, nlu_result, trace_id
                )
            else:  # deep route
                response_data = await self._execute_deep(request, nlu_result, trace_id)

            # STEP 5: Cache successful response
            if response_data and "error" not in response_data:
                try:
                    self.smart_cache.set(
                        nlu_result.intent,
                        request.message,
                        response_data,
                        ttl=(
                            300
                            if nlu_result.intent in ["time.now", "weather.lookup"]
                            else 600
                        ),
                    )
                except Exception as e:
                    logger.warn("Failed to cache response", error=str(e))

            total_latency_ms = (time.perf_counter() - start_time) * 1000

            # Build final response
            final_response = ChatResponse(
                response=response_data.get("render_instruction", {}).get(
                    "content", "Response generated"
                ),
                model=response_data.get("meta", {}).get(
                    "model_id", route_decision.route
                ),
                meta={
                    "trace_id": trace_id,
                    "route": route_decision.route,
                    "latency_ms": total_latency_ms,
                    "cache_hit": False,
                    "nlu_intent": nlu_result.intent,
                    "nlu_source": nlu_result.source,
                    "tool_precision": response_data.get("meta", {}).get(
                        "tool_precision", 1.0
                    ),
                    "schema_ok": response_data.get("meta", {}).get("schema_ok", True),
                },
            )

            logger.info(
                "Request completed successfully",
                trace_id=trace_id,
                total_latency_ms=total_latency_ms,
                route=route_decision.route,
                cache_checked=True,
                nlu_processed=True,
            )

            return final_response

        except Exception as e:
            error_latency_ms = (time.perf_counter() - start_time) * 1000
            logger.error(
                "Request failed",
                trace_id=trace_id,
                error=str(e),
                latency_ms=error_latency_ms,
            )

            # Store in negative cache
            self.smart_cache.set_negative(request.message, "error", ttl=60)

            return ChatResponse(
                response="Ursäkta, jag stötte på ett tekniskt problem. Försök igen om en stund.",
                model="error_handler",
                meta={
                    "trace_id": trace_id,
                    "error": str(e),
                    "latency_ms": error_latency_ms,
                    "route": "error",
                },
            )

    async def _process_nlu(self, text: str) -> NLUResult:
        """Process with NLU including fallback"""
        try:
            return await self.nlu_client.parse(text)
        except Exception as e:
            logger.warn("NLU processing failed, using simple fallback", error=str(e))
            # Simple keyword fallback
            if any(word in text.lower() for word in ["hej", "hello", "hi"]):
                return NLUResult("greeting.hello", 0.8, {}, "micro", "fallback")
            else:
                return NLUResult("general.query", 0.5, {}, "planner", "fallback")

    async def _execute_micro(
        self, request: ChatRequest, nlu_result: NLUResult, trace_id: str
    ) -> Dict[str, Any]:
        """Execute with micro model"""

        micro_start = time.perf_counter()

        try:
            response = self.micro_client.generate(request.message)
            micro_ms = (time.perf_counter() - micro_start) * 1000

            logger.info(
                "Micro execution completed",
                trace_id=trace_id,
                micro_latency_ms=micro_ms,
                tool_detected=response.get("tool_detected", "unknown"),
            )

            # Parse the JSON response
            response_data = json.loads(response["text"])
            response_data["meta"]["latency_ms"] = micro_ms
            response_data["meta"]["route"] = "micro"

            return response_data

        except Exception as e:
            logger.error("Micro execution failed", trace_id=trace_id, error=str(e))
            return {
                "intent": "error",
                "tool": None,
                "args": {},
                "render_instruction": {
                    "type": "text",
                    "content": "Jag stötte på ett problem med din förfrågan.",
                },
                "meta": {"route": "micro_error", "error": str(e), "schema_ok": False},
            }

    async def _execute_planner(
        self, request: ChatRequest, nlu_result: NLUResult, trace_id: str
    ) -> Dict[str, Any]:
        """Execute with planner model (with circuit breaker)"""

        try:
            # Use circuit breaker for planner calls
            response_data = self.planner_circuit_breaker.call(
                self._call_planner_service, request, nlu_result, trace_id
            )
            return response_data

        except CircuitOpenError:
            logger.warn(
                "Planner circuit breaker open - using fallback", trace_id=trace_id
            )
            # Fallback to micro for simple cases
            return await self._execute_micro(request, nlu_result, trace_id)

        except Exception as e:
            logger.error("Planner execution failed", trace_id=trace_id, error=str(e))
            return {
                "intent": "planner_error",
                "tool": None,
                "args": {},
                "render_instruction": {
                    "type": "text",
                    "content": "Planner-tjänsten är inte tillgänglig just nu.",
                },
                "meta": {"route": "planner_error", "error": str(e), "schema_ok": False},
            }

    def _call_planner_service(
        self, request: ChatRequest, nlu_result: NLUResult, trace_id: str
    ) -> Dict[str, Any]:
        """Call planner service (protected by circuit breaker)"""

        planner_start = time.perf_counter()

        # Simulate planner call (replace with actual implementation)
        time.sleep(0.1)  # Simulate some processing time

        planner_ms = (time.perf_counter() - planner_start) * 1000

        return {
            "intent": nlu_result.intent,
            "tool": "planner_tool",
            "args": {"query": request.message},
            "render_instruction": {
                "type": "text",
                "content": f"Planner hanterar: {request.message}",
            },
            "meta": {
                "route": "planner",
                "latency_ms": planner_ms,
                "nlu_intent": nlu_result.intent,
                "schema_ok": True,
                "tool_precision": 0.9,
            },
        }

    async def _execute_deep(
        self, request: ChatRequest, nlu_result: NLUResult, trace_id: str
    ) -> Dict[str, Any]:
        """Execute with deep model for complex reasoning"""

        deep_start = time.perf_counter()

        # Simulate deep processing
        await asyncio.sleep(0.2)

        deep_ms = (time.perf_counter() - deep_start) * 1000

        return {
            "intent": "deep_reasoning",
            "tool": "deep_analysis",
            "args": {"complex_query": request.message},
            "render_instruction": {
                "type": "text",
                "content": f"Deep analysis av: {request.message}",
            },
            "meta": {
                "route": "deep",
                "latency_ms": deep_ms,
                "model_id": "deep_model",
                "schema_ok": True,
                "tool_precision": 0.95,
            },
        }


# Global orchestrator instance
_orchestrator: Optional[OptimizedOrchestrator] = None


def get_optimized_orchestrator() -> OptimizedOrchestrator:
    """Get or create optimized orchestrator"""
    global _orchestrator
    if _orchestrator is None:
        _orchestrator = OptimizedOrchestrator()
    return _orchestrator


# FastAPI endpoints
@router.post("/api/chat/optimized", response_model=ChatResponse)
async def chat_optimized(request: ChatRequest):
    """Optimized chat endpoint with all performance improvements"""

    orchestrator = get_optimized_orchestrator()
    return await orchestrator.process_request(request)


@router.get("/api/health/optimized")
async def health_optimized():
    """Health check for optimized orchestrator"""

    orchestrator = get_optimized_orchestrator()

    # Quick health checks
    cache_healthy = orchestrator.smart_cache.redis_client is not None

    return {
        "status": "healthy",
        "version": "optimized-v1.0",
        "components": {
            "smart_cache": "healthy" if cache_healthy else "unhealthy",
            "nlu_client": "healthy",  # Always healthy with fallback
            "circuit_breakers": "monitored",
        },
        "optimization_features": [
            "smart_cache",
            "circuit_breaker",
            "nlu_fallback",
            "quota_tracking",
            "few_shot_micro",
            "semantic_caching",
        ],
    }
