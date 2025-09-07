#!/usr/bin/env python3
"""
Schema migration utilities for Episode data
Handles backward compatibility when schema evolves
"""

import json
import logging
from typing import Any, Dict, List

from packaging import version

logger = logging.getLogger(__name__)

# Current schema version - update when making breaking changes
CURRENT_SCHEMA_VERSION = "1.0.0"


def migrate_episode_data(episode_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Migrate episode data to current schema version

    Args:
        episode_data: Raw episode dictionary from JSONL

    Returns:
        Migrated episode data compatible with current schema
    """
    # Default to 1.0.0 if no version specified (backward compatibility)
    data_version = episode_data.get("schema_version", "1.0.0")

    if data_version == CURRENT_SCHEMA_VERSION:
        return episode_data  # Already current

    # Migration path for different versions
    if version.parse(data_version) < version.parse("1.0.0"):
        episode_data = _migrate_to_1_0_0(episode_data)

    # Future migrations would go here
    # if version.parse(data_version) < version.parse("1.1.0"):
    #     episode_data = _migrate_to_1_1_0(episode_data)

    episode_data["schema_version"] = CURRENT_SCHEMA_VERSION
    return episode_data


def _migrate_to_1_0_0(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Migration to schema version 1.0.0
    - Adds schema_version field
    - Ensures strict field validation
    """
    logger.info("Migrating episode data to schema 1.0.0")

    # Add schema_version if missing
    if "schema_version" not in data:
        data["schema_version"] = "1.0.0"

    # Ensure all required fields exist with defaults
    if "meta" not in data:
        data["meta"] = {}

    # Clean up any deprecated fields that would break strict mode
    deprecated_fields = [
        "deprecated_field_example"
    ]  # Add actual deprecated fields here
    for field in deprecated_fields:
        if field in data:
            logger.warning(f"Removing deprecated field: {field}")
            del data[field]

    return data


def validate_schema_compatibility(episodes: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Validate schema compatibility across episode list

    Returns:
        Compatibility report with version distribution and issues
    """
    version_counts = {}
    issues = []

    for i, episode in enumerate(episodes):
        ep_version = episode.get("schema_version", "1.0.0")
        version_counts[ep_version] = version_counts.get(ep_version, 0) + 1

        # Check for potential compatibility issues
        if version.parse(ep_version) > version.parse(CURRENT_SCHEMA_VERSION):
            issues.append(
                {
                    "episode_index": i,
                    "issue": "future_version",
                    "version": ep_version,
                    "message": f"Episode has newer schema version {ep_version} > {CURRENT_SCHEMA_VERSION}",
                }
            )

    return {
        "current_version": CURRENT_SCHEMA_VERSION,
        "version_distribution": version_counts,
        "total_episodes": len(episodes),
        "issues": issues,
        "compatibility_ok": len(issues) == 0,
    }


def create_schema_manifest() -> Dict[str, Any]:
    """
    Create schema manifest with version and field information
    """
    from services.rl.pipelines.dataset_schemas import Episode

    # Extract field information from Pydantic model
    fields_info = {}
    for field_name, field_info in Episode.model_fields.items():
        fields_info[field_name] = {
            "type": str(field_info.annotation),
            "required": field_info.is_required(),
            "default": (
                str(field_info.default) if field_info.default is not None else None
            ),
            "description": field_info.description,
        }

    return {
        "schema_version": CURRENT_SCHEMA_VERSION,
        "model_name": "Episode",
        "fields": fields_info,
        "strict_mode": True,
        "migration_supported": True,
        "created_at": "2025-09-07T00:00:00Z",
    }


if __name__ == "__main__":
    # Generate schema manifest for documentation
    manifest = create_schema_manifest()
    print(json.dumps(manifest, indent=2))
