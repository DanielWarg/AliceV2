"""
Alice v2 Testing Configuration
SLO targets, endpoints, and safety limits for autonomous testing
"""

import os
from typing import Dict, Any


class TestConfig:
    """Configuration for Alice v2 autonomous testing system"""
    
    # === Service Endpoints ===
    API_BASE = os.getenv("API_BASE", "http://localhost:8000")
    WS_ASR = os.getenv("WS_ASR", "ws://localhost:8000/ws/asr") 
    GUARDIAN_URL = os.getenv("GUARDIAN_URL", "http://localhost:8787")
    VOICE_SERVICE_URL = os.getenv("VOICE_SERVICE_URL", "http://localhost:8001")
    DASHBOARD_URL = os.getenv("DASHBOARD_URL", "http://localhost:8501")
    
    # === External Service URLs (Sandbox Accounts) ===
    EMAIL_SMTP_URL = os.getenv("EMAIL_SMTP_URL", "smtp://testuser:pass@sandbox-mail.example.com:587")
    EMAIL_IMAP_URL = os.getenv("EMAIL_IMAP_URL", "imap://testuser:pass@sandbox-mail.example.com:993")
    CALDAV_URL = os.getenv("CALDAV_URL", "https://testuser:pass@sandbox-cal.example.com/caldav/")
    HOME_ASSISTANT_URL = os.getenv("HOME_ASSISTANT_URL", "http://homeassistant-dev:8123")
    CAMERA_RTSP_URL = os.getenv("CAMERA_RTSP_URL", "rtsp://demo:demo@cam.example.com/live.sdp")
    
    # === SLO Performance Targets (milliseconds) ===
    # Voice Pipeline
    SLO_VOICE_E2E_MS = int(os.getenv("SLO_VOICE_E2E_MS", "2000"))       # End-to-end voice latency
    SLO_ASR_PARTIAL_MS = int(os.getenv("SLO_ASR_PARTIAL_MS", "300"))    # Partial transcript
    SLO_ASR_FINAL_MS = int(os.getenv("SLO_ASR_FINAL_MS", "800"))        # Final transcript
    
    # LLM Performance  
    SLO_MICRO_FIRST_MS = int(os.getenv("SLO_MICRO_FIRST_MS", "250"))    # Micro LLM first token
    SLO_PLANNER_FIRST_MS = int(os.getenv("SLO_PLANNER_FIRST_MS", "900")) # Planner first token
    SLO_PLANNER_FULL_MS = int(os.getenv("SLO_PLANNER_FULL_MS", "1500"))  # Planner complete
    SLO_DEEP_FIRST_MS = int(os.getenv("SLO_DEEP_FIRST_MS", "1800"))     # Deep LLM first token
    SLO_DEEP_FULL_MS = int(os.getenv("SLO_DEEP_FULL_MS", "3000"))       # Deep complete
    
    # TTS Performance
    SLO_TTS_CACHED_MS = int(os.getenv("SLO_TTS_CACHED_MS", "120"))      # Cached TTS response
    SLO_TTS_UNCACHED_MS = int(os.getenv("SLO_TTS_UNCACHED_MS", "800"))  # Fresh TTS generation
    
    # Guardian & System
    SLO_GUARDIAN_RESPONSE_MS = int(os.getenv("SLO_GUARDIAN_RESPONSE_MS", "150"))
    SLO_GUARDIAN_RECOVERY_S = int(os.getenv("SLO_GUARDIAN_RECOVERY_S", "45"))
    
    # Vision System
    SLO_VISION_FIRST_DETECTION_MS = int(os.getenv("SLO_VISION_FIRST_DETECTION_MS", "350"))
    SLO_RTSP_RECONNECT_MS = int(os.getenv("SLO_RTSP_RECONNECT_MS", "2000"))
    
    # === SLO Quality Targets (ratios 0.0-1.0) ===
    SLO_WER_CLEAN = float(os.getenv("SLO_WER_CLEAN", "0.07"))           # ≤7% WER clean audio
    SLO_WER_NOISY = float(os.getenv("SLO_WER_NOISY", "0.11"))           # ≤11% WER with noise
    SLO_INTENT_ACCURACY = float(os.getenv("SLO_INTENT_ACCURACY", "0.92")) # ≥92% intent accuracy
    SLO_TOOL_SUCCESS_RATE = float(os.getenv("SLO_TOOL_SUCCESS_RATE", "0.95")) # ≥95% tool success
    SLO_SYSTEM_AVAILABILITY = float(os.getenv("SLO_SYSTEM_AVAILABILITY", "0.995")) # 99.5% uptime
    
    # === Resource Limits ===
    MAX_RAM_MB = int(os.getenv("MAX_RAM_MB", "15360"))                  # 15GB total system RAM
    MAX_CONCURRENT_DEEP_JOBS = int(os.getenv("MAX_CONCURRENT_DEEP_JOBS", "1"))
    MAX_ENERGY_BUDGET_WH = float(os.getenv("MAX_ENERGY_BUDGET_WH", "5.0"))
    
    # === Test Execution Configuration ===
    TEST_CYCLE_INTERVAL_S = int(os.getenv("TEST_CYCLE_INTERVAL_S", "900"))  # 15 minutes
    MAX_PARALLEL_SCENARIOS = int(os.getenv("MAX_PARALLEL_SCENARIOS", "3"))
    SCENARIO_TIMEOUT_S = int(os.getenv("SCENARIO_TIMEOUT_S", "300"))        # 5 minute timeout
    
    # === Remediation Safety Limits ===
    REMEDIATION_ENABLED = os.getenv("REMEDIATION_ENABLED", "true").lower() == "true"
    MAX_REMEDIATIONS_PER_CYCLE = int(os.getenv("MAX_REMEDIATIONS_PER_CYCLE", "1"))
    REMEDIATION_COOLDOWN_S = int(os.getenv("REMEDIATION_COOLDOWN_S", "1800"))  # 30 minutes
    AUTO_ROLLBACK_AFTER_FAILURES = int(os.getenv("AUTO_ROLLBACK_AFTER_FAILURES", "2"))
    
    # === Data Management ===
    DATASET_MAX_AGE_DAYS = int(os.getenv("DATASET_MAX_AGE_DAYS", "30"))
    NOISE_PROFILE_MAX_AGE_DAYS = int(os.getenv("NOISE_PROFILE_MAX_AGE_DAYS", "7"))
    AUDIO_RETENTION_HOURS = int(os.getenv("AUDIO_RETENTION_HOURS", "24"))
    LOG_RETENTION_DAYS = int(os.getenv("LOG_RETENTION_DAYS", "30"))
    
    # === Privacy & Security ===
    CONSENT_SCOPES = os.getenv("CONSENT_SCOPES", "memory:write,email:metadata,calendar:read").split(",")
    PII_MASKING_ENABLED = os.getenv("PII_MASKING_ENABLED", "true").lower() == "true"
    SANDBOX_MODE_ONLY = os.getenv("SANDBOX_MODE_ONLY", "true").lower() == "true"
    
    # === Remediation Parameter Ranges ===
    # Safe parameter adjustment ranges for automatic remediation
    REMEDIATION_RANGES = {
        # Voice Activity Detection
        "vad_start_threshold": {"min": 0.3, "max": 0.7, "default": 0.5},
        "vad_stop_threshold": {"min": 0.2, "max": 0.5, "default": 0.35},
        "vad_eos_timeout_ms": {"min": 500, "max": 1200, "default": 700},
        
        # ASR Parameters
        "asr_beam_width": {"min": 1, "max": 5, "default": 3},
        "asr_language_weight": {"min": 0.5, "max": 2.0, "default": 1.0},
        
        # RAG & Memory
        "rag_top_k": {"min": 2, "max": 10, "default": 5},
        "rag_similarity_threshold": {"min": 0.6, "max": 0.9, "default": 0.75},
        "memory_context_window": {"min": 1000, "max": 4000, "default": 2000},
        
        # LLM Parameters
        "llm_temperature": {"min": 0.1, "max": 0.9, "default": 0.7},
        "llm_max_tokens": {"min": 100, "max": 1000, "default": 500},
        "llm_timeout_s": {"min": 5, "max": 30, "default": 15},
        
        # TTS Parameters  
        "tts_speed": {"min": 0.8, "max": 1.3, "default": 1.0},
        "tts_cache_ttl_hours": {"min": 1, "max": 24, "default": 6},
        
        # Guardian Thresholds
        "guardian_ram_soft_pct": {"min": 0.70, "max": 0.85, "default": 0.80},
        "guardian_recovery_timeout_s": {"min": 30, "max": 90, "default": 45},
        
        # Vision System
        "vision_confidence_threshold": {"min": 0.5, "max": 0.95, "default": 0.75},
        "rtsp_reconnect_attempts": {"min": 2, "max": 8, "default": 3},
        "vision_processing_timeout_s": {"min": 2, "max": 10, "default": 5}
    }
    
    @classmethod
    def get_slo_targets(cls) -> Dict[str, Any]:
        """Return all SLO targets as a dictionary"""
        return {
            "voice_e2e_ms": cls.SLO_VOICE_E2E_MS,
            "asr_partial_ms": cls.SLO_ASR_PARTIAL_MS, 
            "asr_final_ms": cls.SLO_ASR_FINAL_MS,
            "micro_first_ms": cls.SLO_MICRO_FIRST_MS,
            "planner_first_ms": cls.SLO_PLANNER_FIRST_MS,
            "planner_full_ms": cls.SLO_PLANNER_FULL_MS,
            "deep_first_ms": cls.SLO_DEEP_FIRST_MS,
            "deep_full_ms": cls.SLO_DEEP_FULL_MS,
            "tts_cached_ms": cls.SLO_TTS_CACHED_MS,
            "tts_uncached_ms": cls.SLO_TTS_UNCACHED_MS,
            "guardian_response_ms": cls.SLO_GUARDIAN_RESPONSE_MS,
            "wer_clean": cls.SLO_WER_CLEAN,
            "wer_noisy": cls.SLO_WER_NOISY,
            "intent_accuracy": cls.SLO_INTENT_ACCURACY,
            "tool_success_rate": cls.SLO_TOOL_SUCCESS_RATE,
            "system_availability": cls.SLO_SYSTEM_AVAILABILITY
        }
    
    @classmethod
    def validate_config(cls) -> bool:
        """Validate configuration values are within acceptable ranges"""
        issues = []
        
        # Check required environment variables
        required_vars = ["API_BASE", "GUARDIAN_URL"]
        for var in required_vars:
            if not getattr(cls, var):
                issues.append(f"Missing required config: {var}")
                
        # Validate SLO targets are reasonable
        if cls.SLO_WER_CLEAN >= 0.15:  # >15% WER is too high
            issues.append(f"WER clean target too high: {cls.SLO_WER_CLEAN}")
            
        if cls.SLO_VOICE_E2E_MS > 5000:  # >5s is unacceptable
            issues.append(f"Voice E2E target too slow: {cls.SLO_VOICE_E2E_MS}ms")
            
        # Check resource limits
        if cls.MAX_RAM_MB < 8192:  # <8GB probably insufficient
            issues.append(f"RAM limit too low: {cls.MAX_RAM_MB}MB")
            
        if issues:
            print(f"❌ Configuration validation failed:")
            for issue in issues:
                print(f"  - {issue}")
            return False
            
        return True
    
    def __str__(self) -> str:
        """String representation for logging"""
        return (f"TestConfig(API_BASE={self.API_BASE}, "
                f"WER_CLEAN≤{self.SLO_WER_CLEAN*100:.1f}%, "
                f"VOICE_E2E≤{self.SLO_VOICE_E2E_MS}ms, "
                f"REMEDIATION={self.REMEDIATION_ENABLED})")