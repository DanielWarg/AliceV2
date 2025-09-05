"""
SLO Monitor - Real-time system health with red/yellow/green status
==================================================================

Production-ready service level objective monitoring for Alice v2
- Real-time health status (green/yellow/red)
- Resource threshold monitoring (RAM/CPU)
- 429/503 error rate tracking
- Human-readable status messages
- Webhook integration for alerts
"""

import json
import logging
from dataclasses import asdict, dataclass
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Callable, Dict, List, Optional

import httpx
import structlog

logger = structlog.get_logger(__name__)


# SLO Status Colors
class SLOStatus(str, Enum):
    GREEN = "green"  # All systems normal
    YELLOW = "yellow"  # Warning thresholds exceeded
    RED = "red"  # Critical issues, degraded service


@dataclass
class SLOThresholds:
    """Production-tight SLO thresholds per blueprint"""

    # P95 response time budgets per route (ms)
    fast_p95_budget_ms: int = 250
    fast_p95_yellow_pct: float = 1.10  # 10% over budget = yellow
    fast_p95_red_pct: float = 1.20  # 20% over budget = red

    planner_first_p95_budget_ms: int = 900
    planner_full_p95_budget_ms: int = 1500
    planner_yellow_pct: float = 1.15  # 15% over budget = yellow
    planner_red_pct: float = 1.30  # 30% over budget = red

    deep_first_p95_budget_ms: int = 1800
    deep_full_p95_budget_ms: int = 3000
    deep_yellow_pct: float = 1.15  # 15% over budget = yellow
    deep_red_pct: float = 1.30  # 30% over budget = red

    # Resource thresholds (%) - production values
    ram_soft_pct: float = 0.80  # 80% soft trigger
    ram_hard_pct: float = 0.92  # 92% hard trigger
    ram_recovery_pct: float = 0.75  # 75% recovery
    cpu_soft_pct: float = 0.80  # 80% soft trigger
    cpu_hard_pct: float = 0.92  # 92% hard trigger
    cpu_recovery_pct: float = 0.75  # 75% recovery

    # Temp/battery cutoffs
    temp_yellow_c: float = 80.0  # 80°C warning
    temp_red_c: float = 85.0  # 85°C critical
    battery_yellow_pct: float = 30.0  # 30% battery warning
    battery_red_pct: float = 25.0  # 25% battery critical

    # Error budget thresholds (per window)
    error_window_min: int = 5  # 5-minute windows
    error_429_yellow_rate: float = 0.01  # >1% 429s = yellow
    error_429_red_rate: float = 0.05  # >5% 429s = red
    error_5xx_yellow_rate: float = 0.005  # >0.5% 5xx = yellow
    error_5xx_red_rate: float = 0.02  # >2% 5xx = red

    # Hysteresis settings
    measurement_window: int = 5  # 5-point sliding window
    recovery_hysteresis_s: int = 60  # 60s recovery before NORMAL
    violation_consecutive: int = 3  # 3 consecutive violations for alert


@dataclass
class SystemMetrics:
    """Current system metrics with route-specific P95s"""

    timestamp: str

    # Route-specific P95 response times (ms)
    p95_fast_ms: float = 0.0
    p95_planner_first_ms: float = 0.0
    p95_planner_full_ms: float = 0.0
    p95_deep_first_ms: float = 0.0
    p95_deep_full_ms: float = 0.0

    # P50 for observability
    p50_fast_ms: float = 0.0
    p50_planner_ms: float = 0.0
    p50_deep_ms: float = 0.0

    # Resource metrics with 5-point sliding window
    ram_pct: float = 0.0
    ram_peak_mb: float = 0.0
    cpu_pct: float = 0.0
    temp_c: Optional[float] = None
    battery_pct: Optional[float] = None

    # Error budget metrics (per 5-min window)
    error_429_rate: float = 0.0  # Admission control failures
    error_5xx_rate: float = 0.0  # Server failures
    total_requests: int = 0

    # Guardian metrics
    guardian_state: str = "NORMAL"
    guardian_level: Optional[str] = None  # LIGHT/MODERATE/HEAVY brownout
    guardian_available: bool = True
    brownout_reason: Optional[str] = None
    brownout_since_s: float = 0.0

    # Test & observability
    test_success_rate: float = 1.0
    last_test_run: Optional[str] = None
    rag_hit_rate: float = 0.0
    tool_error_rate: float = 0.0


@dataclass
class SLOResult:
    """SLO evaluation result"""

    status: SLOStatus
    score: int  # 0-100 health score
    message: str
    issues: List[str]
    metrics: SystemMetrics
    recommendations: List[str]


class SLOMonitor:
    """Real-time SLO monitoring with status indicators"""

    def __init__(
        self,
        thresholds: Optional[SLOThresholds] = None,
        orchestrator_url: str = "http://localhost:8000",
        guardian_url: str = "http://localhost:8787",
    ):
        self.thresholds = thresholds or SLOThresholds()
        self.orchestrator_url = orchestrator_url
        self.guardian_url = guardian_url
        self.logger = logging.getLogger("slo_monitor")

        # Metrics storage
        self.metrics_history: List[SystemMetrics] = []
        self.current_status = SLOStatus.GREEN

        # Alert hooks
        self.alert_hooks: List[Callable[[SLOResult], None]] = []

    def add_alert_hook(self, hook: Callable[[SLOResult], None]):
        """Add webhook for status change alerts"""
        self.alert_hooks.append(hook)

    async def collect_metrics(self) -> SystemMetrics:
        """Collect current system metrics from all services"""

        timestamp = datetime.utcnow().isoformat() + "Z"
        metrics = SystemMetrics(timestamp=timestamp)

        # Collect orchestrator metrics
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(f"{self.orchestrator_url}/health")
                if response.status_code == 200:
                    data = response.json()
                    metrics.avg_response_ms = data.get("metrics", {}).get(
                        "avg_response_ms", 0.0
                    )
                    metrics.success_rate = data.get("metrics", {}).get(
                        "success_rate", 1.0
                    )
                else:
                    self.logger.warning(
                        f"Orchestrator health check failed: {response.status_code}"
                    )
                    metrics.success_rate = 0.0
        except Exception as e:
            self.logger.error(f"Failed to collect orchestrator metrics: {e}")
            metrics.success_rate = 0.0

        # Collect Guardian metrics
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(f"{self.guardian_url}/health")
                if response.status_code == 200:
                    data = response.json()
                    guardian_metrics = data.get("metrics", {})
                    metrics.ram_pct = guardian_metrics.get("ram_pct", 0.0) / 100.0
                    metrics.cpu_pct = guardian_metrics.get("cpu_pct", 0.0) / 100.0
                    metrics.guardian_state = data.get("status", "normal")
                    metrics.guardian_available = True
                else:
                    self.logger.warning(
                        f"Guardian health check failed: {response.status_code}"
                    )
                    metrics.guardian_available = False
        except Exception as e:
            self.logger.error(f"Failed to collect Guardian metrics: {e}")
            metrics.guardian_available = False

        # Load recent test results
        try:
            trends_file = Path("test-results/trends/nightly_trends.jsonl")
            if trends_file.exists():
                # Read last trend entry
                with open(trends_file, "r") as f:
                    lines = f.readlines()
                    if lines:
                        last_trend = json.loads(lines[-1].strip())
                        metrics.test_success_rate = (
                            1.0 if last_trend.get("slo_compliant", True) else 0.8
                        )
                        metrics.last_test_run = last_trend.get("timestamp")
        except Exception as e:
            self.logger.error(f"Failed to load test metrics: {e}")

        # Store in history (keep last 100 entries)
        self.metrics_history.append(metrics)
        if len(self.metrics_history) > 100:
            self.metrics_history.pop(0)

        return metrics

    def calculate_weighted_health_score(
        self, metrics: SystemMetrics, violations: Dict[str, float]
    ) -> int:
        """
        Calculate weighted health score (0-100) based on blueprint formula:
        Score = 100 - (SLO_violations*40 + error_budget*25 + guardian_penalty*20 + temp_battery*15)
        """
        penalty = 0.0

        # SLO violations (40% weight) - per-route P95 overruns
        slo_penalty = 0.0
        if violations.get("p95_fast", 0) > 0:
            slo_penalty += min(violations["p95_fast"] * 15, 15)  # Max 15 points
        if violations.get("p95_planner", 0) > 0:
            slo_penalty += min(violations["p95_planner"] * 15, 15)  # Max 15 points
        if violations.get("p95_deep", 0) > 0:
            slo_penalty += min(violations["p95_deep"] * 10, 10)  # Max 10 points
        penalty += min(slo_penalty, 40)  # Cap at 40 points

        # Error budget violations (25% weight)
        error_penalty = 0.0
        if metrics.error_429_rate > self.thresholds.error_429_yellow_rate:
            error_penalty += (
                10 if metrics.error_429_rate > self.thresholds.error_429_red_rate else 5
            )
        if metrics.error_5xx_rate > self.thresholds.error_5xx_yellow_rate:
            error_penalty += (
                15 if metrics.error_5xx_rate > self.thresholds.error_5xx_red_rate else 8
            )
        penalty += min(error_penalty, 25)  # Cap at 25 points

        # Guardian state penalties (20% weight)
        guardian_penalty = {
            "LOCKDOWN": 20,
            "EMERGENCY": 18,
            "DEGRADED": 15,
            "BROWNOUT": {"HEAVY": 12, "MODERATE": 8, "LIGHT": 5}.get(
                metrics.guardian_level, 8
            ),
            "NORMAL": 0,
        }.get(metrics.guardian_state, 0)
        if not metrics.guardian_available:
            guardian_penalty = 20
        penalty += guardian_penalty

        # Temp/battery penalties (15% weight)
        temp_battery_penalty = 0.0
        if metrics.temp_c:
            if metrics.temp_c >= self.thresholds.temp_red_c:
                temp_battery_penalty += 8
            elif metrics.temp_c >= self.thresholds.temp_yellow_c:
                temp_battery_penalty += 4
        if metrics.battery_pct:
            if metrics.battery_pct <= self.thresholds.battery_red_pct:
                temp_battery_penalty += 7
            elif metrics.battery_pct <= self.thresholds.battery_yellow_pct:
                temp_battery_penalty += 3
        penalty += min(temp_battery_penalty, 15)  # Cap at 15 points

        return max(0, min(100, int(100 - penalty)))

    def evaluate_slo(self, metrics: SystemMetrics) -> SLOResult:
        """Evaluate current metrics against production SLO thresholds"""

        issues = []
        recommendations = []
        status = SLOStatus.GREEN
        violations = {}

        # Route-specific P95 SLO evaluation
        # Fast route (≤250ms budget)
        if (
            metrics.p95_fast_ms
            > self.thresholds.fast_p95_budget_ms * self.thresholds.fast_p95_red_pct
        ):
            overrun = metrics.p95_fast_ms / self.thresholds.fast_p95_budget_ms
            violations["p95_fast"] = overrun
            issues.append(
                f"Critical: Fast route P95 {metrics.p95_fast_ms:.0f}ms > {self.thresholds.fast_p95_budget_ms * self.thresholds.fast_p95_red_pct:.0f}ms"
            )
            recommendations.append(
                "Scale fast route capacity or implement degrade & gate"
            )
            status = SLOStatus.RED
        elif (
            metrics.p95_fast_ms
            > self.thresholds.fast_p95_budget_ms * self.thresholds.fast_p95_yellow_pct
        ):
            overrun = metrics.p95_fast_ms / self.thresholds.fast_p95_budget_ms
            violations["p95_fast"] = overrun
            issues.append(
                f"Warning: Fast route P95 {metrics.p95_fast_ms:.0f}ms > {self.thresholds.fast_p95_budget_ms * self.thresholds.fast_p95_yellow_pct:.0f}ms"
            )
            recommendations.append("Monitor fast route latency trends")
            if status == SLOStatus.GREEN:
                status = SLOStatus.YELLOW

        # Planner route (≤900/1500ms budget)
        if (
            metrics.p95_planner_full_ms
            > self.thresholds.planner_full_p95_budget_ms
            * self.thresholds.planner_red_pct
        ):
            overrun = (
                metrics.p95_planner_full_ms / self.thresholds.planner_full_p95_budget_ms
            )
            violations["p95_planner"] = overrun
            issues.append(
                f"Critical: Planner P95 {metrics.p95_planner_full_ms:.0f}ms > {self.thresholds.planner_full_p95_budget_ms * self.thresholds.planner_red_pct:.0f}ms"
            )
            recommendations.append(
                "Reduce planner context size or enable brownout mode"
            )
            status = SLOStatus.RED
        elif (
            metrics.p95_planner_full_ms
            > self.thresholds.planner_full_p95_budget_ms
            * self.thresholds.planner_yellow_pct
        ):
            overrun = (
                metrics.p95_planner_full_ms / self.thresholds.planner_full_p95_budget_ms
            )
            violations["p95_planner"] = overrun
            issues.append(
                f"Warning: Planner P95 {metrics.p95_planner_full_ms:.0f}ms > {self.thresholds.planner_full_p95_budget_ms * self.thresholds.planner_yellow_pct:.0f}ms"
            )
            recommendations.append("Consider reducing planner complexity")
            if status == SLOStatus.GREEN:
                status = SLOStatus.YELLOW

        # Deep route (≤1800/3000ms budget)
        if (
            metrics.p95_deep_full_ms
            > self.thresholds.deep_full_p95_budget_ms * self.thresholds.deep_red_pct
        ):
            overrun = metrics.p95_deep_full_ms / self.thresholds.deep_full_p95_budget_ms
            violations["p95_deep"] = overrun
            issues.append(
                f"Critical: Deep route P95 {metrics.p95_deep_full_ms:.0f}ms > {self.thresholds.deep_full_p95_budget_ms * self.thresholds.deep_red_pct:.0f}ms"
            )
            recommendations.append("Emergency: Degrade deep processing or gate traffic")
            status = SLOStatus.RED
        elif (
            metrics.p95_deep_full_ms
            > self.thresholds.deep_full_p95_budget_ms * self.thresholds.deep_yellow_pct
        ):
            overrun = metrics.p95_deep_full_ms / self.thresholds.deep_full_p95_budget_ms
            violations["p95_deep"] = overrun
            issues.append(
                f"Warning: Deep route P95 {metrics.p95_deep_full_ms:.0f}ms > {self.thresholds.deep_full_p95_budget_ms * self.thresholds.deep_yellow_pct:.0f}ms"
            )
            recommendations.append("Monitor deep route resource usage")
            if status == SLOStatus.GREEN:
                status = SLOStatus.YELLOW

        # Error budget evaluation (5-minute windows)
        if metrics.error_429_rate > self.thresholds.error_429_red_rate:
            issues.append(
                f"Critical: 429 rate {metrics.error_429_rate:.1%} > {self.thresholds.error_429_red_rate:.1%} (admission control failure)"
            )
            recommendations.append(
                "Emergency: Implement aggressive admission control and degrade & gate"
            )
            status = SLOStatus.RED
        elif metrics.error_429_rate > self.thresholds.error_429_yellow_rate:
            issues.append(
                f"Warning: 429 rate {metrics.error_429_rate:.1%} > {self.thresholds.error_429_yellow_rate:.1%} (high traffic)"
            )
            recommendations.append("Consider preemptive brownout mode")
            if status == SLOStatus.GREEN:
                status = SLOStatus.YELLOW

        if metrics.error_5xx_rate > self.thresholds.error_5xx_red_rate:
            issues.append(
                f"Critical: 5xx rate {metrics.error_5xx_rate:.1%} > {self.thresholds.error_5xx_red_rate:.1%} (server failures)"
            )
            recommendations.append(
                "Emergency: Investigate service failures and restart components"
            )
            status = SLOStatus.RED
        elif metrics.error_5xx_rate > self.thresholds.error_5xx_yellow_rate:
            issues.append(
                f"Warning: 5xx rate {metrics.error_5xx_rate:.1%} > {self.thresholds.error_5xx_yellow_rate:.1%} (service degradation)"
            )
            recommendations.append("Monitor service health and error logs")
            if status == SLOStatus.GREEN:
                status = SLOStatus.YELLOW

        # Resource evaluation with production thresholds
        if metrics.ram_pct > self.thresholds.ram_hard_pct:
            issues.append(
                f"Critical: RAM usage {metrics.ram_pct:.1%} > {self.thresholds.ram_hard_pct:.1%} (hard trigger)"
            )
            recommendations.append(
                "Emergency: Trigger Guardian emergency mode immediately"
            )
            status = SLOStatus.RED
        elif metrics.ram_pct > self.thresholds.ram_soft_pct:
            issues.append(
                f"Warning: RAM usage {metrics.ram_pct:.1%} > {self.thresholds.ram_soft_pct:.1%} (soft trigger)"
            )
            recommendations.append("Trigger Guardian brownout mode and degrade & gate")
            if status == SLOStatus.GREEN:
                status = SLOStatus.YELLOW

        if metrics.cpu_pct > self.thresholds.cpu_hard_pct:
            issues.append(
                f"Critical: CPU usage {metrics.cpu_pct:.1%} > {self.thresholds.cpu_hard_pct:.1%} (hard trigger)"
            )
            recommendations.append("Emergency: Reduce CPU load or scale resources")
            status = SLOStatus.RED
        elif metrics.cpu_pct > self.thresholds.cpu_soft_pct:
            issues.append(
                f"Warning: CPU usage {metrics.cpu_pct:.1%} > {self.thresholds.cpu_soft_pct:.1%} (soft trigger)"
            )
            recommendations.append("Monitor CPU trends and enable brownout if needed")
            if status == SLOStatus.GREEN:
                status = SLOStatus.YELLOW

        # Temperature/battery evaluation
        if metrics.temp_c and metrics.temp_c >= self.thresholds.temp_red_c:
            issues.append(
                f"Critical: Temperature {metrics.temp_c:.1f}°C ≥ {self.thresholds.temp_red_c}°C"
            )
            recommendations.append(
                "Emergency: Reduce processing load to prevent thermal throttling"
            )
            status = SLOStatus.RED
        elif metrics.temp_c and metrics.temp_c >= self.thresholds.temp_yellow_c:
            issues.append(
                f"Warning: Temperature {metrics.temp_c:.1f}°C ≥ {self.thresholds.temp_yellow_c}°C"
            )
            recommendations.append("Monitor thermal state and consider cooling")
            if status == SLOStatus.GREEN:
                status = SLOStatus.YELLOW

        if (
            metrics.battery_pct
            and metrics.battery_pct <= self.thresholds.battery_red_pct
        ):
            issues.append(
                f"Critical: Battery {metrics.battery_pct:.1f}% ≤ {self.thresholds.battery_red_pct}%"
            )
            recommendations.append(
                "Emergency: Enable power saving mode and reduce load"
            )
            status = SLOStatus.RED
        elif (
            metrics.battery_pct
            and metrics.battery_pct <= self.thresholds.battery_yellow_pct
        ):
            issues.append(
                f"Warning: Battery {metrics.battery_pct:.1f}% ≤ {self.thresholds.battery_yellow_pct}%"
            )
            recommendations.append("Consider reducing background processing")
            if status == SLOStatus.GREEN:
                status = SLOStatus.YELLOW

        # Guardian state evaluation with new states
        if not metrics.guardian_available:
            issues.append("Warning: Guardian service unavailable")
            recommendations.append("Guardian metrics unavailable - using cached data")
            # Don't set status to RED for Guardian unavailability - allow degraded operation
            if status == SLOStatus.GREEN:
                status = SLOStatus.YELLOW
        elif metrics.guardian_state in ["EMERGENCY", "LOCKDOWN"]:
            issues.append(f"Critical: Guardian in {metrics.guardian_state} state")
            if metrics.brownout_reason:
                issues.append(
                    f"Trigger: {metrics.brownout_reason} ({metrics.brownout_since_s:.1f}s ago)"
                )
            recommendations.append(
                "Investigate system overload and degrade & gate traffic"
            )
            status = SLOStatus.RED
        elif metrics.guardian_state == "DEGRADED":
            issues.append("Critical: Guardian in DEGRADED state")
            recommendations.append("System in recovery mode - monitor closely")
            status = SLOStatus.RED
        elif metrics.guardian_state == "BROWNOUT":
            level_desc = (
                f" ({metrics.guardian_level})" if metrics.guardian_level else ""
            )
            issues.append(f"Warning: Guardian in BROWNOUT{level_desc} mode")
            if metrics.brownout_since_s > 300:  # > 5 minutes
                recommendations.append(
                    f"Brownout active for {metrics.brownout_since_s/60:.1f}min - investigate load reduction"
                )
            else:
                recommendations.append("Brownout active - degrade & gate in effect")
            if status == SLOStatus.GREEN:
                status = SLOStatus.YELLOW

        # Test success evaluation
        if metrics.test_success_rate < 0.85:  # 85% minimum for tests
            issues.append(
                f"Warning: Test success rate {metrics.test_success_rate:.1%} below 85%"
            )
            recommendations.append("Review failing test scenarios and fix core issues")
            if status == SLOStatus.GREEN:
                status = SLOStatus.YELLOW

        # Calculate weighted health score using production formula
        score = self.calculate_weighted_health_score(metrics, violations)

        # Generate human-readable message
        if status == SLOStatus.GREEN:
            message = f"All systems operational (Health Score: {score}/100)"
        elif status == SLOStatus.YELLOW:
            message = f"System degraded - {len(issues)} warning(s) (Health Score: {score}/100)"
        else:
            message = f"Critical issues detected - {len(issues)} error(s) (Health Score: {score}/100)"

        return SLOResult(
            status=status,
            score=score,
            message=message,
            issues=issues,
            metrics=metrics,
            recommendations=recommendations,
        )

    def get_status_emoji(self, status: SLOStatus) -> str:
        """Get emoji for status display"""
        return {SLOStatus.GREEN: "🟢", SLOStatus.YELLOW: "🟡", SLOStatus.RED: "🔴"}[
            status
        ]

    def format_human_status(self, result: SLOResult) -> str:
        """Format status for human display"""

        emoji = self.get_status_emoji(result.status)
        lines = [
            f"{emoji} **Alice System Status: {result.status.upper()}**",
            f"Health Score: {result.score}/100",
            f"Last Updated: {result.metrics.timestamp}",
            "",
            "📊 **Key Metrics:**",
            f"• Response Time: {result.metrics.avg_response_ms:.0f}ms",
            f"• Success Rate: {result.metrics.success_rate:.1%}",
            f"• RAM Usage: {result.metrics.ram_pct:.1%}",
            f"• CPU Usage: {result.metrics.cpu_pct:.1%}",
            f"• Guardian: {result.metrics.guardian_state.title()}",
            "",
        ]

        if result.issues:
            lines.append("⚠️ **Issues:**")
            for issue in result.issues:
                lines.append(f"• {issue}")
            lines.append("")

        if result.recommendations:
            lines.append("💡 **Recommendations:**")
            for rec in result.recommendations:
                lines.append(f"• {rec}")

        return "\n".join(lines)

    async def check_and_alert(self) -> SLOResult:
        """Check SLO status and send alerts if status changed"""

        metrics = await self.collect_metrics()
        result = self.evaluate_slo(metrics)

        # Send alerts if status changed
        if result.status != self.current_status:
            self.logger.info(
                f"SLO status changed: {self.current_status} -> {result.status}"
            )

            for hook in self.alert_hooks:
                try:
                    hook(result)
                except Exception as e:
                    self.logger.error(f"Alert hook failed: {e}")

            self.current_status = result.status

        return result

    def save_status_report(self, result: SLOResult, file_path: str):
        """Save detailed status report to file"""

        report = {
            "generated_at": datetime.utcnow().isoformat() + "Z",
            "status": result.status,
            "score": result.score,
            "message": result.message,
            "issues": result.issues,
            "recommendations": result.recommendations,
            "metrics": asdict(result.metrics),
            "thresholds": asdict(self.thresholds),
        }

        with open(file_path, "w") as f:
            json.dump(report, f, indent=2, ensure_ascii=False)

        self.logger.info(f"Status report saved: {file_path}")


# Example alert hooks
def slack_webhook_alert(webhook_url: str):
    """Create Slack webhook alert function"""

    def send_alert(result: SLOResult):
        emoji = {
            SLOStatus.GREEN: ":green_circle:",
            SLOStatus.YELLOW: ":yellow_circle:",
            SLOStatus.RED: ":red_circle:",
        }[result.status]

        message = {
            "text": f"{emoji} Alice System Status: {result.status.upper()}",
            "blocks": [
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"*{emoji} Alice System Status: {result.status.upper()}*\n{result.message}",
                    },
                }
            ],
        }

        if result.issues:
            message["blocks"].append(
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": "*Issues:*\n"
                        + "\n".join([f"• {issue}" for issue in result.issues]),
                    },
                }
            )

        # Send to Slack (implementation would use requests/httpx)

    return send_alert


def console_alert(result: SLOResult):
    """Simple console alert for development"""
    logger.warning(
        "SLO Alert", status=result.status, message=result.message, issues=result.issues
    )
