"""
Alice Memory Service
Redis TTL session storage + FAISS user memory with Swedish embeddings
"""

import os
import json
import time
import uuid
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Any
from pathlib import Path

import redis
import numpy as np
import structlog
from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from sentence_transformers import SentenceTransformer
import faiss

# Configure logging
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
        structlog.processors.JSONRenderer()
    ],
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    wrapper_class=structlog.stdlib.BoundLogger,
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger(__name__)

# Configuration
REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379")
MEMORY_TTL_DAYS = int(os.getenv("MEMORY_TTL_DAYS", "7"))
PERSONA_TTL_DAYS = int(os.getenv("PERSONA_TTL_DAYS", "90"))  # Longer TTL for persona
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2")
FAISS_INDEX_PATH = Path("/data/embeddings/user_memory.faiss")
MEMORY_DATA_PATH = Path("/data/embeddings/memory_data.json")
PERSONA_INDEX_PATH = Path("/data/embeddings/persona_memory.faiss")
EPISODES_INDEX_PATH = Path("/data/embeddings/episodes_memory.faiss")

# Memory namespaces
class MemoryNamespace(str):
    GENERAL = "general"      # Default memory
    PERSONA = "persona"      # User preferences, values, tone
    EPISODES = "episodes"    # Compact event summaries from dialogue

# Pydantic models
class MemoryChunk(BaseModel):
    id: str = Field(..., description="Unique memory chunk ID")
    user_id: str = Field(..., description="User identifier")
    session_id: str = Field(..., description="Session identifier")
    namespace: str = Field(default=MemoryNamespace.GENERAL, description="Memory namespace")
    text: str = Field(..., description="Memory text content")
    embedding: Optional[List[float]] = Field(None, description="Text embedding vector")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="Creation timestamp")
    consent_scopes: List[str] = Field(default_factory=list, description="Consent scopes")

class MemoryQuery(BaseModel):
    user_id: str = Field(..., description="User identifier")
    query: str = Field(..., description="Query text")
    namespace: Optional[str] = Field(None, description="Specific namespace to search")
    top_k: int = Field(default=3, description="Number of top results to return")
    min_score: float = Field(default=0.6, description="Minimum similarity score")

class MemoryResponse(BaseModel):
    chunks: List[MemoryChunk] = Field(..., description="Retrieved memory chunks")
    scores: List[float] = Field(..., description="Similarity scores")
    total_hits: int = Field(..., description="Total number of hits")
    query_time_ms: float = Field(..., description="Query execution time in milliseconds")
    namespace: str = Field(..., description="Namespace that was searched")

class StoreMemoryRequest(BaseModel):
    user_id: str = Field(..., description="User identifier")
    session_id: str = Field(..., description="Session identifier")
    namespace: str = Field(default=MemoryNamespace.GENERAL, description="Memory namespace")
    text: str = Field(..., description="Text to store")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")
    consent_scopes: List[str] = Field(default_factory=list, description="Consent scopes")

class SocialSignals(BaseModel):
    sentiment: str = Field(..., description="Positive/negative/neutral")
    politeness: float = Field(..., description="Politeness score 0-1")
    urgency: float = Field(..., description="Urgency score 0-1")
    uncertainty: float = Field(..., description="Uncertainty score 0-1")
    user_goal_guess: str = Field(..., description="Guessed user goal")

class AnalyzeSocialRequest(BaseModel):
    text: str = Field(..., description="Text to analyze")
    session_id: str = Field(..., description="Session identifier")

class ForgetRequest(BaseModel):
    user_id: str = Field(..., description="User identifier")
    session_id: Optional[str] = Field(None, description="Specific session to forget (optional)")
    namespace: Optional[str] = Field(None, description="Specific namespace to forget (optional)")

# Initialize FastAPI app
app = FastAPI(
    title="Alice Memory Service",
    description="Redis TTL session storage + FAISS user memory with Swedish embeddings",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global variables
redis_client: Optional[redis.Redis] = None
embedding_model: Optional[SentenceTransformer] = None
faiss_indices: Dict[str, faiss.IndexFlatIP] = {}
memory_data: Dict[str, Any] = {}

def get_redis_client() -> redis.Redis:
    """Get Redis client with connection pooling"""
    global redis_client
    if redis_client is None:
        redis_client = redis.from_url(REDIS_URL, decode_responses=True)
    return redis_client

def get_embedding_model() -> SentenceTransformer:
    """Get sentence transformer model for embeddings"""
    global embedding_model
    if embedding_model is None:
        logger.info("Loading embedding model", model=EMBEDDING_MODEL)
        embedding_model = SentenceTransformer(EMBEDDING_MODEL)
        logger.info("Embedding model loaded successfully")
    return embedding_model

def get_faiss_index(namespace: str = MemoryNamespace.GENERAL) -> faiss.IndexFlatIP:
    """Get or create FAISS index for specific namespace"""
    global faiss_indices
    
    if namespace not in faiss_indices:
        # Determine index path based on namespace
        if namespace == MemoryNamespace.PERSONA:
            index_path = PERSONA_INDEX_PATH
        elif namespace == MemoryNamespace.EPISODES:
            index_path = EPISODES_INDEX_PATH
        else:
            index_path = FAISS_INDEX_PATH
            
        if index_path.exists():
            logger.info("Loading existing FAISS index", namespace=namespace, path=str(index_path))
            faiss_indices[namespace] = faiss.read_index(str(index_path))
        else:
            logger.info("Creating new FAISS index", namespace=namespace)
            # Get embedding dimension from model
            model = get_embedding_model()
            dimension = model.get_sentence_embedding_dimension()
            faiss_indices[namespace] = faiss.IndexFlatIP(dimension)  # Inner product for cosine similarity
            
        logger.info("FAISS index ready", namespace=namespace, dimension=faiss_indices[namespace].d)
    
    return faiss_indices[namespace]

def load_memory_data():
    """Load memory data from disk"""
    global memory_data
    if MEMORY_DATA_PATH.exists():
        try:
            with open(MEMORY_DATA_PATH, 'r', encoding='utf-8') as f:
                memory_data = json.load(f)
            logger.info("Memory data loaded", chunks=len(memory_data.get("chunks", [])))
        except Exception as e:
            logger.error("Failed to load memory data", error=str(e))
            memory_data = {"chunks": [], "next_id": 0}
    else:
        memory_data = {"chunks": [], "next_id": 0}

def save_memory_data():
    """Save memory data to disk"""
    try:
        MEMORY_DATA_PATH.parent.mkdir(parents=True, exist_ok=True)
        with open(MEMORY_DATA_PATH, 'w', encoding='utf-8') as f:
            json.dump(memory_data, f, ensure_ascii=False, indent=2, default=str)
        logger.info("Memory data saved", chunks=len(memory_data.get("chunks", [])))
    except Exception as e:
        logger.error("Failed to save memory data", error=str(e))

def save_faiss_indices():
    """Save all FAISS indices to disk"""
    global faiss_indices
    try:
        for namespace, index in faiss_indices.items():
            if namespace == MemoryNamespace.PERSONA:
                path = PERSONA_INDEX_PATH
            elif namespace == MemoryNamespace.EPISODES:
                path = EPISODES_INDEX_PATH
            else:
                path = FAISS_INDEX_PATH
                
            path.parent.mkdir(parents=True, exist_ok=True)
            faiss.write_index(index, str(path))
            logger.info("FAISS index saved", namespace=namespace, path=str(path))
    except Exception as e:
        logger.error("Failed to save FAISS indices", error=str(e))

def analyze_social_signals(text: str) -> SocialSignals:
    """Analyze social signals in text using simple heuristics"""
    text_lower = text.lower()
    
    # Sentiment analysis (simple keyword-based)
    positive_words = ["bra", "tack", "hjälp", "snälla", "vänlig", "trevlig", "kul", "roligt"]
    negative_words = ["dåligt", "fel", "problem", "irriterande", "tråkigt", "svårt", "jobbigt"]
    
    positive_count = sum(1 for word in positive_words if word in text_lower)
    negative_count = sum(1 for word in negative_words if word in text_lower)
    
    if positive_count > negative_count:
        sentiment = "positive"
    elif negative_count > positive_count:
        sentiment = "negative"
    else:
        sentiment = "neutral"
    
    # Politeness (presence of polite words)
    polite_words = ["tack", "snälla", "vänlig", "ursäkta", "förlåt"]
    politeness = min(1.0, sum(1 for word in polite_words if word in text_lower) / 3.0)
    
    # Urgency (exclamation marks, urgent words)
    urgent_words = ["nu", "direkt", "snart", "fort", "skynda"]
    urgency = min(1.0, (text.count("!") * 0.3 + sum(1 for word in urgent_words if word in text_lower) * 0.2))
    
    # Uncertainty (question marks, uncertain words)
    uncertain_words = ["kanske", "troligen", "vet inte", "osäker", "tror"]
    uncertainty = min(1.0, (text.count("?") * 0.3 + sum(1 for word in uncertain_words if word in text_lower) * 0.2))
    
    # User goal guess (simple intent classification)
    if any(word in text_lower for word in ["hjälp", "hjälpa"]):
        user_goal = "help_request"
    elif any(word in text_lower for word in ["boka", "schemalägg", "möte"]):
        user_goal = "scheduling"
    elif any(word in text_lower for word in ["vad", "hur", "när", "var"]):
        user_goal = "information_request"
    else:
        user_goal = "general_conversation"
    
    return SocialSignals(
        sentiment=sentiment,
        politeness=round(politeness, 2),
        urgency=round(urgency, 2),
        uncertainty=round(uncertainty, 2),
        user_goal_guess=user_goal
    )

@app.on_event("startup")
async def startup_event():
    """Initialize services on startup"""
    logger.info("Starting Alice Memory Service")
    
    # Test Redis connection
    try:
        redis_client = get_redis_client()
        redis_client.ping()
        logger.info("Redis connection established")
    except Exception as e:
        logger.error("Failed to connect to Redis", error=str(e))
        raise
    
    # Load embedding model
    try:
        get_embedding_model()
        logger.info("Embedding model loaded")
    except Exception as e:
        logger.error("Failed to load embedding model", error=str(e))
        raise
    
    # Initialize FAISS indices for all namespaces
    try:
        for namespace in [MemoryNamespace.GENERAL, MemoryNamespace.PERSONA, MemoryNamespace.EPISODES]:
            get_faiss_index(namespace)
        logger.info("All FAISS indices initialized")
    except Exception as e:
        logger.error("Failed to initialize FAISS indices", error=str(e))
        raise
    
    # Load memory data
    load_memory_data()
    
    logger.info("Alice Memory Service started successfully")

@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    logger.info("Shutting down Alice Memory Service")
    
    # Save memory data and FAISS indices
    save_memory_data()
    save_faiss_indices()
    
    logger.info("Alice Memory Service shutdown complete")

@app.get("/health")
async def health_check_simple():
    """Simple health check for Docker"""
    return {"status": "healthy"}

@app.get("/api/memory/health")
async def health_check():
    """Health check endpoint"""
    try:
        # Test Redis
        redis_client = get_redis_client()
        redis_client.ping()
        
        # Test embedding model
        model = get_embedding_model()
        
        # Test FAISS indices
        for namespace in [MemoryNamespace.GENERAL, MemoryNamespace.PERSONA, MemoryNamespace.EPISODES]:
            get_faiss_index(namespace)
        
        # Get stats for all namespaces
        namespace_stats = {}
        for namespace in [MemoryNamespace.GENERAL, MemoryNamespace.PERSONA, MemoryNamespace.EPISODES]:
            index = get_faiss_index(namespace)
            namespace_chunks = [chunk for chunk in memory_data.get("chunks", []) 
                               if chunk.get("namespace") == namespace]
            namespace_stats[namespace] = {
                "chunks": len(namespace_chunks),
                "faiss_vectors": index.ntotal if index else 0
            }
        
        return {
            "status": "healthy",
            "timestamp": datetime.utcnow().isoformat(),
            "services": {
                "redis": "connected",
                "embedding_model": "loaded",
                "faiss_indices": "ready"
            },
            "memory_stats": {
                "total_chunks": len(memory_data.get("chunks", [])),
                "namespaces": namespace_stats
            }
        }
    except Exception as e:
        logger.error("Health check failed", error=str(e))
        raise HTTPException(status_code=503, detail=f"Service unhealthy: {str(e)}")

@app.post("/api/memory/store", response_model=Dict[str, Any])
async def store_memory(request: StoreMemoryRequest):
    """Store a memory chunk"""
    start_time = time.time()
    
    try:
        # Generate unique ID
        chunk_id = str(uuid.uuid4())
        
        # Create memory chunk
        chunk = MemoryChunk(
            id=chunk_id,
            user_id=request.user_id,
            session_id=request.session_id,
            namespace=request.namespace,
            text=request.text,
            metadata=request.metadata,
            consent_scopes=request.consent_scopes
        )
        
        # Generate embedding
        model = get_embedding_model()
        embedding = model.encode([request.text])[0].tolist()
        chunk.embedding = embedding
        
        # Store in Redis with TTL based on namespace
        redis_client = get_redis_client()
        redis_key = f"memory:{request.user_id}:{chunk_id}"
        redis_data = {
            "chunk": chunk.model_dump(),
            "created_at": datetime.utcnow().isoformat()
        }
        
        # Determine TTL based on namespace
        ttl_days = PERSONA_TTL_DAYS if request.namespace == MemoryNamespace.PERSONA else MEMORY_TTL_DAYS
        
        redis_client.setex(
            redis_key,
            timedelta(days=ttl_days),
            json.dumps(redis_data, ensure_ascii=False, default=str)
        )
        
        # Add to FAISS index for specific namespace
        index = get_faiss_index(request.namespace)
        embedding_array = np.array([embedding], dtype=np.float32)
        index.add(embedding_array)
        
        # Store in memory data with namespace
        if "chunks" not in memory_data:
            memory_data["chunks"] = []
        memory_data["chunks"].append(chunk.model_dump())
        memory_data["next_id"] = memory_data.get("next_id", 0) + 1
        
        # Save to disk
        save_memory_data()
        save_faiss_indices()
        
        query_time = (time.time() - start_time) * 1000
        
        logger.info(
            "Memory stored successfully",
            chunk_id=chunk_id,
            user_id=request.user_id,
            session_id=request.session_id,
            namespace=request.namespace,
            text_length=len(request.text),
            query_time_ms=query_time
        )
        
        # Determine TTL based on namespace
        ttl_days = PERSONA_TTL_DAYS if request.namespace == MemoryNamespace.PERSONA else MEMORY_TTL_DAYS
        
        return {
            "success": True,
            "chunk_id": chunk_id,
            "query_time_ms": query_time,
            "ttl_days": ttl_days,
            "namespace": request.namespace
        }
        
    except Exception as e:
        logger.error("Failed to store memory", error=str(e), user_id=request.user_id)
        raise HTTPException(status_code=500, detail=f"Failed to store memory: {str(e)}")

@app.post("/api/memory/query", response_model=MemoryResponse)
async def query_memory(request: MemoryQuery):
    """Query memory using semantic search"""
    start_time = time.time()
    
    try:
        # Generate query embedding
        model = get_embedding_model()
        query_embedding = model.encode([request.query])[0]
        
        # Determine namespace to search
        namespace = request.namespace or MemoryNamespace.GENERAL
        
        # Search FAISS index for specific namespace
        index = get_faiss_index(namespace)
        if index.ntotal == 0:
            return MemoryResponse(
                chunks=[],
                scores=[],
                total_hits=0,
                query_time_ms=(time.time() - start_time) * 1000,
                namespace=namespace
            )
        
        # Perform similarity search
        query_array = np.array([query_embedding], dtype=np.float32)
        scores, indices = index.search(query_array, min(request.top_k, index.ntotal))
        
        # Get chunks from memory data
        chunks = []
        valid_scores = []
        
        for i, (score, idx) in enumerate(zip(scores[0], indices[0])):
            if idx < len(memory_data.get("chunks", [])) and score >= request.min_score:
                chunk_data = memory_data["chunks"][idx]
                # Filter by user_id
                if chunk_data.get("user_id") == request.user_id:
                    chunk = MemoryChunk(**chunk_data)
                    chunks.append(chunk)
                    valid_scores.append(float(score))
        
        query_time = (time.time() - start_time) * 1000
        
        logger.info(
            "Memory query completed",
            user_id=request.user_id,
            query=request.query,
            namespace=namespace,
            total_hits=len(chunks),
            query_time_ms=query_time
        )
        
        return MemoryResponse(
            chunks=chunks,
            scores=valid_scores,
            total_hits=len(chunks),
            query_time_ms=query_time,
            namespace=namespace
        )
        
    except Exception as e:
        logger.error("Failed to query memory", error=str(e), user_id=request.user_id)
        raise HTTPException(status_code=500, detail=f"Failed to query memory: {str(e)}")

@app.post("/api/memory/analyze_social")
async def analyze_social_signals_endpoint(request: AnalyzeSocialRequest):
    """Analyze social signals in text"""
    start_time = time.time()
    
    try:
        signals = analyze_social_signals(request.text)
        query_time = (time.time() - start_time) * 1000
        
        logger.info(
            "Social signals analyzed",
            session_id=request.session_id,
            sentiment=signals.sentiment,
            politeness=signals.politeness,
            urgency=signals.urgency,
            uncertainty=signals.uncertainty,
            user_goal=signals.user_goal_guess,
            query_time_ms=query_time
        )
        
        return {
            "success": True,
            "signals": signals.model_dump(),
            "query_time_ms": query_time
        }
        
    except Exception as e:
        logger.error("Failed to analyze social signals", error=str(e), session_id=request.session_id)
        raise HTTPException(status_code=500, detail=f"Failed to analyze social signals: {str(e)}")

@app.post("/api/memory/forget")
async def forget_memory(request: ForgetRequest):
    """Forget user memory (GDPR compliance)"""
    start_time = time.time()
    
    try:
        redis_client = get_redis_client()
        
        if request.session_id:
            # Forget specific session
            pattern = f"memory:{request.user_id}:*"
            keys = redis_client.keys(pattern)
            deleted_count = 0
            
            for key in keys:
                try:
                    chunk_data = json.loads(redis_client.get(key))
                    chunk = chunk_data.get("chunk", {})
                    if (chunk.get("session_id") == request.session_id and 
                        (request.namespace is None or chunk.get("namespace") == request.namespace)):
                        redis_client.delete(key)
                        deleted_count += 1
                except Exception:
                    continue
            
            # Mark as deleted in memory_data
            for chunk in memory_data.get("chunks", []):
                if (chunk.get("user_id") == request.user_id and 
                    chunk.get("session_id") == request.session_id and
                    (request.namespace is None or chunk.get("namespace") == request.namespace)):
                    chunk["deleted"] = True
            
            logger.info(
                "Session memory forgotten",
                user_id=request.user_id,
                session_id=request.session_id,
                namespace=request.namespace,
                deleted_count=deleted_count,
                query_time_ms=(time.time() - start_time) * 1000
            )
            
        else:
            # Forget all user memory or specific namespace
            pattern = f"memory:{request.user_id}:*"
            keys = redis_client.keys(pattern)
            deleted_count = 0
            
            for key in keys:
                try:
                    chunk_data = json.loads(redis_client.get(key))
                    chunk = chunk_data.get("chunk", {})
                    if request.namespace is None or chunk.get("namespace") == request.namespace:
                        redis_client.delete(key)
                        deleted_count += 1
                except Exception:
                    continue
            
            # Mark chunks as deleted
            for chunk in memory_data.get("chunks", []):
                if (chunk.get("user_id") == request.user_id and
                    (request.namespace is None or chunk.get("namespace") == request.namespace)):
                    chunk["deleted"] = True
            
            logger.info(
                "User memory forgotten",
                user_id=request.user_id,
                namespace=request.namespace,
                deleted_count=deleted_count,
                query_time_ms=(time.time() - start_time) * 1000
            )
        
        # Save updated memory data
        save_memory_data()
        
        return {
            "success": True,
            "deleted_count": deleted_count if 'deleted_count' in locals() else 0,
            "namespace": request.namespace,
            "query_time_ms": (time.time() - start_time) * 1000
        }
        
    except Exception as e:
        logger.error("Failed to forget memory", error=str(e), user_id=request.user_id)
        raise HTTPException(status_code=500, detail=f"Failed to forget memory: {str(e)}")

@app.get("/api/memory/stats")
async def get_stats():
    """Get memory service statistics"""
    try:
        redis_client = get_redis_client()
        
        # Count active chunks per user and namespace
        user_stats = {}
        namespace_stats = {}
        
        for chunk in memory_data.get("chunks", []):
            if not chunk.get("deleted", False):
                user_id = chunk.get("user_id")
                namespace = chunk.get("namespace", MemoryNamespace.GENERAL)
                
                # User stats
                if user_id not in user_stats:
                    user_stats[user_id] = {}
                user_stats[user_id][namespace] = user_stats[user_id].get(namespace, 0) + 1
                
                # Namespace stats
                namespace_stats[namespace] = namespace_stats.get(namespace, 0) + 1
        
        # Get FAISS stats for each namespace
        faiss_stats = {}
        for namespace in [MemoryNamespace.GENERAL, MemoryNamespace.PERSONA, MemoryNamespace.EPISODES]:
            index = get_faiss_index(namespace)
            faiss_stats[namespace] = index.ntotal if index else 0
        
        return {
            "total_chunks": len([c for c in memory_data.get("chunks", []) if not c.get("deleted", False)]),
            "faiss_vectors": faiss_stats,
            "users": len(user_stats),
            "user_stats": user_stats,
            "namespace_stats": namespace_stats,
            "ttl_days": {
                "general": MEMORY_TTL_DAYS,
                "persona": PERSONA_TTL_DAYS,
                "episodes": MEMORY_TTL_DAYS
            }
        }
        
    except Exception as e:
        logger.error("Failed to get stats", error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to get stats: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8300)
