#!/usr/bin/env python3
"""
Shadow Mode för Alice RL - lär i bakgrunden utan att påverka prod.
Samlar data och tränar policies medan befintlig system kör normalt.
"""

from __future__ import annotations

import json
import threading
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, Optional

import structlog

logger = structlog.get_logger(__name__)


class ShadowModeController:
    """
    Styr Alice's shadow mode learning - observerar prod utan att påverka.
    """

    def __init__(
        self,
        telemetry_file: str = "services/orchestrator/telemetry.jsonl",
        shadow_policies_dir: str = "services/rl/shadow_models",
        retrain_interval_hours: float = 6.0,
        min_new_episodes: int = 50,
    ):
        """
        Initialize shadow mode controller.

        Args:
            telemetry_file: Path to live telemetry
            shadow_policies_dir: Where to store shadow policies
            retrain_interval_hours: How often to retrain
            min_new_episodes: Minimum new episodes before retrain
        """
        self.telemetry_file = Path(telemetry_file)
        self.shadow_dir = Path(shadow_policies_dir)
        self.retrain_interval = timedelta(hours=retrain_interval_hours)
        self.min_new_episodes = min_new_episodes

        # State tracking
        self.last_retrain = datetime.now()
        self.last_episode_count = 0
        self.shadow_policies = {}
        self.performance_log = []

        # Threading
        self.running = False
        self.shadow_thread: Optional[threading.Thread] = None

        # Create directories
        self.shadow_dir.mkdir(parents=True, exist_ok=True)
        (self.shadow_dir / "logs").mkdir(exist_ok=True)
        (self.shadow_dir / "metrics").mkdir(exist_ok=True)

        logger.info(
            "Shadow mode controller initialized",
            telemetry_file=str(self.telemetry_file),
            shadow_dir=str(self.shadow_dir),
            retrain_interval_hours=retrain_interval_hours,
        )

    def count_new_episodes(self) -> int:
        """Räkna nya episodes sedan senaste retrain."""
        if not self.telemetry_file.exists():
            return 0

        try:
            with open(self.telemetry_file, "r") as f:
                lines = f.readlines()

            new_episodes = 0
            cutoff_time = self.last_retrain

            for line in lines[-1000:]:  # Check last 1000 lines for efficiency
                try:
                    episode = json.loads(line.strip())
                    episode_time = datetime.fromisoformat(episode.get("timestamp", ""))

                    if episode_time > cutoff_time:
                        new_episodes += 1
                except:
                    continue

            return new_episodes

        except Exception as e:
            logger.warning("Failed to count new episodes", error=str(e))
            return 0

    def should_retrain(self) -> tuple[bool, str]:
        """Avgör om det är dags att träna om."""
        now = datetime.now()

        # Time-based trigger
        if now - self.last_retrain >= self.retrain_interval:
            new_episodes = self.count_new_episodes()
            if new_episodes >= self.min_new_episodes:
                return True, f"Time trigger: {new_episodes} new episodes"
            else:
                return (
                    False,
                    f"Not enough new data: {new_episodes} < {self.min_new_episodes}",
                )

        # Episode-based trigger (more frequent checks if lots of data)
        new_episodes = self.count_new_episodes()
        if (
            new_episodes >= self.min_new_episodes * 3
        ):  # 3x threshold = immediate retrain
            return True, f"Data trigger: {new_episodes} new episodes"

        return (
            False,
            f"No trigger: {(now - self.last_retrain).total_seconds()/3600:.1f}h, {new_episodes} episodes",
        )

    def run_shadow_training(self) -> tuple[bool, str]:
        """Kör shadow training utan att påverka prod."""
        try:
            logger.info("Starting shadow training")
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

            # 1. Build dataset from latest telemetry
            dataset_path = self.shadow_dir / f"episodes_{timestamp}.json"
            cmd_build = [
                "python",
                "build_dataset.py",
                "--input",
                str(self.telemetry_file),
                "--output",
                str(dataset_path),
                "--min-episodes",
                "10",  # Lower threshold for shadow mode
            ]

            import subprocess

            result = subprocess.run(
                cmd_build, cwd="services/rl", capture_output=True, text=True
            )
            if result.returncode != 0:
                return False, f"Dataset building failed: {result.stderr}"

            # 2. Train shadow routing policy
            routing_path = self.shadow_dir / f"routing_{timestamp}.json"
            cmd_routing = [
                "python",
                "bandits/routing_linucb.py",
                "--episodes",
                str(dataset_path),
                "--output",
                str(routing_path),
                "--alpha",
                "0.3",  # More conservative for shadow
            ]

            result = subprocess.run(
                cmd_routing, cwd="services/rl", capture_output=True, text=True
            )
            if result.returncode != 0:
                return False, f"Routing training failed: {result.stderr}"

            # 3. Train shadow tool policy
            tools_path = self.shadow_dir / f"tools_{timestamp}.json"
            cmd_tools = [
                "python",
                "bandits/tool_thompson.py",
                "--episodes",
                str(dataset_path),
                "--output",
                str(tools_path),
            ]

            result = subprocess.run(
                cmd_tools, cwd="services/rl", capture_output=True, text=True
            )
            if result.returncode != 0:
                return False, f"Tool training failed: {result.stderr}"

            # 4. Shadow evaluation (don't deploy)
            eval_path = self.shadow_dir / "logs" / f"shadow_eval_{timestamp}.json"
            cmd_eval = [
                "python",
                "eval/offline_ips_eval.py",
                "--episodes",
                str(dataset_path),
                "--routing-policy",
                str(routing_path),
                "--tool-policy",
                str(tools_path),
                "--output",
                str(eval_path),
            ]

            result = subprocess.run(
                cmd_eval, cwd="services/rl", capture_output=True, text=True
            )
            if result.returncode != 0:
                logger.warning("Shadow evaluation failed", error=result.stderr)
                # Continue anyway - evaluation failure isn't critical

            # 5. Store shadow policies (don't deploy to prod)
            self.shadow_policies = {
                "timestamp": timestamp,
                "routing_policy": str(routing_path),
                "tool_policy": str(tools_path),
                "evaluation": str(eval_path),
                "dataset": str(dataset_path),
            }

            # Save shadow policy manifest
            manifest_path = self.shadow_dir / "latest_shadow_policies.json"
            with open(manifest_path, "w") as f:
                json.dump(self.shadow_policies, f, indent=2)

            self.last_retrain = datetime.now()

            logger.info(
                "Shadow training completed",
                timestamp=timestamp,
                policies=len(self.shadow_policies),
            )

            return True, f"Shadow policies trained: {timestamp}"

        except Exception as e:
            logger.error("Shadow training failed", error=str(e))
            return False, f"Shadow training error: {str(e)}"

    def compare_shadow_to_prod(self) -> Dict[str, Any]:
        """Jämför shadow policies med production performance."""
        try:
            if not self.shadow_policies:
                return {"error": "No shadow policies available"}

            eval_path = Path(self.shadow_policies.get("evaluation", ""))
            if not eval_path.exists():
                return {"error": "No shadow evaluation available"}

            with open(eval_path, "r") as f:
                shadow_results = json.load(f)

            # Get production baseline (would need prod metrics endpoint)
            # For now, use estimated baselines
            prod_baseline = {
                "policy_value": 0.65,  # Estimated current prod performance
                "success_rate": 0.83,
                "avg_latency_ms": 500,
                "tool_precision": 0.547,
            }

            shadow_value = shadow_results.get("policy_value", 0.0)
            shadow_success = shadow_results.get("routing", {}).get("success_rate", 0.0)

            comparison = {
                "shadow_policy_value": shadow_value,
                "prod_policy_value": prod_baseline["policy_value"],
                "improvement": shadow_value - prod_baseline["policy_value"],
                "improvement_pct": (shadow_value - prod_baseline["policy_value"])
                / prod_baseline["policy_value"]
                * 100,
                "shadow_success_rate": shadow_success,
                "ready_for_canary": shadow_value
                > prod_baseline["policy_value"] * 1.05,  # 5% improvement threshold
                "timestamp": self.shadow_policies["timestamp"],
            }

            return comparison

        except Exception as e:
            logger.error("Shadow comparison failed", error=str(e))
            return {"error": str(e)}

    def get_shadow_status(self) -> Dict[str, Any]:
        """Hämta status för shadow mode."""
        new_episodes = self.count_new_episodes()
        should_retrain, retrain_reason = self.should_retrain()

        return {
            "running": self.running,
            "last_retrain": self.last_retrain.isoformat(),
            "hours_since_retrain": (datetime.now() - self.last_retrain).total_seconds()
            / 3600,
            "new_episodes_since_retrain": new_episodes,
            "should_retrain": should_retrain,
            "retrain_reason": retrain_reason,
            "shadow_policies": bool(self.shadow_policies),
            "shadow_policies_timestamp": self.shadow_policies.get("timestamp"),
            "comparison_available": bool(
                self.shadow_policies
                and Path(self.shadow_policies.get("evaluation", "")).exists()
            ),
        }

    def shadow_worker(self):
        """Background worker för shadow mode."""
        logger.info("Shadow worker started")

        while self.running:
            try:
                should_retrain, reason = self.should_retrain()

                if should_retrain:
                    logger.info("Triggering shadow retrain", reason=reason)
                    success, message = self.run_shadow_training()

                    if success:
                        logger.info("Shadow training successful", message=message)

                        # Compare with prod
                        comparison = self.compare_shadow_to_prod()
                        if comparison.get("ready_for_canary"):
                            logger.info(
                                "Shadow policy ready for canary deployment!",
                                improvement_pct=comparison.get("improvement_pct", 0),
                            )

                    else:
                        logger.error("Shadow training failed", message=message)

                # Check every 30 minutes
                for _ in range(30 * 60):  # 30 minutes in seconds
                    if not self.running:
                        break
                    time.sleep(1)

            except Exception as e:
                logger.error("Shadow worker error", error=str(e))
                time.sleep(60)  # Wait 1 minute before retry

        logger.info("Shadow worker stopped")

    def start_shadow_mode(self):
        """Starta shadow mode i bakgrunden."""
        if self.running:
            logger.warning("Shadow mode already running")
            return

        self.running = True
        self.shadow_thread = threading.Thread(
            target=self.shadow_worker, daemon=True, name="alice-shadow-mode"
        )
        self.shadow_thread.start()

        logger.info("Shadow mode started")

    def stop_shadow_mode(self):
        """Stoppa shadow mode."""
        if not self.running:
            return

        self.running = False

        if self.shadow_thread and self.shadow_thread.is_alive():
            self.shadow_thread.join(timeout=10.0)

        logger.info("Shadow mode stopped")

    def promote_shadow_to_canary(self) -> tuple[bool, str]:
        """Promota bästa shadow policy till canary."""
        if not self.shadow_policies:
            return False, "No shadow policies available"

        try:
            # Get latest shadow policies
            routing_path = self.shadow_policies["routing_policy"]
            tools_path = self.shadow_policies["tool_policy"]
            timestamp = self.shadow_policies["timestamp"]

            # Create deployment package
            package_path = f"services/rl/deploy/shadow_to_canary_{timestamp}.json"

            import subprocess

            cmd_export = [
                "python",
                "deploy/export_policies.py",
                "--routing",
                routing_path,
                "--tools",
                tools_path,
                "--out",
                package_path,
                "--version",
                f"shadow_{timestamp}",
                "--stage",
                "canary",
            ]

            result = subprocess.run(
                cmd_export, cwd="services/rl", capture_output=True, text=True
            )
            if result.returncode != 0:
                return False, f"Package export failed: {result.stderr}"

            # Deploy to canary
            cmd_deploy = [
                "python",
                "deploy/promote.py",
                "--stage",
                "canary",
                "--pack",
                package_path,
                "--destination",
                "services/orchestrator/src/policies/live",
            ]

            result = subprocess.run(cmd_deploy, capture_output=True, text=True)
            if result.returncode != 0:
                return False, f"Canary deployment failed: {result.stderr}"

            logger.info(
                "Shadow policy promoted to canary",
                timestamp=timestamp,
                package=package_path,
            )

            return True, f"Shadow policy {timestamp} promoted to canary"

        except Exception as e:
            logger.error("Shadow promotion failed", error=str(e))
            return False, f"Promotion error: {str(e)}"


def main():
    """Main shadow mode script."""
    import argparse

    parser = argparse.ArgumentParser(description="Alice Shadow Mode Controller")
    parser.add_argument(
        "--action",
        choices=["start", "stop", "status", "retrain", "compare", "promote"],
        required=True,
        help="Action to perform",
    )
    parser.add_argument(
        "--telemetry",
        default="services/orchestrator/telemetry.jsonl",
        help="Telemetry file path",
    )
    parser.add_argument(
        "--interval", type=float, default=6.0, help="Retrain interval in hours"
    )
    parser.add_argument(
        "--min-episodes", type=int, default=50, help="Minimum episodes before retrain"
    )

    args = parser.parse_args()

    # Setup logging
    structlog.configure(
        processors=[structlog.dev.ConsoleRenderer()],
        logger_factory=structlog.stdlib.LoggerFactory(),
    )

    try:
        controller = ShadowModeController(
            telemetry_file=args.telemetry,
            retrain_interval_hours=args.interval,
            min_new_episodes=args.min_episodes,
        )

        if args.action == "start":
            controller.start_shadow_mode()
            print("🌑 Shadow mode started - Alice is learning in the background")
            print("   Monitor with: python shadow_mode.py --action status")

            # Keep running
            try:
                while True:
                    time.sleep(10)
            except KeyboardInterrupt:
                controller.stop_shadow_mode()

        elif args.action == "stop":
            controller.stop_shadow_mode()
            print("🌑 Shadow mode stopped")

        elif args.action == "status":
            status = controller.get_shadow_status()
            print("\n🌑 Shadow Mode Status:")
            print(f"   Running: {'🟢 YES' if status['running'] else '🔴 NO'}")
            print(f"   Last Retrain: {status['last_retrain']}")
            print(f"   Hours Since: {status['hours_since_retrain']:.1f}")
            print(f"   New Episodes: {status['new_episodes_since_retrain']}")
            print(
                f"   Should Retrain: {'🟡 YES' if status['should_retrain'] else '🟢 NO'}"
            )
            print(f"   Reason: {status['retrain_reason']}")

            if status["shadow_policies"]:
                print("\n📊 Latest Shadow Policies:")
                print(f"   Timestamp: {status['shadow_policies_timestamp']}")
                print(
                    f"   Comparison Available: {'🟢 YES' if status['comparison_available'] else '🔴 NO'}"
                )

        elif args.action == "retrain":
            print("🌑 Running shadow retrain...")
            success, message = controller.run_shadow_training()
            print(f"{'✅' if success else '❌'} {message}")

        elif args.action == "compare":
            comparison = controller.compare_shadow_to_prod()
            if "error" in comparison:
                print(f"❌ {comparison['error']}")
            else:
                print("\n📊 Shadow vs Production Comparison:")
                print(
                    f"   Shadow Policy Value: {comparison['shadow_policy_value']:.3f}"
                )
                print(f"   Prod Policy Value:   {comparison['prod_policy_value']:.3f}")
                print(
                    f"   Improvement: {comparison['improvement']:+.3f} ({comparison['improvement_pct']:+.1f}%)"
                )
                print(
                    f"   Ready for Canary: {'🟢 YES' if comparison['ready_for_canary'] else '🔴 NO'}"
                )

        elif args.action == "promote":
            print("🚀 Promoting shadow policy to canary...")
            success, message = controller.promote_shadow_to_canary()
            print(f"{'✅' if success else '❌'} {message}")

    except Exception as e:
        logger.error("Shadow mode failed", error=str(e))
        return 1

    return 0


if __name__ == "__main__":
    exit(main())
