# services/orchestrator/src/rl_policy.py
from __future__ import annotations

import os
import threading
import time
from pathlib import Path

from services.rl.online.routing_linucb import LinUCBRouter, features_from_episode
from services.rl.online.tool_thompson import ThompsonToolSelector

LINUCB_PATH = os.getenv("RL_LINUCB_PATH", "services/rl/weights/bandits/linucb.json")
THOMPSON_PATH = os.getenv(
    "RL_THOMPSON_PATH", "services/rl/weights/bandits/thompson.json"
)
CANARY_SHARE = float(os.getenv("CANARY_SHARE", "0.05"))  # 5% default
SNAPSHOT_INTERVAL_S = int(os.getenv("RL_SNAPSHOT_INTERVAL_S", "60"))
SNAPSHOT_MIN_UPDATES = int(os.getenv("RL_SNAPSHOT_MIN_UPDATES", "100"))


class RLPolicy:
    def __init__(self):
        self.linucb = LinUCBRouter.load(LINUCB_PATH)
        self.thomp = ThompsonToolSelector.load(THOMPSON_PATH)
        self._updates_since_snapshot = 0
        self._last_snapshot_ts = time.time()
        self._lock = threading.Lock()

    def choose_route(self, episode_stub: dict, baseline_hint: str) -> str:
        """
        Canary: endast CANARY_SHARE av trafiken får använda banditvalet.
        Övriga kör baseline (din befintliga router/intent-guard).
        """
        import random

        if random.random() >= CANARY_SHARE:
            return baseline_hint  # 95% baseline (justera via env)
        x = features_from_episode(episode_stub)
        try:
            return self.linucb.choose_arm(x)
        except Exception:
            return baseline_hint

    def choose_tool(self, intent: str, baseline_tool: str | None) -> str:
        import random

        if random.random() >= CANARY_SHARE:
            return baseline_tool or "none"
        t = self.thomp.choose(intent)
        return t or (baseline_tool or "none")

    def update_from_episode(self, episode: dict) -> None:
        """
        Kallas efter turn när reward_components.total är beräknad (T3).
        Threadsäkert + periodiska snapshots.
        """
        with self._lock:
            try:
                self.linucb.update_from_episode(episode)
                self.thomp.update_from_episode(episode)
                self._updates_since_snapshot += 1
            except Exception:
                return

            now = time.time()
            if (
                self._updates_since_snapshot >= SNAPSHOT_MIN_UPDATES
                and (now - self._last_snapshot_ts) >= SNAPSHOT_INTERVAL_S
            ):
                try:
                    Path(LINUCB_PATH).parent.mkdir(parents=True, exist_ok=True)
                    self.linucb.save(LINUCB_PATH)
                    Path(THOMPSON_PATH).parent.mkdir(parents=True, exist_ok=True)
                    self.thomp.save(THOMPSON_PATH)
                    self._updates_since_snapshot = 0
                    self._last_snapshot_ts = now
                except Exception:
                    pass
