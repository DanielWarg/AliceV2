"""
Build RL dataset from Alice telemetry.

Extracts episodes from JSONL telemetry files and creates training datasets
for routing, tool selection, and preference modeling.
"""

from __future__ import annotations

import argparse
import json
import pathlib
from typing import Any, Dict, List, Optional

import structlog

try:
    import pandas as pd
except ImportError:
    pd = None

from rl.reward import turn_reward
from rl.utils.io import find_files, iter_jsonl, peek_jsonl_schema

logger = structlog.get_logger(__name__)


def extract_tool_info(tools_data: Any) -> tuple[bool, str]:
    """
    Extract tool success and primary tool name.

    Args:
        tools_data: Tools field from telemetry (various formats)

    Returns:
        (tool_success, primary_tool_name)
    """
    if not tools_data:
        return False, "none"

    # Handle different tool data formats
    if isinstance(tools_data, list):
        if not tools_data:
            return False, "none"

        # Check if all tools succeeded
        tool_success = True
        primary_tool = "none"

        for tool in tools_data:
            if isinstance(tool, dict):
                tool_ok = tool.get("success", False) and tool.get("schema_ok", True)
                if not tool_ok:
                    tool_success = False

                # Get primary tool name
                if not primary_tool or primary_tool == "none":
                    primary_tool = tool.get("name", "unknown")

        return tool_success, primary_tool

    elif isinstance(tools_data, dict):
        # Single tool object
        tool_success = tools_data.get("success", False) and tools_data.get(
            "schema_ok", True
        )
        primary_tool = tools_data.get("name", "unknown")
        return tool_success, primary_tool

    elif isinstance(tools_data, str):
        # Tool name only
        return True, tools_data  # Assume success if just name provided

    return False, "none"


def _flatten_event(event: Dict[str, Any]) -> Dict[str, Any]:
    """
    Flatten Alice telemetry event into standardized episode format.

    Args:
        event: Raw event from telemetry

    Returns:
        Standardized episode dict
    """
    # Extract core fields with multiple fallbacks
    intent = (
        event.get("intent") or event.get("nlu", {}).get("intent")
        if isinstance(event.get("nlu"), dict)
        else None or event.get("detected_intent") or "unknown"
    )

    # Language detection
    lang = (
        event.get("lang")
        or event.get("language")
        or event.get("locale", "").split("-")[0]  # en-US -> en
        or "sv"  # Default to Swedish
    )

    # Input text extraction
    text = ""
    if event.get("input"):
        if isinstance(event["input"], dict):
            text = event["input"].get("text", "")
        else:
            text = str(event["input"])
    else:
        text = event.get("text", "") or event.get("message", "")

    # Tool analysis
    tools_data = event.get("tools", [])
    tool_ok, primary_tool = extract_tool_info(tools_data)

    # Performance metrics
    latency_ms = float(event.get("latency_ms") or event.get("latencyMs") or 0.0)
    cost_usd = float(event.get("cost_usd") or event.get("costUsd") or 0.0)

    # Success detection with multiple indicators
    success = bool(
        event.get("success")
        or event.get("status") == "ok"
        or event.get("status") == "success"
        or (event.get("response") and not event.get("error"))
    )

    # Cache and guardian state
    cache_hit = bool(event.get("cache_hit") or event.get("cacheHit", False))
    guardian_state = event.get("guardian_state", "NORMAL")
    guard_flag = bool(
        guardian_state == "LOCKDOWN"
        or event.get("guard_flag")
        or event.get("blocked")
        or event.get("flagged")
    )

    # Route extraction (for training)
    route = (
        event.get("route")
        or event.get("model_route")
        or event.get("model_used")
        or event.get("metadata", {}).get("route")
        if isinstance(event.get("metadata"), dict)
        else None or "micro"  # Default
    )

    # NLU confidence if available
    intent_confidence = 0.0
    if isinstance(event.get("nlu"), dict):
        intent_confidence = float(event["nlu"].get("confidence", 0.0))
    elif event.get("intent_confidence"):
        intent_confidence = float(event.get("intent_confidence", 0.0))

    # Propensities for IPS (if logged)
    route_propensity = float(event.get("route_propensity", 1.0))
    tool_propensity = float(event.get("tool_propensity", 1.0))

    # Session context
    session_id = event.get("session_id") or event.get("sessionId", "")
    user_id = event.get("user_id") or event.get("userId", "")
    timestamp = event.get("timestamp") or event.get("ts") or 0

    # Build standardized episode
    episode = {
        # Core identification
        "session_id": session_id,
        "user_id": user_id,
        "timestamp": timestamp,
        "trace_id": event.get("trace_id", ""),
        # Input features
        "intent": str(intent).lower(),
        "lang": str(lang).lower(),
        "text_len": len(str(text)),
        "word_count": len(str(text).split()) if text else 0,
        "intent_confidence": intent_confidence,
        # Performance metrics
        "latency_ms": latency_ms,
        "cost_usd": cost_usd,
        # Outcomes
        "success": success,
        "tool_ok": tool_ok,
        "cache_hit": cache_hit,
        "guard_flag": guard_flag,
        # Actions taken
        "route": str(route).lower(),
        "tool_primary": str(primary_tool).lower(),
        # Context
        "guardian_state": guardian_state,
        # IPS weights
        "route_propensity": route_propensity,
        "tool_propensity": tool_propensity,
        # Raw event for debugging
        "raw_event_type": event.get("event_type", ""),
    }

    # Calculate reward
    episode["reward"] = turn_reward(
        success=success,
        tool_ok=tool_ok,
        latency_ms=latency_ms,
        cost_usd=cost_usd,
        cache_hit=cache_hit,
        guard_flag=guard_flag,
    )

    return episode


def load_telemetry_data(
    telemetry_dir: pathlib.Path,
    tests_dir: Optional[pathlib.Path] = None,
    max_events: Optional[int] = None,
) -> List[Dict[str, Any]]:
    """
    Load telemetry data from multiple sources.

    Args:
        telemetry_dir: Directory with telemetry JSONL files
        tests_dir: Optional directory with test results
        max_events: Maximum events to load

    Returns:
        List of flattened episodes
    """
    episodes = []

    # Load telemetry events
    telemetry_files = find_files(telemetry_dir, "events_*.jsonl*")
    if not telemetry_files:
        # Try broader pattern
        telemetry_files = find_files(telemetry_dir, "*.jsonl*")

    logger.info("Found telemetry files", count=len(telemetry_files))

    # Peek at schema first
    if telemetry_files:
        schema = peek_jsonl_schema(telemetry_files[:3], sample_size=50)
        logger.info(
            "Telemetry schema preview",
            common_fields=list(schema.get("common_fields", {}).keys())[:10],
            unique_fields=schema.get("unique_fields", 0),
        )

    event_count = 0
    for file_path in telemetry_files:
        logger.info("Processing telemetry file", path=str(file_path))

        for event in iter_jsonl(file_path):
            # Filter for turn events
            event_type = event.get("event_type") or event.get("type") or ""
            if event_type and event_type not in {
                "turn",
                "turn_completed",
                "response",
                "chat",
            }:
                continue

            # Skip events without basic required fields
            if not (event.get("intent") or event.get("text") or event.get("message")):
                continue

            episode = _flatten_event(event)
            episodes.append(episode)
            event_count += 1

            if max_events and event_count >= max_events:
                logger.info("Reached max_events limit", max_events=max_events)
                break

        if max_events and event_count >= max_events:
            break

    # Load test results if provided
    if tests_dir and tests_dir.exists():
        test_files = find_files(tests_dir, "results*.jsonl*")
        logger.info("Found test files", count=len(test_files))

        for file_path in test_files:
            for event in iter_jsonl(file_path):
                # Test results should have intent/route info
                if event.get("intent") or event.get("route"):
                    episode = _flatten_event(event)
                    episodes.append(episode)
                    event_count += 1

                    if max_events and event_count >= max_events:
                        break

            if max_events and event_count >= max_events:
                break

    logger.info("Loaded episodes", total=len(episodes), from_telemetry=len(episodes))

    if not episodes:
        raise ValueError(
            "No valid episodes found. Check telemetry directory and file patterns."
        )

    return episodes


def create_preference_pairs(episodes: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Create preference pairs for DPO training.

    Uses heuristic: successful + fast responses preferred over failed/slow ones.

    Args:
        episodes: List of episode dicts

    Returns:
        List of preference pairs
    """
    # Group by intent for fair comparison
    intent_groups = {}
    for episode in episodes:
        intent = episode.get("intent", "unknown")
        if intent not in intent_groups:
            intent_groups[intent] = []
        intent_groups[intent].append(episode)

    pairs = []

    for intent, group in intent_groups.items():
        if len(group) < 2:
            continue

        # Sort by preference: success first, then by latency
        group.sort(
            key=lambda x: (
                -int(x.get("success", False)),  # Success first (negative for desc)
                -int(x.get("tool_ok", False)),  # Tool success second
                x.get("latency_ms", float("inf")),  # Then by latency (asc)
                x.get("cost_usd", float("inf")),  # Then by cost (asc)
            )
        )

        # Create pairs between best and worst quartiles
        n = len(group)
        best_quartile = group[: max(1, n // 4)]
        worst_quartile = group[max(1, 3 * n // 4) :]

        for chosen in best_quartile:
            for rejected in worst_quartile:
                # Only create pair if there's a meaningful difference
                if (
                    chosen.get("success", False) != rejected.get("success", False)
                    or abs(chosen.get("latency_ms", 0) - rejected.get("latency_ms", 0))
                    > 100
                ):
                    pairs.append(
                        {
                            "context": {
                                "intent": intent,
                                "lang": chosen.get("lang", "sv"),
                                "text_len": chosen.get("text_len", 0),
                            },
                            "chosen": {
                                "success": chosen.get("success", False),
                                "latency_ms": chosen.get("latency_ms", 0),
                                "tool_ok": chosen.get("tool_ok", False),
                                "route": chosen.get("route", ""),
                                "reward": chosen.get("reward", 0),
                            },
                            "rejected": {
                                "success": rejected.get("success", False),
                                "latency_ms": rejected.get("latency_ms", 0),
                                "tool_ok": rejected.get("tool_ok", False),
                                "route": rejected.get("route", ""),
                                "reward": rejected.get("reward", 0),
                            },
                        }
                    )

                    # Limit pairs per intent to avoid imbalance
                    if (
                        len([p for p in pairs if p["context"]["intent"] == intent])
                        >= 10
                    ):
                        break

            if len([p for p in pairs if p["context"]["intent"] == intent]) >= 10:
                break

    logger.info(
        "Created preference pairs", total=len(pairs), intents=len(intent_groups)
    )

    return pairs


def main():
    """Main entry point for dataset building."""
    parser = argparse.ArgumentParser(
        description="Build RL dataset from Alice telemetry"
    )
    parser.add_argument(
        "--telemetry", required=True, help="Directory with telemetry JSONL files"
    )
    parser.add_argument("--tests", help="Directory with test results JSONL files")
    parser.add_argument("--out", required=True, help="Output file (.parquet or .csv)")
    parser.add_argument("--prefs", help="Output preference pairs for DPO (.jsonl)")
    parser.add_argument("--max-events", type=int, help="Maximum events to process")
    parser.add_argument(
        "--sample-schema",
        action="store_true",
        help="Just sample and show schema, don't build dataset",
    )

    args = parser.parse_args()

    # Setup logging
    structlog.configure(
        processors=[structlog.dev.ConsoleRenderer()],
        logger_factory=structlog.stdlib.LoggerFactory(),
    )

    telemetry_dir = pathlib.Path(args.telemetry)
    tests_dir = pathlib.Path(args.tests) if args.tests else None
    output_path = pathlib.Path(args.out)

    # Validate inputs
    if not telemetry_dir.exists():
        raise ValueError(f"Telemetry directory not found: {telemetry_dir}")

    if tests_dir and not tests_dir.exists():
        logger.warning("Tests directory not found", path=tests_dir)
        tests_dir = None

    # Just show schema if requested
    if args.sample_schema:
        logger.info("Sampling schema only...")
        files = find_files(telemetry_dir)
        if files:
            schema = peek_jsonl_schema(files[:5], sample_size=100)
            print(json.dumps(schema, indent=2))
        return

    try:
        # Load data
        episodes = load_telemetry_data(
            telemetry_dir=telemetry_dir, tests_dir=tests_dir, max_events=args.max_events
        )

        # Create output directory
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # Save episodes
        if pd is not None and output_path.suffix == ".parquet":
            df = pd.DataFrame(episodes)
            df.to_parquet(output_path, index=False)
            logger.info(
                "Saved episodes to parquet", path=output_path, count=len(episodes)
            )
        else:
            # Fallback to CSV
            if pd is not None:
                df = pd.DataFrame(episodes)
                csv_path = output_path.with_suffix(".csv")
                df.to_csv(csv_path, index=False)
                logger.info("Saved episodes to CSV", path=csv_path, count=len(episodes))
            else:
                # Pure JSON fallback
                json_path = output_path.with_suffix(".jsonl")
                with open(json_path, "w", encoding="utf-8") as f:
                    for episode in episodes:
                        json.dump(episode, f, ensure_ascii=False)
                        f.write("\\n")
                logger.info(
                    "Saved episodes to JSONL", path=json_path, count=len(episodes)
                )

        # Create preference pairs if requested
        if args.prefs:
            prefs_path = pathlib.Path(args.prefs)
            prefs_path.parent.mkdir(parents=True, exist_ok=True)

            pairs = create_preference_pairs(episodes)

            with open(prefs_path, "w", encoding="utf-8") as f:
                for pair in pairs:
                    json.dump(pair, f, ensure_ascii=False)
                    f.write("\\n")

            logger.info("Saved preference pairs", path=prefs_path, count=len(pairs))

        # Summary statistics
        from rl.reward import analyze_rewards

        stats = analyze_rewards(episodes)
        logger.info("Dataset statistics", **stats)

    except Exception as e:
        logger.error("Dataset building failed", error=str(e))
        raise


if __name__ == "__main__":
    main()
