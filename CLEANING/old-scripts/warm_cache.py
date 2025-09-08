#!/usr/bin/env python3
"""
Cache warming script for Alice v2
Pre-populates semantic cache with regression scenarios for faster responses
"""

import asyncio
from pathlib import Path

import aiohttp
import yaml


async def warm_cache(
    base_url: str = "http://localhost:18000", regression_dir: str = "eval/regression"
):
    """Warm the cache with regression scenarios"""

    # Load scenarios
    scenarios = []
    regression_path = Path(regression_dir)

    if not regression_path.exists():
        print(f"❌ Regression directory not found: {regression_dir}")
        return

    for yaml_file in regression_path.glob("*.yml"):
        with open(yaml_file, "r", encoding="utf-8") as f:
            scenario = yaml.safe_load(f)
            scenarios.append(scenario)

    print(f"🔥 Warming cache with {len(scenarios)} scenarios...")

    # Warm cache with EASY/MEDIUM scenarios only (HARD scenarios change too much)
    easy_medium_scenarios = [s for s in scenarios if "HARD" not in s.get("tags", [])]

    print(f"📊 Warming {len(easy_medium_scenarios)} EASY/MEDIUM scenarios...")

    # Make requests to populate cache
    async with aiohttp.ClientSession() as session:
        tasks = []

        for scenario in easy_medium_scenarios:
            payload = {
                "v": "1",
                "message": scenario["prompt_sv"],
                "session_id": f"warm_{scenario['id']}",
            }

            task = session.post(
                f"{base_url}/api/orchestrator/chat",
                json=payload,
                headers={"Content-Type": "application/json"},
            )
            tasks.append(task)

        # Execute all requests concurrently
        responses = await asyncio.gather(*tasks, return_exceptions=True)

        # Count successful cache warmings
        successful = 0
        for i, response in enumerate(responses):
            if isinstance(response, Exception):
                print(
                    f"❌ Failed to warm cache for scenario {easy_medium_scenarios[i]['id']}: {response}"
                )
            else:
                successful += 1
                if i < 5:  # Show first 5 responses
                    print(
                        f"✅ Warmed cache: {easy_medium_scenarios[i]['prompt_sv'][:30]}..."
                    )

    print(
        f"🎉 Cache warming complete: {successful}/{len(easy_medium_scenarios)} scenarios cached"
    )


async def check_cache_status(base_url: str = "http://localhost:18000"):
    """Check cache status and hit rates"""

    try:
        async with aiohttp.ClientSession() as session:
            # Test a few scenarios to check cache hits
            test_scenarios = [
                "Vad är klockan?",
                "Vad är vädret i Stockholm?",
                "Hej!",
                "Boka ett möte imorgon kl 14:00",
            ]

            print("🔍 Testing cache hit rates...")

            for scenario in test_scenarios:
                payload = {
                    "v": "1",
                    "message": scenario,
                    "session_id": f"cache_test_{hash(scenario) % 1000}",
                }

                start_time = asyncio.get_event_loop().time()

                async with session.post(
                    f"{base_url}/api/orchestrator/chat",
                    json=payload,
                    headers={"Content-Type": "application/json"},
                ) as response:
                    response_data = await response.json()
                    end_time = asyncio.get_event_loop().time()

                    latency_ms = (end_time - start_time) * 1000
                    print(f"📊 '{scenario[:20]}...' → {latency_ms:.0f}ms")

    except Exception as e:
        print(f"❌ Error checking cache status: {e}")


def main():
    """Main cache warming function"""
    import argparse

    parser = argparse.ArgumentParser(description="Alice v2 Cache Warming")
    parser.add_argument(
        "--base-url", default="http://localhost:18000", help="Base URL for Alice API"
    )
    parser.add_argument(
        "--regression-dir",
        default="eval/regression",
        help="Directory with regression scenarios",
    )
    parser.add_argument(
        "--check-only", action="store_true", help="Only check cache status, don't warm"
    )

    args = parser.parse_args()

    if args.check_only:
        asyncio.run(check_cache_status(args.base_url))
    else:
        asyncio.run(warm_cache(args.base_url, args.regression_dir))
        print("\n" + "=" * 50)
        asyncio.run(check_cache_status(args.base_url))


if __name__ == "__main__":
    main()
