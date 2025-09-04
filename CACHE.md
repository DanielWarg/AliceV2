# Alice v2 Cache System

_Robust semantic cache with deterministic fingerprinting and intent-aware caching_

## 🎯 Overview

The Alice v2 cache system provides intelligent caching for planner responses with:

- **Deterministic fingerprinting** - Same input → same cache key
- **Intent-aware caching** - Prevents cross-contamination between intents
- **Versioned invalidation** - Safe cache clearing for schema/deps updates
- **PII/size protection** - Automatic filtering and size limits
- **Real-time telemetry** - Hit/miss/save_ms/stale_prevented metrics

**🚀 CURRENT STATUS**: Cache system implemented but experiencing ~90% miss rate. Optimization in progress with micro_key canonicalization and negative cache implementation.

## 🏗️ Architecture

```
Cache Request Flow:
1. Classifier → Intent + Level
2. Build fingerprint (intent + schema + deps + context)
3. Cache lookup (Redis key: sc:v1:schema:deps:intent:fp24)
4. HIT → Return cached response
5. MISS → Run planner, validate, cache (EASY/MEDIUM only)
6. Intent drift → Prevent stale write
```

## 📋 Key Components

### 1. Deterministic Fingerprint (`key_builder.py`)

```python
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
    # Normalized, canonical JSON → SHA256
```

**Features:**

- Fixed field order for 100% determinism
- Intent-aware (different intents → different hashes)
- Context normalization (sorted, deduplicated)
- Time-bucket support for time-sensitive intents

### 2. Versioned Redis Keys (`models.py`)

```python
class CacheKey(BaseModel):
    fingerprint: str
    intent: str
    schema_version: str
    deps_version: str

    def redis_key(self) -> str:
        return f"sc:v1:{self.schema_version}:{self.deps_version}:{self.intent}:{self.fingerprint[:24]}"
```

**Benefits:**

- Namespace isolation (`sc:v1`)
- Schema version separation
- Intent-specific invalidation
- Short fingerprint (24 chars) for key length

### 3. Semantic Cache Decorator (`decorators.py`)

```python
@semantic_cache(store, settings)
async def plan(*, prompt_core, context_facts, classifier, ...) -> dict:
    # Intent-aware cache with guards
```

**Guards:**

- Intent drift detection (prevent stale writes)
- Size limits (max 128KB response)
- Level gating (EASY/MEDIUM only)
- Schema validation (schema_ok=true required)

### 4. Redis Store (`redis_store.py`)

```python
class RedisCacheStore(ICacheStore):
    async def invalidate(self, intent: Optional[str] = None,
                        schema_version: Optional[str] = None,
                        deps_version: Optional[str] = None) -> int:
        # Efficient pattern-based invalidation
```

**Features:**

- Async Redis operations
- Pattern-based invalidation
- Batch delete support
- Connection pooling

## 🔧 Configuration

### Environment Variables

```bash
CACHE_ENABLED=1                    # Enable/disable cache
REDIS_URL=redis://alice-cache:6379 # Redis connection
```

### TTL by Level

```python
TTL_BY_LEVEL = {
    "easy": 3600,    # 1 hour
    "medium": 1800,  # 30 minutes
    "hard": 300,     # 5 minutes (minimal)
}
```

### Size Limits

```python
MAX_RESPONSE_SIZE_KB = 128  # Max response size
MAX_EVIDENCE_SIZE_KB = 64   # Max evidence size
```

### PII Patterns

```python
PII_PATTERNS = [
    r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',  # email
    r'\b\d{10,12}\b',  # phone numbers
    r'\b\d{4}-\d{2}-\d{2}\b',  # dates
]
```

## 📊 Telemetry

### Metrics

- `cache_hit_total{intent,level}` - Cache hits per intent/level
- `cache_miss_total{intent,level}` - Cache misses per intent/level
- `cache_stale_prevented_total` - Stale writes prevented
- `cache_save_duration_seconds{intent,level}` - Save performance

### Monitoring

```bash
# View cache metrics in HUD
open http://localhost:3001

# Check Redis keys
redis-cli -h localhost -p 6379 KEYS "sc:v1:*"

# Invalidate specific intent
curl -X POST http://localhost:18000/api/cache/invalidate \
  -H 'Content-Type: application/json' \
  -d '{"intent": "weather.lookup"}'
```

## 🧪 Testing

### Unit Tests

```bash
# Run cache tests
python3 test_cache.py
```

**Test Coverage:**

- ✅ Deterministic fingerprinting
- ✅ Intent-aware key generation
- ✅ Redis store operations
- ✅ Cache metrics

### Integration Tests

```bash
# Test with Redis
docker compose up alice-cache
python3 test_cache.py

# Validate cache hit rate
make test-all
# Check HUD for cache metrics
```

## 🚀 Usage

### Basic Integration

```python
from services.cache.src import semantic_cache, RedisCacheStore

store = RedisCacheStore("redis://localhost:6379")

@semantic_cache(store, {})
async def plan(*, prompt_core, context_facts, classifier, ...):
    # Your planning logic here
    return response
```

### Cache Invalidation

```python
# Invalidate by intent
await store.invalidate(intent="weather.lookup")

# Invalidate by schema version
await store.invalidate(schema_version="4.1")

# Invalidate all
await store.invalidate()
```

## 🔒 Security & Safety

### PII Protection

- Automatic email/phone/date filtering
- Evidence sanitization
- No PII in cache keys

### Size Protection

- Response size limits (128KB)
- Evidence size limits (64KB)
- Automatic rejection of oversized entries

### Intent Safety

- Intent drift detection
- Cross-contamination prevention
- Stale write blocking

## 📈 Performance

### Expected Hit Rates

- **EASY**: 80-90% (stable intents)
- **MEDIUM**: 60-80% (moderate complexity)
- **HARD**: 0-20% (minimal caching)

### Latency Impact

- **Cache hit**: ~5-10ms (Redis lookup)
- **Cache miss**: ~50-100ms (save operation)
- **Overall**: 20-40% latency reduction for cached responses

## 🔄 Migration & Versioning

### Schema Updates

```python
# Bump namespace for clean cutover
CACHE_NS = "sc:v2"  # New schema version

# Old keys remain accessible
# New requests use new namespace
```

### Intent Changes

```python
# Invalidate specific intent
await store.invalidate(intent="old.intent")

# New intent gets fresh cache space
```

## 🐛 Troubleshooting

### Common Issues

1. **Low hit rate**: Check intent classification accuracy
2. **Stale responses**: Verify intent drift detection
3. **Redis connection**: Check `REDIS_URL` and network
4. **Size limits**: Review response/evidence sizes

### Debug Commands

```bash
# Check Redis health
redis-cli -h localhost -p 6379 ping

# View cache keys
redis-cli -h localhost -p 6379 KEYS "sc:v1:*"

# Monitor cache operations
redis-cli -h localhost -p 6379 MONITOR
```

## 📚 References

- **ROADMAP.md**: Step 8.5 implementation details
- **test_cache.py**: Comprehensive test suite
- **services/cache/src/**: Source code
- **HUD**: Real-time metrics visualization
