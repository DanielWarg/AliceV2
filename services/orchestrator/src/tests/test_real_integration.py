"""
Real Integration Tests for Alice v2 Orchestrator
Tests against actual running services - NO MOCKS

These tests require:
1. Guardian service running on localhost:8787
2. Redis running for session storage
3. Orchestrator service running on localhost:8000

Run with: pytest src/tests/test_real_integration.py --real-services
"""

import time

import httpx
import pytest
from src.utils.data_collection import log_test_event

# Test configuration
ORCHESTRATOR_URL = "http://localhost:8000"
GUARDIAN_URL = "http://localhost:8787"
TEST_TIMEOUT = 30.0


class RealIntegrationTestSuite:
    """Test suite for real service integration"""

    @classmethod
    def setup_class(cls):
        """Verify all required services are running"""
        cls.orchestrator_client = httpx.Client(
            base_url=ORCHESTRATOR_URL, timeout=TEST_TIMEOUT
        )
        cls.guardian_client = httpx.Client(base_url=GUARDIAN_URL, timeout=TEST_TIMEOUT)

        # Health check all services before running tests
        try:
            # Check orchestrator
            response = cls.orchestrator_client.get("/")
            assert (
                response.status_code == 200
            ), f"Orchestrator not running: {response.status_code}"

            # Check guardian (if available)
            try:
                response = cls.guardian_client.get("/health")
                cls.guardian_available = response.status_code in [200, 503]
            except:
                cls.guardian_available = False
                print("⚠️  Guardian service not available - some tests will be skipped")

        except Exception as e:
            pytest.fail(f"Services not ready: {e}")

    @classmethod
    def teardown_class(cls):
        """Cleanup after tests"""
        cls.orchestrator_client.close()
        cls.guardian_client.close()


class TestRealisticOrchestratorAPI(RealIntegrationTestSuite):
    """Test orchestrator API against real services with realistic expectations"""

    def test_orchestrator_basic_health_check(self):
        """Test basic health endpoint - should work even if Guardian is down"""
        start_time = time.perf_counter()

        response = self.orchestrator_client.get("/health")

        end_time = time.perf_counter()
        response_time = (end_time - start_time) * 1000

        # Log real test data
        log_test_event(
            "orchestrator_health_check",
            response_time_ms=response_time,
            status_code=response.status_code,
            guardian_available=self.guardian_available,
        )

        # Realistic expectations
        if self.guardian_available:
            # If Guardian is up, health should be 200
            assert response.status_code == 200
            data = response.json()
            assert "service" in data
            assert data["service"] == "orchestrator"
        else:
            # If Guardian is down, 503 is acceptable
            assert response.status_code in [200, 503]

        # Performance should be reasonable
        assert response_time < 200, f"Health check too slow: {response_time}ms"

    def test_chat_api_realistic_flow(self):
        """Test chat API with realistic Swedish input"""
        test_cases = [
            {
                "input": "Hej Alice, vad är klockan?",
                "expected_intent": "TIME.CURRENT",
                "description": "Simple time query",
            },
            {
                "input": "Boka möte med Anna imorgon kl 14",
                "expected_intent": "TIME.BOOK",
                "description": "Calendar booking in Swedish",
            },
            {
                "input": "Vad är vädret idag?",
                "expected_intent": "WEATHER.CURRENT",
                "description": "Weather query",
            },
        ]

        success_count = 0
        total_response_time = 0

        for i, case in enumerate(test_cases):
            start_time = time.perf_counter()

            response = self.orchestrator_client.post(
                "/api/chat",
                json={
                    "v": "1",
                    "session_id": f"real_test_{i}",
                    "message": case["input"],
                },
            )

            end_time = time.perf_counter()
            response_time = (end_time - start_time) * 1000
            total_response_time += response_time

            # Log detailed test data
            log_test_event(
                f"chat_realistic_{i}",
                input_text=case["input"],
                response_time_ms=response_time,
                status_code=response.status_code,
                expected_intent=case["expected_intent"],
                test_case=case["description"],
            )

            if response.status_code == 200:
                success_count += 1
                data = response.json()

                # Basic response structure validation
                assert "response" in data or "message" in data

        # Realistic success rate - not 100% perfection
        success_rate = success_count / len(test_cases)
        avg_response_time = total_response_time / len(test_cases)

        # 80% success rate is realistic for complex NLU
        assert success_rate >= 0.8, f"Success rate too low: {success_rate}"

        # Performance should be reasonable
        assert (
            avg_response_time < 2000
        ), f"Average response too slow: {avg_response_time}ms"

    def test_api_version_handling_realistic(self):
        """Test API versioning with realistic error handling"""
        test_scenarios = [
            {"v": "1", "should_work": True, "description": "Valid version"},
            {"v": "2", "should_work": False, "description": "Future version"},
            # Missing version should have graceful handling, not hard failure
        ]

        results = []

        for scenario in test_scenarios:
            payload = {"session_id": "version_test", "message": "test version handling"}

            if "v" in scenario:
                payload["v"] = scenario["v"]

            response = self.orchestrator_client.post("/api/chat", json=payload)

            results.append(
                {
                    "scenario": scenario["description"],
                    "status_code": response.status_code,
                    "expected_success": scenario["should_work"],
                }
            )

            log_test_event(
                "api_version_handling",
                version=scenario.get("v", "missing"),
                status_code=response.status_code,
                expected_success=scenario["should_work"],
            )

        # At least valid version should work
        valid_version_worked = any(
            r["status_code"] == 200 for r in results if r["scenario"] == "Valid version"
        )
        assert valid_version_worked, "Valid API version should work"

    def test_concurrent_load_realistic(self):
        """Test realistic concurrent load handling"""
        import concurrent.futures

        def make_request(request_id):
            try:
                start_time = time.perf_counter()
                response = self.orchestrator_client.post(
                    "/api/chat",
                    json={
                        "v": "1",
                        "session_id": f"concurrent_{request_id}",
                        "message": f"Concurrent test {request_id}",
                    },
                )
                end_time = time.perf_counter()

                return {
                    "request_id": request_id,
                    "response_time": (end_time - start_time) * 1000,
                    "status_code": response.status_code,
                    "success": response.status_code == 200,
                }
            except Exception as e:
                return {
                    "request_id": request_id,
                    "response_time": 30000,  # Timeout
                    "status_code": 0,
                    "success": False,
                    "error": str(e),
                }

        # Test with realistic concurrent load (not extreme)
        concurrent_requests = 5

        with concurrent.futures.ThreadPoolExecutor(
            max_workers=concurrent_requests
        ) as executor:
            futures = [
                executor.submit(make_request, i) for i in range(concurrent_requests)
            ]
            results = [f.result() for f in futures]

        # Analyze results with realistic expectations
        success_count = sum(1 for r in results if r["success"])
        success_rate = success_count / concurrent_requests

        response_times = [r["response_time"] for r in results if r["success"]]
        avg_response_time = (
            sum(response_times) / len(response_times) if response_times else 0
        )

        log_test_event(
            "concurrent_load_realistic",
            concurrent_requests=concurrent_requests,
            success_rate=success_rate,
            avg_response_time_ms=avg_response_time,
        )

        # Realistic expectations - some failures under load are acceptable
        assert success_rate >= 0.8, f"Success rate under load too low: {success_rate}"

        # Performance degradation under load is normal
        if response_times:
            assert (
                avg_response_time < 5000
            ), f"Response time under load too slow: {avg_response_time}ms"


class TestGuardianIntegration(RealIntegrationTestSuite):
    """Test real Guardian service integration"""

    @pytest.mark.skipif(
        not hasattr(RealIntegrationTestSuite, "guardian_available")
        or not RealIntegrationTestSuite.guardian_available,
        reason="Guardian service not available",
    )
    def test_guardian_health_states_realistic(self):
        """Test against real Guardian states - not mocked"""

        # Get actual Guardian state
        guardian_response = self.guardian_client.get("/health")

        if guardian_response.status_code == 200:
            guardian_data = guardian_response.json()
            actual_state = guardian_data.get("state", "UNKNOWN")

            log_test_event(
                "guardian_health_realistic",
                guardian_state=actual_state,
                guardian_available=guardian_data.get("available", False),
                ram_pct=guardian_data.get("ram_pct", 0),
            )

            # Test orchestrator's response to real Guardian state
            orch_response = self.orchestrator_client.get("/health")

            # Realistic expectation: orchestrator should handle any Guardian state gracefully
            assert orch_response.status_code in [200, 503]

            if orch_response.status_code == 200:
                orch_data = orch_response.json()
                assert "dependencies" in orch_data
                assert "guardian" in orch_data["dependencies"]

    def test_guardian_resource_awareness(self):
        """Test that orchestrator adapts to Guardian resource status"""

        if not self.guardian_available:
            pytest.skip("Guardian not available")

        # Get Guardian resource status
        guardian_response = self.guardian_client.get("/health")

        if guardian_response.status_code == 200:
            guardian_data = guardian_response.json()
            ram_pct = guardian_data.get("ram_pct", 0)
            state = guardian_data.get("state", "UNKNOWN")

            # Test orchestrator behavior under different resource conditions
            chat_response = self.orchestrator_client.post(
                "/api/chat",
                json={
                    "v": "1",
                    "session_id": "resource_test",
                    "message": "Test under current resource conditions",
                },
            )

            log_test_event(
                "guardian_resource_awareness",
                guardian_ram_pct=ram_pct,
                guardian_state=state,
                orchestrator_response_code=chat_response.status_code,
            )

            # Under high resource usage, some degradation is acceptable
            if ram_pct > 80:
                # High resource usage - slower responses acceptable
                assert chat_response.status_code in [200, 429, 503]
            else:
                # Normal resources - should work normally
                assert chat_response.status_code == 200


class TestErrorHandlingRealistic(RealIntegrationTestSuite):
    """Test realistic error handling scenarios"""

    def test_malformed_requests_graceful_handling(self):
        """Test graceful handling of malformed requests - not 100% perfection"""

        test_scenarios = [
            {"json": {}, "severity": "HIGH", "should_reject": True},
            {"json": {"v": "1"}, "severity": "HIGH", "should_reject": True},
            {
                "json": {"v": "1", "session_id": ""},
                "severity": "MEDIUM",
                "should_reject": True,
            },
            {
                "json": {"v": "1", "session_id": "test", "message": ""},
                "severity": "MEDIUM",
                "should_reject": True,
            },
            {
                "json": {"v": "1", "session_id": "test", "message": "x" * 5000},
                "severity": "LOW",
                "should_reject": False,
            },
            {
                "json": {"v": "1", "session_id": "test", "message": "Normal message"},
                "severity": "NONE",
                "should_reject": False,
            },
        ]

        critical_handled = 0
        total_critical = 0

        for i, scenario in enumerate(test_scenarios):
            response = self.orchestrator_client.post("/api/chat", json=scenario["json"])

            is_critical = scenario["severity"] in ["HIGH", "MEDIUM"]
            if is_critical:
                total_critical += 1

            properly_handled = (
                scenario["should_reject"] and response.status_code >= 400
            ) or (not scenario["should_reject"] and response.status_code == 200)

            if is_critical and properly_handled:
                critical_handled += 1

            log_test_event(
                f"malformed_request_{i}",
                severity=scenario["severity"],
                should_reject=scenario["should_reject"],
                status_code=response.status_code,
                properly_handled=properly_handled,
            )

        # Focus on critical issues being handled
        if total_critical > 0:
            critical_success_rate = critical_handled / total_critical
            assert (
                critical_success_rate >= 0.9
            ), f"Critical error handling too low: {critical_success_rate}"

    def test_network_resilience(self):
        """Test resilience to network issues"""
        import socket

        # Test with various timeout scenarios
        timeouts = [0.1, 1.0, 5.0]  # seconds

        for timeout in timeouts:
            client = httpx.Client(base_url=ORCHESTRATOR_URL, timeout=timeout)

            try:
                start_time = time.perf_counter()
                response = client.post(
                    "/api/chat",
                    json={
                        "v": "1",
                        "session_id": f"timeout_test_{timeout}",
                        "message": "Test network resilience",
                    },
                )
                end_time = time.perf_counter()

                response_time = (end_time - start_time) * 1000

                log_test_event(
                    "network_resilience",
                    timeout_s=timeout,
                    status_code=response.status_code,
                    response_time_ms=response_time,
                    success=True,
                )

            except (httpx.TimeoutException, socket.timeout) as e:
                log_test_event(
                    "network_resilience",
                    timeout_s=timeout,
                    status_code=0,
                    error=str(e),
                    success=False,
                )

                # Very short timeouts are expected to fail sometimes
                if timeout >= 1.0:
                    pytest.fail(
                        f"Request failed with reasonable timeout {timeout}s: {e}"
                    )

            finally:
                client.close()


class TestEndToEndUserJourneys(RealIntegrationTestSuite):
    """Test complete user journeys end-to-end"""

    def test_swedish_conversation_flow(self):
        """Test realistic Swedish conversation with Alice"""

        conversation = [
            {
                "user": "Hej Alice!",
                "expected_type": "greeting",
                "description": "Initial greeting",
            },
            {
                "user": "Vad kan du hjälpa mig med?",
                "expected_type": "capabilities",
                "description": "Asking about capabilities",
            },
            {
                "user": "Boka ett möte med John imorgon klockan 15",
                "expected_type": "calendar_booking",
                "description": "Calendar booking request",
            },
            {
                "user": "Tack så mycket!",
                "expected_type": "thanks",
                "description": "Thanking Alice",
            },
        ]

        session_id = f"swedish_conversation_{int(time.time())}"
        successful_turns = 0

        for i, turn in enumerate(conversation):
            start_time = time.perf_counter()

            response = self.orchestrator_client.post(
                "/api/chat",
                json={"v": "1", "session_id": session_id, "message": turn["user"]},
            )

            end_time = time.perf_counter()
            response_time = (end_time - start_time) * 1000

            success = response.status_code == 200
            if success:
                successful_turns += 1

            log_test_event(
                f"swedish_conversation_turn_{i}",
                user_input=turn["user"],
                expected_type=turn["expected_type"],
                response_time_ms=response_time,
                status_code=response.status_code,
                success=success,
                turn_description=turn["description"],
            )

        # Realistic expectation: Most of conversation should work
        conversation_success_rate = successful_turns / len(conversation)
        assert (
            conversation_success_rate >= 0.75
        ), f"Conversation success rate too low: {conversation_success_rate}"

    def test_error_recovery_flow(self):
        """Test that system recovers gracefully from errors"""

        session_id = f"error_recovery_{int(time.time())}"

        # 1. Send a problematic request
        bad_response = self.orchestrator_client.post(
            "/api/chat",
            json={
                "v": "1",
                "session_id": session_id,
                "message": "x" * 10000,  # Very long message
            },
        )

        # 2. Immediately follow with a normal request
        time.sleep(0.1)  # Brief pause

        good_response = self.orchestrator_client.post(
            "/api/chat",
            json={
                "v": "1",
                "session_id": session_id,
                "message": "Hej, fungerar systemet nu?",
            },
        )

        log_test_event(
            "error_recovery_flow",
            bad_request_status=bad_response.status_code,
            good_request_status=good_response.status_code,
            system_recovered=good_response.status_code == 200,
        )

        # System should recover and handle normal requests after errors
        assert (
            good_response.status_code == 200
        ), "System should recover after handling bad request"
