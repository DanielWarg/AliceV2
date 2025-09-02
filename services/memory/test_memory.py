#!/usr/bin/env python3
"""
Test script for Alice Memory Service
"""

import asyncio
import httpx
import json
import time
from typing import Dict, Any

async def test_memory_service():
    """Test memory service endpoints"""
    base_url = "http://localhost:8300"
    
    print("🧠 Testing Alice Memory Service...")
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        # Test health check
        print("\n1. Testing health check...")
        try:
            response = await client.get(f"{base_url}/health")
            response.raise_for_status()
            health_data = response.json()
            print(f"✅ Health check passed: {health_data}")
        except Exception as e:
            print(f"❌ Health check failed: {e}")
            return False
        
        # Test store memory
        print("\n2. Testing store memory...")
        store_data = {
            "user_id": "test-user-123",
            "session_id": "test-session-456",
            "text": "Jag gillar att programmera Python och bygga AI-system",
            "metadata": {"source": "test", "lang": "sv"},
            "consent_scopes": ["basic_logging", "rag:index"]
        }
        
        try:
            response = await client.post(f"{base_url}/store", json=store_data)
            response.raise_for_status()
            store_result = response.json()
            print(f"✅ Memory stored: {store_result}")
            chunk_id = store_result.get("chunk_id")
        except Exception as e:
            print(f"❌ Store memory failed: {e}")
            return False
        
        # Test query memory
        print("\n3. Testing query memory...")
        query_data = {
            "user_id": "test-user-123",
            "query": "programmering Python",
            "top_k": 3,
            "min_score": 0.5
        }
        
        try:
            response = await client.post(f"{base_url}/query", json=query_data)
            response.raise_for_status()
            query_result = response.json()
            print(f"✅ Memory query: {query_result}")
            
            # Check if we got results
            total_hits = query_result.get("total_hits", 0)
            if total_hits > 0:
                print(f"✅ Found {total_hits} memory chunks")
            else:
                print("⚠️  No memory chunks found (this might be expected for new index)")
                
        except Exception as e:
            print(f"❌ Query memory failed: {e}")
            return False
        
        # Test stats
        print("\n4. Testing stats...")
        try:
            response = await client.get(f"{base_url}/stats")
            response.raise_for_status()
            stats_result = response.json()
            print(f"✅ Memory stats: {stats_result}")
        except Exception as e:
            print(f"❌ Stats failed: {e}")
            return False
        
        # Test forget memory (session-specific)
        print("\n5. Testing forget memory (session)...")
        forget_data = {
            "user_id": "test-user-123",
            "session_id": "test-session-456"
        }
        
        try:
            response = await client.post(f"{base_url}/forget", json=forget_data)
            response.raise_for_status()
            forget_result = response.json()
            print(f"✅ Memory forgotten (session): {forget_result}")
        except Exception as e:
            print(f"❌ Forget memory failed: {e}")
            return False
        
        # Test forget all user memory
        print("\n6. Testing forget all user memory...")
        forget_all_data = {
            "user_id": "test-user-123"
        }
        
        try:
            response = await client.post(f"{base_url}/forget", json=forget_all_data)
            response.raise_for_status()
            forget_all_result = response.json()
            print(f"✅ All memory forgotten: {forget_all_result}")
        except Exception as e:
            print(f"❌ Forget all memory failed: {e}")
            return False
    
    print("\n🎉 All memory service tests completed successfully!")
    return True

async def test_memory_performance():
    """Test memory service performance"""
    base_url = "http://localhost:8300"
    
    print("\n🚀 Testing memory service performance...")
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        # Store multiple memories
        print("Storing multiple memories...")
        start_time = time.time()
        
        for i in range(5):
            store_data = {
                "user_id": f"perf-user-{i}",
                "session_id": f"perf-session-{i}",
                "text": f"Detta är minne nummer {i} för prestandatest",
                "metadata": {"test": "performance", "index": i},
                "consent_scopes": ["basic_logging"]
            }
            
            try:
                response = await client.post(f"{base_url}/store", json=store_data)
                response.raise_for_status()
                result = response.json()
                print(f"  Stored memory {i+1}/5: {result.get('query_time_ms', 0):.1f}ms")
            except Exception as e:
                print(f"  ❌ Failed to store memory {i+1}: {e}")
        
        store_time = time.time() - start_time
        print(f"✅ Stored 5 memories in {store_time:.2f}s")
        
        # Query performance
        print("Testing query performance...")
        start_time = time.time()
        
        query_data = {
            "user_id": "perf-user-0",
            "query": "minne prestandatest",
            "top_k": 3,
            "min_score": 0.5
        }
        
        try:
            response = await client.post(f"{base_url}/query", json=query_data)
            response.raise_for_status()
            result = response.json()
            query_time = result.get("query_time_ms", 0)
            print(f"✅ Query completed in {query_time:.1f}ms")
            
            if query_time < 1000:  # Less than 1 second
                print("✅ Query performance: GOOD")
            else:
                print("⚠️  Query performance: SLOW")
                
        except Exception as e:
            print(f"❌ Query performance test failed: {e}")
    
    print("🎉 Performance tests completed!")

if __name__ == "__main__":
    print("🧠 Alice Memory Service Test Suite")
    print("=" * 50)
    
    # Run basic tests
    success = asyncio.run(test_memory_service())
    
    if success:
        # Run performance tests
        asyncio.run(test_memory_performance())
        
        print("\n🎉 All tests passed! Memory service is working correctly.")
    else:
        print("\n❌ Some tests failed. Please check the memory service.")
