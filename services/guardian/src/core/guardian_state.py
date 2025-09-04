"""Guardian state management and configuration"""

from dataclasses import dataclass
from enum import Enum


class GuardianState(Enum):
    """Guardian systemtillstånd med hysteresis"""

    NORMAL = "normal"
    BROWNOUT = "brownout"  # Intelligent degradation
    DEGRADED = "degraded"  # Basic degradation
    EMERGENCY = "emergency"  # Hard kill läge
    LOCKDOWN = "lockdown"  # Manual intervention required


@dataclass
class GuardianConfig:
    """Deterministisk konfiguration - inga AI-parametrar"""

    # Polling
    poll_interval_s: float = 1.0

    # Hysteresis trösklar (andel av total) - Optimized för production
    ram_soft_pct: float = 0.80  # Mjuk degradation trigger (var 0.85)
    ram_hard_pct: float = 0.92  # Hard kill trigger
    ram_recovery_pct: float = 0.70  # Recovery threshold (hysteresis)
    cpu_soft_pct: float = 0.80  # Mjuk degradation trigger (var 0.85)
    cpu_hard_pct: float = 0.92  # Hard kill trigger
    cpu_recovery_pct: float = 0.75  # Recovery threshold (hysteresis)
    disk_hard_pct: float = 0.95  # Hard kill
    temp_hard_c: float = 90.0  # Hard kill (om tillgänglig)

    # Hysteresis och flap detection - Optimized för stability
    measurement_window: int = 3  # Antal mätpunkter för trigger (var 5)
    recovery_window_s: float = 45.0  # Återställningstid i sekunder (var 60.0)
    flap_detection_window: int = 15  # Fönster för oscillation detection (var 10)

    # Kill cooldown settings
    kill_cooldown_short_s: float = 300.0  # 5 min mellan kills
    kill_cooldown_long_s: float = 1800.0  # 30 min window för max kills
    max_kills_per_window: int = 3  # Max 3 kills per 30min
    lockdown_duration_s: float = 3600.0  # 1h lockdown efter överträdelse

    # Brownout settings
    brownout_model_primary: str = "gpt-oss:20b"
    brownout_model_fallback: str = "gpt-oss:7b"
    brownout_context_window: int = 8  # Normal context
    brownout_context_reduced: int = 3  # Reduced context
    brownout_rag_top_k: int = 8  # Normal RAG
    brownout_rag_reduced: int = 3  # Reduced RAG

    # Auto-tuning
    concurrency_adjustment_interval_s: float = 60.0  # Justering var 60s
    target_p95_latency_ms: float = 2000.0  # Target p95 latency
    concurrency_min: int = 1
    concurrency_max: int = 10

    # Åtgärder
    enable_unload_model: bool = True
    enable_stop_intake: bool = True
    enable_kill_ollama: bool = True
    enable_brownout: bool = True
    enable_lockdown: bool = True

    # Endpoints - configurable via environment variables
    alice_base_url: str = "http://localhost:8000"  # Override with ALICE_BASE_URL
    ollama_base_url: str = "http://localhost:11434"  # Override with OLLAMA_BASE_URL
    guardian_port: int = 8787  # Override with GUARDIAN_PORT

    # Logging
    log_level: str = "INFO"
    log_format: str = "structured"  # structured|simple
    metrics_enabled: bool = True
