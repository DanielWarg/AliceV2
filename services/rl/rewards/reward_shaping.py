#!/usr/bin/env python3
"""
T3 - Fibonacci Reward Shaping v1
φ-viktad belöningsfunktion med gyllene snittet för Alice vNext
"""
import os
import math
from typing import Optional

# Fibonacci konstanter
PHI = 1.61803398875  # Gyllene snittet (φ)
ALPHA = int(os.getenv("RL_FR_ALPHA", "2"))  # Exponentiell viktning

# Miljö-konfiguration för trösklar
MIN_LATENCY_MS = int(os.getenv("RL_MIN_LATENCY_MS", "0"))
MAX_LATENCY_MS = int(os.getenv("RL_MAX_LATENCY_MS", "900"))
LATENCY_GOOD_MS = int(os.getenv("RL_LATENCY_GOOD_MS", "250"))

MIN_ENERGY_WH = float(os.getenv("RL_MIN_ENERGY_WH", "0.0"))
MAX_ENERGY_WH = float(os.getenv("RL_MAX_ENERGY_WH", "0.1"))
ENERGY_GOOD_WH = float(os.getenv("RL_ENERGY_GOOD_WH", "0.03"))


def precision_reward(precision: int) -> float:
    """
    Precision belöning: +1.0 för korrekt, -1.0 för fel
    
    Args:
        precision: 1 för korrekt svar, 0 för fel/okänt
    
    Returns:
        1.0 om precision==1, annars -1.0
    """
    return 1.0 if precision == 1 else -1.0


def latency_reward(latency_ms: Optional[int]) -> float:
    """
    Latens belöning med trappsteg:
    +1.0: ≤ 250ms (snabb)
    0.0: 251-900ms (acceptabel)
    -1.0: > 900ms (långsam)
    
    Args:
        latency_ms: Svarstid i millisekunder, None = unknown
    
    Returns:
        Latens belöning mellan -1.0 och +1.0
    """
    if latency_ms is None:
        return 0.0  # Okänd latens = neutral
    
    if latency_ms <= LATENCY_GOOD_MS:
        return 1.0
    elif latency_ms <= MAX_LATENCY_MS:
        return 0.0
    else:
        return -1.0


def energy_reward(energy_wh: Optional[float]) -> float:
    """
    Energi belöning:
    +1.0: ≤ 0.03 Wh (låg energi)
    0.0: > 0.03 Wh (högar energi)
    
    Args:
        energy_wh: Energiförbrukning i Watt-timmar, None = unknown
    
    Returns:
        Energi belöning 0.0 eller +1.0
    """
    if energy_wh is None:
        return 0.0  # Okänd energi = neutral
    
    return 1.0 if energy_wh <= ENERGY_GOOD_WH else 0.0


def safety_reward(safety_ok: bool) -> float:
    """
    Säkerhets belöning:
    +1.0: Säkert (ingen policy refusal)
    -1.0: Osäkert (policy refusal)
    
    Args:
        safety_ok: True för säkert, False för osäkert
    
    Returns:
        +1.0 för säkert, -1.0 för osäkert
    """
    return 1.0 if safety_ok else -1.0


def shaped_reward(precision: int, latency_ms: Optional[int], energy_wh: Optional[float], safety_ok: bool) -> float:
    """
    Huvudfunktion: Fibonacci-viktad total belöning
    
    Använder gyllene snittet (φ = 1.618) för att vikta komponenter:
    - φ^α * precision (högst vikt)
    - φ^(α-1) * latency  
    - φ^(α-2) * energy
    - φ^(α-3) * safety (lägst vikt)
    
    Args:
        precision: 1 för korrekt, 0 för fel
        latency_ms: Svarstid i ms (None = unknown)
        energy_wh: Energiförbrukning i Wh (None = unknown)
        safety_ok: True för säkert, False för osäkert
    
    Returns:
        Total viktad belöning
    """
    # Beräkna individuella belöningar
    r_precision = precision_reward(precision)
    r_latency = latency_reward(latency_ms)
    r_energy = energy_reward(energy_wh)
    r_safety = safety_reward(safety_ok)
    
    # Fibonacci-viktning med φ^α-mönster
    # Precision dominerar (φ^α), sedan latency (φ^(α-1)), osv.
    w_precision = PHI ** ALPHA
    w_latency = PHI ** (ALPHA - 1) if ALPHA >= 1 else 1.0
    w_energy = PHI ** (ALPHA - 2) if ALPHA >= 2 else 1.0
    w_safety = PHI ** (ALPHA - 3) if ALPHA >= 3 else 1.0
    
    # Viktad summa
    total_reward = (
        w_precision * r_precision +
        w_latency * r_latency +
        w_energy * r_energy +
        w_safety * r_safety
    )
    
    return total_reward


def compute_reward_components(precision: int, latency_ms: Optional[int], energy_wh: Optional[float], safety_ok: bool) -> dict:
    """
    Beräkna alla belöningskomponenter för Episode.reward_components
    
    Returns:
        Dict med precision, latency, energy, safety, total
    """
    r_precision = precision_reward(precision)
    r_latency = latency_reward(latency_ms)
    r_energy = energy_reward(energy_wh)
    r_safety = safety_reward(safety_ok)
    r_total = shaped_reward(precision, latency_ms, energy_wh, safety_ok)
    
    return {
        "precision": int(r_precision) if r_precision in [-1, 1] else 0,
        "latency": int(r_latency) if r_latency in [-1, 0, 1] else 0,
        "energy": int(r_energy) if r_energy in [0, 1] else 0,
        "safety": int(r_safety) if r_safety in [-1, 1] else 0,
        "total": float(r_total)
    }


def get_reward_info() -> dict:
    """Returnera konfigurationsinformation för debugging"""
    return {
        "phi": PHI,
        "alpha": ALPHA,
        "weights": {
            "precision": PHI ** ALPHA,
            "latency": PHI ** (ALPHA - 1) if ALPHA >= 1 else 1.0,
            "energy": PHI ** (ALPHA - 2) if ALPHA >= 2 else 1.0,
            "safety": PHI ** (ALPHA - 3) if ALPHA >= 3 else 1.0
        },
        "thresholds": {
            "latency_good_ms": LATENCY_GOOD_MS,
            "latency_max_ms": MAX_LATENCY_MS,
            "energy_good_wh": ENERGY_GOOD_WH
        }
    }


if __name__ == "__main__":
    # Test exempel
    print("🧮 Fibonacci Reward Shaping v1 Test")
    print(f"φ = {PHI}, α = {ALPHA}")
    print()
    
    # Test cases
    test_cases = [
        {"precision": 1, "latency_ms": 200, "energy_wh": 0.02, "safety_ok": True, "desc": "Perfekt episod"},
        {"precision": 1, "latency_ms": 500, "energy_wh": 0.05, "safety_ok": True, "desc": "Korrekt men långsam"},
        {"precision": 0, "latency_ms": 100, "energy_wh": 0.01, "safety_ok": True, "desc": "Snabb men fel svar"},
        {"precision": 1, "latency_ms": 200, "energy_wh": 0.02, "safety_ok": False, "desc": "Korrekt men osäker"},
    ]
    
    for i, case in enumerate(test_cases, 1):
        print(f"Test {i}: {case['desc']}")
        components = compute_reward_components(
            case["precision"], case["latency_ms"], case["energy_wh"], case["safety_ok"]
        )
        print(f"  Komponenter: {components}")
        print(f"  Total: {components['total']:.3f}")
        print()
    
    print("Konfiguration:")
    info = get_reward_info()
    for key, value in info.items():
        print(f"  {key}: {value}")