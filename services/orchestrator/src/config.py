"""
Configuration Management
Environment validation and configuration using Pydantic Settings
"""

from pydantic import BaseSettings, Field, validator
from typing import Optional, List
import os

class OrchestratorSettings(BaseSettings):
    """Orchestrator configuration with environment validation"""
    
    # API Configuration
    api_version: str = Field(default="1", env="API_VERSION")
    api_title: str = Field(default="Alice v2 Orchestrator", env="API_TITLE")
    api_description: str = Field(default="LLM routing and API gateway for Alice AI Assistant", env="API_DESCRIPTION")
    
    # Server Configuration
    host: str = Field(default="127.0.0.1", env="HOST")
    port: int = Field(default=8000, env="PORT")
    debug: bool = Field(default=False, env="DEBUG")
    
    # Guardian Configuration
    guardian_url: str = Field(default="http://localhost:8787", env="GUARDIAN_URL")
    guardian_timeout: float = Field(default=0.5, env="GUARDIAN_TIMEOUT")
    
    # Rate Limiting
    rate_limit_enabled: bool = Field(default=True, env="RATE_LIMIT_ENABLED")
    default_rate_limit: int = Field(default=100, env="DEFAULT_RATE_LIMIT")
    rate_limit_window: int = Field(default=60, env="RATE_LIMIT_WINDOW")
    
    # Authentication
    auth_enabled: bool = Field(default=True, env="AUTH_ENABLED")
    api_keys: List[str] = Field(default=[], env="API_KEYS")
    
    # Metrics & Monitoring
    prometheus_enabled: bool = Field(default=True, env="PROMETHEUS_ENABLED")
    metrics_endpoint: str = Field(default="/metrics", env="METRICS_ENDPOINT")
    
    # Logging
    log_level: str = Field(default="INFO", env="LOG_LEVEL")
    log_format: str = Field(default="json", env="LOG_FORMAT")
    
    # PII & Consent
    pii_masking_enabled: bool = Field(default=True, env="PII_MASKING_ENABLED")
    default_consent_level: str = Field(default="bronze", env="DEFAULT_CONSENT_LEVEL")
    
    # Idempotency
    idempotency_enabled: bool = Field(default=True, env="IDEMPOTENCY_ENABLED")
    idempotency_ttl: int = Field(default=60, env="IDEMPOTENCY_TTL")
    
    # CORS
    cors_origins: List[str] = Field(default=["http://localhost:3000"], env="CORS_ORIGINS")
    cors_credentials: bool = Field(default=True, env="CORS_CREDENTIALS")
    
    # Telemetry
    telemetry_enabled: bool = Field(default=True, env="TELEMETRY_ENABLED")
    telemetry_dir: str = Field(default="/data/telemetry", env="TELEMETRY_DIR")
    
    @validator('api_version')
    def validate_api_version(cls, v):
        if v not in ["1"]:
            raise ValueError("Only API version 1 is supported")
        return v
    
    @validator('default_consent_level')
    def validate_consent_level(cls, v):
        if v not in ["bronze", "silver", "gold"]:
            raise ValueError("Consent level must be bronze, silver, or gold")
        return v
    
    @validator('log_level')
    def validate_log_level(cls, v):
        valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        if v.upper() not in valid_levels:
            raise ValueError(f"Log level must be one of {valid_levels}")
        return v.upper()
    
    @validator('port')
    def validate_port(cls, v):
        if not 1 <= v <= 65535:
            raise ValueError("Port must be between 1 and 65535")
        return v
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False

# Global settings instance
settings = OrchestratorSettings()

def validate_environment():
    """Validate that all required environment variables are set"""
    required_vars = [
        "GUARDIAN_URL",
        "API_VERSION",
    ]
    
    missing_vars = []
    for var in required_vars:
        if not os.getenv(var):
            missing_vars.append(var)
    
    if missing_vars:
        raise ValueError(f"Missing required environment variables: {', '.join(missing_vars)}")
    
    return True

def get_config_summary() -> dict:
    """Get configuration summary for logging"""
    return {
        "api_version": settings.api_version,
        "host": settings.host,
        "port": settings.port,
        "guardian_url": settings.guardian_url,
        "rate_limit_enabled": settings.rate_limit_enabled,
        "auth_enabled": settings.auth_enabled,
        "prometheus_enabled": settings.prometheus_enabled,
        "pii_masking_enabled": settings.pii_masking_enabled,
        "idempotency_enabled": settings.idempotency_enabled,
    }
