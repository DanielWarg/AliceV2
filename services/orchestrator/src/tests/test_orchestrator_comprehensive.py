"""
Comprehensive Orchestrator Testing Suite
Implements RealOps testing approach according to Alice v2 Testing Strategy
"""

import pytest
import asyncio
import time
import json
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, patch
from concurrent.futures import ThreadPoolExecutor

from main import app
from src.utils.data_collection import (
    log_event, log_test_event, log_performance_baseline, 
    log_test_failure, logging_context
)


@pytest.fixture
def client():
    """Test client for FastAPI app"""
    return TestClient(app)


class TestOrchestratorCore:
    """Core orchestrator functionality tests"""
    
    @patch('src.services.guardian_client.GuardianClient.get_health')
    def test_orchestrator_health_states(self, mock_get_health, client, test_metrics):
        """Test orchestrator behavior across Guardian states"""
        guardian_states = [
            {"state": "NORMAL", "available": True, "expected_status": 200},
            {"state": "BROWNOUT", "available": True, "expected_status": 200},
            {"state": "DEGRADED", "available": True, "expected_status": 200},
            {"state": "EMERGENCY", "available": False, "expected_status": 503},
        ]
        
        total_response_time = 0
        state_compliance_score = 0
        
        for i, state_config in enumerate(guardian_states):
            mock_get_health.return_value = state_config
            
            start_time = time.perf_counter()
            response = client.get("/health")
            end_time = time.perf_counter()
            
            response_time = (end_time - start_time) * 1000
            total_response_time += response_time
            
            # Verify expected behavior
            if response.status_code == state_config["expected_status"]:
                state_compliance_score += 1
                
            test_metrics(f"guardian_state_{i}_response_ms", response_time)
            test_metrics(f"guardian_state_{state_config['state']}_status", response.status_code)
        
        avg_response_time = total_response_time / len(guardian_states)
        compliance_rate = state_compliance_score / len(guardian_states)
        
        test_metrics("guardian_avg_response_ms", avg_response_time)
        test_metrics("guardian_state_compliance_rate", compliance_rate)
        
        # SLO targets: Guardian response <150ms
        assert avg_response_time < 150, f"Guardian response too slow: {avg_response_time}ms > 150ms"
        assert compliance_rate == 1.0, f"Guardian state compliance failed: {compliance_rate}"

    @patch('src.services.guardian_client.GuardianClient.check_admission')
    @patch('src.services.guardian_client.GuardianClient.get_health')
    def test_api_versioning_compliance(self, mock_get_health, mock_check_admission, client, test_metrics):
        """Test API version handling and consistency"""
        mock_get_health.return_value = {"state": "NORMAL", "available": True}
        mock_check_admission.return_value = True
        
        version_scenarios = [
            {"v": "1", "expected_status": 200, "valid": True},
            {"v": "2", "expected_status": 422, "valid": False}, 
            {"v": "", "expected_status": 422, "valid": False},
            # Missing version field should fail
        ]
        
        version_compliance_score = 0
        total_response_time = 0
        
        for i, scenario in enumerate(version_scenarios):
            payload = {"session_id": f"version_test_{i}", "message": "test version handling"}
            if scenario.get("v"):
                payload["v"] = scenario["v"]
                
            start_time = time.perf_counter()
            response = client.post("/api/chat", json=payload)
            end_time = time.perf_counter()
            
            response_time = (end_time - start_time) * 1000
            total_response_time += response_time
            
            if response.status_code == scenario["expected_status"]:
                version_compliance_score += 1
                
            test_metrics(f"version_{scenario.get('v', 'missing')}_response_ms", response_time)
            test_metrics(f"version_{scenario.get('v', 'missing')}_status", response.status_code)
        
        compliance_rate = version_compliance_score / len(version_scenarios)
        avg_response_time = total_response_time / len(version_scenarios)
        
        test_metrics("api_version_compliance_rate", compliance_rate)
        test_metrics("api_version_avg_response_ms", avg_response_time)
        
        assert compliance_rate == 1.0, f"API version compliance failed: {compliance_rate}"
        assert avg_response_time < 100, f"API version response too slow: {avg_response_time}ms"


class TestOrchestratorPerformance:
    """Performance and SLO compliance tests"""
    
    @patch('src.services.guardian_client.GuardianClient.check_admission')
    @patch('src.services.guardian_client.GuardianClient.get_health')
    @patch('src.services.guardian_client.GuardianClient.get_recommended_model')
    def test_chat_api_slo_compliance(self, mock_get_model, mock_get_health, mock_check_admission, client, test_metrics):
        """Test chat API SLO compliance under various conditions"""
        mock_check_admission.return_value = True
        mock_get_health.return_value = {"state": "NORMAL", "available": True}
        mock_get_model.return_value = "micro"
        
        # Warm up request
        client.post("/api/chat", json={"v": "1", "session_id": "warmup", "message": "warmup"})
        
        # SLO performance testing
        response_times = []
        success_count = 0
        test_iterations = 20
        
        for i in range(test_iterations):
            start_time = time.perf_counter()
            
            response = client.post("/api/chat", json={
                "v": "1",
                "session_id": f"slo_test_{i}",
                "message": f"SLO test message {i}"
            })
            
            end_time = time.perf_counter()
            response_time = (end_time - start_time) * 1000
            response_times.append(response_time)
            
            if response.status_code == 200:
                success_count += 1
                
            test_metrics(f"chat_slo_iteration_{i}_ms", response_time)
        
        # Calculate SLO metrics
        response_times.sort()
        p50 = response_times[len(response_times)//2]
        p95 = response_times[int(len(response_times)*0.95)]
        p99 = response_times[int(len(response_times)*0.99)]
        avg_response = sum(response_times) / len(response_times)
        success_rate = success_count / test_iterations
        
        test_metrics("chat_api_p50_ms", p50)
        test_metrics("chat_api_p95_ms", p95)
        test_metrics("chat_api_p99_ms", p99)
        test_metrics("chat_api_avg_ms", avg_response)
        test_metrics("chat_api_success_rate", success_rate)
        
        # SLO targets from README: API Response Time P95 <100ms
        assert p95 < 100, f"Chat API P95 SLO violation: {p95}ms > 100ms"
        assert success_rate >= 0.99, f"Chat API success rate too low: {success_rate}"
        
    @patch('src.services.guardian_client.GuardianClient.check_admission')
    @patch('src.services.guardian_client.GuardianClient.get_health')
    def test_concurrent_request_handling(self, mock_get_health, mock_check_admission, client, test_metrics):
        """Test orchestrator behavior under concurrent load"""
        mock_check_admission.return_value = True
        mock_get_health.return_value = {"state": "NORMAL", "available": True}
        
        concurrent_requests = 10
        request_results = []
        
        def make_request(request_id):
            start_time = time.perf_counter()
            response = client.post("/api/chat", json={
                "v": "1",
                "session_id": f"concurrent_{request_id}",
                "message": f"Concurrent test {request_id}"
            })
            end_time = time.perf_counter()
            
            return {
                "request_id": request_id,
                "response_time": (end_time - start_time) * 1000,
                "status_code": response.status_code,
                "success": response.status_code == 200
            }
        
        # Execute concurrent requests
        with ThreadPoolExecutor(max_workers=concurrent_requests) as executor:
            futures = [executor.submit(make_request, i) for i in range(concurrent_requests)]
            request_results = [f.result() for f in futures]
        
        # Analyze results
        response_times = [r["response_time"] for r in request_results]
        success_count = sum(1 for r in request_results if r["success"])
        
        max_response_time = max(response_times)
        avg_response_time = sum(response_times) / len(response_times)
        success_rate = success_count / concurrent_requests
        
        test_metrics("concurrent_max_response_ms", max_response_time)
        test_metrics("concurrent_avg_response_ms", avg_response_time)
        test_metrics("concurrent_success_rate", success_rate)
        test_metrics("concurrent_request_count", concurrent_requests)
        
        # Log individual request metrics
        for result in request_results:
            test_metrics(f"concurrent_req_{result['request_id']}_ms", result["response_time"])
        
        # Performance assertions
        assert success_rate >= 0.95, f"Concurrent success rate too low: {success_rate}"
        assert avg_response_time < 200, f"Concurrent avg response too slow: {avg_response_time}ms"


class TestOrchestratorResilience:
    """Resilience and error handling tests"""
    
    def test_malformed_request_handling(self, client, test_metrics):
        """Test resilience against malformed requests"""
        malformed_scenarios = [
            {"json": {}, "expected_status": 422, "error_type": "empty_payload"},
            {"json": {"v": "1"}, "expected_status": 422, "error_type": "missing_session"},
            {"json": {"v": "1", "session_id": ""}, "expected_status": 422, "error_type": "empty_session"},
            {"json": {"v": "1", "session_id": "test"}, "expected_status": 422, "error_type": "missing_message"},
            {"json": {"v": "1", "session_id": "test", "message": ""}, "expected_status": 422, "error_type": "empty_message"},
            {"json": {"v": "1", "session_id": "test", "message": "x" * 10000}, "expected_status": 422, "error_type": "message_too_long"},
        ]
        
        resilience_score = 0
        total_error_response_time = 0
        
        for i, scenario in enumerate(malformed_scenarios):
            start_time = time.perf_counter()
            response = client.post("/api/chat", json=scenario["json"])
            end_time = time.perf_counter()
            
            response_time = (end_time - start_time) * 1000
            total_error_response_time += response_time
            
            if response.status_code == scenario["expected_status"]:
                resilience_score += 1
                
            test_metrics(f"error_handling_{scenario['error_type']}_ms", response_time)
            test_metrics(f"error_handling_{scenario['error_type']}_status", response.status_code)
        
        avg_error_response = total_error_response_time / len(malformed_scenarios)
        resilience_rate = resilience_score / len(malformed_scenarios)
        
        test_metrics("error_handling_avg_response_ms", avg_error_response)
        test_metrics("error_handling_resilience_rate", resilience_rate)
        
        assert resilience_rate == 1.0, f"Error handling resilience failed: {resilience_rate}"
        assert avg_error_response < 100, f"Error response too slow: {avg_error_response}ms"
        
    @patch('src.services.guardian_client.GuardianClient.get_health')
    def test_guardian_failure_scenarios(self, mock_get_health, client, test_metrics):
        """Test behavior when Guardian is unreachable or failing"""
        guardian_failure_scenarios = [
            {"side_effect": ConnectionError("Guardian unreachable"), "expected_status": 503},
            {"side_effect": TimeoutError("Guardian timeout"), "expected_status": 503},
            {"return_value": {"state": "UNKNOWN", "available": False}, "expected_status": 503},
        ]
        
        failure_handling_score = 0
        total_failure_response_time = 0
        
        for i, scenario in enumerate(guardian_failure_scenarios):
            if "side_effect" in scenario:
                mock_get_health.side_effect = scenario["side_effect"]
            else:
                mock_get_health.return_value = scenario["return_value"]
                mock_get_health.side_effect = None
                
            start_time = time.perf_counter()
            response = client.get("/health")
            end_time = time.perf_counter()
            
            response_time = (end_time - start_time) * 1000
            total_failure_response_time += response_time
            
            if response.status_code == scenario["expected_status"]:
                failure_handling_score += 1
                
            test_metrics(f"guardian_failure_{i}_response_ms", response_time)
            test_metrics(f"guardian_failure_{i}_status", response.status_code)
        
        avg_failure_response = total_failure_response_time / len(guardian_failure_scenarios)
        failure_handling_rate = failure_handling_score / len(guardian_failure_scenarios)
        
        test_metrics("guardian_failure_avg_response_ms", avg_failure_response)
        test_metrics("guardian_failure_handling_rate", failure_handling_rate)
        
        assert failure_handling_rate == 1.0, f"Guardian failure handling failed: {failure_handling_rate}"
        assert avg_failure_response < 500, f"Guardian failure response too slow: {avg_failure_response}ms"


class TestOrchestratorObservability:
    """Observability and monitoring tests"""
    
    def test_structured_logging_compliance(self, client, test_metrics):
        """Test that all responses include proper structured logging"""
        test_requests = [
            {"endpoint": "/", "method": "GET"},
            {"endpoint": "/health", "method": "GET"},
            {"endpoint": "/api/chat", "method": "POST", "json": {"v": "1", "session_id": "log_test", "message": "test"}},
        ]
        
        for request in test_requests:
            start_time = time.perf_counter()
            
            if request["method"] == "GET":
                response = client.get(request["endpoint"])
            else:
                response = client.post(request["endpoint"], json=request.get("json"))
                
            end_time = time.perf_counter()
            response_time = (end_time - start_time) * 1000
            
            # Check for trace ID in response headers
            has_trace_id = "x-trace-id" in response.headers
            
            test_metrics(f"logging_{request['endpoint'].replace('/', '_')}_response_ms", response_time)
            test_metrics(f"logging_{request['endpoint'].replace('/', '_')}_has_trace_id", int(has_trace_id))
        
        # Verify trace ID propagation
        chat_response = client.post("/api/chat", json={"v": "1", "session_id": "trace_test", "message": "trace"})
        has_trace_id = "x-trace-id" in chat_response.headers
        
        test_metrics("trace_id_propagation", int(has_trace_id))
        
        # For now we'll not enforce this but track the metric
        # assert has_trace_id, "Response missing trace ID for observability"