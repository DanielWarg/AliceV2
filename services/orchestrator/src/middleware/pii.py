"""
PII Masking Middleware
Masks sensitive data in logs and responses based on consent scopes
"""

import re
from typing import Any, Dict

import structlog
from fastapi import Request

logger = structlog.get_logger(__name__)

# PII patterns to detect and mask
PII_PATTERNS = {
    "email": r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b",
    "phone": r"\b(?:\+?1[-.\s]?)?\(?([0-9]{3})\)?[-.\s]?([0-9]{3})[-.\s]?([0-9]{4})\b",
    "personnummer": r"\b\d{6}[-+]?\d{4}\b",  # Swedish personal number
    "name": r"\b[A-Z][a-z]+ [A-Z][a-z]+\b",  # Simple name pattern
}

# Consent scopes that control PII handling
CONSENT_SCOPES = {
    "bronze": ["basic_logging"],  # Only basic info
    "silver": ["basic_logging", "performance_metrics"],  # + performance data
    "gold": [
        "basic_logging",
        "performance_metrics",
        "detailed_analytics",
    ],  # + detailed data
}


def mask_pii(text: str, consent_level: str = "bronze") -> str:
    """Mask PII in text based on consent level"""
    if consent_level == "gold":
        return text  # No masking for gold level

    masked_text = text

    # Mask email addresses
    if consent_level in ["bronze", "silver"]:
        masked_text = re.sub(
            PII_PATTERNS["email"],
            lambda m: f"{m.group(0)[:3]}***@{m.group(0).split('@')[1]}",
            masked_text,
        )

    # Mask phone numbers
    if consent_level == "bronze":
        masked_text = re.sub(PII_PATTERNS["phone"], "***-***-****", masked_text)

    # Mask personal numbers
    if consent_level == "bronze":
        masked_text = re.sub(PII_PATTERNS["personnummer"], "******-****", masked_text)

    # Mask names (simple approach)
    if consent_level == "bronze":
        masked_text = re.sub(
            PII_PATTERNS["name"],
            lambda m: f"{m.group(0)[0]}*** {m.group(0).split()[1][0]}***",
            masked_text,
        )

    return masked_text


def get_consent_level(request: Request) -> str:
    """Get consent level from request headers or default to bronze"""
    consent_header = request.headers.get("X-Consent-Level", "bronze")
    if consent_header not in CONSENT_SCOPES:
        return "bronze"
    return consent_header


def mask_request_data(data: Dict[str, Any], consent_level: str) -> Dict[str, Any]:
    """Mask PII in request data"""
    if consent_level == "gold":
        return data

    masked_data = {}
    for key, value in data.items():
        if isinstance(value, str):
            masked_data[key] = mask_pii(value, consent_level)
        elif isinstance(value, dict):
            masked_data[key] = mask_request_data(value, consent_level)
        else:
            masked_data[key] = value

    return masked_data


def create_pii_safe_logger(request: Request):
    """Create a logger that automatically masks PII"""
    consent_level = get_consent_level(request)

    def safe_log(level: str, message: str, **kwargs):
        # Mask PII in kwargs
        safe_kwargs = mask_request_data(kwargs, consent_level)

        # Add consent level to log
        safe_kwargs["consent_level"] = consent_level

        # Log with masked data
        getattr(logger, level)(message, **safe_kwargs)

    return safe_log
