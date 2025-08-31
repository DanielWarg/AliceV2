from fastapi import APIRouter
from .metrics import METRICS
from .services.guardian_client import GuardianClient

router = APIRouter(prefix="/api/status", tags=["status"])

# Guardian client for health checks
guardian_client = GuardianClient()

async def poll_and_log():
    """Poll Guardian health and return status"""
    try:
        health = await guardian_client.get_health()
        return health
    except Exception as e:
        return {"state": "ERROR", "error": str(e)}

@router.get("/simple")
async def simple():
    s = METRICS.snapshot()
    return {"ok": True, "metrics": s}

@router.get("/guardian")
async def guardian():
    g = await poll_and_log()
    return {"ok": bool(g), "guardian": g}

@router.get("/routes")
async def routes():
    snap = METRICS.snapshot()["routes"]
    # map to blueprint keys
    return {
        "fast_p95_ms": snap.get("micro",{}).get("p95_ms"),
        "planner_p95_ms": snap.get("planner",{}).get("p95_ms"),
        "deep_p95_ms": snap.get("deep",{}).get("p95_ms"),
        "raw": snap
    }