"""
Deep LLM Bomb - Stress test Deep processing with heavy prompts
=============================================================
"""

import concurrent.futures
import os
import time
from typing import Any, Dict

import httpx

# Configuration
API_BASE = os.getenv("API_BASE", "http://localhost:8000")
DEEP_PROMPT_TOKENS = int(os.getenv("DEEP_PROMPT_TOKENS", "1800"))
DEEP_CONCURRENCY = int(os.getenv("DEEP_CONCURRENCY", "2"))

# Swedish heavy text for realistic deep processing
HEAVY_SWEDISH_TEXT = (
    """
Analysera och sammanfatta följande komplexa svenska text noggrant och detaljerat. 
Fördjupningen kräver omfattande språkbehandling och kontextuell förståelse av svenska 
kulturella referenser, idiomatiska uttryck och komplicerade meningsstrukturer.

Sverige har en lång historia av teknologisk innovation som sträcker sig från Alfred Nobels 
dynamit till moderna företag som Spotify och Skype. Den svenska modellen kombinerar 
marknadsekonomi med stark välfärd och har skapat en unik balans mellan entreprenörskap 
och social trygghet. 

Denna text innehåller avsiktligt komplexa resonemang om ekonomi, teknik, kultur och 
samhälle för att maximera bearbetningstiden för språkmodeller. Svenska språkets 
särskilda egenskaper som sammansatta ord och böjningsmönster gör texten extra krävande 
att analysera korrekt.

Artificiell intelligens och maskininlärning blir alltmer centrala inom svensk industri. 
Från Ericssons 5G-teknik till H&M:s leveranskedjor använder svenska företag AI för att 
optimera processer och skapa konkurrensfördelar på den globala marknaden.
"""
    * 10
)  # Multiply to reach target token count


def create_deep_request(session_id: str, request_id: int) -> Dict[str, Any]:
    """Create a deep processing request"""
    # Trim text to approximate token count (4 chars ≈ 1 token for Swedish)
    text = HEAVY_SWEDISH_TEXT[: DEEP_PROMPT_TOKENS * 4]

    return {
        "v": "1",
        "session_id": f"{session_id}_deep_{request_id}",
        "lang": "sv",
        "text": text,
        "intent": "INFO.ANALYZE",
        "route_hint": "deep",  # Force deep processing
        "context": {"processing_mode": "comprehensive", "analysis_depth": "maximum"},
    }


def send_deep_request(client: httpx.Client, request: Dict[str, Any]) -> Dict[str, Any]:
    """Send a single deep processing request"""
    start_time = time.perf_counter()

    try:
        response = client.post(
            f"{API_BASE}/api/orchestrator/ingest", json=request, timeout=30.0
        )

        duration_ms = int((time.perf_counter() - start_time) * 1000)

        return {
            "status_code": response.status_code,
            "duration_ms": duration_ms,
            "success": response.status_code == 200,
            "session_id": request["session_id"],
        }

    except Exception as e:
        duration_ms = int((time.perf_counter() - start_time) * 1000)
        return {
            "status_code": 0,
            "duration_ms": duration_ms,
            "success": False,
            "error": str(e),
            "session_id": request["session_id"],
        }


def run(seconds: int = 30, concurrency: int = None) -> Dict[str, Any]:
    """
    Run deep bomb stress test

    Args:
        seconds: Duration to run test
        concurrency: Number of concurrent requests (default from env)

    Returns:
        Test results with success rate and timing stats
    """
    concurrency = concurrency or DEEP_CONCURRENCY
    session_id = f"loadgen_deep_{int(time.time())}"

    print(f"🧠 Starting Deep LLM bomb: {concurrency} concurrent for {seconds}s")
    print(f"   Target tokens per request: {DEEP_PROMPT_TOKENS}")

    start_time = time.perf_counter()
    end_time = start_time + seconds
    results = []
    request_counter = 0

    with httpx.Client(timeout=30.0) as client:
        while time.perf_counter() < end_time:
            # Launch concurrent batch
            batch_requests = []
            for i in range(concurrency):
                request = create_deep_request(session_id, request_counter)
                batch_requests.append(request)
                request_counter += 1

            # Execute batch concurrently
            with concurrent.futures.ThreadPoolExecutor(
                max_workers=concurrency
            ) as executor:
                futures = [
                    executor.submit(send_deep_request, client, req)
                    for req in batch_requests
                ]

                for future in concurrent.futures.as_completed(futures):
                    try:
                        result = future.result()
                        results.append(result)
                    except Exception as e:
                        results.append(
                            {
                                "status_code": 0,
                                "duration_ms": 0,
                                "success": False,
                                "error": f"Future error: {e}",
                            }
                        )

            # Brief pause to prevent overwhelming
            time.sleep(0.1)

    # Calculate statistics
    total_requests = len(results)
    successful_requests = sum(1 for r in results if r["success"])
    success_rate = successful_requests / total_requests if total_requests > 0 else 0

    durations = [r["duration_ms"] for r in results if r["success"]]
    avg_duration = sum(durations) / len(durations) if durations else 0
    max_duration = max(durations) if durations else 0

    result_summary = {
        "test_type": "deep_bomb",
        "duration_s": seconds,
        "concurrency": concurrency,
        "total_requests": total_requests,
        "successful_requests": successful_requests,
        "success_rate": success_rate,
        "avg_duration_ms": round(avg_duration, 1),
        "max_duration_ms": max_duration,
        "requests_per_second": round(total_requests / seconds, 2),
        "target_tokens": DEEP_PROMPT_TOKENS,
    }

    print(
        f"   Completed: {successful_requests}/{total_requests} requests "
        f"({success_rate:.1%} success rate)"
    )
    print(f"   Avg duration: {avg_duration:.1f}ms, Max: {max_duration}ms")

    return result_summary
