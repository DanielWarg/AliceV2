# services/rl/persistence/bandit_store.py
"""
JSON-baserad persistence för bandits med fil-lås säkerhet
"""

from __future__ import annotations

import json
import os
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Dict, Optional

import numpy as np

# State directory
STATE_DIR = Path(os.getenv("RL_STATE_DIR", "services/rl/state"))


def get_paths() -> Dict[str, Path]:
    """Get paths for bandit state files"""
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    return {
        "linucb": STATE_DIR / "linucb.json",
        "thompson": STATE_DIR / "thompson.json",
    }


@dataclass
class LinUCBArm:
    """State for one LinUCB arm"""

    name: str
    A: list[list[float]]  # d x d matrix
    b: list[float]  # d vector
    pulls: int = 0
    reward_sum: float = 0.0


@dataclass
class LinUCBState:
    """Complete LinUCB state"""

    dim: int
    alpha: float
    arms: Dict[str, LinUCBArm]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "dim": self.dim,
            "alpha": self.alpha,
            "arms": {name: asdict(arm) for name, arm in self.arms.items()},
        }

    @staticmethod
    def from_dict(data: Dict[str, Any]) -> "LinUCBState":
        arms = {}
        for name, arm_data in data["arms"].items():
            arms[name] = LinUCBArm(**arm_data)
        return LinUCBState(dim=data["dim"], alpha=data["alpha"], arms=arms)


@dataclass
class BetaArm:
    """Beta distribution for Thompson sampling"""

    alpha: float = 1.0
    beta: float = 1.0
    pulls: int = 0
    reward_sum: float = 0.0


@dataclass
class ThompsonState:
    """Thompson sampling state per (intent, tool)"""

    policies: Dict[str, Dict[str, BetaArm]]  # intent -> tool -> BetaArm

    def to_dict(self) -> Dict[str, Any]:
        result = {}
        for intent, tools in self.policies.items():
            result[intent] = {tool: asdict(arm) for tool, arm in tools.items()}
        return {"policies": result}

    @staticmethod
    def from_dict(data: Dict[str, Any]) -> "ThompsonState":
        policies = {}
        for intent, tools_data in data.get("policies", {}).items():
            policies[intent] = {}
            for tool, arm_data in tools_data.items():
                policies[intent][tool] = BetaArm(**arm_data)
        return ThompsonState(policies=policies)


def _safe_file_operation(filepath: Path, operation: str, data: Any = None) -> Any:
    """Perform file operation with locking"""
    lock_path = filepath.with_suffix(filepath.suffix + ".lock")

    # Wait for lock with timeout
    max_wait = 5.0  # seconds
    start_time = time.time()

    while lock_path.exists():
        if time.time() - start_time > max_wait:
            # Force remove stale lock
            lock_path.unlink(missing_ok=True)
            break
        time.sleep(0.1)

    try:
        # Create lock
        with lock_path.open("w") as lock_file:
            lock_file.write(str(os.getpid()))

        if operation == "load":
            if not filepath.exists():
                return None
            with filepath.open("r", encoding="utf-8") as f:
                return json.load(f)

        elif operation == "save":
            with filepath.open("w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
                f.flush()
                os.fsync(f.fileno())
            return True

    finally:
        # Remove lock
        lock_path.unlink(missing_ok=True)


def load_linucb() -> Optional[LinUCBState]:
    """Load LinUCB state from disk"""
    paths = get_paths()
    data = _safe_file_operation(paths["linucb"], "load")

    if data is None:
        return None

    try:
        return LinUCBState.from_dict(data)
    except Exception as e:
        print(f"Error loading LinUCB state: {e}")
        return None


def save_linucb(state: LinUCBState) -> bool:
    """Save LinUCB state to disk"""
    paths = get_paths()
    try:
        return _safe_file_operation(paths["linucb"], "save", state.to_dict())
    except Exception as e:
        print(f"Error saving LinUCB state: {e}")
        return False


def load_thompson() -> Optional[ThompsonState]:
    """Load Thompson state from disk"""
    paths = get_paths()
    data = _safe_file_operation(paths["thompson"], "load")

    if data is None:
        return None

    try:
        return ThompsonState.from_dict(data)
    except Exception as e:
        print(f"Error loading Thompson state: {e}")
        return None


def save_thompson(state: ThompsonState) -> bool:
    """Save Thompson state to disk"""
    paths = get_paths()
    try:
        return _safe_file_operation(paths["thompson"], "save", state.to_dict())
    except Exception as e:
        print(f"Error saving Thompson state: {e}")
        return False


def init_empty_linucb(
    actions: list[str], dim: int = 6, alpha: float = 0.8
) -> LinUCBState:
    """Initialize empty LinUCB state"""
    arms = {}
    for action in actions:
        arms[action] = LinUCBArm(
            name=action, A=np.eye(dim).tolist(), b=np.zeros(dim).tolist()
        )

    return LinUCBState(dim=dim, alpha=alpha, arms=arms)


def init_empty_thompson() -> ThompsonState:
    """Initialize empty Thompson state"""
    return ThompsonState(policies={})


# Test persistence if run directly
if __name__ == "__main__":
    print("Testing bandit persistence...")

    # Test LinUCB
    actions = ["micro", "planner", "deep"]
    linucb = init_empty_linucb(actions)
    print(f"Saving LinUCB with {len(linucb.arms)} arms...")
    save_linucb(linucb)

    loaded = load_linucb()
    print(f"Loaded LinUCB with {len(loaded.arms) if loaded else 0} arms")

    # Test Thompson
    thompson = init_empty_thompson()
    print("Saving empty Thompson state...")
    save_thompson(thompson)

    loaded_t = load_thompson()
    print(f"Loaded Thompson with {len(loaded_t.policies) if loaded_t else 0} policies")

    print("Persistence test complete!")
