#!/usr/bin/env python3
"""
🧮 Simple Fibonacci Training - Alice v2 Cache Optimization
Simplified training utan external dependencies - använder curl direkt
"""

import json
import random
import subprocess
import time
from datetime import datetime

# Fibonacci constants
FIBONACCI_SEQUENCE = [
    1,
    1,
    2,
    3,
    5,
    8,
    13,
    21,
    34,
    55,
    89,
    144,
    233,
    377,
    610,
    987,
    1597,
    2584,
    4181,
    6765,
    10946,
    17711,
]
GOLDEN_RATIO = 1.618033988749


class SimpleFibonacciTraining:
    def __init__(self):
        self.orchestrator_url = "http://localhost:8000"
        self.results = []

        # Fast training phases
        self.phases = {
            "rapid_warm_up": {"queries": 21, "name": "Rapid Cache Warm-up"},
            "pattern_boost": {"queries": 34, "name": "Pattern Recognition"},
            "optimization_sprint": {"queries": 55, "name": "Fibonacci Optimization"},
        }

    def generate_training_queries(self):
        """Generate diverse queries för cache warming"""
        queries = [
            # Fibonacci & Golden Ratio queries
            "Vad är Fibonacci tal?",
            "What is Fibonacci sequence?",
            "Beräkna golden ratio",
            "Calculate 1.618",
            "Fibonacci sekvens förklaring",
            "Golden ratio explanation",
            "Vad är φ (phi)?",
            "Phi mathematical constant",
            # Common Alice queries
            "Vad är klockan?",
            "What time is it?",
            "Hej Alice",
            "Hello Alice",
            "Hjälp mig",
            "Help me",
            "Tack så mycket",
            "Thank you",
            # Swedish variations
            "Fibonacci i naturen",
            "Fibonacci in nature",
            "Golden ratio design",
            "Gyllene snittet",
            "Spiral patterns",
            "Spiral mönster",
            # Mathematical queries
            "1 + 1 = ?",
            "Beräkna 42 * 1.618",
            "What is 5 + 8?",
            "Calculate 13 * 21",
            "Math help",
            "Matematik hjälp",
            # System queries
            "System status",
            "Cache performance",
            "Response time",
            "Memory usage",
            "Health check",
            "Hälsokontroll",
        ]

        return queries

    def make_request(self, message, session_id):
        """Make HTTP request using curl"""
        payload = {
            "message": message,
            "session_id": session_id,
            "context": {"training": True, "fibonacci_optimization": True},
        }

        try:
            cmd = [
                "docker",
                "exec",
                "alice-orchestrator",
                "curl",
                "-s",
                "-X",
                "POST",
                "http://localhost:8000/api/orchestrator/chat",
                "-H",
                "Content-Type: application/json",
                "-d",
                json.dumps(payload),
            ]

            start_time = time.time()
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            end_time = time.time()

            response_time_ms = (end_time - start_time) * 1000

            if result.returncode == 0 and result.stdout.strip():
                try:
                    response_data = json.loads(result.stdout)
                    return {
                        "success": True,
                        "response_time_ms": response_time_ms,
                        "response": response_data,
                    }
                except json.JSONDecodeError:
                    return {
                        "success": False,
                        "response_time_ms": response_time_ms,
                        "error": "JSON decode error",
                    }
            else:
                return {
                    "success": False,
                    "response_time_ms": response_time_ms,
                    "error": result.stderr or "Request failed",
                }

        except subprocess.TimeoutExpired:
            return {
                "success": False,
                "response_time_ms": 30000,  # Timeout
                "error": "Request timeout",
            }
        except Exception as e:
            return {"success": False, "response_time_ms": 0, "error": str(e)}

    def get_cache_stats(self):
        """Get Redis cache statistics"""
        try:
            cmd = ["docker", "exec", "alice-cache", "redis-cli", "info", "stats"]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)

            if result.returncode == 0:
                lines = result.stdout.strip().split("\n")
                stats = {}
                for line in lines:
                    if ":" in line and not line.startswith("#"):
                        key, value = line.split(":", 1)
                        if key in ["keyspace_hits", "keyspace_misses"]:
                            stats[key] = int(value.strip())

                total_ops = stats.get("keyspace_hits", 0) + stats.get(
                    "keyspace_misses", 0
                )
                hit_rate = (
                    (stats.get("keyspace_hits", 0) / total_ops * 100)
                    if total_ops > 0
                    else 0
                )

                return {
                    "hits": stats.get("keyspace_hits", 0),
                    "misses": stats.get("keyspace_misses", 0),
                    "hit_rate": hit_rate,
                }
        except Exception as e:
            print(f"Cache stats error: {e}")

        return {"hits": 0, "misses": 0, "hit_rate": 0}

    def run_training_phase(self, phase_name, phase_config):
        """Run en träningsfas"""
        print(f"\n🧮 PHASE: {phase_config['name']}")
        print(
            f"Queries: {phase_config['queries']} | Target: Cache warming & pattern learning"
        )

        queries = self.generate_training_queries()
        selected_queries = random.choices(queries, k=phase_config["queries"])

        phase_results = {
            "phase": phase_name,
            "start_time": datetime.utcnow().isoformat(),
            "response_times": [],
            "successful_requests": 0,
            "failed_requests": 0,
        }

        for i, query in enumerate(selected_queries):
            session_id = f"fib_training_{phase_name}_{i}"

            print(
                f"  Request {i+1:2d}/{phase_config['queries']}: '{query[:40]}{'...' if len(query) > 40 else ''}' ",
                end="",
            )

            result = self.make_request(query, session_id)

            if result["success"]:
                phase_results["response_times"].append(result["response_time_ms"])
                phase_results["successful_requests"] += 1
                print(f"✅ {result['response_time_ms']:.0f}ms")
            else:
                phase_results["failed_requests"] += 1
                print(f"❌ {result.get('error', 'Failed')}")

            # Progress update every 10 requests
            if (i + 1) % 10 == 0:
                if phase_results["response_times"]:
                    avg_time = sum(phase_results["response_times"]) / len(
                        phase_results["response_times"]
                    )
                    cache_stats = self.get_cache_stats()

                    print(
                        f"    🎯 Progress: {i+1}/{phase_config['queries']} | "
                        f"Avg: {avg_time:.1f}ms | "
                        f"Cache: {cache_stats['hit_rate']:.1f}% hit rate"
                    )

            # Small delay mellan requests
            time.sleep(0.2)

        # Phase summary
        if phase_results["response_times"]:
            avg_time = sum(phase_results["response_times"]) / len(
                phase_results["response_times"]
            )
            min_time = min(phase_results["response_times"])
            max_time = max(phase_results["response_times"])

            phase_results.update(
                {
                    "avg_response_time": avg_time,
                    "min_response_time": min_time,
                    "max_response_time": max_time,
                }
            )

            print("\n📊 Phase Results:")
            print(f"    Average: {avg_time:.1f}ms")
            print(f"    Range: {min_time:.1f}ms - {max_time:.1f}ms")
            print(
                f"    Success Rate: {phase_results['successful_requests']}/{phase_config['queries']} "
                f"({phase_results['successful_requests']/phase_config['queries']*100:.1f}%)"
            )

        cache_stats = self.get_cache_stats()
        phase_results["cache_stats"] = cache_stats

        print(
            f"    Cache Stats: {cache_stats['hits']} hits, {cache_stats['misses']} misses "
            f"({cache_stats['hit_rate']:.1f}% hit rate)"
        )

        self.results.append(phase_results)
        return phase_results

    def run_full_training(self):
        """Run complete Fibonacci training loop"""
        print("🧮 FIBONACCI CACHE TRAINING STARTED")
        print(f"Timestamp: {datetime.utcnow().isoformat()}")
        print("Target: Improve from 417ms baseline → 35.9ms (38.2% improvement)")
        print(f"Golden Ratio: φ = {GOLDEN_RATIO}")

        # Initial cache stats
        initial_cache = self.get_cache_stats()
        print(f"Initial Cache: {initial_cache['hit_rate']:.1f}% hit rate")

        start_time = time.time()

        # Run all training phases
        for phase_name, phase_config in self.phases.items():
            try:
                self.run_training_phase(phase_name, phase_config)
            except KeyboardInterrupt:
                print(f"\n⚠️ Training interrupted during {phase_name}")
                break
            except Exception as e:
                print(f"\n❌ Phase {phase_name} failed: {e}")
                continue

        end_time = time.time()
        total_duration = end_time - start_time

        # Final analysis
        print("\n🎯 FIBONACCI TRAINING COMPLETE!")
        print(f"Duration: {total_duration/60:.1f} minutes")

        if self.results:
            all_response_times = []
            for result in self.results:
                if "response_times" in result:
                    all_response_times.extend(result["response_times"])

            if all_response_times:
                overall_avg = sum(all_response_times) / len(all_response_times)
                improvement = (417 - overall_avg) / 417 * 100

                print("\n📈 PERFORMANCE RESULTS:")
                print("    Baseline: 417ms (pre-training)")
                print(f"    Current: {overall_avg:.1f}ms (post-training)")
                print(f"    Improvement: {improvement:+.1f}%")
                print(
                    f"    Target Progress: {((417-overall_avg)/(417-35.9)*100):.1f}% towards 35.9ms goal"
                )

        # Final cache stats
        final_cache = self.get_cache_stats()
        print("\n💾 CACHE PERFORMANCE:")
        print(f"    Initial: {initial_cache['hit_rate']:.1f}% hit rate")
        print(f"    Final: {final_cache['hit_rate']:.1f}% hit rate")
        print(
            f"    Improvement: {final_cache['hit_rate'] - initial_cache['hit_rate']:+.1f} percentage points"
        )
        print("    Target: 70%+ hit rate")

        # Success evaluation
        success_criteria = {
            "performance_improved": len(all_response_times) > 0 and overall_avg < 417,
            "cache_improved": final_cache["hit_rate"] > initial_cache["hit_rate"],
            "target_progress": len(all_response_times) > 0
            and overall_avg < 300,  # Reasonable progress
        }

        successful_criteria = sum(success_criteria.values())
        print(f"\n✅ SUCCESS CRITERIA: {successful_criteria}/3")

        for criterion, met in success_criteria.items():
            status = "✅" if met else "❌"
            print(f"    {status} {criterion}")

        return {
            "duration_minutes": total_duration / 60,
            "phases_completed": len(self.results),
            "overall_avg_ms": overall_avg if all_response_times else None,
            "performance_improvement_pct": improvement if all_response_times else None,
            "initial_cache_hit_rate": initial_cache["hit_rate"],
            "final_cache_hit_rate": final_cache["hit_rate"],
            "success_criteria_met": successful_criteria,
        }


if __name__ == "__main__":
    trainer = SimpleFibonacciTraining()
    results = trainer.run_full_training()

    # Save results
    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    with open(f"fibonacci_training_results_{timestamp}.json", "w") as f:
        json.dump(results, f, indent=2)

    print(
        f"\n🧮 Training complete! Results saved to fibonacci_training_results_{timestamp}.json"
    )
