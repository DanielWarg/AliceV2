"""
Structured Logging Middleware
JSON formatted logs with trace IDs and request correlation
"""

import structlog
import logging
import sys
import uuid
import time
from typing import Callable
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

def setup_logging() -> None:
    """Configure structured logging for the application"""
    
    # Configure structlog
    structlog.configure(
        processors=[
            structlog.stdlib.filter_by_level,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            structlog.stdlib.PositionalArgumentsFormatter(),
            structlog.processors.TimeStamper(fmt="ISO"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.UnicodeDecoder(),
            structlog.processors.JSONRenderer(indent=None, sort_keys=True)
        ],
        wrapper_class=structlog.stdlib.BoundLogger,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )
    
    # Configure standard library logging
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=logging.INFO,
    )
    
    # Disable uvicorn access logs (we handle them ourselves)
    logging.getLogger("uvicorn.access").disabled = True

class LoggingMiddleware(BaseHTTPMiddleware):
    """Middleware for request/response logging with trace correlation"""
    
    def __init__(self, app: ASGIApp):
        super().__init__(app)
        self.logger = structlog.get_logger(__name__)
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process request with structured logging"""
        
        # Generate trace ID for request correlation
        trace_id = str(uuid.uuid4())
        start_time = time.time()
        
        # Add trace ID to request state
        request.state.trace_id = trace_id
        
        # Extract basic request info
        client_ip = request.client.host if request.client else "unknown"
        user_agent = request.headers.get("user-agent", "unknown")
        
        # Log request start
        self.logger.info(
            "Request started",
            trace_id=trace_id,
            method=request.method,
            url=str(request.url),
            path=request.url.path,
            client_ip=client_ip,
            user_agent=user_agent,
        )
        
        try:
            # Process request
            response = await call_next(request)
            
            # Calculate response time
            response_time_ms = int((time.time() - start_time) * 1000)
            
            # Add trace ID to response headers
            response.headers["X-Trace-ID"] = trace_id
            
            # Log successful response
            self.logger.info(
                "Request completed",
                trace_id=trace_id,
                method=request.method,
                path=request.url.path,
                status_code=response.status_code,
                response_time_ms=response_time_ms,
                client_ip=client_ip
            )
            
            return response
            
        except Exception as e:
            # Calculate response time for error case
            response_time_ms = int((time.time() - start_time) * 1000)
            
            # Log error
            self.logger.error(
                "Request failed",
                trace_id=trace_id,
                method=request.method,
                path=request.url.path,
                error=str(e),
                error_type=type(e).__name__,
                response_time_ms=response_time_ms,
                client_ip=client_ip,
                exc_info=True
            )
            
            raise

def get_trace_id(request: Request) -> str:
    """Extract trace ID from request state"""
    return getattr(request.state, "trace_id", "unknown")

def get_logger_with_trace(request: Request, name: str = __name__) -> structlog.BoundLogger:
    """Get logger bound with trace ID from request"""
    logger = structlog.get_logger(name)
    trace_id = get_trace_id(request)
    return logger.bind(trace_id=trace_id)