#!/usr/bin/env python3
"""
🧮 Fibonacci Training Loop - Alice v2 Cache Optimization
Tränar Fibonacci spiral cache system med VERKLIG data patterns
"""

import asyncio
import json
import math
import random

# Import Fibonacci constants
import sys
import time
from datetime import datetime
from typing import Dict, List

import aiohttp
import structlog

sys.path.append("/Users/evil/Desktop/EVIL/PROJECT/alice-v2/services/orchestrator")
from src.config.fibonacci import FIBONACCI_SEQUENCE, GOLDEN_RATIO

logger = structlog.get_logger(__name__)


class FibonacciTrainingLoop:
    """
    Träningsloop för Fibonacci cache optimization med golden ratio learning
    """

    def __init__(
        self, orchestrator_url: str = "http://localhost:8001", fast_mode: bool = True
    ):
        self.orchestrator_url = orchestrator_url
        self.training_data = []
        self.performance_metrics = []
        self.golden_ratio = GOLDEN_RATIO
        self.fast_mode = fast_mode

        # Optimized training parameters - smaller batches för snabbare feedback
        if fast_mode:
            self.training_phases = {
                "rapid_warm_up": {
                    "queries": FIBONACCI_SEQUENCE[10],  # 55 queries - snabb test
                    "duration_minutes": 5,
                    "learning_rate": self.golden_ratio**-1,  # φ^-1 ≈ 0.618
                    "concurrent_requests": 3,  # Parallella requests
                },
                "pattern_boost": {
                    "queries": FIBONACCI_SEQUENCE[11],  # 89 queries
                    "duration_minutes": 10,
                    "learning_rate": 1.0 / self.golden_ratio,
                    "concurrent_requests": 5,
                },
                "optimization_sprint": {
                    "queries": FIBONACCI_SEQUENCE[12],  # 144 queries
                    "duration_minutes": 15,
                    "learning_rate": self.golden_ratio**-2,
                    "concurrent_requests": 8,
                },
            }
        else:
            # Original comprehensive training
            self.training_phases = {
                "warm_up": {
                    "queries": FIBONACCI_SEQUENCE[17],  # 1597 queries
                    "duration_hours": 1,
                    "learning_rate": self.golden_ratio**-2,
                    "concurrent_requests": 1,
                },
                "pattern_learning": {
                    "queries": FIBONACCI_SEQUENCE[16],  # 987 queries
                    "duration_hours": 3,
                    "learning_rate": self.golden_ratio**-1,
                    "concurrent_requests": 2,
                },
                "optimization": {
                    "queries": FIBONACCI_SEQUENCE[15],  # 610 queries
                    "duration_hours": 8,
                    "learning_rate": 1.0 / self.golden_ratio,
                    "concurrent_requests": 3,
                },
                "convergence": {
                    "queries": FIBONACCI_SEQUENCE[14],  # 377 queries
                    "duration_hours": 24,
                    "learning_rate": self.golden_ratio**-3,
                    "concurrent_requests": 1,
                },
            }

    def generate_fibonacci_training_queries(self) -> List[Dict]:
        """
        Genererar träningsqueries baserat på Fibonacci spiral patterns
        Optimerat för snabbare cache warming och pattern recognition
        """
        # Expanderad query set för bättre cache coverage
        base_queries = [
            # Mathematical queries - core Fibonacci patterns
            "Vad är Fibonacci tal?",
            "Beräkna golden ratio",
            "Förklara Fibonacci sekvens",
            "Vad är φ (phi)?",
            "1 1 2 3 5 8 13 21 förklaring",
            "Fibonacci spiral i naturen",
            "Golden ratio arkitektur",
            "Phi konstant matematik",
            # Semantic variations för spiral matching - KRITISKT för cache hits
            "Fibonacci numbers explanation",
            "Golden ratio calculation",
            "Fibonacci sequence svenska",
            "Phi mathematical constant",
            "What is Fibonacci sequence",
            "Calculate 1.618 golden ratio",
            "Fibonacci tal förklaring",
            "Golden section mathematics",
            # Svenska/English variations - dubbel cache coverage
            "Hjälp mig förstå Fibonacci",
            "Help me understand Fibonacci",
            "Beräkna 1.618 * 42",
            "Calculate 1.618 times 42",
            "Fibonacci i naturen exempel",
            "Fibonacci in nature examples",
            "Spiral pattern mathematics",
            "Spiral mönster matematik",
            # Complex reasoning - för ML pattern learning
            "Hur används golden ratio i design?",
            "How is golden ratio used in design?",
            "Fibonacci trading strategies",
            "Fibonacci handelsstrategi",
            "Mathematical beauty förklaring",
            "Mathematical beauty explanation",
            "Natural patterns matematik",
            "Natural patterns mathematics",
            # System optimization queries - för operational cache
            "Cache performance status",
            "System health check",
            "Response time optimization",
            "Memory usage analysis",
            "Fibonacci cache statistics",
            "Golden ratio load balancing",
            "Spiral matching performance",
            "φ optimization metrics",
            # Common Alice queries - för praktisk cache warming
            "Vad är klockan?",
            "What time is it?",
            "Hej Alice",
            "Hello Alice",
            "Hjälp mig",
            "Help me",
            "Tack",
            "Thank you",
            "Vad kan du göra?",
            "What can you do?",
            # Numerical variations - för mathematical patterns
            "1.618",
            "0.618",
            "Fibonacci 21",
            "Fibonacci 34",
            "Golden ratio 1.618033988749",
            "Phi värde",
            "Phi value",
        ]

        # Expandera med semantic variations
        expanded_queries = []
        for base in base_queries:
            # Original query
            expanded_queries.append(
                {
                    "message": base,
                    "intent": self._extract_intent(base),
                    "complexity": self._calculate_complexity(base),
                    "spiral_weight": self._calculate_spiral_weight(base),
                }
            )

            # Semantic variations
            variations = self._generate_semantic_variations(base)
            for var in variations:
                expanded_queries.append(
                    {
                        "message": var,
                        "intent": self._extract_intent(var),
                        "complexity": self._calculate_complexity(var),
                        "spiral_weight": self._calculate_spiral_weight(var),
                    }
                )

        return expanded_queries

    def _extract_intent(self, query: str) -> str:
        """Extract intent från query för cache key normalization"""
        query_lower = query.lower()

        if any(word in query_lower for word in ["fibonacci", "sekvens", "sequence"]):
            return "fibonacci_explanation"
        elif any(word in query_lower for word in ["golden", "ratio", "phi", "1.618"]):
            return "golden_ratio_math"
        elif any(word in query_lower for word in ["cache", "performance", "system"]):
            return "system_query"
        elif any(word in query_lower for word in ["beräkna", "calculate", "math"]):
            return "calculation"
        else:
            return "general_inquiry"

    def _calculate_complexity(self, query: str) -> float:
        """Beräkna query complexity för Fibonacci weighting"""
        factors = {
            "length": len(query.split()) / 10.0,
            "mathematical_terms": len(
                [
                    w
                    for w in query.lower().split()
                    if w in ["fibonacci", "ratio", "beräkna", "math"]
                ]
            )
            / 5.0,
            "question_complexity": query.count("?")
            + query.count("hur")
            + query.count("varför"),
        }

        base_complexity = sum(factors.values())
        # Apply golden ratio weighting
        return base_complexity * self.golden_ratio

    def _calculate_spiral_weight(self, query: str) -> float:
        """Beräkna spiral weight för semantic matching"""
        # Hash query to coordinates on Fibonacci spiral
        query_hash = hash(query.lower()) % 1000
        angle = query_hash * (2 * math.pi / (self.golden_ratio**2))

        # Fibonacci spiral radius
        radius = self.golden_ratio ** (angle / math.pi)

        return min(radius / 100.0, 1.0)  # Normalize to [0,1]

    def _generate_semantic_variations(self, base_query: str) -> List[str]:
        """Generera semantic variations för spiral pattern learning"""
        variations = []

        # Svenska/Engelska variations
        sv_en_map = {
            "vad är": "what is",
            "förklara": "explain",
            "beräkna": "calculate",
            "hjälp": "help",
            "exempel": "example",
        }

        for sv, en in sv_en_map.items():
            if sv in base_query.lower():
                variations.append(base_query.lower().replace(sv, en))

        # Synonym variations
        synonyms = {
            "fibonacci": ["fibonacci sequence", "fibonacci numbers", "fibonacci tal"],
            "golden ratio": ["phi", "1.618", "golden proportion"],
            "beräkna": ["räkna ut", "calculate", "compute"],
        }

        for original, syns in synonyms.items():
            if original.lower() in base_query.lower():
                for syn in syns:
                    variations.append(base_query.lower().replace(original.lower(), syn))

        return variations[:5]  # Limit variations

    async def execute_training_phase(self, phase_name: str, phase_config: Dict):
        """
        Kör en träningsfas med Fibonacci parameters
        """
        logger.info(
            f"Starting Fibonacci training phase: {phase_name}", config=phase_config
        )

        queries = self.generate_fibonacci_training_queries()
        phase_queries = phase_config["queries"]
        learning_rate = phase_config["learning_rate"]

        # Select queries baserat på Fibonacci distribution
        selected_queries = random.choices(queries, k=phase_queries)

        phase_metrics = {
            "phase": phase_name,
            "start_time": datetime.utcnow().isoformat(),
            "queries_planned": phase_queries,
            "learning_rate": learning_rate,
            "response_times": [],
            "cache_hits": 0,
            "cache_misses": 0,
            "errors": 0,
        }

        async with aiohttp.ClientSession() as session:
            for i, query_data in enumerate(selected_queries):
                try:
                    # Execute query
                    start_time = time.time()

                    async with session.post(
                        f"{self.orchestrator_url}/api/orchestrator/chat",
                        json={
                            "message": query_data["message"],
                            "session_id": f"fibonacci_training_{phase_name}_{i}",
                            "context": {
                                "training": True,
                                "phase": phase_name,
                                "intent": query_data["intent"],
                                "complexity": query_data["complexity"],
                                "spiral_weight": query_data["spiral_weight"],
                            },
                        },
                        timeout=aiohttp.ClientTimeout(total=30),
                    ) as response:
                        end_time = time.time()
                        response_time_ms = (end_time - start_time) * 1000

                        if response.status == 200:
                            result = await response.json()
                            phase_metrics["response_times"].append(response_time_ms)

                            # Check if cache hit
                            if result.get("metadata", {}).get("cache_hit"):
                                phase_metrics["cache_hits"] += 1
                            else:
                                phase_metrics["cache_misses"] += 1
                        else:
                            phase_metrics["errors"] += 1

                except Exception as e:
                    logger.error("Training query failed", error=str(e))
                    phase_metrics["errors"] += 1

                # Fibonacci-based sleep between queries
                if i % FIBONACCI_SEQUENCE[5] == 0:  # Every 5th query
                    await asyncio.sleep(learning_rate)  # φ-based delay

                # Enhanced progress logging med real-time metrics
                if i % 10 == 0 and i > 0:  # Mer frequent logging
                    avg_time = sum(phase_metrics["response_times"]) / len(
                        phase_metrics["response_times"]
                    )
                    hit_rate = (
                        phase_metrics["cache_hits"]
                        / (phase_metrics["cache_hits"] + phase_metrics["cache_misses"])
                        * 100
                        if (phase_metrics["cache_hits"] + phase_metrics["cache_misses"])
                        > 0
                        else 0
                    )
                    improvement = (417 - avg_time) / 417 * 100 if avg_time < 417 else 0

                    logger.info(
                        f"🧮 Training progress: {i}/{phase_queries}",
                        avg_response_ms=f"{avg_time:.1f}",
                        cache_hit_rate=f"{hit_rate:.1f}%",
                        improvement_vs_baseline=f"{improvement:.1f}%",
                        target_35_9ms_progress=(
                            f"{((417-avg_time)/(417-35.9)*100):.1f}%"
                            if avg_time < 417
                            else "0%"
                        ),
                    )

                    # Early success detection
                    if avg_time <= 35.9 and hit_rate >= 70:
                        logger.info(
                            "🎯 TARGET ACHIEVED EARLY! Fibonacci optimization successful!"
                        )
                        break

        # Calculate phase results
        phase_metrics["end_time"] = datetime.utcnow().isoformat()
        phase_metrics["avg_response_time"] = sum(phase_metrics["response_times"]) / len(
            phase_metrics["response_times"]
        )
        phase_metrics["cache_hit_rate"] = (
            phase_metrics["cache_hits"]
            / (phase_metrics["cache_hits"] + phase_metrics["cache_misses"])
            * 100
        )

        self.performance_metrics.append(phase_metrics)

        logger.info(
            f"Fibonacci training phase complete: {phase_name}", metrics=phase_metrics
        )

        return phase_metrics

    async def run_full_training_loop(self):
        """
        Kör complete Fibonacci training loop
        """
        logger.info(
            "🧮 Starting Fibonacci Training Loop",
            golden_ratio=self.golden_ratio,
            phases=list(self.training_phases.keys()),
        )

        start_time = datetime.utcnow()

        for phase_name, phase_config in self.training_phases.items():
            try:
                await self.execute_training_phase(phase_name, phase_config)

                # Save intermediate results
                self._save_training_progress()

                # Check för early convergence
                if self._check_convergence_criteria():
                    logger.info("🎯 Early convergence achieved! Stopping training.")
                    break

            except Exception as e:
                logger.error(f"Training phase failed: {phase_name}", error=str(e))
                continue

        # Final analysis
        final_metrics = self._analyze_training_results()

        end_time = datetime.utcnow()
        training_duration = (end_time - start_time).total_seconds()

        logger.info(
            "🚀 Fibonacci Training Loop Complete!",
            duration_seconds=training_duration,
            final_metrics=final_metrics,
        )

        return final_metrics

    def _check_convergence_criteria(self) -> bool:
        """Check if Fibonacci optimization targets är reached"""
        if len(self.performance_metrics) < 2:
            return False

        latest = self.performance_metrics[-1]

        # Target: 38.2% improvement (35.9ms from 58.125ms baseline)
        target_response_time = 35.9

        # Target: 70%+ cache hit rate
        target_cache_hit_rate = 70.0

        converged = (
            latest["avg_response_time"] <= target_response_time
            and latest["cache_hit_rate"] >= target_cache_hit_rate
        )

        return converged

    def _analyze_training_results(self) -> Dict:
        """Analyze complete training results"""
        if not self.performance_metrics:
            return {}

        initial = self.performance_metrics[0]
        final = self.performance_metrics[-1]

        improvement = {
            "response_time_improvement": (
                initial["avg_response_time"] - final["avg_response_time"]
            )
            / initial["avg_response_time"]
            * 100,
            "cache_hit_improvement": final["cache_hit_rate"]
            - initial["cache_hit_rate"],
            "error_rate": final["errors"] / final["queries_planned"] * 100,
            "fibonacci_convergence_achieved": self._check_convergence_criteria(),
        }

        return improvement

    def _save_training_progress(self):
        """Save training progress to file"""
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        filename = f"fibonacci_training_progress_{timestamp}.json"

        with open(filename, "w") as f:
            json.dump(
                {
                    "golden_ratio": self.golden_ratio,
                    "training_phases": self.training_phases,
                    "performance_metrics": self.performance_metrics,
                },
                f,
                indent=2,
            )


async def main():
    """Main training loop execution"""
    trainer = FibonacciTrainingLoop()
    results = await trainer.run_full_training_loop()
    print("🧮 Fibonacci Training Complete:", results)


if __name__ == "__main__":
    asyncio.run(main())
