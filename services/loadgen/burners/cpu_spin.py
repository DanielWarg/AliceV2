"""
CPU Spin - Controlled CPU stress test in pulses
===============================================
"""

import concurrent.futures
import os
import time
from typing import Any, Dict

import psutil

# Configuration
CPU_THREADS = int(os.getenv("CPU_THREADS", "4"))


def _cpu_burn_cycle(iterations: int = 10_000_000) -> int:
    """Single CPU burn cycle - compute-intensive work"""
    accumulator = 0
    for i in range(iterations):
        # Mix of operations to stress different CPU units
        accumulator += i * i
        accumulator = accumulator % 1000000  # Prevent overflow
        if i % 100000 == 0:
            accumulator ^= i  # XOR operation
    return accumulator


def get_cpu_stats() -> Dict[str, float]:
    """Get current CPU statistics"""
    cpu_percent = psutil.cpu_percent(interval=0.1)
    cpu_count = psutil.cpu_count()
    load_avg = os.getloadavg() if hasattr(os, "getloadavg") else [0, 0, 0]

    return {
        "cpu_percent": cpu_percent,
        "cpu_count": cpu_count,
        "load_1min": load_avg[0],
        "load_5min": load_avg[1],
        "load_15min": load_avg[2],
    }


def run(threads: int = None, seconds: int = 30) -> Dict[str, Any]:
    """
    Run CPU spin stress test

    Args:
        threads: Number of CPU threads to use (default from env)
        seconds: Duration to run test

    Returns:
        Test results with CPU utilization stats
    """
    threads = threads or CPU_THREADS

    print(f"⚙️  Starting CPU Spin: {threads} threads for {seconds}s")

    # Get baseline CPU stats
    baseline_stats = get_cpu_stats()
    print(
        f"   Baseline CPU: {baseline_stats['cpu_percent']:.1f}%, "
        f"Load: {baseline_stats['load_1min']:.2f}"
    )

    start_time = time.perf_counter()
    end_time = start_time + seconds
    total_cycles = 0
    cpu_samples = []

    try:
        with concurrent.futures.ThreadPoolExecutor(max_workers=threads) as executor:
            while time.perf_counter() < end_time:
                # Launch CPU burn batch
                batch_start = time.perf_counter()

                # Submit work to all threads
                futures = [
                    executor.submit(
                        _cpu_burn_cycle, 5_000_000
                    )  # Smaller cycles for responsiveness
                    for _ in range(threads)
                ]

                # Wait for batch completion
                batch_results = []
                for future in concurrent.futures.as_completed(futures):
                    try:
                        result = future.result()
                        batch_results.append(result)
                    except Exception as e:
                        print(f"   ⚠️  CPU thread error: {e}")

                batch_time = time.perf_counter() - batch_start
                total_cycles += len(batch_results)

                # Sample CPU usage periodically
                if (
                    len(cpu_samples) == 0
                    or time.perf_counter() - cpu_samples[-1]["time"] > 2
                ):
                    current_stats = get_cpu_stats()
                    cpu_samples.append(
                        {
                            "time": time.perf_counter(),
                            "cpu_percent": current_stats["cpu_percent"],
                            "load_1min": current_stats["load_1min"],
                        }
                    )

                    elapsed = time.perf_counter() - start_time
                    remaining = seconds - elapsed
                    print(
                        f"   CPU: {current_stats['cpu_percent']:.1f}%, "
                        f"Load: {current_stats['load_1min']:.2f}, "
                        f"{remaining:.0f}s remaining"
                    )

                # Brief pause to prevent system lockup
                time.sleep(0.05)

    except KeyboardInterrupt:
        print("   CPU stress test interrupted")

    # Final CPU stats
    final_stats = get_cpu_stats()
    total_time = time.perf_counter() - start_time

    # Calculate CPU statistics
    avg_cpu = (
        sum(s["cpu_percent"] for s in cpu_samples) / len(cpu_samples)
        if cpu_samples
        else 0
    )
    max_cpu = max(s["cpu_percent"] for s in cpu_samples) if cpu_samples else 0
    avg_load = (
        sum(s["load_1min"] for s in cpu_samples) / len(cpu_samples)
        if cpu_samples
        else 0
    )

    result_summary = {
        "test_type": "cpu_spin",
        "duration_s": seconds,
        "threads_used": threads,
        "total_cycles": total_cycles,
        "cycles_per_second": round(total_cycles / total_time, 2),
        "cpu_stats": {
            "baseline": baseline_stats,
            "final": final_stats,
            "avg_cpu_percent": round(avg_cpu, 1),
            "max_cpu_percent": round(max_cpu, 1),
            "avg_load": round(avg_load, 2),
        },
        "samples_taken": len(cpu_samples),
    }

    print(
        f"   Completed: {total_cycles} cycles, avg CPU: {avg_cpu:.1f}%, "
        f"max: {max_cpu:.1f}%"
    )

    return result_summary
