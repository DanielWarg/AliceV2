"""
Pytest Configuration with Structured JSON Logging
Captures all test data for Alice's continuous learning system
"""

import pytest
import json
import time
import os
from datetime import datetime
from pathlib import Path


class TestMetricsCollector:
    """Collects structured test metrics for Alice's learning system"""
    
    def __init__(self):
        self.start_time = None
        self.test_results = []
        self.session_id = f"test_session_{int(time.time())}"
        
        # Create test-results directory structure  
        base_dir = Path(__file__).parent.parent.parent.parent.parent / "test-results"  # Absolute path to repo root/test-results
        timestamp = datetime.now().strftime('%Y%m%d_%H%M')
        
        self.log_dir = base_dir / "raw-logs" / timestamp
        self.log_dir.mkdir(parents=True, exist_ok=True)
        
        # JSON lines log file
        self.log_file = self.log_dir / f"test_session_{int(time.time())}.jsonl"

    def log_event(self, event_type: str, data: dict):
        """Log structured test event"""
        event = {
            "timestamp": datetime.now().isoformat(),
            "session_id": self.session_id,
            "event_type": event_type,
            "data": data
        }
        
        # Append to JSONL file
        with open(self.log_file, "a") as f:
            f.write(json.dumps(event) + "\n")

    def pytest_sessionstart(self, session):
        """Called when test session starts"""
        self.start_time = time.time()
        
        self.log_event("session_start", {
            "pytest_version": pytest.__version__,
            "test_directory": str(Path.cwd()),
            "python_version": session.config.getoption("--tb"),
        })

    def pytest_runtest_setup(self, item):
        """Called before each test"""
        self.log_event("test_setup", {
            "test_name": item.name,
            "test_module": item.module.__name__ if item.module else None,
            "test_class": item.cls.__name__ if item.cls else None,
        })

    def pytest_runtest_call(self, item):
        """Called during test execution"""
        start_time = time.time()
        item.test_start_time = start_time

    def pytest_runtest_teardown(self, item, nextitem):
        """Called after test execution"""
        if hasattr(item, 'test_start_time'):
            duration = time.time() - item.test_start_time
            
            # Get test result from item's report
            test_result = getattr(item, '_test_outcome', 'unknown')
            
            self.log_event("test_complete", {
                "test_name": item.name,
                "duration_ms": int(duration * 1000),
                "outcome": test_result,
            })

    def pytest_runtest_logreport(self, report):
        """Called when test report is available"""
        if report.when == "call":  # Only log the actual test call, not setup/teardown
            
            # Extract useful metrics from test
            test_data = {
                "test_name": report.nodeid.split("::")[-1],
                "test_module": report.nodeid.split("::")[0],
                "outcome": report.outcome,
                "duration_ms": int(report.duration * 1000),
                "failed": report.failed,
                "passed": report.passed,
                "skipped": report.skipped,
            }
            
            # Add failure details if test failed
            if report.failed and report.longrepr:
                test_data["failure_reason"] = str(report.longrepr).split('\n')[-2] if '\n' in str(report.longrepr) else str(report.longrepr)
                test_data["failure_type"] = report.longrepr.reprcrash.message if hasattr(report.longrepr, 'reprcrash') else "unknown"

            # Add performance metrics if available
            if hasattr(report, 'user_properties'):
                for key, value in report.user_properties:
                    if key.startswith('metric_'):
                        test_data[key] = value

            self.log_event("test_result", test_data)
            self.test_results.append(test_data)

    def pytest_sessionfinish(self, session, exitstatus):
        """Called when test session finishes"""
        total_duration = time.time() - self.start_time if self.start_time else 0
        
        # Calculate summary statistics
        total_tests = len(self.test_results)
        passed_tests = sum(1 for r in self.test_results if r['passed'])
        failed_tests = sum(1 for r in self.test_results if r['failed'])
        avg_duration = sum(r['duration_ms'] for r in self.test_results) / total_tests if total_tests > 0 else 0
        
        session_summary = {
            "total_duration_ms": int(total_duration * 1000),
            "total_tests": total_tests,
            "passed_tests": passed_tests,
            "failed_tests": failed_tests,
            "success_rate": passed_tests / total_tests if total_tests > 0 else 0,
            "average_test_duration_ms": int(avg_duration),
            "exit_status": exitstatus,
            "test_efficiency_score": passed_tests / (total_duration + 1),  # Tests per second
        }
        
        self.log_event("session_complete", session_summary)
        
        # Create summary JSON in summaries directory
        base_dir = Path(__file__).parent.parent.parent.parent.parent / "test-results"  # Same as in __init__
        summary_dir = base_dir / "summaries" / "daily"
        summary_dir.mkdir(parents=True, exist_ok=True)
        summary_file = summary_dir / f"{datetime.now().strftime('%Y%m%d')}_summary.json"
        summary_data = {
            "session_id": self.session_id,
            "timestamp": datetime.now().isoformat(),
            "summary": session_summary,
            "test_details": self.test_results
        }
        
        with open(summary_file, "w") as f:
            json.dump(summary_data, f, indent=2)
            
        # Print summary for immediate feedback
        print(f"\n🔍 Test Metrics Logged:")
        print(f"   📊 Success Rate: {session_summary['success_rate']:.1%}")
        print(f"   ⏱️  Avg Duration: {session_summary['average_test_duration_ms']}ms")
        print(f"   📝 Log File: {self.log_file}")
        print(f"   📋 Summary: {summary_file}")


# Global collector instance
collector = TestMetricsCollector()

# Register pytest hooks
pytest_sessionstart = collector.pytest_sessionstart
pytest_runtest_setup = collector.pytest_runtest_setup  
pytest_runtest_call = collector.pytest_runtest_call
pytest_runtest_teardown = collector.pytest_runtest_teardown
pytest_runtest_logreport = collector.pytest_runtest_logreport
pytest_sessionfinish = collector.pytest_sessionfinish


@pytest.fixture
def test_metrics():
    """Fixture to add custom metrics to tests"""
    def add_metric(name: str, value):
        """Add custom metric that will be logged"""
        # This gets picked up by the test reporter
        return pytest.current_request.node.user_properties.append((f"metric_{name}", value))
    
    return add_metric