# services/rl/online/tool_thompson.py
# Thompson Sampling per intent→tool, med kontinuerlig reward ∈ [0,1].
from __future__ import annotations
import json
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Dict, Optional
import random


def clamp01(x: float) -> float:
    return max(0.0, min(1.0, float(x)))


@dataclass
class BetaState:
    a: float = 1.0
    b: float = 1.0
    pulls: int = 0
    reward_sum: float = 0.0

    def sample(self) -> float:
        # enkel TS via python.random.betavariate
        return random.betavariate(self.a, self.b)

    def update(self, r: float) -> None:
        r = clamp01(r)
        # "continuous Bernoulli" approx: lägg reward i a, (1-reward) i b
        self.a += r
        self.b += (1.0 - r)
        self.pulls += 1
        self.reward_sum += r


@dataclass
class ToolPolicy:
    tools: Dict[str, BetaState]  # tool_name -> beta
    def to_json(self) -> Dict:
        return {"tools": {k: asdict(v) for k, v in self.tools.items()}}
    @staticmethod
    def from_json(d: Dict) -> "ToolPolicy":
        return ToolPolicy(tools={k: BetaState(**v) for k, v in d["tools"].items()})


class ThompsonToolSelector:
    def __init__(self):
        # intent -> ToolPolicy
        self.policies: Dict[str, ToolPolicy] = {}

    # ---------- Persistence ----------
    def save(self, path: str | Path) -> None:
        p = Path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        data = {intent: pol.to_json() for intent, pol in self.policies.items()}
        p.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

    @staticmethod
    def load(path: str | Path) -> "ThompsonToolSelector":
        p = Path(path)
        obj = ThompsonToolSelector()
        if not p.exists():
            return obj
        data = json.loads(p.read_text(encoding="utf-8"))
        obj.policies = {intent: ToolPolicy.from_json(pol) for intent, pol in data.items()}
        return obj

    # ---------- Core ----------
    def ensure_tools(self, intent: str, tool_names: Optional[list[str]]) -> None:
        if intent not in self.policies:
            tools = tool_names or []
            self.policies[intent] = ToolPolicy(tools={t: BetaState() for t in tools})

    def add_tool_if_missing(self, intent: str, tool_name: str) -> None:
        self.ensure_tools(intent, [])
        if tool_name not in self.policies[intent].tools:
            self.policies[intent].tools[tool_name] = BetaState()

    def choose(self, intent: str) -> Optional[str]:
        pol = self.policies.get(intent)
        if not pol or not pol.tools:
            return None
        samples = {t: st.sample() for t, st in pol.tools.items()}
        return max(samples.items(), key=lambda kv: kv[1])[0]

    def update(self, intent: str, tool_name: str, reward: float) -> None:
        reward = clamp01(reward)
        self.add_tool_if_missing(intent, tool_name)
        self.policies[intent].tools[tool_name].update(reward)

    # ---------- Hook mot episod ----------
    def update_from_episode(self, ep: Dict) -> None:
        state = ep.get("state") or {}
        action = ep.get("action") or {}
        intent = str(state.get("intent") or "unknown")
        tool = str(action.get("tool_name") or "unknown")
        r = (ep.get("reward_components") or {}).get("total")
        reward = 0.0 if r is None else float(r)
        self.update(intent, tool, reward)