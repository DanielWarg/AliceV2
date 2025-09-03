#!/usr/bin/env python3
"""
Quality Gates for Alice v2 Eval Harness
Validates evaluation results against quality thresholds
"""

import json
import sys
from typing import Dict, Any

# Quality gate thresholds
QUALITY_GATES = {
    "easy_medium_schema_ok": 0.95,  # EASY + MEDIUM schema_ok@first ≥ 95%
    "tool_precision": 0.85,         # Tool precision ≥ 85%
    "latency_p95": 900,             # Latency P95 ≤ 900ms
    "success_rate": 0.90            # Overall success rate ≥ 90%
}

def load_eval_report(report_file: str) -> Dict[str, Any]:
    """Load evaluation report from JSON file"""
    try:
        with open(report_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"❌ Evaluation report not found: {report_file}")
        sys.exit(1)
    except json.JSONDecodeError as e:
        print(f"❌ Invalid JSON in evaluation report: {e}")
        sys.exit(1)

def check_quality_gates(report: Dict[str, Any]) -> Dict[str, bool]:
    """Check all quality gates against evaluation results"""
    metrics = report.get("metrics", {})
    
    # Calculate EASY+MEDIUM schema_ok average
    easy_schema_ok = metrics.get("easy.schema_ok_first", 0.0)
    medium_schema_ok = metrics.get("medium.schema_ok_first", 0.0)
    easy_medium_avg = (easy_schema_ok + medium_schema_ok) / 2
    
    # Check each quality gate
    results = {
        "easy_medium_schema_ok": easy_medium_avg >= QUALITY_GATES["easy_medium_schema_ok"],
        "tool_precision": metrics.get("tool_precision", 0.0) >= QUALITY_GATES["tool_precision"],
        "latency_p95": metrics.get("latency_p95_ms", float('inf')) <= QUALITY_GATES["latency_p95"],
        "success_rate": metrics.get("success_rate", 0.0) >= QUALITY_GATES["success_rate"]
    }
    
    return results

def print_quality_gate_results(gate_results: Dict[str, bool], report: Dict[str, Any]):
    """Print quality gate results with details"""
    metrics = report.get("metrics", {})
    
    print("\n" + "="*60)
    print("🎯 QUALITY GATES VALIDATION")
    print("="*60)
    
    # EASY+MEDIUM schema_ok
    easy_schema_ok = metrics.get("easy.schema_ok_first", 0.0)
    medium_schema_ok = metrics.get("medium.schema_ok_first", 0.0)
    easy_medium_avg = (easy_schema_ok + medium_schema_ok) / 2
    
    print(f"📊 EASY+MEDIUM schema_ok@first ≥ 95%:")
    print(f"   EASY: {easy_schema_ok:.1%}")
    print(f"   MEDIUM: {medium_schema_ok:.1%}")
    print(f"   Average: {easy_medium_avg:.1%}")
    print(f"   Status: {'✅ PASS' if gate_results['easy_medium_schema_ok'] else '❌ FAIL'}")
    
    # Tool precision
    tool_precision = metrics.get("tool_precision", 0.0)
    print(f"\n🎯 Tool precision ≥ 85%:")
    print(f"   Actual: {tool_precision:.1%}")
    print(f"   Status: {'✅ PASS' if gate_results['tool_precision'] else '❌ FAIL'}")
    
    # Latency P95
    latency_p95 = metrics.get("latency_p95_ms", float('inf'))
    print(f"\n⚡ Latency P95 ≤ 900ms:")
    print(f"   Actual: {latency_p95:.0f}ms")
    print(f"   Status: {'✅ PASS' if gate_results['latency_p95'] else '❌ FAIL'}")
    
    # Success rate
    success_rate = metrics.get("success_rate", 0.0)
    print(f"\n📈 Success rate ≥ 90%:")
    print(f"   Actual: {success_rate:.1%}")
    print(f"   Status: {'✅ PASS' if gate_results['success_rate'] else '❌ FAIL'}")
    
    print("="*60)
    
    # Overall result
    all_passed = all(gate_results.values())
    if all_passed:
        print("🎉 ALL QUALITY GATES PASSED!")
    else:
        print("❌ SOME QUALITY GATES FAILED!")
        failed_gates = [gate for gate, passed in gate_results.items() if not passed]
        print(f"   Failed gates: {', '.join(failed_gates)}")
    
    print("="*60)

def main():
    """Main quality gates function"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Alice v2 Quality Gates")
    parser.add_argument("report_file", help="Path to evaluation report JSON file")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    
    args = parser.parse_args()
    
    try:
        # Load evaluation report
        report = load_eval_report(args.report_file)
        
        if args.verbose:
            print(f"📊 Loaded evaluation report:")
            print(f"   SHA: {report.get('sha', 'unknown')}")
            print(f"   Planner: {report.get('planner', 'unknown')}")
            print(f"   Schema: {report.get('schema', 'unknown')}")
            print(f"   Timestamp: {report.get('timestamp', 'unknown')}")
            print(f"   Total scenarios: {report.get('total_scenarios', 0)}")
            print(f"   Successful scenarios: {report.get('successful_scenarios', 0)}")
        
        # Check quality gates
        gate_results = check_quality_gates(report)
        
        # Print results
        print_quality_gate_results(gate_results, report)
        
        # Exit with appropriate code
        all_passed = all(gate_results.values())
        if all_passed:
            print("✅ Quality gates validation successful")
            sys.exit(0)
        else:
            print("❌ Quality gates validation failed")
            sys.exit(1)
            
    except Exception as e:
        print(f"❌ Quality gates validation error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
