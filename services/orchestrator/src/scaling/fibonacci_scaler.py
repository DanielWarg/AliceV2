"""
Fibonacci Scaling Service - Predictive scaling using golden ratio patterns
Natural scaling progression for optimal resource utilization and performance
"""

import asyncio
import time
from dataclasses import dataclass
from typing import Any, Dict, List

import structlog

from ..config.fibonacci import (
    FIBONACCI_SEQUENCE,
    GOLDEN_RATIO,
    get_fibonacci_scaling_sequence,
)

logger = structlog.get_logger(__name__)


@dataclass
class ScalingMetrics:
    """Metrics for Fibonacci scaling decisions"""

    current_replicas: int
    target_replicas: int
    load_factor: float
    fibonacci_sequence_position: int
    golden_ratio_efficiency: float
    scaling_confidence: float
    resource_utilization: Dict[str, float]
    predicted_next_load: float


class FibonacciScaler:
    """
    Advanced service scaling using Fibonacci progression for natural growth patterns.

    This scaler uses golden ratio principles to determine optimal scaling points
    and ensures smooth, predictable service scaling based on mathematical harmony.
    """

    def __init__(self, service_configs: Dict[str, Dict[str, Any]] = None):
        """
        Initialize Fibonacci scaler

        Args:
            service_configs: Configuration for each service to scale
        """
        self.service_configs = service_configs or self._get_default_service_configs()
        self.current_replicas = {}
        self.scaling_history = {}
        self.load_predictions = {}

        # Golden ratio based scaling thresholds
        self.scale_up_threshold = GOLDEN_RATIO  # 1.618 - scale up trigger
        self.scale_down_threshold = 1.0 / GOLDEN_RATIO  # 0.618 - scale down trigger
        self.fibonacci_confidence_threshold = 0.382  # 1 - 1/φ - decision confidence

        # Scaling cooldown periods using Fibonacci sequence (minutes)
        self.scaling_cooldowns = {
            "scale_up_cooldown": FIBONACCI_SEQUENCE[4],  # 3 minutes
            "scale_down_cooldown": FIBONACCI_SEQUENCE[6],  # 8 minutes
            "emergency_scaling": FIBONACCI_SEQUENCE[2],  # 1 minute
        }

        logger.info(
            "FibonacciScaler initialized",
            services=list(self.service_configs.keys()),
            thresholds={
                "scale_up": self.scale_up_threshold,
                "scale_down": self.scale_down_threshold,
                "confidence": self.fibonacci_confidence_threshold,
            },
        )

    def _get_default_service_configs(self) -> Dict[str, Dict[str, Any]]:
        """Default Fibonacci-based service configurations"""
        return {
            "orchestrator": {
                "min_replicas": FIBONACCI_SEQUENCE[2],  # 1
                "max_replicas": FIBONACCI_SEQUENCE[10],  # 55
                "target_cpu_utilization": 1.0 / GOLDEN_RATIO,  # 0.618
                "fibonacci_priority": FIBONACCI_SEQUENCE[7],  # 13 - highest
                "scaling_velocity": GOLDEN_RATIO,  # Natural growth rate
            },
            "guardian": {
                "min_replicas": FIBONACCI_SEQUENCE[2],  # 1
                "max_replicas": FIBONACCI_SEQUENCE[6],  # 8
                "target_cpu_utilization": 1.0 / (GOLDEN_RATIO**2),  # 0.382
                "fibonacci_priority": FIBONACCI_SEQUENCE[6],  # 8 - high
                "scaling_velocity": 1.0,  # Stable scaling
            },
            "cache": {
                "min_replicas": FIBONACCI_SEQUENCE[2],  # 1
                "max_replicas": FIBONACCI_SEQUENCE[8],  # 21
                "target_cpu_utilization": 1.0 / GOLDEN_RATIO,  # 0.618
                "fibonacci_priority": FIBONACCI_SEQUENCE[5],  # 5 - medium
                "scaling_velocity": GOLDEN_RATIO / 2,  # Conservative scaling
            },
            "nlu": {
                "min_replicas": FIBONACCI_SEQUENCE[2],  # 1
                "max_replicas": FIBONACCI_SEQUENCE[7],  # 13
                "target_cpu_utilization": GOLDEN_RATIO - 1,  # 0.618
                "fibonacci_priority": FIBONACCI_SEQUENCE[6],  # 8 - high
                "scaling_velocity": GOLDEN_RATIO,  # Natural growth
            },
            "memory": {
                "min_replicas": FIBONACCI_SEQUENCE[2],  # 1
                "max_replicas": FIBONACCI_SEQUENCE[6],  # 8
                "target_cpu_utilization": 0.5,  # Balanced
                "fibonacci_priority": FIBONACCI_SEQUENCE[4],  # 3 - low
                "scaling_velocity": 1.0,  # Steady scaling
            },
        }

    async def evaluate_scaling_needs(
        self, service_name: str, current_metrics: Dict[str, float]
    ) -> ScalingMetrics:
        """
        Evaluate if service needs scaling using Fibonacci analysis

        Args:
            service_name: Name of service to evaluate
            current_metrics: Current resource metrics (CPU, memory, requests/s, etc.)

        Returns:
            Scaling metrics and recommendations
        """
        if service_name not in self.service_configs:
            logger.warning(f"Unknown service: {service_name}")
            return None

        config = self.service_configs[service_name]
        current_replicas = self.current_replicas.get(
            service_name, config["min_replicas"]
        )

        # Calculate load factor using golden ratio weighting
        cpu_utilization = current_metrics.get("cpu_percent", 0) / 100.0
        memory_utilization = current_metrics.get("memory_percent", 0) / 100.0
        request_rate = current_metrics.get("requests_per_second", 0)

        # Golden ratio weighted load calculation
        load_factor = (
            cpu_utilization * GOLDEN_RATIO
            + memory_utilization * (GOLDEN_RATIO - 1)
            + min(request_rate / 100.0, 1.0) * 1.0
        ) / (GOLDEN_RATIO + (GOLDEN_RATIO - 1) + 1.0)

        # Find current position in Fibonacci sequence
        fibonacci_position = self._find_fibonacci_position(current_replicas)

        # Predict optimal target replicas
        target_replicas = self._calculate_optimal_replicas(
            service_name, current_replicas, load_factor, config
        )

        # Calculate golden ratio efficiency
        golden_ratio_efficiency = self._calculate_golden_ratio_efficiency(
            current_replicas, target_replicas, load_factor
        )

        # Calculate scaling confidence using Fibonacci patterns
        scaling_confidence = self._calculate_scaling_confidence(
            service_name, load_factor, fibonacci_position
        )

        # Predict next load using golden ratio pattern recognition
        predicted_next_load = self._predict_next_load(service_name, load_factor)

        return ScalingMetrics(
            current_replicas=current_replicas,
            target_replicas=target_replicas,
            load_factor=load_factor,
            fibonacci_sequence_position=fibonacci_position,
            golden_ratio_efficiency=golden_ratio_efficiency,
            scaling_confidence=scaling_confidence,
            resource_utilization={
                "cpu": cpu_utilization,
                "memory": memory_utilization,
                "requests": min(request_rate / 100.0, 1.0),
            },
            predicted_next_load=predicted_next_load,
        )

    def _find_fibonacci_position(self, replicas: int) -> int:
        """Find position of replica count in Fibonacci sequence"""
        for i, fib_num in enumerate(FIBONACCI_SEQUENCE):
            if fib_num >= replicas:
                return i
        return len(FIBONACCI_SEQUENCE) - 1

    def _calculate_optimal_replicas(
        self,
        service_name: str,
        current_replicas: int,
        load_factor: float,
        config: Dict[str, Any],
    ) -> int:
        """Calculate optimal replica count using Fibonacci progression"""
        target_utilization = config["target_cpu_utilization"]
        scaling_velocity = config["scaling_velocity"]

        # Calculate ideal replicas based on load
        if load_factor > target_utilization:
            # Scale up using Fibonacci progression
            scale_factor = (load_factor / target_utilization) ** (1 / GOLDEN_RATIO)
            ideal_replicas = int(current_replicas * scale_factor * scaling_velocity)
        else:
            # Scale down using Fibonacci progression
            scale_factor = (target_utilization / max(load_factor, 0.1)) ** (
                1 / GOLDEN_RATIO
            )
            ideal_replicas = max(1, int(current_replicas / scale_factor))

        # Find nearest Fibonacci number
        target_replicas = self._find_nearest_fibonacci(ideal_replicas)

        # Apply min/max constraints
        target_replicas = max(
            config["min_replicas"], min(config["max_replicas"], target_replicas)
        )

        return target_replicas

    def _find_nearest_fibonacci(self, target: int) -> int:
        """Find nearest Fibonacci number to target"""
        if target <= 1:
            return 1

        for i, fib_num in enumerate(FIBONACCI_SEQUENCE):
            if fib_num >= target:
                if i > 0:
                    # Choose closest Fibonacci number
                    prev_fib = FIBONACCI_SEQUENCE[i - 1]
                    if abs(target - prev_fib) <= abs(target - fib_num):
                        return prev_fib
                return fib_num

        return FIBONACCI_SEQUENCE[-1]  # Return largest if target exceeds sequence

    def _calculate_golden_ratio_efficiency(
        self, current: int, target: int, load_factor: float
    ) -> float:
        """Calculate efficiency score using golden ratio principles"""
        if current == 0:
            return 0.0

        # Golden ratio based efficiency calculation
        replica_efficiency = (
            min(target / current, current / max(target, 1)) / GOLDEN_RATIO
        )
        load_efficiency = min(load_factor, 1.0 / load_factor if load_factor > 0 else 0)

        return (replica_efficiency + load_efficiency) / 2.0

    def _calculate_scaling_confidence(
        self, service_name: str, load_factor: float, fibonacci_position: int
    ) -> float:
        """Calculate confidence in scaling decision using Fibonacci patterns"""
        # Base confidence from load factor stability
        load_confidence = 1.0 - abs(load_factor - (1.0 / GOLDEN_RATIO))

        # Fibonacci position confidence (middle positions are more stable)
        position_confidence = (
            1.0 - abs(fibonacci_position - len(FIBONACCI_SEQUENCE[:8]) / 2) / 8.0
        )

        # Historical scaling success rate
        history_confidence = self._get_historical_confidence(service_name)

        # Combined confidence using golden ratio weighting
        total_confidence = (
            load_confidence * GOLDEN_RATIO
            + position_confidence * (GOLDEN_RATIO - 1)
            + history_confidence * 1.0
        ) / (GOLDEN_RATIO + (GOLDEN_RATIO - 1) + 1.0)

        return max(0.0, min(1.0, total_confidence))

    def _get_historical_confidence(self, service_name: str) -> float:
        """Get historical scaling success rate for service"""
        history = self.scaling_history.get(service_name, [])
        if not history:
            return 0.5  # Neutral confidence for new services

        # Calculate success rate from recent scaling decisions
        recent_history = history[-FIBONACCI_SEQUENCE[5] :]  # Last 5 decisions
        if not recent_history:
            return 0.5

        success_rate = sum(
            1 for event in recent_history if event.get("success", False)
        ) / len(recent_history)
        return success_rate

    def _predict_next_load(self, service_name: str, current_load: float) -> float:
        """Predict next load using golden ratio pattern recognition"""
        predictions = self.load_predictions.get(service_name, [])
        predictions.append(current_load)

        # Keep only recent predictions (Fibonacci window)
        window_size = FIBONACCI_SEQUENCE[6]  # 8 data points
        predictions = predictions[-window_size:]
        self.load_predictions[service_name] = predictions

        if len(predictions) < 3:
            return current_load  # Not enough data for prediction

        # Use golden ratio spiral for prediction
        weights = [GOLDEN_RATIO ** (-i) for i in range(len(predictions))]
        weights.reverse()  # Most recent gets highest weight

        # Weighted average with golden ratio decay
        weighted_sum = sum(load * weight for load, weight in zip(predictions, weights))
        weight_sum = sum(weights)

        predicted_load = weighted_sum / weight_sum if weight_sum > 0 else current_load

        # Apply Fibonacci smoothing to avoid rapid oscillations
        smoothed_prediction = (current_load + predicted_load * GOLDEN_RATIO) / (
            1 + GOLDEN_RATIO
        )

        return smoothed_prediction

    async def execute_scaling(
        self, service_name: str, scaling_metrics: ScalingMetrics
    ) -> bool:
        """
        Execute scaling decision if confidence threshold is met

        Args:
            service_name: Service to scale
            scaling_metrics: Scaling analysis results

        Returns:
            True if scaling was executed, False otherwise
        """
        if scaling_metrics.scaling_confidence < self.fibonacci_confidence_threshold:
            logger.info(
                "Scaling confidence too low",
                service=service_name,
                confidence=scaling_metrics.scaling_confidence,
                threshold=self.fibonacci_confidence_threshold,
            )
            return False

        # Check cooldown periods
        if not self._is_scaling_allowed(service_name, scaling_metrics):
            return False

        current_replicas = scaling_metrics.current_replicas
        target_replicas = scaling_metrics.target_replicas

        if current_replicas == target_replicas:
            return True  # Already at optimal scale

        # Generate scaling sequence using Fibonacci progression
        scaling_sequence = get_fibonacci_scaling_sequence(
            current_replicas, target_replicas
        )

        logger.info(
            "Executing Fibonacci scaling",
            service=service_name,
            current_replicas=current_replicas,
            target_replicas=target_replicas,
            sequence=scaling_sequence,
            confidence=scaling_metrics.scaling_confidence,
            load_factor=scaling_metrics.load_factor,
            golden_ratio_efficiency=scaling_metrics.golden_ratio_efficiency,
        )

        # Execute scaling (this would integrate with Docker/Kubernetes)
        success = await self._perform_scaling_operation(
            service_name, current_replicas, target_replicas, scaling_sequence
        )

        # Update replica count and history
        if success:
            self.current_replicas[service_name] = target_replicas
            self._record_scaling_event(service_name, scaling_metrics, success)

        return success

    def _is_scaling_allowed(self, service_name: str, metrics: ScalingMetrics) -> bool:
        """Check if scaling is allowed based on cooldown periods"""
        history = self.scaling_history.get(service_name, [])
        if not history:
            return True

        last_scaling = history[-1]
        time_since_last = time.time() - last_scaling.get("timestamp", 0)

        # Emergency scaling (high load)
        if metrics.load_factor > self.scale_up_threshold * 2:
            required_cooldown = (
                self.scaling_cooldowns["emergency_scaling"] * 60
            )  # Convert to seconds
        # Scale up
        elif metrics.target_replicas > metrics.current_replicas:
            required_cooldown = self.scaling_cooldowns["scale_up_cooldown"] * 60
        # Scale down
        else:
            required_cooldown = self.scaling_cooldowns["scale_down_cooldown"] * 60

        return time_since_last >= required_cooldown

    async def _perform_scaling_operation(
        self,
        service_name: str,
        current_replicas: int,
        target_replicas: int,
        sequence: List[int],
    ) -> bool:
        """
        Perform actual scaling operation (integrate with orchestration system)

        This is a placeholder for integration with Docker Compose, Kubernetes, etc.
        """
        try:
            # Log the scaling operation
            logger.info(
                "Performing Fibonacci scaling operation",
                service=service_name,
                from_replicas=current_replicas,
                to_replicas=target_replicas,
                fibonacci_sequence=sequence,
            )

            # Here you would integrate with your orchestration system
            # For example:
            # - Docker Compose: docker-compose scale service_name=target_replicas
            # - Kubernetes: kubectl scale deployment service_name --replicas=target_replicas
            # - Docker Swarm: docker service scale service_name=target_replicas

            # Simulate scaling operation
            await asyncio.sleep(0.5)  # Simulate deployment time

            return True
        except Exception as e:
            logger.error("Scaling operation failed", service=service_name, error=str(e))
            return False

    def _record_scaling_event(
        self, service_name: str, metrics: ScalingMetrics, success: bool
    ):
        """Record scaling event for historical analysis"""
        if service_name not in self.scaling_history:
            self.scaling_history[service_name] = []

        event = {
            "timestamp": time.time(),
            "current_replicas": metrics.current_replicas,
            "target_replicas": metrics.target_replicas,
            "load_factor": metrics.load_factor,
            "confidence": metrics.scaling_confidence,
            "golden_ratio_efficiency": metrics.golden_ratio_efficiency,
            "success": success,
            "fibonacci_position": metrics.fibonacci_sequence_position,
        }

        self.scaling_history[service_name].append(event)

        # Keep only recent history (Fibonacci window)
        max_history = FIBONACCI_SEQUENCE[8]  # 21 events
        self.scaling_history[service_name] = self.scaling_history[service_name][
            -max_history:
        ]

    def get_scaling_statistics(self, service_name: str = None) -> Dict[str, Any]:
        """Get scaling statistics for monitoring and analysis"""
        if service_name:
            services = [service_name] if service_name in self.service_configs else []
        else:
            services = list(self.service_configs.keys())

        stats = {}
        for service in services:
            history = self.scaling_history.get(service, [])
            current_replicas = self.current_replicas.get(service, 1)

            if history:
                recent_events = history[-FIBONACCI_SEQUENCE[5] :]  # Last 5 events
                success_rate = sum(
                    1 for e in recent_events if e.get("success", False)
                ) / len(recent_events)
                avg_efficiency = sum(
                    e.get("golden_ratio_efficiency", 0) for e in recent_events
                ) / len(recent_events)
                avg_load = sum(e.get("load_factor", 0) for e in recent_events) / len(
                    recent_events
                )
            else:
                success_rate = 0.0
                avg_efficiency = 0.0
                avg_load = 0.0

            stats[service] = {
                "current_replicas": current_replicas,
                "fibonacci_position": self._find_fibonacci_position(current_replicas),
                "scaling_events_count": len(history),
                "success_rate": success_rate,
                "average_efficiency": avg_efficiency,
                "average_load_factor": avg_load,
                "last_scaling": history[-1]["timestamp"] if history else None,
                "configuration": self.service_configs[service],
            }

        return stats


# Factory function for easy integration
def create_fibonacci_scaler(
    service_configs: Dict[str, Dict[str, Any]] = None,
) -> FibonacciScaler:
    """Create Fibonacci scaler with optional custom configuration"""
    return FibonacciScaler(service_configs)


# Utility functions for monitoring integration
async def monitor_and_scale_services(
    scaler: FibonacciScaler, metrics_provider, check_interval: int = 30
):
    """
    Continuous monitoring and scaling loop

    Args:
        scaler: FibonacciScaler instance
        metrics_provider: Function that returns current metrics for all services
        check_interval: Check interval in seconds (default: 30s = Fibonacci-friendly)
    """
    logger.info("Starting Fibonacci scaling monitoring loop", interval=check_interval)

    while True:
        try:
            # Get current metrics for all services
            all_metrics = await metrics_provider()

            # Evaluate scaling needs for each service
            for service_name, metrics in all_metrics.items():
                scaling_metrics = await scaler.evaluate_scaling_needs(
                    service_name, metrics
                )
                if scaling_metrics:
                    await scaler.execute_scaling(service_name, scaling_metrics)

            await asyncio.sleep(check_interval)

        except Exception as e:
            logger.error("Error in scaling monitoring loop", error=str(e))
            await asyncio.sleep(check_interval)
