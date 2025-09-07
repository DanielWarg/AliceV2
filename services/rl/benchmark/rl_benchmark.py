#!/usr/bin/env python3
"""
Reproducerbar RL benchmark för T1-T4 validering
Genererar CSV/JSON artefakter för objektiv bedömning
"""

import argparse
import csv
import json
import platform
import statistics
import subprocess

# Ensure imports work
import sys
import time
from pathlib import Path
from typing import Any, Dict

import numpy as np

sys.path.append(str(Path(__file__).parent.parent.parent))

from services.rl.online.linucb_router import LinUCBRouter
from services.rl.online.thompson_tools import ThompsonTools
from services.rl.rewards.phi_reward import compute_phi_total


def create_artefacts_dir() -> Path:
    """Create artefacts directory"""
    artefacts = Path("artefacts/rl_bench")
    artefacts.mkdir(parents=True, exist_ok=True)
    return artefacts


def collect_env_info(artefacts_dir: Path) -> Dict[str, Any]:
    """Collect environment information"""
    try:
        git_commit = subprocess.check_output(
            ["git", "rev-parse", "HEAD"], text=True
        ).strip()
        git_branch = subprocess.check_output(
            ["git", "branch", "--show-current"], text=True
        ).strip()
        git_dirty = (
            len(
                subprocess.check_output(
                    ["git", "status", "--porcelain"], text=True
                ).strip()
            )
            > 0
        )
    except Exception:
        git_commit = "unknown"
        git_branch = "unknown"
        git_dirty = True

    env_info = {
        "platform": platform.platform(),
        "processor": platform.processor(),
        "python_version": platform.python_version(),
        "git_commit": git_commit,
        "git_branch": git_branch,
        "git_dirty": git_dirty,
        "timestamp": time.time(),
    }

    # Write env files
    with open(artefacts_dir / "env.txt", "w") as f:
        for k, v in env_info.items():
            f.write(f"{k}: {v}\n")

    with open(artefacts_dir / "git.txt", "w") as f:
        f.write(f"commit: {git_commit}\n")
        f.write(f"branch: {git_branch}\n")
        f.write(f"dirty: {git_dirty}\n")

    return env_info


def benchmark_micro_ops() -> Dict[str, Any]:
    """Benchmark pure LinUCB/Thompson operations (no I/O)"""
    print("🔬 Running micro-ops benchmark...")

    # Initialize components
    router = LinUCBRouter()
    tools = ThompsonTools()

    # Sample contexts
    contexts = [
        {
            "intent_conf": 0.8,
            "len_chars": 25,
            "has_question": True,
            "cache_hint": False,
            "guardian_state": "NORMAL",
            "prev_tool_error": False,
        },
        {
            "intent_conf": 0.5,
            "len_chars": 100,
            "has_question": False,
            "cache_hint": True,
            "guardian_state": "BROWNOUT",
            "prev_tool_error": True,
        },
        {
            "intent_conf": 0.9,
            "len_chars": 10,
            "has_question": True,
            "cache_hint": False,
            "guardian_state": "EMERGENCY",
            "prev_tool_error": False,
        },
    ]

    # Warmup
    for _ in range(100):
        ctx = contexts[0]
        route = router.select(ctx)
        router.update(ctx, route, 0.8)
        tools.update("test.intent", "test_tool", 0.8)

    # Actual benchmark
    num_ops = 10000
    latencies = []

    start_time = time.time()
    for i in range(num_ops):
        op_start = time.perf_counter()

        ctx = contexts[i % len(contexts)]
        route = router.select(ctx)
        router.update(ctx, route, 0.7 + (i % 30) / 100)

        intent = f"intent.{i % 10}"
        tool = tools.select(intent) or "fallback"
        tools.update(intent, tool, 0.6 + (i % 40) / 100)

        op_end = time.perf_counter()
        latencies.append((op_end - op_start) * 1000)  # ms

    total_time = time.time() - start_time
    ops_per_sec = num_ops / total_time

    return {
        "mode": "micro_ops",
        "num_ops": num_ops,
        "total_time_sec": total_time,
        "ops_per_sec": ops_per_sec,
        "latency_p50_ms": statistics.median(latencies),
        "latency_p95_ms": np.percentile(latencies, 95),
        "latency_p99_ms": np.percentile(latencies, 99),
        "latencies": latencies,
    }


def benchmark_turn_sim() -> Dict[str, Any]:
    """Benchmark full turn simulation (incl φ-reward, persistence)"""
    print("🎮 Running turn simulation benchmark...")

    router = LinUCBRouter()
    tools = ThompsonTools()

    num_turns = 1000
    latencies = []
    successes = 0

    start_time = time.time()
    for i in range(num_turns):
        turn_start = time.perf_counter()

        try:
            # Context
            context = {
                "intent_conf": 0.7 + (i % 30) / 100,
                "len_chars": 20 + (i % 100),
                "has_question": i % 3 == 0,
                "cache_hint": i % 4 == 0,
                "guardian_state": ["NORMAL", "BROWNOUT"][i % 2],
                "prev_tool_error": i % 5 == 0,
            }

            # Decision making
            route = router.select(context)
            intent = f"intent.category_{i % 20}"
            tool = tools.select(intent) or "fallback_tool"

            # φ-reward calculation
            reward_components = compute_phi_total(
                latency_ms=50 + (i % 200),
                energy_wh=0.001 + (i % 50) / 50000,
                safety_ok=i % 10 != 0,
                tool_success=i % 8 != 0,
                schema_ok=i % 12 != 0,
            )
            reward = reward_components.get("total", 0.5)

            # Learning updates
            router.update(context, route, reward)
            tools.update(intent, tool, reward)

            # Periodic persistence (every 50 turns)
            if i % 50 == 0:
                router.save()
                tools.save()

            successes += 1

        except Exception as e:
            print(f"Turn {i} failed: {e}")

        turn_end = time.perf_counter()
        latencies.append((turn_end - turn_start) * 1000)  # ms

    total_time = time.time() - start_time
    turns_per_sec = num_turns / total_time
    success_rate = successes / num_turns

    return {
        "mode": "turn_sim",
        "num_turns": num_turns,
        "total_time_sec": total_time,
        "turns_per_sec": turns_per_sec,
        "success_rate": success_rate,
        "latency_p50_ms": statistics.median(latencies),
        "latency_p95_ms": np.percentile(latencies, 95),
        "latency_p99_ms": np.percentile(latencies, 99),
        "latencies": latencies,
    }


def benchmark_replay() -> Dict[str, Any]:
    """Benchmark replay training"""
    print("🔄 Running replay benchmark...")

    from services.rl.replay.replay_from_episodes import replay_training

    episodes_file = Path("data/rl/v1/train.jsonl")
    if not episodes_file.exists():
        return {"mode": "replay", "error": "No training episodes found"}

    # Count episodes
    with open(episodes_file) as f:
        episodes = sum(1 for _ in f)

    router = LinUCBRouter()
    tools = ThompsonTools()

    start_time = time.time()
    replay_training(episodes_file, epochs=1, router=router, tools=tools)
    total_time = time.time() - start_time

    episodes_per_sec = episodes / total_time if total_time > 0 else 0

    return {
        "mode": "replay",
        "episodes_processed": episodes,
        "total_time_sec": total_time,
        "episodes_per_sec": episodes_per_sec,
        "router_updates": router.get_stats()["total_updates"],
        "tools_updates": tools.get_stats()["total_updates"],
    }


def run_benchmark(mode: str = "all") -> Dict[str, Any]:
    """Run benchmark suite"""
    artefacts_dir = create_artefacts_dir()

    print(f"🚀 Starting RL benchmark (mode={mode})")
    print(f"📁 Artefacts will be saved to: {artefacts_dir}")

    # Collect environment info
    env_info = collect_env_info(artefacts_dir)

    results = {
        "benchmark_info": {"mode": mode, "timestamp": time.time(), "env": env_info},
        "results": {},
    }

    # Run benchmarks based on mode
    if mode in ["all", "micro"]:
        results["results"]["micro_ops"] = benchmark_micro_ops()

    if mode in ["all", "turn"]:
        results["results"]["turn_sim"] = benchmark_turn_sim()

    if mode in ["all", "replay"]:
        results["results"]["replay"] = benchmark_replay()

    # Save summary
    with open(artefacts_dir / "summary.json", "w") as f:
        json.dump(results, f, indent=2)

    # Save latency histograms
    with open(artefacts_dir / "latency_hist.csv", "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["mode", "latency_ms"])

        for mode_name, result in results["results"].items():
            if "latencies" in result:
                for latency in result["latencies"]:
                    writer.writerow([mode_name, latency])

    # Save QPS summary
    with open(artefacts_dir / "qps_by_mode.csv", "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["mode", "ops_per_sec", "p95_latency_ms", "success_rate"])

        for mode_name, result in results["results"].items():
            ops_sec = result.get(
                "ops_per_sec",
                result.get("turns_per_sec", result.get("episodes_per_sec", 0)),
            )
            p95_lat = result.get("latency_p95_ms", 0)
            success = result.get("success_rate", 1.0)
            writer.writerow([mode_name, ops_sec, p95_lat, success])

    return results


def check_slo_gates(results: Dict[str, Any]) -> bool:
    """Check SLO gates for CI"""
    gates_passed = True

    print("\n🚦 Checking SLO gates...")

    if "micro_ops" in results["results"]:
        micro = results["results"]["micro_ops"]
        min_ops_sec = 5000

        if micro["ops_per_sec"] < min_ops_sec:
            print(
                f"❌ Micro-ops too slow: {micro['ops_per_sec']:.1f} < {min_ops_sec} ops/sec"
            )
            gates_passed = False
        else:
            print(f"✅ Micro-ops: {micro['ops_per_sec']:.1f} ops/sec")

    if "turn_sim" in results["results"]:
        turn = results["results"]["turn_sim"]
        max_p95_ms = 50
        min_success = 0.985

        if turn["latency_p95_ms"] > max_p95_ms:
            print(
                f"❌ Turn-sim p95 too high: {turn['latency_p95_ms']:.1f} > {max_p95_ms}ms"
            )
            gates_passed = False
        else:
            print(f"✅ Turn-sim p95: {turn['latency_p95_ms']:.1f}ms")

        if turn["success_rate"] < min_success:
            print(
                f"❌ Turn-sim success too low: {turn['success_rate']:.3f} < {min_success}"
            )
            gates_passed = False
        else:
            print(f"✅ Turn-sim success: {turn['success_rate']:.1%}")

    return gates_passed


def main():
    parser = argparse.ArgumentParser(description="RL Benchmark Suite")
    parser.add_argument(
        "--mode",
        choices=["all", "micro", "turn", "replay", "CI"],
        default="all",
        help="Benchmark mode",
    )

    args = parser.parse_args()

    try:
        results = run_benchmark(args.mode)

        # Print summary
        print("\n📊 BENCHMARK RESULTS")
        print("=" * 50)

        for mode_name, result in results["results"].items():
            print(f"\n{mode_name.upper()}:")

            if "ops_per_sec" in result:
                print(f"  Performance: {result['ops_per_sec']:.1f} ops/sec")
            elif "turns_per_sec" in result:
                print(f"  Performance: {result['turns_per_sec']:.1f} turns/sec")
            elif "episodes_per_sec" in result:
                print(f"  Performance: {result['episodes_per_sec']:.1f} episodes/sec")

            if "latency_p95_ms" in result:
                print(f"  Latency p95: {result['latency_p95_ms']:.2f}ms")

            if "success_rate" in result:
                print(f"  Success rate: {result['success_rate']:.1%}")

        # Check gates for CI mode
        if args.mode == "CI":
            gates_passed = check_slo_gates(results)
            if not gates_passed:
                print("\n❌ SLO gates FAILED")
                sys.exit(1)
            else:
                print("\n✅ All SLO gates PASSED")

        print("\n📁 Artefacts saved to: artefacts/rl_bench/")

    except Exception as e:
        print(f"❌ Benchmark failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
