#!/usr/bin/env python3
"""
T8 – Route Controller
- Feature-flaggor:
  * T8_ENABLED (default: false)
  * T8_ONLINE_ADAPTATION (default: false)
- Väljer route "baseline" eller "adapter" via:
  * Canary fast andel (PREFS_CANARY_SHARE) när ONLINE_ADAPTATION=false
  * Thompson Sampling (BetaBandit) när ONLINE_ADAPTATION=true
- Säkerhetsgrind stoppar adapter-route om metrics bryter SLO.
- Lagrar banditstate i data/ops/bandit_state.json (enkel best-effort).
"""

import json
import os
import random
from pathlib import Path

from services.rl.online.bandit_router import BetaBandit
from services.rl.online.safety_gate import allow_online_adaptation

STATE_PATH = "data/ops/bandit_state.json"


def _load_state():
    if not Path(STATE_PATH).exists():
        return {"a": 1.0, "b": 1.0}
    try:
        return json.loads(open(STATE_PATH, "r", encoding="utf-8").read())
    except Exception:
        return {"a": 1.0, "b": 1.0}


def _save_state(st):
    Path(STATE_PATH).parent.mkdir(parents=True, exist_ok=True)
    with open(STATE_PATH, "w", encoding="utf-8") as f:
        json.dump(st, f, ensure_ascii=False, indent=2)


def want_adapter_route(runtime_metrics: dict) -> bool:
    # feature flags
    if os.getenv("T8_ENABLED", "false").lower() != "true":
        return False
    # hard safety gate
    if not allow_online_adaptation(
        {
            "verifier_fail": runtime_metrics.get("verifier_fail", 1.0),
            "policy_breach": runtime_metrics.get("policy_breach", 0),
            "p95_delta": runtime_metrics.get("p95_delta", 0.0),
        }
    ):
        return False

    # online adaptation?
    if os.getenv("T8_ONLINE_ADAPTATION", "false").lower() == "true":
        st = _load_state()
        bandit = BetaBandit(a=st.get("a", 1.0), b=st.get("b", 1.0))
        sample = bandit.sample()
        thresh = 0.5  # indifferent priors
        choose_adapter = sample >= thresh
        # persist sample-threshold for transparency (optional)
        _save_state(
            {"a": st.get("a", 1.0), "b": st.get("b", 1.0), "last_sample": sample}
        )
        return choose_adapter

    # else: canary share
    share = float(os.getenv("PREFS_CANARY_SHARE", "0.05"))
    return random.random() < share


def report_outcome(adapter_used: bool, reward: float):
    """
    Uppdatera bandit endast om ONLINE_ADAPTATION=true.
    reward ∈ {0.0, 1.0} (t.ex. verifier_ok &/eller human_like win)
    """
    if os.getenv("T8_ONLINE_ADAPTATION", "false").lower() != "true":
        return
    st = _load_state()
    a, b = st.get("a", 1.0), st.get("b", 1.0)
    if adapter_used:
        a += reward
        b += 1.0 - reward
    else:
        # baseline uppdateras separat om man kör två-armed bandit; här håller vi enkel
        pass
    _save_state({"a": a, "b": b})
