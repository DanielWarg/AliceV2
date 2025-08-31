"""
Health Check Management
Separates liveness (process alive) from readiness (dependencies ready)
"""

import asyncio
import time
from typing import Dict, Any
from fastapi import HTTPException
import structlog
from .services.guardian_client import GuardianClient

logger = structlog.get_logger(__name__)

# Global readiness state
READINESS_STATE = {
    "startup_time": time.time(),
    "dependencies_ready": False,
    "models_warmed": False,
    "guardian_reachable": False,
    "last_check": 0,
    "error_count": 0
}

guardian_client = GuardianClient()

async def check_dependencies() -> Dict[str, Any]:
    """Check all critical dependencies"""
    try:
        # Check Guardian
        guardian_health = await guardian_client.get_health()
        guardian_ok = guardian_health.get("state") in ["NORMAL", "BROWNOUT"]
        
        # Check internal services (placeholder for future)
        internal_ok = True  # Will check model loading, cache, etc.
        
        # Check external dependencies (placeholder)
        external_ok = True  # Will check databases, external APIs, etc.
        
        return {
            "guardian": guardian_ok,
            "internal": internal_ok,
            "external": external_ok,
            "all_ready": guardian_ok and internal_ok and external_ok
        }
    except Exception as e:
        logger.error("Dependency check failed", error=str(e))
        return {
            "guardian": False,
            "internal": False,
            "external": False,
            "all_ready": False,
            "error": str(e)
        }

async def check_readiness() -> Dict[str, Any]:
    """Comprehensive readiness check"""
    global READINESS_STATE
    
    # Rate limit checks to avoid overwhelming dependencies
    if time.time() - READINESS_STATE["last_check"] < 5:  # Max every 5s
        return {
            "ready": READINESS_STATE["dependencies_ready"],
            "startup_time": READINESS_STATE["startup_time"],
            "uptime_s": time.time() - READINESS_STATE["startup_time"],
            "last_check": READINESS_STATE["last_check"]
        }
    
    READINESS_STATE["last_check"] = time.time()
    
    # Check dependencies
    deps = await check_dependencies()
    READINESS_STATE["dependencies_ready"] = deps["all_ready"]
    
    if deps["all_ready"]:
        READINESS_STATE["error_count"] = 0
    else:
        READINESS_STATE["error_count"] += 1
    
    return {
        "ready": deps["all_ready"],
        "startup_time": READINESS_STATE["startup_time"],
        "uptime_s": time.time() - READINESS_STATE["startup_time"],
        "dependencies": deps,
        "error_count": READINESS_STATE["error_count"]
    }

def check_liveness() -> Dict[str, Any]:
    """Simple liveness check - just process alive"""
    return {
        "alive": True,
        "pid": __import__("os").getpid(),
        "uptime_s": time.time() - READINESS_STATE["startup_time"]
    }

async def wait_for_readiness(timeout_s: float = 30.0) -> bool:
    """Wait for readiness with timeout"""
    start = time.time()
    while time.time() - start < timeout_s:
        ready_check = await check_readiness()
        if ready_check["ready"]:
            logger.info("Service ready for traffic")
            return True
        await asyncio.sleep(1)
    
    logger.error("Service failed to become ready within timeout", timeout_s=timeout_s)
    return False
