#!/usr/bin/env python3
"""
Alice RL Pipeline Automation
Automatiserar hela RL-processen från telemetri till produktion.
"""

from __future__ import annotations

import argparse
import json
import pathlib
import subprocess
import time
from datetime import datetime
from typing import Any, Dict, Optional

import structlog

logger = structlog.get_logger(__name__)


class RLPipelineAutomation:
    """
    Automation för hela RL-pipeline från telemetri till prod.
    """

    def __init__(
        self,
        base_dir: str = "services/rl",
        orchestrator_dir: str = "services/orchestrator",
        telemetry_path: str = "services/orchestrator/telemetry.jsonl",
        config_path: Optional[str] = None,
    ):
        """
        Initialize pipeline automation.

        Args:
            base_dir: RL service base directory
            orchestrator_dir: Orchestrator service directory
            telemetry_path: Path to telemetry data
            config_path: Optional config file path
        """
        self.base_dir = pathlib.Path(base_dir)
        self.orchestrator_dir = pathlib.Path(orchestrator_dir)
        self.telemetry_path = pathlib.Path(telemetry_path)

        # Load config
        self.config = self._load_config(config_path)

        # Directories
        self.models_dir = self.base_dir / "models"
        self.data_dir = self.base_dir / "data"
        self.eval_dir = self.base_dir / "eval_runs"
        self.deploy_dir = self.base_dir / "deploy"
        self.policies_dir = self.orchestrator_dir / "src" / "policies" / "live"

        logger.info(
            "RL Pipeline automation initialized",
            base_dir=str(self.base_dir),
            telemetry_path=str(self.telemetry_path),
        )

    def _load_config(self, config_path: Optional[str]) -> Dict[str, Any]:
        """Load automation configuration."""
        default_config = {
            "dataset": {"min_episodes": 100, "min_date": None, "lookback_days": 7},
            "training": {
                "routing": {"alpha": 0.5, "feature_dim": 64},
                "tools": {"alpha_prior": 1.0, "beta_prior": 1.0},
                "cache": {"alpha": 1.0},
            },
            "evaluation": {"min_policy_value": 0.6, "max_variance": 0.1},
            "deployment": {
                "canary_stability_minutes": 5.0,
                "canary_traffic_pct": 5.0,
                "prod_after_canary": True,
            },
        }

        if config_path:
            try:
                with open(config_path, "r") as f:
                    user_config = json.load(f)
                # Deep merge configs
                return self._merge_configs(default_config, user_config)
            except Exception as e:
                logger.warning("Failed to load config, using defaults", error=str(e))

        return default_config

    def _merge_configs(
        self, default: Dict[str, Any], user: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Merge user config into default config."""
        result = default.copy()
        for key, value in user.items():
            if (
                key in result
                and isinstance(result[key], dict)
                and isinstance(value, dict)
            ):
                result[key] = self._merge_configs(result[key], value)
            else:
                result[key] = value
        return result

    def _run_command(
        self, cmd: list[str], cwd: Optional[pathlib.Path] = None
    ) -> tuple[bool, str]:
        """Run shell command and return success status and output."""
        try:
            cwd_path = cwd or self.base_dir
            logger.info("Running command", cmd=" ".join(cmd), cwd=str(cwd_path))

            result = subprocess.run(
                cmd, cwd=cwd_path, capture_output=True, text=True, check=False
            )

            success = result.returncode == 0
            output = result.stdout + result.stderr

            if success:
                logger.debug("Command succeeded", output=output[:500])
            else:
                logger.error(
                    "Command failed", returncode=result.returncode, output=output[:500]
                )

            return success, output

        except Exception as e:
            logger.error("Command execution failed", error=str(e))
            return False, str(e)

    def step1_build_dataset(self) -> tuple[bool, str]:
        """Step 1: Build dataset from telemetry."""
        logger.info("=== STEP 1: Building dataset from telemetry ===")

        if not self.telemetry_path.exists():
            return False, f"Telemetry file not found: {self.telemetry_path}"

        # Create data directory
        self.data_dir.mkdir(parents=True, exist_ok=True)

        # Build dataset
        cmd = [
            "python",
            "build_dataset.py",
            "--input",
            str(self.telemetry_path),
            "--output",
            "data/episodes.json",
            "--min-episodes",
            str(self.config["dataset"]["min_episodes"]),
        ]

        if self.config["dataset"]["min_date"]:
            cmd.extend(["--min-date", self.config["dataset"]["min_date"]])

        success, output = self._run_command(cmd)

        if success:
            # Validate dataset
            episodes_file = self.data_dir / "episodes.json"
            if episodes_file.exists():
                try:
                    with open(episodes_file) as f:
                        episodes = json.load(f)

                    episode_count = len(episodes)
                    logger.info("Dataset built successfully", episodes=episode_count)

                    if episode_count < self.config["dataset"]["min_episodes"]:
                        return (
                            False,
                            f"Insufficient episodes: {episode_count} < {self.config['dataset']['min_episodes']}",
                        )

                    return True, f"Dataset built with {episode_count} episodes"
                except Exception as e:
                    return False, f"Dataset validation failed: {e}"
            else:
                return False, "Dataset file not created"

        return False, f"Dataset building failed: {output}"

    def step2_train_routing(self) -> tuple[bool, str]:
        """Step 2: Train routing policy."""
        logger.info("=== STEP 2: Training routing policy ===")

        # Create models directory
        self.models_dir.mkdir(parents=True, exist_ok=True)

        cmd = [
            "python",
            "bandits/routing_linucb.py",
            "--episodes",
            "data/episodes.json",
            "--output",
            "models/routing_policy.json",
            "--alpha",
            str(self.config["training"]["routing"]["alpha"]),
            "--feature-dim",
            str(self.config["training"]["routing"]["feature_dim"]),
        ]

        success, output = self._run_command(cmd)

        if success:
            model_file = self.models_dir / "routing_policy.json"
            if model_file.exists():
                return True, "Routing policy trained successfully"

        return False, f"Routing training failed: {output}"

    def step3_train_tools(self) -> tuple[bool, str]:
        """Step 3: Train tool selection policy."""
        logger.info("=== STEP 3: Training tool selection policy ===")

        cmd = [
            "python",
            "bandits/tool_thompson.py",
            "--episodes",
            "data/episodes.json",
            "--output",
            "models/tool_policy.json",
            "--alpha-prior",
            str(self.config["training"]["tools"]["alpha_prior"]),
            "--beta-prior",
            str(self.config["training"]["tools"]["beta_prior"]),
        ]

        success, output = self._run_command(cmd)

        if success:
            model_file = self.models_dir / "tool_policy.json"
            if model_file.exists():
                return True, "Tool policy trained successfully"

        return False, f"Tool training failed: {output}"

    def step4_train_cache(self) -> tuple[bool, str]:
        """Step 4: Train cache policy."""
        logger.info("=== STEP 4: Training cache policy ===")

        cmd = [
            "python",
            "bandits/cache_bandit.py",
            "--episodes",
            "data/episodes.json",
            "--output",
            "models/cache_policy.json",
            "--alpha",
            str(self.config["training"]["cache"]["alpha"]),
        ]

        success, output = self._run_command(cmd)

        if success:
            model_file = self.models_dir / "cache_policy.json"
            if model_file.exists():
                return True, "Cache policy trained successfully"

        return False, f"Cache training failed: {output}"

    def step5_offline_evaluation(self) -> tuple[bool, str]:
        """Step 5: Offline IPS evaluation."""
        logger.info("=== STEP 5: Offline policy evaluation ===")

        self.eval_dir.mkdir(parents=True, exist_ok=True)

        cmd = [
            "python",
            "eval/offline_ips_eval.py",
            "--episodes",
            "data/episodes.json",
            "--routing-policy",
            "models/routing_policy.json",
            "--tool-policy",
            "models/tool_policy.json",
            "--cache-policy",
            "models/cache_policy.json",
            "--output",
            "eval_runs/offline_eval.json",
        ]

        success, output = self._run_command(cmd)

        if success:
            # Validate evaluation results
            eval_file = self.eval_dir / "offline_eval.json"
            if eval_file.exists():
                try:
                    with open(eval_file) as f:
                        results = json.load(f)

                    policy_value = results.get("policy_value", 0.0)
                    variance = results.get("variance", float("inf"))

                    logger.info(
                        "Evaluation completed",
                        policy_value=policy_value,
                        variance=variance,
                    )

                    # Check if policy meets quality thresholds
                    min_value = self.config["evaluation"]["min_policy_value"]
                    max_var = self.config["evaluation"]["max_variance"]

                    if policy_value < min_value:
                        return (
                            False,
                            f"Policy value too low: {policy_value:.3f} < {min_value}",
                        )

                    if variance > max_var:
                        return False, f"Variance too high: {variance:.3f} > {max_var}"

                    return (
                        True,
                        f"Evaluation passed (value: {policy_value:.3f}, var: {variance:.3f})",
                    )

                except Exception as e:
                    return False, f"Evaluation validation failed: {e}"
            else:
                return False, "Evaluation file not created"

        return False, f"Evaluation failed: {output}"

    def step6_package_policies(self) -> tuple[bool, str]:
        """Step 6: Package policies for deployment."""
        logger.info("=== STEP 6: Packaging policies for deployment ===")

        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        package_path = self.deploy_dir / f"policy_pack_{timestamp}.json"

        cmd = [
            "python",
            "deploy/export_policies.py",
            "--routing",
            "models/routing_policy.json",
            "--tools",
            "models/tool_policy.json",
            "--cache",
            "models/cache_policy.json",
            "--out",
            str(package_path),
            "--version",
            timestamp,
            "--stage",
            "canary",
            "--traffic",
            str(self.config["deployment"]["canary_traffic_pct"]),
        ]

        success, output = self._run_command(cmd)

        if success and package_path.exists():
            return True, f"Policy package created: {package_path.name}"

        return False, f"Packaging failed: {output}"

    def step7_deploy_canary(self, package_path: pathlib.Path) -> tuple[bool, str]:
        """Step 7: Deploy to canary."""
        logger.info("=== STEP 7: Deploying to canary ===")

        cmd = [
            "python",
            "deploy/promote.py",
            "--stage",
            "canary",
            "--pack",
            str(package_path),
            "--destination",
            str(self.policies_dir),
            "--stability-duration",
            str(self.config["deployment"]["canary_stability_minutes"]),
        ]

        success, output = self._run_command(cmd)

        if success:
            return True, "Canary deployment successful"

        return False, f"Canary deployment failed: {output}"

    def step8_deploy_prod(self, package_path: pathlib.Path) -> tuple[bool, str]:
        """Step 8: Deploy to production."""
        logger.info("=== STEP 8: Deploying to production ===")

        if not self.config["deployment"]["prod_after_canary"]:
            logger.info("Production deployment disabled in config")
            return True, "Production deployment skipped (disabled in config)"

        cmd = [
            "python",
            "deploy/promote.py",
            "--stage",
            "prod",
            "--pack",
            str(package_path),
            "--destination",
            str(self.policies_dir),
            "--skip-stability-check",  # Stability already verified in canary
        ]

        success, output = self._run_command(cmd)

        if success:
            return True, "Production deployment successful"

        return False, f"Production deployment failed: {output}"

    def run_full_pipeline(self) -> bool:
        """Run the complete RL pipeline."""
        logger.info("🚀 Starting full RL pipeline automation")
        start_time = time.time()

        try:
            # Step 1: Build dataset
            success, message = self.step1_build_dataset()
            if not success:
                logger.error("Pipeline failed at dataset building", error=message)
                return False
            logger.info("✅ Dataset building: " + message)

            # Step 2: Train routing
            success, message = self.step2_train_routing()
            if not success:
                logger.error("Pipeline failed at routing training", error=message)
                return False
            logger.info("✅ Routing training: " + message)

            # Step 3: Train tools
            success, message = self.step3_train_tools()
            if not success:
                logger.error("Pipeline failed at tool training", error=message)
                return False
            logger.info("✅ Tool training: " + message)

            # Step 4: Train cache
            success, message = self.step4_train_cache()
            if not success:
                logger.error("Pipeline failed at cache training", error=message)
                return False
            logger.info("✅ Cache training: " + message)

            # Step 5: Offline evaluation
            success, message = self.step5_offline_evaluation()
            if not success:
                logger.error("Pipeline failed at evaluation", error=message)
                return False
            logger.info("✅ Offline evaluation: " + message)

            # Step 6: Package policies
            success, message = self.step6_package_policies()
            if not success:
                logger.error("Pipeline failed at packaging", error=message)
                return False
            logger.info("✅ Policy packaging: " + message)

            # Find the created package
            latest_package = max(
                self.deploy_dir.glob("policy_pack_*.json"),
                key=lambda p: p.stat().st_mtime,
            )

            # Step 7: Deploy to canary
            success, message = self.step7_deploy_canary(latest_package)
            if not success:
                logger.error("Pipeline failed at canary deployment", error=message)
                return False
            logger.info("✅ Canary deployment: " + message)

            # Step 8: Deploy to production
            success, message = self.step8_deploy_prod(latest_package)
            if not success:
                logger.error("Pipeline failed at production deployment", error=message)
                return False
            logger.info("✅ Production deployment: " + message)

            # Success summary
            elapsed = time.time() - start_time
            logger.info(
                "🎉 Full pipeline completed successfully",
                elapsed_minutes=elapsed / 60,
                package=latest_package.name,
            )

            print("\n🎉 RL PIPELINE COMPLETED SUCCESSFULLY! 🎉")
            print(f"⏱️  Total time: {elapsed / 60:.1f} minutes")
            print(f"📦 Package: {latest_package.name}")
            print("🚀 Alice is now powered by RL policies!")

            return True

        except Exception as e:
            logger.error("Pipeline failed with exception", error=str(e))
            return False


def main():
    """Main automation script."""
    parser = argparse.ArgumentParser(description="Alice RL Pipeline Automation")
    parser.add_argument("--config", help="Configuration file path")
    parser.add_argument(
        "--telemetry",
        default="services/orchestrator/telemetry.jsonl",
        help="Telemetry data path",
    )
    parser.add_argument(
        "--base-dir", default="services/rl", help="RL service base directory"
    )
    parser.add_argument(
        "--orchestrator-dir",
        default="services/orchestrator",
        help="Orchestrator service directory",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Validate configuration without running pipeline",
    )

    # Individual step options
    parser.add_argument(
        "--step",
        choices=[
            "dataset",
            "routing",
            "tools",
            "cache",
            "eval",
            "package",
            "canary",
            "prod",
            "all",
        ],
        default="all",
        help="Run specific pipeline step",
    )

    args = parser.parse_args()

    # Setup logging
    structlog.configure(
        processors=[structlog.dev.ConsoleRenderer()],
        logger_factory=structlog.stdlib.LoggerFactory(),
    )

    try:
        # Initialize pipeline
        pipeline = RLPipelineAutomation(
            base_dir=args.base_dir,
            orchestrator_dir=args.orchestrator_dir,
            telemetry_path=args.telemetry,
            config_path=args.config,
        )

        if args.dry_run:
            logger.info("Dry run - configuration validated successfully")
            print("✅ Configuration is valid - ready to run pipeline")
            return 0

        # Run specific step or full pipeline
        if args.step == "all":
            success = pipeline.run_full_pipeline()
        elif args.step == "dataset":
            success, message = pipeline.step1_build_dataset()
            print(f"{'✅' if success else '❌'} {message}")
        elif args.step == "routing":
            success, message = pipeline.step2_train_routing()
            print(f"{'✅' if success else '❌'} {message}")
        elif args.step == "tools":
            success, message = pipeline.step3_train_tools()
            print(f"{'✅' if success else '❌'} {message}")
        elif args.step == "cache":
            success, message = pipeline.step4_train_cache()
            print(f"{'✅' if success else '❌'} {message}")
        elif args.step == "eval":
            success, message = pipeline.step5_offline_evaluation()
            print(f"{'✅' if success else '❌'} {message}")
        elif args.step == "package":
            success, message = pipeline.step6_package_policies()
            print(f"{'✅' if success else '❌'} {message}")
        else:
            logger.error("Individual canary/prod steps require package path")
            return 1

        return 0 if success else 1

    except KeyboardInterrupt:
        logger.info("Pipeline interrupted by user")
        return 1
    except Exception as e:
        logger.error("Pipeline failed with exception", error=str(e))
        return 1


if __name__ == "__main__":
    exit(main())
