from prometheus_client import Counter, Histogram

# Cache hit/miss metrics
cache_hit = Counter("cache_hit_total", "Total cache hits", ["intent", "level"])

cache_miss = Counter("cache_miss_total", "Total cache misses", ["intent", "level"])

stale_prevented = Counter(
    "cache_stale_prevented_total", "Total stale writes prevented due to intent drift"
)

# Cache performance metrics
save_ms = Histogram(
    "cache_save_duration_seconds", "Time to save cache entry", ["intent", "level"]
)
