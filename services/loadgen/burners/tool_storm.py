"""
Tool Storm - Burst planner + tool requests (calendar/email)
===========================================================
"""

import os
import random
import time
from typing import Any, Dict

import httpx

# Configuration
API_BASE = os.getenv("API_BASE", "http://localhost:8000")

# Swedish tool request templates
TOOL_REQUESTS = [
    # Calendar/Time requests
    {
        "text": "Sätt påminnelse 13:50 imorgon om tandläkartid",
        "intent": "TIME.REMIND",
        "expected_tools": ["calendar", "reminder"],
    },
    {
        "text": "Boka möte med Anna nästa tisdag klockan 14:00",
        "intent": "TIME.BOOK",
        "expected_tools": ["calendar", "scheduling"],
    },
    {
        "text": "Vilka möten har jag på fredag?",
        "intent": "TIME.CHECK",
        "expected_tools": ["calendar"],
    },
    {
        "text": "Flytta mitt 15:00-möte till 16:30 samma dag",
        "intent": "TIME.RESCHEDULE",
        "expected_tools": ["calendar"],
    },
    # Email requests
    {
        "text": "Skicka mejl till johan@exempel.se om projektuppdatering",
        "intent": "EMAIL.SEND",
        "expected_tools": ["email", "compose"],
    },
    {
        "text": "Har jag fått några viktiga mejl idag?",
        "intent": "EMAIL.CHECK",
        "expected_tools": ["email", "filter"],
    },
    {
        "text": "Svara på det senaste mejlet från Maria",
        "intent": "EMAIL.REPLY",
        "expected_tools": ["email", "compose"],
    },
    # Mixed complex requests
    {
        "text": "Kolla kalendern och skicka mejl till deltagarna om vi flyttar mötet",
        "intent": "COMPLEX.MULTI",
        "expected_tools": ["calendar", "email", "compose"],
    },
    {
        "text": "Sätt upp veckomöte med teamet varje måndag 09:00",
        "intent": "TIME.RECURRING",
        "expected_tools": ["calendar", "recurring"],
    },
    {
        "text": "Hitta ledig tid för 2-timmars workshop nästa vecka",
        "intent": "TIME.FIND_SLOT",
        "expected_tools": ["calendar", "availability"],
    },
]


def create_tool_request(session_id: str, request_id: int) -> Dict[str, Any]:
    """Create a tool-heavy request"""
    template = random.choice(TOOL_REQUESTS)

    return {
        "v": "1",
        "session_id": f"{session_id}_tool_{request_id}",
        "lang": "sv",
        "text": template["text"],
        "intent": template["intent"],
        "route_hint": "planner",  # Force planner route for tool usage
        "context": {
            "tools_enabled": True,
            "expected_tools": template.get("expected_tools", []),
        },
    }


def send_tool_request(client: httpx.Client, request: Dict[str, Any]) -> Dict[str, Any]:
    """Send a single tool request"""
    start_time = time.perf_counter()

    try:
        response = client.post(
            f"{API_BASE}/api/orchestrator/ingest",
            json=request,
            timeout=15.0,  # Tools can take longer
        )

        duration_ms = int((time.perf_counter() - start_time) * 1000)

        # Check if response mentions tools (basic validation)
        response_text = response.text if response.status_code == 200 else ""
        tools_mentioned = any(
            tool in response_text.lower()
            for tool in ["kalender", "mejl", "påminnelse", "möte"]
        )

        return {
            "status_code": response.status_code,
            "duration_ms": duration_ms,
            "success": response.status_code == 200,
            "tools_detected": tools_mentioned,
            "session_id": request["session_id"],
            "intent": request["intent"],
        }

    except Exception as e:
        duration_ms = int((time.perf_counter() - start_time) * 1000)
        return {
            "status_code": 0,
            "duration_ms": duration_ms,
            "success": False,
            "error": str(e),
            "session_id": request["session_id"],
            "intent": request.get("intent", "UNKNOWN"),
        }


def run(rps: float = 2.0, seconds: int = 20) -> Dict[str, Any]:
    """
    Run tool storm stress test

    Args:
        rps: Requests per second rate
        seconds: Duration to run test

    Returns:
        Test results with tool usage stats
    """
    session_id = f"loadgen_tools_{int(time.time())}"

    print(f"🔨 Starting Tool Storm: {rps} RPS for {seconds}s")

    start_time = time.perf_counter()
    end_time = start_time + seconds
    results = []
    request_counter = 0

    with httpx.Client(timeout=15.0) as client:
        while time.perf_counter() < end_time:
            request_start = time.perf_counter()

            # Create and send request
            request = create_tool_request(session_id, request_counter)
            result = send_tool_request(client, request)
            results.append(result)
            request_counter += 1

            # Rate limiting
            request_time = time.perf_counter() - request_start
            target_interval = 1.0 / max(0.1, rps)  # Minimum 0.1 RPS
            sleep_time = max(0, target_interval - request_time)

            if sleep_time > 0:
                time.sleep(sleep_time)

            # Progress update
            if request_counter % 5 == 0:
                elapsed = time.perf_counter() - start_time
                current_rps = request_counter / elapsed if elapsed > 0 else 0
                print(
                    f"   Sent {request_counter} tool requests "
                    f"({current_rps:.1f} RPS)"
                )

    # Calculate statistics
    total_requests = len(results)
    successful_requests = sum(1 for r in results if r["success"])
    tools_detected = sum(1 for r in results if r.get("tools_detected", False))
    success_rate = successful_requests / total_requests if total_requests > 0 else 0

    # Response time statistics
    durations = [r["duration_ms"] for r in results if r["success"]]
    avg_duration = sum(durations) / len(durations) if durations else 0
    max_duration = max(durations) if durations else 0

    # Intent distribution
    intent_counts = {}
    for result in results:
        intent = result.get("intent", "UNKNOWN")
        intent_counts[intent] = intent_counts.get(intent, 0) + 1

    actual_rps = total_requests / seconds if seconds > 0 else 0

    result_summary = {
        "test_type": "tool_storm",
        "target_rps": rps,
        "actual_rps": round(actual_rps, 2),
        "duration_s": seconds,
        "total_requests": total_requests,
        "successful_requests": successful_requests,
        "success_rate": success_rate,
        "tools_detected": tools_detected,
        "tool_detection_rate": (
            tools_detected / total_requests if total_requests > 0 else 0
        ),
        "avg_duration_ms": round(avg_duration, 1),
        "max_duration_ms": max_duration,
        "intent_distribution": intent_counts,
    }

    print(
        f"   Completed: {successful_requests}/{total_requests} requests "
        f"({success_rate:.1%} success)"
    )
    print(
        f"   Tools detected: {tools_detected}/{total_requests} "
        f"({tools_detected/total_requests:.1%})"
    )
    print(f"   Avg duration: {avg_duration:.1f}ms")

    return result_summary
