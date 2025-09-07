# services/rl/rewards/reward_shaping.py
from __future__ import annotations

import os
from typing import Any, Dict, Optional, Tuple

PHI = (1 + 5**0.5) / 2  # 1.6180339887...


def _env_float(name: str, default: float) -> float:
    try:
        return float(os.getenv(name, str(default)))
    except Exception:
        return default


# Standardiserade mål/skalor (kan överstyras via env vid behov)
DEFAULTS = {
    "TARGET_P95_MS": 900.0,  # planner-route p95 (justera per route)
    "TARGET_FAST_MS": 250.0,  # fast-route p95
    "ENERGY_BUDGET_WH": 0.05,  # energibudget per turn (exempel)
    "ALPHA": 2.0,  # exponent för vikttrappa (φ^α, φ^(α-1), ...)
    "LATENCY_MODE": "auto",  # "auto" väljer mål utifrån route_hint
}


def _latency_target_ms(features: Dict[str, Any]) -> float:
    # Auto-välj mål beroende på route_hint (fast/micro vs planner)
    mode = os.getenv("RL_LATENCY_MODE", DEFAULTS["LATENCY_MODE"]).lower()
    if mode == "fast":
        return _env_float("RL_TARGET_FAST_MS", DEFAULTS["TARGET_FAST_MS"])
    if mode == "planner":
        return _env_float("RL_TARGET_P95_MS", DEFAULTS["TARGET_P95_MS"])
    # auto
    hint = (features or {}).get("route_hint", "") or ""
    if str(hint).lower() in {"micro", "fast"}:
        return _env_float("RL_TARGET_FAST_MS", DEFAULTS["TARGET_FAST_MS"])
    return _env_float("RL_TARGET_P95_MS", DEFAULTS["TARGET_P95_MS"])


def _clip01(x: float) -> float:
    return max(0.0, min(1.0, x))


def _safe_bool_to_score(flag: Optional[bool]) -> Optional[float]:
    if flag is None:
        return None
    return 1.0 if flag else 0.0


def component_scores(
    *,
    tool_success: Optional[bool],
    latency_ms: Optional[float],
    energy_wh: Optional[float],
    safety_ok: Optional[bool],
    features: Dict[str, Any] | None = None,
    energy_budget_wh: Optional[float] = None,
) -> Dict[str, Optional[float]]:
    """
    Returnerar normaliserade delpoäng i [0,1] för precision, latency, energy, safety.
    - precision: 1 om verktyget lyckades, else 0 (None om okänt)
    - latency:    1 när latency <= target, faller linjärt mot 0 upp till 3x target
    - energy:     1 när energi <= budget, linjärt mot 0 upp till 3x budget
    - safety:     1 om ja, annars 0 (policy_refusal etc → 0)
    """
    # precision
    precision = _safe_bool_to_score(tool_success)

    # latency
    lat_score: Optional[float] = None
    if latency_ms is not None and latency_ms >= 0:
        target = _latency_target_ms(features or {})
        # Linear decay: target → 1.0, 3x target → 0.0
        lat_score = _clip01((3.0 * target - float(latency_ms)) / (2.0 * target))

    # energy
    energy_score: Optional[float] = None
    if energy_wh is not None and energy_wh >= 0:
        budget = energy_budget_wh or _env_float(
            "RL_ENERGY_BUDGET_WH", DEFAULTS["ENERGY_BUDGET_WH"]
        )
        energy_score = _clip01((3.0 * budget - float(energy_wh)) / (2.0 * budget))

    # safety
    safety = _safe_bool_to_score(safety_ok)

    return {
        "precision": precision,
        "latency": lat_score,
        "energy": energy_score,
        "safety": safety,
    }


def fibonacci_weighted_total(
    comp: Dict[str, Optional[float]],
    alpha: Optional[float] = None,
    missing_policy: str = "skip",  # "skip" ignorerar None, "zero" räknar None som 0
) -> float:
    """
    φ-viktad totalscore:
      R_total = φ^α * precision + φ^(α-1) * latency + φ^(α-2) * energy + φ^(α-3) * safety
    Saknade komponenter hanteras via missing_policy.
    Normaliseras genom att dividera med summan av använda vikter → [0,1].
    """
    a = _env_float("RL_ALPHA", DEFAULTS["ALPHA"]) if alpha is None else alpha

    weights = {
        "precision": PHI**a,
        "latency": PHI ** (a - 1.0),
        "energy": PHI ** (a - 2.0),
        "safety": PHI ** (a - 3.0),
    }

    num, den = 0.0, 0.0
    for k in ("precision", "latency", "energy", "safety"):
        v = comp.get(k, None)
        if v is None:
            if missing_policy == "zero":
                v = 0.0
            else:  # skip
                continue
        w = weights[k]
        num += w * float(v)
        den += w

    if den <= 0:
        return 0.0
    return _clip01(num / den)


def compute_reward_total(
    *,
    tool_success: Optional[bool],
    latency_ms: Optional[float],
    energy_wh: Optional[float],
    safety_ok: Optional[bool],
    features: Dict[str, Any] | None = None,
    alpha: Optional[float] = None,
    energy_budget_wh: Optional[float] = None,
    missing_policy: str = "skip",
) -> Tuple[Dict[str, Optional[float]], float]:
    """
    Bekväm wrapper: beräkna komponentpoäng + totalt φ-viktat resultat.
    """
    comps = component_scores(
        tool_success=tool_success,
        latency_ms=latency_ms,
        energy_wh=energy_wh,
        safety_ok=safety_ok,
        features=features,
        energy_budget_wh=energy_budget_wh,
    )
    total = fibonacci_weighted_total(comps, alpha=alpha, missing_policy=missing_policy)
    return comps, total
