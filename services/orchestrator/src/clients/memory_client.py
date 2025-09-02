"""
Memory client for orchestrator to communicate with memory service
"""

import httpx
import structlog
from typing import Dict, List, Optional, Any
from datetime import datetime

logger = structlog.get_logger(__name__)

class MemoryClient:
    """Client for Alice Memory Service"""
    
    def __init__(self, base_url: str = "http://memory:8300"):
        self.base_url = base_url.rstrip("/")
        self.client = httpx.AsyncClient(timeout=30.0)
    
    async def store_memory(
        self,
        user_id: str,
        session_id: str,
        text: str,
        metadata: Optional[Dict[str, Any]] = None,
        consent_scopes: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """Store a memory chunk"""
        try:
            payload = {
                "user_id": user_id,
                "session_id": session_id,
                "text": text,
                "metadata": metadata or {},
                "consent_scopes": consent_scopes or ["basic_logging"]
            }
            
            response = await self.client.post(
                f"{self.base_url}/store",
                json=payload
            )
            response.raise_for_status()
            
            result = response.json()
            logger.info(
                "Memory stored successfully",
                user_id=user_id,
                session_id=session_id,
                chunk_id=result.get("chunk_id"),
                query_time_ms=result.get("query_time_ms")
            )
            
            return result
            
        except Exception as e:
            logger.error(
                "Failed to store memory",
                user_id=user_id,
                session_id=session_id,
                error=str(e)
            )
            raise
    
    async def query_memory(
        self,
        user_id: str,
        query: str,
        top_k: int = 3,
        min_score: float = 0.6
    ) -> Dict[str, Any]:
        """Query memory using semantic search"""
        try:
            payload = {
                "user_id": user_id,
                "query": query,
                "top_k": top_k,
                "min_score": min_score
            }
            
            response = await self.client.post(
                f"{self.base_url}/query",
                json=payload
            )
            response.raise_for_status()
            
            result = response.json()
            logger.info(
                "Memory query completed",
                user_id=user_id,
                query=query,
                total_hits=result.get("total_hits", 0),
                query_time_ms=result.get("query_time_ms")
            )
            
            return result
            
        except Exception as e:
            logger.error(
                "Failed to query memory",
                user_id=user_id,
                query=query,
                error=str(e)
            )
            raise
    
    async def forget_memory(
        self,
        user_id: str,
        session_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Forget user memory (GDPR compliance)"""
        try:
            payload = {
                "user_id": user_id
            }
            if session_id:
                payload["session_id"] = session_id
            
            response = await self.client.post(
                f"{self.base_url}/forget",
                json=payload
            )
            response.raise_for_status()
            
            result = response.json()
            logger.info(
                "Memory forgotten",
                user_id=user_id,
                session_id=session_id,
                deleted_count=result.get("deleted_count", 0),
                query_time_ms=result.get("query_time_ms")
            )
            
            return result
            
        except Exception as e:
            logger.error(
                "Failed to forget memory",
                user_id=user_id,
                session_id=session_id,
                error=str(e)
            )
            raise
    
    async def get_stats(self) -> Dict[str, Any]:
        """Get memory service statistics"""
        try:
            response = await self.client.get(f"{self.base_url}/stats")
            response.raise_for_status()
            
            result = response.json()
            logger.info(
                "Memory stats retrieved",
                total_chunks=result.get("total_chunks", 0),
                users=result.get("users", 0)
            )
            
            return result
            
        except Exception as e:
            logger.error("Failed to get memory stats", error=str(e))
            raise
    
    async def health_check(self) -> bool:
        """Check if memory service is healthy"""
        try:
            response = await self.client.get(f"{self.base_url}/health")
            response.raise_for_status()
            
            data = response.json()
            return data.get("status") == "healthy"
            
        except Exception as e:
            logger.error("Memory service health check failed", error=str(e))
            return False
    
    async def close(self):
        """Close the client"""
        await self.client.aclose()

# Global memory client instance
_memory_client: Optional[MemoryClient] = None

def get_memory_client() -> MemoryClient:
    """Get or create global memory client instance"""
    global _memory_client
    if _memory_client is None:
        _memory_client = MemoryClient()
    return _memory_client

def reset_memory_client():
    """Reset the global memory client instance (for testing)"""
    global _memory_client
    if _memory_client:
        _memory_client = None
