"""
Promote RL policies from canary to production with safety checks.

Handles canary deployment, monitoring, and promotion to production
with automatic rollback capabilities.
"""

from __future__ import annotations

import argparse
import json
import pathlib
import shutil
import time
from datetime import datetime, timedelta
from typing import Any, Dict

import structlog

try:
    import requests
except ImportError:
    requests = None

logger = structlog.get_logger(__name__)


class PolicyPromoter:
    """
    Handles policy promotion with safety checks and rollback capabilities.
    """

    def __init__(
        self,
        orchestrator_url: str = "http://localhost:8000",
        health_check_timeout: float = 30.0,
    ):
        """
        Initialize policy promoter.

        Args:
            orchestrator_url: Base URL for orchestrator service
            health_check_timeout: Timeout for health checks in seconds
        """
        self.orchestrator_url = orchestrator_url.rstrip("/")
        self.health_check_timeout = health_check_timeout

        logger.info("Policy promoter initialized", orchestrator_url=orchestrator_url)

    def health_check(self) -> tuple[bool, Dict[str, Any]]:
        """
        Check orchestrator health before deployment.

        Returns:
            (is_healthy, health_status)
        """
        if not requests:
            logger.warning("Requests library not available - skipping health check")
            return True, {"status": "unknown", "reason": "no_requests_lib"}

        try:
            response = requests.get(
                f"{self.orchestrator_url}/health", timeout=self.health_check_timeout
            )

            if response.status_code == 200:
                health_data = (
                    response.json()
                    if response.headers.get("content-type", "").startswith(
                        "application/json"
                    )
                    else {}
                )
                return True, {"status": "healthy", "data": health_data}
            else:
                return False, {
                    "status": "unhealthy",
                    "http_code": response.status_code,
                    "response": response.text[:200],
                }

        except Exception as e:
            return False, {"status": "error", "error": str(e)}

    def deploy_to_stage(
        self, package_path: pathlib.Path, stage: str, destination_dir: pathlib.Path
    ) -> tuple[bool, str]:
        """
        Deploy policy package to specified stage.

        Args:
            package_path: Path to policy package JSON
            stage: Target stage ("canary" or "prod")
            destination_dir: Destination directory for policies

        Returns:
            (success, message)
        """
        try:
            # Create destination directory
            destination_dir.mkdir(parents=True, exist_ok=True)

            # Load and validate package
            with open(package_path, "r", encoding="utf-8") as f:
                package = json.load(f)

            if not package.get("metadata", {}).get("package_valid", False):
                return (
                    False,
                    "Package validation failed - cannot deploy invalid package",
                )

            # Copy package to destination
            stage_package_path = destination_dir / f"policy_pack_{stage}.json"
            shutil.copy2(package_path, stage_package_path)

            # Create stage marker
            stage_info = {
                "stage": stage,
                "deployed_at": datetime.now().isoformat(),
                "package_version": package["version"],
                "package_path": str(stage_package_path),
                "deployment_config": package.get("deployment_config", {}),
            }

            stage_marker_path = destination_dir / f"stage_{stage}.json"
            with open(stage_marker_path, "w", encoding="utf-8") as f:
                json.dump(stage_info, f, indent=2)

            # Create symbolic link to active package for easy access
            active_link = destination_dir / "active_policy_pack.json"
            if active_link.exists() or active_link.is_symlink():
                active_link.unlink()
            active_link.symlink_to(stage_package_path.name)

            logger.info(
                "Deployed package to stage",
                stage=stage,
                package_version=package["version"],
                destination=str(stage_package_path),
            )

            return True, f"Successfully deployed to {stage}"

        except Exception as e:
            error_msg = f"Deployment failed: {str(e)}"
            logger.error("Deployment failed", stage=stage, error=str(e))
            return False, error_msg

    def create_rollback_point(
        self, destination_dir: pathlib.Path, stage: str
    ) -> tuple[bool, str]:
        """
        Create rollback point before deployment.

        Args:
            destination_dir: Policy directory
            stage: Stage being deployed

        Returns:
            (success, message)
        """
        try:
            rollback_dir = destination_dir / "rollback"
            rollback_dir.mkdir(exist_ok=True)

            # Save current active package if it exists
            active_package = destination_dir / "active_policy_pack.json"
            if active_package.exists():
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                rollback_package = rollback_dir / f"rollback_{stage}_{timestamp}.json"
                shutil.copy2(active_package, rollback_package)

                # Save rollback info
                rollback_info = {
                    "created_at": datetime.now().isoformat(),
                    "stage": stage,
                    "previous_package": str(rollback_package),
                    "trigger": "pre_deployment",
                }

                rollback_info_path = rollback_dir / f"rollback_{stage}_info.json"
                with open(rollback_info_path, "w", encoding="utf-8") as f:
                    json.dump(rollback_info, f, indent=2)

                logger.info(
                    "Created rollback point",
                    stage=stage,
                    rollback_package=str(rollback_package),
                )

                return True, "Rollback point created"
            else:
                return True, "No existing package to backup"

        except Exception as e:
            error_msg = f"Failed to create rollback point: {str(e)}"
            logger.error("Rollback point creation failed", error=str(e))
            return False, error_msg

    def rollback_deployment(
        self, destination_dir: pathlib.Path, stage: str
    ) -> tuple[bool, str]:
        """
        Rollback to previous deployment.

        Args:
            destination_dir: Policy directory
            stage: Stage to rollback

        Returns:
            (success, message)
        """
        try:
            rollback_dir = destination_dir / "rollback"
            rollback_info_path = rollback_dir / f"rollback_{stage}_info.json"

            if not rollback_info_path.exists():
                return False, f"No rollback point found for stage {stage}"

            with open(rollback_info_path, "r", encoding="utf-8") as f:
                rollback_info = json.load(f)

            previous_package = pathlib.Path(rollback_info["previous_package"])
            if not previous_package.exists():
                return False, f"Rollback package not found: {previous_package}"

            # Restore previous package
            active_package = destination_dir / "active_policy_pack.json"
            if active_package.exists() or active_package.is_symlink():
                active_package.unlink()

            shutil.copy2(previous_package, active_package)

            # Update stage marker
            rollback_stage_info = {
                "stage": stage,
                "deployed_at": datetime.now().isoformat(),
                "rollback_from": rollback_info,
                "status": "rolled_back",
            }

            stage_marker_path = destination_dir / f"stage_{stage}.json"
            with open(stage_marker_path, "w", encoding="utf-8") as f:
                json.dump(rollback_stage_info, f, indent=2)

            logger.info(
                "Rollback completed",
                stage=stage,
                restored_package=str(previous_package),
            )

            return True, f"Successfully rolled back {stage} to previous version"

        except Exception as e:
            error_msg = f"Rollback failed: {str(e)}"
            logger.error("Rollback failed", stage=stage, error=str(e))
            return False, error_msg

    def wait_for_stability(
        self, duration_minutes: float = 5.0, check_interval: float = 30.0
    ) -> tuple[bool, Dict[str, Any]]:
        """
        Wait and monitor system stability after deployment.

        Args:
            duration_minutes: How long to monitor
            check_interval: Health check interval in seconds

        Returns:
            (is_stable, monitoring_results)
        """
        logger.info(
            "Monitoring system stability",
            duration_minutes=duration_minutes,
            check_interval=check_interval,
        )

        end_time = datetime.now() + timedelta(minutes=duration_minutes)
        checks = []

        while datetime.now() < end_time:
            healthy, health_status = self.health_check()

            check_result = {
                "timestamp": datetime.now().isoformat(),
                "healthy": healthy,
                "health_status": health_status,
            }
            checks.append(check_result)

            if not healthy:
                logger.warning(
                    "Health check failed during stability monitoring",
                    health_status=health_status,
                )

            # Wait before next check
            time.sleep(check_interval)

        # Analyze stability
        healthy_checks = sum(1 for check in checks if check["healthy"])
        total_checks = len(checks)
        stability_ratio = healthy_checks / total_checks if total_checks > 0 else 0.0

        is_stable = stability_ratio >= 0.8  # 80% healthy checks required

        monitoring_results = {
            "total_checks": total_checks,
            "healthy_checks": healthy_checks,
            "stability_ratio": stability_ratio,
            "is_stable": is_stable,
            "duration_minutes": duration_minutes,
            "checks": checks[-10:],  # Keep last 10 checks for debugging
        }

        logger.info(
            "Stability monitoring complete",
            stability_ratio=stability_ratio,
            is_stable=is_stable,
            total_checks=total_checks,
        )

        return is_stable, monitoring_results


def main():
    """Main promotion script."""
    parser = argparse.ArgumentParser(description="Promote RL policies between stages")
    parser.add_argument(
        "--stage",
        choices=["canary", "prod"],
        required=True,
        help="Target deployment stage",
    )
    parser.add_argument("--pack", required=True, help="Path to policy package JSON")
    parser.add_argument(
        "--destination",
        default="services/orchestrator/src/policies/live",
        help="Destination directory for policies",
    )
    parser.add_argument(
        "--orchestrator-url",
        default="http://localhost:8000",
        help="Orchestrator service URL",
    )
    parser.add_argument(
        "--skip-health-check",
        action="store_true",
        help="Skip health check before deployment",
    )
    parser.add_argument(
        "--skip-stability-check",
        action="store_true",
        help="Skip stability monitoring after deployment",
    )
    parser.add_argument(
        "--stability-duration",
        type=float,
        default=5.0,
        help="Stability monitoring duration in minutes",
    )
    parser.add_argument(
        "--rollback", action="store_true", help="Rollback instead of deploying"
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Force deployment even if health checks fail",
    )

    args = parser.parse_args()

    # Setup logging
    structlog.configure(
        processors=[structlog.dev.ConsoleRenderer()],
        logger_factory=structlog.stdlib.LoggerFactory(),
    )

    try:
        package_path = pathlib.Path(args.pack)
        destination_dir = pathlib.Path(args.destination)

        # Initialize promoter
        promoter = PolicyPromoter(orchestrator_url=args.orchestrator_url)

        # Handle rollback
        if args.rollback:
            logger.info("Performing rollback", stage=args.stage)
            success, message = promoter.rollback_deployment(destination_dir, args.stage)

            if success:
                print(f"✅ {message}")
                logger.info("Rollback successful")
            else:
                print(f"❌ {message}")
                logger.error("Rollback failed")
                return 1

            return 0

        # Validate package exists
        if not package_path.exists():
            logger.error("Policy package not found", path=package_path)
            return 1

        # Pre-deployment health check
        if not args.skip_health_check:
            logger.info("Performing pre-deployment health check")
            healthy, health_status = promoter.health_check()

            if not healthy and not args.force:
                logger.error(
                    "Pre-deployment health check failed", health_status=health_status
                )
                print("❌ Health check failed - use --force to override")
                return 1
            elif not healthy:
                logger.warning("Health check failed but continuing due to --force flag")

        # Create rollback point
        logger.info("Creating rollback point")
        rollback_success, rollback_message = promoter.create_rollback_point(
            destination_dir, args.stage
        )

        if not rollback_success:
            logger.warning("Failed to create rollback point", message=rollback_message)

        # Deploy package
        logger.info(
            "Deploying policy package", stage=args.stage, package=str(package_path)
        )

        deploy_success, deploy_message = promoter.deploy_to_stage(
            package_path, args.stage, destination_dir
        )

        if not deploy_success:
            logger.error("Deployment failed", message=deploy_message)
            print(f"❌ {deploy_message}")
            return 1

        print(f"✅ {deploy_message}")

        # Post-deployment stability check
        if not args.skip_stability_check and args.stage == "canary":
            logger.info("Starting post-deployment stability monitoring")

            stable, monitoring_results = promoter.wait_for_stability(
                duration_minutes=args.stability_duration
            )

            if not stable:
                logger.error(
                    "System unstable after deployment",
                    monitoring_results=monitoring_results,
                )

                print("❌ System unstable - consider rollback")
                print(
                    f"   Stability ratio: {monitoring_results['stability_ratio']:.2%}"
                )

                # Auto-rollback for canary if very unstable
                if monitoring_results["stability_ratio"] < 0.5:
                    logger.warning("Auto-rolling back due to severe instability")
                    rollback_success, rollback_message = promoter.rollback_deployment(
                        destination_dir, args.stage
                    )

                    if rollback_success:
                        print(f"🔄 Auto-rollback completed: {rollback_message}")
                    else:
                        print(f"❌ Auto-rollback failed: {rollback_message}")

                return 1
            else:
                logger.info("System stable after deployment")
                print(
                    f"✅ System stable (ratio: {monitoring_results['stability_ratio']:.2%})"
                )

        # Success summary
        print(f"🚀 Deployment to {args.stage} completed successfully")

        if args.stage == "canary":
            print("📊 Monitor canary performance before promoting to production")
            print(f"   Use: python {__file__} --stage prod --pack {args.pack}")
        else:
            print("🎉 Production deployment complete!")

        return 0

    except KeyboardInterrupt:
        logger.info("Deployment interrupted by user")
        print("🛑 Deployment interrupted")
        return 1
    except Exception as e:
        logger.error("Deployment failed with exception", error=str(e))
        print(f"❌ Deployment failed: {str(e)}")
        return 1


if __name__ == "__main__":
    exit(main())
