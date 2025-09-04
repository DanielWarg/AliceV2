"""
Smart cache system with telemetry, semantic matching and multi-tier storage.
Designed for maximum hit rate and minimum latency.
"""

import hashlib
import json
import os
import time
from typing import Any, Dict, Optional

import redis
import structlog

from ..cache_key import build_cache_key, canonical_prompt

logger = structlog.get_logger(__name__)


class CacheResult:
    """Cache operation result with detailed telemetry"""

    def __init__(
        self,
        hit: bool,
        data: Any = None,
        reason: str = "",
        source: str = "miss",
        latency_ms: float = 0.0,
    ):
        self.hit = hit
        self.data = data
        self.reason = reason
        self.source = source  # "l1", "l2", "semantic", "miss"
        self.latency_ms = latency_ms


class SmartCache:
    """Multi-tier cache with semantic understanding and telemetry"""

    def __init__(self):
        self.redis_url = os.getenv("REDIS_URL", "redis://alice-cache:6379")
        self.semantic_threshold = float(os.getenv("CACHE_SEMANTIC_THRESHOLD", "0.85"))

        # Statistics tracking
        self.stats = {
            "total_requests": 0,
            "l1_hits": 0,  # Exact matches
            "l2_hits": 0,  # Semantic matches
            "negative_hits": 0,  # Negative cache hits
            "misses": 0,
            "errors": 0,
            "avg_hit_latency_ms": 0.0,
            "avg_miss_latency_ms": 0.0,
        }

        try:
            self.redis_client = redis.from_url(self.redis_url, decode_responses=True)
            self.redis_client.ping()  # Test connection
            logger.info("Smart cache initialized", redis_url=self.redis_url)
        except Exception as e:
            logger.error("Failed to connect to Redis", error=str(e))
            self.redis_client = None

    async def get(
        self,
        intent: str,
        prompt: str,
        model_id: str = "qwen2.5:3b",
        schema_version: str = "v4",
    ) -> CacheResult:
        """Get from cache with multi-tier lookup and telemetry"""

        start_time = time.perf_counter()
        self.stats["total_requests"] += 1

        if not self.redis_client:
            return CacheResult(False, reason="redis_unavailable")

        try:
            # L1: Exact canonical match
            l1_key = build_cache_key(intent, prompt, [], schema_version, model_id)
            l1_result = self.redis_client.get(f"l1:{l1_key}")

            if l1_result:
                latency_ms = (time.perf_counter() - start_time) * 1000
                self.stats["l1_hits"] += 1
                self._update_hit_latency(latency_ms)

                logger.info(
                    "L1 cache HIT",
                    key=l1_key[:20],
                    intent=intent,
                    latency_ms=latency_ms,
                )

                return CacheResult(
                    True, json.loads(l1_result), "l1_exact_match", "l1", latency_ms
                )

            # L2: Semantic similarity search
            l2_result = await self._semantic_lookup(intent, prompt, model_id)
            if l2_result.hit:
                latency_ms = (time.perf_counter() - start_time) * 1000
                self.stats["l2_hits"] += 1
                self._update_hit_latency(latency_ms)
                return l2_result

            # L3: Check negative cache (known failures)
            neg_key = f"neg:{hashlib.md5(prompt.encode()).hexdigest()[:12]}"
            if self.redis_client.get(neg_key):
                latency_ms = (time.perf_counter() - start_time) * 1000
                self.stats["negative_hits"] += 1
                self._update_hit_latency(latency_ms)

                logger.info("Negative cache HIT", intent=intent, prompt=prompt[:30])
                return CacheResult(
                    True,
                    self._get_negative_response(intent),
                    "negative_cache",
                    "negative",
                    latency_ms,
                )

            # Cache MISS
            latency_ms = (time.perf_counter() - start_time) * 1000
            self.stats["misses"] += 1
            self._update_miss_latency(latency_ms)

            logger.info(
                "Cache MISS",
                intent=intent,
                prompt=prompt[:30],
                l1_key=l1_key[:20],
                latency_ms=latency_ms,
            )

            return CacheResult(False, reason="no_match", latency_ms=latency_ms)

        except Exception as e:
            self.stats["errors"] += 1
            logger.error("Cache lookup failed", error=str(e))
            return CacheResult(False, reason=f"error: {e}")

    async def _semantic_lookup(
        self, intent: str, prompt: str, model_id: str
    ) -> CacheResult:
        """Semantic similarity search in L2 cache"""

        try:
            canonical = canonical_prompt(prompt)

            # Search for similar prompts in same intent category
            pattern = f"l2:{intent}:*"
            keys = self.redis_client.keys(pattern)

            if not keys:
                return CacheResult(False, reason="no_l2_candidates")

            # Simple similarity check (could be improved with embeddings)
            best_similarity = 0.0
            best_key = None
            best_data = None

            for key in keys[:10]:  # Limit search to prevent slowdown
                cached_item = self.redis_client.hgetall(key)
                if not cached_item:
                    continue

                cached_prompt = cached_item.get("canonical_prompt", "")
                similarity = self._calculate_similarity(canonical, cached_prompt)

                if (
                    similarity > best_similarity
                    and similarity >= self.semantic_threshold
                ):
                    best_similarity = similarity
                    best_key = key
                    best_data = json.loads(cached_item.get("response", "{}"))

            if best_data:
                logger.info(
                    "L2 semantic HIT",
                    similarity=best_similarity,
                    threshold=self.semantic_threshold,
                    key=best_key[-20:],
                )

                return CacheResult(
                    True, best_data, f"semantic_match_{best_similarity:.2f}", "l2"
                )

            return CacheResult(False, reason="semantic_threshold_not_met")

        except Exception as e:
            logger.warn("Semantic lookup failed", error=str(e))
            return CacheResult(False, reason=f"semantic_error: {e}")

    def set(
        self,
        intent: str,
        prompt: str,
        response: Dict[str, Any],
        model_id: str = "qwen2.5:3b",
        schema_version: str = "v4",
        ttl: int = 300,
    ):
        """Store in multi-tier cache with telemetry"""

        if not self.redis_client:
            return

        try:
            # L1: Exact canonical key
            l1_key = build_cache_key(intent, prompt, [], schema_version, model_id)
            self.redis_client.setex(f"l1:{l1_key}", ttl, json.dumps(response))

            # L2: Semantic searchable format
            l2_key = f"l2:{intent}:{hashlib.md5(prompt.encode()).hexdigest()[:12]}"
            l2_data = {
                "canonical_prompt": canonical_prompt(prompt),
                "original_prompt": prompt,
                "response": json.dumps(response),
                "intent": intent,
                "model_id": model_id,
                "timestamp": time.time(),
                "schema_version": schema_version,
            }

            self.redis_client.hset(l2_key, mapping=l2_data)
            self.redis_client.expire(l2_key, ttl)

            logger.info(
                "Cache SET",
                intent=intent,
                l1_key=l1_key[:20],
                l2_key=l2_key[-20:],
                ttl=ttl,
            )

        except Exception as e:
            logger.error("Cache set failed", error=str(e))

    def set_negative(self, prompt: str, intent: str = "unknown", ttl: int = 60):
        """Store negative cache entry for failed/rejected requests"""

        if not self.redis_client:
            return

        try:
            neg_key = f"neg:{hashlib.md5(prompt.encode()).hexdigest()[:12]}"
            self.redis_client.setex(neg_key, ttl, intent)

            logger.info(
                "Negative cache SET", prompt=prompt[:30], intent=intent, ttl=ttl
            )

        except Exception as e:
            logger.error("Negative cache set failed", error=str(e))

    def _calculate_similarity(self, text1: str, text2: str) -> float:
        """Simple Jaccard similarity for text comparison"""

        words1 = set(text1.lower().split())
        words2 = set(text2.lower().split())

        if not words1 and not words2:
            return 1.0
        if not words1 or not words2:
            return 0.0

        intersection = words1.intersection(words2)
        union = words1.union(words2)

        return len(intersection) / len(union)

    def _get_negative_response(self, intent: str) -> Dict[str, Any]:
        """Generate standard negative response"""

        return {
            "intent": "negative",
            "tool": None,
            "args": {},
            "render_instruction": {
                "type": "text",
                "content": "Ursäkta, jag kan inte hjälpa med den frågan just nu.",
            },
            "meta": {"version": "4.0", "source": "negative_cache", "schema_ok": True},
        }

    def _update_hit_latency(self, latency_ms: float):
        """Update hit latency statistics"""
        total_hits = (
            self.stats["l1_hits"] + self.stats["l2_hits"] + self.stats["negative_hits"]
        )
        if total_hits > 1:
            self.stats["avg_hit_latency_ms"] = (
                self.stats["avg_hit_latency_ms"] * (total_hits - 1) + latency_ms
            ) / total_hits
        else:
            self.stats["avg_hit_latency_ms"] = latency_ms

    def _update_miss_latency(self, latency_ms: float):
        """Update miss latency statistics"""
        if self.stats["misses"] > 1:
            self.stats["avg_miss_latency_ms"] = (
                self.stats["avg_miss_latency_ms"] * (self.stats["misses"] - 1)
                + latency_ms
            ) / self.stats["misses"]
        else:
            self.stats["avg_miss_latency_ms"] = latency_ms

    def get_stats(self) -> Dict[str, Any]:
        """Get comprehensive cache statistics"""

        total = self.stats["total_requests"]
        hit_rate = 0.0
        if total > 0:
            hits = (
                self.stats["l1_hits"]
                + self.stats["l2_hits"]
                + self.stats["negative_hits"]
            )
            hit_rate = hits / total

        return {
            **self.stats,
            "hit_rate": hit_rate,
            "l1_hit_rate": self.stats["l1_hits"] / total if total > 0 else 0.0,
            "l2_hit_rate": self.stats["l2_hits"] / total if total > 0 else 0.0,
            "miss_rate": self.stats["misses"] / total if total > 0 else 0.0,
            "error_rate": self.stats["errors"] / total if total > 0 else 0.0,
            "semantic_threshold": self.semantic_threshold,
        }

    def clear_stats(self):
        """Reset statistics counters"""
        for key in self.stats.keys():
            if isinstance(self.stats[key], (int, float)):
                self.stats[key] = 0


# Global cache instance
_smart_cache: Optional[SmartCache] = None


def get_smart_cache() -> SmartCache:
    """Get or create global smart cache instance"""
    global _smart_cache
    if _smart_cache is None:
        _smart_cache = SmartCache()
    return _smart_cache
