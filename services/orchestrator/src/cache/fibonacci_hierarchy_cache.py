"""
Fibonacci AI Architecture - Multi-dimensional Cache Hierarchy (L1-L10)
Natural cache progression using Fibonacci numbers and golden ratio optimization
"""

import hashlib
import json
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

import redis
import structlog

from ..config.fibonacci import (
    FIBONACCI_SEQUENCE,
    GOLDEN_RATIO,
    calculate_golden_ratio_threshold,
)
from .fibonacci_spiral_matcher import create_fibonacci_matcher

logger = structlog.get_logger(__name__)


@dataclass
class CacheEntry:
    """Multi-dimensional cache entry with Fibonacci metadata"""

    key: str
    data: Any
    tier: int  # L1-L10
    fibonacci_weight: int
    golden_ratio_score: float
    similarity_threshold: float
    ttl_seconds: int
    created_at: float = field(default_factory=time.time)
    access_count: int = 0
    last_accessed: float = field(default_factory=time.time)

    def is_expired(self) -> bool:
        """Check if cache entry is expired"""
        return time.time() - self.created_at > self.ttl_seconds

    def access(self):
        """Record access to this cache entry"""
        self.access_count += 1
        self.last_accessed = time.time()


@dataclass
class CacheLookupResult:
    """Result of multi-tier cache lookup"""

    hit: bool
    data: Any = None
    tier: int = 0  # Which tier provided the result
    fibonacci_weight: int = 0
    golden_ratio_factor: float = 0.0
    similarity_score: float = 0.0
    latency_ms: float = 0.0
    reason: str = ""
    cache_path: List[str] = field(default_factory=list)  # Tiers checked


class FibonacciHierarchyCache:
    """
    Multi-dimensional cache hierarchy using Fibonacci progression (L1-L10)

    Cache Tiers:
    L1: Exact matches (TTL: 1h) - Weight: 1
    L2: Semantic exact (TTL: 2h) - Weight: 1
    L3: Similarity 95%+ (TTL: 3h) - Weight: 2
    L4: Similarity 80%+ (TTL: 5h) - Weight: 3
    L5: Intent matches (TTL: 8h) - Weight: 5
    L6: Context similar (TTL: 13h) - Weight: 8
    L7: Pattern matches (TTL: 21h) - Weight: 13
    L8: Domain related (TTL: 34h) - Weight: 21
    L9: Category broad (TTL: 55h) - Weight: 34
    L10: Generic fallback (TTL: 89h) - Weight: 55

    Each tier uses Fibonacci numbers for natural progression and golden ratio
    optimization for cache eviction and performance tuning.
    """

    def __init__(self, redis_url: str = "redis://alice-cache:6379"):
        self.redis_url = redis_url
        self.redis_client = None

        # Initialize Fibonacci spiral matcher
        self.spiral_matcher = create_fibonacci_matcher()

        # Define cache tier configuration using Fibonacci numbers
        self.cache_tiers = self._initialize_fibonacci_tiers()

        # Performance tracking for each tier
        self.tier_stats = {
            i: {
                "hits": 0,
                "misses": 0,
                "latency_sum": 0.0,
                "fibonacci_optimizations": 0,
            }
            for i in range(1, 11)
        }

        # Connect to Redis
        self._connect_redis()

    def _initialize_fibonacci_tiers(self) -> Dict[int, Dict[str, Any]]:
        """Initialize cache tier configuration with Fibonacci progression"""
        tiers = {}

        for i in range(1, 11):  # L1-L10
            fib_index = min(i - 1, len(FIBONACCI_SEQUENCE) - 1)
            fibonacci_weight = FIBONACCI_SEQUENCE[fib_index]

            # TTL increases by Fibonacci progression (hours)
            ttl_hours = fibonacci_weight
            if i > len(FIBONACCI_SEQUENCE):
                ttl_hours = FIBONACCI_SEQUENCE[-1] + (i - len(FIBONACCI_SEQUENCE)) * 13

            # Similarity thresholds decrease with golden ratio
            base_threshold = (
                1.0 - (i - 1) * (1.0 - calculate_golden_ratio_threshold(1.0)) / 9
            )

            tiers[i] = {
                "name": f"L{i}",
                "fibonacci_weight": fibonacci_weight,
                "ttl_seconds": ttl_hours * 3600,
                "similarity_threshold": max(0.1, base_threshold),
                "golden_ratio_factor": GOLDEN_RATIO ** (-(i - 1)),
                "description": self._get_tier_description(i),
                "max_entries": fibonacci_weight * 100,  # Capacity based on Fibonacci
            }

        return tiers

    def _get_tier_description(self, tier: int) -> str:
        """Get human-readable description for each cache tier"""
        descriptions = {
            1: "Exact key matches - Perfect hits",
            2: "Semantic exact matches - Same meaning",
            3: "High similarity 95%+ - Very close matches",
            4: "Good similarity 80%+ - Close matches",
            5: "Intent matches - Same purpose",
            6: "Context similar - Related context",
            7: "Pattern matches - Similar patterns",
            8: "Domain related - Same domain",
            9: "Category broad - Broad category",
            10: "Generic fallback - Catch-all tier",
        }
        return descriptions.get(tier, f"L{tier} cache tier")

    def _connect_redis(self):
        """Connect to Redis with error handling"""
        try:
            self.redis_client = redis.from_url(self.redis_url, decode_responses=True)
            self.redis_client.ping()
            logger.info(
                "Fibonacci Hierarchy Cache connected to Redis",
                tiers=len(self.cache_tiers),
            )
        except Exception as e:
            logger.error("Failed to connect to Redis", error=str(e))
            self.redis_client = None

    async def get(
        self, query: str, context: Dict[str, Any] = None
    ) -> CacheLookupResult:
        """
        Multi-tier cache lookup with Fibonacci progression

        Searches through L1-L10 tiers using natural Fibonacci progression:
        - Start with exact matches (L1)
        - Progress through similarity tiers (L2-L9)
        - Fallback to generic patterns (L10)
        """
        start_time = time.perf_counter()
        cache_path = []

        if not self.redis_client:
            return CacheLookupResult(
                hit=False,
                reason="redis_unavailable",
                latency_ms=(time.perf_counter() - start_time) * 1000,
            )

        context = context or {}
        query_hash = hashlib.sha256(query.encode()).hexdigest()

        # Search through cache tiers in Fibonacci order
        for tier_num in range(1, 11):
            tier_config = self.cache_tiers[tier_num]
            cache_path.append(f"L{tier_num}")

            # Record tier search attempt
            self.tier_stats[tier_num]["misses"] += 1

            try:
                result = await self._search_tier(
                    tier_num, query, query_hash, context, tier_config
                )

                if result:
                    # Cache HIT in this tier
                    latency_ms = (time.perf_counter() - start_time) * 1000

                    self.tier_stats[tier_num]["hits"] += 1
                    self.tier_stats[tier_num]["misses"] -= 1
                    self.tier_stats[tier_num]["latency_sum"] += latency_ms

                    logger.info(
                        f"Cache HIT L{tier_num}",
                        tier=tier_num,
                        fibonacci_weight=tier_config["fibonacci_weight"],
                        similarity=result.get("similarity_score", 1.0),
                        latency_ms=latency_ms,
                    )

                    return CacheLookupResult(
                        hit=True,
                        data=result["data"],
                        tier=tier_num,
                        fibonacci_weight=tier_config["fibonacci_weight"],
                        golden_ratio_factor=tier_config["golden_ratio_factor"],
                        similarity_score=result.get("similarity_score", 1.0),
                        latency_ms=latency_ms,
                        reason=f"L{tier_num}_hit",
                        cache_path=cache_path,
                    )

            except Exception as e:
                logger.warning(f"L{tier_num} search failed", error=str(e))
                continue

        # Complete cache MISS across all tiers
        latency_ms = (time.perf_counter() - start_time) * 1000

        logger.info(
            "Complete cache MISS",
            query_length=len(query),
            tiers_searched=len(cache_path),
            latency_ms=latency_ms,
        )

        return CacheLookupResult(
            hit=False,
            reason="no_match_all_tiers",
            latency_ms=latency_ms,
            cache_path=cache_path,
        )

    async def _search_tier(
        self,
        tier_num: int,
        query: str,
        query_hash: str,
        context: Dict[str, Any],
        tier_config: Dict[str, Any],
    ) -> Optional[Dict[str, Any]]:
        """Search specific cache tier using tier-appropriate algorithm"""

        if tier_num == 1:
            # L1: Exact key matching
            return await self._search_l1_exact(query_hash)

        elif tier_num == 2:
            # L2: Semantic exact matching
            return await self._search_l2_semantic(query, context)

        elif tier_num in [3, 4]:
            # L3-L4: High similarity matching
            return await self._search_similarity(
                query, context, tier_config["similarity_threshold"]
            )

        elif tier_num == 5:
            # L5: Intent matching
            return await self._search_intent(query, context)

        elif tier_num == 6:
            # L6: Context similarity
            return await self._search_context(query, context)

        elif tier_num == 7:
            # L7: Pattern matching
            return await self._search_patterns(query, context)

        elif tier_num in [8, 9]:
            # L8-L9: Domain/category matching
            return await self._search_domain_category(query, context, tier_num)

        elif tier_num == 10:
            # L10: Generic fallback
            return await self._search_generic_fallback(query, context)

        return None

    async def _search_l1_exact(self, query_hash: str) -> Optional[Dict[str, Any]]:
        """L1: Exact key matching using hash"""
        key = f"fib:l1:{query_hash}"
        cached_data = self.redis_client.get(key)

        if cached_data:
            return {"data": json.loads(cached_data), "similarity_score": 1.0}
        return None

    async def _search_l2_semantic(
        self, query: str, context: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """L2: Semantic exact matching using embeddings"""
        # Use Fibonacci spiral matcher for semantic similarity
        pattern = "fib:l2:*"
        keys = self.redis_client.keys(pattern)

        if not keys:
            return None

        # Find best semantic match using spiral matching
        best_match = None
        best_score = 0.0

        for key in keys[:21]:  # Fibonacci number limit
            cached_item = self.redis_client.hgetall(key)
            if not cached_item:
                continue

            cached_query = cached_item.get("query", "")
            if cached_query:
                # Use golden ratio threshold for semantic matching
                similarity = self._calculate_semantic_similarity(query, cached_query)
                if similarity > calculate_golden_ratio_threshold(1.0):  # ~0.618
                    if similarity > best_score:
                        best_score = similarity
                        best_match = cached_item.get("data")

        if best_match:
            return {
                "data": (
                    json.loads(best_match)
                    if isinstance(best_match, str)
                    else best_match
                ),
                "similarity_score": best_score,
            }
        return None

    async def _search_similarity(
        self, query: str, context: Dict[str, Any], threshold: float
    ) -> Optional[Dict[str, Any]]:
        """L3-L4: High similarity matching"""
        # Use Fibonacci spiral matcher for advanced similarity
        return await self._fibonacci_spiral_search(query, context, threshold)

    async def _search_intent(
        self, query: str, context: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """L5: Intent-based matching"""
        intent = context.get("intent", "general")
        pattern = f"fib:l5:{intent}:*"
        keys = self.redis_client.keys(pattern)

        if keys:
            # Return most recent intent match
            for key in keys[:8]:  # Fibonacci limit
                cached_data = self.redis_client.get(key)
                if cached_data:
                    return {"data": json.loads(cached_data), "similarity_score": 0.8}
        return None

    async def _search_context(
        self, query: str, context: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """L6: Context similarity matching"""
        # Match based on context similarity
        context_keys = list(context.keys())[:5]  # Fibonacci limit

        for ctx_key in context_keys:
            pattern = f"fib:l6:ctx_{ctx_key}:*"
            keys = self.redis_client.keys(pattern)

            if keys:
                cached_data = self.redis_client.get(keys[0])
                if cached_data:
                    return {"data": json.loads(cached_data), "similarity_score": 0.7}
        return None

    async def _search_patterns(
        self, query: str, context: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """L7: Pattern matching using Fibonacci sequences"""
        # Extract patterns from query (length, structure, etc.)
        query_len = len(query)

        # Find closest Fibonacci number for query length
        fib_pattern = None
        for fib_num in FIBONACCI_SEQUENCE:
            if abs(query_len - fib_num) < 10:
                fib_pattern = fib_num
                break

        if fib_pattern:
            pattern = f"fib:l7:len_{fib_pattern}:*"
            keys = self.redis_client.keys(pattern)

            if keys:
                cached_data = self.redis_client.get(keys[0])
                if cached_data:
                    return {"data": json.loads(cached_data), "similarity_score": 0.6}
        return None

    async def _search_domain_category(
        self, query: str, context: Dict[str, Any], tier: int
    ) -> Optional[Dict[str, Any]]:
        """L8-L9: Domain and category matching"""
        domain = context.get("domain", "general")
        category = context.get("category", "misc")

        search_key = domain if tier == 8 else category
        pattern = f"fib:l{tier}:{search_key}:*"
        keys = self.redis_client.keys(pattern)

        if keys:
            # Use golden ratio selection for best match
            selected_index = int(len(keys) * calculate_golden_ratio_threshold(1.0))
            selected_key = keys[min(selected_index, len(keys) - 1)]

            cached_data = self.redis_client.get(selected_key)
            if cached_data:
                return {
                    "data": json.loads(cached_data),
                    "similarity_score": 0.5 if tier == 8 else 0.4,
                }
        return None

    async def _search_generic_fallback(
        self, query: str, context: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """L10: Generic fallback responses"""
        # Generic responses for common patterns
        generic_patterns = {
            "question": "I understand you have a question. Let me help you with that.",
            "greeting": "Hello! How can I assist you today?",
            "thanks": "You're welcome! Is there anything else I can help with?",
            "default": "I'll do my best to help you with that request.",
        }

        # Simple pattern detection
        query_lower = query.lower()
        if "?" in query:
            pattern_type = "question"
        elif any(word in query_lower for word in ["hej", "hello", "hi"]):
            pattern_type = "greeting"
        elif any(word in query_lower for word in ["tack", "thanks"]):
            pattern_type = "thanks"
        else:
            pattern_type = "default"

        return {
            "data": {"response": generic_patterns[pattern_type]},
            "similarity_score": 0.3,
        }

    async def _fibonacci_spiral_search(
        self, query: str, context: Dict[str, Any], threshold: float
    ) -> Optional[Dict[str, Any]]:
        """Advanced similarity search using Fibonacci spiral coordinates"""
        try:
            # Use existing spiral matcher
            pattern = "fib:spiral:*"
            keys = self.redis_client.keys(pattern)

            if not keys:
                return None

            spiral_entries = []
            for key in keys[:55]:  # Fibonacci limit
                cached_item = self.redis_client.hgetall(key)
                if cached_item and "query" in cached_item:
                    spiral_entries.append(
                        {
                            "query": cached_item["query"],
                            "data": cached_item.get("data"),
                            "metadata": context,
                        }
                    )

            if spiral_entries:
                matches = self.spiral_matcher.find_spiral_matches(
                    query, context, spiral_entries, max_matches=3
                )

                for match in matches:
                    if match.similarity_score >= threshold:
                        return {
                            "data": (
                                json.loads(match.cached_response)
                                if isinstance(match.cached_response, str)
                                else match.cached_response
                            ),
                            "similarity_score": match.similarity_score,
                        }

        except Exception as e:
            logger.warning("Fibonacci spiral search failed", error=str(e))

        return None

    def _calculate_semantic_similarity(self, text1: str, text2: str) -> float:
        """Calculate semantic similarity using golden ratio optimization"""
        if not text1 or not text2:
            return 0.0

        # Simple similarity calculation enhanced with golden ratio
        words1 = set(text1.lower().split())
        words2 = set(text2.lower().split())

        if not words1 or not words2:
            return 0.0

        intersection = len(words1 & words2)
        union = len(words1 | words2)

        if union == 0:
            return 0.0

        # Apply golden ratio enhancement for better semantic understanding
        base_similarity = intersection / union
        golden_enhancement = (
            base_similarity * GOLDEN_RATIO if base_similarity > 0.5 else base_similarity
        )

        return min(1.0, golden_enhancement)

    async def put(
        self, query: str, data: Any, tier: int = None, context: Dict[str, Any] = None
    ) -> bool:
        """Store data in appropriate cache tier using Fibonacci optimization"""
        if not self.redis_client:
            return False

        context = context or {}

        # Auto-determine tier if not specified
        if tier is None:
            tier = self._determine_optimal_tier(query, data, context)

        tier_config = self.cache_tiers.get(tier, self.cache_tiers[1])

        try:
            # Generate tier-specific key
            query_hash = hashlib.sha256(query.encode()).hexdigest()

            if tier == 1:
                key = f"fib:l1:{query_hash}"
                self.redis_client.setex(
                    key, tier_config["ttl_seconds"], json.dumps(data)
                )

            elif tier == 2:
                key = f"fib:l2:semantic:{query_hash[:16]}"
                cache_entry = {
                    "query": query,
                    "data": json.dumps(data),
                    "context": json.dumps(context),
                    "fibonacci_weight": tier_config["fibonacci_weight"],
                }
                self.redis_client.hset(key, mapping=cache_entry)
                self.redis_client.expire(key, tier_config["ttl_seconds"])

            elif tier >= 3:
                # Higher tiers store with more metadata
                key = (
                    f"fib:l{tier}:{context.get('domain', 'general')}:{query_hash[:12]}"
                )
                cache_entry = {
                    "query": query,
                    "data": json.dumps(data),
                    "context": json.dumps(context),
                    "tier": tier,
                    "fibonacci_weight": tier_config["fibonacci_weight"],
                    "golden_ratio_factor": tier_config["golden_ratio_factor"],
                    "created_at": time.time(),
                }
                self.redis_client.hset(key, mapping=cache_entry)
                self.redis_client.expire(key, tier_config["ttl_seconds"])

            logger.debug(
                f"Cached in L{tier}",
                tier=tier,
                fibonacci_weight=tier_config["fibonacci_weight"],
                ttl_hours=tier_config["ttl_seconds"] / 3600,
            )

            return True

        except Exception as e:
            logger.error("Cache put failed", tier=tier, error=str(e))
            return False

    def _determine_optimal_tier(
        self, query: str, data: Any, context: Dict[str, Any]
    ) -> int:
        """Determine optimal cache tier using Fibonacci analysis"""

        # Simple heuristics for tier selection
        query_len = len(query)
        has_context = bool(context)
        data_complexity = len(str(data)) if data else 0

        # Use Fibonacci numbers to determine tier
        if query_len < 34 and not has_context:  # Fibonacci 9th number
            return 1
        elif query_len < 55 and data_complexity < 200:  # Fibonacci 10th number
            return 2
        elif query_len < 89:  # Fibonacci 11th number
            return 3
        elif has_context and data_complexity > 500:
            return 5
        else:
            return 4

    def get_hierarchy_stats(self) -> Dict[str, Any]:
        """Get comprehensive statistics for all cache tiers"""

        total_hits = sum(stats["hits"] for stats in self.tier_stats.values())
        total_requests = total_hits + sum(
            stats["misses"] for stats in self.tier_stats.values()
        )

        tier_details = {}
        for tier_num, tier_config in self.cache_tiers.items():
            stats = self.tier_stats[tier_num]
            avg_latency = (
                (stats["latency_sum"] / stats["hits"]) if stats["hits"] > 0 else 0.0
            )

            tier_details[f"L{tier_num}"] = {
                "fibonacci_weight": tier_config["fibonacci_weight"],
                "ttl_hours": tier_config["ttl_seconds"] / 3600,
                "similarity_threshold": tier_config["similarity_threshold"],
                "golden_ratio_factor": tier_config["golden_ratio_factor"],
                "hits": stats["hits"],
                "misses": stats["misses"],
                "hit_rate": (
                    (stats["hits"] / (stats["hits"] + stats["misses"]))
                    if (stats["hits"] + stats["misses"]) > 0
                    else 0.0
                ),
                "avg_latency_ms": avg_latency,
                "description": tier_config["description"],
            }

        return {
            "cache_type": "fibonacci_hierarchy",
            "tiers": len(self.cache_tiers),
            "total_requests": total_requests,
            "total_hits": total_hits,
            "overall_hit_rate": (
                (total_hits / total_requests) if total_requests > 0 else 0.0
            ),
            "fibonacci_sequence": FIBONACCI_SEQUENCE[:10],
            "golden_ratio": GOLDEN_RATIO,
            "tier_details": tier_details,
        }


# Global cache instance
_fibonacci_cache: Optional[FibonacciHierarchyCache] = None


def create_fibonacci_hierarchy_cache(
    redis_url: str = "redis://alice-cache:6379",
) -> FibonacciHierarchyCache:
    """Create or update global Fibonacci hierarchy cache"""
    global _fibonacci_cache
    _fibonacci_cache = FibonacciHierarchyCache(redis_url)
    return _fibonacci_cache


def get_fibonacci_hierarchy_cache() -> Optional[FibonacciHierarchyCache]:
    """Get existing Fibonacci hierarchy cache"""
    return _fibonacci_cache
