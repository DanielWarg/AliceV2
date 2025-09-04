# services/loadgen/watchers.py
"""
Guardian State Watchers - Measure brownout trigger latency and recovery time
============================================================================
"""

import json
import os
import pathlib
import time
from datetime import datetime
from typing import Any, Dict, Optional, Tuple

import httpx

# Configuration from environment
HEALTH_URL = os.getenv("GUARD_HEALTH", "http://localhost:8787/health")
TRIGGER_BUDGET_MS = int(os.getenv("SLO_BROWNOUT_TRIGGER_MS", "150"))
RECOVER_BUDGET_S = int(os.getenv("RECOVER_S", "60"))
EMERGENCY_TIMEOUT_S = int(os.getenv("EMERGENCY_TIMEOUT_S", "10"))


class GuardianWatcher:
    """Watch Guardian state transitions and measure SLO compliance"""

    def __init__(self):
        self.client = httpx.Client(timeout=2.0)
        self.last_state = "UNKNOWN"
        self.emergency_start = None

    def poll_guardian(self) -> Dict[str, Any]:
        """Poll Guardian health endpoint"""
        try:
            response = self.client.get(HEALTH_URL)
            response.raise_for_status()
            data = response.json()

            # Safety check for EMERGENCY state
            current_state = data.get("status", "UNKNOWN")
            if current_state == "EMERGENCY":
                if self.emergency_start is None:
                    self.emergency_start = time.perf_counter()
                elif time.perf_counter() - self.emergency_start > EMERGENCY_TIMEOUT_S:
                    raise RuntimeError(
                        f"EMERGENCY state exceeded {EMERGENCY_TIMEOUT_S}s - aborting for safety"
                    )
            else:
                self.emergency_start = None

            return data

        except httpx.RequestError as e:
            return {"status": "ERROR", "error": str(e)}

    def wait_for_brownout(
        self, start_ts: Optional[float] = None
    ) -> Tuple[Optional[int], Dict[str, Any]]:
        """
        Wait for Guardian to enter BROWNOUT or EMERGENCY state
        Returns: (trigger_latency_ms, final_state)
        """
        t0 = start_ts or time.perf_counter()
        poll_interval = 0.05  # 50ms polling

        print(f"⏱️  Waiting for brownout trigger (budget: {TRIGGER_BUDGET_MS}ms)...")

        while True:
            data = self.poll_guardian()
            current_state = data.get("status", "UNKNOWN")

            if current_state in ["BROWNOUT", "EMERGENCY"]:
                trigger_latency = int((time.perf_counter() - t0) * 1000)
                brownout_level = data.get("metrics", {}).get("degraded", False)

                print(
                    f"🟡 Brownout triggered: {current_state} after {trigger_latency}ms"
                )
                if brownout_level:
                    print(f"   Level: {data.get('level', 'UNKNOWN')}")

                return trigger_latency, data

            # Safety timeout - if no brownout after reasonable time
            if time.perf_counter() - t0 > 120:  # 2 minutes max wait
                print("⚠️  No brownout after 120s - test may have failed")
                return None, data

            time.sleep(poll_interval)

    def wait_for_recovery(self) -> Optional[int]:
        """
        Wait for Guardian to recover to NORMAL state with RAM < 75%
        Returns: recovery_time_seconds or None if timeout
        """
        t0 = time.perf_counter()
        poll_interval = 1.0  # 1s polling for recovery

        print(f"🔄 Waiting for recovery to NORMAL (budget: {RECOVER_BUDGET_S}s)...")

        while True:
            data = self.poll_guardian()
            current_state = data.get("status", "UNKNOWN")
            ram_pct = data.get("metrics", {}).get("ram_pct", 100)

            # Recovery conditions: NORMAL state AND RAM < 75%
            if current_state == "NORMAL" and ram_pct < 75:
                recovery_time = int(time.perf_counter() - t0)
                print(
                    f"🟢 Recovery complete: NORMAL state, RAM {ram_pct:.1f}% after {recovery_time}s"
                )
                return recovery_time

            # Timeout check
            elapsed = time.perf_counter() - t0
            if elapsed > RECOVER_BUDGET_S + 30:  # 30s grace period
                print(f"❌ Recovery timeout after {elapsed:.1f}s")
                return None

            if elapsed % 10 == 0:  # Progress update every 10s
                print(
                    f"   Still recovering... {current_state}, RAM {ram_pct:.1f}% ({elapsed:.0f}s)"
                )

            time.sleep(poll_interval)

    def close(self):
        """Close HTTP client"""
        self.client.close()


def write_guardian_event(payload: Dict[str, Any], run_dir: str):
    """Write Guardian event to JSONL log"""
    run_dir = pathlib.Path(run_dir)
    run_dir.mkdir(parents=True, exist_ok=True)

    # Add version and timestamp if not present
    if "v" not in payload:
        payload["v"] = "1"
    if "ts" not in payload:
        payload["ts"] = datetime.utcnow().isoformat() + "Z"

    log_file = run_dir / "guardian_events.jsonl"
    with open(log_file, "a", encoding="utf-8", buffering=1) as f:
        f.write(json.dumps(payload, ensure_ascii=False) + "\n")


def write_slo_result(
    run_dir: str, trigger_ms: Optional[int], recovery_s: Optional[int]
) -> bool:
    """Write SLO compliance result"""
    run_dir = pathlib.Path(run_dir)

    # Evaluate SLO compliance
    trigger_ok = trigger_ms is not None and trigger_ms <= TRIGGER_BUDGET_MS
    recovery_ok = recovery_s is not None and recovery_s <= RECOVER_BUDGET_S
    overall_pass = trigger_ok and recovery_ok

    result = {
        "slo_compliance": {
            "trigger_latency_ms": trigger_ms,
            "trigger_budget_ms": TRIGGER_BUDGET_MS,
            "trigger_pass": trigger_ok,
            "recovery_time_s": recovery_s,
            "recovery_budget_s": RECOVER_BUDGET_S,
            "recovery_pass": recovery_ok,
            "overall_pass": overall_pass,
        },
        "timestamp": datetime.utcnow().isoformat() + "Z",
    }

    # Write detailed JSON result
    with open(run_dir / "slo_result.json", "w") as f:
        json.dump(result, f, indent=2, ensure_ascii=False)

    # Write simple PASS/FAIL
    with open(run_dir / "result.txt", "w") as f:
        f.write("PASS" if overall_pass else "FAIL")

    return overall_pass
