"""
Fibonacci AI Architecture - Routing Module
Golden ratio load balancing and natural traffic distribution
"""

from .golden_ratio_balancer import (
    GoldenRatioLoadBalancer,
    LoadBalancingDecision,
    ServiceMetrics,
    create_golden_ratio_balancer,
    get_golden_ratio_balancer,
)

__all__ = [
    "GoldenRatioLoadBalancer",
    "create_golden_ratio_balancer",
    "get_golden_ratio_balancer",
    "ServiceMetrics",
    "LoadBalancingDecision",
]
