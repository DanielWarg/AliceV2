from datetime import datetime

from fastapi import APIRouter

from .metrics import METRICS
from .services.guardian_client import GuardianClient

router = APIRouter(prefix="/api/status", tags=["status"])

# Guardian client for health checks
guardian_client = GuardianClient()


@router.get("/simple")
async def simple():
    """Get system status with Guardian health check - always returns 200"""
    try:
        # Get metrics snapshot
        s = METRICS.snapshot()

        # Get Guardian status (with fallback)
        try:
            guardian_health = await guardian_client.get_health()
            guardian_ok = guardian_health.get("available", False)
            guardian_state = guardian_health.get("state", "UNKNOWN")
        except Exception as e:
            guardian_ok = False
            guardian_state = "ERROR"
            guardian_health = {"state": "ERROR", "error": str(e)}

        # Always return 200 with status info
        return {
            "v": "1",
            "ok": True,  # System is operational even if Guardian is down
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "metrics": s,
            "guardian": {
                "available": guardian_ok,
                "state": guardian_state,
                "details": guardian_health,
            },
            "issues": [] if guardian_ok else ["guardian_unreachable"],
        }
    except Exception as e:
        # Even if everything fails, return 200 with error info
        return {
            "v": "1",
            "ok": False,
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "error": str(e),
            "guardian": {"available": False, "state": "ERROR"},
            "issues": ["system_error"],
        }


@router.get("/guardian")
async def guardian():
    """Get Guardian status"""
    try:
        health = await guardian_client.get_health()
        return {"ok": bool(health), "guardian": health}
    except Exception as e:
        return {"ok": False, "guardian": {"state": "ERROR", "error": str(e)}}


@router.get("/routes")
async def routes():
    snap = METRICS.snapshot()["routes"]
    # map to blueprint keys
    return {
        "fast_p95_ms": snap.get("micro", {}).get("p95_ms"),
        "planner_p95_ms": snap.get("planner", {}).get("p95_ms"),
        "deep_p95_ms": snap.get("deep", {}).get("p95_ms"),
        "raw": snap,
    }
