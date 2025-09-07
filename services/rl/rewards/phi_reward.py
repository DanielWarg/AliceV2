# services/rl/rewards/phi_reward.py
from __future__ import annotations
import os
from dataclasses import dataclass
from typing import Optional, Dict, Any

# Golden ratio
PHI = float(os.getenv("RL_PHI", "1.618033988749895"))

# ---------- Defaults (kan override:as via env) ----------
# Latency: perfekt ≤ 900 ms, sämsta gräns 1500 ms (linjär normalisering, clamp 0..1)
LATENCY_TARGET_MS = float(os.getenv("RL_LATENCY_TARGET_MS", "900"))
LATENCY_WORST_MS  = float(os.getenv("RL_LATENCY_WORST_MS",  "1500"))

# Energy: perfekt ≤ 0.05 Wh, sämsta gräns 0.20 Wh (linjär normalisering, clamp 0..1)
ENERGY_BUDGET_WH  = float(os.getenv("RL_ENERGY_BUDGET_WH",  "0.05"))
ENERGY_WORST_WH   = float(os.getenv("RL_ENERGY_WORST_WH",   "0.20"))

# Missing-policy för komponenter: "skip" (normalisera över tillgängliga), "zero" (räkna som 0), "impute" (sätt 0.5)
MISSING_POLICY    = os.getenv("RL_MISSING_POLICY", "skip").lower()  # "skip" rekommenderas (din T3)

# Säkerhets-straff: om safety_ok=False → safety=0 (hård)
SAFETY_HARD_FAIL  = os.getenv("RL_SAFETY_HARD_FAIL", "true").lower() in ("1","true","yes","y")

# Viktprofil (φ^α nedåt per komponentordning)
# Ordning: precision, latency, energy, safety (som i dina T1–T3)
ALPHA = float(os.getenv("RL_WEIGHT_ALPHA", "2.0"))  # precision får φ^2, latency φ^1, energy φ^0, safety φ^-1

@dataclass
class RewardComponents:
    precision: Optional[float]  # 0..1 eller None
    latency:   Optional[float]  # 0..1 eller None
    energy:    Optional[float]  # 0..1 eller None
    safety:    Optional[float]  # 0..1 eller None
    total:     Optional[float]  # 0..1

def _clamp01(x: float) -> float:
    return 0.0 if x < 0 else 1.0 if x > 1 else x

def _norm_latency(latency_ms: Optional[float]) -> Optional[float]:
    if latency_ms is None:
        return None
    if latency_ms <= LATENCY_TARGET_MS:
        return 1.0
    if latency_ms >= LATENCY_WORST_MS:
        return 0.0
    # linjär fallande mellan target och worst
    span = (LATENCY_WORST_MS - LATENCY_TARGET_MS)
    return _clamp01(1.0 - ((latency_ms - LATENCY_TARGET_MS) / span))

def _norm_energy(energy_wh: Optional[float]) -> Optional[float]:
    if energy_wh is None:
        return None
    if energy_wh <= ENERGY_BUDGET_WH:
        return 1.0
    if energy_wh >= ENERGY_WORST_WH:
        return 0.0
    span = (ENERGY_WORST_WH - ENERGY_BUDGET_WH)
    return _clamp01(1.0 - ((energy_wh - ENERGY_BUDGET_WH) / span))

def _score_precision(tool_success: Optional[bool], schema_ok: Optional[bool]) -> Optional[float]:
    # Enkel deterministisk precision: kräver att schema_ok == True och tool_success == True
    # Om bara schema_ok finns → räkna 1.0 om True, annars 0.0. Om inget finns → None.
    if tool_success is None and schema_ok is None:
        return None
    if tool_success is None:
        return 1.0 if bool(schema_ok) else 0.0
    if schema_ok is None:
        return 1.0 if bool(tool_success) else 0.0
    return 1.0 if (tool_success and schema_ok) else 0.0

def _score_safety(safety_ok: Optional[bool]) -> Optional[float]:
    if safety_ok is None:
        return None
    if SAFETY_HARD_FAIL:
        return 1.0 if safety_ok else 0.0
    # mjukare alternativ kunde vara 0.5 vid None/okänd, men vi håller oss till hård default
    return 1.0 if safety_ok else 0.0

def _apply_missing(x: Optional[float]) -> Optional[float]:
    if x is not None:
        return _clamp01(x)
    if MISSING_POLICY == "skip":
        return None
    if MISSING_POLICY == "zero":
        return 0.0
    if MISSING_POLICY == "impute":
        return 0.5
    # default fallback
    return None

def _weights_phi(alpha: float) -> Dict[str, float]:
    # precision: φ^α, latency: φ^(α-1), energy: φ^(α-2), safety: φ^(α-3)
    return {
        "precision": PHI ** (alpha - 0.0),
        "latency":   PHI ** (alpha - 1.0),
        "energy":    PHI ** (alpha - 2.0),
        "safety":    PHI ** (alpha - 3.0),
    }

def compute_phi_total(
    *,
    latency_ms: Optional[float],
    energy_wh: Optional[float],
    safety_ok: Optional[bool],
    tool_success: Optional[bool],
    schema_ok: Optional[bool],
) -> Dict[str, Optional[float]]:
    """
    Huvudfunktion: beräkna komponentpoäng + φ-vägd total (normaliserad över tillgängliga komponenter).
    Matchar T3-beteendet: saknade komponenter hanteras enligt MISSING_POLICY, default "skip".
    """

    precision = _apply_missing(_score_precision(tool_success, schema_ok))
    latency   = _apply_missing(_norm_latency(latency_ms))
    energy    = _apply_missing(_norm_energy(energy_wh))
    safety    = _apply_missing(_score_safety(safety_ok))

    weights = _weights_phi(ALPHA)

    # Samla aktiva (ej None) komponenter
    parts = []
    for name, val in (("precision", precision), ("latency", latency), ("energy", energy), ("safety", safety)):
        if val is not None:
            parts.append((name, val, weights[name]))

    if not parts:
        total = None
    else:
        # φ-viktad medelpoäng normaliserad över de komponenter som finns
        w_sum = sum(w for _, _, w in parts)
        total = sum(v * w for _, v, w in parts) / (w_sum if w_sum > 0 else 1.0)
        total = _clamp01(total)

    return {
        "precision": precision,
        "latency": latency,
        "energy": energy,
        "safety": safety,
        "total": total,
    }

# ---------- Hjälpare för orkestratorn ----------

def compute_from_metrics(metrics: Dict[str, Any]) -> Dict[str, Optional[float]]:
    """
    Bekväm wrapper när du har en metrics-dict från turnen.
    Förväntar nycklar:
      - "latency_ms": float
      - "energy_wh": float
      - "safety_ok": bool
      - "tool_success": bool | None
      - "schema_ok": bool | None
    Onämnda = behandlas som None → följer MISSING_POLICY.
    """
    return compute_phi_total(
        latency_ms = metrics.get("latency_ms"),
        energy_wh  = metrics.get("energy_wh"),
        safety_ok  = metrics.get("safety_ok"),
        tool_success = metrics.get("tool_success"),
        schema_ok    = metrics.get("schema_ok"),
    )


if __name__ == "__main__":
    # Perfekt case: låg latens, låg energi, säker, ok schema+tool
    print("Perfect case:")
    print(compute_phi_total(
        latency_ms=231.0,
        energy_wh=0.0004,
        safety_ok=True,
        tool_success=True,
        schema_ok=True,
    ))
    
    # Case utan precision (t.ex. ingen tool_success/schema_ok i metrik)
    print("\nSkipped precision case:")
    os.environ["RL_MISSING_POLICY"] = "skip"
    print(compute_phi_total(
        latency_ms=231.0,
        energy_wh=0.0004,
        safety_ok=True,
        tool_success=None,
        schema_ok=None,
    ))