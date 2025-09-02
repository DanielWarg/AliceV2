from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import psutil, time, os
from collections import deque

app = FastAPI()

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:3001"],  # Web frontend + HUD
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["*"],
)
class State(BaseModel):
    state: str = "NORMAL"  # NORMAL|BROWNOUT|EMERGENCY|LOCKDOWN
    brownout_level: str = "NONE"  # NONE|LIGHT|MODERATE|HEAVY
    reason: str = ""
    since_s: float = 0.0

S = State()
LAST_TS = time.time()

# thresholds
RAM_SOFT = float(os.getenv("GUARD_RAM_SOFT","0.80"))
RAM_HARD = float(os.getenv("GUARD_RAM_HARD","0.92"))
RECOVER_RAM = float(os.getenv("GUARD_RECOVER_RAM","0.70"))
CPU_SOFT = float(os.getenv("GUARD_CPU_SOFT","0.80"))
TEMP_HARD = float(os.getenv("GUARD_TEMP_C_HARD","85"))
BATT_HARD = float(os.getenv("GUARD_BATTERY_PCT_HARD","25"))

# 5-punkts glidfönster
W = 5
ram_w = deque(maxlen=W)
cpu_w = deque(maxlen=W)

def measure():
    ram = psutil.virtual_memory().percent/100.0
    cpu = psutil.cpu_percent(interval=None)/100.0
    # temp och batteri kan saknas på vissa system
    temp = None
    try:
        ts = psutil.sensors_temperatures()
        if ts:
            # ta högsta värdet
            temp = max(v.current for arr in ts.values() for v in arr)
    except: pass
    batt = None
    try:
        b = psutil.sensors_battery()
        if b:
            batt = b.percent
    except: pass
    return ram, cpu, temp, batt

def update_state():
    global LAST_TS, S
    ram, cpu, temp, batt = measure()
    ram_w.append(ram); cpu_w.append(cpu)

    # fönsterlogik (5 punkter)
    soft = (all(x>=RAM_SOFT for x in ram_w) or all(x>=CPU_SOFT for x in cpu_w))
    hard = (ram>=RAM_HARD or (temp and temp>=TEMP_HARD) or (batt is not None and batt<=BATT_HARD))

    prev = S.state
    if prev in ("NORMAL","DEGRADED") and hard:
        S.state = "EMERGENCY"; S.brownout_level="HEAVY"; S.reason="HARD_TRIGGER"
        LAST_TS = time.time()
    elif prev == "NORMAL" and soft:
        # börja lätt brownout
        S.state = "BROWNOUT"; S.brownout_level="LIGHT"; S.reason="SOFT_TRIGGER"
        LAST_TS = time.time()
    elif prev in ("BROWNOUT","EMERGENCY"):
        # 60s återhämtningshysteresis + recover-gränser
        if ram_w and max(ram_w) < RECOVER_RAM and cpu_w and max(cpu_w) < CPU_SOFT:
            if time.time() - LAST_TS >= 60.0:
                S.state = "NORMAL"; S.brownout_level="NONE"; S.reason="RECOVER"
                LAST_TS = time.time()

    S.since_s = round(time.time() - LAST_TS, 1)
    return ram, cpu, temp, batt

@app.get("/health")
def health_root():
    ram, cpu, temp, batt = update_state()
    return {
        "v":"1",
        "state": S.state,
        "brownout_level": S.brownout_level,
        "reason": S.reason,
        "since_s": S.since_s,
        "ram_pct": round(ram*100,1),
        "cpu_pct": round(cpu*100,1),
        "temp_c": temp,
        "battery_pct": batt
    }

# kompatibel alias
@app.get("/guardian/health")
def health_alias():
    return health_root()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8787)