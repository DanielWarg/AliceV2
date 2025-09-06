#!/usr/bin/env python3
"""
🧮 Simple Fibonacci Training - Alice v2 Cache Optimization
Simplified training utan external dependencies - använder curl direkt
"""

import json
import os
import random
import subprocess
import time
from datetime import datetime
from pathlib import Path

# Fibonacci constants
FIBONACCI_SEQUENCE = [
    1,
    1,
    2,
    3,
    5,
    8,
    13,
    21,
    34,
    55,
    89,
    144,
    233,
    377,
    610,
    987,
    1597,
    2584,
    4181,
    6765,
    10946,
    17711,
]
GOLDEN_RATIO = 1.618033988749


class SimpleFibonacciTraining:
    def __init__(self):
        self.orchestrator_url = "http://localhost:8000"
        self.results = []
        self.session_id = f"fibonacci_training_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        self.log_file = f"fibonacci_training_log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        
        # Create logs directory if it doesn't exist
        os.makedirs("logs", exist_ok=True)
        self.log_path = Path("logs") / self.log_file
        
        # Fast training phases
        self.phases = {
            "rapid_warm_up": {"queries": 21, "name": "Rapid Cache Warm-up"},
            "pattern_boost": {"queries": 34, "name": "Pattern Recognition"},
            "optimization_sprint": {"queries": 55, "name": "Fibonacci Optimization"},
        }
        
        # Initialize logging
        self.log_message(f"🧮 FIBONACCI TRAINING SESSION STARTED: {self.session_id}")

    def generate_training_queries(self):
        """Generate diverse queries för cache warming"""
        queries = [
            # Fibonacci & Golden Ratio queries
            "Vad är Fibonacci tal?",
            "What is Fibonacci sequence?",
            "Beräkna golden ratio",
            "Calculate 1.618",
            "Fibonacci sekvens förklaring",
            "Golden ratio explanation",
            "Vad är φ (phi)?",
            "Phi mathematical constant",
            # Common Alice queries
            "Vad är klockan?",
            "What time is it?",
            "Hej Alice",
            "Hello Alice",
            "Hjälp mig",
            "Help me",
            "Tack så mycket",
            "Thank you",
            # Swedish variations
            "Fibonacci i naturen",
            "Fibonacci in nature",
            "Golden ratio design",
            "Gyllene snittet",
            "Spiral patterns",
            "Spiral mönster",
            # Mathematical queries
            "1 + 1 = ?",
            "Beräkna 42 * 1.618",
            "What is 5 + 8?",
            "Calculate 13 * 21",
            "Math help",
            "Matematik hjälp",
            # System queries
            "System status",
            "Cache performance",
            "Response time",
            "Memory usage",
            "Health check",
            "Hälsokontroll",
        ]

        return queries
    
    def log_message(self, message: str, also_print: bool = True):
        """Log message to file and optionally print to console"""
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        log_entry = f"[{timestamp}] {message}"
        
        # Write to log file
        try:
            with open(self.log_path, 'a', encoding='utf-8') as f:
                f.write(log_entry + '\n')
        except Exception as e:
            print(f"Warning: Could not write to log file: {e}")
        
        # Print to console if requested
        if also_print:
            print(message)
    
    def generate_phase_report(self, phase_results: dict, phase_name: str) -> str:
        """Generate detailed phase completion report"""
        if not phase_results or not phase_results.get('response_times'):
            return f"❌ Phase {phase_name} failed - no successful responses"
        
        avg_time = phase_results.get('avg_response_time', 0)
        success_rate = (phase_results.get('successful_requests', 0) / 
                       (phase_results.get('successful_requests', 0) + phase_results.get('failed_requests', 0)) * 100)
        cache_stats = phase_results.get('cache_stats', {})
        
        # Performance rating
        if avg_time < 1000:
            performance = "🟢 Excellent"
        elif avg_time < 5000:
            performance = "🟡 Good"
        else:
            performance = "🔴 Poor (likely quota limited)"
        
        report = f"""
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🎯 PHASE COMPLETE: {phase_name.upper()}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📊 Performance: {performance}
   • Average Response: {avg_time:.1f}ms
   • Min/Max: {phase_results.get('min_response_time', 0):.0f}ms - {phase_results.get('max_response_time', 0):.0f}ms
   • Success Rate: {success_rate:.1f}% ({phase_results.get('successful_requests', 0)}/{phase_results.get('successful_requests', 0) + phase_results.get('failed_requests', 0)} requests)

💾 Cache Performance:
   • Hit Rate: {cache_stats.get('hit_rate', 0):.1f}%
   • Hits/Misses: {cache_stats.get('hits', 0)}/{cache_stats.get('misses', 0)}

⏱️  Timing Analysis:
   • Requests < 1s: {len([t for t in phase_results['response_times'] if t < 1000])}
   • Requests 1-5s: {len([t for t in phase_results['response_times'] if 1000 <= t < 5000])}
   • Requests > 5s: {len([t for t in phase_results['response_times'] if t >= 5000])}
   
{self._get_performance_analysis(avg_time, success_rate)}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"""
        return report
    
    def _get_performance_analysis(self, avg_time: float, success_rate: float) -> str:
        """Provide analysis and recommendations based on performance"""
        analysis = "\n🔍 Analysis:\n"
        
        if avg_time > 10000:  # > 10s
            analysis += "   • QUOTA EXCEEDED: System forced to use planner route\n"
            analysis += "   • Recommendation: Wait for quota reset or reduce request frequency\n"
        elif avg_time > 5000:  # > 5s
            analysis += "   • SLOW RESPONSES: Possible quota limits or system load\n"
            analysis += "   • Recommendation: Monitor system resources\n"
        elif avg_time < 500:  # < 0.5s
            analysis += "   • OPTIMAL PERFORMANCE: Fast micro route responses\n"
            analysis += "   • Status: Fibonacci optimization working well\n"
        
        if success_rate < 80:
            analysis += "   • LOW SUCCESS RATE: Check service connectivity\n"
        elif success_rate > 95:
            analysis += "   • EXCELLENT SUCCESS RATE: System stable\n"
        
        return analysis
    
    def post_phase_report(self, phase_results: dict, phase_name: str):
        """Post comprehensive phase completion report"""
        report = self.generate_phase_report(phase_results, phase_name)
        
        # Log the full report
        self.log_message(report, also_print=True)
        
        # Also save individual phase report to separate file
        phase_report_file = f"logs/phase_{phase_name}_{datetime.now().strftime('%H%M%S')}.txt"
        try:
            with open(phase_report_file, 'w', encoding='utf-8') as f:
                f.write(report)
                f.write(f"\n\n📋 Raw Data:\n{json.dumps(phase_results, indent=2)}")
        except Exception as e:
            self.log_message(f"Warning: Could not save phase report: {e}")
    
    def generate_final_report(self, all_results: list, initial_cache: dict, final_cache: dict, total_duration: float) -> str:
        """Generate comprehensive final training report"""
        if not all_results:
            return "❌ No training results to report"
        
        # Calculate overall statistics
        all_response_times = []
        total_successful = 0
        total_failed = 0
        
        for result in all_results:
            if 'response_times' in result:
                all_response_times.extend(result['response_times'])
            total_successful += result.get('successful_requests', 0)
            total_failed += result.get('failed_requests', 0)
        
        if not all_response_times:
            return "❌ No successful responses to analyze"
        
        overall_avg = sum(all_response_times) / len(all_response_times)
        baseline_ms = 417  # From comments in original code
        improvement = ((baseline_ms - overall_avg) / baseline_ms) * 100
        
        # Target analysis
        target_ms = 35.9
        target_progress = ((baseline_ms - overall_avg) / (baseline_ms - target_ms)) * 100
        
        final_report = f"""
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🏁 FIBONACCI TRAINING COMPLETE - FINAL REPORT
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📊 OVERALL PERFORMANCE:
   • Duration: {total_duration/60:.1f} minutes
   • Total Requests: {total_successful + total_failed}
   • Success Rate: {(total_successful/(total_successful + total_failed)*100):.1f}%
   
⚡ RESPONSE TIME ANALYSIS:
   • Overall Average: {overall_avg:.1f}ms
   • Baseline (pre-training): {baseline_ms}ms
   • Improvement: {improvement:+.1f}%
   • Best Response: {min(all_response_times):.1f}ms
   • Worst Response: {max(all_response_times):.1f}ms
   
🎯 TARGET PROGRESS:
   • Target: {target_ms}ms (38.2% improvement)
   • Current Progress: {target_progress:.1f}% towards target
   • Status: {"🎉 TARGET ACHIEVED!" if overall_avg <= target_ms else "🔄 In Progress"}
   
💾 CACHE IMPROVEMENT:
   • Initial Hit Rate: {initial_cache.get('hit_rate', 0):.1f}%
   • Final Hit Rate: {final_cache.get('hit_rate', 0):.1f}%
   • Improvement: {final_cache.get('hit_rate', 0) - initial_cache.get('hit_rate', 0):+.1f} percentage points
   • Target: 70%+ hit rate
   
📈 PHASE BREAKDOWN:
{self._generate_phase_breakdown(all_results)}
   
🔍 FIBONACCI ANALYSIS:
   • Golden Ratio φ: {GOLDEN_RATIO}
   • Optimization Status: {self._get_fibonacci_status(overall_avg, final_cache.get('hit_rate', 0))}
   
📋 RECOMMENDATIONS:
{self._generate_recommendations(overall_avg, final_cache.get('hit_rate', 0), improvement)}

📁 Session ID: {self.session_id}
📄 Full logs: {self.log_path}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"""
        return final_report
    
    def _generate_phase_breakdown(self, all_results: list) -> str:
        """Generate breakdown of all phase results"""
        breakdown = ""
        for i, result in enumerate(all_results):
            phase_name = result.get('phase', f'Phase_{i+1}')
            avg_time = result.get('avg_response_time', 0)
            success_rate = (result.get('successful_requests', 0) / 
                           (result.get('successful_requests', 0) + result.get('failed_requests', 0)) * 100)
            
            status = "🟢" if avg_time < 1000 and success_rate > 90 else "🟡" if success_rate > 70 else "🔴"
            breakdown += f"   {status} {phase_name}: {avg_time:.1f}ms ({success_rate:.1f}% success)\n"
        
        return breakdown
    
    def _get_fibonacci_status(self, avg_time: float, hit_rate: float) -> str:
        """Analyze performance relative to Fibonacci/Golden Ratio principles"""
        # Golden ratio target for cache hit rate (φ^-1 ≈ 0.618 = 61.8%)
        golden_target = 1 / GOLDEN_RATIO  # ≈ 0.618
        
        if hit_rate/100 >= golden_target and avg_time < 200:
            return "🌟 Excellent - Golden Ratio optimization achieved"
        elif hit_rate/100 >= golden_target * 0.8:
            return "📈 Good - Approaching Golden Ratio efficiency"
        else:
            return "⚠️ Needs Improvement - Below optimal Fibonacci performance"
    
    def _generate_recommendations(self, avg_time: float, hit_rate: float, improvement: float) -> str:
        """Generate actionable recommendations based on results"""
        recommendations = []
        
        if avg_time > 5000:
            recommendations.append("• Reduce request frequency to avoid quota limits")
            recommendations.append("• Consider running training during off-peak hours")
        
        if hit_rate < 40:
            recommendations.append("• Increase cache size using Fibonacci progression")
            recommendations.append("• Implement Fibonacci-based TTL optimization")
        
        if improvement < 10:
            recommendations.append("• Run longer training sessions for better cache warming")
            recommendations.append("• Diversify query patterns for better coverage")
        
        if not recommendations:
            recommendations.append("• System is performing well - continue monitoring")
            recommendations.append("• Consider advanced Fibonacci spiral matching optimization")
        
        return "\n".join(recommendations)
    
    def post_final_report(self, all_results: list, initial_cache: dict, final_cache: dict, total_duration: float):
        """Post and save final comprehensive report"""
        final_report = self.generate_final_report(all_results, initial_cache, final_cache, total_duration)
        
        # Log to main log file
        self.log_message(final_report, also_print=True)
        
        # Save final report to dedicated file
        final_report_file = f"logs/FINAL_REPORT_{self.session_id}.txt"
        try:
            with open(final_report_file, 'w', encoding='utf-8') as f:
                f.write(final_report)
                f.write(f"\n\n🗃️ FULL SESSION DATA:\n{json.dumps(all_results, indent=2)}")
            
            self.log_message(f"\n💾 Final report saved to: {final_report_file}")
        except Exception as e:
            self.log_message(f"Warning: Could not save final report: {e}")

    def make_request(self, message, session_id):
        """Make HTTP request using curl with enhanced error reporting"""
        payload = {
            "message": message,
            "session_id": session_id,
            "context": {"training": True, "fibonacci_optimization": True},
        }

        try:
            cmd = [
                "docker",
                "exec",
                "alice-orchestrator",
                "curl",
                "-s",
                "-X",
                "POST",
                "http://localhost:8000/api/orchestrator/chat",
                "-H",
                "Content-Type: application/json",
                "-d",
                json.dumps(payload),
            ]

            start_time = time.time()
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=45)  # Increased timeout
            end_time = time.time()

            response_time_ms = (end_time - start_time) * 1000
            
            # Enhanced error detection
            if result.returncode == 0 and result.stdout.strip():
                try:
                    response_data = json.loads(result.stdout)
                    
                    # Check for quota exceeded in response
                    if "quota" in result.stdout.lower() or "exceeded" in result.stdout.lower():
                        print(f"\n⚠️  QUOTA WARNING: Response time {response_time_ms:.0f}ms suggests quota limits")
                    
                    # Warn about slow responses
                    if response_time_ms > 10000:  # 10 seconds
                        print(f"\n🐌 SLOW RESPONSE: {response_time_ms/1000:.1f}s - likely quota exceeded, using planner route")
                    elif response_time_ms > 5000:  # 5 seconds
                        print(f"\n⏰ MODERATE DELAY: {response_time_ms/1000:.1f}s - possible routing issues")
                    
                    return {
                        "success": True,
                        "response_time_ms": response_time_ms,
                        "response": response_data,
                        "warning": "slow_response" if response_time_ms > 5000 else None
                    }
                except json.JSONDecodeError as e:
                    print(f"\n❌ JSON DECODE ERROR: {e}")
                    print(f"   Raw response: {result.stdout[:200]}...")
                    return {
                        "success": False,
                        "response_time_ms": response_time_ms,
                        "error": f"JSON decode error: {e}",
                        "raw_response": result.stdout[:500]  # First 500 chars for debugging
                    }
            else:
                error_details = []
                if result.returncode != 0:
                    error_details.append(f"Exit code: {result.returncode}")
                if result.stderr:
                    error_details.append(f"Stderr: {result.stderr.strip()}")
                if not result.stdout.strip():
                    error_details.append("Empty response")
                    
                error_msg = "; ".join(error_details) or "Request failed"
                print(f"\n❌ REQUEST FAILED: {error_msg}")
                
                return {
                    "success": False,
                    "response_time_ms": response_time_ms,
                    "error": error_msg,
                    "returncode": result.returncode,
                    "stderr": result.stderr
                }

        except subprocess.TimeoutExpired:
            print(f"\n⏰ REQUEST TIMEOUT: Query took >45s - likely orchestrator issues")
            return {
                "success": False,
                "response_time_ms": 45000,  # Timeout
                "error": "Request timeout (45s)",
                "suggestion": "Check if orchestrator is responsive"
            }
        except Exception as e:
            print(f"\n💥 UNEXPECTED ERROR: {type(e).__name__}: {e}")
            return {
                "success": False, 
                "response_time_ms": 0, 
                "error": f"Exception: {type(e).__name__}: {e}",
                "suggestion": "Check Docker and service health"
            }

    def get_cache_stats(self):
        """Get Redis cache statistics"""
        try:
            cmd = ["docker", "exec", "alice-cache", "redis-cli", "info", "stats"]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)

            if result.returncode == 0:
                lines = result.stdout.strip().split("\n")
                stats = {}
                for line in lines:
                    if ":" in line and not line.startswith("#"):
                        key, value = line.split(":", 1)
                        if key in ["keyspace_hits", "keyspace_misses"]:
                            stats[key] = int(value.strip())

                total_ops = stats.get("keyspace_hits", 0) + stats.get(
                    "keyspace_misses", 0
                )
                hit_rate = (
                    (stats.get("keyspace_hits", 0) / total_ops * 100)
                    if total_ops > 0
                    else 0
                )

                return {
                    "hits": stats.get("keyspace_hits", 0),
                    "misses": stats.get("keyspace_misses", 0),
                    "hit_rate": hit_rate,
                }
        except Exception as e:
            print(f"Cache stats error: {e}")

        return {"hits": 0, "misses": 0, "hit_rate": 0}

    def run_training_phase(self, phase_name, phase_config):
        """Run en träningsfas"""
        print(f"\n🧮 PHASE: {phase_config['name']}")
        print(
            f"Queries: {phase_config['queries']} | Target: Cache warming & pattern learning"
        )

        queries = self.generate_training_queries()
        selected_queries = random.choices(queries, k=phase_config["queries"])

        phase_results = {
            "phase": phase_name,
            "start_time": datetime.utcnow().isoformat(),
            "response_times": [],
            "successful_requests": 0,
            "failed_requests": 0,
        }

        for i, query in enumerate(selected_queries):
            session_id = f"fib_training_{phase_name}_{i}"

            print(
                f"  Request {i+1:2d}/{phase_config['queries']}: '{query[:40]}{'...' if len(query) > 40 else ''}' ",
                end="",
            )

            result = self.make_request(query, session_id)

            if result["success"]:
                phase_results["response_times"].append(result["response_time_ms"])
                phase_results["successful_requests"] += 1
                
                # Color-coded success based on response time
                if result["response_time_ms"] < 1000:  # < 1s
                    print(f"✅ {result['response_time_ms']:.0f}ms")
                elif result["response_time_ms"] < 5000:  # < 5s
                    print(f"🟡 {result['response_time_ms']:.0f}ms (slow)")
                else:  # >= 5s
                    print(f"🔴 {result['response_time_ms']:.0f}ms (very slow)")
                    
                # Log warnings for problematic responses
                if result.get("warning"):
                    print(f"      ⚠️  Warning: {result['warning']}")
                    
            else:
                phase_results["failed_requests"] += 1
                error_msg = result.get('error', 'Failed')
                print(f"❌ {error_msg}")
                
                # Add detailed error info
                if result.get('suggestion'):
                    print(f"      💡 Suggestion: {result['suggestion']}")
                    
                # Critical failure detection
                if phase_results["failed_requests"] >= 5:
                    print(f"\n🚨 CRITICAL: {phase_results['failed_requests']} consecutive failures!")
                    print(f"   Consider checking service health or stopping training")

            # Progress update every 10 requests
            if (i + 1) % 10 == 0:
                if phase_results["response_times"]:
                    avg_time = sum(phase_results["response_times"]) / len(
                        phase_results["response_times"]
                    )
                    cache_stats = self.get_cache_stats()

                    print(
                        f"    🎯 Progress: {i+1}/{phase_config['queries']} | "
                        f"Avg: {avg_time:.1f}ms | "
                        f"Cache: {cache_stats['hit_rate']:.1f}% hit rate"
                    )

            # Small delay mellan requests
            time.sleep(0.2)

        # Phase summary
        if phase_results["response_times"]:
            avg_time = sum(phase_results["response_times"]) / len(
                phase_results["response_times"]
            )
            min_time = min(phase_results["response_times"])
            max_time = max(phase_results["response_times"])

            phase_results.update(
                {
                    "avg_response_time": avg_time,
                    "min_response_time": min_time,
                    "max_response_time": max_time,
                }
            )

            print("\n📊 Phase Results:")
            print(f"    Average: {avg_time:.1f}ms")
            print(f"    Range: {min_time:.1f}ms - {max_time:.1f}ms")
            print(
                f"    Success Rate: {phase_results['successful_requests']}/{phase_config['queries']} "
                f"({phase_results['successful_requests']/phase_config['queries']*100:.1f}%)"
            )

        cache_stats = self.get_cache_stats()
        phase_results["cache_stats"] = cache_stats

        print(
            f"    Cache Stats: {cache_stats['hits']} hits, {cache_stats['misses']} misses "
            f"({cache_stats['hit_rate']:.1f}% hit rate)"
        )

        self.results.append(phase_results)
        
        # Post comprehensive phase report
        self.post_phase_report(phase_results, phase_name)
        
        return phase_results

    def check_prerequisites(self):
        """Check if all services are ready before training"""
        print("\n🔍 Checking prerequisites...")
        issues = []
        
        # Check Docker services
        try:
            result = subprocess.run(["docker", "ps"], capture_output=True, text=True)
            if "alice-orchestrator" not in result.stdout:
                issues.append("❌ alice-orchestrator not running")
            elif "(healthy)" not in result.stdout:
                issues.append("⚠️  alice-orchestrator not healthy")
                
            if "alice-cache" not in result.stdout:
                issues.append("❌ alice-cache not running")
        except Exception as e:
            issues.append(f"❌ Docker check failed: {e}")
            
        # Quick health check
        try:
            result = subprocess.run([
                "docker", "exec", "alice-orchestrator", 
                "curl", "-s", "-f", "http://localhost:8000/health"
            ], capture_output=True, text=True, timeout=5)
            if result.returncode != 0:
                issues.append("❌ Orchestrator health check failed")
        except Exception as e:
            issues.append(f"❌ Health check failed: {e}")
        
        if issues:
            print("\n🚨 PREREQUISITES FAILED:")
            for issue in issues:
                print(f"   {issue}")
            print("\n💡 Try running: make down && make up")
            return False
        else:
            print("✅ All prerequisites OK")
            return True
    
    def run_full_training(self):
        """Run complete Fibonacci training loop with enhanced monitoring"""
        print("🧮 FIBONACCI CACHE TRAINING STARTED")
        print(f"Timestamp: {datetime.utcnow().isoformat()}")
        print("Target: Improve from 417ms baseline → 35.9ms (38.2% improvement)")
        print(f"Golden Ratio: φ = {GOLDEN_RATIO}")

        # Check prerequisites first
        if not self.check_prerequisites():
            print("\n❌ Training aborted due to prerequisite failures")
            return {"error": "Prerequisites not met"}

        # Initial cache stats
        initial_cache = self.get_cache_stats()
        print(f"Initial Cache: {initial_cache['hit_rate']:.1f}% hit rate")

        start_time = time.time()
        consecutive_failures = 0

        # Run all training phases with enhanced error handling
        for phase_name, phase_config in self.phases.items():
            try:
                print(f"\n🚀 Starting phase: {phase_name}")
                self.log_message(f"🚀 PHASE START: {phase_name} - {phase_config['name']}")
                phase_result = self.run_training_phase(phase_name, phase_config)
                
                # Check phase success rate
                if phase_result and "successful_requests" in phase_result:
                    success_rate = phase_result["successful_requests"] / phase_config["queries"] * 100
                    if success_rate < 50:
                        warning_msg = f"⚠️  WARNING: Phase {phase_name} had low success rate: {success_rate:.1f}%"
                        print(f"\n{warning_msg}")
                        self.log_message(warning_msg)
                        consecutive_failures += 1
                    else:
                        consecutive_failures = 0  # Reset on success
                        self.log_message(f"✅ Phase {phase_name} completed successfully: {success_rate:.1f}% success rate")
                        
                    # Abort if too many failures
                    if consecutive_failures >= 2:
                        print(f"\n🚨 ABORTING: Too many failed phases ({consecutive_failures})")
                        print("   Check service health and network connectivity")
                        break
                        
            except KeyboardInterrupt:
                print(f"\n⚠️ Training interrupted during {phase_name}")
                print("   Gracefully shutting down...")
                break
            except Exception as e:
                print(f"\n❌ Phase {phase_name} failed with exception: {type(e).__name__}: {e}")
                consecutive_failures += 1
                if consecutive_failures >= 2:
                    print(f"\n🚨 ABORTING: Too many consecutive failures")
                    break
                print(f"   Continuing to next phase...")
                continue

        end_time = time.time()
        total_duration = end_time - start_time

        # Final analysis
        print("\n🎯 FIBONACCI TRAINING COMPLETE!")
        print(f"Duration: {total_duration/60:.1f} minutes")

        if self.results:
            all_response_times = []
            for result in self.results:
                if "response_times" in result:
                    all_response_times.extend(result["response_times"])

            if all_response_times:
                overall_avg = sum(all_response_times) / len(all_response_times)
                improvement = (417 - overall_avg) / 417 * 100

                print("\n📈 PERFORMANCE RESULTS:")
                print("    Baseline: 417ms (pre-training)")
                print(f"    Current: {overall_avg:.1f}ms (post-training)")
                print(f"    Improvement: {improvement:+.1f}%")
                print(
                    f"    Target Progress: {((417-overall_avg)/(417-35.9)*100):.1f}% towards 35.9ms goal"
                )

        # Final cache stats
        final_cache = self.get_cache_stats()
        print("\n💾 CACHE PERFORMANCE:")
        print(f"    Initial: {initial_cache['hit_rate']:.1f}% hit rate")
        print(f"    Final: {final_cache['hit_rate']:.1f}% hit rate")
        print(
            f"    Improvement: {final_cache['hit_rate'] - initial_cache['hit_rate']:+.1f} percentage points"
        )
        print("    Target: 70%+ hit rate")

        # Post comprehensive final report
        self.post_final_report(self.results, initial_cache, final_cache, total_duration)
        
        # Success evaluation
        success_criteria = {
            "performance_improved": len(all_response_times) > 0 and overall_avg < 417,
            "cache_improved": final_cache["hit_rate"] > initial_cache["hit_rate"],
            "target_progress": len(all_response_times) > 0
            and overall_avg < 300,  # Reasonable progress
        }

        successful_criteria = sum(success_criteria.values())
        self.log_message(f"\n✅ SUCCESS CRITERIA: {successful_criteria}/3")

        for criterion, met in success_criteria.items():
            status = "✅" if met else "❌"
            self.log_message(f"    {status} {criterion}")

        return {
            "duration_minutes": total_duration / 60,
            "phases_completed": len(self.results),
            "overall_avg_ms": overall_avg if all_response_times else None,
            "performance_improvement_pct": improvement if all_response_times else None,
            "initial_cache_hit_rate": initial_cache["hit_rate"],
            "final_cache_hit_rate": final_cache["hit_rate"],
            "success_criteria_met": successful_criteria,
        }


if __name__ == "__main__":
    trainer = SimpleFibonacciTraining()
    results = trainer.run_full_training()

    # Save results in logs directory
    os.makedirs("logs", exist_ok=True)
    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    results_file = f"logs/fibonacci_training_results_{timestamp}.json"
    with open(results_file, "w") as f:
        json.dump(results, f, indent=2)

    print(
        f"\n🧮 Training complete! Results saved to {results_file}"
    )
    print(f"📊 Full session logs available in: logs/")
    print(f"🎯 Session ID: {trainer.session_id}")
    
    # Print summary of all generated files
    log_files = list(Path("logs").glob(f"*{trainer.session_id.split('_')[-2]}_{trainer.session_id.split('_')[-1]}*"))
    all_files = list(Path("logs").glob(f"*{timestamp}*")) + log_files
    
    if all_files:
        print(f"\n📁 Generated files:")
        for log_file in sorted(set(all_files)):
            size = log_file.stat().st_size
            print(f"   • {log_file} ({size} bytes)")
