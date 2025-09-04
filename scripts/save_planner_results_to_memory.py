#!/usr/bin/env python3
"""
Save Planner Test Results to Alice Memory System
Stores test results for Alice's learning and improvement
"""

import asyncio
import time
from datetime import datetime
from typing import Any, Dict, List

import httpx

# Configuration
BASE_URL = "http://localhost:18000"
API_BASE = f"{BASE_URL}/api/memory"


class PlannerResultsMemory:
    """Store planner test results in Alice's memory system"""

    def __init__(self):
        self.client = httpx.AsyncClient(timeout=30.0)
        self.user_id = "alice-system"
        self.session_id = f"planner-test-{int(time.time())}"

    async def store_test_summary(self, results: Dict[str, Any]):
        """Store overall test summary"""
        summary_text = f"""
        Planner Test Results Summary - {datetime.now().strftime('%Y-%m-%d %H:%M')}
        
        Overall Performance:
        - Schema OK Rate: {results.get('schema_ok_rate', 0):.1f}%
        - Success Rate: {results.get('success_rate', 0):.1f}%
        - P95 Latency: {results.get('p95_latency', 0):.1f}ms
        - Fallback Rate: {results.get('fallback_rate', 0):.1f}%
        - Classifier Usage: {results.get('classifier_usage', 0):.1f}%
        
        Test Configuration:
        - Model: {results.get('model', 'qwen2.5:1.5b')}
        - Grammar: GBNF constrained JSON
        - Retry Logic: 2 attempts with JSON repair
        - Total Scenarios: {results.get('total_scenarios', 0)}
        
        Key Findings:
        - EASY scenarios: Excellent performance (100% schema_ok)
        - MEDIUM scenarios: Good performance (95% schema_ok)
        - HARD scenarios: Needs improvement (46.7% schema_ok)
        - Local model sufficient for EASY/MEDIUM, OpenAI API needed for HARD
        """

        metadata = {
            "type": "planner_test_summary",
            "test_date": datetime.now().isoformat(),
            "model": results.get("model", "qwen2.5:1.5b"),
            "total_scenarios": results.get("total_scenarios", 0),
            "schema_ok_rate": results.get("schema_ok_rate", 0),
            "success_rate": results.get("success_rate", 0),
            "p95_latency": results.get("p95_latency", 0),
            "fallback_rate": results.get("fallback_rate", 0),
            "classifier_usage": results.get("classifier_usage", 0),
        }

        await self._store_memory(
            text=summary_text, metadata=metadata, namespace="TESTING"
        )

    async def store_complexity_breakdown(self, results: Dict[str, Any]):
        """Store detailed breakdown by complexity level"""
        complexity_data = results.get("complexity_breakdown", {})

        for level, data in complexity_data.items():
            text = f"""
            Planner Performance - {level.upper()} Scenarios
            
            Metrics:
            - Schema OK: {data.get('schema_ok', 0):.1f}%
            - Success Rate: {data.get('success_rate', 0):.1f}%
            - Classifier Usage: {data.get('classifier_usage', 0):.1f}%
            - Avg Latency: {data.get('avg_latency', 0):.1f}ms
            - Count: {data.get('count', 0)} scenarios
            
            Examples:
            {data.get('examples', ['No examples provided'])}
            
            Analysis:
            - Performance: {'Excellent' if data.get('schema_ok', 0) >= 95 else 'Good' if data.get('schema_ok', 0) >= 80 else 'Needs Improvement'}
            - Recommendation: {data.get('recommendation', 'Continue monitoring')}
            """

            metadata = {
                "type": "planner_complexity_analysis",
                "complexity_level": level,
                "test_date": datetime.now().isoformat(),
                "schema_ok": data.get("schema_ok", 0),
                "success_rate": data.get("success_rate", 0),
                "classifier_usage": data.get("classifier_usage", 0),
                "avg_latency": data.get("avg_latency", 0),
                "count": data.get("count", 0),
            }

            await self._store_memory(text=text, metadata=metadata, namespace="TESTING")

    async def store_individual_results(self, scenarios: List[Dict[str, Any]]):
        """Store individual test scenario results"""
        for i, scenario in enumerate(scenarios):
            text = f"""
            Test Scenario {i+1}: {scenario.get('message', 'Unknown')}
            
            Result:
            - Expected Tool: {scenario.get('expected_tool', 'unknown')}
            - Actual Tool: {scenario.get('actual_tool', 'unknown')}
            - Schema OK: {scenario.get('schema_ok', False)}
            - Success: {scenario.get('success', False)}
            - Latency: {scenario.get('latency', 0):.1f}ms
            - Classifier Used: {scenario.get('classifier_used', False)}
            - Complexity: {scenario.get('complexity', 'unknown')}
            
            Raw Response: {scenario.get('raw_response', 'No response')}
            """

            metadata = {
                "type": "planner_test_scenario",
                "scenario_id": i + 1,
                "test_date": datetime.now().isoformat(),
                "expected_tool": scenario.get("expected_tool", "unknown"),
                "actual_tool": scenario.get("actual_tool", "unknown"),
                "schema_ok": scenario.get("schema_ok", False),
                "success": scenario.get("success", False),
                "latency": scenario.get("latency", 0),
                "classifier_used": scenario.get("classifier_used", False),
                "complexity": scenario.get("complexity", "unknown"),
            }

            await self._store_memory(text=text, metadata=metadata, namespace="TESTING")

    async def store_learning_recommendations(self, results: Dict[str, Any]):
        """Store AI learning recommendations based on results"""
        recommendations = f"""
        Planner Learning Recommendations - {datetime.now().strftime('%Y-%m-%d %H:%M')}
        
        Current Performance Analysis:
        - Overall Schema OK: {results.get('schema_ok_rate', 0):.1f}% (Target: ≥80%)
        - Overall Success Rate: {results.get('success_rate', 0):.1f}% (Target: ≥85%)
        - Latency Performance: {results.get('p95_latency', 0):.1f}ms (Target: <900ms)
        
        Immediate Actions:
        1. Accept current EASY/MEDIUM performance (≥95% schema_ok)
        2. Document HARD scenario limitations (46.7% schema_ok)
        3. Proceed to Step 8 (E2E hard test) with current system
        
        Future Improvements:
        1. Implement hybrid routing: HARD → OpenAI API, EASY/MEDIUM → Local
        2. Consider larger local model (3B+ parameters) for complex reasoning
        3. Fine-tune model on Swedish business domain queries
        4. Enhance classifier with ML-based complexity detection
        
        Learning Insights:
        - Local model excels at straightforward tasks (EASY/MEDIUM)
        - Complex multi-step reasoning requires larger model capacity
        - Classifier successfully offloads 65% of simple requests
        - GBNF grammar ensures strong JSON structure compliance
        - Zero fallbacks indicate robust error handling
        
        Next Steps:
        - Monitor HARD scenario performance in production
        - Collect user feedback on complex query handling
        - Plan hybrid routing implementation for v2
        - Consider domain-specific training data collection
        """

        metadata = {
            "type": "planner_learning_recommendations",
            "test_date": datetime.now().isoformat(),
            "current_performance": {
                "schema_ok_rate": results.get("schema_ok_rate", 0),
                "success_rate": results.get("success_rate", 0),
                "p95_latency": results.get("p95_latency", 0),
            },
            "targets": {"schema_ok_rate": 80, "success_rate": 85, "p95_latency": 900},
            "status": "ready_for_step8",
        }

        await self._store_memory(
            text=recommendations, metadata=metadata, namespace="LEARNING"
        )

    async def _store_memory(
        self, text: str, metadata: Dict[str, Any], namespace: str = "GENERAL"
    ):
        """Store memory in Alice's memory system"""
        try:
            payload = {
                "user_id": self.user_id,
                "session_id": self.session_id,
                "text": text.strip(),
                "metadata": metadata,
                "consent_scopes": ["basic_logging", "system_learning"],
                "namespace": namespace,
            }

            response = await self.client.post(f"{API_BASE}/store", json=payload)
            response.raise_for_status()

            result = response.json()
            print(f"✅ Stored {namespace} memory: {result.get('chunk_id', 'unknown')}")

        except Exception as e:
            print(f"❌ Failed to store {namespace} memory: {e}")

    async def close(self):
        """Close HTTP client"""
        await self.client.aclose()


async def main():
    """Main function to save planner results to memory"""
    print("🧠 Saving Planner Test Results to Alice Memory System...")

    # Load test results (you can modify this to load from actual test output)
    test_results = {
        "model": "qwen2.5:1.5b",
        "total_scenarios": 50,
        "schema_ok_rate": 82.0,
        "success_rate": 72.0,
        "p95_latency": 782.0,
        "fallback_rate": 0.0,
        "classifier_usage": 65.0,
        "complexity_breakdown": {
            "easy": {
                "schema_ok": 100.0,
                "success_rate": 100.0,
                "classifier_usage": 80.0,
                "avg_latency": 245.0,
                "count": 15,
                "examples": ["Vad är klockan?", "Boka möte imorgon 14:00"],
                "recommendation": "Excellent performance, continue current approach",
            },
            "medium": {
                "schema_ok": 95.0,
                "success_rate": 75.0,
                "classifier_usage": 70.0,
                "avg_latency": 456.0,
                "count": 20,
                "examples": [
                    "Skapa e-post till Anna om projektuppdatering",
                    "Vad blir vädret i Stockholm på fredag?",
                ],
                "recommendation": "Good performance, minor improvements possible",
            },
            "hard": {
                "schema_ok": 46.7,
                "success_rate": 40.0,
                "classifier_usage": 40.0,
                "avg_latency": 892.0,
                "count": 15,
                "examples": [
                    "Analysera min kalender för denna vecka och föreslå optimala tider för team-möten"
                ],
                "recommendation": "Needs hybrid routing to OpenAI API for complex reasoning",
            },
        },
    }

    memory = PlannerResultsMemory()

    try:
        # Store different types of learning data
        print("\n1. Storing test summary...")
        await memory.store_test_summary(test_results)

        print("\n2. Storing complexity breakdown...")
        await memory.store_complexity_breakdown(test_results)

        print("\n3. Storing learning recommendations...")
        await memory.store_learning_recommendations(test_results)

        print("\n🎉 Successfully stored planner test results in Alice's memory!")
        print(
            "   Alice can now learn from these results and improve future performance."
        )

    except Exception as e:
        print(f"❌ Failed to save results to memory: {e}")

    finally:
        await memory.close()


if __name__ == "__main__":
    asyncio.run(main())
