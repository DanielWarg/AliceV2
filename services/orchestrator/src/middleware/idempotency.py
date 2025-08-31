"""
Idempotency Middleware
Implements idempotency key support with 60-second response caching
"""

import time
import hashlib
import json
from typing import Dict, Optional, Any
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
import structlog

logger = structlog.get_logger(__name__)

# In-memory cache (in production, use Redis)
idempotency_cache: Dict[str, Dict[str, Any]] = {}
CACHE_TTL = 60  # 60 seconds

class IdempotencyMiddleware(BaseHTTPMiddleware):
    """Middleware for handling idempotency keys"""
    
    async def dispatch(self, request: Request, call_next):
        # Only apply to POST endpoints that support idempotency
        if request.method != "POST" or not request.url.path.startswith("/api/"):
            return await call_next(request)
        
        # Check for idempotency key
        idempotency_key = request.headers.get("Idempotency-Key")
        if not idempotency_key:
            return await call_next(request)
        
        # Create cache key from idempotency key + request path
        cache_key = f"{idempotency_key}:{request.url.path}"
        
        # Check if we have a cached response
        if cache_key in idempotency_cache:
            cached = idempotency_cache[cache_key]
            
            # Check if cache is still valid
            if time.time() - cached["timestamp"] < CACHE_TTL:
                logger.info(
                    "Returning cached response for idempotency key",
                    idempotency_key=idempotency_key[:8] + "...",
                    cache_age=time.time() - cached["timestamp"],
                    status_code=cached["status_code"]
                )
                
                # Return cached response
                response = Response(
                    content=cached["content"],
                    status_code=cached["status_code"],
                    headers=cached["headers"]
                )
                return response
            else:
                # Remove expired cache entry
                del idempotency_cache[cache_key]
        
        # Process request normally
        response = await call_next(request)
        
        # Cache successful responses (2xx status codes)
        if 200 <= response.status_code < 300:
            # Read response content
            response_body = b""
            async for chunk in response.body_iterator:
                response_body += chunk
            
            # Create new response with the same content
            new_response = Response(
                content=response_body,
                status_code=response.status_code,
                headers=dict(response.headers)
            )
            
            # Cache the response
            idempotency_cache[cache_key] = {
                "content": response_body,
                "status_code": response.status_code,
                "headers": dict(response.headers),
                "timestamp": time.time()
            }
            
            # Clean up old cache entries
            self._cleanup_cache()
            
            logger.info(
                "Cached response for idempotency key",
                idempotency_key=idempotency_key[:8] + "...",
                status_code=response.status_code
            )
            
            return new_response
        
        return response
    
    def _cleanup_cache(self):
        """Remove expired cache entries"""
        current_time = time.time()
        expired_keys = [
            key for key, value in idempotency_cache.items()
            if current_time - value["timestamp"] >= CACHE_TTL
        ]
        
        for key in expired_keys:
            del idempotency_cache[key]
        
        if expired_keys:
            logger.debug(f"Cleaned up {len(expired_keys)} expired cache entries")
