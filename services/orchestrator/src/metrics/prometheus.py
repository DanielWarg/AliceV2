"""
Prometheus Metrics Exporter
Exports P50/P95 per route and error rates for monitoring
"""

from prometheus_client import Counter, Histogram, Gauge, generate_latest, CONTENT_TYPE_LATEST
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
import time
import structlog

logger = structlog.get_logger(__name__)

# Prometheus metrics
REQUEST_COUNT = Counter(
    "alice_orchestrator_requests_total",
    "Total number of requests",
    ["method", "endpoint", "status_code", "route"]
)

REQUEST_DURATION = Histogram(
    "alice_orchestrator_request_duration_seconds",
    "Request duration in seconds",
    ["method", "endpoint", "route"],
    buckets=[0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0]
)

ERROR_RATE = Counter(
    "alice_orchestrator_errors_total",
    "Total number of errors",
    ["method", "endpoint", "status_code", "route"]
)

GUARDIAN_STATE = Gauge(
    "alice_guardian_state",
    "Current Guardian system state",
    ["state"]
)

class PrometheusMiddleware(BaseHTTPMiddleware):
    """Middleware for collecting Prometheus metrics"""
    
    async def dispatch(self, request: Request, call_next):
        start_time = time.time()
        
        # Process request
        response = await call_next(request)
        
        # Calculate duration
        duration = time.time() - start_time
        
        # Extract route from response headers
        route = response.headers.get("X-Route", "unknown")
        
        # Record metrics
        REQUEST_COUNT.labels(
            method=request.method,
            endpoint=request.url.path,
            status_code=response.status_code,
            route=route
        ).inc()
        
        REQUEST_DURATION.labels(
            method=request.method,
            endpoint=request.url.path,
            route=route
        ).observe(duration)
        
        # Record errors (4xx and 5xx)
        if response.status_code >= 400:
            ERROR_RATE.labels(
                method=request.method,
                endpoint=request.url.path,
                status_code=response.status_code,
                route=route
            ).inc()
        
        return response

def update_guardian_state(state: str):
    """Update Guardian state metric"""
    # Reset all states to 0
    for guardian_state in ["NORMAL", "BROWNOUT", "EMERGENCY", "LOCKDOWN"]:
        GUARDIAN_STATE.labels(state=guardian_state).set(0)
    
    # Set current state to 1
    GUARDIAN_STATE.labels(state=state).set(1)

def get_metrics():
    """Get Prometheus metrics"""
    return generate_latest()

def get_metrics_response():
    """Get Prometheus metrics as FastAPI response"""
    return Response(
        content=generate_latest(),
        media_type=CONTENT_TYPE_LATEST
    )
