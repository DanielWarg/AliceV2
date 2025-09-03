import os
from typing import Dict, Any, Optional
from services.cache.src import semantic_cache, RedisCacheStore
from ..llm.planner_classifier import ClassificationResult


class CacheIntegration:
    def __init__(self):
        self.enabled = os.getenv("CACHE_ENABLED", "0") == "1"
        self.store = None
        if self.enabled:
            redis_url = os.getenv("REDIS_URL", "redis://localhost:6379")
            self.store = RedisCacheStore(redis_url)
    
    def get_cache_decorator(self):
        """Return cache decorator if enabled, otherwise no-op decorator"""
        if not self.enabled or not self.store:
            return lambda store, settings: lambda func: func
        
        return semantic_cache(self.store, {})
    
    async def invalidate_intent(self, intent: str) -> int:
        """Invalidate all cache entries for a specific intent"""
        if not self.enabled or not self.store:
            return 0
        return await self.store.invalidate(intent=intent)
    
    async def invalidate_schema_version(self, schema_version: str) -> int:
        """Invalidate all cache entries for a specific schema version"""
        if not self.enabled or not self.store:
            return 0
        return await self.store.invalidate(schema_version=schema_version)


# Global cache integration instance
cache_integration = CacheIntegration()


def get_cache_decorator():
    """Get the appropriate cache decorator based on configuration"""
    return cache_integration.get_cache_decorator()
