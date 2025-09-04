"""
Guardian Health Schema v1 - Production-tight JSON schemas per blueprint
========================================================================
"""

import json
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional


@dataclass
class GuardianHealthPayloadV1:
    """Guardian health payload schema v1"""

    v: str = "1"
    ts: str = ""
    state: str = "NORMAL"
    level: Optional[str] = None  # LIGHT/MODERATE/HEAVY for brownout
    ram_pct: float = 0.0
    cpu_pct: float = 0.0
    temp_c: Optional[float] = None
    battery_pct: Optional[float] = None
    p95: Dict[str, float] = None
    error_budget: Dict[str, Any] = None
    brownout_reason: Optional[str] = None
    since_s: float = 0.0

    def __post_init__(self):
        if not self.ts:
            self.ts = datetime.utcnow().isoformat() + "Z"
        if self.p95 is None:
            self.p95 = {
                "fast_ms": 0.0,
                "planner_first_ms": 0.0,
                "planner_full_ms": 0.0,
                "deep_first_ms": 0.0,
                "deep_full_ms": 0.0,
            }
        if self.error_budget is None:
            self.error_budget = {"window_min": 5, "r429_rate": 0.0, "r5xx_rate": 0.0}


@dataclass
class SLOWindowResultV1:
    """SLO window result schema v1 for dashboard/trends"""

    v: str = "1"
    window: str = ""  # "2025-08-31T11:30:00Z/2025-08-31T11:35:00Z"
    p95: Dict[str, float] = None
    error_budget: Dict[str, float] = None
    ram_peak_mb: float = 0.0
    guardian_state: str = "NORMAL"
    health_score: int = 100

    def __post_init__(self):
        if self.p95 is None:
            self.p95 = {
                "fast_ms": 0.0,
                "planner_first_ms": 0.0,
                "planner_full_ms": 0.0,
                "deep_first_ms": 0.0,
                "deep_full_ms": 0.0,
            }
        if self.error_budget is None:
            self.error_budget = {"r429_rate": 0.0, "r5xx_rate": 0.0}


class GuardianHealthLogger:
    """Production JSONL logger for Guardian health data"""

    def __init__(self, base_path: str = "/data/telemetry"):
        self.base_path = Path(base_path)
        self.current_date = None
        self.log_file = None

    def _ensure_log_file(self):
        """Ensure log file is open for current date"""
        today = datetime.utcnow().strftime("%Y-%m-%d")

        if today != self.current_date:
            if self.log_file:
                self.log_file.close()

            self.current_date = today
            log_dir = self.base_path / today
            log_dir.mkdir(parents=True, exist_ok=True)

            self.log_file = open(log_dir / "guardian.jsonl", "a", encoding="utf-8")

    def log_guardian_health(self, health_payload: GuardianHealthPayloadV1):
        """Log Guardian health payload to JSONL"""
        self._ensure_log_file()

        json_line = json.dumps(asdict(health_payload), ensure_ascii=False)
        self.log_file.write(json_line + "\n")
        self.log_file.flush()

    def log_slo_window(self, window_result: SLOWindowResultV1):
        """Log SLO window result to JSONL"""
        self._ensure_log_file()

        json_line = json.dumps(asdict(window_result), ensure_ascii=False)
        self.log_file.write(json_line + "\n")
        self.log_file.flush()

    def close(self):
        """Close log file"""
        if self.log_file:
            self.log_file.close()
            self.log_file = None


# Global logger instance
_health_logger = GuardianHealthLogger()


def log_guardian_health_v1(
    state: str = "NORMAL",
    level: Optional[str] = None,
    ram_pct: float = 0.0,
    cpu_pct: float = 0.0,
    temp_c: Optional[float] = None,
    battery_pct: Optional[float] = None,
    p95_metrics: Optional[Dict[str, float]] = None,
    error_rates: Optional[Dict[str, float]] = None,
    brownout_reason: Optional[str] = None,
    since_s: float = 0.0,
):
    """Log Guardian health event with v1 schema"""

    payload = GuardianHealthPayloadV1(
        state=state,
        level=level,
        ram_pct=ram_pct,
        cpu_pct=cpu_pct,
        temp_c=temp_c,
        battery_pct=battery_pct,
        p95=p95_metrics or {},
        error_budget={
            "window_min": 5,
            "r429_rate": error_rates.get("r429_rate", 0.0) if error_rates else 0.0,
            "r5xx_rate": error_rates.get("r5xx_rate", 0.0) if error_rates else 0.0,
        },
        brownout_reason=brownout_reason,
        since_s=since_s,
    )

    _health_logger.log_guardian_health(payload)


def log_slo_window_v1(
    window_start: datetime,
    window_end: datetime,
    p95_metrics: Dict[str, float],
    error_budget: Dict[str, float],
    ram_peak_mb: float,
    guardian_state: str,
    health_score: int,
):
    """Log 5-minute SLO window result with v1 schema"""

    window_str = f"{window_start.isoformat()}Z/{window_end.isoformat()}Z"

    result = SLOWindowResultV1(
        window=window_str,
        p95=p95_metrics,
        error_budget=error_budget,
        ram_peak_mb=ram_peak_mb,
        guardian_state=guardian_state,
        health_score=health_score,
    )

    _health_logger.log_slo_window(result)


# Example usage functions
def create_sample_guardian_health() -> Dict[str, Any]:
    """Create sample Guardian health payload for testing"""

    payload = GuardianHealthPayloadV1(
        state="BROWNOUT",
        level="LIGHT",
        ram_pct=91.3,
        cpu_pct=72.4,
        temp_c=79.8,
        battery_pct=100.0,
        p95={
            "fast_ms": 280,
            "planner_first_ms": 980,
            "planner_full_ms": 1600,
            "deep_first_ms": 2100,
            "deep_full_ms": 3400,
        },
        error_budget={"window_min": 5, "r429_rate": 0.012, "r5xx_rate": 0.003},
        brownout_reason="SOFT_TRIGGER_RAM",
        since_s=17.4,
    )

    return asdict(payload)


def create_sample_slo_window() -> Dict[str, Any]:
    """Create sample SLO window result for testing"""

    result = SLOWindowResultV1(
        window="2025-08-31T11:30:00Z/2025-08-31T11:35:00Z",
        p95={
            "fast_ms": 232,
            "planner_first_ms": 871,
            "planner_full_ms": 1420,
            "deep_first_ms": 1760,
            "deep_full_ms": 2960,
        },
        error_budget={"r429_rate": 0.004, "r5xx_rate": 0.001},
        ram_peak_mb=8123,
        guardian_state="NORMAL",
        health_score=97,
    )

    return asdict(result)
