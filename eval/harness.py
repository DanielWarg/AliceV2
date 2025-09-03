#!/usr/bin/env python3
"""
Alice v2 Eval Harness - Run regression tests and collect metrics
"""

import yaml
import json
import time
import asyncio
import aiohttp
import statistics
from pathlib import Path
from typing import Dict, List, Any, Optional
from datetime import datetime
import os
import sys

# Add services to path
sys.path.append('services/orchestrator/src')

class EvalHarness:
    def __init__(self, base_url: str = "http://localhost:18000"):
        self.base_url = base_url
        self.results = []
        self.metrics = {
            "easy": {"schema_ok_first": [], "latency_ms": [], "tool_precision": []},
            "medium": {"schema_ok_first": [], "latency_ms": [], "tool_precision": []},
            "hard": {"schema_ok_first": [], "latency_ms": [], "tool_precision": []}
        }
    
    def load_scenarios(self, regression_dir: str = "eval/regression") -> List[Dict[str, Any]]:
        """Load all YAML scenarios from regression directory"""
        scenarios = []
        regression_path = Path(regression_dir)
        
        if not regression_path.exists():
            raise FileNotFoundError(f"Regression directory not found: {regression_dir}")
        
        for yaml_file in regression_path.glob("*.yml"):
            with open(yaml_file, 'r', encoding='utf-8') as f:
                scenario = yaml.safe_load(f)
                scenarios.append(scenario)
        
        print(f"Loaded {len(scenarios)} scenarios from {regression_dir}")
        return scenarios
    
    async def run_scenario(self, scenario: Dict[str, Any]) -> Dict[str, Any]:
        """Run a single scenario and collect metrics"""
        start_time = time.time()
        
        try:
            # Make API call
            async with aiohttp.ClientSession() as session:
                payload = {
                    "v": "1",
                    "message": scenario["prompt_sv"],
                    "session_id": f"eval_{scenario['id']}"
                }
                
                async with session.post(
                    f"{self.base_url}/api/orchestrator/chat",
                    json=payload,
                    headers={"Content-Type": "application/json"}
                ) as response:
                    response_data = await response.json()
                    
        except Exception as e:
            print(f"❌ Error running scenario {scenario['id']}: {e}")
            return {
                "scenario_id": scenario["id"],
                "success": False,
                "error": str(e),
                "latency_ms": 0,
                "schema_ok_first": False,
                "tool_precision": 0.0
            }
        
        latency_ms = (time.time() - start_time) * 1000
        
        # Extract metrics from response
        try:
            response_text = response_data.get("response", "")
            metadata = response_data.get("metadata", {})
            
            # Parse response JSON if possible
            try:
                response_json = json.loads(response_text)
                actual_intent = response_json.get("intent", "")
                actual_tools = response_json.get("tool", [])
                if isinstance(actual_tools, str) and actual_tools:
                    actual_tools = [actual_tools]
                elif not actual_tools:
                    actual_tools = []
            except:
                actual_intent = ""
                actual_tools = []
            
            # Calculate tool precision
            expected_tools = set(scenario["expected_tools"])
            actual_tools_set = set(actual_tools)
            
            if expected_tools:
                tool_precision = len(expected_tools.intersection(actual_tools_set)) / len(expected_tools)
            else:
                tool_precision = 1.0 if not actual_tools else 0.0
            
            # Check schema_ok
            schema_ok_first = metadata.get("planner_schema_ok", False)
            
            # Check intent match
            intent_match = actual_intent == scenario["expected_intent"]
            
            result = {
                "scenario_id": scenario["id"],
                "success": True,
                "latency_ms": latency_ms,
                "schema_ok_first": schema_ok_first,
                "tool_precision": tool_precision,
                "intent_match": intent_match,
                "expected_intent": scenario["expected_intent"],
                "actual_intent": actual_intent,
                "expected_tools": scenario["expected_tools"],
                "actual_tools": actual_tools,
                "max_latency_ms": scenario["max_latency_ms"],
                "tags": scenario["tags"]
            }
            
        except Exception as e:
            print(f"❌ Error parsing response for scenario {scenario['id']}: {e}")
            result = {
                "scenario_id": scenario["id"],
                "success": False,
                "error": str(e),
                "latency_ms": latency_ms,
                "schema_ok_first": False,
                "tool_precision": 0.0
            }
        
        return result
    
    async def run_all_scenarios(self, scenarios: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Run all scenarios and collect results"""
        print(f"🚀 Running {len(scenarios)} scenarios...")
        
        # Run scenarios concurrently (but limit concurrency to avoid overwhelming the system)
        semaphore = asyncio.Semaphore(5)  # Max 5 concurrent requests
        
        async def run_with_semaphore(scenario):
            async with semaphore:
                return await self.run_scenario(scenario)
        
        tasks = [run_with_semaphore(scenario) for scenario in scenarios]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Handle exceptions
        processed_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                print(f"❌ Exception in scenario {scenarios[i]['id']}: {result}")
                processed_results.append({
                    "scenario_id": scenarios[i]["id"],
                    "success": False,
                    "error": str(result),
                    "latency_ms": 0,
                    "schema_ok_first": False,
                    "tool_precision": 0.0
                })
            else:
                processed_results.append(result)
        
        return processed_results
    
    def calculate_metrics(self, results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Calculate aggregated metrics from results"""
        # Group results by difficulty level
        easy_results = [r for r in results if "EASY" in r.get("tags", [])]
        medium_results = [r for r in results if "MEDIUM" in r.get("tags", [])]
        hard_results = [r for r in results if "HARD" in r.get("tags", [])]
        
        def calculate_level_metrics(level_results: List[Dict[str, Any]], level_name: str) -> Dict[str, Any]:
            if not level_results:
                return {
                    f"{level_name.lower()}.schema_ok_first": 0.0,
                    f"{level_name.lower()}.latency_p50_ms": 0,
                    f"{level_name.lower()}.latency_p95_ms": 0,
                    f"{level_name.lower()}.tool_precision": 0.0,
                    f"{level_name.lower()}.success_rate": 0.0
                }
            
            successful_results = [r for r in level_results if r.get("success", False)]
            
            schema_ok_rates = [r.get("schema_ok_first", False) for r in successful_results]
            latencies = [r.get("latency_ms", 0) for r in successful_results]
            tool_precisions = [r.get("tool_precision", 0.0) for r in successful_results]
            
            return {
                f"{level_name.lower()}.schema_ok_first": sum(schema_ok_rates) / len(schema_ok_rates) if schema_ok_rates else 0.0,
                f"{level_name.lower()}.latency_p50_ms": statistics.median(latencies) if latencies else 0,
                f"{level_name.lower()}.latency_p95_ms": statistics.quantiles(latencies, n=20)[18] if len(latencies) >= 20 else max(latencies) if latencies else 0,
                f"{level_name.lower()}.tool_precision": sum(tool_precisions) / len(tool_precisions) if tool_precisions else 0.0,
                f"{level_name.lower()}.success_rate": len(successful_results) / len(level_results)
            }
        
        # Calculate overall metrics
        all_latencies = [r.get("latency_ms", 0) for r in results if r.get("success", False)]
        all_tool_precisions = [r.get("tool_precision", 0.0) for r in results if r.get("success", False)]
        
        metrics = {
            "easy": calculate_level_metrics(easy_results, "EASY"),
            "medium": calculate_level_metrics(medium_results, "MEDIUM"),
            "hard": calculate_level_metrics(hard_results, "HARD"),
            "overall": {
                "latency_p95_ms": statistics.quantiles(all_latencies, n=20)[18] if len(all_latencies) >= 20 else max(all_latencies) if all_latencies else 0,
                "tool_precision": sum(all_tool_precisions) / len(all_tool_precisions) if all_tool_precisions else 0.0,
                "success_rate": len([r for r in results if r.get("success", False)]) / len(results)
            }
        }
        
        return metrics
    
    def generate_report(self, results: List[Dict[str, Any]], metrics: Dict[str, Any]) -> Dict[str, Any]:
        """Generate comprehensive evaluation report"""
        # Get system info
        planner_model = os.getenv("LLM_PLANNER", "unknown")
        schema_version = os.getenv("PLANNER_SCHEMA_VERSION", "unknown")
        
        report = {
            "sha": os.getenv("GITHUB_SHA", "local"),
            "planner": planner_model,
            "schema": f"v{schema_version}",
            "prompt": "v1.0",
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "total_scenarios": len(results),
            "successful_scenarios": len([r for r in results if r.get("success", False)]),
            "metrics": {
                "easy.schema_ok_first": metrics["easy"]["easy.schema_ok_first"],
                "medium.schema_ok_first": metrics["medium"]["medium.schema_ok_first"],
                "hard.schema_ok_first": metrics["hard"]["hard.schema_ok_first"],
                "tool_precision": metrics["overall"]["tool_precision"],
                "latency_p95_ms": metrics["overall"]["latency_p95_ms"],
                "success_rate": metrics["overall"]["success_rate"]
            },
            "detailed_metrics": metrics,
            "scenario_results": results
        }
        
        return report
    
    def save_report(self, report: Dict[str, Any], output_file: str):
        """Save report to JSON file"""
        os.makedirs(os.path.dirname(output_file), exist_ok=True)
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
        
        print(f"📊 Report saved to: {output_file}")
    
    def print_summary(self, report: Dict[str, Any]):
        """Print evaluation summary"""
        metrics = report["metrics"]
        
        print("\n" + "="*60)
        print("📊 EVALUATION SUMMARY")
        print("="*60)
        print(f"Total scenarios: {report['total_scenarios']}")
        print(f"Successful scenarios: {report['successful_scenarios']}")
        print(f"Success rate: {metrics['success_rate']:.1%}")
        print()
        print("📈 Key Metrics:")
        print(f"  EASY schema_ok@first: {metrics['easy.schema_ok_first']:.1%}")
        print(f"  MEDIUM schema_ok@first: {metrics['medium.schema_ok_first']:.1%}")
        print(f"  HARD schema_ok@first: {metrics['hard.schema_ok_first']:.1%}")
        print(f"  Tool precision: {metrics['tool_precision']:.1%}")
        print(f"  Latency P95: {metrics['latency_p95_ms']:.0f}ms")
        print()
        print("🎯 Quality Gates:")
        print(f"  EASY+MEDIUM schema_ok ≥ 95%: {'✅' if (metrics['easy.schema_ok_first'] + metrics['medium.schema_ok_first']) / 2 >= 0.95 else '❌'}")
        print(f"  Tool precision ≥ 85%: {'✅' if metrics['tool_precision'] >= 0.85 else '❌'}")
        print(f"  Latency P95 ≤ 900ms: {'✅' if metrics['latency_p95_ms'] <= 900 else '❌'}")
        print("="*60)

async def main():
    """Main evaluation function"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Alice v2 Eval Harness")
    parser.add_argument("--base-url", default="http://localhost:18000", help="Base URL for Alice API")
    parser.add_argument("--regression-dir", default="eval/regression", help="Directory with regression scenarios")
    parser.add_argument("--output", default="eval_runs/eval_report.json", help="Output file for report")
    
    args = parser.parse_args()
    
    # Create eval harness
    harness = EvalHarness(base_url=args.base_url)
    
    try:
        # Load scenarios
        scenarios = harness.load_scenarios(args.regression_dir)
        
        # Run scenarios
        results = await harness.run_all_scenarios(scenarios)
        
        # Calculate metrics
        metrics = harness.calculate_metrics(results)
        
        # Generate report
        report = harness.generate_report(results, metrics)
        
        # Save report
        harness.save_report(report, args.output)
        
        # Print summary
        harness.print_summary(report)
        
        # Exit with error if quality gates fail
        quality_gates_passed = (
            (metrics["easy"]["easy.schema_ok_first"] + metrics["medium"]["medium.schema_ok_first"]) / 2 >= 0.95 and
            metrics["overall"]["tool_precision"] >= 0.85 and
            metrics["overall"]["latency_p95_ms"] <= 900
        )
        
        if not quality_gates_passed:
            print("❌ Quality gates failed!")
            sys.exit(1)
        else:
            print("✅ All quality gates passed!")
            sys.exit(0)
            
    except Exception as e:
        print(f"❌ Evaluation failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())
