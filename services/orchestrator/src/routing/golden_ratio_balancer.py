"""
Fibonacci AI Architecture - Golden Ratio Load Balancer
Natural traffic distribution using phi (φ = 1.618033988749) and Fibonacci progressions
"""

import time
from collections import deque
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

import structlog

from ..config.fibonacci import (
    FIBONACCI_SEQUENCE,
    GOLDEN_RATIO,
    calculate_golden_ratio_threshold,
)

logger = structlog.get_logger(__name__)


@dataclass
class ServiceMetrics:
    """Real-time service performance metrics"""

    name: str
    current_load: float = 0.0  # 0.0 to 1.0
    response_time_ms: float = 0.0
    error_rate: float = 0.0
    requests_per_second: float = 0.0
    health_score: float = 1.0  # 1.0 = perfect health
    capacity: int = 1  # Number of replicas/instances
    last_updated: float = field(default_factory=time.time)

    # Fibonacci optimization fields
    fibonacci_weight: int = 1
    golden_ratio_adjustment: float = 1.0
    natural_priority: float = 1.0


@dataclass
class LoadBalancingDecision:
    """Golden ratio optimized load balancing decision"""

    selected_service: str
    confidence: float  # 0.0 to 1.0
    load_distribution: Dict[str, float]  # Service -> load percentage
    fibonacci_weights: Dict[str, int]
    golden_ratio_factors: Dict[str, float]
    reason: str
    predicted_response_time: float


class GoldenRatioLoadBalancer:
    """
    Load balancer using golden ratio and Fibonacci sequences for natural traffic distribution

    Principles:
    - Services are weighted using Fibonacci numbers (1,1,2,3,5,8,13...)
    - Load distribution follows golden ratio proportions (φ = 1.618...)
    - Healthy services get φ boost, unhealthy get φ reduction
    - Natural scaling follows Fibonacci progression
    """

    def __init__(self, services: List[str]):
        self.services = services
        self.metrics: Dict[str, ServiceMetrics] = {}
        self.request_history: deque = deque(
            maxlen=1000
        )  # Last 1000 requests for analysis
        self.golden_ratio_window = deque(maxlen=144)  # Fibonacci 12th number

        # Initialize service metrics with Fibonacci weights
        for i, service in enumerate(services):
            fib_index = min(i, len(FIBONACCI_SEQUENCE) - 1)
            self.metrics[service] = ServiceMetrics(
                name=service,
                fibonacci_weight=FIBONACCI_SEQUENCE[fib_index],
                natural_priority=self._calculate_natural_priority(i),
            )

        logger.info(
            "Golden Ratio Load Balancer initialized",
            services=services,
            fibonacci_weights={s: self.metrics[s].fibonacci_weight for s in services},
        )

    def _calculate_natural_priority(self, index: int) -> float:
        """Calculate natural priority using golden ratio"""
        return GOLDEN_RATIO ** (-index)  # Higher priority for lower indices

    async def update_service_metrics(
        self, service_name: str, metrics_data: Dict[str, Any]
    ) -> None:
        """Update metrics for a specific service with live data"""
        if service_name not in self.metrics:
            logger.warning("Unknown service", service=service_name)
            return

        service = self.metrics[service_name]

        # Update with live data
        service.current_load = min(1.0, metrics_data.get("cpu_percent", 0.0) / 100.0)
        service.response_time_ms = metrics_data.get(
            "avg_response_time_ms", service.response_time_ms
        )
        service.error_rate = metrics_data.get("error_rate", 0.0)
        service.requests_per_second = metrics_data.get("requests_per_second", 0.0)
        service.capacity = metrics_data.get("replicas", 1)
        service.last_updated = time.time()

        # Calculate health score using golden ratio thresholds
        health_factors = []

        # CPU load health (golden ratio thresholds)
        if service.current_load < calculate_golden_ratio_threshold(0.5):  # ~0.309
            health_factors.append(GOLDEN_RATIO)  # Excellent
        elif service.current_load < calculate_golden_ratio_threshold(1.0):  # ~0.618
            health_factors.append(1.0)  # Good
        else:
            health_factors.append(1.0 / GOLDEN_RATIO)  # Poor

        # Response time health
        if service.response_time_ms < 55:  # Fibonacci threshold
            health_factors.append(GOLDEN_RATIO)
        elif service.response_time_ms < 89:  # Next Fibonacci
            health_factors.append(1.0)
        else:
            health_factors.append(1.0 / GOLDEN_RATIO)

        # Error rate health
        if service.error_rate < 0.01:  # 1%
            health_factors.append(GOLDEN_RATIO)
        elif service.error_rate < 0.05:  # 5%
            health_factors.append(1.0)
        else:
            health_factors.append(1.0 / GOLDEN_RATIO)

        # Golden ratio geometric mean for overall health
        service.health_score = (
            health_factors[0] * health_factors[1] * health_factors[2]
        ) ** (1 / 3)

        # Apply golden ratio adjustment based on health
        if service.health_score > GOLDEN_RATIO - 0.5:  # ~1.118
            service.golden_ratio_adjustment = GOLDEN_RATIO
        elif service.health_score < 1.0 / GOLDEN_RATIO:  # ~0.618
            service.golden_ratio_adjustment = 1.0 / GOLDEN_RATIO
        else:
            service.golden_ratio_adjustment = 1.0

        logger.debug(
            "Service metrics updated",
            service=service_name,
            health_score=service.health_score,
            golden_ratio_adjustment=service.golden_ratio_adjustment,
            load=service.current_load,
            response_time=service.response_time_ms,
        )

    def select_service(
        self, request_context: Dict[str, Any] = None
    ) -> LoadBalancingDecision:
        """
        Select optimal service using golden ratio load balancing

        Algorithm:
        1. Calculate effective capacity = fibonacci_weight * capacity * health_score * golden_ratio_adjustment
        2. Distribute load using golden ratio proportions
        3. Select service with lowest current_load / effective_capacity ratio
        """
        if not self.metrics:
            raise ValueError("No services available")

        # Calculate effective capacity for each service
        service_capacities = {}
        total_effective_capacity = 0

        for name, service in self.metrics.items():
            effective_capacity = (
                service.fibonacci_weight
                * service.capacity
                * service.health_score
                * service.golden_ratio_adjustment
                * service.natural_priority
            )
            service_capacities[name] = effective_capacity
            total_effective_capacity += effective_capacity

        # Calculate golden ratio load distribution
        load_distribution = {}
        golden_ratio_factors = {}

        for name, capacity in service_capacities.items():
            if total_effective_capacity > 0:
                base_ratio = capacity / total_effective_capacity

                # Apply golden ratio optimization for healthy services
                service = self.metrics[name]
                if service.health_score > 1.0:
                    golden_factor = GOLDEN_RATIO
                elif service.health_score < 1.0 / GOLDEN_RATIO:
                    golden_factor = 1.0 / GOLDEN_RATIO
                else:
                    golden_factor = 1.0

                load_distribution[name] = base_ratio * golden_factor
                golden_ratio_factors[name] = golden_factor
            else:
                load_distribution[name] = 1.0 / len(self.metrics)
                golden_ratio_factors[name] = 1.0

        # Normalize load distribution
        total_distribution = sum(load_distribution.values())
        if total_distribution > 0:
            load_distribution = {
                k: v / total_distribution for k, v in load_distribution.items()
            }

        # Select service with lowest load ratio (current_load / target_load)
        best_service = None
        best_score = float("inf")

        for name, target_load in load_distribution.items():
            service = self.metrics[name]
            if target_load > 0:
                load_ratio = service.current_load / target_load

                # Golden ratio bonus for underutilized healthy services
                if (
                    load_ratio < calculate_golden_ratio_threshold(1.0)
                    and service.health_score > 1.0
                ):
                    load_ratio /= GOLDEN_RATIO

                if load_ratio < best_score:
                    best_score = load_ratio
                    best_service = name

        if best_service is None:
            # Fallback to first available service
            best_service = list(self.metrics.keys())[0]

        # Predict response time using Fibonacci sequence
        predicted_time = self._predict_response_time(best_service, request_context)

        # Generate reasoning
        service = self.metrics[best_service]
        reason = (
            f"Golden ratio selection: {service.fibonacci_weight}x weight, "
            f"{service.health_score:.2f} health, "
            f"{service.golden_ratio_adjustment:.2f}x φ-adjustment"
        )

        # Record decision in history
        decision_record = {
            "timestamp": time.time(),
            "service": best_service,
            "load_ratio": best_score,
            "health_score": service.health_score,
            "fibonacci_weight": service.fibonacci_weight,
        }
        self.request_history.append(decision_record)
        self.golden_ratio_window.append(service.golden_ratio_adjustment)

        logger.info(
            "Service selected",
            service=best_service,
            confidence=1.0 / (1.0 + best_score),
            predicted_time=predicted_time,
            reason=reason,
        )

        return LoadBalancingDecision(
            selected_service=best_service,
            confidence=min(1.0, 1.0 / (1.0 + best_score)),
            load_distribution=load_distribution,
            fibonacci_weights={
                s: self.metrics[s].fibonacci_weight for s in self.metrics
            },
            golden_ratio_factors=golden_ratio_factors,
            reason=reason,
            predicted_response_time=predicted_time,
        )

    def _predict_response_time(
        self, service_name: str, context: Dict[str, Any] = None
    ) -> float:
        """Predict response time using Fibonacci-based estimation"""
        service = self.metrics[service_name]

        # Base prediction on current metrics
        base_time = service.response_time_ms

        # Apply Fibonacci complexity scaling
        if context:
            text_length = context.get("text_length", 0)
            # Find appropriate Fibonacci number for text length
            for i, fib_num in enumerate(FIBONACCI_SEQUENCE):
                if text_length <= fib_num * 10:  # 10 chars per Fibonacci unit
                    complexity_factor = (
                        FIBONACCI_SEQUENCE[min(i, len(FIBONACCI_SEQUENCE) - 1)] / 10
                    )
                    break
            else:
                complexity_factor = FIBONACCI_SEQUENCE[-1] / 10

            base_time *= 1.0 + complexity_factor * 0.1

        # Apply load-based adjustment using golden ratio
        load_factor = 1.0 + (service.current_load * GOLDEN_RATIO - 1.0)
        predicted_time = base_time * load_factor

        return max(13, predicted_time)  # Minimum Fibonacci response time

    def get_load_balancer_stats(self) -> Dict[str, Any]:
        """Get comprehensive load balancer statistics"""

        # Calculate golden ratio window average
        golden_ratio_avg = (
            sum(self.golden_ratio_window) / len(self.golden_ratio_window)
            if self.golden_ratio_window
            else 1.0
        )

        # Recent request distribution
        recent_requests = list(self.request_history)[-100:]  # Last 100 requests
        service_counts = {}
        for req in recent_requests:
            service = req["service"]
            service_counts[service] = service_counts.get(service, 0) + 1

        total_requests = len(recent_requests)
        request_distribution = {
            s: (count / total_requests * 100) if total_requests > 0 else 0
            for s, count in service_counts.items()
        }

        return {
            "balancer_type": "golden_ratio_fibonacci",
            "services": len(self.metrics),
            "total_requests_tracked": len(self.request_history),
            "golden_ratio_window_avg": golden_ratio_avg,
            "recent_request_distribution": request_distribution,
            "service_details": {
                name: {
                    "fibonacci_weight": service.fibonacci_weight,
                    "current_load": service.current_load,
                    "health_score": service.health_score,
                    "golden_ratio_adjustment": service.golden_ratio_adjustment,
                    "natural_priority": service.natural_priority,
                    "response_time_ms": service.response_time_ms,
                    "capacity": service.capacity,
                    "last_updated_ago_seconds": time.time() - service.last_updated,
                }
                for name, service in self.metrics.items()
            },
            "fibonacci_sequence": FIBONACCI_SEQUENCE[: len(self.metrics)],
            "golden_ratio": GOLDEN_RATIO,
        }

    async def optimize_service_scaling(self) -> List[Dict[str, Any]]:
        """Suggest service scaling using Fibonacci progression"""
        scaling_recommendations = []

        for name, service in self.metrics.items():
            current_replicas = service.capacity

            # Determine if scaling is needed
            load_threshold_high = calculate_golden_ratio_threshold(1.0)  # ~0.618
            load_threshold_low = calculate_golden_ratio_threshold(0.5)  # ~0.309

            if (
                service.current_load > load_threshold_high
                and service.health_score < 1.0
            ):
                # Scale up using next Fibonacci number
                current_fib_index = (
                    FIBONACCI_SEQUENCE.index(current_replicas)
                    if current_replicas in FIBONACCI_SEQUENCE
                    else 0
                )
                next_fib_index = min(current_fib_index + 1, len(FIBONACCI_SEQUENCE) - 1)
                target_replicas = FIBONACCI_SEQUENCE[next_fib_index]

                scaling_recommendations.append(
                    {
                        "service": name,
                        "action": "scale_up",
                        "current_replicas": current_replicas,
                        "target_replicas": target_replicas,
                        "fibonacci_progression": True,
                        "reason": f"Load {service.current_load:.2f} > threshold {load_threshold_high:.2f}",
                        "confidence": service.current_load - load_threshold_high,
                    }
                )

            elif service.current_load < load_threshold_low and current_replicas > 1:
                # Scale down to previous Fibonacci number
                current_fib_index = (
                    FIBONACCI_SEQUENCE.index(current_replicas)
                    if current_replicas in FIBONACCI_SEQUENCE
                    else 1
                )
                prev_fib_index = max(current_fib_index - 1, 0)
                target_replicas = FIBONACCI_SEQUENCE[prev_fib_index]

                if target_replicas < current_replicas:
                    scaling_recommendations.append(
                        {
                            "service": name,
                            "action": "scale_down",
                            "current_replicas": current_replicas,
                            "target_replicas": target_replicas,
                            "fibonacci_progression": True,
                            "reason": f"Load {service.current_load:.2f} < threshold {load_threshold_low:.2f}",
                            "confidence": load_threshold_low - service.current_load,
                        }
                    )

        logger.info(
            "Scaling recommendations generated",
            recommendations=len(scaling_recommendations),
        )

        return scaling_recommendations


# Global load balancer instance
_golden_ratio_balancer: Optional[GoldenRatioLoadBalancer] = None


def create_golden_ratio_balancer(services: List[str]) -> GoldenRatioLoadBalancer:
    """Create or update global golden ratio load balancer"""
    global _golden_ratio_balancer
    _golden_ratio_balancer = GoldenRatioLoadBalancer(services)
    return _golden_ratio_balancer


def get_golden_ratio_balancer() -> Optional[GoldenRatioLoadBalancer]:
    """Get existing golden ratio load balancer"""
    return _golden_ratio_balancer
