"""
Shadow mode evaluator and canary router
"""

import hashlib
import json
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Dict

import structlog

from .models import CanaryConfig, PlannerComparison, ShadowEvent, ShadowResponse

logger = structlog.get_logger(__name__)


class ShadowEvaluator:
    """Evaluates primary vs shadow planner responses"""

    def __init__(self):
        self.eval_dir = Path(os.getenv("SHADOW_EVAL_DIR", "data/shadow_eval"))
        self.eval_dir.mkdir(parents=True, exist_ok=True)

    def compare_responses(
        self, primary_result: Dict[str, Any], shadow_result: Dict[str, Any]
    ) -> PlannerComparison:
        """Compare primary and shadow planner responses"""

        # Extract key fields
        primary_tool = primary_result.get("tool", "none")
        shadow_tool = shadow_result.get("tool", "none")

        # Extract intent - planner v1 doesn't have intent field, so derive from tool
        primary_intent = primary_result.get("intent")
        if primary_intent is None or primary_intent == "none":
            # Derive intent from tool for planner v1
            if primary_tool == "email.create_draft":
                primary_intent = "email"
            elif primary_tool == "calendar.create_draft":
                primary_intent = "calendar"
            elif primary_tool == "weather.lookup":
                primary_intent = "weather"
            elif primary_tool == "memory.query":
                primary_intent = "memory"
            else:
                primary_intent = "none"

        shadow_intent = shadow_result.get("intent", "none")
        primary_schema_ok = primary_result.get("schema_ok", False)
        shadow_schema_ok = shadow_result.get("schema_ok", False)

        # Get complexity level from classifier result
        complexity = primary_result.get("complexity", "MEDIUM")
        level = primary_result.get(
            "level", complexity.lower()
        )  # Map HARD -> hard, MEDIUM -> medium, etc.

        # Calculate latency delta
        primary_latency = primary_result.get("total_time_ms", 0)
        shadow_latency = shadow_result.get("total_time_ms", 0)
        latency_delta = shadow_latency - primary_latency

        # Calculate response similarity
        primary_text = primary_result.get("text", "")
        shadow_text = shadow_result.get("text", "")
        similarity = self._calculate_similarity(primary_text, shadow_text)

        # Normalize args for comparison
        primary_args = self._canonical_args(
            primary_result.get("args", {}), primary_tool
        )
        shadow_args = self._canonical_args(shadow_result.get("args", {}), shadow_tool)

        return PlannerComparison(
            intent_match=primary_intent == shadow_intent,
            schema_ok_both=primary_schema_ok and shadow_schema_ok,
            tool_choice_same=primary_tool == shadow_tool,
            latency_delta_ms=latency_delta,
            response_similarity=similarity,
            level=level,
            canary_eligible=False,  # Will be set by canary router
            canary_routed=False,  # Will be set by canary router
            rollback_reason=None,  # Will be set if rollback occurs
        )

    def _calculate_similarity(self, text1: str, text2: str) -> float:
        """Calculate similarity between two JSON responses"""
        try:
            # Parse JSON and compare structure
            json1 = json.loads(text1) if text1 else {}
            json2 = json.loads(text2) if text2 else {}

            # Simple similarity based on tool choice
            if json1.get("tool") == json2.get("tool"):
                return 1.0
            else:
                return 0.0
        except:
            return 0.0

    def _canonical_args(self, args: Dict[str, Any], tool: str) -> Dict[str, Any]:
        """Normalize args to canonical form for comparison"""
        if not isinstance(args, dict):
            return {}

        canonical = args.copy()

        # Add defaults based on tool
        if tool == "calendar.create_draft":
            if "title" not in canonical:
                canonical["title"] = ""
            if "start_iso" not in canonical:
                canonical["start_iso"] = "now+30m"
            if "duration_min" not in canonical:
                canonical["duration_min"] = 30
            if "attendees" not in canonical:
                canonical["attendees"] = []
            if "timezone" not in canonical:
                canonical["timezone"] = "Europe/Stockholm"

        elif tool == "weather.lookup":
            if "location" not in canonical:
                canonical["location"] = "Stenungsund"
            if "unit" not in canonical:
                canonical["unit"] = "metric"

        elif tool == "email.create_draft":
            if "to" not in canonical:
                canonical["to"] = []
            if "subject" not in canonical:
                canonical["subject"] = ""
            if "body" not in canonical:
                canonical["body"] = ""
            if "importance" not in canonical:
                canonical["importance"] = "normal"

        return canonical

    def log_event(self, event: ShadowEvent) -> None:
        """Log shadow evaluation event"""
        try:
            # Write to JSONL file
            event_file = (
                self.eval_dir
                / f"shadow_events_{datetime.utcnow().strftime('%Y-%m-%d')}.jsonl"
            )
            with open(event_file, "a") as f:
                f.write(event.model_dump_json() + "\n")

            logger.info(
                "Shadow event logged",
                session_id=event.session_id,
                trace_id=event.trace_id,
                intent_match=event.comparison.intent_match,
                tool_choice_same=event.comparison.tool_choice_same,
                canary_routed=event.canary_routed,
            )
        except Exception as e:
            logger.error("Failed to log shadow event", error=str(e))


class CanaryRouter:
    """Routes requests between primary and shadow planners based on canary config"""

    def __init__(self):
        self.config = self._load_config()
        self.evaluator = ShadowEvaluator()

    def _load_config(self) -> CanaryConfig:
        """Load canary configuration from environment"""
        return CanaryConfig(
            enabled=os.getenv("PLANNER_CANARY_ENABLED", "0") == "1",
            percentage=float(os.getenv("PLANNER_CANARY_PERCENT", "5.0")),
            min_schema_ok=float(os.getenv("PLANNER_CANARY_MIN_SCHEMA_OK", "0.95")),
            min_intent_match=float(
                os.getenv("PLANNER_CANARY_MIN_INTENT_MATCH", "0.90")
            ),
            evaluation_window_hours=int(
                os.getenv("PLANNER_CANARY_EVAL_WINDOW_HOURS", "24")
            ),
            allowed_levels=os.getenv("PLANNER_CANARY_LEVELS", "easy,medium").split(","),
            max_latency_delta_ms=float(os.getenv("PLANNER_CANARY_MAX_LAT_MS", "150.0")),
        )

    def should_route_canary(
        self, session_id: str, comparison: PlannerComparison
    ) -> bool:
        """Determine if request should be routed via canary"""
        if not self.config.enabled:
            return False

        # Check if session qualifies for canary (hash-based selection)
        session_hash = int(hashlib.md5(session_id.encode()).hexdigest()[:8], 16)
        canary_threshold = (self.config.percentage / 100.0) * 0xFFFFFFFF

        if session_hash > canary_threshold:
            return False

        # Check level gate (EASY+MEDIUM only)
        if comparison.level not in self.config.allowed_levels:
            return False

        # Check quality gates
        if not comparison.schema_ok_both:
            return False

        if not comparison.intent_match:
            return False

        # Check latency gate
        if comparison.latency_delta_ms > self.config.max_latency_delta_ms:
            return False

        return True

    async def evaluate_shadow(
        self,
        session_id: str,
        message: str,
        primary_result: Dict[str, Any],
        shadow_result: Dict[str, Any],
        trace_id: str,
    ) -> ShadowResponse:
        """Evaluate primary vs shadow results and determine canary routing"""

        # Compare responses
        comparison = self.evaluator.compare_responses(primary_result, shadow_result)

        # Determine canary eligibility and rollback reason
        canary_eligible = self.should_route_canary(session_id, comparison)
        canary_routed = (
            canary_eligible and comparison.schema_ok_both and comparison.intent_match
        )

        # Determine rollback reason if not eligible
        rollback_reason = None
        if not canary_eligible:
            if comparison.level not in self.config.allowed_levels:
                rollback_reason = "level_blocked"
            elif not comparison.schema_ok_both:
                rollback_reason = "schema_fail"
            elif not comparison.intent_match:
                rollback_reason = "intent_mismatch"
            elif comparison.latency_delta_ms > self.config.max_latency_delta_ms:
                rollback_reason = "latency_regress"
            else:
                rollback_reason = "hash_not_selected"

        # Update comparison with canary info
        comparison.canary_eligible = canary_eligible
        comparison.canary_routed = canary_routed
        comparison.rollback_reason = rollback_reason

        # Create response
        response = ShadowResponse(
            session_id=session_id,
            trace_id=trace_id,
            primary_result=primary_result,
            shadow_result=shadow_result,
            comparison=comparison.model_dump(),
            canary_eligible=canary_eligible,
            canary_routed=canary_routed,
        )

        # Log event
        event = ShadowEvent(
            session_id=session_id,
            trace_id=trace_id,
            primary_result=primary_result,
            shadow_result=shadow_result,
            comparison=comparison,
            canary_eligible=canary_eligible,
            canary_routed=canary_routed,
        )
        self.evaluator.log_event(event)

        logger.info(
            "Shadow evaluation completed",
            session_id=session_id,
            trace_id=trace_id,
            intent_match=comparison.intent_match,
            tool_choice_same=comparison.tool_choice_same,
            canary_eligible=canary_eligible,
            canary_routed=canary_routed,
            latency_delta_ms=comparison.latency_delta_ms,
        )

        return response
