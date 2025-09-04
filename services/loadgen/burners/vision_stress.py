"""
Vision Stress - RTSP camera requests if available
=================================================
"""

import os
import time
from typing import Any, Dict

import httpx

# Configuration
API_BASE = os.getenv("API_BASE", "http://localhost:8000")
CAMERA_RTSP_URL = os.getenv("CAMERA_RTSP_URL", None)

# Swedish vision request templates
VISION_REQUESTS = [
    {
        "text": "Visa kameran vid ytterdörren",
        "intent": "VISION.DETECT",
        "expected_response": "camera",
    },
    {
        "text": "Kolla vad som händer utomhus nu",
        "intent": "VISION.MONITOR",
        "expected_response": "outdoor",
    },
    {
        "text": "Ta en bild från säkerhetskameran",
        "intent": "VISION.CAPTURE",
        "expected_response": "capture",
    },
    {
        "text": "Finns det någon rörelse vid entrén?",
        "intent": "VISION.MOTION",
        "expected_response": "motion",
    },
    {
        "text": "Analysera vad som syns i kameraflödet",
        "intent": "VISION.ANALYZE",
        "expected_response": "analysis",
    },
]


def create_vision_request(session_id: str, request_id: int) -> Dict[str, Any]:
    """Create a vision processing request"""
    import random

    template = random.choice(VISION_REQUESTS)

    request = {
        "v": "1",
        "session_id": f"{session_id}_vision_{request_id}",
        "lang": "sv",
        "text": template["text"],
        "intent": template["intent"],
        "route_hint": "vision",  # Force vision processing
        "context": {
            "vision_enabled": True,
            "camera_source": "rtsp" if CAMERA_RTSP_URL else "mock",
        },
    }

    # Add RTSP URL if available
    if CAMERA_RTSP_URL:
        request["context"]["rtsp_url"] = CAMERA_RTSP_URL

    return request


def send_vision_request(
    client: httpx.Client, request: Dict[str, Any]
) -> Dict[str, Any]:
    """Send a single vision processing request"""
    start_time = time.perf_counter()

    try:
        response = client.post(
            f"{API_BASE}/api/orchestrator/ingest",
            json=request,
            timeout=20.0,  # Vision processing can take longer
        )

        duration_ms = int((time.perf_counter() - start_time) * 1000)

        # Check if response mentions vision/camera processing
        response_text = response.text if response.status_code == 200 else ""
        vision_processed = any(
            keyword in response_text.lower()
            for keyword in ["kamera", "bild", "video", "rtsp", "vision"]
        )

        return {
            "status_code": response.status_code,
            "duration_ms": duration_ms,
            "success": response.status_code == 200,
            "vision_processed": vision_processed,
            "has_rtsp": CAMERA_RTSP_URL is not None,
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


def run(seconds: int = 30) -> Dict[str, Any]:
    """
    Run vision stress test

    Args:
        seconds: Duration to run test

    Returns:
        Test results with vision processing stats
    """
    session_id = f"loadgen_vision_{int(time.time())}"

    if CAMERA_RTSP_URL:
        print(f"📹 Starting Vision Stress: RTSP camera for {seconds}s")
        print(f"   RTSP URL: {CAMERA_RTSP_URL}")
    else:
        print(f"📹 Starting Vision Stress: Mock camera for {seconds}s")
        print("   Note: No RTSP URL configured - using mock responses")

    start_time = time.perf_counter()
    end_time = start_time + seconds
    results = []
    request_counter = 0

    with httpx.Client(timeout=20.0) as client:
        while time.perf_counter() < end_time:
            # Create and send vision request
            request = create_vision_request(session_id, request_counter)
            result = send_vision_request(client, request)
            results.append(result)
            request_counter += 1

            # Progress update
            elapsed = time.perf_counter() - start_time
            if request_counter % 3 == 0 or elapsed >= seconds:
                print(
                    f"   Sent {request_counter} vision requests "
                    f"({elapsed:.1f}s elapsed)"
                )

            # Pace requests - vision processing is heavy
            time.sleep(2.0)  # 2 second intervals

    # Calculate statistics
    total_requests = len(results)
    successful_requests = sum(1 for r in results if r["success"])
    vision_processed = sum(1 for r in results if r.get("vision_processed", False))
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

    result_summary = {
        "test_type": "vision_stress",
        "duration_s": seconds,
        "camera_type": "rtsp" if CAMERA_RTSP_URL else "mock",
        "rtsp_url_configured": CAMERA_RTSP_URL is not None,
        "total_requests": total_requests,
        "successful_requests": successful_requests,
        "success_rate": success_rate,
        "vision_processed": vision_processed,
        "vision_processing_rate": (
            vision_processed / total_requests if total_requests > 0 else 0
        ),
        "avg_duration_ms": round(avg_duration, 1),
        "max_duration_ms": max_duration,
        "intent_distribution": intent_counts,
        "requests_per_minute": round((total_requests / seconds) * 60, 1),
    }

    print(
        f"   Completed: {successful_requests}/{total_requests} requests "
        f"({success_rate:.1%} success)"
    )
    if vision_processed > 0:
        print(
            f"   Vision processed: {vision_processed}/{total_requests} "
            f"({vision_processed/total_requests:.1%})"
        )
    print(f"   Avg duration: {avg_duration:.1f}ms")

    return result_summary
