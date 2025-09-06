#!/usr/bin/env python3
"""
Fibonacci Training Metrics Exporter
Converts training results to enterprise monitoring formats (Prometheus, CSV, Grafana JSON)
Ensures consistent schema compliance and automated alert generation.
"""

import csv
import json
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

import jsonschema


class FibonacciMetricsExporter:
    """Export Fibonacci training results to multiple monitoring formats."""
    
    def __init__(self, project_root: str = None):
        self.project_root = Path(project_root) if project_root else Path(__file__).parent.parent.parent
        self.schema_path = self.project_root / "schemas" / "fibonacci_training_schema.json"
        self.metrics_dir = self.project_root / "metrics"
        self.logs_dir = self.project_root / "logs"
        
        # Ensure directories exist
        self.metrics_dir.mkdir(exist_ok=True)
        
        # Load schema for validation
        self.schema = self._load_schema()
    
    def _load_schema(self) -> Dict:
        """Load the canonical schema for validation."""
        try:
            with open(self.schema_path, 'r') as f:
                return json.load(f)
        except Exception as e:
            print(f"Warning: Could not load schema: {e}")
            return {}
    
    def validate_training_result(self, result: Dict) -> bool:
        """Validate training result against canonical schema."""
        if not self.schema:
            return True  # Skip validation if schema not available
            
        try:
            jsonschema.validate(result, self.schema)
            return True
        except jsonschema.ValidationError as e:
            print(f"Schema validation failed: {e}")
            return False
    
    def standardize_training_result(self, raw_result: Dict) -> Dict:
        """Convert raw training result to canonical schema format."""
        
        # Extract basic session info
        session_id = raw_result.get('session_id', f"fibonacci_training_{datetime.now().strftime('%Y%m%d_%H%M%S')}")
        
        # Calculate performance metrics
        all_times = []
        total_successful = 0
        total_failed = 0
        
        for phase in raw_result.get('phase_results', []):
            if 'response_times' in phase:
                all_times.extend(phase['response_times'])
            total_successful += phase.get('successful_requests', 0)
            total_failed += phase.get('failed_requests', 0)
        
        avg_time = sum(all_times) / len(all_times) if all_times else 0
        success_rate = (total_successful / (total_successful + total_failed) * 100) if (total_successful + total_failed) > 0 else 0
        
        # Calculate improvements
        baseline_ms = 417
        target_ms = 35.9
        improvement = ((baseline_ms - avg_time) / baseline_ms) * 100 if avg_time > 0 else 0
        target_progress = ((baseline_ms - avg_time) / (baseline_ms - target_ms)) * 100 if avg_time > 0 else 0
        
        # Cache metrics
        initial_cache = raw_result.get('initial_cache_hit_rate', 0)
        final_cache = raw_result.get('final_cache_hit_rate', 0)
        
        # Fibonacci analysis
        golden_ratio = 1.618033988749
        golden_target = 1.0 / golden_ratio  # ≈ 0.618
        golden_efficiency = (final_cache/100) / golden_target if final_cache > 0 else 0
        
        # Performance ratings
        def get_performance_rating(avg_time_ms: float, success_rate_pct: float) -> str:
            if avg_time_ms < 1000 and success_rate_pct > 95:
                return "excellent"
            elif avg_time_ms < 5000 and success_rate_pct > 80:
                return "good" 
            elif avg_time_ms < 10000 and success_rate_pct > 50:
                return "moderate"
            else:
                return "poor"
        
        def get_fibonacci_status(efficiency: float) -> str:
            if efficiency >= 0.8:
                return "excellent"
            elif efficiency >= 0.6:
                return "good"
            else:
                return "needs_improvement"
        
        # Generate alerts
        alerts = []
        thresholds = {
            "response_time": {"excellent_max_ms": 1000, "good_max_ms": 5000, "poor_min_ms": 10000},
            "success_rate": {"excellent_min_percent": 95, "good_min_percent": 80, "poor_max_percent": 50},
            "cache": {"target_hit_rate_percent": 70, "baseline_hit_rate_percent": 10},
            "targets": {"target_response_time_ms": 35.9, "baseline_response_time_ms": 417}
        }
        
        if avg_time > thresholds["response_time"]["poor_min_ms"]:
            alerts.append({
                "severity": "critical",
                "message": "Response time exceeds critical threshold - quota limits detected",
                "threshold_breached": "response_time_critical",
                "current_value": avg_time,
                "threshold_value": thresholds["response_time"]["poor_min_ms"]
            })
        
        if success_rate < thresholds["success_rate"]["poor_max_percent"]:
            alerts.append({
                "severity": "critical", 
                "message": "Success rate below acceptable threshold",
                "threshold_breached": "success_rate_critical",
                "current_value": success_rate,
                "threshold_value": thresholds["success_rate"]["poor_max_percent"]
            })
        
        if final_cache < thresholds["cache"]["target_hit_rate_percent"]:
            alerts.append({
                "severity": "warning",
                "message": "Cache hit rate below target",
                "threshold_breached": "cache_hit_rate_target", 
                "current_value": final_cache,
                "threshold_value": thresholds["cache"]["target_hit_rate_percent"]
            })
        
        # Generate recommendations
        recommendations = []
        if avg_time > 5000:
            recommendations.append({
                "priority": "high",
                "category": "performance", 
                "description": "Reduce request frequency to avoid quota limits",
                "actionable": True,
                "technical_details": "Implement exponential backoff or reduce concurrent requests"
            })
        
        if final_cache < 40:
            recommendations.append({
                "priority": "medium",
                "category": "cache",
                "description": "Increase cache size using Fibonacci progression",
                "actionable": True,
                "technical_details": "Scale cache size to next Fibonacci number in sequence"
            })
        
        if golden_efficiency < 0.6:
            recommendations.append({
                "priority": "medium", 
                "category": "fibonacci",
                "description": "Implement advanced Fibonacci spiral optimization",
                "actionable": False,
                "technical_details": "Research spiral matching algorithms for better cache patterns"
            })
        
        # Standardize phase results
        standardized_phases = []
        phase_names = ["rapid_warm_up", "pattern_boost", "optimization_sprint"]
        phase_display_names = ["Rapid Cache Warm-up", "Pattern Recognition", "Fibonacci Optimization"]
        
        for i, phase in enumerate(raw_result.get('phase_results', [])):
            phase_times = phase.get('response_times', [])
            phase_avg = sum(phase_times) / len(phase_times) if phase_times else 0
            phase_success_rate = (phase.get('successful_requests', 0) / 
                                (phase.get('successful_requests', 0) + phase.get('failed_requests', 0)) * 100) if (phase.get('successful_requests', 0) + phase.get('failed_requests', 0)) > 0 else 0
            
            standardized_phases.append({
                "phase_name": phase_names[i] if i < len(phase_names) else f"phase_{i+1}",
                "phase_display_name": phase_display_names[i] if i < len(phase_display_names) else f"Phase {i+1}",
                "queries": len(phase_times),
                "avg_response_time_ms": phase_avg,
                "success_rate_percent": phase_success_rate,
                "duration_seconds": phase.get('duration_seconds', 0),
                "performance_rating": get_performance_rating(phase_avg, phase_success_rate)
            })
        
        # Build canonical result
        canonical_result = {
            "session_metadata": {
                "session_id": session_id,
                "timestamp": datetime.now().isoformat(),
                "duration_seconds": raw_result.get('duration_minutes', 0) * 60,
                "golden_ratio": golden_ratio,
                "version": "1.0.0"
            },
            "performance_metrics": {
                "avg_response_time_ms": avg_time,
                "min_response_time_ms": min(all_times) if all_times else 0,
                "max_response_time_ms": max(all_times) if all_times else 0,
                "success_rate_percent": success_rate,
                "total_requests": total_successful + total_failed,
                "successful_requests": total_successful,
                "failed_requests": total_failed,
                "performance_rating": get_performance_rating(avg_time, success_rate),
                "improvement_percent": improvement,
                "target_progress_percent": min(target_progress, 100)
            },
            "cache_metrics": {
                "initial_hit_rate_percent": initial_cache,
                "final_hit_rate_percent": final_cache,
                "hit_rate_improvement": final_cache - initial_cache,
                "total_hits": raw_result.get('total_hits', 0),
                "total_misses": raw_result.get('total_misses', 0),
                "target_hit_rate_percent": 70
            },
            "fibonacci_analysis": {
                "golden_ratio_efficiency": golden_efficiency,
                "fibonacci_status": get_fibonacci_status(golden_efficiency),
                "optimization_achieved": golden_efficiency >= 0.8 and avg_time <= target_ms,
                "golden_ratio_target": golden_target * 100
            },
            "phase_results": standardized_phases,
            "thresholds": thresholds,
            "recommendations": recommendations,
            "alerts": alerts
        }
        
        return canonical_result
    
    def export_to_prometheus(self, result: Dict, output_file: str = None) -> str:
        """Export metrics in Prometheus format."""
        if output_file is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_file = str(self.metrics_dir / f"fibonacci_metrics_{timestamp}.prom")
        
        metrics = []
        session_id = result["session_metadata"]["session_id"]
        
        # Performance metrics
        perf = result["performance_metrics"]
        metrics.append(f"# HELP fibonacci_avg_response_time_ms Average response time in milliseconds")
        metrics.append(f"# TYPE fibonacci_avg_response_time_ms gauge")
        metrics.append(f'fibonacci_avg_response_time_ms{{session_id="{session_id}"}} {perf["avg_response_time_ms"]}')
        
        metrics.append(f"# HELP fibonacci_success_rate_percent Success rate as percentage")
        metrics.append(f"# TYPE fibonacci_success_rate_percent gauge") 
        metrics.append(f'fibonacci_success_rate_percent{{session_id="{session_id}"}} {perf["success_rate_percent"]}')
        
        metrics.append(f"# HELP fibonacci_improvement_percent Improvement from baseline as percentage")
        metrics.append(f"# TYPE fibonacci_improvement_percent gauge")
        metrics.append(f'fibonacci_improvement_percent{{session_id="{session_id}"}} {perf["improvement_percent"]}')
        
        # Cache metrics
        cache = result["cache_metrics"]
        metrics.append(f"# HELP fibonacci_cache_hit_rate_percent Cache hit rate as percentage")
        metrics.append(f"# TYPE fibonacci_cache_hit_rate_percent gauge")
        metrics.append(f'fibonacci_cache_hit_rate_percent{{session_id="{session_id}"}} {cache["final_hit_rate_percent"]}')
        
        # Fibonacci analysis
        fib = result["fibonacci_analysis"]
        metrics.append(f"# HELP fibonacci_golden_ratio_efficiency Golden ratio efficiency (1.0 = optimal)")
        metrics.append(f"# TYPE fibonacci_golden_ratio_efficiency gauge")
        metrics.append(f'fibonacci_golden_ratio_efficiency{{session_id="{session_id}"}} {fib["golden_ratio_efficiency"]}')
        
        # Phase metrics
        for phase in result["phase_results"]:
            phase_name = phase["phase_name"]
            metrics.append(f'fibonacci_phase_response_time_ms{{session_id="{session_id}",phase="{phase_name}"}} {phase["avg_response_time_ms"]}')
            metrics.append(f'fibonacci_phase_success_rate_percent{{session_id="{session_id}",phase="{phase_name}"}} {phase["success_rate_percent"]}')
        
        # Alert metrics
        for alert in result["alerts"]:
            severity_value = {"critical": 3, "warning": 2, "info": 1}.get(alert["severity"], 0)
            metrics.append(f'fibonacci_alert{{session_id="{session_id}",severity="{alert["severity"]}",threshold="{alert["threshold_breached"]}"}} {severity_value}')
        
        with open(output_file, 'w') as f:
            f.write("\\n".join(metrics) + "\\n")
        
        return output_file
    
    def export_to_csv(self, result: Dict, output_file: str = None) -> str:
        """Export metrics in CSV format for historical analysis.""" 
        if output_file is None:
            output_file = str(self.metrics_dir / "fibonacci_training_history.csv")
        
        # Check if file exists to determine if we need headers
        file_exists = os.path.exists(output_file)
        
        with open(output_file, 'a', newline='') as f:
            fieldnames = [
                'timestamp', 'session_id', 'duration_seconds',
                'avg_response_time_ms', 'success_rate_percent', 'improvement_percent', 'target_progress_percent',
                'initial_cache_hit_rate', 'final_cache_hit_rate', 'cache_improvement',
                'golden_ratio_efficiency', 'fibonacci_status', 'optimization_achieved',
                'performance_rating', 'alert_count', 'recommendation_count'
            ]
            
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            
            if not file_exists:
                writer.writeheader()
            
            # Flatten data for CSV
            row = {
                'timestamp': result["session_metadata"]["timestamp"],
                'session_id': result["session_metadata"]["session_id"],
                'duration_seconds': result["session_metadata"]["duration_seconds"],
                'avg_response_time_ms': result["performance_metrics"]["avg_response_time_ms"],
                'success_rate_percent': result["performance_metrics"]["success_rate_percent"],
                'improvement_percent': result["performance_metrics"]["improvement_percent"],
                'target_progress_percent': result["performance_metrics"]["target_progress_percent"],
                'initial_cache_hit_rate': result["cache_metrics"]["initial_hit_rate_percent"],
                'final_cache_hit_rate': result["cache_metrics"]["final_hit_rate_percent"], 
                'cache_improvement': result["cache_metrics"]["hit_rate_improvement"],
                'golden_ratio_efficiency': result["fibonacci_analysis"]["golden_ratio_efficiency"],
                'fibonacci_status': result["fibonacci_analysis"]["fibonacci_status"],
                'optimization_achieved': result["fibonacci_analysis"]["optimization_achieved"],
                'performance_rating': result["performance_metrics"]["performance_rating"],
                'alert_count': len(result["alerts"]),
                'recommendation_count': len(result["recommendations"])
            }
            
            writer.writerow(row)
        
        return output_file
    
    def export_to_grafana_json(self, result: Dict, output_file: str = None) -> str:
        """Export metrics in Grafana JSON format for dashboards."""
        if output_file is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_file = str(self.metrics_dir / f"grafana_data_{timestamp}.json")
        
        # Grafana-compatible time series data
        grafana_data = {
            "dashboard": {
                "title": "Fibonacci Training Metrics",
                "tags": ["fibonacci", "training", "performance"],
                "timezone": "UTC",
                "panels": []
            },
            "timeSeries": {
                "responseTime": {
                    "target": "fibonacci.response_time",
                    "datapoints": [
                        [result["performance_metrics"]["avg_response_time_ms"], 
                         int(datetime.fromisoformat(result["session_metadata"]["timestamp"]).timestamp() * 1000)]
                    ]
                },
                "cacheHitRate": {
                    "target": "fibonacci.cache_hit_rate",
                    "datapoints": [
                        [result["cache_metrics"]["final_hit_rate_percent"],
                         int(datetime.fromisoformat(result["session_metadata"]["timestamp"]).timestamp() * 1000)]
                    ]
                },
                "goldenRatioEfficiency": {
                    "target": "fibonacci.golden_ratio_efficiency", 
                    "datapoints": [
                        [result["fibonacci_analysis"]["golden_ratio_efficiency"],
                         int(datetime.fromisoformat(result["session_metadata"]["timestamp"]).timestamp() * 1000)]
                    ]
                }
            },
            "annotations": [
                {
                    "time": int(datetime.fromisoformat(result["session_metadata"]["timestamp"]).timestamp() * 1000),
                    "title": f"Training Session: {result['session_metadata']['session_id']}",
                    "text": f"Performance: {result['performance_metrics']['performance_rating']} | "
                           f"Fibonacci Status: {result['fibonacci_analysis']['fibonacci_status']}",
                    "tags": ["training", "fibonacci"]
                }
            ]
        }
        
        with open(output_file, 'w') as f:
            json.dump(grafana_data, f, indent=2)
        
        return output_file
    
    def process_latest_training_result(self) -> Optional[Dict]:
        """Find and process the latest training result."""
        # Find latest result file
        result_files = list(self.logs_dir.glob("fibonacci_training_results_*.json"))
        if not result_files:
            print("No training result files found")
            return None
        
        latest_file = max(result_files, key=lambda f: f.stat().st_mtime)
        print(f"Processing latest result: {latest_file}")
        
        # Load and standardize
        try:
            with open(latest_file, 'r') as f:
                raw_result = json.load(f)
            
            canonical_result = self.standardize_training_result(raw_result)
            
            # Validate against schema
            if self.validate_training_result(canonical_result):
                print("✅ Result validated against canonical schema")
            else:
                print("⚠️  Result validation failed - proceeding anyway")
            
            return canonical_result
            
        except Exception as e:
            print(f"Error processing result file: {e}")
            return None
    
    def export_all_formats(self, result: Dict = None) -> Dict[str, str]:
        """Export to all monitoring formats."""
        if result is None:
            result = self.process_latest_training_result()
            if result is None:
                return {}
        
        output_files = {}
        
        try:
            # Export to Prometheus
            prom_file = self.export_to_prometheus(result)
            output_files["prometheus"] = prom_file
            print(f"📊 Prometheus metrics: {prom_file}")
            
            # Export to CSV
            csv_file = self.export_to_csv(result)
            output_files["csv"] = csv_file
            print(f"📈 CSV history: {csv_file}")
            
            # Export to Grafana JSON
            grafana_file = self.export_to_grafana_json(result)
            output_files["grafana"] = grafana_file
            print(f"📉 Grafana JSON: {grafana_file}")
            
            # Save canonical result
            canonical_file = str(self.metrics_dir / f"canonical_{result['session_metadata']['session_id']}.json")
            with open(canonical_file, 'w') as f:
                json.dump(result, f, indent=2)
            output_files["canonical"] = canonical_file
            print(f"🎯 Canonical result: {canonical_file}")
            
        except Exception as e:
            print(f"Error during export: {e}")
        
        return output_files


def main():
    """Main execution for command line usage."""
    exporter = FibonacciMetricsExporter()
    
    print("🔄 Processing latest Fibonacci training results...")
    result = exporter.process_latest_training_result()
    
    if result:
        print("\\n📊 Exporting to all monitoring formats...")
        output_files = exporter.export_all_formats(result)
        
        if output_files:
            print(f"\\n✅ Successfully exported {len(output_files)} formats:")
            for format_name, file_path in output_files.items():
                print(f"   • {format_name}: {file_path}")
            
            # Print summary
            print(f"\\n📋 TRAINING SUMMARY:")
            print(f"   Session: {result['session_metadata']['session_id']}")
            print(f"   Performance: {result['performance_metrics']['performance_rating']} "
                  f"({result['performance_metrics']['avg_response_time_ms']:.1f}ms avg)")
            print(f"   Cache Hit Rate: {result['cache_metrics']['final_hit_rate_percent']:.1f}%")
            print(f"   Fibonacci Status: {result['fibonacci_analysis']['fibonacci_status']}")
            print(f"   Alerts: {len(result['alerts'])} active")
            print(f"   Recommendations: {len(result['recommendations'])} pending")
        else:
            print("❌ Export failed")
    else:
        print("❌ No training results found to process")


if __name__ == "__main__":
    main()