from fastapi import APIRouter
from metrics import METRICS
from guardian_client import poll_and_log

router = APIRouter(prefix="/api/status", tags=["status"])

@router.get("/simple")
def simple():
    s = METRICS.snapshot()
    return {"ok": True, "metrics": s}

@router.get("/guardian")
def guardian():
    g = poll_and_log()
    return {"ok": bool(g), "guardian": g}

@router.get("/routes")
def routes():
    snap = METRICS.snapshot()["routes"]
    # map to blueprint keys
    return {
        "fast_p95_ms": snap.get("micro",{}).get("p95_ms"),
        "planner_p95_ms": snap.get("planner",{}).get("p95_ms"),
        "deep_p95_ms": snap.get("deep",{}).get("p95_ms"),
        "raw": snap
    }