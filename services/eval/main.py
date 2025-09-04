#!/usr/bin/env python3
"""
Alice v2 Eval Harness v1
Nightly evaluation service with 20 test scenarios
"""

import asyncio
import json
import os
import time
from datetime import datetime
from typing import Any, Dict, List

import httpx
import structlog

logger = structlog.get_logger(__name__)

# Test scenarios
SCENARIOS = [
    {
        "id": "book_meeting",
        "name": "Book a meeting",
        "message": "Boka ett möte imorgon kl 14:00 med Anna",
        "expected_tool": "calendar.create",
        "expected_route": "planner",
    },
    {
        "id": "send_email",
        "name": "Send email",
        "message": "Skicka ett mail till kund@firma.se om projektuppdatering",
        "expected_tool": "email.send",
        "expected_route": "planner",
    },
    {
        "id": "weather_check",
        "name": "Check weather",
        "message": "Vad är vädret i Stockholm idag?",
        "expected_tool": "weather.current",
        "expected_route": "micro",
    },
    {
        "id": "web_search",
        "name": "Web search",
        "message": "Sök efter senaste nyheterna om AI",
        "expected_tool": "web.search",
        "expected_route": "micro",
    },
    {
        "id": "translate_text",
        "name": "Translate text",
        "message": "Översätt 'Hello world' till svenska",
        "expected_tool": "translate.swedish",
        "expected_route": "micro",
    },
    {
        "id": "math_calculation",
        "name": "Math calculation",
        "message": "Beräkna 15% av 2500 kr",
        "expected_tool": "math.calculate",
        "expected_route": "micro",
    },
    {
        "id": "news_fetch",
        "name": "Fetch news",
        "message": "Visa mig de senaste nyheterna",
        "expected_tool": "news.latest",
        "expected_route": "micro",
    },
    {
        "id": "music_play",
        "name": "Play music",
        "message": "Spela låten 'Shape of You'",
        "expected_tool": "music.spotify",
        "expected_route": "micro",
    },
    {
        "id": "vision_detect",
        "name": "Vision detection",
        "message": "Analysera bilden från kameran",
        "expected_tool": "vision.rtsp",
        "expected_route": "deep",
    },
    {
        "id": "complex_planning",
        "name": "Complex planning",
        "message": "Planera en resa till Japan med flera städer och aktiviteter",
        "expected_tool": "planner.create",
        "expected_route": "deep",
    },
    {
        "id": "email_draft",
        "name": "Draft email",
        "message": "Skriv ett utkast till ett mail om projektstatus",
        "expected_tool": "email.draft",
        "expected_route": "planner",
    },
    {
        "id": "calendar_read",
        "name": "Read calendar",
        "message": "Visa min kalender för nästa vecka",
        "expected_tool": "calendar.read",
        "expected_route": "micro",
    },
    {
        "id": "weather_forecast",
        "name": "Weather forecast",
        "message": "Vad blir vädret i Göteborg på fredag?",
        "expected_tool": "weather.forecast",
        "expected_route": "micro",
    },
    {
        "id": "web_browse",
        "name": "Web browse",
        "message": "Besök hemsidan för svenska regeringen",
        "expected_tool": "web.browse",
        "expected_route": "micro",
    },
    {
        "id": "translate_english",
        "name": "Translate to English",
        "message": "Översätt 'Hej världen' till engelska",
        "expected_tool": "translate.english",
        "expected_route": "micro",
    },
    {
        "id": "math_estimate",
        "name": "Math estimate",
        "message": "Uppskatta hur många personer som bor i Sverige",
        "expected_tool": "math.estimate",
        "expected_route": "micro",
    },
    {
        "id": "news_trending",
        "name": "Trending news",
        "message": "Visa mig trendande nyheter just nu",
        "expected_tool": "news.trending",
        "expected_route": "micro",
    },
    {
        "id": "music_search",
        "name": "Music search",
        "message": "Sök efter låtar av Ed Sheeran",
        "expected_tool": "music.search",
        "expected_route": "micro",
    },
    {
        "id": "vision_snapshot",
        "name": "Vision snapshot",
        "message": "Ta en bild och analysera vad du ser",
        "expected_tool": "vision.snapshot",
        "expected_route": "deep",
    },
    {
        "id": "simple_qa",
        "name": "Simple Q&A",
        "message": "Vad är huvudstaden i Sverige?",
        "expected_tool": None,
        "expected_route": "micro",
    },
]


class EvalHarness:
    def __init__(self, api_base: str = "http://localhost:8000"):
        self.api_base = api_base
        self.client = httpx.AsyncClient(timeout=30.0)
        self.results: List[Dict[str, Any]] = []

    async def run_scenario(self, scenario: Dict[str, Any]) -> Dict[str, Any]:
        """Kör ett test scenario"""
        start_time = time.time()

        try:
            # Skicka chat request
            response = await self.client.post(
                f"{self.api_base}/api/orchestrator/chat",
                json={
                    "session_id": f"eval-{scenario['id']}",
                    "message": scenario["message"],
                    "model": "micro",
                },
                headers={"Authorization": "Bearer test-key-123"},
            )

            response_time = int((time.time() - start_time) * 1000)

            if response.status_code == 200:
                data = response.json()

                # Analysera response
                success = True
                tool_used = None
                route_used = "micro"  # Default för nu

                # TODO: Parse response för att hitta tool usage
                # För nu antar vi att micro route används

                result = {
                    "v": "1",
                    "ts": datetime.utcnow().isoformat() + "Z",
                    "id": scenario["id"],
                    "trace_id": data.get("trace_id", "unknown"),
                    "ok": success,
                    "route": route_used,
                    "p95_ms": response_time,
                    "tool_used": tool_used,
                    "errors": {"klass": None},
                    "guardian": "NORMAL",  # TODO: Get från Guardian
                    "expected_tool": scenario["expected_tool"],
                    "expected_route": scenario["expected_route"],
                    "success": success,
                }

            else:
                result = {
                    "v": "1",
                    "ts": datetime.utcnow().isoformat() + "Z",
                    "id": scenario["id"],
                    "trace_id": "error",
                    "ok": False,
                    "route": "error",
                    "p95_ms": response_time,
                    "tool_used": None,
                    "errors": {"klass": "5xx"},
                    "guardian": "ERROR",
                    "expected_tool": scenario["expected_tool"],
                    "expected_route": scenario["expected_route"],
                    "success": False,
                    "error": f"HTTP {response.status_code}",
                }

        except Exception as e:
            response_time = int((time.time() - start_time) * 1000)

            result = {
                "v": "1",
                "ts": datetime.utcnow().isoformat() + "Z",
                "id": scenario["id"],
                "trace_id": "exception",
                "ok": False,
                "route": "error",
                "p95_ms": response_time,
                "tool_used": None,
                "errors": {"klass": "timeout"},
                "guardian": "ERROR",
                "expected_tool": scenario["expected_tool"],
                "expected_route": scenario["expected_route"],
                "success": False,
                "error": str(e),
            }

        return result

    async def run_all_scenarios(self) -> List[Dict[str, Any]]:
        """Kör alla test scenarios"""
        logger.info("Starting eval harness", total_scenarios=len(SCENARIOS))

        results = []
        for i, scenario in enumerate(SCENARIOS, 1):
            logger.info(
                f"Running scenario {i}/{len(SCENARIOS)}", scenario_id=scenario["id"]
            )

            result = await self.run_scenario(scenario)
            results.append(result)

            # Liten paus mellan requests
            await asyncio.sleep(0.5)

        logger.info("Eval harness completed", total_results=len(results))
        return results

    def check_slo_compliance(self, results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Kontrollera SLO compliance"""
        success_count = sum(1 for r in results if r.get("success", False))
        success_rate = success_count / len(results) if results else 0

        # SLO thresholds
        min_success_rate = 0.80  # 80% success rate
        max_p95_micro = 250  # 250ms P95 för micro
        max_p95_planner = 1500  # 1500ms P95 för planner
        max_p95_deep = 3000  # 3000ms P95 för deep

        # Beräkna P95 per route
        micro_latencies = [r["p95_ms"] for r in results if r.get("route") == "micro"]
        planner_latencies = [
            r["p95_ms"] for r in results if r.get("route") == "planner"
        ]
        deep_latencies = [r["p95_ms"] for r in results if r.get("route") == "deep"]

        def p95(values: List[int]) -> int:
            if not values:
                return 0
            sorted_values = sorted(values)
            index = int(len(sorted_values) * 0.95)
            return sorted_values[index]

        p95_micro = p95(micro_latencies)
        p95_planner = p95(planner_latencies)
        p95_deep = p95(deep_latencies)

        # SLO compliance
        slo_passed = (
            success_rate >= min_success_rate
            and p95_micro <= max_p95_micro
            and p95_planner <= max_p95_planner
            and p95_deep <= max_p95_deep
        )

        return {
            "slo_passed": slo_passed,
            "success_rate": success_rate,
            "min_success_rate": min_success_rate,
            "p95_micro": p95_micro,
            "max_p95_micro": max_p95_micro,
            "p95_planner": p95_planner,
            "max_p95_planner": max_p95_planner,
            "p95_deep": p95_deep,
            "max_p95_deep": max_p95_deep,
            "total_scenarios": len(results),
            "successful_scenarios": success_count,
        }

    def write_results(self, results: List[Dict[str, Any]], slo_check: Dict[str, Any]):
        """Skriv results till JSONL fil"""
        os.makedirs("data/tests", exist_ok=True)

        # Skriv individuella results
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        results_file = f"data/tests/results_{timestamp}.jsonl"

        with open(results_file, "w", encoding="utf-8") as f:
            for result in results:
                f.write(json.dumps(result) + "\n")

        # Skriv summary
        summary = {
            "v": "1",
            "ts": datetime.utcnow().isoformat() + "Z",
            "eval_run_id": timestamp,
            "slo_compliance": slo_check,
            "results_file": results_file,
            "total_scenarios": len(results),
        }

        summary_file = f"data/tests/summary_{timestamp}.json"
        with open(summary_file, "w", encoding="utf-8") as f:
            json.dump(summary, f, indent=2)

        logger.info(
            "Results written", results_file=results_file, summary_file=summary_file
        )

        return results_file, summary_file


async def main():
    """Main entry point"""
    api_base = os.getenv("API_BASE", "http://localhost:8000")

    harness = EvalHarness(api_base)

    try:
        # Kör alla scenarios
        results = await harness.run_all_scenarios()

        # Kontrollera SLO compliance
        slo_check = harness.check_slo_compliance(results)

        # Skriv results
        results_file, summary_file = harness.write_results(results, slo_check)

        # Logga resultat
        logger.info(
            "Eval harness completed",
            slo_passed=slo_check["slo_passed"],
            success_rate=slo_check["success_rate"],
            p95_micro=slo_check["p95_micro"],
        )

        # Exit code baserat på SLO compliance
        if not slo_check["slo_passed"]:
            logger.error("SLO compliance failed", slo_check=slo_check)
            exit(1)
        else:
            logger.info("SLO compliance passed", slo_check=slo_check)
            exit(0)

    except Exception as e:
        logger.error("Eval harness failed", error=str(e))
        exit(1)


if __name__ == "__main__":
    asyncio.run(main())
