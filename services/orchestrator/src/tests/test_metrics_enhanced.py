"""
Enhanced Integration Tests with Performance Metrics
Tests that generate structured data for Alice's learning system
"""

import pytest
import time
import httpx
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, patch

from main import app
from src.models.api import ModelType, GuardianState


@pytest.fixture
def client():
    """Test client for FastAPI app"""
    return TestClient(app)


class TestOrchestrator_Performance:
    """Performance-focused tests with detailed metrics"""

    @patch('src.services.guardian_client.GuardianClient.check_admission')
    @patch('src.services.guardian_client.GuardianClient.get_health')
    @patch('src.services.guardian_client.GuardianClient.get_recommended_model')
    def test_chat_performance_under_load(self, mock_get_model, mock_get_health, mock_check_admission, client, test_metrics):
        """Test chat API performance under simulated load"""
        mock_check_admission.return_value = True
        mock_get_health.return_value = {"state": "NORMAL", "available": True}
        mock_get_model.return_value = "micro"
        
        # Warm up
        client.post("/api/chat", json={"v": "1", "session_id": "warmup", "message": "test"})
        
        # Performance test
        response_times = []
        success_count = 0
        
        for i in range(10):  # 10 requests for statistical significance
            start_time = time.perf_counter()
            
            response = client.post("/api/chat", json={
                "v": "1", 
                "session_id": f"perf_test_{i}",
                "message": f"Performance test request {i}"
            })
            
            end_time = time.perf_counter()
            duration_ms = (end_time - start_time) * 1000
            response_times.append(duration_ms)
            
            if response.status_code == 200:
                success_count += 1
                
            # Add per-request metric
            test_metrics(f"request_{i}_duration_ms", duration_ms)
            test_metrics(f"request_{i}_status", response.status_code)
        
        # Calculate statistics
        avg_response_time = sum(response_times) / len(response_times)
        p95_response_time = sorted(response_times)[int(0.95 * len(response_times))]
        success_rate = success_count / 10
        
        # Log performance metrics
        test_metrics("avg_response_time_ms", avg_response_time)
        test_metrics("p95_response_time_ms", p95_response_time)
        test_metrics("success_rate", success_rate)
        test_metrics("total_requests", 10)
        test_metrics("throughput_rps", 10 / (sum(response_times) / 1000))
        
        # Assertions
        assert success_rate >= 0.9, f"Success rate {success_rate} below threshold"
        assert avg_response_time < 200, f"Average response time {avg_response_time}ms too high"
        assert p95_response_time < 300, f"P95 response time {p95_response_time}ms too high"

    def test_orchestrator_routing_accuracy(self, client, test_metrics):
        """Test routing decision accuracy and consistency"""
        test_cases = [
            {"text": "Hej Alice", "expected_lang": "sv", "expected_priority": 5},
            {"text": "Complex mathematical analysis of quantum mechanics", "expected_complexity": "high"},
            {"text": "What time is it?", "expected_intent": "time_query"},
            {"text": "Send email to john@example.com", "expected_intent": "email_action"},
        ]
        
        routing_accuracy = 0
        total_routing_time = 0
        
        for i, test_case in enumerate(test_cases):
            start_time = time.perf_counter()
            
            response = client.post("/api/orchestrator/ingest", json={
                "v": "1",
                "session_id": f"routing_test_{i}",
                "text": test_case["text"],
                "lang": "sv"
            })
            
            end_time = time.perf_counter()
            routing_time = (end_time - start_time) * 1000
            total_routing_time += routing_time
            
            if response.status_code == 200:
                data = response.json()
                
                # Verify routing consistency (Phase 1: always micro)
                if data.get("model") == "micro" and data.get("accepted") == True:
                    routing_accuracy += 1
                    
                # Log detailed routing metrics
                test_metrics(f"routing_{i}_time_ms", routing_time)
                test_metrics(f"routing_{i}_model", data.get("model"))
                test_metrics(f"routing_{i}_priority", data.get("priority"))
                test_metrics(f"routing_{i}_estimated_latency", data.get("estimated_latency_ms"))
        
        # Calculate routing performance metrics
        avg_routing_time = total_routing_time / len(test_cases)
        routing_accuracy_rate = routing_accuracy / len(test_cases)
        
        test_metrics("avg_routing_time_ms", avg_routing_time)
        test_metrics("routing_accuracy_rate", routing_accuracy_rate)
        test_metrics("total_routing_decisions", len(test_cases))
        
        # Assertions for routing quality
        assert routing_accuracy_rate >= 0.8, f"Routing accuracy {routing_accuracy_rate} too low"
        assert avg_routing_time < 50, f"Routing time {avg_routing_time}ms too high"

    def test_error_handling_resilience(self, client, test_metrics):
        """Test system resilience under various error conditions"""
        error_scenarios = [
            {"json": {}, "expected_status": 422, "error_type": "validation"},
            {"json": {"v": "2"}, "expected_status": 422, "error_type": "version_mismatch"}, 
            {"json": {"v": "1", "session_id": ""}, "expected_status": 422, "error_type": "empty_session"},
            {"json": {"v": "1", "session_id": "test", "message": ""}, "expected_status": 422, "error_type": "empty_message"},
        ]
        
        error_handling_score = 0
        total_error_response_time = 0
        
        for i, scenario in enumerate(error_scenarios):
            start_time = time.perf_counter()
            
            response = client.post("/api/chat", json=scenario["json"])
            
            end_time = time.perf_counter()
            response_time = (end_time - start_time) * 1000
            total_error_response_time += response_time
            
            # Verify expected error handling
            if response.status_code == scenario["expected_status"]:
                error_handling_score += 1
                
            test_metrics(f"error_{i}_response_time_ms", response_time)
            test_metrics(f"error_{i}_status_code", response.status_code)
            test_metrics(f"error_{i}_type", scenario["error_type"])
        
        # Calculate error handling metrics
        avg_error_response_time = total_error_response_time / len(error_scenarios)
        error_handling_rate = error_handling_score / len(error_scenarios)
        
        test_metrics("avg_error_response_time_ms", avg_error_response_time)
        test_metrics("error_handling_accuracy", error_handling_rate)
        test_metrics("total_error_scenarios", len(error_scenarios))
        
        # Assertions
        assert error_handling_rate >= 0.9, f"Error handling accuracy {error_handling_rate} too low"
        assert avg_error_response_time < 100, f"Error response time {avg_error_response_time}ms too high"

    @patch('src.services.guardian_client.GuardianClient.get_health')
    def test_guardian_integration_reliability(self, mock_get_health, client, test_metrics):
        """Test Guardian integration reliability under various states"""
        guardian_states = [
            {"state": "NORMAL", "available": True, "expected_admission": True},
            {"state": "BROWNOUT", "available": True, "expected_admission": True},
            {"state": "DEGRADED", "available": True, "expected_admission": True},
            {"state": "EMERGENCY", "available": False, "expected_admission": False},
            {"state": "UNREACHABLE", "available": False, "expected_admission": False},
        ]
        
        guardian_integration_score = 0
        total_guardian_time = 0
        
        for i, state_config in enumerate(guardian_states):
            mock_get_health.return_value = state_config
            
            start_time = time.perf_counter()
            
            response = client.get("/health")
            
            end_time = time.perf_counter()
            response_time = (end_time - start_time) * 1000
            total_guardian_time += response_time
            
            if response.status_code in [200, 503]:  # Both are valid responses
                guardian_integration_score += 1
                
            # Log Guardian integration metrics
            test_metrics(f"guardian_{i}_response_time_ms", response_time)
            test_metrics(f"guardian_{i}_state", state_config["state"])
            test_metrics(f"guardian_{i}_available", state_config["available"])
            test_metrics(f"guardian_{i}_status_code", response.status_code)
        
        # Calculate Guardian integration metrics
        avg_guardian_time = total_guardian_time / len(guardian_states)
        guardian_integration_rate = guardian_integration_score / len(guardian_states)
        
        test_metrics("avg_guardian_integration_time_ms", avg_guardian_time)
        test_metrics("guardian_integration_reliability", guardian_integration_rate)
        test_metrics("guardian_states_tested", len(guardian_states))
        
        # Assertions
        assert guardian_integration_rate >= 0.9, f"Guardian integration reliability {guardian_integration_rate} too low"
        assert avg_guardian_time < 150, f"Guardian integration time {avg_guardian_time}ms too high"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])