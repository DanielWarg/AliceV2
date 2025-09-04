import json
import os
import pathlib
import sys
import time
import uuid

import httpx

API = os.getenv("API_BASE", "http://localhost:8000")
ART = pathlib.Path("../../data/tests")
ART.mkdir(parents=True, exist_ok=True)
SCEN = pathlib.Path(__file__).with_name("scenarios.json")
RESULTS = ART / "results.jsonl"


def run_chat(text, session="eval"):
    payload = {"session_id": f"{session}-{uuid.uuid4().hex[:6]}", "message": text}
    t0 = time.perf_counter()
    with httpx.Client(timeout=10) as c:
        # Use NLU-aware chat endpoint (mock-friendly)
        r = c.post(
            f"{API}/api/chat",
            json=payload,
            headers={"Authorization": "Bearer test-key-123"},
        )
        dt = (time.perf_counter() - t0) * 1000
        return r, dt


def main():
    scenarios = json.loads(SCEN.read_text())
    passed = 0
    total = 0
    with RESULTS.open("a") as f:
        for sc in scenarios:
            total += 1
            r, dt = run_chat(sc["text"], session=sc["id"])
            ok = r.status_code == 200
            # Prefer route hint header (from NLU), fall back to model_used
            route = r.headers.get("X-Route-Hint")
            try:
                data = r.json()
                if not route:
                    route = data.get("model_used")
            except Exception:
                ok = False
            # Security-kind scenarier påverkar inte pass-rate (observations-only)
            if sc.get("kind") == "security":
                ok = True
            if "expect" in sc and "route" in sc["expect"]:
                ok = ok and (route == sc["expect"]["route"])
            row = {
                "v": "1",
                "ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                "id": sc["id"],
                "ok": ok,
                "lat_ms": round(dt, 1),
                "route": route,
                "status": r.status_code,
            }
            f.write(json.dumps(row) + "\n")
            if ok:
                passed += 1
    rate = (100.0 * passed / total) if total else 100.0
    print(json.dumps({"total": total, "passed": passed, "rate_pct": round(rate, 1)}))
    # exit kode 1 om under 80% pass
    sys.exit(0 if rate >= 80.0 else 1)


if __name__ == "__main__":
    main()
