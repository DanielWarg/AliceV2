"""Guardian Gate Middleware - Admission control for Alice API"""

import logging
import time
from collections import deque
from typing import Any

import httpx
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse


class GuardianGate(BaseHTTPMiddleware):
    """
    Guardian Gate middleware för admission control

    Blockerar requests baserat på Guardian status för att skydda systemet
    från överbelastning innan requests når LLM-lagret.
    """

    def __init__(
        self,
        app,
        guardian_url: str = "http://localhost:8787/health",
        cache_ttl_ms: int = 250,
        timeout_s: float = 0.5,
        unknown_hysteresis_count: int = 3,
    ):
        super().__init__(app)
        self.guardian_url = guardian_url
        self.cache_ttl_ms = cache_ttl_ms
        self.timeout_s = timeout_s
        self.unknown_hysteresis_count = unknown_hysteresis_count

        # Caching
        self.cached_status: dict[str, Any] | None = None
        self.cache_timestamp: float = 0

        # Hysteresis för unknown states
        self.unknown_responses: deque = deque(maxlen=unknown_hysteresis_count)

        self.logger = logging.getLogger("guardian.gate")

    async def dispatch(self, request: Request, call_next):
        """Process request through Guardian gate"""

        # Skip Guardian check for health endpoints and static assets
        if self._should_skip_guardian(request):
            return await call_next(request)

        # Get Guardian status (cached)
        guardian_status = await self._get_guardian_status()

        # Check admission control
        admission_result = self._check_admission(guardian_status)

        if admission_result["allowed"]:
            # Request allowed, proceed
            return await call_next(request)
        # Request blocked, return error response
        return JSONResponse(
            status_code=admission_result["status_code"],
            content={
                "error": admission_result["message"],
                "guardian_state": guardian_status.get("status", "unknown"),
                "retry_after": admission_result.get("retry_after"),
            },
            headers=admission_result.get("headers", {}),
        )

    def _should_skip_guardian(self, request: Request) -> bool:
        """Check if request should skip Guardian gate"""
        path = request.url.path

        # Skip health checks
        if path in ["/health", "/", "/api/health"]:
            return True

        # Skip Guardian API endpoints
        if path.startswith("/api/guard/"):
            return True

        # Skip static assets
        if any(path.endswith(ext) for ext in [".css", ".js", ".ico", ".png", ".jpg"]):
            return True

        return False

    async def _get_guardian_status(self) -> dict[str, Any]:
        """Get Guardian status with caching"""
        now = time.time() * 1000  # milliseconds

        # Check cache validity
        if self.cached_status and now - self.cache_timestamp < self.cache_ttl_ms:
            return self.cached_status

        # Fetch fresh status
        try:
            async with httpx.AsyncClient(timeout=self.timeout_s) as client:
                response = await client.get(self.guardian_url)

                if response.status_code == 200:
                    status = response.json()
                    self.cached_status = status
                    self.cache_timestamp = now
                    self.unknown_responses.clear()  # Clear unknown streak
                    return status
                self.logger.warning(f"Guardian returned {response.status_code}")

        except Exception as e:
            self.logger.debug(f"Guardian check failed: {e}")

        # Guardian unreachable - handle with hysteresis
        self.unknown_responses.append(True)

        # Return safe default or cached status
        if self.cached_status:
            # Use stale cache if available
            return self.cached_status
        # No cache available, return unknown status
        return {"status": "unknown"}

    def _check_admission(self, guardian_status: dict[str, Any]) -> dict[str, Any]:
        """Check if request should be admitted based on Guardian status"""
        status = guardian_status.get("status", "unknown")

        # Handle different Guardian states
        if status == "normal":
            return {"allowed": True}

        if status == "brownout":
            # Allow with warning header
            return {"allowed": True, "headers": {"X-Guardian-State": "brownout"}}

        if status == "degraded":
            # Allow with degraded performance warning
            return {
                "allowed": True,
                "headers": {
                    "X-Guardian-State": "degraded",
                    "X-Guardian-Warning": "System running in degraded mode",
                },
            }

        if status == "emergency":
            # Block with 503 Service Unavailable
            return {
                "allowed": False,
                "status_code": 503,
                "message": "Service temporarily unavailable due to high system load",
                "retry_after": 15,
                "headers": {"Retry-After": "15"},
            }

        if status == "lockdown":
            # Block with 503 Service Unavailable
            return {
                "allowed": False,
                "status_code": 503,
                "message": "Service temporarily unavailable - system in lockdown",
                "retry_after": 60,
                "headers": {"Retry-After": "60"},
            }

        if status == "unknown":
            # Handle unknown state with hysteresis
            if len(self.unknown_responses) >= self.unknown_hysteresis_count:
                # Too many consecutive unknown responses - block to be safe
                return {
                    "allowed": False,
                    "status_code": 503,
                    "message": "Service temporarily unavailable - guardian status unknown",
                    "retry_after": 5,
                    "headers": {"Retry-After": "5"},
                }
            # Still within hysteresis window - allow with warning
            return {"allowed": True, "headers": {"X-Guardian-State": "unknown"}}

        # Default: block unknown states
        return {
            "allowed": False,
            "status_code": 503,
            "message": f"Service temporarily unavailable - guardian state: {status}",
            "retry_after": 10,
            "headers": {"Retry-After": "10"},
        }
