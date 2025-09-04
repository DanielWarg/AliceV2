"""
Authentication and Rate Limiting Middleware
Implements bearer token validation and per-session rate limiting
"""

import hashlib
import time
from collections import defaultdict, deque
from typing import Dict, Optional

import structlog
from fastapi import Depends, HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

logger = structlog.get_logger(__name__)

# Rate limiting configuration
RATE_LIMITS = {
    "/api/chat": {"requests": 10, "window": 60},  # 10 req/min
    "/api/orchestrator/ingest": {"requests": 20, "window": 60},  # 20 req/min
    "/api/orchestrator/run": {"requests": 20, "window": 60},  # 20 req/min
    "default": {"requests": 100, "window": 60},  # 100 req/min
}

# In-memory rate limit storage (in production, use Redis)
rate_limit_store: Dict[str, deque] = defaultdict(lambda: deque(maxlen=1000))

# API keys (in production, use database + hashing)
VALID_API_KEYS = {
    "test-key-123": {"client": "test-client", "rate_limit_multiplier": 1.0},
    "system-key-456": {"client": "system-account", "rate_limit_multiplier": 5.0},
}

security = HTTPBearer(auto_error=False)


def get_api_key(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
) -> str:
    """Extract and validate API key from bearer token"""
    if not credentials:
        raise HTTPException(
            status_code=401,
            detail="API key required. Use Bearer token in Authorization header",
        )

    api_key = credentials.credentials

    if api_key not in VALID_API_KEYS:
        logger.warning(
            "Invalid API key attempted",
            api_key_hash=hashlib.sha256(api_key.encode()).hexdigest()[:8],
        )
        raise HTTPException(status_code=401, detail="Invalid API key")

    return api_key


def check_rate_limit(request: Request, api_key: str) -> None:
    """Check rate limit for the current request"""
    client_info = VALID_API_KEYS[api_key]
    client_id = client_info["client"]

    # Get rate limit config for this endpoint
    endpoint = request.url.path
    rate_config = RATE_LIMITS.get(endpoint, RATE_LIMITS["default"])

    # Apply client-specific multiplier
    max_requests = int(rate_config["requests"] * client_info["rate_limit_multiplier"])
    window = rate_config["window"]

    # Create rate limit key
    rate_key = f"{client_id}:{endpoint}"

    # Get current window
    current_time = time.time()
    window_start = current_time - window

    # Clean old entries
    if rate_key in rate_limit_store:
        while (
            rate_limit_store[rate_key] and rate_limit_store[rate_key][0] < window_start
        ):
            rate_limit_store[rate_key].popleft()

    # Check if limit exceeded
    if rate_key in rate_limit_store and len(rate_limit_store[rate_key]) >= max_requests:
        retry_after = int(window - (current_time - rate_limit_store[rate_key][0]))

        logger.warning(
            "Rate limit exceeded",
            client_id=client_id,
            endpoint=endpoint,
            current_requests=len(rate_limit_store[rate_key]),
            max_requests=max_requests,
            retry_after=retry_after,
        )

        raise HTTPException(
            status_code=429,
            detail=f"Rate limit exceeded. Try again in {retry_after} seconds",
            headers={"Retry-After": str(retry_after)},
        )

    # Add current request
    if rate_key not in rate_limit_store:
        rate_limit_store[rate_key] = deque()
    rate_limit_store[rate_key].append(current_time)

    # Log rate limit info
    logger.debug(
        "Rate limit check passed",
        client_id=client_id,
        endpoint=endpoint,
        current_requests=len(rate_limit_store[rate_key]),
        max_requests=max_requests,
    )


def get_client_info(api_key: str) -> Dict[str, any]:
    """Get client information for the API key"""
    return VALID_API_KEYS[api_key]
