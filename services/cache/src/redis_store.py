import json
from typing import Optional

import redis.asyncio as redis

from models import CACHE_NS, CacheEntry, CacheKey


class ICacheStore:
    async def get(self, key: CacheKey) -> Optional[CacheEntry]:
        raise NotImplementedError

    async def set(self, key: CacheKey, entry: CacheEntry) -> None:
        raise NotImplementedError

    async def invalidate(
        self,
        intent: Optional[str] = None,
        schema_version: Optional[str] = None,
        deps_version: Optional[str] = None,
    ) -> int:
        raise NotImplementedError


class RedisCacheStore(ICacheStore):
    def __init__(self, url: str):
        self.cli = redis.from_url(url, decode_responses=True)

    async def get(self, key: CacheKey) -> Optional[CacheEntry]:
        data = await self.cli.get(key.redis_key())
        return CacheEntry(**json.loads(data)) if data else None

    async def set(self, key: CacheKey, entry: CacheEntry) -> None:
        await self.cli.setex(
            key.redis_key(), entry.ttl_sec, json.dumps(entry.dict(), ensure_ascii=False)
        )

    async def invalidate(
        self,
        intent: Optional[str] = None,
        schema_version: Optional[str] = None,
        deps_version: Optional[str] = None,
    ) -> int:
        # Begränsa scan till rätt namespace
        pattern = f"{CACHE_NS}:{schema_version or '*'}:{deps_version or '*'}:{intent or '*'}:*"
        n = 0
        async for k in self._scan_iter(pattern):
            n += 1
            # batch delete kan göras också
            await self.cli.delete(k)
        return n

    async def _scan_iter(self, match: str, count: int = 500):
        cursor = 0
        while True:
            cursor, keys = await self.cli.scan(cursor=cursor, match=match, count=count)
            for k in keys:
                yield k
            if cursor == 0:
                break
