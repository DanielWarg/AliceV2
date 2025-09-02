#!/usr/bin/env python3
"""
Test script for Alice Memory Service
Tests all memory endpoints and functionality
"""

import asyncio
import httpx
import json
import time
import uuid
from typing import Dict, Any

# Configuration
BASE_URL = "http://localhost:18000"
API_BASE = f"{BASE_URL}/api/memory"

async def test_memory_service():
    """Test all memory service endpoints"""
    print("🧠 Testing Alice Memory Service...")
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        # Test 1: Health check
        print("\n1. Testing health check...")
        try:
            response = await client.get(f"{API_BASE}/health")
            response.raise_for_status()
            health_data = response.json()
            print(f"✅ Health check passed: {health_data['status']}")
            print(f"   Services: {health_data['services']}")
        except Exception as e:
            print(f"❌ Health check failed: {e}")
            return False
        
        # Test 2: Store memory
        print("\n2. Testing memory storage...")
        user_id = f"test-user-{uuid.uuid4().hex[:8]}"
        session_id = f"test-session-{uuid.uuid4().hex[:8]}"
        
        store_data = {
            "user_id": user_id,
            "session_id": session_id,
            "text": "Jag gillar att programmera Python och bygga AI-system. Det är roligt att lära sig nya tekniker.",
            "metadata": {"source": "test", "lang": "sv", "category": "programming"},
            "consent_scopes": ["basic_logging", "memory_storage"]
        }
        
        try:
            response = await client.post(f"{API_BASE}/store", json=store_data)
            response.raise_for_status()
            store_result = response.json()
            chunk_id = store_result["chunk_id"]
            print(f"✅ Memory stored successfully: {chunk_id}")
            print(f"   Query time: {store_result['query_time_ms']:.2f}ms")
        except Exception as e:
            print(f"❌ Memory storage failed: {e}")
            return False
        
        # Test 3: Query memory
        print("\n3. Testing memory query...")
        query_data = {
            "user_id": user_id,
            "query": "programmering Python",
            "top_k": 3,
            "min_score": 0.5
        }
        
        try:
            response = await client.post(f"{API_BASE}/query", json=query_data)
            response.raise_for_status()
            query_result = response.json()
            print(f"✅ Memory query successful: {query_result['total_hits']} hits")
            print(f"   Query time: {query_result['query_time_ms']:.2f}ms")
            
            if query_result['total_hits'] > 0:
                print(f"   Top result: {query_result['chunks'][0]['text'][:50]}...")
        except Exception as e:
            print(f"❌ Memory query failed: {e}")
            return False
        
        # Test 4: Get stats
        print("\n4. Testing memory stats...")
        try:
            response = await client.get(f"{API_BASE}/stats")
            response.raise_for_status()
            stats = response.json()
            print(f"✅ Stats retrieved: {stats['data']['total_chunks']} chunks")
        except Exception as e:
            print(f"❌ Stats retrieval failed: {e}")
            return False
        
        # Test 5: Forget memory (cleanup)
        print("\n5. Testing memory cleanup...")
        forget_data = {
            "user_id": user_id,
            "session_id": session_id
        }
        
        try:
            response = await client.post(f"{API_BASE}/forget", json=forget_data)
            response.raise_for_status()
            forget_result = response.json()
            print(f"✅ Memory cleanup successful: {forget_result['data']['deleted_count']} chunks deleted")
        except Exception as e:
            print(f"❌ Memory cleanup failed: {e}")
            return False
    
    print("\n🎉 All memory service tests passed!")
    return True

async def test_memory_performance():
    """Test memory service performance"""
    print("\n🚀 Testing memory service performance...")
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        # Store multiple memories
        user_id = f"perf-user-{uuid.uuid4().hex[:8]}"
        texts = [
            "Python är ett fantastiskt programmeringsspråk",
            "Machine learning är spännande",
            "AI-system kan hjälpa människor",
            "Data science är framtidens yrke",
            "Programmering är kreativt och logiskt"
        ]
        
        start_time = time.time()
        
        for i, text in enumerate(texts):
            store_data = {
                "user_id": user_id,
                "session_id": f"perf-session-{i}",
                "text": text,
                "metadata": {"source": "perf-test", "index": i},
                "consent_scopes": ["basic_logging"]
            }
            
            try:
                response = await client.post(f"{API_BASE}/store", json=store_data)
                response.raise_for_status()
                result = response.json()
                print(f"   Stored {i+1}/{len(texts)}: {result['query_time_ms']:.2f}ms")
            except Exception as e:
                print(f"   Failed to store {i+1}: {e}")
        
        store_time = time.time() - start_time
        
        # Query performance
        start_time = time.time()
        query_data = {
            "user_id": user_id,
            "query": "programmering",
            "top_k": 5,
            "min_score": 0.3
        }
        
        try:
            response = await client.post(f"{API_BASE}/query", json=query_data)
            response.raise_for_status()
            result = response.json()
            query_time = time.time() - start_time
            print(f"   Query performance: {result['query_time_ms']:.2f}ms (client: {query_time*1000:.2f}ms)")
        except Exception as e:
            print(f"   Query failed: {e}")
        
        # Cleanup
        forget_data = {"user_id": user_id}
        try:
            response = await client.post(f"{API_BASE}/forget", json=forget_data)
            response.raise_for_status()
        except Exception as e:
            print(f"   Cleanup failed: {e}")
    
    print("✅ Performance test completed")

async def main():
    """Main test function"""
    print("🧪 Alice Memory Service Test Suite")
    print("=" * 50)
    
    # Test basic functionality
    success = await test_memory_service()
    
    if success:
        # Test performance
        await test_memory_performance()
        print("\n🎉 All tests completed successfully!")
        return 0
    else:
        print("\n❌ Some tests failed!")
        return 1

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    exit(exit_code)
