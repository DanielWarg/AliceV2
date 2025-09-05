"""
Alice v2 Structured Data Collection
Production-ready logging system for telemetry, evaluation, and training data
"""

import hashlib
import json
import os
import pathlib
import re
import time
from contextlib import contextmanager
from datetime import datetime
from threading import Lock
from typing import Any, Dict, Optional, Tuple

import structlog

logger = structlog.get_logger(__name__)

# Thread-safe logging setup
_log_lock = Lock()
_log_file = None
_log_dir = None


def initialize_logging(base_dir: str = None):
    """Initialize thread-safe logging infrastructure"""
    global _log_file, _log_dir

    # Default to test-results directory in development
    if base_dir is None:
        # Find project root by looking for git directory
        current_dir = pathlib.Path(__file__).parent
        while current_dir.parent != current_dir:
            if (current_dir / ".git").exists():
                base_dir = str(current_dir / "test-results" / "telemetry")
                break
            current_dir = current_dir.parent
        else:
            # Fallback to relative path
            base_dir = str(
                pathlib.Path(__file__).parent.parent.parent.parent
                / "test-results"
                / "telemetry"
            )

    _log_dir = pathlib.Path(os.getenv("LOG_DIR", base_dir)) / time.strftime("%Y-%m-%d")
    _log_dir.mkdir(parents=True, exist_ok=True)

    if _log_file is None:
        _log_file = open(_log_dir / "events.jsonl", "a", buffering=1, encoding="utf-8")


def mask_pii(text: str) -> Tuple[str, bool]:
    """
    Mask PII in text according to Swedish privacy requirements
    Returns: (masked_text, was_modified)
    """
    patterns = {
        # Email addresses
        r"\b[\w.-]+@[\w.-]+\.\w+\b": "<EMAIL>",
        # Swedish phone numbers (+46 or 0-prefixed)
        r"\b(?:\+46|0)[1-9]\d{8,9}\b": "<PHONE>",
        # Swedish personnummer (YYYYMMDD-XXXX or YYMMDD-XXXX)
        r"\b\d{6,8}-\d{4}\b": "<PERSONNUMMER>",
        # Swedish names (capitalized words, common Swedish pattern)
        r"\b[A-ZÅÄÖ][a-zåäö]+ [A-ZÅÄÖ][a-zåäö]+(?:\s[A-ZÅÄÖ][a-zåäö]+)*\b": "<FULLNAME>",
        # Swedish addresses (contains "gatan", "vägen", etc.)
        r"\b\w+(?:gatan|vägen|torget|platsen)\s+\d+[A-Za-z]?\b": "<ADDRESS>",
        # Credit card numbers (basic pattern)
        r"\b\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}\b": "<CREDITCARD>",
    }

    modified = False
    masked_text = text

    for pattern, replacement in patterns.items():
        if re.search(pattern, masked_text, re.IGNORECASE):
            masked_text = re.sub(pattern, replacement, masked_text, flags=re.IGNORECASE)
            modified = True

    return masked_text, modified


def normalize_swedish_dates(text: str) -> str:
    """
    Normalize Swedish relative dates to ISO format
    Examples: "imorgon" -> "2025-09-01", "nästa vecka" -> "2025-09-07"
    """
    from datetime import datetime, timedelta

    now = datetime.now()
    tomorrow = now + timedelta(days=1)
    next_week = now + timedelta(days=7)

    replacements = {
        r"\bimorgon\b": tomorrow.strftime("%Y-%m-%d"),
        r"\bidag\b": now.strftime("%Y-%m-%d"),
        r"\bigår\b": (now - timedelta(days=1)).strftime("%Y-%m-%d"),
        r"\bnästa vecka\b": next_week.strftime("%Y-%m-%d"),
        r"\bnästa månad\b": (now + timedelta(days=30)).strftime("%Y-%m-%d"),
    }

    normalized_text = text
    for pattern, replacement in replacements.items():
        normalized_text = re.sub(
            pattern, replacement, normalized_text, flags=re.IGNORECASE
        )

    return normalized_text


def calculate_hash(payload: Dict[str, Any]) -> str:
    """Calculate deterministic hash for deduplication"""
    # Remove timestamps and non-deterministic fields for consistent hashing
    hash_payload = {
        k: v for k, v in payload.items() if k not in ["ts", "hash", "session_id"]
    }

    hash_content = json.dumps(hash_payload, sort_keys=True, ensure_ascii=False)
    return f"sha256:{hashlib.sha256(hash_content.encode()).hexdigest()}"


@contextmanager
def logging_context(session_id: str, user_id: str = "anon"):
    """Context manager for session-based logging"""
    context = {
        "session_id": session_id,
        "user_id": user_id,
        "start_time": time.perf_counter(),
    }

    try:
        yield context
    finally:
        # Log session completion
        log_event(
            {
                "event": "session.complete",
                "session_id": session_id,
                "duration_s": time.perf_counter() - context["start_time"],
            }
        )


def log_event(payload: Dict[str, Any]):
    """
    Thread-safe structured event logging with PII protection

    Args:
        payload: Event data to log
    """
    global _log_file, _log_lock

    if _log_file is None:
        initialize_logging()

    with _log_lock:
        # Ensure required fields
        payload["v"] = payload.get("v", "1")
        payload["ts"] = datetime.utcnow().isoformat() + "Z"

        # PII masking for all text fields
        pii_masked = False

        if "input" in payload and isinstance(payload["input"], dict):
            if "text" in payload["input"]:
                original_text = payload["input"]["text"]
                masked_text, was_masked = mask_pii(original_text)
                normalized_text = normalize_swedish_dates(masked_text)
                payload["input"]["text"] = normalized_text
                pii_masked = pii_masked or was_masked

        if "output" in payload and isinstance(payload["output"], dict):
            if "text_sv" in payload["output"]:
                original_text = payload["output"]["text_sv"]
                masked_text, was_masked = mask_pii(original_text)
                payload["output"]["text_sv"] = masked_text
                pii_masked = pii_masked or was_masked

        payload["pii_masked"] = pii_masked

        # Generate hash for deduplication
        payload["hash"] = calculate_hash(payload)

        # Atomic write
        try:
            _log_file.write(json.dumps(payload, ensure_ascii=False) + "\n")
            _log_file.flush()
        except Exception as e:
            # Fallback logging to stderr if main logging fails

            logger.error("Logging failed", error=str(e))


def log_test_event(test_name: str, **kwargs):
    """Convenience function for test event logging"""

    event_data = {
        "event": "test.execution",
        "test_name": test_name,
        "component": "orchestrator",
        **kwargs,
    }

    log_event(event_data)


def log_performance_baseline(
    test_name: str,
    metrics: Dict[str, Any],
    environment: Optional[Dict[str, Any]] = None,
):
    """Log performance metrics for regression detection"""

    baseline_event = {
        "event": "test.baseline",
        "test_name": test_name,
        "component": "orchestrator",
        "metrics": metrics,
        "environment": environment or {},
        "slo_compliance": {
            "api_response_p95": metrics.get("p95_ms", 0) < 100,
            "guardian_response": metrics.get("guardian_ms", 0) < 150,
            "success_rate": metrics.get("success_rate", 0) >= 0.95,
        },
    }

    log_event(baseline_event)


def log_test_failure(test_name: str, failure_info: Dict[str, Any]):
    """Log detailed failure information for learning"""

    failure_event = {
        "event": "test.failure",
        "test_name": test_name,
        "failure_type": failure_info.get("type"),
        "root_cause": failure_info.get("root_cause"),
        "system_state": failure_info.get("system_state", {}),
        "stack_trace": failure_info.get("stack_trace"),
        "reproduction_steps": failure_info.get("steps", []),
        "impact_assessment": {
            "severity": failure_info.get("severity", "MEDIUM"),
            "user_impact": failure_info.get("user_impact"),
            "system_stability": failure_info.get("system_stability", "UNKNOWN"),
        },
    }

    log_event(failure_event)


def log_orchestrator_turn(
    session_id: str,
    turn_id: str,
    user_input: str,
    response: Dict[str, Any],
    metrics: Dict[str, Any],
    guardian_state: Dict[str, Any],
    consent_scopes: list = None,
):
    """Log a complete orchestrator turn for training data"""

    turn_event = {
        "event": "orchestrator.turn",
        "session_id": session_id,
        "turn_id": turn_id,
        "lang": "sv",
        "input": {
            "text": user_input,
            "audio_ref": None,
        },  # Will be populated by voice service
        "nlu": response.get("nlu", {}),
        "guardian": guardian_state,
        "route": response.get("route", "micro"),
        "rag": response.get("rag", {}),
        "tool_calls": response.get("tool_calls", []),
        "llm": response.get("llm", {}),
        "output": response.get("output", {}),
        "metrics": metrics,
        "consent_scopes": consent_scopes or [],
        "test_metadata": {"environment": "test", "version": "1.0.0"},
    }

    log_event(turn_event)


# Data quality validation functions
def validate_schema_compliance(log_file_path: str) -> float:
    """Check what percentage of logged events comply with schema"""
    total_events = 0
    valid_events = 0

    required_fields = ["v", "event", "ts", "hash"]

    try:
        with open(log_file_path, "r", encoding="utf-8") as f:
            for line in f:
                total_events += 1
                try:
                    event = json.loads(line.strip())
                    if all(field in event for field in required_fields):
                        valid_events += 1
                except json.JSONDecodeError:
                    continue
    except FileNotFoundError:
        return 0.0

    return valid_events / total_events if total_events > 0 else 0.0


def check_pii_masking_coverage(log_file_path: str) -> float:
    """Check what percentage of events have PII properly masked"""
    total_events = 0
    masked_events = 0

    try:
        with open(log_file_path, "r", encoding="utf-8") as f:
            for line in f:
                total_events += 1
                try:
                    event = json.loads(line.strip())
                    if event.get("pii_masked", False):
                        masked_events += 1
                except json.JSONDecodeError:
                    continue
    except FileNotFoundError:
        return 0.0

    return masked_events / total_events if total_events > 0 else 0.0


def calculate_duplicate_percentage(log_file_path: str) -> float:
    """Calculate percentage of duplicate events (same hash)"""
    seen_hashes = set()
    total_events = 0
    duplicate_events = 0

    try:
        with open(log_file_path, "r", encoding="utf-8") as f:
            for line in f:
                total_events += 1
                try:
                    event = json.loads(line.strip())
                    event_hash = event.get("hash")
                    if event_hash:
                        if event_hash in seen_hashes:
                            duplicate_events += 1
                        else:
                            seen_hashes.add(event_hash)
                except json.JSONDecodeError:
                    continue
    except FileNotFoundError:
        return 0.0

    return duplicate_events / total_events if total_events > 0 else 0.0


# Cleanup function
def cleanup_old_logs(retention_days: int = 7):
    """Remove log files older than retention_days"""
    if _log_dir is None:
        return

    import datetime

    cutoff_date = datetime.datetime.now() - datetime.timedelta(days=retention_days)

    base_dir = _log_dir.parent
    for date_dir in base_dir.glob("????-??-??"):
        try:
            dir_date = datetime.datetime.strptime(date_dir.name, "%Y-%m-%d")
            if dir_date < cutoff_date:
                import shutil

                shutil.rmtree(date_dir)
                logger.info("Removed old log directory", directory=str(date_dir))
        except ValueError:
            # Invalid date format, skip
            continue


# Initialize logging on module import
initialize_logging()
