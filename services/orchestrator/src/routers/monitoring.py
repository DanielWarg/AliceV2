"""
Monitoring endpoints for Alice system performance.
Shows cache stats, quota tracking, circuit breakers, and overall health.
"""

import os
import time
from typing import Any, Dict

import structlog
from fastapi import APIRouter

from ..cache.smart_cache import get_smart_cache
from ..clients.nlu_client import get_nlu_client
from ..utils.circuit_breaker import get_all_circuit_stats
from ..utils.quota_tracker import get_all_quota_stats

logger = structlog.get_logger(__name__)
router = APIRouter()


@router.get("/api/monitoring/health")
async def system_health():
    """Comprehensive system health check"""

    start_time = time.time()

    # Component health checks
    cache = get_smart_cache()
    nlu_client = get_nlu_client()

    health_status = {
        "overall_status": "healthy",
        "timestamp": time.time(),
        "version": "2.0-optimized",
        "uptime_seconds": time.time() - start_time,
        # Component statuses
        "components": {
            "redis_cache": "healthy" if cache.redis_client else "unhealthy",
            "nlu_service": "unknown",  # Will be updated below
            "ollama_host": "unknown",  # Will be updated below
        },
        # Configuration
        "config": {
            "micro_model": os.getenv("MICRO_MODEL", "qwen2.5:3b"),
            "planner_model": os.getenv("LLM_PLANNER", "qwen2.5:3b-instruct-q4_K_M"),
            "micro_max_share": float(os.getenv("MICRO_MAX_SHARE", "0.2")),
            "planner_timeout_ms": int(os.getenv("PLANNER_TIMEOUT_MS", "3000")),
            "cache_enabled": os.getenv("CACHE_ENABLED", "1") == "1",
        },
    }

    # Check NLU service
    try:
        nlu_health = await nlu_client.health_check()
        health_status["components"]["nlu_service"] = nlu_health["status"]
        health_status["nlu_details"] = nlu_health
    except Exception as e:
        health_status["components"]["nlu_service"] = "error"
        health_status["nlu_error"] = str(e)

    # Check Ollama host
    try:
        import httpx

        ollama_url = os.getenv("OLLAMA_BASE_URL", "http://host.docker.internal:11434")
        with httpx.Client(timeout=2.0) as client:
            response = client.get(f"{ollama_url}/api/tags")
            response.raise_for_status()
            health_status["components"]["ollama_host"] = "healthy"
            health_status["ollama_models"] = [
                model["name"] for model in response.json().get("models", [])
            ]
    except Exception as e:
        health_status["components"]["ollama_host"] = "error"
        health_status["ollama_error"] = str(e)

    # Determine overall status
    unhealthy_components = [
        k for k, v in health_status["components"].items() if v != "healthy"
    ]
    if unhealthy_components:
        health_status["overall_status"] = "degraded"
        health_status["unhealthy_components"] = unhealthy_components

    return health_status


@router.get("/api/monitoring/cache")
async def cache_stats():
    """Cache performance statistics"""

    cache = get_smart_cache()
    return {
        "cache_stats": cache.get_stats(),
        "configuration": {
            "redis_url": cache.redis_url,
            "semantic_threshold": cache.semantic_threshold,
        },
        "recommendations": _get_cache_recommendations(cache.get_stats()),
    }


@router.get("/api/monitoring/routing")
async def routing_stats():
    """Routing and quota statistics"""

    quota_stats = get_all_quota_stats()

    return {
        "quota_trackers": quota_stats,
        "recommendations": _get_routing_recommendations(quota_stats),
    }


@router.get("/api/monitoring/circuit-breakers")
async def circuit_breaker_stats():
    """Circuit breaker status"""

    return {
        "circuit_breakers": get_all_circuit_stats(),
        "recommendations": _get_circuit_breaker_recommendations(),
    }


@router.get("/api/monitoring/performance")
async def performance_metrics():
    """Performance metrics and SLO tracking"""

    cache_stats = get_smart_cache().get_stats()
    quota_stats = get_all_quota_stats()
    circuit_stats = get_all_circuit_stats()

    # Calculate performance score
    performance_score = _calculate_performance_score(cache_stats, quota_stats)

    return {
        "performance_score": performance_score,
        "slo_status": {
            "target_latency_p95_ms": 900,
            "target_tool_precision": 0.85,
            "target_success_rate": 0.98,
            "target_cache_hit_rate": 0.4,
        },
        "current_metrics": {
            "cache_hit_rate": cache_stats.get("hit_rate", 0.0),
            "avg_hit_latency_ms": cache_stats.get("avg_hit_latency_ms", 0.0),
            "micro_routing_share": quota_stats.get("micro_routing", {}).get(
                "micro_share", 0.0
            ),
        },
        "recommendations": _get_performance_recommendations(
            performance_score, cache_stats, quota_stats
        ),
    }


@router.post("/api/monitoring/reset-stats")
async def reset_statistics():
    """Reset all performance statistics"""

    # Reset cache stats
    cache = get_smart_cache()
    cache.clear_stats()

    # Reset quota trackers
    from ..utils.quota_tracker import get_quota_tracker

    quota_tracker = get_quota_tracker("micro_routing")
    quota_tracker.reset()

    logger.info("All statistics reset")

    return {"status": "statistics_reset", "timestamp": time.time()}


def _get_cache_recommendations(stats: Dict[str, Any]) -> list:
    """Generate cache optimization recommendations"""

    recommendations = []
    hit_rate = stats.get("hit_rate", 0.0)

    if hit_rate < 0.2:
        recommendations.append(
            {
                "level": "critical",
                "message": "Cache hit rate very low - check semantic threshold and key canonicalization",
            }
        )
    elif hit_rate < 0.4:
        recommendations.append(
            {
                "level": "warning",
                "message": "Cache hit rate below target - consider lowering semantic threshold",
            }
        )
    else:
        recommendations.append(
            {"level": "info", "message": "Cache performance is good"}
        )

    if stats.get("l1_hit_rate", 0.0) < 0.1:
        recommendations.append(
            {
                "level": "warning",
                "message": "L1 exact matches very low - check prompt canonicalization",
            }
        )

    return recommendations


def _get_routing_recommendations(quota_stats: Dict[str, Dict]) -> list:
    """Generate routing optimization recommendations"""

    recommendations = []
    micro_stats = quota_stats.get("micro_routing", {})
    micro_share = micro_stats.get("micro_share", 0.0)

    target_share = float(os.getenv("MICRO_MAX_SHARE", "0.2"))

    if micro_share > target_share + 0.1:
        recommendations.append(
            {
                "level": "warning",
                "message": f"Micro routing above target ({micro_share:.2f} > {target_share})",
            }
        )
    elif micro_share < target_share - 0.1:
        recommendations.append(
            {
                "level": "info",
                "message": "Micro routing below target - could increase for better latency",
            }
        )
    else:
        recommendations.append(
            {"level": "info", "message": "Routing distribution is optimal"}
        )

    return recommendations


def _get_circuit_breaker_recommendations() -> list:
    """Generate circuit breaker recommendations"""

    circuit_stats = get_all_circuit_stats()
    recommendations = []

    for cb_stat in circuit_stats:
        if cb_stat["state"] == "open":
            recommendations.append(
                {
                    "level": "critical",
                    "message": f"Circuit breaker {cb_stat['name']} is OPEN - service failing",
                }
            )
        elif cb_stat["failure_count"] > 0:
            recommendations.append(
                {
                    "level": "warning",
                    "message": f"Circuit breaker {cb_stat['name']} has recent failures",
                }
            )

    if not recommendations:
        recommendations.append(
            {"level": "info", "message": "All circuit breakers healthy"}
        )

    return recommendations


def _calculate_performance_score(cache_stats: Dict, quota_stats: Dict) -> float:
    """Calculate overall performance score 0-100"""

    # Weight different metrics
    cache_score = min(cache_stats.get("hit_rate", 0.0) * 2.5, 1.0) * 40  # Max 40 points
    error_score = max(0, 1.0 - cache_stats.get("error_rate", 0.0)) * 20  # Max 20 points

    # Routing efficiency (how well we stick to quotas)
    micro_stats = quota_stats.get("micro_routing", {})
    target_share = float(os.getenv("MICRO_MAX_SHARE", "0.2"))
    actual_share = micro_stats.get("micro_share", 0.0)
    routing_efficiency = (
        max(0, 1.0 - abs(actual_share - target_share) * 2) * 20
    )  # Max 20 points

    latency_score = 20  # Placeholder - would need actual latency measurements

    return cache_score + error_score + routing_efficiency + latency_score


def _get_performance_recommendations(
    score: float, cache_stats: Dict, quota_stats: Dict
) -> list:
    """Generate performance optimization recommendations"""

    recommendations = []

    if score < 60:
        recommendations.append(
            {
                "level": "critical",
                "message": "System performance below acceptable levels",
            }
        )
    elif score < 80:
        recommendations.append(
            {"level": "warning", "message": "System performance needs optimization"}
        )
    else:
        recommendations.append(
            {"level": "info", "message": "System performance is excellent!"}
        )

    return recommendations
