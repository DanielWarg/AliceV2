"""
Test Metrics Collection and Reporting
Writes structured metrics, generates summaries, and tracks SLO compliance
"""

import csv
import json
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Any, Optional
import numpy as np


class MetricsWriter:
    """Handles test metrics collection and report generation"""
    
    def __init__(self, run_dir: Path):
        self.run_dir = run_dir
        self.run_dir.mkdir(parents=True, exist_ok=True)
        
        # Initialize output files
        self.metrics_file = self.run_dir / "metrics.csv"
        self.log_file = self.run_dir / "log.jsonl"
        self.summary_file = self.run_dir / "summary.md"
        
        # Track all results for summary generation
        self.all_results: List[Dict[str, Any]] = []
        self.remediation_actions: List[Dict[str, Any]] = []
        
        # Initialize CSV with headers
        self._init_csv_file()
        
        print(f"📊 Metrics output: {self.run_dir}")
    
    def write_result(self, result: Dict[str, Any], rerun: bool = False):
        """Write test result to metrics files"""
        
        # Add to internal tracking
        if rerun:
            result["rerun"] = True
        self.all_results.append(result)
        
        # Write to CSV
        self._write_csv_row(result)
        
        # Write to structured log
        self._write_log_entry("test_result", result)
        
    def log_error(self, scenario: Dict[str, Any], error: str):
        """Log test execution error"""
        error_entry = {
            "timestamp": datetime.now().isoformat(),
            "event": "test_error",
            "scenario_id": scenario.get("id", "unknown"),
            "scenario_kind": scenario.get("kind", "unknown"),
            "error": error
        }
        
        self._write_log_entry("test_error", error_entry)
        
    def log_remediation(self, failure_type: str, action: Dict[str, Any]):
        """Log remediation action taken"""
        remediation_entry = {
            "timestamp": datetime.now().isoformat(),
            "event": "remediation_applied",
            "failure_type": failure_type,
            "action": action
        }
        
        self.remediation_actions.append(remediation_entry)
        self._write_log_entry("remediation", remediation_entry)
        
    def generate_summary(self, results: List[Dict[str, Any]]):
        """Generate comprehensive test run summary"""
        
        if not results:
            summary = "# Alice v2 Test Run Summary\n\n**No test results available**\n"
            self._write_summary(summary)
            return
            
        # Calculate overall metrics
        total_scenarios = len(results)
        passed_scenarios = len([r for r in results if r.get("slo_pass", False)])
        failed_scenarios = total_scenarios - passed_scenarios
        
        # Group results by scenario type
        voice_results = [r for r in results if r.get("scenario_kind") == "voice"]
        nlu_results = [r for r in results if r.get("scenario_kind") == "nlu"]
        planner_results = [r for r in results if r.get("scenario_kind") == "planner"]
        deep_results = [r for r in results if r.get("scenario_kind") == "deep"]
        vision_results = [r for r in results if r.get("scenario_kind") == "vision"]
        
        # Generate summary sections
        summary_parts = [
            self._generate_header(),
            self._generate_overview(total_scenarios, passed_scenarios, failed_scenarios),
            self._generate_slo_compliance_table(results),
            self._generate_voice_metrics(voice_results),
            self._generate_llm_metrics(planner_results, deep_results),
            self._generate_tool_metrics(planner_results),
            self._generate_system_metrics(results),
            self._generate_remediation_summary(),
            self._generate_recommendations(results)
        ]
        
        summary = "\n\n".join(filter(None, summary_parts))
        self._write_summary(summary)
        
        # Also generate JSON summary for programmatic access
        self._generate_json_summary(results)
        
    def _generate_header(self) -> str:
        """Generate summary header"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        return f"""# Alice v2 Test Run Summary

**Date**: {timestamp}  
**Run Directory**: {self.run_dir.name}  
**Test Duration**: {self._calculate_run_duration()}"""

    def _generate_overview(self, total: int, passed: int, failed: int) -> str:
        """Generate test overview section"""
        pass_rate = (passed / total * 100) if total > 0 else 0
        status_emoji = "✅" if failed == 0 else "⚠️" if failed < total * 0.1 else "❌"
        status_text = "PASS" if failed == 0 else "DEGRADED" if failed < total * 0.1 else "FAIL"
        
        return f"""## Overview

**Overall Status**: {status_emoji} {status_text}  
**Test Scenarios**: {total} total, {passed} passed, {failed} failed  
**Pass Rate**: {pass_rate:.1f}%  
**SLO Compliance**: {"All targets met" if failed == 0 else f"{failed} SLO violations"}"""

    def _generate_slo_compliance_table(self, results: List[Dict]) -> str:
        """Generate SLO compliance table"""
        
        # Calculate key SLO metrics
        slo_metrics = {}
        
        # Voice metrics
        voice_results = [r for r in results if r.get("scenario_kind") == "voice"]
        if voice_results:
            wer_values = [r.get("wer", 1.0) for r in voice_results if r.get("wer") is not None]
            final_times = [r.get("asr_final_ms", 0) for r in voice_results if r.get("asr_final_ms")]
            
            if wer_values:
                slo_metrics["Swedish WER Clean"] = {
                    "target": "≤7.0%",
                    "actual": f"{np.mean([w for w in wer_values if w <= 0.1]) * 100:.1f}%",
                    "status": "✅" if np.mean(wer_values) <= 0.07 else "❌"
                }
                
            if final_times:
                p95_final = np.percentile(final_times, 95)
                slo_metrics["ASR Final P95"] = {
                    "target": "≤800ms",
                    "actual": f"{p95_final:.0f}ms",
                    "status": "✅" if p95_final <= 800 else "❌"
                }
        
        # LLM metrics  
        planner_results = [r for r in results if r.get("scenario_kind") == "planner"]
        if planner_results:
            first_times = [r.get("llm_first_ms", 0) for r in planner_results if r.get("llm_first_ms")]
            if first_times:
                p95_first = np.percentile(first_times, 95)
                slo_metrics["Planner First Token P95"] = {
                    "target": "≤900ms", 
                    "actual": f"{p95_first:.0f}ms",
                    "status": "✅" if p95_first <= 900 else "❌"
                }
        
        # Tool success rate
        tool_results = [r for r in results if r.get("tool_success") is not None]
        if tool_results:
            success_rates = [r.get("tool_success", 0) for r in tool_results]
            avg_success = np.mean(success_rates)
            slo_metrics["Tool Success Rate"] = {
                "target": "≥95%",
                "actual": f"{avg_success * 100:.1f}%", 
                "status": "✅" if avg_success >= 0.95 else "❌"
            }
        
        # Generate table
        if not slo_metrics:
            return "## SLO Compliance\n\nNo SLO metrics available."
            
        table_rows = ["| Metric | Target | Actual | Status |", "|--------|--------|--------|--------|"]
        for metric, data in slo_metrics.items():
            row = f"| {metric} | {data['target']} | {data['actual']} | {data['status']} |"
            table_rows.append(row)
            
        return f"## SLO Compliance\n\n" + "\n".join(table_rows)
    
    def _generate_voice_metrics(self, voice_results: List[Dict]) -> Optional[str]:
        """Generate voice pipeline specific metrics"""
        if not voice_results:
            return None
            
        # WER analysis
        wer_values = [r.get("wer", 1.0) for r in voice_results if r.get("wer") is not None]
        clean_wer = [r.get("wer", 1.0) for r in voice_results if "clean" in r.get("scenario_id", "")]
        noisy_wer = [r.get("wer", 1.0) for r in voice_results if "noise" in r.get("scenario_id", "")]
        
        # Timing analysis
        partial_times = [r.get("asr_partial_ms") for r in voice_results if r.get("asr_partial_ms")]
        final_times = [r.get("asr_final_ms") for r in voice_results if r.get("asr_final_ms")]
        
        metrics = []
        metrics.append("## Voice Pipeline Metrics")
        
        if wer_values:
            metrics.append(f"**Overall WER**: {np.mean(wer_values) * 100:.1f}%")
        if clean_wer:
            metrics.append(f"**Clean Audio WER**: {np.mean(clean_wer) * 100:.1f}%")
        if noisy_wer:
            metrics.append(f"**Noisy Audio WER**: {np.mean(noisy_wer) * 100:.1f}%")
            
        if partial_times:
            metrics.append(f"**Partial Transcript Latency**: P95 {np.percentile(partial_times, 95):.0f}ms")
        if final_times:
            metrics.append(f"**Final Transcript Latency**: P95 {np.percentile(final_times, 95):.0f}ms")
            
        # Error analysis
        errors = sum(r.get("processing_errors", 0) for r in voice_results)
        if errors > 0:
            metrics.append(f"**Processing Errors**: {errors} total")
            
        return "\n".join(metrics)
    
    def _generate_llm_metrics(self, planner_results: List[Dict], deep_results: List[Dict]) -> Optional[str]:
        """Generate LLM performance metrics"""
        if not planner_results and not deep_results:
            return None
            
        metrics = ["## LLM Performance Metrics"]
        
        # Planner LLM analysis
        if planner_results:
            first_times = [r.get("llm_first_ms") for r in planner_results if r.get("llm_first_ms")]
            full_times = [r.get("llm_full_ms") for r in planner_results if r.get("llm_full_ms")]
            
            if first_times:
                metrics.append(f"**Planner First Token**: P95 {np.percentile(first_times, 95):.0f}ms")
            if full_times:
                metrics.append(f"**Planner Complete**: P95 {np.percentile(full_times, 95):.0f}ms")
                
        # Deep LLM analysis  
        if deep_results:
            first_times = [r.get("llm_first_ms") for r in deep_results if r.get("llm_first_ms")]
            full_times = [r.get("llm_full_ms") for r in deep_results if r.get("llm_full_ms")]
            
            if first_times:
                metrics.append(f"**Deep First Token**: P95 {np.percentile(first_times, 95):.0f}ms")
            if full_times:
                metrics.append(f"**Deep Complete**: P95 {np.percentile(full_times, 95):.0f}ms")
                
        return "\n".join(metrics)
    
    def _generate_tool_metrics(self, planner_results: List[Dict]) -> Optional[str]:
        """Generate tool integration metrics"""
        tool_results = [r for r in planner_results if r.get("tool_success") is not None]
        if not tool_results:
            return None
            
        # Tool success analysis
        success_rates = [r.get("tool_success", 0) for r in tool_results]
        avg_success = np.mean(success_rates)
        
        # Tool-specific analysis
        email_results = [r for r in tool_results if "email" in r.get("scenario_id", "")]
        calendar_results = [r for r in tool_results if "calendar" in r.get("scenario_id", "")]
        
        metrics = ["## Tool Integration Metrics"]
        metrics.append(f"**Overall Tool Success**: {avg_success * 100:.1f}%")
        
        if email_results:
            email_success = np.mean([r.get("tool_success", 0) for r in email_results])
            metrics.append(f"**Email Tools**: {email_success * 100:.1f}% success")
            
        if calendar_results:
            calendar_success = np.mean([r.get("tool_success", 0) for r in calendar_results])
            metrics.append(f"**Calendar Tools**: {calendar_success * 100:.1f}% success")
            
        return "\n".join(metrics)
    
    def _generate_system_metrics(self, results: List[Dict]) -> str:
        """Generate system resource metrics"""
        ram_values = [r.get("ram_peak_mb", 0) for r in results if r.get("ram_peak_mb")]
        energy_values = [r.get("energy_wh", 0) for r in results if r.get("energy_wh")]
        
        metrics = ["## System Resource Metrics"]
        
        if ram_values:
            peak_ram = max(ram_values)
            avg_ram = np.mean(ram_values)
            metrics.append(f"**Memory Usage**: Peak {peak_ram:.0f}MB, Average {avg_ram:.0f}MB")
        
        if energy_values:
            total_energy = sum(energy_values)
            metrics.append(f"**Energy Consumption**: {total_energy:.2f}Wh total")
            
        # Guardian state analysis
        guardian_failures = [r for r in results if r.get("guardian_response_ms", 0) > 150]
        if guardian_failures:
            metrics.append(f"**Guardian Issues**: {len(guardian_failures)} slow responses")
        else:
            metrics.append("**Guardian Status**: All responses within SLO")
            
        return "\n".join(metrics)
    
    def _generate_remediation_summary(self) -> Optional[str]:
        """Generate remediation actions summary"""
        if not self.remediation_actions:
            return "## Remediation Actions\n\nNo remediation actions required - all tests passed."
            
        summary = ["## Remediation Actions"]
        summary.append(f"**Total Actions**: {len(self.remediation_actions)}")
        
        for action in self.remediation_actions:
            action_data = action.get("action", {})
            summary.append(f"- **{action_data.get('action_type', 'Unknown')}**: {action_data.get('reasoning', 'No details')}")
            
        return "\n".join(summary)
    
    def _generate_recommendations(self, results: List[Dict]) -> str:
        """Generate recommendations for improvements"""
        recommendations = ["## Recommendations"]
        
        failed_results = [r for r in results if not r.get("slo_pass", True)]
        
        if not failed_results:
            recommendations.append("✅ All tests passed - no immediate actions required.")
            return "\n".join(recommendations)
            
        # Analysis-based recommendations
        voice_failures = [r for r in failed_results if r.get("scenario_kind") == "voice"]
        if voice_failures:
            high_wer = [r for r in voice_failures if r.get("wer", 0) > 0.1]
            if high_wer:
                recommendations.append("- Consider updating Swedish ASR model or VAD parameters")
                
        llm_failures = [r for r in failed_results if r.get("llm_first_ms", 0) > 1500]
        if llm_failures:
            recommendations.append("- Optimize LLM context size or consider model quantization")
            
        tool_failures = [r for r in failed_results if r.get("tool_success", 1.0) < 0.95]
        if tool_failures:
            recommendations.append("- Review tool integration timeouts and error handling")
            
        if not recommendations[1:]:  # Only header exists
            recommendations.append("- Review detailed logs for specific failure patterns")
            
        return "\n".join(recommendations)
    
    def _init_csv_file(self):
        """Initialize CSV file with headers"""
        headers = [
            "timestamp", "scenario_id", "scenario_kind", "wer", "asr_partial_ms", "asr_final_ms",
            "intent_accuracy", "nlu_latency_ms", "llm_first_ms", "llm_full_ms", "tool_success",
            "tts_cached_ms", "tts_uncached_ms", "guardian_response_ms", "ram_peak_mb", 
            "energy_wh", "processing_errors", "slo_pass", "rerun"
        ]
        
        with open(self.metrics_file, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(headers)
    
    def _write_csv_row(self, result: Dict[str, Any]):
        """Write single result to CSV"""
        row = [
            result.get("timestamp", datetime.now().isoformat()),
            result.get("scenario_id", ""),
            result.get("scenario_kind", ""),
            result.get("wer", ""),
            result.get("asr_partial_ms", ""),
            result.get("asr_final_ms", ""),
            result.get("intent_accuracy", ""),
            result.get("nlu_latency_ms", ""),
            result.get("llm_first_ms", ""),
            result.get("llm_full_ms", ""),
            result.get("tool_success", ""),
            result.get("tts_cached_ms", ""),
            result.get("tts_uncached_ms", ""),
            result.get("guardian_response_ms", ""),
            result.get("ram_peak_mb", ""),
            result.get("energy_wh", ""),
            result.get("processing_errors", ""),
            result.get("slo_pass", ""),
            result.get("rerun", False)
        ]
        
        with open(self.metrics_file, 'a', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(row)
    
    def _write_log_entry(self, event_type: str, data: Dict[str, Any]):
        """Write structured log entry"""
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "event": event_type,
            **data
        }
        
        with open(self.log_file, 'a') as f:
            f.write(json.dumps(log_entry) + "\n")
    
    def _write_summary(self, summary: str):
        """Write summary to markdown file"""
        with open(self.summary_file, 'w') as f:
            f.write(summary)
            
    def _generate_json_summary(self, results: List[Dict]):
        """Generate JSON summary for programmatic access"""
        summary_data = {
            "timestamp": datetime.now().isoformat(),
            "run_directory": str(self.run_dir),
            "total_scenarios": len(results),
            "passed_scenarios": len([r for r in results if r.get("slo_pass", False)]),
            "failed_scenarios": len([r for r in results if not r.get("slo_pass", True)]),
            "remediation_actions": len(self.remediation_actions),
            "results": results,
            "remediations": self.remediation_actions
        }
        
        json_file = self.run_dir / "summary.json"
        with open(json_file, 'w') as f:
            json.dump(summary_data, f, indent=2)
    
    def _calculate_run_duration(self) -> str:
        """Calculate test run duration"""
        if not self.all_results:
            return "Unknown"
            
        timestamps = [r.get("timestamp") for r in self.all_results if r.get("timestamp")]
        if len(timestamps) < 2:
            return "< 1 minute"
            
        try:
            start_time = min(timestamps)
            end_time = max(timestamps)
            
            start_dt = datetime.fromisoformat(start_time.replace('Z', '+00:00'))
            end_dt = datetime.fromisoformat(end_time.replace('Z', '+00:00'))
            
            duration = end_dt - start_dt
            
            if duration.total_seconds() < 60:
                return f"{duration.total_seconds():.0f} seconds"
            else:
                return f"{duration.total_seconds() / 60:.1f} minutes"
                
        except Exception:
            return "Unknown"