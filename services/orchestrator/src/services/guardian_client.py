"""
Guardian System Client
Handles communication with Alice v2 Guardian safety system
"""

import httpx
import structlog
from typing import Dict, Any, Optional
import asyncio
from contextlib import asynccontextmanager

from ..models.api import GuardianState

logger = structlog.get_logger(__name__)

class GuardianClient:
    """Client for Guardian safety system integration"""
    
    def __init__(self, base_url: str = "http://localhost:8787", timeout: float = 0.5):
        self.base_url = base_url
        self.timeout = timeout
        self._client: Optional[httpx.AsyncClient] = None
        self._last_health: Optional[Dict[str, Any]] = None
        self._health_cache_ttl = 1.0  # Cache for 1 second
        self._last_health_check = 0.0
        
    async def initialize(self) -> None:
        """Initialize HTTP client"""
        self._client = httpx.AsyncClient(
            base_url=self.base_url,
            timeout=self.timeout,
            limits=httpx.Limits(max_connections=10, max_keepalive_connections=5)
        )
        logger.info("Guardian client initialized", base_url=self.base_url)
    
    async def close(self) -> None:
        """Close HTTP client"""
        if self._client:
            await self._client.aclose()
            logger.info("Guardian client closed")
    
    async def get_health(self, use_cache: bool = True) -> Dict[str, Any]:
        """
        Get Guardian health status with caching
        
        Args:
            use_cache: Whether to use cached result if available
            
        Returns:
            Guardian health status dict
        """
        current_time = asyncio.get_event_loop().time()
        
        # Return cached result if recent
        if (use_cache and 
            self._last_health and 
            current_time - self._last_health_check < self._health_cache_ttl):
            return self._last_health
        
        try:
            if not self._client:
                await self.initialize()
                
            response = await self._client.get("/guardian/health")
            response.raise_for_status()
            
            health_data = response.json()
            
            # Cache the result
            self._last_health = health_data
            self._last_health_check = current_time
            
            logger.debug("Guardian health check successful", 
                        state=health_data.get("state"),
                        response_time_ms=int(response.elapsed.total_seconds() * 1000))
            
            return health_data
            
        except httpx.TimeoutException:
            logger.warning("Guardian health check timeout")
            return {"state": "TIMEOUT", "available": False}
            
        except httpx.ConnectError:
            logger.warning("Guardian connection failed")
            return {"state": "UNREACHABLE", "available": False}
            
        except Exception as e:
            logger.error("Guardian health check error", error=str(e))
            return {"state": "ERROR", "available": False, "error": str(e)}
    
    async def check_admission(self, request_data: Optional[Dict[str, Any]] = None) -> bool:
        """
        Check if request should be admitted based on Guardian state
        
        Args:
            request_data: Optional request data for advanced admission control
            
        Returns:
            True if request should be admitted, False otherwise
        """
        try:
            health = await self.get_health()
            state = health.get("state", "UNKNOWN")
            
            # Block during emergency and lockdown states
            if state in ["EMERGENCY", "LOCKDOWN"]:
                logger.info("Guardian blocking request", state=state)
                return False
            
            # Allow during normal and brownout states
            # (brownout may have rate limiting but doesn't block entirely)
            return True
            
        except Exception as e:
            logger.error("Guardian admission check failed", error=str(e))
            # Fail-open for now - allow requests if Guardian is unavailable
            # In production, this should be configurable
            return True
    
    async def get_recommended_model(self, request_data: Optional[Dict[str, Any]] = None) -> str:
        """
        Get Guardian's recommended model based on system state
        
        Args:
            request_data: Request data for model recommendation
            
        Returns:
            Recommended model name ("micro", "planner", "deep")
        """
        try:
            health = await self.get_health()
            state = health.get("state", "NORMAL")
            ram_pct = health.get("ram_pct", 0)
            
            # During high resource usage, prefer lighter models
            if state == "BROWNOUT" or ram_pct > 75:
                return "micro"
            elif state == "DEGRADED" or ram_pct > 60:
                return "planner"
            else:
                return "micro"  # Phase 1: Always return micro
                
        except Exception as e:
            logger.error("Guardian model recommendation failed", error=str(e))
            return "micro"  # Safe default
    
    async def report_request_metrics(self, metrics: Dict[str, Any]) -> None:
        """
        Report request metrics to Guardian for system monitoring
        
        Args:
            metrics: Request metrics (latency, model used, etc.)
        """
        try:
            if not self._client:
                await self.initialize()
                
            # Guardian may implement metrics ingestion in future
            await self._client.post("/guardian/metrics", json=metrics, timeout=0.1)
            
        except Exception as e:
            # Don't log errors for optional metrics reporting
            pass
    
    def get_retry_after_seconds(self, health_data: Optional[Dict[str, Any]] = None) -> int:
        """
        Get recommended retry delay based on Guardian state
        
        Args:
            health_data: Guardian health data (if available)
            
        Returns:
            Recommended retry delay in seconds
        """
        if not health_data:
            return 5
        
        state = health_data.get("state", "NORMAL")
        
        retry_map = {
            "NORMAL": 0,
            "BROWNOUT": 1,
            "DEGRADED": 5,
            "EMERGENCY": 30,
            "LOCKDOWN": 60,
            "TIMEOUT": 2,
            "UNREACHABLE": 10,
            "ERROR": 5
        }
        
        return retry_map.get(state, 5)