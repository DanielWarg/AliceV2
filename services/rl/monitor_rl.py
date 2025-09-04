#!/usr/bin/env python3
"""
RL Policy Monitoring Dashboard
Övervakar RL-policy prestanda i realtid.
"""

from __future__ import annotations

import argparse
import time
from datetime import datetime
from typing import Any, Dict, Optional

import structlog

try:
    import requests
except ImportError:
    requests = None

logger = structlog.get_logger(__name__)


class RLMonitor:
    """Monitor för RL-policy prestanda."""

    def __init__(self, orchestrator_url: str = "http://localhost:8000"):
        self.orchestrator_url = orchestrator_url.rstrip("/")
        self.baseline_metrics: Optional[Dict[str, Any]] = None

    def get_health_status(self) -> tuple[bool, Dict[str, Any]]:
        """Hämta hälsostatus från orchestrator."""
        if not requests:
            return False, {"error": "requests library not available"}

        try:
            response = requests.get(f"{self.orchestrator_url}/health", timeout=5)
            if response.status_code == 200:
                return True, (
                    response.json()
                    if response.headers.get("content-type", "").startswith(
                        "application/json"
                    )
                    else {}
                )
            return False, {"http_code": response.status_code}
        except Exception as e:
            return False, {"error": str(e)}

    def get_metrics(self) -> Optional[Dict[str, Any]]:
        """Hämta metrics från orchestrator."""
        if not requests:
            return None

        try:
            response = requests.get(f"{self.orchestrator_url}/metrics", timeout=5)
            if response.status_code == 200 and response.headers.get(
                "content-type", ""
            ).startswith("application/json"):
                return response.json()
        except Exception:
            pass
        return None

    def get_policy_status(self) -> Optional[Dict[str, Any]]:
        """Hämta policy status."""
        if not requests:
            return None

        try:
            response = requests.get(f"{self.orchestrator_url}/rl-status", timeout=5)
            if response.status_code == 200 and response.headers.get(
                "content-type", ""
            ).startswith("application/json"):
                return response.json()
        except Exception:
            pass
        return None

    def calculate_performance_delta(self, current: Dict[str, Any]) -> Dict[str, float]:
        """Beräkna prestanda-förändring från baseline."""
        if not self.baseline_metrics:
            return {}

        deltas = {}

        # Success rate delta
        baseline_success = self.baseline_metrics.get("success_rate", 0.8)
        current_success = current.get("success_rate", 0.8)
        deltas["success_rate"] = current_success - baseline_success

        # Latency delta (negative is better)
        baseline_latency = self.baseline_metrics.get("avg_latency_ms", 500)
        current_latency = current.get("avg_latency_ms", 500)
        deltas["latency_ms"] = current_latency - baseline_latency

        # Cost delta (negative is better)
        baseline_cost = self.baseline_metrics.get("avg_cost_usd", 0.003)
        current_cost = current.get("avg_cost_usd", 0.003)
        deltas["cost_usd"] = current_cost - baseline_cost

        # Cache hit rate delta
        baseline_cache = self.baseline_metrics.get("cache_hit_rate", 0.3)
        current_cache = current.get("cache_hit_rate", 0.3)
        deltas["cache_hit_rate"] = current_cache - baseline_cache

        return deltas

    def print_status_report(
        self,
        healthy: bool,
        metrics: Optional[Dict[str, Any]],
        policy_status: Optional[Dict[str, Any]],
    ):
        """Skriv ut statusrapport."""
        print(f"\n{'='*60}")
        print(f"Alice RL Monitor - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"{'='*60}")

        # System health
        health_emoji = "🟢" if healthy else "🔴"
        print(f"{health_emoji} System Health: {'HEALTHY' if healthy else 'UNHEALTHY'}")

        # Policy status
        if policy_status:
            routing_active = policy_status.get("routing_policy_active", False)
            tools_active = policy_status.get("tools_policy_active", False)
            cache_active = policy_status.get("cache_policy_active", False)

            print("\n📊 RL Policy Status:")
            print(f"   Routing: {'🟢 ACTIVE' if routing_active else '🔴 INACTIVE'}")
            print(f"   Tools:   {'🟢 ACTIVE' if tools_active else '🔴 INACTIVE'}")
            print(f"   Cache:   {'🟢 ACTIVE' if cache_active else '🔴 INACTIVE'}")
        else:
            print("\n📊 RL Policy Status: ❓ UNKNOWN")

        # Performance metrics
        if metrics:
            print("\n📈 Performance Metrics:")
            print(f"   Success Rate:  {metrics.get('success_rate', 0.0):.1%}")
            print(f"   Avg Latency:   {metrics.get('avg_latency_ms', 0):.0f} ms")
            print(f"   Avg Cost:      ${metrics.get('avg_cost_usd', 0.0):.4f}")
            print(f"   Cache Hit Rate: {metrics.get('cache_hit_rate', 0.0):.1%}")

            # Route distribution
            routes = metrics.get("route_distribution", {})
            if routes:
                print("\n🛤️  Route Distribution:")
                for route, pct in routes.items():
                    print(f"   {route:10} {pct:.1%}")

            # Tool distribution
            tools = metrics.get("tool_distribution", {})
            if tools:
                print("\n🔧 Tool Distribution:")
                for tool, pct in sorted(
                    tools.items(), key=lambda x: x[1], reverse=True
                )[:5]:
                    print(f"   {tool:15} {pct:.1%}")

            # Performance deltas
            deltas = self.calculate_performance_delta(metrics)
            if deltas:
                print("\n📊 Performance vs Baseline:")
                for metric, delta in deltas.items():
                    if metric == "success_rate":
                        trend = "📈" if delta > 0 else "📉" if delta < -0.01 else "➡️"
                        print(f"   Success Rate:  {trend} {delta:+.1%}")
                    elif metric == "latency_ms":
                        trend = "📉" if delta < 0 else "📈" if delta > 50 else "➡️"
                        print(f"   Latency:       {trend} {delta:+.0f} ms")
                    elif metric == "cost_usd":
                        trend = "📉" if delta < 0 else "📈" if delta > 0.001 else "➡️"
                        print(f"   Cost:          {trend} ${delta:+.4f}")
                    elif metric == "cache_hit_rate":
                        trend = "📈" if delta > 0 else "📉" if delta < -0.05 else "➡️"
                        print(f"   Cache Hits:    {trend} {delta:+.1%}")
        else:
            print("\n📈 Performance Metrics: ❓ UNAVAILABLE")

        print(f"{'='*60}\n")

    def set_baseline(self, metrics: Dict[str, Any]):
        """Sätt baseline metrics för jämförelse."""
        self.baseline_metrics = metrics.copy()
        logger.info("Baseline metrics set", metrics=metrics)

    def monitor_continuous(
        self, interval: float = 30.0, duration_minutes: Optional[float] = None
    ):
        """Kontinuerlig övervakning."""
        logger.info(
            "Starting continuous monitoring",
            interval_seconds=interval,
            duration_minutes=duration_minutes,
        )

        start_time = time.time()
        iteration = 0

        try:
            while True:
                iteration += 1

                # Get current status
                healthy, health_data = self.get_health_status()
                metrics = self.get_metrics()
                policy_status = self.get_policy_status()

                # Set baseline on first iteration
                if iteration == 1 and metrics:
                    self.set_baseline(metrics)

                # Print status report
                self.print_status_report(healthy, metrics, policy_status)

                # Log any alerts
                if not healthy:
                    logger.warning("System unhealthy", health_data=health_data)

                if metrics:
                    success_rate = metrics.get("success_rate", 0.8)
                    if success_rate < 0.7:
                        logger.warning(
                            "Low success rate detected", success_rate=success_rate
                        )

                    avg_latency = metrics.get("avg_latency_ms", 500)
                    if avg_latency > 2000:
                        logger.warning("High latency detected", latency_ms=avg_latency)

                # Check duration
                if duration_minutes:
                    elapsed = (time.time() - start_time) / 60
                    if elapsed >= duration_minutes:
                        logger.info(
                            "Monitoring duration reached", elapsed_minutes=elapsed
                        )
                        break

                # Wait for next iteration
                time.sleep(interval)

        except KeyboardInterrupt:
            logger.info("Monitoring stopped by user")


def main():
    """Main monitoring script."""
    parser = argparse.ArgumentParser(description="Alice RL Policy Monitor")
    parser.add_argument(
        "--url", default="http://localhost:8000", help="Orchestrator URL"
    )
    parser.add_argument(
        "--interval", type=float, default=30.0, help="Check interval in seconds"
    )
    parser.add_argument("--duration", type=float, help="Monitoring duration in minutes")
    parser.add_argument("--once", action="store_true", help="Run once and exit")

    args = parser.parse_args()

    # Setup logging
    structlog.configure(
        processors=[structlog.dev.ConsoleRenderer()],
        logger_factory=structlog.stdlib.LoggerFactory(),
    )

    try:
        monitor = RLMonitor(orchestrator_url=args.url)

        if args.once:
            # Single check
            healthy, health_data = monitor.get_health_status()
            metrics = monitor.get_metrics()
            policy_status = monitor.get_policy_status()

            monitor.print_status_report(healthy, metrics, policy_status)
        else:
            # Continuous monitoring
            monitor.monitor_continuous(
                interval=args.interval, duration_minutes=args.duration
            )

    except Exception as e:
        logger.error("Monitoring failed", error=str(e))
        return 1

    return 0


if __name__ == "__main__":
    exit(main())
