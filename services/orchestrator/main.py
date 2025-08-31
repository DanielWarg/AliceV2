#!/usr/bin/env python3
"""
Alice v2 Orchestrator Service
Main FastAPI application entry point
"""

from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import structlog
import httpx
from typing import AsyncGenerator

from src.routers import chat, orchestrator, status
from src.middleware.logging import setup_logging, LoggingMiddleware
from src.services.guardian_client import GuardianClient
from src.mw_metrics import MetricsMiddleware
from src.status_router import router as fix_status_router

# Setup structured logging
setup_logging()
logger = structlog.get_logger(__name__)

# Global Guardian client
guardian_client = GuardianClient()

@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan management"""
    logger.info("Alice v2 Orchestrator starting up", version="1.0.0")
    
    # Initialize Guardian client
    await guardian_client.initialize()
    
    # Health check Guardian connection
    guardian_status = await guardian_client.get_health()
    logger.info("Guardian connection established", status=guardian_status)
    
    yield
    
    logger.info("Alice v2 Orchestrator shutting down")
    await guardian_client.close()

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
    allow_origins=["http://localhost:3000"],  # Web frontend
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["*"],
)

# Add logging middleware
app.add_middleware(LoggingMiddleware)

# Add metrics middleware for real latency/status tracking
app.add_middleware(MetricsMiddleware)

# Health check endpoint
@app.get("/health")
async def health():
    """Service health check with dependency status"""
    try:
        # Check Guardian status
        guardian_health = await guardian_client.get_health()
        
        return {
            "status": "healthy",
            "service": "orchestrator",
            "version": "1.0.0",
            "dependencies": {
                "guardian": guardian_health.get("state", "unknown")
            }
        }
    except Exception as e:
        logger.error("Health check failed", error=str(e))
        raise HTTPException(status_code=503, detail="Service unhealthy")

# Include API routers
app.include_router(chat.router, prefix="/api", tags=["chat"])
app.include_router(orchestrator.router, prefix="/api/orchestrator", tags=["orchestrator"])
app.include_router(status.router, prefix="/api/status", tags=["status"])

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
        "health": "/health"
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