import os, httpx, time, json, pathlib

GUARD_URLS = [
    os.getenv("GUARDIAN_HEALTH_URL", "http://guardian:8787/health"),
    "http://guardian:8787/guardian/health",
    "http://guardian:8787/health",
]

LOG_DIR = os.getenv("LOG_DIR", "/data/telemetry")

def _normalize(payload: dict) -> dict:
    # Normalisera till v1 schema (ram_pct, cpu_pct, state, level, reason ...)
    out = {"v":"1"}
    out.update(payload)
    # minimal normalisering om fältnamn skiljer
    if "ram" in payload and "ram_pct" not in payload: out["ram_pct"] = payload["ram"]
    if "cpu" in payload and "cpu_pct" not in payload: out["cpu_pct"] = payload["cpu"]
    # level mapping
    if out.get("state") == "BROWNOUT" and "brownout_level" not in out:
        out["brownout_level"] = "LIGHT"
    return out

def poll_and_log():
    today = time.strftime("%Y-%m-%d")
    p = pathlib.Path(LOG_DIR) / today
    p.mkdir(parents=True, exist_ok=True)
    f = (p / "guardian.jsonl").open("a", buffering=1)
    with httpx.Client(timeout=1.5) as c:
        for url in GUARD_URLS:
            try:
                r = c.get(url)
                if r.status_code == 200:
                    data = r.json()
                    out = _normalize(data)
                    out["ts"] = time.strftime("%Y-%m-%dT%H:%M:%S")
                    f.write(json.dumps(out) + "\n")
                    return out
            except Exception:
                continue
    return None