import hashlib
import json
from typing import Any, Dict, Optional

_CANON_ORDER = [
    "intent", "prompt_core", "context_facts", "schema_version", "prompt_version",
    "deps_version", "locale_user", "persona_mode", "time_bucket",
    "safety_mode", "model_id"
]


def _canonical_json(obj: Any) -> str:
    return json.dumps(obj, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def build_fingerprint(
    intent: str,
    prompt_core: str,
    context_facts: list[str],
    schema_version: str,
    prompt_version: str,
    deps_version: str,
    locale_user: str,
    persona_mode: str,
    time_bucket: Optional[str],
    safety_mode: str,
    model_id: str,
) -> str:
    # Normalisera
    payload = {
        "intent": intent,
        "prompt_core": prompt_core.strip(),
        "context_facts": sorted(set(context_facts or [])),
        "schema_version": schema_version,
        "prompt_version": prompt_version,
        "deps_version": deps_version,
        "locale_user": (locale_user or "sv-SE"),
        "persona_mode": persona_mode or "standard",
        "time_bucket": time_bucket or "",
        "safety_mode": safety_mode or "standard",
        "model_id": model_id or "unknown",
    }
    # Skriv i fast ordning för 100% determinism
    ordered = {k: payload[k] for k in _CANON_ORDER}
    data = _canonical_json(ordered).encode("utf-8")
    return hashlib.sha256(data).hexdigest()
