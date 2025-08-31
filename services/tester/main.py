#!/usr/bin/env python3
"""
Alice v2 Autonomous Testing System
Real-data E2E testing with self-healing capabilities
"""

import asyncio
import time
import pathlib
import yaml
from datetime import datetime
from typing import Dict, List, Any, Optional

from config import TestConfig
from metrics.writer import MetricsWriter  
from remedies.guardian_actions import apply_safe_remediation, analyze_failures
from runners.voice_ws import VoiceTestRunner
from runners.nlu_eval import NLUTestRunner  
from runners.planner_tools import PlannerTestRunner
from runners.deep_eval import DeepTestRunner
from runners.vision_rtsp import VisionTestRunner
from chaos.network_glitch import ChaosTestRunner


class AliceTestOrchestrator:
    """Autonomous test execution with self-healing capabilities"""
    
    def __init__(self, config_path: str = "config.py"):
        self.config = TestConfig()
        self.runners = {
            "voice": VoiceTestRunner(self.config),
            "nlu": NLUTestRunner(self.config), 
            "planner": PlannerTestRunner(self.config),
            "deep": DeepTestRunner(self.config),
            "vision": VisionTestRunner(self.config),
            "chaos": ChaosTestRunner(self.config)
        }
        
    async def run_autonomous_loop(self):
        """Main autonomous testing loop - runs continuously"""
        print("🤖 Alice v2 Autonomous Testing System Started")
        print(f"📊 SLO Targets: Voice E2E <{self.config.SLO_VOICE_E2E_MS}ms, WER <{self.config.SLO_WER_CLEAN*100}%")
        
        while True:
            try:
                await self._execute_test_cycle()
                await asyncio.sleep(self.config.TEST_CYCLE_INTERVAL_S)
            except KeyboardInterrupt:
                print("🛑 Test orchestrator stopped by user")
                break
            except Exception as e:
                print(f"❌ Test cycle error: {e}")
                await asyncio.sleep(60)  # Brief pause before retry
                
    async def _execute_test_cycle(self):
        """Execute one complete test cycle"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        run_dir = pathlib.Path(f"./runs/{timestamp}")
        run_dir.mkdir(parents=True, exist_ok=True)
        
        print(f"🚀 Starting test cycle: {timestamp}")
        
        # Initialize metrics writer
        metrics = MetricsWriter(run_dir)
        
        # Load test scenarios
        scenarios = self._load_scenarios("scenarios.yaml")
        
        # Pre-flight checks
        if not await self._preflight_checks():
            print("❌ Pre-flight checks failed, skipping cycle")
            return
            
        # Execute test scenarios
        results = []
        for scenario in scenarios:
            try:
                result = await self._execute_scenario(scenario)
                if result:
                    results.append(result)
                    metrics.write_result(result)
                    
            except Exception as e:
                print(f"❌ Scenario {scenario.get('id')} failed: {e}")
                metrics.log_error(scenario, str(e))
                
        # Analyze results and apply remediation if needed
        failures = [r for r in results if not r.get("slo_pass", True)]
        if failures:
            print(f"⚠️  Found {len(failures)} SLO violations")
            await self._handle_failures(failures, metrics, run_dir)
            
        # Generate final report
        metrics.generate_summary(results)
        print(f"✅ Test cycle complete: {len(results)} scenarios, {len(failures)} failures")
        
    async def _execute_scenario(self, scenario: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Execute a single test scenario"""
        scenario_id = scenario.get("id", "unknown")
        scenario_kind = scenario.get("kind", "unknown")
        
        print(f"🔬 Running {scenario_id} ({scenario_kind})")
        
        runner = self.runners.get(scenario_kind)
        if not runner:
            print(f"❌ No runner for scenario kind: {scenario_kind}")
            return None
            
        start_time = time.time()
        try:
            result = await runner.execute(scenario)
            result["scenario_id"] = scenario_id
            result["duration_s"] = time.time() - start_time
            result["timestamp"] = datetime.now().isoformat()
            
            # Validate against SLOs
            result["slo_pass"] = self._validate_slo(result, scenario)
            
            status = "✅ PASS" if result["slo_pass"] else "❌ FAIL"
            print(f"  {status} {scenario_id}: {result.get('summary', 'completed')}")
            
            return result
            
        except Exception as e:
            print(f"❌ {scenario_id} execution error: {e}")
            return {
                "scenario_id": scenario_id,
                "error": str(e),
                "slo_pass": False,
                "timestamp": datetime.now().isoformat()
            }
    
    async def _handle_failures(self, failures: List[Dict], metrics: MetricsWriter, run_dir: pathlib.Path):
        """Analyze failures and apply safe remediation"""
        print("🔧 Analyzing failures for remediation opportunities...")
        
        # Group failures by type for targeted remediation
        failure_analysis = analyze_failures(failures)
        
        for failure_type, failed_scenarios in failure_analysis.items():
            print(f"  📊 {failure_type}: {len(failed_scenarios)} scenarios")
            
            # Apply remediation if safe and effective
            remediation_applied = await apply_safe_remediation(failure_type, failed_scenarios, self.config)
            
            if remediation_applied:
                print(f"  🔧 Applied remediation for {failure_type}")
                metrics.log_remediation(failure_type, remediation_applied)
                
                # Re-run only the failed scenarios to validate fix
                await self._validate_remediation(failed_scenarios, metrics)
            else:
                print(f"  ⚠️  No safe remediation available for {failure_type}")
                # Create issue report for manual investigation
                self._create_issue_report(failure_type, failed_scenarios, run_dir)
                
    async def _validate_remediation(self, failed_scenarios: List[str], metrics: MetricsWriter):
        """Re-run failed scenarios to validate remediation effectiveness"""
        print("🔄 Validating remediation by re-running failed scenarios...")
        
        scenarios = self._load_scenarios("scenarios.yaml")
        rerun_scenarios = [s for s in scenarios if s.get("id") in failed_scenarios]
        
        for scenario in rerun_scenarios:
            result = await self._execute_scenario(scenario)
            if result:
                metrics.write_result(result, rerun=True)
                status = "✅ FIXED" if result["slo_pass"] else "❌ STILL FAILING"
                print(f"  {status} {scenario['id']}")
    
    def _validate_slo(self, result: Dict[str, Any], scenario: Dict[str, Any]) -> bool:
        """Validate test result against SLO targets"""
        scenario_kind = scenario.get("kind")
        
        # Voice pipeline SLOs
        if scenario_kind == "voice":
            if result.get("wer", 0) > self.config.SLO_WER_CLEAN:
                return False
            if result.get("asr_final_ms", 0) > self.config.SLO_ASR_FINAL_MS:
                return False
                
        # LLM performance SLOs  
        elif scenario_kind in ["planner", "deep"]:
            target_ms = getattr(self.config, f"SLO_{scenario_kind.upper()}_FIRST_MS")
            if result.get("llm_first_ms", 0) > target_ms:
                return False
                
        # Tool success SLOs
        if result.get("tool_success") is not None:
            if result["tool_success"] < self.config.SLO_TOOL_SUCCESS_RATE:
                return False
                
        return True
        
    async def _preflight_checks(self) -> bool:
        """Verify all services are healthy before testing"""
        import httpx
        
        checks = [
            (f"{self.config.API_BASE}/health", "Orchestrator"),
            (f"{self.config.GUARDIAN_URL}/guardian/health", "Guardian"),
            (f"{self.config.API_BASE.replace('8000', '8001')}/health", "Voice Service")
        ]
        
        async with httpx.AsyncClient(timeout=5.0) as client:
            for url, service in checks:
                try:
                    response = await client.get(url)
                    if response.status_code != 200:
                        print(f"❌ {service} health check failed: {response.status_code}")
                        return False
                    print(f"✅ {service} healthy")
                except Exception as e:
                    print(f"❌ {service} unreachable: {e}")
                    return False
                    
        return True
        
    def _load_scenarios(self, yaml_path: str) -> List[Dict[str, Any]]:
        """Load test scenarios from YAML file"""
        try:
            with open(yaml_path, 'r') as f:
                data = yaml.safe_load(f)
                return data.get("scenarios", [])
        except FileNotFoundError:
            print(f"❌ Scenarios file not found: {yaml_path}")
            return []
        except yaml.YAMLError as e:
            print(f"❌ Invalid YAML in {yaml_path}: {e}")
            return []
            
    def _create_issue_report(self, failure_type: str, scenarios: List[str], run_dir: pathlib.Path):
        """Create detailed issue report for manual investigation"""
        issue_file = run_dir / "issue.md"
        
        with open(issue_file, "w") as f:
            f.write(f"# Alice v2 Test Failure Report\n\n")
            f.write(f"**Failure Type**: {failure_type}\n")
            f.write(f"**Affected Scenarios**: {', '.join(scenarios)}\n") 
            f.write(f"**Timestamp**: {datetime.now().isoformat()}\n\n")
            f.write(f"## Summary\n")
            f.write(f"Automated remediation was unable to resolve this issue. Manual investigation required.\n\n")
            f.write(f"## Next Steps\n")
            f.write(f"1. Review detailed logs in `log.jsonl`\n")
            f.write(f"2. Check service health and resource usage\n") 
            f.write(f"3. Investigate root cause in affected components\n")
            f.write(f"4. Update remediation rules if appropriate\n")
            
        print(f"📋 Created issue report: {issue_file}")


async def main():
    """Main entry point"""
    orchestrator = AliceTestOrchestrator()
    await orchestrator.run_autonomous_loop()


if __name__ == "__main__":
    asyncio.run(main())