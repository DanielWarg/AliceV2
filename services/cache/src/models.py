from pydantic import BaseModel
from datetime import datetime
from typing import Optional, Any, Dict

CACHE_NS = "sc:v1"  # bumpa vid schema för key-space cutover


class CacheKey(BaseModel):
    fingerprint: str
    intent: str
    schema_version: str
    deps_version: str

    def redis_key(self) -> str:
        # Kort fingerprint för nyckellängd, men fullt i value
        return f"{CACHE_NS}:{self.schema_version}:{self.deps_version}:{self.intent}:{self.fingerprint[:24]}"


class CacheEntry(BaseModel):
    response: Dict[str, Any]
    evidence: Dict[str, Any]
    cached_at: datetime
    ttl_sec: int
