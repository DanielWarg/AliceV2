"""
System Status Router - SLO monitoring with red/yellow/green indicators
======================================================================
"""

from datetime import datetime
from typing import Any, Dict

import structlog
from fastapi import APIRouter, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse

from ..utils.slo_monitor import SLOMonitor, console_alert

# Initialize logging
logger = structlog.get_logger(__name__)

# Initialize SLO monitor
slo_monitor = SLOMonitor()
slo_monitor.add_alert_hook(console_alert)

# Create router
router = APIRouter()


@router.get("/", response_model=Dict[str, Any])
async def get_system_status():
    """Get current system status with SLO evaluation"""
    try:
        result = await slo_monitor.check_and_alert()

        return {
            "status": result.status,
            "health_score": result.score,
            "message": result.message,
            "timestamp": result.metrics.timestamp,
            "issues": result.issues,
            "recommendations": result.recommendations,
            "metrics": {
                "response_time_ms": result.metrics.avg_response_ms,
                "success_rate": result.metrics.success_rate,
                "ram_usage_pct": result.metrics.ram_pct * 100,
                "cpu_usage_pct": result.metrics.cpu_pct * 100,
                "guardian_state": result.metrics.guardian_state,
                "guardian_available": result.metrics.guardian_available,
                "test_success_rate": result.metrics.test_success_rate,
                "last_test_run": result.metrics.last_test_run,
            },
            "thresholds": {
                "response_time_yellow_ms": slo_monitor.thresholds.response_time_yellow_ms,
                "response_time_red_ms": slo_monitor.thresholds.response_time_red_ms,
                "success_rate_yellow": slo_monitor.thresholds.success_rate_yellow,
                "success_rate_red": slo_monitor.thresholds.success_rate_red,
                "ram_yellow_pct": slo_monitor.thresholds.ram_yellow * 100,
                "ram_red_pct": slo_monitor.thresholds.ram_red * 100,
                "cpu_yellow_pct": slo_monitor.thresholds.cpu_yellow * 100,
                "cpu_red_pct": slo_monitor.thresholds.cpu_red * 100,
            },
        }

    except Exception as e:
        logger.error("Failed to get system status", error=str(e))
        raise HTTPException(status_code=500, detail="Status check failed")


@router.get("/simple")
async def get_simple_status():
    """Get simple status for quick health checks"""
    try:
        result = await slo_monitor.check_and_alert()

        status_code = {"green": 200, "yellow": 200, "red": 503}.get(result.status, 500)

        return JSONResponse(
            status_code=status_code,
            content={
                "status": result.status,
                "score": result.score,
                "message": result.message,
                "emoji": slo_monitor.get_status_emoji(result.status),
            },
        )

    except Exception as e:
        logger.error("Failed to get simple status", error=str(e))
        return JSONResponse(
            status_code=500,
            content={
                "status": "red",
                "score": 0,
                "message": "Status check failed",
                "emoji": "🔴",
            },
        )


@router.get("/human", response_class=HTMLResponse)
async def get_human_status():
    """Get human-readable status page"""
    try:
        result = await slo_monitor.check_and_alert()

        # Convert markdown to HTML for display
        human_text = slo_monitor.format_human_status(result)
        html_content = (
            human_text.replace("\n", "<br>")
            .replace("**", "<strong>")
            .replace("**", "</strong>")
        )

        # Color coding
        bg_color = {"green": "#d4edda", "yellow": "#fff3cd", "red": "#f8d7da"}.get(
            result.status, "#f8f9fa"
        )

        border_color = {"green": "#c3e6cb", "yellow": "#ffeaa7", "red": "#f5c6cb"}.get(
            result.status, "#dee2e6"
        )

        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Alice System Status</title>
            <meta charset="utf-8">
            <meta name="viewport" content="width=device-width, initial-scale=1">
            <meta http-equiv="refresh" content="30"> <!-- Auto-refresh every 30s -->
            <style>
                body {{ 
                    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Arial, sans-serif;
                    margin: 20px;
                    background-color: #f8f9fa;
                }}
                .status-card {{
                    max-width: 800px;
                    margin: 0 auto;
                    background: {bg_color};
                    border: 2px solid {border_color};
                    border-radius: 8px;
                    padding: 20px;
                    box-shadow: 0 2px 4px rgba(0,0,0,0.1);
                }}
                .timestamp {{
                    color: #6c757d;
                    font-size: 0.9em;
                    margin-bottom: 15px;
                }}
                .score {{
                    font-size: 1.2em;
                    font-weight: bold;
                    margin: 10px 0;
                }}
                .metrics {{
                    background: white;
                    padding: 15px;
                    border-radius: 5px;
                    margin: 15px 0;
                }}
                .issue {{
                    background: #fff3cd;
                    border-left: 4px solid #ffc107;
                    padding: 10px;
                    margin: 5px 0;
                }}
                .critical {{
                    background: #f8d7da;
                    border-left-color: #dc3545;
                }}
            </style>
        </head>
        <body>
            <div class="status-card">
                <div class="timestamp">Last Updated: {result.metrics.timestamp}</div>
                {html_content}
                <div class="metrics">
                    <strong>📊 Technical Details:</strong><br>
                    Response Time: {result.metrics.avg_response_ms:.0f}ms<br>
                    RAM: {result.metrics.ram_pct:.1%} | CPU: {result.metrics.cpu_pct:.1%}<br>
                    Guardian: {result.metrics.guardian_state.title()}<br>
                    Test Success: {result.metrics.test_success_rate:.1%}
                </div>
            </div>
        </body>
        </html>
        """

        return HTMLResponse(content=html)

    except Exception as e:
        logger.error("Failed to get human status", error=str(e))
        return HTMLResponse(
            content=f"<h1>🔴 Status Check Failed</h1><p>Error: {str(e)}</p>",
            status_code=500,
        )


@router.get("/metrics/history")
async def get_metrics_history():
    """Get historical metrics for trending"""
    try:
        history = [
            {
                "timestamp": m.timestamp,
                "response_time_ms": m.avg_response_ms,
                "success_rate": m.success_rate,
                "ram_pct": m.ram_pct * 100,
                "cpu_pct": m.cpu_pct * 100,
                "guardian_state": m.guardian_state,
            }
            for m in slo_monitor.metrics_history[-50:]  # Last 50 entries
        ]

        return {"history": history, "count": len(history)}

    except Exception as e:
        logger.error("Failed to get metrics history", error=str(e))
        raise HTTPException(status_code=500, detail="History unavailable")


@router.post("/thresholds")
async def update_thresholds(thresholds: dict):
    """Update SLO thresholds (admin endpoint)"""
    try:
        # Update thresholds dynamically
        for key, value in thresholds.items():
            if hasattr(slo_monitor.thresholds, key):
                setattr(slo_monitor.thresholds, key, value)
                logger.info(f"Updated threshold: {key} = {value}")

        return {
            "message": "Thresholds updated successfully",
            "updated_thresholds": thresholds,
        }

    except Exception as e:
        logger.error("Failed to update thresholds", error=str(e))
        raise HTTPException(status_code=500, detail="Threshold update failed")


@router.get("/slo-report")
async def generate_slo_report():
    """Generate detailed SLO compliance report"""
    try:
        result = await slo_monitor.check_and_alert()

        # Save detailed report
        report_path = f"test-results/slo-reports/slo_report_{datetime.utcnow().strftime('%Y%m%d_%H%M')}.json"
        slo_monitor.save_status_report(result, report_path)

        return {
            "status": result.status,
            "health_score": result.score,
            "compliance": result.score >= 90,  # 90+ is compliant
            "issues_count": len(result.issues),
            "recommendations_count": len(result.recommendations),
            "report_file": report_path,
            "summary": result.message,
        }

    except Exception as e:
        logger.error("Failed to generate SLO report", error=str(e))
        raise HTTPException(status_code=500, detail="Report generation failed")
