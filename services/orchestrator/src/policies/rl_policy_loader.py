"""
RL Policy loader for Alice orchestrator runtime.

Loads and manages RL policies (routing, tools, cache) with hot-reloading
and graceful fallback to existing policies.
"""

from __future__ import annotations

import json
import pathlib
import threading
from datetime import datetime
from typing import Any, Callable, Dict, Optional

import structlog

logger = structlog.get_logger(__name__)


class RLPolicyLoader:
    """
    Manages loading and hot-reloading of RL policies.

    Monitors policy files for changes and provides thread-safe access
    to loaded policies with fallback to defaults.
    """

    def __init__(
        self,
        policy_dir: str = "src/policies/live",
        check_interval: float = 60.0,
        enable_hot_reload: bool = True,
    ):
        """
        Initialize policy loader.

        Args:
            policy_dir: Directory containing policy files
            check_interval: File check interval in seconds
            enable_hot_reload: Whether to enable hot-reloading
        """
        self.policy_dir = pathlib.Path(policy_dir)
        self.check_interval = check_interval
        self.enable_hot_reload = enable_hot_reload

        # Thread safety
        self._lock = threading.RLock()

        # Loaded policies
        self._routing_policy: Optional[Dict[str, Any]] = None
        self._tool_policy: Optional[Dict[str, Any]] = None
        self._cache_policy: Optional[Dict[str, Any]] = None

        # File modification times for change detection
        self._file_mtimes: Dict[str, float] = {}

        # Hot-reload thread
        self._reload_thread: Optional[threading.Thread] = None
        self._stop_reload = threading.Event()

        # Policy change callbacks
        self._change_callbacks: list[Callable[[str, Dict[str, Any]], None]] = []

        logger.info(
            "RL Policy loader initialized",
            policy_dir=str(self.policy_dir),
            hot_reload=enable_hot_reload,
        )

        # Initial load
        self.load_all_policies()

        # Start hot-reload thread
        if enable_hot_reload:
            self.start_hot_reload()

    def add_change_callback(
        self, callback: Callable[[str, Dict[str, Any]], None]
    ) -> None:
        """Add callback to be called when policies change."""
        with self._lock:
            self._change_callbacks.append(callback)

    def load_all_policies(self) -> bool:
        """
        Load all available policies from disk.

        Returns:
            True if at least one policy was loaded successfully
        """
        with self._lock:
            success_count = 0

            # Try to load routing policy
            if self._load_routing_policy():
                success_count += 1

            # Try to load tool policy
            if self._load_tool_policy():
                success_count += 1

            # Try to load cache policy
            if self._load_cache_policy():
                success_count += 1

            logger.info(
                "Policy loading complete",
                policies_loaded=success_count,
                total_attempted=3,
            )

            return success_count > 0

    def _load_routing_policy(self) -> bool:
        """Load routing policy from active package."""
        try:
            package_path = self.policy_dir / "active_policy_pack.json"

            if not package_path.exists():
                logger.debug("No active policy package found")
                return False

            # Check modification time
            mtime = package_path.stat().st_mtime
            if self._file_mtimes.get("routing") == mtime and self._routing_policy:
                return True  # No change

            with open(package_path, "r", encoding="utf-8") as f:
                package = json.load(f)

            if "routing" in package.get("policies", {}):
                self._routing_policy = package["policies"]["routing"]
                self._file_mtimes["routing"] = mtime

                logger.info(
                    "Loaded routing policy", version=package.get("version", "unknown")
                )

                # Notify callbacks
                for callback in self._change_callbacks:
                    try:
                        callback("routing", self._routing_policy)
                    except Exception as e:
                        logger.error(
                            "Callback error", callback=str(callback), error=str(e)
                        )

                return True

        except Exception as e:
            logger.error("Failed to load routing policy", error=str(e))

        return False

    def _load_tool_policy(self) -> bool:
        """Load tool policy from active package."""
        try:
            package_path = self.policy_dir / "active_policy_pack.json"

            if not package_path.exists():
                return False

            mtime = package_path.stat().st_mtime
            if self._file_mtimes.get("tools") == mtime and self._tool_policy:
                return True

            with open(package_path, "r", encoding="utf-8") as f:
                package = json.load(f)

            if "tools" in package.get("policies", {}):
                self._tool_policy = package["policies"]["tools"]
                self._file_mtimes["tools"] = mtime

                logger.info(
                    "Loaded tool policy", version=package.get("version", "unknown")
                )

                for callback in self._change_callbacks:
                    try:
                        callback("tools", self._tool_policy)
                    except Exception as e:
                        logger.error("Callback error", error=str(e))

                return True

        except Exception as e:
            logger.error("Failed to load tool policy", error=str(e))

        return False

    def _load_cache_policy(self) -> bool:
        """Load cache policy from active package."""
        try:
            package_path = self.policy_dir / "active_policy_pack.json"

            if not package_path.exists():
                return False

            mtime = package_path.stat().st_mtime
            if self._file_mtimes.get("cache") == mtime and self._cache_policy:
                return True

            with open(package_path, "r", encoding="utf-8") as f:
                package = json.load(f)

            if "cache" in package.get("policies", {}):
                self._cache_policy = package["policies"]["cache"]
                self._file_mtimes["cache"] = mtime

                logger.info(
                    "Loaded cache policy", version=package.get("version", "unknown")
                )

                for callback in self._change_callbacks:
                    try:
                        callback("cache", self._cache_policy)
                    except Exception as e:
                        logger.error("Callback error", error=str(e))

                return True

        except Exception as e:
            logger.error("Failed to load cache policy", error=str(e))

        return False

    def get_routing_policy(self) -> Optional[Dict[str, Any]]:
        """Get current routing policy."""
        with self._lock:
            return self._routing_policy.copy() if self._routing_policy else None

    def get_tool_policy(self) -> Optional[Dict[str, Any]]:
        """Get current tool policy."""
        with self._lock:
            return self._tool_policy.copy() if self._tool_policy else None

    def get_cache_policy(self) -> Optional[Dict[str, Any]]:
        """Get current cache policy."""
        with self._lock:
            return self._cache_policy.copy() if self._cache_policy else None

    def start_hot_reload(self) -> None:
        """Start hot-reload monitoring thread."""
        if self._reload_thread and self._reload_thread.is_alive():
            logger.warning("Hot-reload thread already running")
            return

        self._stop_reload.clear()
        self._reload_thread = threading.Thread(
            target=self._hot_reload_worker, daemon=True, name="rl-policy-reloader"
        )
        self._reload_thread.start()

        logger.info("Hot-reload monitoring started", check_interval=self.check_interval)

    def stop_hot_reload(self) -> None:
        """Stop hot-reload monitoring thread."""
        if self._reload_thread and self._reload_thread.is_alive():
            self._stop_reload.set()
            self._reload_thread.join(timeout=5.0)

            if self._reload_thread.is_alive():
                logger.warning("Hot-reload thread did not stop gracefully")

        logger.info("Hot-reload monitoring stopped")

    def _hot_reload_worker(self) -> None:
        """Worker thread for hot-reloading policies."""
        logger.info("Hot-reload worker started")

        while not self._stop_reload.wait(self.check_interval):
            try:
                self.load_all_policies()
            except Exception as e:
                logger.error("Hot-reload error", error=str(e))

        logger.info("Hot-reload worker stopped")

    def get_status(self) -> Dict[str, Any]:
        """Get loader status and policy information."""
        with self._lock:
            status = {
                "policy_dir": str(self.policy_dir),
                "hot_reload_enabled": self.enable_hot_reload,
                "hot_reload_active": self._reload_thread
                and self._reload_thread.is_alive(),
                "policies_loaded": {
                    "routing": self._routing_policy is not None,
                    "tools": self._tool_policy is not None,
                    "cache": self._cache_policy is not None,
                },
                "last_check": datetime.now().isoformat(),
                "file_modification_times": self._file_mtimes.copy(),
                "callbacks_registered": len(self._change_callbacks),
            }

            # Add policy versions if available
            if self._routing_policy:
                status["routing_version"] = self._routing_policy.get(
                    "routing_policy", {}
                ).get("version", "unknown")

            if self._tool_policy:
                status["tool_version"] = self._tool_policy.get("tool_policy", {}).get(
                    "version", "unknown"
                )

            if self._cache_policy:
                status["cache_version"] = self._cache_policy.get("version", "unknown")

            return status

    def __del__(self):
        """Cleanup when loader is destroyed."""
        try:
            self.stop_hot_reload()
        except:
            pass


# Global policy loader instance
_policy_loader: Optional[RLPolicyLoader] = None


def get_policy_loader() -> RLPolicyLoader:
    """Get or create global policy loader instance."""
    global _policy_loader

    if _policy_loader is None:
        _policy_loader = RLPolicyLoader()

    return _policy_loader


def initialize_policy_loader(
    policy_dir: str = "src/policies/live",
    check_interval: float = 60.0,
    enable_hot_reload: bool = True,
) -> RLPolicyLoader:
    """Initialize global policy loader with custom settings."""
    global _policy_loader

    if _policy_loader:
        _policy_loader.stop_hot_reload()

    _policy_loader = RLPolicyLoader(
        policy_dir=policy_dir,
        check_interval=check_interval,
        enable_hot_reload=enable_hot_reload,
    )

    return _policy_loader
