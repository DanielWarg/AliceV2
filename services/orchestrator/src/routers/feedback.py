from fastapi import APIRouter
from typing import Dict, Any
import os, json
from datetime import datetime

router = APIRouter(prefix="/api/feedback", tags=["feedback"])


def append_event(ev: Dict[str, Any]) -> None:
    log_dir = os.getenv("LOG_DIR", "/data/telemetry")
    today = datetime.utcnow().strftime("%Y-%m-%d")
    # flat daily file for simplicity
    filename = os.path.join(log_dir, f"events_{today}.jsonl")
    os.makedirs(log_dir, exist_ok=True)
    with open(filename, "a", encoding="utf-8") as f:
        f.write(json.dumps(ev, ensure_ascii=False) + "\n")


@router.post("/thumbs")
async def thumbs(body: Dict[str, Any]):
    ev = {
        "v": "1",
        "kind": "feedback",
        "trace_id": body.get("trace_id"),
        "explicit": {"thumbs_up": bool(body.get("up", False)), "comment": body.get("comment")},
    }
    append_event(ev)
    return {"ok": True}


