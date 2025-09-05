#!/usr/bin/env python3
"""
Cache key optimization for Alice v2
Two-tier cache key system for better hit rates
"""

import hashlib
from datetime import datetime
from typing import List


def canonical_prompt(text: str) -> str:
    """Normaliserar prompt för cache."""
    import re
    import unicodedata

    t = unicodedata.normalize("NFKC", text or "")
    t = t.lower()
    t = t.replace(""", '"').replace(""", '"').replace("'", "'")
    t = re.sub(r"\s+", " ", t).strip()
    # ta bort artiga prefix för bättre träff
    t = re.sub(r"^(hej|snälla|kan du|skulle du kunna|vänligen|tack)\s+", "", t)
    # ta bort vanliga suffix
    t = re.sub(r"\s+(tack|snälla|vänligen)$", "", t)
    return t


def canonical_facts(facts: List[str]) -> List[str]:
    """Sorterar och deduplikerar fakta."""
    return sorted(set(facts))[:8]  # top-8


def bucket_5min() -> int:
    """Returnerar 5-minuters bucket för nuvarande tid."""
    now = datetime.utcnow()
    return (now.hour * 60 + now.minute) // 5


def build_cache_key(
    intent: str,
    prompt_raw: str,
    facts: List[str] = None,
    schema_version: str = "v4",
    model_id: str = "llama3:8b",
    time_bucket: int = None,
) -> str:
    """
    Två-tier cache key:
    1. canonical_prompt + intent + schema_version + model_id + time_bucket
    2. Fallback till SHA256(prompt_raw) om miss
    """
    if facts is None:
        facts = []

    if time_bucket is None:
        time_bucket = bucket_5min()

    cp = canonical_prompt(prompt_raw)
    cf = "".join(canonical_facts(facts))

    # Primary key: normalized content
    primary = f"{schema_version}:{model_id}:{intent}:{time_bucket}:{hashlib.md5((cp + cf).encode()).hexdigest()[:12]}"

    return primary


def micro_key(intent: str, text: str) -> str:
    """Micro cache key: intent + canonical prompt hash"""
    c = canonical_prompt(text)
    h = hashlib.sha256(c.encode("utf-8")).hexdigest()[:16]
    return f"micro:{intent}:{h}"


def build_fallback_key(prompt_raw: str) -> str:
    """Fallback cache key för exakt match."""
    return f"fallback:{hashlib.md5(prompt_raw.encode()).hexdigest()[:16]}"
