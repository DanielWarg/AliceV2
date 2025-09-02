#!/usr/bin/env python3
"""
Alice v2 Orchestrator Service
Main FastAPI application entry point - production-ready with operational polish
"""

from fastapi import FastAPI, Request, HTTPException, Response
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import structlog
import httpx
from typing import AsyncGenerator

from src.routers import chat, orchestrator, status, feedback, learn, memory
from src.security.router import router as security_router
from src.middleware.logging import setup_logging, LoggingMiddleware
from src.services.guardian_client import GuardianClient
from src.mw_metrics import MetricsMiddleware
from src.status_router import router as fix_status_router
from src.health import check_readiness, check_liveness, wait_for_readiness
from src.shutdown import shutdown_manager, setup_signal_handlers, request_context, shutdown_app
from src.privacy import privacy_manager
from src.security.policy import load_policy
from src.security.metrics import set_mode

# Setup structured logging
setup_logging()
logger = structlog.get_logger(__name__)

# Global Guardian client
guardian_client = GuardianClient()

@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan management with graceful shutdown"""
    try:
        # Setup signal handlers
        setup_signal_handlers()
        
        logger.info("Alice v2 Orchestrator starting up", version="1.0.0")
        
        # Initialize Guardian client
        await guardian_client.initialize()
        
        # Wait for readiness
        ready = await wait_for_readiness(timeout_s=30.0)
        if not ready:
            logger.error("Service failed to become ready")
            raise RuntimeError("Service not ready")
        
        # Health check Guardian connection
        guardian_status = await guardian_client.get_health()
        logger.info("Guardian connection established", status=guardian_status)
        # Load security policy and set default mode
        try:
            import os as _os
            policy_path = _os.getenv("SECURITY_POLICY_PATH", "config/security_policy.yaml")
            app.state.security_policy = load_policy(policy_path)
            set_mode("NORMAL")
            logger.info("Security policy loaded", path=policy_path)
        except Exception as e:
            logger.warning("Security policy load failed", error=str(e))
        
        yield
        
        logger.info("Alice v2 Orchestrator shutting down")
        
        # Perform graceful shutdown
        await shutdown_app()
        await guardian_client.close()
        
    except Exception as e:
        logger.error("Failed to start Orchestrator", error=str(e))
        raise

# Create FastAPI application
app = FastAPI(
    title="Alice v2 Orchestrator",
    description="LLM routing and API gateway for Alice AI Assistant",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:3001"],  # Web frontend + HUD
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["*"],
)

# Add logging middleware
app.add_middleware(LoggingMiddleware)

# Add metrics middleware for real latency/status tracking
app.add_middleware(MetricsMiddleware)

# Health check endpoints
@app.get("/health")
async def health():
    """Liveness check - just process alive"""
    return check_liveness()

@app.get("/ready")
async def ready():
    """Readiness check - dependencies ready for traffic"""
    readiness = await check_readiness()
    
    if not readiness["ready"]:
        raise HTTPException(status_code=503, detail="Service not ready")
    
    return readiness

# Prometheus metrics endpoint (optional in dev)
try:
    from prometheus_client import generate_latest, CONTENT_TYPE_LATEST

    @app.get("/metrics")
    async def metrics():
        return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)
except Exception:
    pass

# Privacy endpoints
@app.post("/api/privacy/forget")
async def forget_user(request: Request):
    """Right to forget - delete user data"""
    try:
        body = await request.json()
        user_id = body.get("user_id")
        session_id = body.get("session_id")
        
        if not user_id:
            raise HTTPException(status_code=400, detail="user_id required")
        
        # Track request during shutdown
        async with request_context(f"forget_{user_id}"):
            deletion_report = privacy_manager.forget_user(user_id, session_id)
            return deletion_report
            
    except Exception as e:
        logger.error("Forget user failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/privacy/cleanup")
async def cleanup_expired_data():
    """Clean up expired data based on retention policies"""
    try:
        cleaned_items = privacy_manager.cleanup_expired_data()
        return {
            "cleaned_items": cleaned_items,
            "timestamp": "2025-08-31T19:30:00Z"
        }
    except Exception as e:
        logger.error("Data cleanup failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))

# Include API routers
app.include_router(chat.router, prefix="/api", tags=["chat"])  # NLU‑aware chat mock
app.include_router(orchestrator.router, prefix="/api/orchestrator", tags=["orchestrator"])  # full LLM v1
app.include_router(security_router, tags=["security"])  # /api/security/state
app.include_router(status.router, prefix="/api/status", tags=["status"])
app.include_router(feedback.router)
app.include_router(learn.router, tags=["learning"])  # Learning API endpoints
app.include_router(memory.router, tags=["memory"])  # Memory service endpoints

# Include Fix Pack v1 status router with real metrics
app.include_router(fix_status_router)

# Root endpoint
@app.get("/")
async def root():
    """Root endpoint with service information"""
    return {
        "service": "Alice v2 Orchestrator",
        "version": "1.0.0",
        "docs": "/docs",
        "health": "/health",
        "ready": "/ready",
        "privacy": "/api/privacy"
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="127.0.0.1",
        port=8000,
        reload=True,
        log_config=None,  # Use our structured logging
    )