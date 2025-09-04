from fastapi import APIRouter

from .metrics import security_mode_gauge

router = APIRouter()


@router.get("/api/security/state")
def state():
    vals = {"NORMAL": 0, "STRICT": 0, "LOCKDOWN": 0}
    for m in vals:
        try:
            vals[m] = security_mode_gauge.labels(mode=m)._value.get()
        except Exception:
            pass
    return {"v": "1", "modes": vals}
