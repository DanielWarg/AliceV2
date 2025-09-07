#!/usr/bin/env python3
"""
Bandit state rotation and backup system
Roterar snapshots varje 15 min, behåller 24h history
"""

import json
import os
import shutil
import time
from pathlib import Path
from typing import Dict, List

import structlog

logger = structlog.get_logger()

# Configuration
ROTATION_INTERVAL_MINUTES = int(os.getenv("RL_ROTATION_INTERVAL_MINUTES", "15"))
RETENTION_HOURS = int(os.getenv("RL_RETENTION_HOURS", "24"))
SNAPSHOTS_DIR = Path(os.getenv("RL_SNAPSHOTS_DIR", "data/rl/snapshots"))
STATE_DIR = Path(os.getenv("RL_STATE_DIR", "data/rl/v1/state"))


class BanditRotator:
    """Handles bandit state snapshots and rotation"""

    def __init__(self):
        self.snapshots_dir = SNAPSHOTS_DIR
        self.state_dir = STATE_DIR
        self.rotation_interval = ROTATION_INTERVAL_MINUTES * 60  # Convert to seconds
        self.retention_period = RETENTION_HOURS * 3600  # Convert to seconds

        # Create directories
        self.snapshots_dir.mkdir(parents=True, exist_ok=True)
        self.state_dir.mkdir(parents=True, exist_ok=True)

    def should_rotate(self) -> bool:
        """Check if it's time to rotate snapshots"""
        last_snapshot = self._get_latest_snapshot()
        if not last_snapshot:
            return True

        # Extract timestamp from filename
        try:
            timestamp_str = last_snapshot.stem.split("_")[-1]
            last_time = int(timestamp_str)
            current_time = int(time.time())

            return (current_time - last_time) >= self.rotation_interval
        except (ValueError, IndexError):
            return True

    def create_snapshot(self) -> Dict[str, str]:
        """Create a new snapshot of current bandit state"""
        timestamp = int(time.time())
        snapshot_name = f"bandit_snapshot_{timestamp}"
        snapshot_path = self.snapshots_dir / snapshot_name

        snapshot_info = {
            "timestamp": timestamp,
            "snapshot_path": str(snapshot_path),
            "files_copied": [],
            "size_bytes": 0,
        }

        try:
            # Create snapshot directory
            snapshot_path.mkdir(exist_ok=True)

            # Copy state files
            for state_file in self.state_dir.glob("*.json"):
                dest_file = snapshot_path / state_file.name
                shutil.copy2(state_file, dest_file)

                snapshot_info["files_copied"].append(state_file.name)
                snapshot_info["size_bytes"] += dest_file.stat().st_size

            # Create snapshot metadata
            metadata = {
                "created_at": timestamp,
                "created_iso": time.strftime(
                    "%Y-%m-%dT%H:%M:%SZ", time.gmtime(timestamp)
                ),
                "files": snapshot_info["files_copied"],
                "total_size_bytes": snapshot_info["size_bytes"],
                "rotation_interval_minutes": ROTATION_INTERVAL_MINUTES,
                "retention_hours": RETENTION_HOURS,
            }

            # Write metadata
            with open(snapshot_path / "metadata.json", "w") as f:
                json.dump(metadata, f, indent=2)

            logger.info(
                "bandit_snapshot_created",
                snapshot_name=snapshot_name,
                files=len(snapshot_info["files_copied"]),
                size_mb=round(snapshot_info["size_bytes"] / 1024 / 1024, 2),
            )

            return snapshot_info

        except Exception as e:
            logger.error(
                "bandit_snapshot_failed", error=str(e), snapshot_name=snapshot_name
            )

            # Cleanup failed snapshot
            if snapshot_path.exists():
                shutil.rmtree(snapshot_path, ignore_errors=True)

            raise

    def cleanup_old_snapshots(self) -> Dict[str, int]:
        """Remove snapshots older than retention period"""
        current_time = int(time.time())
        cutoff_time = current_time - self.retention_period

        deleted_count = 0
        deleted_size = 0
        errors = 0

        for snapshot_dir in self.snapshots_dir.glob("bandit_snapshot_*"):
            if not snapshot_dir.is_dir():
                continue

            try:
                # Extract timestamp from directory name
                timestamp_str = snapshot_dir.name.split("_")[-1]
                snapshot_time = int(timestamp_str)

                if snapshot_time < cutoff_time:
                    # Calculate size before deletion
                    size = sum(
                        f.stat().st_size for f in snapshot_dir.rglob("*") if f.is_file()
                    )

                    # Delete snapshot
                    shutil.rmtree(snapshot_dir)

                    deleted_count += 1
                    deleted_size += size

                    logger.debug(
                        "bandit_snapshot_deleted",
                        snapshot_name=snapshot_dir.name,
                        age_hours=round((current_time - snapshot_time) / 3600, 1),
                    )

            except (ValueError, OSError) as e:
                logger.warning(
                    "bandit_snapshot_cleanup_error",
                    snapshot_name=snapshot_dir.name,
                    error=str(e),
                )
                errors += 1

        cleanup_info = {
            "deleted_count": deleted_count,
            "deleted_size_mb": round(deleted_size / 1024 / 1024, 2),
            "errors": errors,
            "retention_hours": RETENTION_HOURS,
        }

        if deleted_count > 0:
            logger.info("bandit_snapshots_cleaned", **cleanup_info)

        return cleanup_info

    def list_snapshots(self) -> List[Dict[str, any]]:
        """List all available snapshots"""
        snapshots = []

        for snapshot_dir in sorted(self.snapshots_dir.glob("bandit_snapshot_*")):
            if not snapshot_dir.is_dir():
                continue

            try:
                # Load metadata if available
                metadata_file = snapshot_dir / "metadata.json"
                if metadata_file.exists():
                    with open(metadata_file) as f:
                        metadata = json.load(f)
                else:
                    # Fallback to basic info
                    timestamp_str = snapshot_dir.name.split("_")[-1]
                    timestamp = int(timestamp_str)
                    metadata = {
                        "created_at": timestamp,
                        "created_iso": time.strftime(
                            "%Y-%m-%dT%H:%M:%SZ", time.gmtime(timestamp)
                        ),
                        "files": [],
                        "total_size_bytes": 0,
                    }

                # Add path info
                metadata["snapshot_path"] = str(snapshot_dir)
                metadata["age_minutes"] = round(
                    (time.time() - metadata["created_at"]) / 60, 1
                )

                snapshots.append(metadata)

            except (ValueError, json.JSONDecodeError) as e:
                logger.warning(
                    "bandit_snapshot_list_error",
                    snapshot_name=snapshot_dir.name,
                    error=str(e),
                )

        return snapshots

    def restore_snapshot(self, snapshot_name: str) -> Dict[str, any]:
        """Restore bandit state from a snapshot"""
        snapshot_path = self.snapshots_dir / snapshot_name

        if not snapshot_path.exists():
            raise FileNotFoundError(f"Snapshot not found: {snapshot_name}")

        restore_info = {
            "snapshot_name": snapshot_name,
            "files_restored": [],
            "restore_time": time.time(),
        }

        try:
            # Backup current state first
            backup_snapshot = self.create_snapshot()

            # Restore files from snapshot
            for state_file in snapshot_path.glob("*.json"):
                if state_file.name == "metadata.json":
                    continue

                dest_file = self.state_dir / state_file.name
                shutil.copy2(state_file, dest_file)
                restore_info["files_restored"].append(state_file.name)

            logger.info(
                "bandit_snapshot_restored",
                snapshot_name=snapshot_name,
                files=len(restore_info["files_restored"]),
                backup_created=backup_snapshot["snapshot_path"],
            )

            return restore_info

        except Exception as e:
            logger.error(
                "bandit_snapshot_restore_failed",
                snapshot_name=snapshot_name,
                error=str(e),
            )
            raise

    def _get_latest_snapshot(self) -> Path:
        """Get the most recent snapshot directory"""
        snapshots = list(self.snapshots_dir.glob("bandit_snapshot_*"))
        if not snapshots:
            return None

        # Sort by timestamp in name
        def extract_timestamp(path):
            try:
                return int(path.name.split("_")[-1])
            except (ValueError, IndexError):
                return 0

        return max(snapshots, key=extract_timestamp)

    def auto_rotate(self) -> Dict[str, any]:
        """Perform automatic rotation if needed"""
        result = {
            "rotated": False,
            "snapshot_created": None,
            "cleanup_info": None,
            "timestamp": time.time(),
        }

        if self.should_rotate():
            try:
                # Create new snapshot
                snapshot_info = self.create_snapshot()
                result["rotated"] = True
                result["snapshot_created"] = snapshot_info

                # Cleanup old snapshots
                cleanup_info = self.cleanup_old_snapshots()
                result["cleanup_info"] = cleanup_info

            except Exception as e:
                logger.error("auto_rotation_failed", error=str(e))
                result["error"] = str(e)

        return result


def main():
    """CLI entry point for manual rotation operations"""
    import argparse

    parser = argparse.ArgumentParser(description="Bandit snapshot rotation")
    parser.add_argument(
        "--action",
        choices=["rotate", "list", "restore", "cleanup"],
        default="rotate",
        help="Action to perform",
    )
    parser.add_argument("--snapshot", help="Snapshot name for restore action")
    parser.add_argument(
        "--force", action="store_true", help="Force rotation even if not due"
    )

    args = parser.parse_args()

    rotator = BanditRotator()

    if args.action == "rotate":
        if args.force or rotator.should_rotate():
            result = rotator.auto_rotate()
            print(json.dumps(result, indent=2))
        else:
            print("Rotation not needed")

    elif args.action == "list":
        snapshots = rotator.list_snapshots()
        print(json.dumps(snapshots, indent=2))

    elif args.action == "restore":
        if not args.snapshot:
            print("Error: --snapshot required for restore action")
            return 1
        result = rotator.restore_snapshot(args.snapshot)
        print(json.dumps(result, indent=2))

    elif args.action == "cleanup":
        result = rotator.cleanup_old_snapshots()
        print(json.dumps(result, indent=2))


if __name__ == "__main__":
    exit(main())
