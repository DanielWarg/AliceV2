"""
Chaos Engineering Tests for Alice v2 Orchestrator
Tests system resilience under realistic failure conditions

These tests simulate real-world problems:
- Network glitches and timeouts
- Service overload and resource exhaustion
- Gradual degradation scenarios
- Recovery behavior validation

Run with: pytest src/tests/test_chaos_engineering.py --chaos
"""

import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

import httpx
import psutil
from src.utils.data_collection import log_test_event

ORCHESTRATOR_URL = "http://localhost:8000"
GUARDIAN_URL = "http://localhost:8787"


class ChaosTestSuite:
    """Base class for chaos engineering tests"""

    @classmethod
    def setup_class(cls):
        """Setup for chaos tests"""
        cls.orchestrator_client = httpx.Client(base_url=ORCHESTRATOR_URL, timeout=10.0)

        # Baseline system performance before chaos
        cls.baseline_response_time = cls._measure_baseline_performance()
        print(f"📊 Baseline response time: {cls.baseline_response_time:.2f}ms")

    @classmethod
    def _measure_baseline_performance(cls) -> float:
        """Measure baseline system performance"""
        times = []
        for _ in range(5):
            start = time.perf_counter()
            response = cls.orchestrator_client.post(
                "/api/chat",
                json={
                    "v": "1",
                    "session_id": "baseline",
                    "message": "Baseline performance test",
                },
            )
            end = time.perf_counter()

            if response.status_code == 200:
                times.append((end - start) * 1000)

        return sum(times) / len(times) if times else 100.0

    @classmethod
    def teardown_class(cls):
        """Cleanup after chaos tests"""
        cls.orchestrator_client.close()


class TestNetworkChaos(ChaosTestSuite):
    """Test network-related failure scenarios"""

    def test_connection_timeout_resilience(self):
        """Test behavior under various connection timeout conditions"""

        timeout_scenarios = [
            {"timeout": 0.1, "description": "Very aggressive timeout"},
            {"timeout": 0.5, "description": "Aggressive timeout"},
            {"timeout": 1.0, "description": "Standard timeout"},
            {"timeout": 5.0, "description": "Generous timeout"},
        ]

        results = []

        for scenario in timeout_scenarios:
            timeout = scenario["timeout"]
            client = httpx.Client(base_url=ORCHESTRATOR_URL, timeout=timeout)

            success_count = 0
            total_requests = 10
            response_times = []

            for i in range(total_requests):
                try:
                    start_time = time.perf_counter()
                    response = client.post(
                        "/api/chat",
                        json={
                            "v": "1",
                            "session_id": f"timeout_test_{timeout}_{i}",
                            "message": f"Testing timeout {timeout}s",
                        },
                    )
                    end_time = time.perf_counter()

                    if response.status_code == 200:
                        success_count += 1
                        response_times.append((end_time - start_time) * 1000)

                except (
                    httpx.TimeoutException,
                    httpx.ConnectTimeout,
                    httpx.ReadTimeout,
                ):
                    # Timeouts are expected with very short timeouts
                    pass

            success_rate = success_count / total_requests
            avg_response_time = (
                sum(response_times) / len(response_times) if response_times else 0
            )

            results.append(
                {
                    "timeout": timeout,
                    "success_rate": success_rate,
                    "avg_response_time": avg_response_time,
                    "description": scenario["description"],
                }
            )

            log_test_event(
                f"connection_timeout_{timeout}",
                timeout_s=timeout,
                success_rate=success_rate,
                avg_response_time_ms=avg_response_time,
                total_requests=total_requests,
            )

            client.close()

        # Analysis: Reasonable timeouts should have good success rates
        reasonable_timeouts = [r for r in results if r["timeout"] >= 1.0]
        for result in reasonable_timeouts:
            assert (
                result["success_rate"] >= 0.8
            ), f"Success rate too low for {result['timeout']}s timeout: {result['success_rate']}"

    def test_connection_pool_exhaustion(self):
        """Test behavior when connection pools are exhausted"""

        def make_long_request(request_id):
            """Simulate a request that takes a while"""
            try:
                # Use individual client to simulate connection pool pressure
                client = httpx.Client(base_url=ORCHESTRATOR_URL, timeout=30.0)

                start_time = time.perf_counter()
                response = client.post(
                    "/api/chat",
                    json={
                        "v": "1",
                        "session_id": f"pool_exhaustion_{request_id}",
                        "message": f"Long request {request_id} - simulate connection pool pressure",
                    },
                )
                end_time = time.perf_counter()

                client.close()

                return {
                    "request_id": request_id,
                    "success": response.status_code == 200,
                    "response_time": (end_time - start_time) * 1000,
                    "status_code": response.status_code,
                }

            except Exception as e:
                return {
                    "request_id": request_id,
                    "success": False,
                    "response_time": 30000,
                    "error": str(e),
                }

        # Launch many concurrent requests to exhaust connection pool
        concurrent_requests = 20

        with ThreadPoolExecutor(max_workers=concurrent_requests) as executor:
            futures = [
                executor.submit(make_long_request, i)
                for i in range(concurrent_requests)
            ]
            results = [future.result() for future in as_completed(futures)]

        # Analyze connection pool behavior
        successful_requests = [r for r in results if r["success"]]
        success_rate = len(successful_requests) / len(results)

        if successful_requests:
            avg_response_time = sum(
                r["response_time"] for r in successful_requests
            ) / len(successful_requests)
        else:
            avg_response_time = 0

        log_test_event(
            "connection_pool_exhaustion",
            concurrent_requests=concurrent_requests,
            success_rate=success_rate,
            avg_response_time_ms=avg_response_time,
        )

        # Under extreme load, some failures are acceptable but system should not completely fail
        assert (
            success_rate >= 0.3
        ), f"Success rate under connection pressure too low: {success_rate}"


class TestResourceChaos(ChaosTestSuite):
    """Test resource exhaustion scenarios"""

    def test_memory_pressure_behavior(self):
        """Test system behavior under memory pressure"""

        # Get current memory usage
        process = psutil.Process()
        initial_memory_mb = process.memory_info().rss / 1024 / 1024

        # Create memory pressure by making many concurrent requests
        def memory_pressure_request(request_id):
            try:
                response = self.orchestrator_client.post(
                    "/api/chat",
                    json={
                        "v": "1",
                        "session_id": f"memory_pressure_{request_id}",
                        "message": f"Memory pressure test {request_id} - "
                        + "X" * 1000,  # Larger payload
                    },
                )

                return {
                    "request_id": request_id,
                    "success": response.status_code == 200,
                    "status_code": response.status_code,
                }
            except Exception as e:
                return {"request_id": request_id, "success": False, "error": str(e)}

        # Launch requests and monitor memory
        concurrent_requests = 15
        memory_readings = []

        with ThreadPoolExecutor(max_workers=concurrent_requests) as executor:
            futures = [
                executor.submit(memory_pressure_request, i)
                for i in range(concurrent_requests)
            ]

            # Monitor memory during test
            for _ in range(10):
                current_memory = process.memory_info().rss / 1024 / 1024
                memory_readings.append(current_memory)
                time.sleep(0.5)

            results = [future.result() for future in futures]

        # Final memory reading
        final_memory_mb = process.memory_info().rss / 1024 / 1024
        peak_memory_mb = max(memory_readings)
        memory_increase = peak_memory_mb - initial_memory_mb

        successful_requests = [r for r in results if r["success"]]
        success_rate = len(successful_requests) / len(results)

        log_test_event(
            "memory_pressure_behavior",
            initial_memory_mb=initial_memory_mb,
            peak_memory_mb=peak_memory_mb,
            final_memory_mb=final_memory_mb,
            memory_increase_mb=memory_increase,
            success_rate=success_rate,
            concurrent_requests=concurrent_requests,
        )

        # System should handle memory pressure gracefully
        assert (
            success_rate >= 0.7
        ), f"Success rate under memory pressure too low: {success_rate}"

        # Memory should not grow excessively
        assert (
            memory_increase < 500
        ), f"Memory increase too high: {memory_increase:.2f}MB"

    def test_cpu_intensive_requests(self):
        """Test behavior with CPU-intensive request patterns"""

        def cpu_intensive_request(request_id):
            """Simulate CPU-intensive request"""
            try:
                start_time = time.perf_counter()

                response = self.orchestrator_client.post(
                    "/api/chat",
                    json={
                        "v": "1",
                        "session_id": f"cpu_intensive_{request_id}",
                        "message": f"CPU intensive request {request_id} - complex analysis of this lengthy text with many parameters and detailed processing requirements that should consume more CPU cycles during natural language understanding and processing phases",
                    },
                )

                end_time = time.perf_counter()
                response_time = (end_time - start_time) * 1000

                return {
                    "request_id": request_id,
                    "success": response.status_code == 200,
                    "response_time": response_time,
                    "status_code": response.status_code,
                }

            except Exception as e:
                return {
                    "request_id": request_id,
                    "success": False,
                    "error": str(e),
                    "response_time": 30000,
                }

        # Launch CPU-intensive requests
        concurrent_requests = 8  # More reasonable number

        with ThreadPoolExecutor(max_workers=concurrent_requests) as executor:
            futures = [
                executor.submit(cpu_intensive_request, i)
                for i in range(concurrent_requests)
            ]
            results = [future.result() for future in futures]

        successful_requests = [r for r in results if r["success"]]
        success_rate = len(successful_requests) / len(results)

        if successful_requests:
            avg_response_time = sum(
                r["response_time"] for r in successful_requests
            ) / len(successful_requests)
            max_response_time = max(r["response_time"] for r in successful_requests)
        else:
            avg_response_time = 0
            max_response_time = 0

        log_test_event(
            "cpu_intensive_requests",
            concurrent_requests=concurrent_requests,
            success_rate=success_rate,
            avg_response_time_ms=avg_response_time,
            max_response_time_ms=max_response_time,
        )

        # CPU-intensive requests should still be handled reasonably
        assert (
            success_rate >= 0.75
        ), f"Success rate for CPU-intensive requests too low: {success_rate}"

        # Response times will be higher but should be reasonable
        if avg_response_time > 0:
            # Allow for higher response times under CPU load but not excessive
            assert (
                avg_response_time < 10000
            ), f"Average response time under CPU load too high: {avg_response_time}ms"


class TestGradualDegradation(ChaosTestSuite):
    """Test gradual system degradation scenarios"""

    def test_increasing_load_degradation(self):
        """Test system behavior under gradually increasing load"""

        load_levels = [1, 3, 5, 8, 12, 15]  # Gradually increase concurrent requests
        results = []

        for load_level in load_levels:
            print(f"🔥 Testing load level: {load_level} concurrent requests")

            def load_test_request(request_id):
                try:
                    start_time = time.perf_counter()
                    response = self.orchestrator_client.post(
                        "/api/chat",
                        json={
                            "v": "1",
                            "session_id": f"load_level_{load_level}_{request_id}",
                            "message": f"Load test at level {load_level}, request {request_id}",
                        },
                    )
                    end_time = time.perf_counter()

                    return {
                        "success": response.status_code == 200,
                        "response_time": (end_time - start_time) * 1000,
                        "status_code": response.status_code,
                    }
                except Exception as e:
                    return {"success": False, "response_time": 30000, "error": str(e)}

            # Execute requests at current load level
            with ThreadPoolExecutor(max_workers=load_level) as executor:
                futures = [
                    executor.submit(load_test_request, i) for i in range(load_level)
                ]
                load_results = [future.result() for future in futures]

            # Analyze results at this load level
            successful = [r for r in load_results if r["success"]]
            success_rate = len(successful) / len(load_results)

            if successful:
                avg_response_time = sum(r["response_time"] for r in successful) / len(
                    successful
                )
                p95_response_time = sorted([r["response_time"] for r in successful])[
                    int(len(successful) * 0.95)
                ]
            else:
                avg_response_time = 0
                p95_response_time = 0

            load_result = {
                "load_level": load_level,
                "success_rate": success_rate,
                "avg_response_time": avg_response_time,
                "p95_response_time": p95_response_time,
            }

            results.append(load_result)

            log_test_event(
                f"load_degradation_{load_level}",
                load_level=load_level,
                success_rate=success_rate,
                avg_response_time_ms=avg_response_time,
                p95_response_time_ms=p95_response_time,
            )

            # Brief pause between load levels
            time.sleep(2)

        # Analysis: System should degrade gracefully, not cliff-drop
        print("\n📊 Load degradation analysis:")
        for result in results:
            print(
                f"Load {result['load_level']:2d}: {result['success_rate']:.1%} success, {result['avg_response_time']:.0f}ms avg"
            )

        # Light loads should work well
        light_loads = [r for r in results if r["load_level"] <= 5]
        for result in light_loads:
            assert (
                result["success_rate"] >= 0.9
            ), f"Light load performance poor at level {result['load_level']}"

        # Heavy loads should degrade gracefully, not fail completely
        heavy_loads = [r for r in results if r["load_level"] >= 10]
        if heavy_loads:
            worst_heavy_load = min(heavy_loads, key=lambda x: x["success_rate"])
            assert (
                worst_heavy_load["success_rate"] >= 0.3
            ), "System should not fail completely under heavy load"


class TestRecoveryScenarios(ChaosTestSuite):
    """Test system recovery from various failure scenarios"""

    def test_error_spike_recovery(self):
        """Test recovery after a spike of errors"""

        print("🚨 Creating error spike...")

        # Phase 1: Create error conditions
        error_requests = []
        for i in range(10):
            try:
                response = self.orchestrator_client.post(
                    "/api/chat",
                    json={"invalid": "request_structure"},  # Intentionally malformed
                )
                error_requests.append(response.status_code)
            except:
                error_requests.append(0)

        # Brief pause to let system handle errors
        time.sleep(1)

        print("🔄 Testing recovery...")

        # Phase 2: Test recovery with normal requests
        recovery_results = []
        for i in range(10):
            try:
                start_time = time.perf_counter()
                response = self.orchestrator_client.post(
                    "/api/chat",
                    json={
                        "v": "1",
                        "session_id": f"recovery_test_{i}",
                        "message": f"Recovery test {i}",
                    },
                )
                end_time = time.perf_counter()

                recovery_results.append(
                    {
                        "success": response.status_code == 200,
                        "response_time": (end_time - start_time) * 1000,
                        "status_code": response.status_code,
                    }
                )

            except Exception as e:
                recovery_results.append({"success": False, "error": str(e)})

            time.sleep(0.2)  # Brief pause between recovery tests

        # Analysis
        successful_recovery = [r for r in recovery_results if r["success"]]
        recovery_rate = len(successful_recovery) / len(recovery_results)

        if successful_recovery:
            avg_recovery_time = sum(
                r["response_time"] for r in successful_recovery
            ) / len(successful_recovery)
        else:
            avg_recovery_time = 0

        log_test_event(
            "error_spike_recovery",
            error_requests_sent=len(error_requests),
            recovery_rate=recovery_rate,
            avg_recovery_time_ms=avg_recovery_time,
        )

        # System should recover well after error spike
        assert (
            recovery_rate >= 0.8
        ), f"Recovery rate after error spike too low: {recovery_rate}"

        # Recovery should not be significantly slower than baseline
        if avg_recovery_time > 0:
            slowdown_factor = avg_recovery_time / self.baseline_response_time
            assert (
                slowdown_factor < 3
            ), f"Recovery too slow compared to baseline: {slowdown_factor:.1f}x"

    def test_sustained_load_recovery(self):
        """Test recovery after sustained high load"""

        print("⚡ Creating sustained load...")

        # Phase 1: Sustained load for 30 seconds
        load_start_time = time.time()
        load_duration = 15  # seconds

        load_results = []

        def sustained_load_worker():
            request_count = 0
            while time.time() - load_start_time < load_duration:
                try:
                    response = self.orchestrator_client.post(
                        "/api/chat",
                        json={
                            "v": "1",
                            "session_id": f"sustained_load_{threading.current_thread().ident}_{request_count}",
                            "message": f"Sustained load test {request_count}",
                        },
                    )
                    load_results.append(response.status_code == 200)
                    request_count += 1

                except:
                    load_results.append(False)

                time.sleep(0.1)  # 10 RPS per thread

        # Run sustained load with multiple threads
        threads = []
        for i in range(3):  # 3 threads = ~30 RPS
            thread = threading.Thread(target=sustained_load_worker)
            threads.append(thread)
            thread.start()

        # Wait for load test to complete
        for thread in threads:
            thread.join()

        # Brief pause to let system settle
        time.sleep(2)

        print("🔄 Testing post-load recovery...")

        # Phase 2: Test recovery
        recovery_results = []
        for i in range(10):
            try:
                start_time = time.perf_counter()
                response = self.orchestrator_client.post(
                    "/api/chat",
                    json={
                        "v": "1",
                        "session_id": f"post_load_recovery_{i}",
                        "message": f"Post-load recovery test {i}",
                    },
                )
                end_time = time.perf_counter()

                recovery_results.append(
                    {
                        "success": response.status_code == 200,
                        "response_time": (end_time - start_time) * 1000,
                    }
                )

            except Exception as e:
                recovery_results.append({"success": False, "error": str(e)})

            time.sleep(0.5)

        # Analysis
        load_success_rate = sum(load_results) / len(load_results) if load_results else 0

        successful_recovery = [r for r in recovery_results if r["success"]]
        recovery_rate = len(successful_recovery) / len(recovery_results)

        if successful_recovery:
            avg_recovery_time = sum(
                r["response_time"] for r in successful_recovery
            ) / len(successful_recovery)
        else:
            avg_recovery_time = 0

        log_test_event(
            "sustained_load_recovery",
            load_duration_s=load_duration,
            load_requests_total=len(load_results),
            load_success_rate=load_success_rate,
            recovery_rate=recovery_rate,
            avg_recovery_time_ms=avg_recovery_time,
        )

        print(f"📊 Sustained load: {load_success_rate:.1%} success rate")
        print(
            f"📊 Recovery: {recovery_rate:.1%} success rate, {avg_recovery_time:.0f}ms avg time"
        )

        # System should recover after sustained load
        assert (
            recovery_rate >= 0.8
        ), f"Recovery rate after sustained load too low: {recovery_rate}"
