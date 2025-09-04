"""
Export and package RL policies for deployment.

Combines multiple trained policies into a single deployment package
with validation and versioning.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import pathlib
from datetime import datetime
from typing import Any, Dict, Optional

import structlog

logger = structlog.get_logger(__name__)


def compute_file_hash(file_path: pathlib.Path) -> str:
    """Compute SHA256 hash of file for integrity checking."""
    if not file_path.exists():
        return ""

    sha256_hash = hashlib.sha256()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            sha256_hash.update(chunk)
    return sha256_hash.hexdigest()


def validate_policy_file(
    file_path: pathlib.Path, expected_keys: list[str]
) -> tuple[bool, str]:
    """
    Validate policy file structure.

    Args:
        file_path: Path to policy JSON file
        expected_keys: Required top-level keys

    Returns:
        (is_valid, error_message)
    """
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        if not isinstance(data, dict):
            return False, "Policy file must contain a JSON object"

        missing_keys = [key for key in expected_keys if key not in data]
        if missing_keys:
            return False, f"Missing required keys: {missing_keys}"

        # Additional validation can be added here
        return True, ""

    except json.JSONDecodeError as e:
        return False, f"Invalid JSON: {e}"
    except Exception as e:
        return False, f"Validation error: {e}"


def create_policy_package(
    routing_path: Optional[str] = None,
    tools_path: Optional[str] = None,
    cache_path: Optional[str] = None,
    dpo_path: Optional[str] = None,
    version: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Create unified policy package from individual policy files.

    Args:
        routing_path: Path to routing policy JSON
        tools_path: Path to tools policy JSON
        cache_path: Path to cache policy JSON
        dpo_path: Path to DPO adapter (placeholder)
        version: Package version (auto-generated if None)

    Returns:
        Policy package dict
    """
    if version is None:
        version = datetime.now().strftime("%Y%m%d-%H%M%S")

    package = {
        "version": version,
        "created_at": datetime.now().isoformat(),
        "format_version": "1.0",
        "policies": {},
        "metadata": {"source_files": {}, "file_hashes": {}, "validation_results": {}},
    }

    # Load and validate routing policy
    if routing_path:
        routing_file = pathlib.Path(routing_path)
        if routing_file.exists():
            valid, error = validate_policy_file(
                routing_file, ["routing_policy", "feature_maker"]
            )

            if valid:
                with open(routing_file, "r", encoding="utf-8") as f:
                    routing_data = json.load(f)
                package["policies"]["routing"] = routing_data
                package["metadata"]["source_files"]["routing"] = str(routing_file)
                package["metadata"]["file_hashes"]["routing"] = compute_file_hash(
                    routing_file
                )
                package["metadata"]["validation_results"]["routing"] = {"valid": True}

                logger.info("Loaded routing policy", path=routing_path)
            else:
                package["metadata"]["validation_results"]["routing"] = {
                    "valid": False,
                    "error": error,
                }
                logger.error("Invalid routing policy", path=routing_path, error=error)
        else:
            logger.warning("Routing policy file not found", path=routing_path)

    # Load and validate tools policy
    if tools_path:
        tools_file = pathlib.Path(tools_path)
        if tools_file.exists():
            valid, error = validate_policy_file(tools_file, ["tool_policy"])

            if valid:
                with open(tools_file, "r", encoding="utf-8") as f:
                    tools_data = json.load(f)
                package["policies"]["tools"] = tools_data
                package["metadata"]["source_files"]["tools"] = str(tools_file)
                package["metadata"]["file_hashes"]["tools"] = compute_file_hash(
                    tools_file
                )
                package["metadata"]["validation_results"]["tools"] = {"valid": True}

                logger.info("Loaded tools policy", path=tools_path)
            else:
                package["metadata"]["validation_results"]["tools"] = {
                    "valid": False,
                    "error": error,
                }
                logger.error("Invalid tools policy", path=tools_path, error=error)
        else:
            logger.warning("Tools policy file not found", path=tools_path)

    # Load cache policy (simpler format)
    if cache_path:
        cache_file = pathlib.Path(cache_path)
        if cache_file.exists():
            valid, error = validate_policy_file(cache_file, ["cache_policy"])

            if valid:
                with open(cache_file, "r", encoding="utf-8") as f:
                    cache_data = json.load(f)
                package["policies"]["cache"] = cache_data
                package["metadata"]["source_files"]["cache"] = str(cache_file)
                package["metadata"]["file_hashes"]["cache"] = compute_file_hash(
                    cache_file
                )
                package["metadata"]["validation_results"]["cache"] = {"valid": True}

                logger.info("Loaded cache policy", path=cache_path)
            else:
                package["metadata"]["validation_results"]["cache"] = {
                    "valid": False,
                    "error": error,
                }
                logger.error("Invalid cache policy", path=cache_path, error=error)
        else:
            logger.warning("Cache policy file not found", path=cache_path)

    # DPO adapter (placeholder for future implementation)
    if dpo_path:
        dpo_file = pathlib.Path(dpo_path)
        if dpo_file.exists():
            package["policies"]["dpo_adapter"] = {
                "adapter_path": str(dpo_file),
                "adapter_hash": compute_file_hash(dpo_file),
                "adapter_type": "lora",
                "base_model": "qwen2.5-3b-instruct",
            }
            package["metadata"]["source_files"]["dpo"] = str(dpo_file)
            package["metadata"]["file_hashes"]["dpo"] = compute_file_hash(dpo_file)
            package["metadata"]["validation_results"]["dpo"] = {"valid": True}

            logger.info("Loaded DPO adapter", path=dpo_path)
        else:
            logger.warning("DPO adapter file not found", path=dpo_path)

    # Package-level validation
    valid_policies = sum(
        1
        for result in package["metadata"]["validation_results"].values()
        if result["valid"]
    )
    total_policies = len(package["metadata"]["validation_results"])

    package["metadata"]["package_valid"] = (
        valid_policies == total_policies and total_policies > 0
    )
    package["metadata"]["policies_loaded"] = valid_policies
    package["metadata"]["policies_attempted"] = total_policies

    if package["metadata"]["package_valid"]:
        logger.info(
            "Policy package created successfully",
            version=version,
            policies=valid_policies,
        )
    else:
        logger.warning(
            "Policy package has validation issues",
            valid=valid_policies,
            total=total_policies,
        )

    return package


def generate_deployment_config(
    package: Dict[str, Any], stage: str = "canary", traffic_percentage: float = 5.0
) -> Dict[str, Any]:
    """
    Generate deployment configuration for a given stage.

    Args:
        package: Policy package
        stage: Deployment stage ("canary", "prod")
        traffic_percentage: Percentage of traffic for canary (ignored for prod)

    Returns:
        Deployment config dict
    """
    config = {
        "stage": stage,
        "package_version": package["version"],
        "deployment_time": datetime.now().isoformat(),
        "policies_enabled": {},
        "rollback_config": {
            "enabled": True,
            "trigger_conditions": {
                "success_rate_drop": 0.05,  # 5% drop triggers rollback
                "latency_increase": 0.2,  # 20% increase triggers rollback
                "error_rate_increase": 0.1,  # 10% increase triggers rollback
            },
        },
    }

    if stage == "canary":
        config["traffic_percentage"] = traffic_percentage
        config["monitoring"] = {
            "enhanced": True,
            "alert_on_anomaly": True,
            "comparison_baseline": "prod",
        }
    elif stage == "prod":
        config["traffic_percentage"] = 100.0
        config["monitoring"] = {"standard": True}

    # Enable policies that are valid in the package
    if "routing" in package["policies"]:
        config["policies_enabled"]["routing"] = True
    if "tools" in package["policies"]:
        config["policies_enabled"]["tools"] = True
    if "cache" in package["policies"]:
        config["policies_enabled"]["cache"] = True
    if "dpo_adapter" in package["policies"]:
        config["policies_enabled"]["dpo"] = True

    return config


def main():
    """Main export script."""
    parser = argparse.ArgumentParser(description="Export RL policies for deployment")
    parser.add_argument("--routing", help="Path to routing policy JSON")
    parser.add_argument("--tools", help="Path to tools policy JSON")
    parser.add_argument("--cache", help="Path to cache policy JSON")
    parser.add_argument("--dpo", help="Path to DPO adapter file")
    parser.add_argument("--out", required=True, help="Output policy package file")
    parser.add_argument(
        "--version", help="Package version (auto-generated if not provided)"
    )
    parser.add_argument(
        "--stage", choices=["canary", "prod"], default="canary", help="Deployment stage"
    )
    parser.add_argument(
        "--traffic",
        type=float,
        default=5.0,
        help="Traffic percentage for canary deployment",
    )
    parser.add_argument(
        "--validate-only",
        action="store_true",
        help="Only validate inputs, don't create package",
    )

    args = parser.parse_args()

    # Setup logging
    structlog.configure(
        processors=[structlog.dev.ConsoleRenderer()],
        logger_factory=structlog.stdlib.LoggerFactory(),
    )

    try:
        # Validate that at least one policy is provided
        policy_paths = [args.routing, args.tools, args.cache, args.dpo]
        if not any(policy_paths):
            raise ValueError("At least one policy file must be provided")

        if args.validate_only:
            logger.info("Validation-only mode - checking policy files")

            valid_count = 0
            for name, path in [
                ("routing", args.routing),
                ("tools", args.tools),
                ("cache", args.cache),
                ("dpo", args.dpo),
            ]:
                if path:
                    file_path = pathlib.Path(path)
                    if file_path.exists():
                        if name == "dpo":
                            # DPO files are binary, just check existence
                            logger.info("DPO file exists", path=path)
                            valid_count += 1
                        else:
                            # Validate JSON policies
                            expected_keys = {
                                "routing": ["routing_policy", "feature_maker"],
                                "tools": ["tool_policy"],
                                "cache": ["cache_policy"],
                            }

                            valid, error = validate_policy_file(
                                file_path, expected_keys[name]
                            )
                            if valid:
                                logger.info("Valid policy file", type=name, path=path)
                                valid_count += 1
                            else:
                                logger.error(
                                    "Invalid policy file",
                                    type=name,
                                    path=path,
                                    error=error,
                                )
                    else:
                        logger.error("Policy file not found", type=name, path=path)

            logger.info("Validation complete", valid_files=valid_count)
            return

        # Create policy package
        logger.info("Creating policy package")
        package = create_policy_package(
            routing_path=args.routing,
            tools_path=args.tools,
            cache_path=args.cache,
            dpo_path=args.dpo,
            version=args.version,
        )

        if not package["metadata"]["package_valid"]:
            logger.error("Package validation failed - some policies are invalid")
            # Still save package but with warnings

        # Generate deployment config
        deployment_config = generate_deployment_config(
            package, stage=args.stage, traffic_percentage=args.traffic
        )
        package["deployment_config"] = deployment_config

        # Save package
        output_path = pathlib.Path(args.out)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(package, f, indent=2, ensure_ascii=False)

        logger.info(
            "Policy package exported",
            path=output_path,
            version=package["version"],
            stage=args.stage,
            policies=package["metadata"]["policies_loaded"],
        )

        # Print summary
        print(f"✅ Policy package created: {output_path}")
        print(f"📦 Version: {package['version']}")
        print(f"🎯 Stage: {args.stage}")
        print(
            f"📊 Policies: {package['metadata']['policies_loaded']}/{package['metadata']['policies_attempted']}"
        )

        if args.stage == "canary":
            print(f"🚦 Traffic: {args.traffic}%")

        if not package["metadata"]["package_valid"]:
            print("⚠️  Warning: Some policy validations failed")
            print("   Check logs for details")

    except Exception as e:
        logger.error("Export failed", error=str(e))
        raise


if __name__ == "__main__":
    main()
