# services/rl/online/routing_linucb.py
# LinUCB-router som lär online av φ-belöningen och kan persistera state.
from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np

DEFAULT_ARMS = ["micro", "planner", "deep"]  # justera om du har andra routes
DEFAULT_ALPHA = 0.8  # utforskningsvikt; kan tunas via env
EPS = 1e-8


def _num(x, default=0.0) -> float:
    try:
        if x is None:
            return float(default)
        return float(x)
    except Exception:
        return float(default)


def _bool01(x) -> float:
    return 1.0 if bool(x) else 0.0


def features_from_episode(ep: Dict) -> np.ndarray:
    """
    Bygg ett litet, stabilt feature-paket av episoden.
    Håll deterministiskt & utan externa beroenden.
    """
    f = ep.get("features", {}) or {}
    meta = ep.get("metadata", {}) or {}
    state = ep.get("state", {}) or {}

    # Grunddrag
    len_chars = _num(f.get("len_chars", len((state.get("text") or ""))))
    has_q = _bool01(f.get("has_question", False) or ("?" in (state.get("text") or "")))

    # Guardian- & cache-signal (om finns)
    guardian_state = (meta.get("guardian_state") or "NORMAL").upper()
    g_norm = (
        1.0
        if guardian_state == "NORMAL"
        else 0.5 if guardian_state == "BROWNOUT" else 0.0
    )

    cache_hit = _bool01(meta.get("cache_hit", f.get("cache_hit", False)))
    rag_hit = _bool01(meta.get("rag_hit", f.get("rag_hit", False)))

    # Normaliseringar (håll dem stabila & kapsla förändringar)
    len_scaled = min(len_chars / 500.0, 1.0)

    x = np.array(
        [
            1.0,  # bias
            len_scaled,
            has_q,
            g_norm,
            cache_hit,
            rag_hit,
        ],
        dtype=np.float64,
    )
    return x


@dataclass
class ArmState:
    name: str
    A: List[List[float]]  # dxd (design-matris)
    b: List[float]  # dx1
    pulls: int = 0
    reward_sum: float = 0.0

    @staticmethod
    def init(name: str, d: int) -> "ArmState":
        return ArmState(
            name=name,
            A=np.eye(d).tolist(),
            b=np.zeros(d).tolist(),
            pulls=0,
            reward_sum=0.0,
        )

    def np_mats(self) -> Tuple[np.ndarray, np.ndarray]:
        return np.array(self.A, dtype=np.float64), np.array(self.b, dtype=np.float64)

    def set_np(self, A: np.ndarray, b: np.ndarray) -> None:
        self.A = A.tolist()
        self.b = b.tolist()


@dataclass
class LinUCBState:
    dim: int
    alpha: float
    arms: Dict[str, ArmState]

    @staticmethod
    def new(arm_names: List[str], dim: int, alpha: float) -> "LinUCBState":
        return LinUCBState(
            dim=dim,
            alpha=alpha,
            arms={a: ArmState.init(a, dim) for a in arm_names},
        )

    def to_json(self) -> Dict:
        return {
            "dim": self.dim,
            "alpha": self.alpha,
            "arms": {k: asdict(v) for k, v in self.arms.items()},
        }

    @staticmethod
    def from_json(d: Dict) -> "LinUCBState":
        arms = {k: ArmState(**v) for k, v in d["arms"].items()}
        return LinUCBState(dim=d["dim"], alpha=d["alpha"], arms=arms)


class LinUCBRouter:
    def __init__(
        self,
        arm_names: Optional[List[str]] = None,
        alpha: float = DEFAULT_ALPHA,
        dim: int = 6,
    ):
        arm_names = arm_names or DEFAULT_ARMS
        self.state = LinUCBState.new(arm_names, dim=dim, alpha=alpha)

    # ---------- Persistence ----------
    def save(self, path: str | Path) -> None:
        p = Path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        with p.open("w", encoding="utf-8") as f:
            json.dump(self.state.to_json(), f, ensure_ascii=False, indent=2)

    @staticmethod
    def load(path: str | Path) -> "LinUCBRouter":
        p = Path(path)
        if not p.exists():
            return LinUCBRouter()
        with p.open("r", encoding="utf-8") as f:
            data = json.load(f)
        obj = LinUCBRouter(
            dim=data["dim"], alpha=data["alpha"], arm_names=list(data["arms"].keys())
        )
        obj.state = LinUCBState.from_json(data)
        return obj

    # ---------- Core LinUCB ----------
    def _theta(self, arm: ArmState) -> np.ndarray:
        A, b = arm.np_mats()
        try:
            invA = np.linalg.inv(A)
        except np.linalg.LinAlgError:
            invA = np.linalg.pinv(A)
        return invA @ b

    def _ucb(self, arm: ArmState, x: np.ndarray) -> float:
        A, b = arm.np_mats()
        try:
            invA = np.linalg.inv(A)
        except np.linalg.LinAlgError:
            invA = np.linalg.pinv(A)
        theta = invA @ b
        mean = float(theta @ x)
        var = float(np.sqrt(x.T @ invA @ x))  # osäkerhet
        return mean + self.state.alpha * var

    def choose_arm(self, x: np.ndarray) -> str:
        scores = {name: self._ucb(arm, x) for name, arm in self.state.arms.items()}
        return max(scores.items(), key=lambda kv: kv[1])[0]

    def update(self, chosen: str, x: np.ndarray, reward: float) -> None:
        reward = float(max(0.0, min(1.0, reward)))
        arm = self.state.arms[chosen]
        A, b = arm.np_mats()
        x = x.reshape(-1, 1)
        A = A + (x @ x.T)
        b = b + (reward * x).flatten()
        arm.set_np(A, b)
        arm.pulls += 1
        arm.reward_sum += reward

    # ---------- Hook mot episod ----------
    def update_from_episode(self, ep: Dict) -> None:
        # 1) bygg features
        x = features_from_episode(ep)
        # 2) hämta vald route (policy action) från episoden
        chosen = (ep.get("action") or {}).get("route") or self.choose_arm(x)
        # 3) ta φ-belöning (total) om finns, annars 0
        r = (ep.get("reward_components") or {}).get("total")
        reward = 0.0 if r is None else float(r)
        # 4) uppdatera
        self.update(chosen, x, reward)
