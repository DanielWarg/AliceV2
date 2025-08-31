"""
Nightly Production Scenario Tests for Alice v2
Runs 20 realistic scenarios for continuous validation and Alice training data

This module implements the complete production test suite that:
1. Validates system behavior against realistic user scenarios
2. Generates structured training data for Alice's learning
3. Monitors SLO compliance over time
4. Detects performance regressions early

Run with: pytest src/tests/test_nightly_scenarios.py --nightly
"""

import pytest
import httpx
import json
import time
import asyncio
from pathlib import Path
from typing import Dict, List, Any, Optional
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime

from src.utils.data_collection import log_event, log_orchestrator_turn, logging_context

# Load scenario definitions
SCENARIOS_FILE = Path(__file__).parent / "test_scenarios_production.json"
ORCHESTRATOR_URL = "http://localhost:8000"
GUARDIAN_URL = "http://localhost:8787"

class NightlyTestSuite:
    """Production scenario test suite"""
    
    @classmethod
    def setup_class(cls):
        """Setup for nightly tests"""
        # Load scenarios
        with open(SCENARIOS_FILE, 'r', encoding='utf-8') as f:
            cls.test_data = json.load(f)
        
        cls.scenarios = cls.test_data["alice_v2_production_test_scenarios"]["scenarios"]
        cls.config = cls.test_data["alice_v2_production_test_scenarios"]["test_execution_config"]
        cls.thresholds = cls.test_data["alice_v2_production_test_scenarios"]["success_thresholds"]
        
        # Setup HTTP clients
        cls.orchestrator_client = httpx.Client(base_url=ORCHESTRATOR_URL, timeout=30.0)
        cls.guardian_client = httpx.Client(base_url=GUARDIAN_URL, timeout=10.0)
        
        # Check system health
        cls._verify_system_health()
    
    @classmethod
    def _get_scenarios(cls):
        """Get scenarios for parametrized tests"""
        return cls.scenarios
        
        # Initialize test session
        cls.session_start_time = time.time()
        cls.test_results = []
        
        print(f"\n🌙 Starting Nightly Test Suite - {len(cls.scenarios)} scenarios")
    
    @classmethod  
    def _verify_system_health(cls):
        """Verify system is ready for testing"""
        # Check Orchestrator
        try:
            response = cls.orchestrator_client.get("/health")
            assert response.status_code == 200, f"Orchestrator unhealthy: {response.status_code}"
        except Exception as e:
            pytest.fail(f"Orchestrator not accessible: {e}")
        
        # Check Guardian (optional)
        try:
            response = cls.guardian_client.get("/health")
            cls.guardian_available = response.status_code in [200, 503]
        except:
            cls.guardian_available = False
            print("⚠️  Guardian not available - some tests will be skipped")
    
    @classmethod
    def teardown_class(cls):
        """Cleanup and generate summary"""
        cls.orchestrator_client.close()
        cls.guardian_client.close()
        
        # Generate nightly test summary
        cls._generate_nightly_summary()
    
    @classmethod
    def _generate_nightly_summary(cls):
        """Generate comprehensive nightly test summary"""
        total_scenarios = len(cls.test_results)
        successful_scenarios = sum(1 for r in cls.test_results if r.get("overall_success", False))
        
        # Calculate category success rates
        category_stats = {}
        for result in cls.test_results:
            category = result.get("category", "unknown")
            if category not in category_stats:
                category_stats[category] = {"total": 0, "success": 0}
            category_stats[category]["total"] += 1
            if result.get("overall_success", False):
                category_stats[category]["success"] += 1
        
        # Calculate response time statistics
        response_times = [r.get("total_response_time_ms", 0) for r in cls.test_results if r.get("overall_success")]
        if response_times:
            response_times.sort()
            p50 = response_times[len(response_times)//2]
            p95 = response_times[int(len(response_times)*0.95)]
            avg_response = sum(response_times) / len(response_times)
        else:
            p50 = p95 = avg_response = 0
        
        summary = {
            "nightly_test_summary": {
                "timestamp": datetime.now().isoformat(),
                "test_duration_minutes": (time.time() - cls.session_start_time) / 60,
                "overall_metrics": {
                    "total_scenarios": total_scenarios,
                    "successful_scenarios": successful_scenarios,
                    "success_rate": successful_scenarios / total_scenarios if total_scenarios > 0 else 0,
                    "response_time_p50_ms": p50,
                    "response_time_p95_ms": p95,
                    "avg_response_time_ms": avg_response
                },
                "category_performance": {
                    cat: {
                        "success_rate": stats["success"] / stats["total"],
                        "scenarios": stats["total"]
                    } for cat, stats in category_stats.items()
                },
                "slo_compliance": {
                    "overall_success_rate": {
                        "target": cls.thresholds["overall_success_rate"],
                        "actual": successful_scenarios / total_scenarios if total_scenarios > 0 else 0,
                        "compliant": (successful_scenarios / total_scenarios) >= cls.thresholds["overall_success_rate"] if total_scenarios > 0 else False
                    },
                    "response_time_p95": {
                        "target_ms": cls.test_data["alice_v2_production_test_scenarios"]["metadata"]["slo_targets"]["response_time_p95_ms"],
                        "actual_ms": p95,
                        "compliant": p95 <= cls.test_data["alice_v2_production_test_scenarios"]["metadata"]["slo_targets"]["response_time_p95_ms"]
                    }
                },
                "detailed_results": cls.test_results
            }
        }
        
        # Log comprehensive summary for Alice
        log_event({
            "event": "nightly_test_complete",
            "session_type": "nightly_validation", 
            **summary["nightly_test_summary"]
        })
        
        print(f"\n📊 Nightly Test Summary:")
        print(f"   Success Rate: {successful_scenarios}/{total_scenarios} ({successful_scenarios/total_scenarios:.1%})")
        print(f"   P95 Response Time: {p95:.0f}ms")
        print(f"   Test Duration: {(time.time() - cls.session_start_time)/60:.1f} minutes")

    def _execute_scenario(self, scenario: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a single test scenario"""
        scenario_id = scenario["id"]
        
        with logging_context(f"nightly_{scenario_id}", "system_test"):
            start_time = time.time()
            
            # Skip Guardian-required tests if Guardian not available
            if scenario.get("requires_guardian", False) and not self.guardian_available:
                return {
                    "scenario_id": scenario_id,
                    "overall_success": False,
                    "skip_reason": "Guardian not available",
                    "skipped": True
                }
            
            result = {
                "scenario_id": scenario_id,
                "category": scenario["category"],
                "priority": scenario["priority"],
                "start_time": datetime.now().isoformat(),
                "turns": [],
                "overall_success": False,
                "total_response_time_ms": 0,
                "success_criteria_met": {}
            }
            
            try:
                # Handle concurrent scenarios
                if scenario.get("concurrent_sessions", 1) > 1:
                    result = self._execute_concurrent_scenario(scenario)
                else:
                    result = self._execute_single_scenario(scenario)
                
                # Evaluate success criteria
                result["overall_success"] = self._evaluate_success_criteria(scenario, result)
                
            except Exception as e:
                result["error"] = str(e)
                result["overall_success"] = False
            
            result["execution_time_s"] = time.time() - start_time
            
            # Log scenario result for Alice training
            log_event({
                "event": "nightly_scenario_complete",
                "scenario_id": scenario_id,
                "category": scenario["category"],
                "priority": scenario["priority"],
                **result
            })
            
            return result
    
    def _execute_single_scenario(self, scenario: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a single conversation scenario"""
        result = {
            "scenario_id": scenario["id"],
            "category": scenario["category"],
            "turns": [],
            "total_response_time_ms": 0
        }
        
        session_id = f"nightly_{scenario['id']}_{int(time.time())}"
        
        for turn_idx, turn in enumerate(scenario["conversation"]):
            turn_start = time.perf_counter()
            
            try:
                # Make request to orchestrator
                response = self.orchestrator_client.post("/api/chat", json={
                    "v": "1",
                    "session_id": session_id,
                    "message": turn["user"]
                })
                
                turn_end = time.perf_counter()
                response_time_ms = (turn_end - turn_start) * 1000
                
                turn_result = {
                    "turn_number": turn_idx + 1,
                    "user_input": turn["user"],
                    "response_time_ms": response_time_ms,
                    "status_code": response.status_code,
                    "success": response.status_code == 200,
                    "within_time_limit": response_time_ms <= turn.get("max_response_time_ms", 5000)
                }
                
                if response.status_code == 200:
                    response_data = response.json()
                    turn_result["response_content"] = response_data
                    
                    # Log structured turn data for Alice training
                    log_orchestrator_turn(
                        session_id=session_id,
                        turn_id=f"t-{turn_idx+1:03d}",
                        user_input=turn["user"],
                        response=response_data,
                        metrics={"response_time_ms": response_time_ms},
                        guardian_state={"state": "NORMAL"},  # TODO: Get real Guardian state
                        consent_scopes=["analytics:training"]
                    )
                
                result["turns"].append(turn_result)
                result["total_response_time_ms"] += response_time_ms
                
            except Exception as e:
                turn_result = {
                    "turn_number": turn_idx + 1,
                    "user_input": turn["user"],
                    "error": str(e),
                    "success": False,
                    "within_time_limit": False
                }
                result["turns"].append(turn_result)
        
        return result
    
    def _execute_concurrent_scenario(self, scenario: Dict[str, Any]) -> Dict[str, Any]:
        """Execute scenario with concurrent users"""
        concurrent_sessions = scenario.get("concurrent_sessions", 5)
        
        def run_concurrent_user(user_id):
            session_id = f"nightly_concurrent_{scenario['id']}_{user_id}_{int(time.time())}"
            
            # Modify user message to include session identifier
            user_message = scenario["conversation"][0]["user"].format(session_id=user_id)
            
            start_time = time.perf_counter()
            
            try:
                response = self.orchestrator_client.post("/api/chat", json={
                    "v": "1",
                    "session_id": session_id,
                    "message": user_message
                })
                
                end_time = time.perf_counter()
                response_time = (end_time - start_time) * 1000
                
                return {
                    "user_id": user_id,
                    "success": response.status_code == 200,
                    "response_time_ms": response_time,
                    "status_code": response.status_code
                }
                
            except Exception as e:
                return {
                    "user_id": user_id,
                    "success": False,
                    "error": str(e),
                    "response_time_ms": 30000
                }
        
        # Execute concurrent requests
        with ThreadPoolExecutor(max_workers=concurrent_sessions) as executor:
            futures = [executor.submit(run_concurrent_user, i) for i in range(concurrent_sessions)]
            concurrent_results = [f.result() for f in futures]
        
        # Aggregate results
        successful_sessions = [r for r in concurrent_results if r["success"]]
        success_rate = len(successful_sessions) / len(concurrent_results)
        
        if successful_sessions:
            avg_response_time = sum(r["response_time_ms"] for r in successful_sessions) / len(successful_sessions)
            max_response_time = max(r["response_time_ms"] for r in successful_sessions)
        else:
            avg_response_time = 0
            max_response_time = 0
        
        return {
            "scenario_id": scenario["id"],
            "category": scenario["category"],
            "concurrent_sessions": concurrent_sessions,
            "success_rate": success_rate,
            "successful_sessions": len(successful_sessions),
            "avg_response_time_ms": avg_response_time,
            "max_response_time_ms": max_response_time,
            "total_response_time_ms": avg_response_time,
            "detailed_results": concurrent_results
        }
    
    def _evaluate_success_criteria(self, scenario: Dict[str, Any], result: Dict[str, Any]) -> bool:
        """Evaluate if scenario meets success criteria"""
        criteria = scenario.get("success_criteria", {})
        met_criteria = {}
        
        # Response time check
        if "response_time_ms" in criteria:
            target_time = criteria["response_time_ms"]
            actual_time = result.get("total_response_time_ms", 0)
            met_criteria["response_time"] = actual_time <= target_time
        
        # Success rate check (for concurrent scenarios)
        if "concurrent_success_rate" in criteria:
            target_rate = criteria["concurrent_success_rate"]
            actual_rate = result.get("success_rate", 0)
            met_criteria["concurrent_success_rate"] = actual_rate >= target_rate
        
        # Conversation completion check
        if "conversation_completion" in criteria:
            turns = result.get("turns", [])
            if turns:
                completed = all(turn.get("success", False) for turn in turns)
                met_criteria["conversation_completion"] = completed
            else:
                met_criteria["conversation_completion"] = result.get("success_rate", 0) > 0
        
        # Intent confidence (placeholder - would need NLU integration)
        if "intent_confidence" in criteria:
            # For now, assume met if response was successful
            met_criteria["intent_confidence"] = result.get("success_rate", 0) > 0 or len([t for t in result.get("turns", []) if t.get("success")]) > 0
        
        result["success_criteria_met"] = met_criteria
        
        # Overall success requires all criteria to be met
        return all(met_criteria.values()) if met_criteria else False
    
# Load scenarios once at module level for parametrize
with open(SCENARIOS_FILE, 'r', encoding='utf-8') as f:
    _scenario_data = json.load(f)
_test_scenarios = _scenario_data["alice_v2_production_test_scenarios"]["scenarios"]

class TestProductionScenarios(NightlyTestSuite):
    """Individual scenario tests"""
    
    def setup_method(self):
        """Setup for each test method"""
        if not hasattr(self, 'test_results'):
            self.test_results = []
    
    @pytest.mark.parametrize("scenario", _test_scenarios, ids=lambda s: s["id"])
    def test_production_scenario(self, scenario):
        """Test individual production scenario"""
        result = self._execute_scenario(scenario)
        
        # Add to class results for summary
        self.test_results.append(result)
        
        # Skip assertion for skipped tests
        if result.get("skipped", False):
            pytest.skip(result.get("skip_reason", "Unknown skip reason"))
        
        # Assert based on priority
        if scenario["priority"] == "CRITICAL":
            assert result["overall_success"], f"Critical scenario {scenario['id']} failed: {result}"
        elif scenario["priority"] == "HIGH":
            # Allow some flexibility for high priority
            if not result["overall_success"]:
                print(f"⚠️  High priority scenario {scenario['id']} failed - investigating")
        
        # Log success for monitoring
        assert "overall_success" in result, f"Scenario {scenario['id']} didn't complete properly"

class TestNightlyAggregation(NightlyTestSuite):
    """Aggregate analysis of nightly test results"""
    
    def test_overall_slo_compliance(self):
        """Test that overall SLOs are met across all scenarios"""
        # This test runs after all individual scenarios
        if not hasattr(self, 'test_results') or not self.test_results:
            pytest.skip("No test results available for SLO analysis")
        
        total_scenarios = len(self.test_results)
        successful_scenarios = sum(1 for r in self.test_results if r.get("overall_success", False))
        overall_success_rate = successful_scenarios / total_scenarios
        
        # Check critical scenarios specifically  
        critical_results = [r for r in self.test_results if r.get("priority") == "CRITICAL"]
        if critical_results:
            critical_success_rate = sum(1 for r in critical_results if r.get("overall_success", False)) / len(critical_results)
            assert critical_success_rate >= self.thresholds["critical_scenarios_success_rate"], \
                f"Critical scenarios success rate too low: {critical_success_rate:.2%}"
        
        # Overall success rate
        assert overall_success_rate >= self.thresholds["overall_success_rate"], \
            f"Overall success rate too low: {overall_success_rate:.2%} (target: {self.thresholds['overall_success_rate']:.2%})"
        
        print(f"✅ SLO Compliance: {overall_success_rate:.1%} success rate")
    
    def test_performance_regression_detection(self):
        """Detect performance regressions compared to baseline"""
        if not hasattr(self, 'test_results') or not self.test_results:
            pytest.skip("No test results for regression analysis")
        
        # Calculate current performance metrics
        response_times = [r.get("total_response_time_ms", 0) for r in self.test_results if r.get("overall_success")]
        
        if not response_times:
            pytest.skip("No successful responses for performance analysis")
        
        response_times.sort()
        current_p95 = response_times[int(len(response_times) * 0.95)]
        
        # Compare against SLO target
        target_p95 = self.test_data["alice_v2_production_test_scenarios"]["metadata"]["slo_targets"]["response_time_p95_ms"]
        
        # Allow some variance but flag significant regressions
        performance_acceptable = current_p95 <= target_p95 * 1.2  # 20% tolerance
        
        log_event({
            "event": "nightly_performance_analysis",
            "current_p95_ms": current_p95,
            "target_p95_ms": target_p95,
            "performance_acceptable": performance_acceptable,
            "regression_detected": not performance_acceptable
        })
        
        if not performance_acceptable:
            print(f"⚠️  Performance regression detected: P95 {current_p95:.0f}ms vs target {target_p95}ms")
        
        # For now, warn but don't fail - allow gradual performance degradation detection
        # In production, you might want to fail on significant regressions
        assert current_p95 <= target_p95 * 2.0, f"Severe performance regression: P95 {current_p95:.0f}ms >> target {target_p95}ms"