from functools import wraps
from datetime import datetime
from typing import Callable, Any, Dict, Optional
import re
from models import CacheKey, CacheEntry
from key_builder import build_fingerprint
from config import TTL_BY_LEVEL, MAX_RESPONSE_SIZE_KB, MAX_EVIDENCE_SIZE_KB, PII_PATTERNS
from metrics import cache_hit, cache_miss, stale_prevented, save_ms


def _filter_pii(text: str) -> str:
    """Filter PII from evidence"""
    filtered = text
    for pattern in PII_PATTERNS:
        filtered = re.sub(pattern, '[REDACTED]', filtered)
    return filtered


def _check_size_limit(data: Dict[str, Any], max_size_kb: int) -> bool:
    """Check if data size is within limit"""
    size_bytes = len(str(data).encode('utf-8'))
    return size_bytes <= max_size_kb * 1024


def semantic_cache(store, settings):
    """
    Använd så här:
    @semantic_cache(store, settings)
    async def plan(*, prompt_core, context_facts, classifier, schema_version, prompt_version, deps_version, locale_user, persona_mode, time_bucket, safety_mode, model_id, level) -> dict:
        ...
    """
    def decorator(func: Callable[..., Any]):
        @wraps(func)
        async def wrapper(*, prompt_core: str, context_facts: list[str], classifier,  # classifier har .intent och .level
                          schema_version: str, prompt_version: str, deps_version: str,
                          locale_user: str, persona_mode: str, time_bucket: Optional[str],
                          safety_mode: str, model_id: str, level: str, **kwargs):
            intent = classifier.intent or "none"
            lvl = (level or classifier.level or "easy").lower()
            ttl = TTL_BY_LEVEL.get(lvl, 300)

            fp = build_fingerprint(
                intent=intent,
                prompt_core=prompt_core,
                context_facts=context_facts,
                schema_version=schema_version,
                prompt_version=prompt_version,
                deps_version=deps_version,
                locale_user=locale_user,
                persona_mode=persona_mode,
                time_bucket=time_bucket,
                safety_mode=safety_mode,
                model_id=model_id,
            )
            key = CacheKey(fingerprint=fp, intent=intent,
                           schema_version=schema_version, deps_version=deps_version)

            # HIT path
            cached = await store.get(key)
            if cached:
                cache_hit.labels(intent=intent, level=lvl).inc()
                return cached.response

            cache_miss.labels(intent=intent, level=lvl).inc()

            # MISS → kör planner
            response: Dict[str, Any] = await func(
                prompt_core=prompt_core, context_facts=context_facts,
                classifier=classifier, schema_version=schema_version,
                prompt_version=prompt_version, deps_version=deps_version,
                locale_user=locale_user, persona_mode=persona_mode,
                time_bucket=time_bucket, safety_mode=safety_mode,
                model_id=model_id, level=lvl, **kwargs
            )

            # skriv endast framgångar och endast EASY/MEDIUM
            schema_ok = bool(response.get("meta", {}).get("schema_ok", True))
            final_intent = response.get("intent", intent)
            
            # Intent drift → skriv inte; förhindra stale
            if final_intent != intent:
                stale_prevented.inc()
                return response
                
            # Size check
            if not _check_size_limit(response, MAX_RESPONSE_SIZE_KB):
                return response
                
            # Level check
            if lvl == "hard" or not schema_ok:
                return response

            # Prepare evidence with PII filtering
            evidence = {
                "tool_args": response.get("args"),
                "selected_facts": [_filter_pii(fact) for fact in context_facts[:10]],
                "model_id": model_id,
            }
            
            if not _check_size_limit(evidence, MAX_EVIDENCE_SIZE_KB):
                return response

            entry = CacheEntry(
                response=response,
                evidence=evidence,
                cached_at=datetime.utcnow(),
                ttl_sec=ttl
            )
            
            with save_ms.labels(intent=intent, level=lvl).time():
                await store.set(key, entry)
            return response
        return wrapper
    return decorator
