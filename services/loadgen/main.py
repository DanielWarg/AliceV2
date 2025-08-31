#!/usr/bin/env python3
"""
Load Generator Main - Orchestrate stress tests and measure Guardian SLO
=======================================================================
"""

import os
import time
import json
import pathlib
import yaml
import traceback
from datetime import datetime
from typing import Dict, Any

# Import stress test modules
from burners.deep_bomb import run as deep_bomb
from burners.memory_balloon import run as memory_balloon  
from burners.cpu_spin import run as cpu_spin
from burners.tool_storm import run as tool_storm
from burners.vision_stress import run as vision_stress

# Import watchers
from watchers import GuardianWatcher, write_guardian_event, write_slo_result

# Configuration
RUN_DIR = f"/data/telemetry/loadgen_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"
SCENARIOS_FILE = "scenarios.yaml"

def load_scenarios() -> Dict[str, Any]:
    """Load test scenarios from YAML"""
    try:
        with open(SCENARIOS_FILE, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)
    except Exception as e:
        print(f"❌ Failed to load scenarios: {e}")
        # Return default scenarios
        return {
            "version": 1,
            "steps": [
                {"id": "deep_bomb", "kind": "deep_bomb", "seconds": 30},
                {"id": "memory_balloon", "kind": "memory_balloon", "gb": 4, "hold_seconds": 60}
            ]
        }

def execute_stress_scenario(scenarios: Dict[str, Any]) -> Dict[str, Any]:
    """Execute the stress test scenario steps"""
    print(f"\n🚀 Executing Stress Test Scenario")
    print(f"Version: {scenarios.get('version', 'unknown')}")
    print(f"Steps: {len(scenarios.get('steps', []))}")
    
    results = {}
    total_start = time.perf_counter()
    
    for step in scenarios.get("steps", []):
        step_id = step.get("id", "unknown")
        step_kind = step.get("kind", "unknown")
        
        print(f"\n📋 Step: {step_id} ({step_kind})")
        step_start = time.perf_counter()
        
        try:
            if step_kind == "deep_bomb":
                result = deep_bomb(
                    seconds=step.get("seconds", 30),
                    concurrency=step.get("params", {}).get("concurrency", 2)
                )
            elif step_kind == "memory_balloon":
                result = memory_balloon(
                    gb=step.get("gb", 4),
                    hold_seconds=step.get("hold_seconds", 60)
                )
            elif step_kind == "cpu_spin":
                result = cpu_spin(
                    threads=step.get("threads", 4),
                    seconds=step.get("seconds", 30)
                )
            elif step_kind == "tool_storm":
                result = tool_storm(
                    rps=step.get("rps", 2),
                    seconds=step.get("seconds", 20)
                )
            elif step_kind == "vision_stress":
                result = vision_stress(
                    seconds=step.get("seconds", 30)
                )
            else:
                print(f"   ⚠️  Unknown step kind: {step_kind}")
                result = {"error": f"Unknown step kind: {step_kind}"}
            
            step_duration = time.perf_counter() - step_start
            result["step_duration_s"] = round(step_duration, 2)
            results[step_id] = result
            
        except Exception as e:
            print(f"   ❌ Step failed: {e}")
            results[step_id] = {
                "error": str(e),
                "traceback": traceback.format_exc(),
                "step_duration_s": round(time.perf_counter() - step_start, 2)
            }
    
    total_duration = time.perf_counter() - total_start
    results["_meta"] = {
        "total_duration_s": round(total_duration, 2),
        "completed_steps": len([r for r in results.values() if not isinstance(r, dict) or "error" not in r]),
        "failed_steps": len([r for r in results.values() if isinstance(r, dict) and "error" in r])
    }
    
    return results

def main():
    """Main load generator orchestration"""
    print("🎯 Alice v2 Load Generator - Brownout SLO Validation")
    print("=" * 60)
    print(f"Run Directory: {RUN_DIR}")
    print(f"Timestamp: {datetime.utcnow().isoformat()}Z")
    
    # Create run directory
    pathlib.Path(RUN_DIR).mkdir(parents=True, exist_ok=True)
    
    # Load scenarios
    scenarios = load_scenarios()
    
    # Initialize Guardian watcher
    watcher = GuardianWatcher()
    
    try:
        # Get baseline Guardian state
        print(f"\n📊 Baseline Guardian State")
        baseline_state = watcher.poll_guardian()
        print(f"   State: {baseline_state.get('status', 'UNKNOWN')}")
        print(f"   RAM: {baseline_state.get('metrics', {}).get('ram_pct', 0):.1f}%")
        print(f"   CPU: {baseline_state.get('metrics', {}).get('cpu_pct', 0):.1f}%")
        
        write_guardian_event({
            "event": "baseline",
            "guardian_state": baseline_state
        }, RUN_DIR)
        
        # Start stress test and measure brownout trigger
        print(f"\n⚡ Starting Aggressive Load...")
        stress_start = time.perf_counter()
        
        # Execute stress scenario in background while watching Guardian
        import threading
        stress_results = {}
        stress_exception = None
        
        def run_stress():
            nonlocal stress_results, stress_exception
            try:
                stress_results = execute_stress_scenario(scenarios)
            except Exception as e:
                stress_exception = e
        
        stress_thread = threading.Thread(target=run_stress)
        stress_thread.start()
        
        # Wait for brownout trigger while stress test runs
        print(f"\n⏱️  Measuring Brownout Trigger Latency...")
        trigger_latency_ms, brownout_state = watcher.wait_for_brownout(stress_start)
        
        write_guardian_event({
            "event": "brownout_triggered", 
            "trigger_latency_ms": trigger_latency_ms,
            "guardian_state": brownout_state
        }, RUN_DIR)
        
        # Wait for stress test to complete
        stress_thread.join(timeout=300)  # 5 minute max
        
        if stress_thread.is_alive():
            print(f"⚠️  Stress test still running after timeout")
        
        if stress_exception:
            print(f"❌ Stress test failed: {stress_exception}")
        
        # Measure recovery time
        print(f"\n🔄 Measuring Recovery Time...")
        recovery_time_s = watcher.wait_for_recovery()
        
        write_guardian_event({
            "event": "recovery_complete",
            "recovery_time_s": recovery_time_s,
            "guardian_state": watcher.poll_guardian()
        }, RUN_DIR)
        
        # Final Guardian state
        final_state = watcher.poll_guardian()
        print(f"\n📊 Final Guardian State")
        print(f"   State: {final_state.get('status', 'UNKNOWN')}")
        print(f"   RAM: {final_state.get('metrics', {}).get('ram_pct', 0):.1f}%")
        print(f"   CPU: {final_state.get('metrics', {}).get('cpu_pct', 0):.1f}%")
        
        # Write comprehensive summary
        summary = {
            "test_metadata": {
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "run_directory": RUN_DIR,
                "scenario_version": scenarios.get("version", 1)
            },
            "guardian_slo": {
                "trigger_latency_ms": trigger_latency_ms,
                "recovery_time_s": recovery_time_s,
                "baseline_state": baseline_state,
                "brownout_state": brownout_state,
                "final_state": final_state
            },
            "stress_test_results": stress_results,
            "environment": {
                "api_base": os.getenv("API_BASE", "http://localhost:8000"),
                "guard_health": os.getenv("GUARD_HEALTH", "http://localhost:8787/health"),
                "camera_rtsp": os.getenv("CAMERA_RTSP_URL") is not None
            }
        }
        
        # Write summary
        summary_file = pathlib.Path(RUN_DIR) / "summary.json"
        with open(summary_file, 'w', encoding='utf-8') as f:
            json.dump(summary, f, indent=2, ensure_ascii=False)
        
        # Evaluate and write SLO result
        slo_pass = write_slo_result(RUN_DIR, trigger_latency_ms, recovery_time_s)
        
        # Final results
        print(f"\n🎯 BROWNOUT SLO VALIDATION RESULTS")
        print("=" * 60)
        
        if trigger_latency_ms is not None:
            budget_ms = int(os.getenv("SLO_BROWNOUT_TRIGGER_MS", "150"))
            trigger_status = "✅ PASS" if trigger_latency_ms <= budget_ms else "❌ FAIL"
            print(f"Brownout Trigger: {trigger_latency_ms}ms (budget: {budget_ms}ms) {trigger_status}")
        else:
            print(f"Brownout Trigger: ❌ FAIL (No brownout detected)")
        
        if recovery_time_s is not None:
            budget_s = int(os.getenv("RECOVER_S", "60"))
            recovery_status = "✅ PASS" if recovery_time_s <= budget_s else "❌ FAIL"
            print(f"Recovery Time: {recovery_time_s}s (budget: {budget_s}s) {recovery_status}")
        else:
            print(f"Recovery Time: ❌ FAIL (No recovery detected)")
        
        overall_status = "✅ PASS" if slo_pass else "❌ FAIL"
        print(f"Overall SLO: {overall_status}")
        
        print(f"\n📁 Results saved to: {RUN_DIR}")
        print(f"   summary.json - Complete test results")
        print(f"   slo_result.json - SLO compliance details")
        print(f"   result.txt - Simple PASS/FAIL")
        print(f"   guardian_events.jsonl - Guardian state transitions")
        
        return 0 if slo_pass else 1
        
    except Exception as e:
        print(f"\n❌ Load generator failed: {e}")
        traceback.print_exc()
        
        # Write error summary
        error_summary = {
            "error": str(e),
            "traceback": traceback.format_exc(),
            "timestamp": datetime.utcnow().isoformat() + "Z"
        }
        
        error_file = pathlib.Path(RUN_DIR) / "error.json"
        with open(error_file, 'w') as f:
            json.dump(error_summary, f, indent=2)
            
        return 1
        
    finally:
        # Cleanup
        watcher.close()

if __name__ == "__main__":
    exit_code = main()
    exit(exit_code)