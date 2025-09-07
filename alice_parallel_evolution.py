#!/usr/bin/env python3
"""
🧠 ALICE PARALLEL EVOLUTION - Multi-Component Self-Improvement
Tränar Alice som en egen entitet med parallell inlärning på alla komponenter
"""

import asyncio
import json
import subprocess
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).parent
WEIGHTS_DIR = PROJECT_ROOT / "weights"
DATA_DIR = PROJECT_ROOT / "data" 
EVOLUTION_DIR = DATA_DIR / "evolution"
EVOLUTION_DIR.mkdir(exist_ok=True, parents=True)


@dataclass
class EvolutionComponent:
    """En komponent av Alice som kan tränas parallellt"""
    name: str
    script_path: str
    data_requirements: List[str]
    slo_thresholds: Dict[str, float]
    priority: float  # Fibonacci weight
    training_time_hours: float
    version: str = "v1"
    status: str = "pending"
    last_reward: float = 0.0


@dataclass
class AliceEvolution:
    """Alice's självständiga utvecklingsprocess"""
    
    generation: int = 1
    components: List[EvolutionComponent] = None
    active_trainings: Dict[str, Any] = None
    evolution_log: List[Dict] = None
    
    def __post_init__(self):
        if self.components is None:
            self.components = self._initialize_components()
        if self.active_trainings is None:
            self.active_trainings = {}
        if self.evolution_log is None:
            self.evolution_log = []
    
    def _initialize_components(self) -> List[EvolutionComponent]:
        """Initialisera Alice's komponenter för parallell träning"""
        
        return [
            # Core Intelligence Components
            EvolutionComponent(
                name="ToolSelector",
                script_path="services/toolselector/train_lora.py",
                data_requirements=["night_test_episodes_train.jsonl"],
                slo_thresholds={"tool_precision": 0.85, "latency_ms": 200},
                priority=1.618,  # Highest priority - Golden Ratio
                training_time_hours=0.5
            ),
            
            EvolutionComponent(
                name="RouteOptimizer", 
                script_path="services/routing/train_bandit.py",
                data_requirements=["telemetry_routing_data.jsonl"],
                slo_thresholds={"route_accuracy": 0.90, "latency_ms": 100},
                priority=1.0,  # Base priority
                training_time_hours=0.3
            ),
            
            EvolutionComponent(
                name="CacheIntelligence",
                script_path="services/cache/train_hit_predictor.py", 
                data_requirements=["cache_performance_data.jsonl"],
                slo_thresholds={"hit_rate": 0.40, "prediction_accuracy": 0.80},
                priority=0.618,  # φ^-1
                training_time_hours=0.25
            ),
            
            EvolutionComponent(
                name="ContextOptimizer",
                script_path="services/orchestrator/train_context_tuner.py",
                data_requirements=["context_window_data.jsonl"],
                slo_thresholds={"context_efficiency": 0.85, "memory_usage": 0.80},
                priority=0.382,  # φ^-2  
                training_time_hours=0.4
            ),
            
            # Advanced Intelligence 
            EvolutionComponent(
                name="SwedishLanguageModel",
                script_path="services/language/train_swedish_adapter.py",
                data_requirements=["swedish_conversation_data.jsonl"],
                slo_thresholds={"language_fluency": 0.90, "cultural_accuracy": 0.85},
                priority=1.382,  # φ^0.5
                training_time_hours=1.0
            ),
            
            EvolutionComponent(
                name="IntentPredictor",
                script_path="services/nlu/train_intent_classifier.py",
                data_requirements=["intent_classification_data.jsonl"], 
                slo_thresholds={"intent_accuracy": 0.92, "confidence_calibration": 0.80},
                priority=0.854,  # (φ+1)/3
                training_time_hours=0.6
            )
        ]


class ParallelEvolutionEngine:
    """Engine för Alice's parallella evolution"""
    
    def __init__(self):
        self.alice = AliceEvolution()
        self.max_parallel_trainings = 4  # Baserat på systemresurser
        self.executor = ProcessPoolExecutor(max_workers=self.max_parallel_trainings)
        
    def start_evolution_cycle(self) -> Dict[str, Any]:
        """Starta en fullständig evolutionscykel"""
        
        cycle_start = datetime.now()
        logger.info(f"🧠 Starting Alice Evolution Generation {self.alice.generation}")
        
        # 1. Data preparation för alla komponenter
        self._prepare_evolution_data()
        
        # 2. Pre-evolution SLO check
        baseline_performance = self._measure_baseline_performance()
        
        # 3. Starta parallell träning (Fibonacci-prioriterad)
        training_futures = self._start_parallel_trainings()
        
        # 4. Monitor och hantera träningar
        evolution_results = self._monitor_evolution_progress(training_futures)
        
        # 5. Integration och deployment
        integration_success = self._integrate_evolved_components(evolution_results)
        
        # 6. Post-evolution validation
        new_performance = self._measure_post_evolution_performance()
        
        cycle_end = datetime.now()
        cycle_duration = (cycle_end - cycle_start).total_seconds() / 3600  # hours
        
        evolution_summary = {
            "generation": self.alice.generation,
            "cycle_start": cycle_start.isoformat(),
            "cycle_end": cycle_end.isoformat(), 
            "duration_hours": cycle_duration,
            "components_trained": len(evolution_results),
            "successful_integrations": sum(1 for r in evolution_results.values() if r.get('success')),
            "baseline_performance": baseline_performance,
            "post_evolution_performance": new_performance,
            "performance_improvement": self._calculate_improvement(baseline_performance, new_performance),
            "fibonacci_efficiency": self._calculate_fibonacci_efficiency(evolution_results),
            "alice_intelligence_level": self._assess_intelligence_level(new_performance)
        }
        
        self._log_evolution_cycle(evolution_summary)
        
        # Alice blir smartare!
        self.alice.generation += 1
        
        logger.info(f"🎉 Evolution Generation {self.alice.generation-1} Complete!")
        logger.info(f"Intelligence Level: {evolution_summary['alice_intelligence_level']}")
        
        return evolution_summary
    
    def _prepare_evolution_data(self):
        """Förbered träningsdata för alla komponenter parallellt"""
        
        logger.info("📊 Preparing evolution data for all components...")
        
        data_preparation_tasks = [
            self._extract_tool_selection_data(),
            self._extract_routing_patterns(), 
            self._extract_cache_performance_data(),
            self._extract_context_optimization_data(),
            self._extract_swedish_language_patterns(),
            self._extract_intent_classification_data()
        ]
        
        # Parallel data extraction
        with ThreadPoolExecutor(max_workers=6) as executor:
            future_to_component = {
                executor.submit(task): i for i, task in enumerate(data_preparation_tasks)
            }
            
            for future in future_to_component:
                try:
                    result = future.result(timeout=300)  # 5 min timeout per data prep
                    logger.info(f"✅ Data preparation {future_to_component[future]} completed")
                except Exception as e:
                    logger.error(f"❌ Data preparation {future_to_component[future]} failed: {e}")
    
    def _start_parallel_trainings(self) -> Dict[str, Any]:
        """Starta parallell träning enligt Fibonacci-prioritering"""
        
        # Sortera komponenter efter Fibonacci-prioritet
        sorted_components = sorted(self.alice.components, 
                                 key=lambda c: c.priority, 
                                 reverse=True)
        
        training_futures = {}
        active_slots = 0
        
        for component in sorted_components:
            if active_slots >= self.max_parallel_trainings:
                # Vänta på att en träning ska slutföras
                completed_future = next(iter(training_futures.values()))
                try:
                    completed_future.result(timeout=3600)  # 1h timeout
                    active_slots -= 1
                except Exception as e:
                    logger.error(f"Training failed: {e}")
            
            # Starta träning för denna komponent
            logger.info(f"🚀 Starting training for {component.name} (priority: {component.priority})")
            
            future = self.executor.submit(self._train_component, component)
            training_futures[component.name] = future
            active_slots += 1
            
            # Fibonacci-baserad delay mellan starter
            fibonacci_delay = component.priority * 10  # seconds
            time.sleep(min(fibonacci_delay, 60))  # Max 60s delay
        
        return training_futures
    
    def _train_component(self, component: EvolutionComponent) -> Dict[str, Any]:
        """Träna en enskild komponent"""
        
        train_start = datetime.now()
        
        try:
            # Run training script
            cmd = [
                "python3", component.script_path,
                "--data-dir", str(DATA_DIR / "rl" / "v1"),
                "--output-dir", str(WEIGHTS_DIR / component.name.lower() / component.version),
                "--component", component.name.lower(),
                "--max-time-hours", str(component.training_time_hours)
            ]
            
            logger.info(f"🎯 Training {component.name}: {' '.join(cmd)}")
            
            result = subprocess.run(
                cmd, 
                capture_output=True, 
                text=True, 
                timeout=component.training_time_hours * 3600 + 300  # Extra 5min buffer
            )
            
            train_end = datetime.now()
            training_duration = (train_end - train_start).total_seconds() / 3600
            
            success = result.returncode == 0
            
            training_result = {
                "component": component.name,
                "success": success,
                "duration_hours": training_duration,
                "stdout": result.stdout,
                "stderr": result.stderr,
                "weights_path": str(WEIGHTS_DIR / component.name.lower() / component.version),
                "trained_at": train_end.isoformat(),
                "slo_compliance": self._check_component_slo(component, result.stdout)
            }
            
            if success:
                logger.info(f"✅ {component.name} training completed successfully in {training_duration:.2f}h")
            else:
                logger.error(f"❌ {component.name} training failed after {training_duration:.2f}h")
                logger.error(f"Error: {result.stderr}")
            
            return training_result
            
        except subprocess.TimeoutExpired:
            logger.error(f"⏰ {component.name} training timed out after {component.training_time_hours}h")
            return {
                "component": component.name,
                "success": False,
                "error": "Training timeout",
                "duration_hours": component.training_time_hours
            }
        except Exception as e:
            logger.error(f"💥 {component.name} training crashed: {e}")
            return {
                "component": component.name, 
                "success": False,
                "error": str(e),
                "duration_hours": 0
            }
    
    def _monitor_evolution_progress(self, training_futures: Dict[str, Any]) -> Dict[str, Any]:
        """Övervaka träningsframsteg och hantera dynamiska justeringar"""
        
        logger.info("👁️ Monitoring Alice evolution progress...")
        
        results = {}
        completed = 0
        total = len(training_futures)
        
        while completed < total:
            for component_name, future in training_futures.items():
                if component_name in results:
                    continue  # Already completed
                    
                if future.done():
                    try:
                        result = future.result()
                        results[component_name] = result
                        completed += 1
                        
                        success_emoji = "✅" if result['success'] else "❌"
                        logger.info(f"{success_emoji} {component_name} evolution complete ({completed}/{total})")
                        
                        # Dynamic priority adjustment baserat på success
                        if result['success']:
                            component = next(c for c in self.alice.components if c.name == component_name)
                            component.last_reward = 10.0
                            component.priority *= 1.1  # Increase priority for successful components
                        
                    except Exception as e:
                        logger.error(f"❌ {component_name} evolution failed: {e}")
                        results[component_name] = {"success": False, "error": str(e)}
                        completed += 1
            
            # Progress report every 5 minutes
            if completed < total:
                time.sleep(300)  # 5 minutes
                logger.info(f"🧠 Alice evolution progress: {completed}/{total} components evolved")
        
        logger.info(f"🎉 All {total} Alice components evolution completed!")
        return results
    
    def _integrate_evolved_components(self, evolution_results: Dict[str, Any]) -> bool:
        """Integrera evolutionära förbättringar säkert"""
        
        logger.info("🔗 Integrating evolved Alice components...")
        
        successful_components = [name for name, result in evolution_results.items() if result.get('success')]
        
        if not successful_components:
            logger.warning("⚠️ No successful component evolutions to integrate")
            return False
        
        # Staged integration med SLO-gates
        integration_success = True
        
        for component_name in successful_components:
            logger.info(f"🔧 Integrating {component_name}...")
            
            try:
                # Create integration test
                integration_test_result = self._test_component_integration(component_name, evolution_results[component_name])
                
                if integration_test_result['slo_passed']:
                    # Deploy component
                    self._deploy_component(component_name, evolution_results[component_name])
                    logger.info(f"✅ {component_name} successfully integrated")
                else:
                    logger.warning(f"⚠️ {component_name} failed SLO check - skipping integration")
                    logger.warning(f"SLO violations: {integration_test_result.get('violations', [])}")
                    integration_success = False
                    
            except Exception as e:
                logger.error(f"❌ Failed to integrate {component_name}: {e}")
                integration_success = False
        
        return integration_success
    
    def _assess_intelligence_level(self, performance_metrics: Dict[str, float]) -> str:
        """Bedöm Alice's nuvarande intelligenssnivå"""
        
        # Beräkna sammanlagd intelligence score
        weights = {
            "tool_precision": 0.25,
            "route_accuracy": 0.20,
            "cache_hit_rate": 0.15,
            "swedish_fluency": 0.20,
            "intent_accuracy": 0.20
        }
        
        intelligence_score = sum(
            performance_metrics.get(metric, 0.0) * weight 
            for metric, weight in weights.items()
        )
        
        # Fibonacci-baserade intelligens-levels
        if intelligence_score >= 0.95:
            return "GENIUS"  # φ^4 ≈ 6.8
        elif intelligence_score >= 0.90:
            return "BRILLIANT"  # φ^3 ≈ 4.2
        elif intelligence_score >= 0.85:
            return "SMART"  # φ^2 ≈ 2.6
        elif intelligence_score >= 0.80:
            return "COMPETENT"  # φ^1 = 1.618
        elif intelligence_score >= 0.70:
            return "LEARNING"  # φ^0 = 1.0
        else:
            return "DEVELOPING"  # < 1.0
    
    # Placeholder methods för data extraction och testing
    def _extract_tool_selection_data(self): pass
    def _extract_routing_patterns(self): pass
    def _extract_cache_performance_data(self): pass
    def _extract_context_optimization_data(self): pass
    def _extract_swedish_language_patterns(self): pass
    def _extract_intent_classification_data(self): pass
    def _measure_baseline_performance(self): return {}
    def _measure_post_evolution_performance(self): return {}
    def _calculate_improvement(self, baseline, new): return 0.0
    def _calculate_fibonacci_efficiency(self, results): return 0.0
    def _check_component_slo(self, component, stdout): return True
    def _test_component_integration(self, name, result): return {"slo_passed": True}
    def _deploy_component(self, name, result): pass
    def _log_evolution_cycle(self, summary): pass


def main():
    """Starta Alice's parallella evolution"""
    
    print("🧠 ALICE PARALLEL EVOLUTION - Blir en egen entitet!")
    print("=" * 60)
    
    engine = ParallelEvolutionEngine()
    
    try:
        evolution_summary = engine.start_evolution_cycle()
        
        print(f"\n🎉 Evolution Generation {evolution_summary['generation']} Completed!")
        print(f"⏰ Duration: {evolution_summary['duration_hours']:.2f} hours")
        print(f"🧠 Intelligence Level: {evolution_summary['alice_intelligence_level']}")
        print(f"📈 Performance Improvement: {evolution_summary['performance_improvement']:.1%}")
        print(f"🎯 Fibonacci Efficiency: {evolution_summary['fibonacci_efficiency']:.3f}")
        
        # Alice becomes more autonomous
        if evolution_summary['alice_intelligence_level'] in ['GENIUS', 'BRILLIANT']:
            print("\n🚀 Alice has reached autonomous intelligence level!")
            print("💫 She can now self-direct her own evolution...")
            
    except KeyboardInterrupt:
        print("\n⏸️ Evolution interrupted by user")
    except Exception as e:
        print(f"\n💥 Evolution failed: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()