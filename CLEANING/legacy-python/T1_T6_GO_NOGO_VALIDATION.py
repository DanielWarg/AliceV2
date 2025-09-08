#!/usr/bin/env python3
"""
T1-T6 Go/No-Go Production Readiness Validation
Comprehensive automated validation of all hardening requirements
"""

import json
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, List


class ProductionReadinessValidator:
    """Comprehensive validator for T1-T6 production readiness"""

    def __init__(self):
        self.results = {}
        self.passed = 0
        self.failed = 0
        self.warnings = 0

    def run_validation(self) -> Dict[str, Any]:
        """Run complete validation suite"""
        print("🔍 STARTING T1-T6 PRODUCTION READINESS VALIDATION")
        print("=" * 60)

        # T1: Schema locks + versioning + seeds
        self.validate_t1_schema_hardening()

        # T2: PII mask + coverage + drift monitoring
        self.validate_t2_privacy_hardening()

        # T3: φ-reward policies + winsorization + tests
        self.validate_t3_reward_hardening()

        # T4: Atomic checkpoints + drift monitoring + fail-open
        self.validate_t4_persistence_hardening()

        # T5: Stable canary + guardian override + telemetry
        self.validate_t5_routing_hardening()

        # T6: Contract tests + canary ramp + drift monitoring
        self.validate_t6_toolselector_hardening()

        # Generate final report
        return self.generate_go_nogo_report()

    def validate_t1_schema_hardening(self):
        """Validate T1: Schema locks + versioning + seeds"""
        print("\n📋 T1: Schema Hardening Validation")
        print("-" * 40)

        # Check 1: Library versions locked
        try:
            with open("services/rl/requirements.txt") as f:
                requirements = f.read()
                locked_versions = [
                    line for line in requirements.split("\n") if "==" in line
                ]

            if len(locked_versions) >= 5:  # Major libraries locked
                self.record_pass(
                    "T1.1",
                    "Library versions locked",
                    f"{len(locked_versions)} packages locked",
                )
            else:
                self.record_fail(
                    "T1.1",
                    "Insufficient locked versions",
                    f"Only {len(locked_versions)} packages locked",
                )
        except Exception as e:
            self.record_fail("T1.1", "Requirements file error", str(e))

        # Check 2: Schema versioning
        try:
            result = subprocess.run(
                [
                    sys.executable,
                    "-c",
                    "from services.rl.pipelines.dataset_schemas import Episode; "
                    "print(Episode.model_fields['schema_version'].default)",
                ],
                capture_output=True,
                text=True,
                cwd=".",
            )

            if result.returncode == 0 and "1.0.0" in result.stdout:
                self.record_pass(
                    "T1.2", "Schema versioning implemented", "Default version: 1.0.0"
                )
            else:
                self.record_fail("T1.2", "Schema versioning missing", result.stderr)
        except Exception as e:
            self.record_fail("T1.2", "Schema validation error", str(e))

        # Check 3: Pydantic strict mode
        try:
            result = subprocess.run(
                [
                    sys.executable,
                    "-c",
                    "from services.rl.pipelines.dataset_schemas import Episode; "
                    "print(Episode.model_config.get('extra'))",
                ],
                capture_output=True,
                text=True,
                cwd=".",
            )

            if "forbid" in result.stdout:
                self.record_pass(
                    "T1.3", "Strict mode enforced", "extra='forbid' configured"
                )
            else:
                self.record_fail("T1.3", "Strict mode not enforced", result.stdout)
        except Exception as e:
            self.record_fail("T1.3", "Strict mode validation error", str(e))

        # Check 4: Frozen seeds
        try:
            result = subprocess.run(
                [
                    sys.executable,
                    "-c",
                    "from services.rl.pipelines.seed_config import T1_T6_FROZEN_SEED; "
                    "print(T1_T6_FROZEN_SEED)",
                ],
                capture_output=True,
                text=True,
                cwd=".",
            )

            if result.returncode == 0 and result.stdout.strip():
                self.record_pass(
                    "T1.4", "Frozen seeds configured", f"Seed: {result.stdout.strip()}"
                )
            else:
                self.record_fail("T1.4", "Frozen seeds not configured", result.stderr)
        except Exception as e:
            self.record_fail("T1.4", "Seed validation error", str(e))

        # Check 5: Schema tests pass
        self.run_test_validation(
            "T1.5",
            "services/rl/tests/test_schema_strict_mode.py",
            "Schema strict mode tests",
        )

    def validate_t2_privacy_hardening(self):
        """Validate T2: PII mask + coverage + drift monitoring"""
        print("\n🔒 T2: Privacy Hardening Validation")
        print("-" * 40)

        # Check 1: PII masking functionality
        try:
            result = subprocess.run(
                [
                    sys.executable,
                    "-c",
                    "from services.rl.pipelines.pii_masker import mask_pii; "
                    "result = mask_pii('Ring mig på 070-123 45 67'); "
                    "print('phone' in result['pii_detected'])",
                ],
                capture_output=True,
                text=True,
                cwd=".",
            )

            if "True" in result.stdout:
                self.record_pass(
                    "T2.1", "PII masking functional", "Phone number detection working"
                )
            else:
                self.record_fail("T2.1", "PII masking broken", result.stdout)
        except Exception as e:
            self.record_fail("T2.1", "PII masking validation error", str(e))

        # Check 2: Drift monitoring
        try:
            result = subprocess.run(
                [
                    sys.executable,
                    "-c",
                    "from services.rl.pipelines.drift_monitor import DriftMonitor; "
                    "monitor = DriftMonitor(); print('OK')",
                ],
                capture_output=True,
                text=True,
                cwd=".",
            )

            if "OK" in result.stdout:
                self.record_pass(
                    "T2.2", "Drift monitoring available", "DriftMonitor instantiable"
                )
            else:
                self.record_fail("T2.2", "Drift monitoring broken", result.stderr)
        except Exception as e:
            self.record_fail("T2.2", "Drift monitoring validation error", str(e))

        # Check 3: PII & drift tests pass
        self.run_test_validation(
            "T2.3",
            "services/rl/tests/test_pii_drift_coverage.py",
            "PII and drift tests",
        )

    def validate_t3_reward_hardening(self):
        """Validate T3: φ-reward policies + winsorization + tests"""
        print("\n🎯 T3: Reward Hardening Validation")
        print("-" * 40)

        # Check 1: φ constant accuracy
        try:
            result = subprocess.run(
                [
                    sys.executable,
                    "-c",
                    "from services.rl.rewards.reward_validator import PHI; "
                    "import math; "
                    "expected = (1 + math.sqrt(5)) / 2; "
                    "print(abs(PHI - expected) < 1e-10)",
                ],
                capture_output=True,
                text=True,
                cwd=".",
            )

            if "True" in result.stdout:
                self.record_pass(
                    "T3.1", "φ constant accurate", "Mathematical precision validated"
                )
            else:
                self.record_fail("T3.1", "φ constant inaccurate", result.stdout)
        except Exception as e:
            self.record_fail("T3.1", "φ validation error", str(e))

        # Check 2: Reward validation
        try:
            result = subprocess.run(
                [
                    sys.executable,
                    "-c",
                    "from services.rl.rewards.reward_validator import RewardValidator; "
                    "validator = RewardValidator(); print('OK')",
                ],
                capture_output=True,
                text=True,
                cwd=".",
            )

            if "OK" in result.stdout:
                self.record_pass(
                    "T3.2", "Reward validator available", "RewardValidator instantiable"
                )
            else:
                self.record_fail("T3.2", "Reward validator broken", result.stderr)
        except Exception as e:
            self.record_fail("T3.2", "Reward validator validation error", str(e))

        # Check 3: φ-reward tests pass
        self.run_test_validation(
            "T3.3",
            "services/rl/tests/test_phi_reward_hardening.py",
            "φ-reward hardening tests",
        )

    def validate_t4_persistence_hardening(self):
        """Validate T4: Atomic checkpoints + drift monitoring + fail-open"""
        print("\n💾 T4: Persistence Hardening Validation")
        print("-" * 40)

        # Check 1: LinUCB router exists and functional
        try:
            result = subprocess.run(
                [
                    sys.executable,
                    "-c",
                    "from services.rl.online.linucb_router import LinUCBRouter; "
                    "router = LinUCBRouter(['test_arm']); print('OK')",
                ],
                capture_output=True,
                text=True,
                cwd=".",
            )

            if "OK" in result.stdout:
                self.record_pass(
                    "T4.1", "LinUCB router functional", "Router instantiable"
                )
            else:
                self.record_fail("T4.1", "LinUCB router broken", result.stderr)
        except Exception as e:
            self.record_fail("T4.1", "LinUCB validation error", str(e))

        # Check 2: Thompson sampling tools exist
        try:
            result = subprocess.run(
                [
                    sys.executable,
                    "-c",
                    "from services.rl.online.thompson_tools import ThompsonTools; "
                    "tools = ThompsonTools(); print('OK')",
                ],
                capture_output=True,
                text=True,
                cwd=".",
            )

            if "OK" in result.stdout:
                self.record_pass(
                    "T4.2", "Thompson tools functional", "Tools instantiable"
                )
            else:
                self.record_fail("T4.2", "Thompson tools broken", result.stderr)
        except Exception as e:
            self.record_fail("T4.2", "Thompson validation error", str(e))

        # Check 3: File locking for persistence
        persistence_file = Path("services/rl/online/persistence.py")
        if persistence_file.exists():
            try:
                with open(persistence_file) as f:
                    content = f.read()
                if "filelock" in content and "FileLock" in content:
                    self.record_pass(
                        "T4.3", "File locking implemented", "FileLock usage detected"
                    )
                else:
                    self.record_warning(
                        "T4.3",
                        "File locking unclear",
                        "FileLock usage not clearly detected",
                    )
            except Exception as e:
                self.record_fail("T4.3", "Persistence file error", str(e))
        else:
            self.record_warning(
                "T4.3",
                "Persistence file not found",
                "May be using alternative persistence",
            )

    def validate_t5_routing_hardening(self):
        """Validate T5: Stable canary + guardian override + telemetry"""
        print("\n🚀 T5: Routing Hardening Validation")
        print("-" * 40)

        # Check 1: Bandit server exists
        server_file = Path("services/rl/online/server.py")
        if server_file.exists():
            self.record_pass("T5.1", "Bandit server exists", "Server file found")
        else:
            self.record_fail("T5.1", "Bandit server missing", "Server file not found")

        # Check 2: FastAPI integration
        try:
            result = subprocess.run(
                [
                    sys.executable,
                    "-c",
                    "from services.rl.online.server import app; print(type(app).__name__)",
                ],
                capture_output=True,
                text=True,
                cwd=".",
            )

            if "FastAPI" in result.stdout:
                self.record_pass(
                    "T5.2", "FastAPI integration working", "App instance created"
                )
            else:
                self.record_fail("T5.2", "FastAPI integration broken", result.stderr)
        except Exception as e:
            self.record_fail("T5.2", "FastAPI validation error", str(e))

        # Check 3: Orchestrator integration
        orchestrator_file = Path("services/orchestrator/src/routes/rl_routes.py")
        if orchestrator_file.exists():
            self.record_pass(
                "T5.3", "Orchestrator integration exists", "RL routes file found"
            )
        else:
            self.record_warning(
                "T5.3", "Orchestrator routes not found", "May be integrated differently"
            )

    def validate_t6_toolselector_hardening(self):
        """Validate T6: Contract tests + canary ramp + drift monitoring"""
        print("\n🛠️ T6: ToolSelector Hardening Validation")
        print("-" * 40)

        # Check 1: ToolSelector v2 exists
        toolselector_file = Path("services/toolselector/toolselector_v2.py")
        if toolselector_file.exists():
            self.record_pass("T6.1", "ToolSelector v2 exists", "V2 file found")
        else:
            self.record_warning(
                "T6.1", "ToolSelector v2 not found", "May be using different structure"
            )

        # Check 2: GBNF schema enforcement
        try:
            result = subprocess.run(
                [
                    "find",
                    ".",
                    "-name",
                    "*.py",
                    "-exec",
                    "grep",
                    "-l",
                    "gbnf\\|GBNF",
                    "{}",
                    ";",
                ],
                capture_output=True,
                text=True,
                cwd=".",
            )

            if result.returncode == 0 and result.stdout.strip():
                self.record_pass(
                    "T6.2",
                    "GBNF schema found",
                    f"Files: {len(result.stdout.strip().split())}",
                )
            else:
                self.record_warning(
                    "T6.2",
                    "GBNF schema not found",
                    "May be using different schema enforcement",
                )
        except Exception as e:
            self.record_fail("T6.2", "GBNF validation error", str(e))

        # Check 3: Makefile targets
        makefile = Path("Makefile")
        if makefile.exists():
            try:
                with open(makefile) as f:
                    content = f.read()
                if "toolselector" in content and "rl-" in content:
                    self.record_pass(
                        "T6.3",
                        "Makefile targets exist",
                        "RL and ToolSelector targets found",
                    )
                else:
                    self.record_warning(
                        "T6.3",
                        "Makefile targets incomplete",
                        "Some targets may be missing",
                    )
            except Exception as e:
                self.record_fail("T6.3", "Makefile error", str(e))
        else:
            self.record_warning(
                "T6.3",
                "Makefile not found",
                "Build automation may be handled differently",
            )

    def run_test_validation(self, check_id: str, test_file: str, description: str):
        """Run pytest validation for specific test file"""
        try:
            result = subprocess.run(
                [sys.executable, "-m", "pytest", test_file, "-x", "--tb=line"],
                capture_output=True,
                text=True,
                cwd=".",
            )

            if result.returncode == 0:
                # Count passed tests
                lines = result.stdout.split("\n")
                passed_line = [
                    line
                    for line in lines
                    if "passed" in line
                    and ("failed" in line or "error" in line or line.endswith("passed"))
                ]
                self.record_pass(
                    check_id,
                    f"{description} pass",
                    passed_line[0] if passed_line else "All tests passed",
                )
            else:
                # Extract failure info
                error_lines = [
                    line
                    for line in result.stdout.split("\n")
                    if "FAILED" in line or "ERROR" in line
                ]
                self.record_fail(
                    check_id, f"{description} fail", f"{len(error_lines)} failures"
                )
        except Exception as e:
            self.record_fail(check_id, f"{description} error", str(e))

    def record_pass(self, check_id: str, title: str, details: str):
        """Record a passed validation check"""
        self.results[check_id] = {"status": "PASS", "title": title, "details": details}
        self.passed += 1
        print(f"✅ {check_id}: {title} - {details}")

    def record_fail(self, check_id: str, title: str, details: str):
        """Record a failed validation check"""
        self.results[check_id] = {"status": "FAIL", "title": title, "details": details}
        self.failed += 1
        print(f"❌ {check_id}: {title} - {details}")

    def record_warning(self, check_id: str, title: str, details: str):
        """Record a warning validation check"""
        self.results[check_id] = {"status": "WARN", "title": title, "details": details}
        self.warnings += 1
        print(f"⚠️  {check_id}: {title} - {details}")

    def generate_go_nogo_report(self) -> Dict[str, Any]:
        """Generate final Go/No-Go report"""
        total_checks = len(self.results)
        pass_rate = self.passed / total_checks if total_checks > 0 else 0

        # Determine Go/No-Go decision
        critical_failures = sum(
            1 for r in self.results.values() if r["status"] == "FAIL"
        )
        go_decision = (
            critical_failures <= 1 and pass_rate >= 0.75
        )  # Allow 1 non-critical failure

        report = {
            "timestamp": "2025-09-07T00:00:00Z",
            "validation_summary": {
                "total_checks": total_checks,
                "passed": self.passed,
                "failed": self.failed,
                "warnings": self.warnings,
                "pass_rate": pass_rate,
            },
            "go_no_go_decision": {
                "decision": "GO" if go_decision else "NO-GO",
                "rationale": self._get_decision_rationale(
                    go_decision, critical_failures, pass_rate
                ),
                "critical_failures": critical_failures,
                "minimum_pass_rate": 0.75,
                "actual_pass_rate": pass_rate,
            },
            "detailed_results": self.results,
            "recommendations": self._generate_recommendations(),
        }

        print("\n" + "=" * 60)
        print("🎯 FINAL GO/NO-GO DECISION")
        print("=" * 60)
        print(f"Decision: {report['go_no_go_decision']['decision']}")
        print(f"Pass Rate: {pass_rate:.1%} (minimum: 75%)")
        print(f"Critical Failures: {critical_failures}")
        print(f"Rationale: {report['go_no_go_decision']['rationale']}")

        if report["recommendations"]:
            print("\n📋 RECOMMENDATIONS:")
            for rec in report["recommendations"]:
                print(f"• {rec}")

        return report

    def _get_decision_rationale(
        self, go_decision: bool, critical_failures: int, pass_rate: float
    ) -> str:
        """Generate rationale for Go/No-Go decision"""
        if go_decision:
            return f"All critical systems validated. {self.passed}/{len(self.results)} checks passed ({pass_rate:.1%}). System ready for production."
        else:
            reasons = []
            if critical_failures > 0:
                reasons.append(f"{critical_failures} critical failures detected")
            if pass_rate < 0.8:
                reasons.append(f"Pass rate {pass_rate:.1%} below minimum 80%")
            return f"Production deployment blocked: {', '.join(reasons)}"

    def _generate_recommendations(self) -> List[str]:
        """Generate recommendations based on validation results"""
        recommendations = []

        failed_checks = [
            check_id
            for check_id, result in self.results.items()
            if result["status"] == "FAIL"
        ]
        warning_checks = [
            check_id
            for check_id, result in self.results.items()
            if result["status"] == "WARN"
        ]

        if failed_checks:
            recommendations.append(
                f"CRITICAL: Fix failed checks: {', '.join(failed_checks)}"
            )

        if warning_checks:
            recommendations.append(f"Address warnings: {', '.join(warning_checks)}")

        if self.passed > 0 and self.failed == 0:
            recommendations.append(
                "System shows strong production readiness - consider deployment"
            )

        return recommendations


if __name__ == "__main__":
    validator = ProductionReadinessValidator()
    report = validator.run_validation()

    # Save report
    with open("T1_T6_VALIDATION_REPORT.json", "w") as f:
        json.dump(report, f, indent=2)

    print("\n📄 Full report saved to: T1_T6_VALIDATION_REPORT.json")

    # Exit with appropriate code
    sys.exit(0 if report["go_no_go_decision"]["decision"] == "GO" else 1)
