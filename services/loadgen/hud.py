#!/usr/bin/env python3
"""
Loadgen HUD - Real-time visualization of brownout testing
========================================================

Streamlit dashboard that reads guardian.jsonl and summary.json
to show trigger/recovery timeline with SLO validation.

Usage:
  streamlit run hud.py -- --run-dir /data/telemetry/loadgen_20241201_143022
"""

import json
import pathlib
import sys
from datetime import datetime
from typing import Any, Dict, List, Optional

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

# Configuration
SLO_BROWNOUT_TRIGGER_MS = 150
SLO_RECOVERY_S = 60


def load_guardian_events(run_dir: pathlib.Path) -> List[Dict[str, Any]]:
    """Load guardian events from JSONL file"""
    guardian_file = run_dir / "guardian.jsonl"
    events = []

    if guardian_file.exists():
        with open(guardian_file, "r") as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        events.append(json.loads(line))
                    except json.JSONDecodeError:
                        continue

    return events


def load_summary(run_dir: pathlib.Path) -> Optional[Dict[str, Any]]:
    """Load test summary"""
    summary_file = run_dir / "summary.json"

    if summary_file.exists():
        with open(summary_file, "r") as f:
            return json.load(f)

    return None


def load_result(run_dir: pathlib.Path) -> str:
    """Load PASS/FAIL result"""
    result_file = run_dir / "result.txt"

    if result_file.exists():
        return result_file.read_text().strip()

    return "UNKNOWN"


def create_timeline_chart(
    events: List[Dict[str, Any]], summary: Dict[str, Any]
) -> go.Figure:
    """Create timeline chart showing Guardian state transitions"""

    fig = go.Figure()

    if not events:
        fig.add_annotation(
            text="No guardian events found",
            xref="paper",
            yref="paper",
            x=0.5,
            y=0.5,
            showarrow=False,
        )
        return fig

    # Convert timestamps to datetime objects
    timeline_data = []
    base_time = None

    for event in events:
        if "ts" in event:
            try:
                ts = datetime.fromisoformat(event["ts"].replace("Z", "+00:00"))
                if base_time is None:
                    base_time = ts

                relative_ms = (ts - base_time).total_seconds() * 1000

                timeline_data.append(
                    {
                        "time_ms": relative_ms,
                        "event": event.get("event", "unknown"),
                        "state": event.get("state", {}).get("state", "UNKNOWN"),
                        "ram_pct": event.get("state", {}).get("ram_pct", 0),
                        "cpu_pct": event.get("state", {}).get("cpu_pct", 0),
                        "trigger_ms": event.get("trigger_ms"),
                        "recovered_s": event.get("recovered_s"),
                    }
                )
            except (ValueError, TypeError):
                continue

    if not timeline_data:
        fig.add_annotation(
            text="No valid timeline data",
            xref="paper",
            yref="paper",
            x=0.5,
            y=0.5,
            showarrow=False,
        )
        return fig

    df = pd.DataFrame(timeline_data)

    # State mapping for colors
    state_colors = {
        "NORMAL": "green",
        "BROWNOUT": "orange",
        "EMERGENCY": "red",
        "LOCKDOWN": "darkred",
        "UNKNOWN": "gray",
    }

    # Add state transitions as scatter plot
    for state in df["state"].unique():
        state_data = df[df["state"] == state]
        fig.add_trace(
            go.Scatter(
                x=state_data["time_ms"],
                y=state_data["ram_pct"],
                mode="markers+lines",
                name=f"Guardian {state}",
                marker=dict(color=state_colors.get(state, "blue"), size=8),
                hovertemplate="<b>%{fullData.name}</b><br>"
                + "Time: %{x:.0f}ms<br>"
                + "RAM: %{y:.1f}%<br>"
                + "<extra></extra>",
            )
        )

    # Add SLO threshold lines
    fig.add_hline(
        y=80,
        line_dash="dash",
        line_color="orange",
        annotation_text="RAM Soft Threshold (80%)",
    )
    fig.add_hline(
        y=92,
        line_dash="dash",
        line_color="red",
        annotation_text="RAM Hard Threshold (92%)",
    )

    # Add trigger latency annotation
    if summary and "trigger_ms" in summary and summary["trigger_ms"]:
        trigger_ms = summary["trigger_ms"]
        status = "✅ PASS" if trigger_ms <= SLO_BROWNOUT_TRIGGER_MS else "❌ FAIL"
        fig.add_annotation(
            x=trigger_ms,
            y=85,
            text=f"Brownout Trigger: {trigger_ms}ms {status}",
            arrowhead=2,
            arrowcolor="red",
        )

    fig.update_layout(
        title="Guardian State Timeline - Brownout Testing",
        xaxis_title="Time (ms from test start)",
        yaxis_title="RAM Usage (%)",
        showlegend=True,
        height=500,
    )

    return fig


def create_metrics_summary(summary: Dict[str, Any], result: str) -> None:
    """Create metrics summary cards"""

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        trigger_ms = summary.get("trigger_ms")
        if trigger_ms is not None:
            status = "🟢 PASS" if trigger_ms <= SLO_BROWNOUT_TRIGGER_MS else "🔴 FAIL"
            st.metric(
                "Brownout Trigger",
                f"{trigger_ms}ms",
                delta=f"{trigger_ms - SLO_BROWNOUT_TRIGGER_MS}ms vs budget",
                delta_color="inverse",
            )
            st.caption(f"Budget: {SLO_BROWNOUT_TRIGGER_MS}ms {status}")
        else:
            st.metric("Brownout Trigger", "❌ Not detected")

    with col2:
        recovered_s = summary.get("recovered_s")
        if recovered_s is not None:
            status = "🟢 PASS" if recovered_s <= SLO_RECOVERY_S else "🔴 FAIL"
            st.metric(
                "Recovery Time",
                f"{recovered_s}s",
                delta=f"{recovered_s - SLO_RECOVERY_S}s vs budget",
                delta_color="inverse",
            )
            st.caption(f"Budget: {SLO_RECOVERY_S}s {status}")
        else:
            st.metric("Recovery Time", "❌ Not detected")

    with col3:
        # Overall SLO status
        overall_pass = (
            trigger_ms is not None and trigger_ms <= SLO_BROWNOUT_TRIGGER_MS
        ) and (recovered_s is not None and recovered_s <= SLO_RECOVERY_S)
        status_icon = "✅" if overall_pass else "❌"
        st.metric("Overall SLO", f"{result} {status_icon}")

    with col4:
        # Test components
        stress_tests = len(
            [
                k
                for k in summary.keys()
                if k in ["deep", "memory", "cpu", "tools", "vision"]
            ]
        )
        st.metric("Stress Tests", f"{stress_tests} modules")


def create_stress_test_breakdown(summary: Dict[str, Any]) -> None:
    """Create breakdown of stress test results"""

    st.subheader("Stress Test Breakdown")

    stress_modules = ["deep", "memory", "cpu", "tools", "vision"]

    cols = st.columns(len(stress_modules))

    for i, module in enumerate(stress_modules):
        if module in summary:
            with cols[i]:
                module_data = summary[module]

                if module == "deep":
                    total = module_data.get("total", 0)
                    ok = module_data.get("ok", 0)
                    success_rate = (ok / total * 100) if total > 0 else 0
                    st.metric(
                        "🧠 Deep-LLM", f"{ok}/{total}", f"{success_rate:.1f}% success"
                    )

                elif module == "memory":
                    allocated = module_data.get("allocated_bytes", 0) / (1024**3)
                    st.metric("🎈 Memory", f"{allocated:.1f}GB", "allocated")

                elif module == "cpu":
                    cycles = module_data.get("cycles", 0)
                    st.metric("⚙️ CPU", f"{cycles}", "burn cycles")

                elif module == "tools":
                    sent = module_data.get("sent", 0)
                    ok = module_data.get("ok", 0)
                    success_rate = (ok / sent * 100) if sent > 0 else 0
                    st.metric(
                        "🔨 Tools", f"{ok}/{sent}", f"{success_rate:.1f}% success"
                    )

                elif module == "vision":
                    status = module_data.get("status", "unknown")
                    code = module_data.get("code", 0)
                    status_icon = "✅" if code == 200 else "❌" if code > 0 else "⏭️"
                    st.metric("📹 Vision", f"{status_icon}", status)


def main():
    st.set_page_config(page_title="Loadgen HUD", page_icon="📊", layout="wide")

    st.title("🔥 Alice v2 - Brownout Load Testing HUD")
    st.caption("Real-time visualization of Guardian SLO validation")

    # Command line argument parsing
    if len(sys.argv) > 1 and "--run-dir" in sys.argv:
        idx = sys.argv.index("--run-dir")
        if idx + 1 < len(sys.argv):
            run_dir = pathlib.Path(sys.argv[idx + 1])
        else:
            st.error("Please provide a run directory path")
            return
    else:
        # Default to latest run
        telemetry_dir = pathlib.Path("/data/telemetry")
        if telemetry_dir.exists():
            loadgen_runs = list(telemetry_dir.glob("loadgen_*"))
            if loadgen_runs:
                run_dir = max(loadgen_runs)  # Latest run
            else:
                st.error("No loadgen runs found in /data/telemetry")
                return
        else:
            st.error("Telemetry directory not found: /data/telemetry")
            return

    st.info(f"📁 Analyzing run: {run_dir.name}")

    if not run_dir.exists():
        st.error(f"Run directory not found: {run_dir}")
        return

    # Load data
    events = load_guardian_events(run_dir)
    summary = load_summary(run_dir)
    result = load_result(run_dir)

    if summary is None:
        st.warning("⏳ Test in progress or summary.json not found")
        summary = {}

    # Auto-refresh every 5 seconds
    if st.button("🔄 Refresh") or st.empty():
        st.rerun()

    # Metrics summary
    if summary:
        create_metrics_summary(summary, result)

        st.divider()

        # Timeline chart
        fig = create_timeline_chart(events, summary)
        st.plotly_chart(fig, use_container_width=True)

        st.divider()

        # Stress test breakdown
        create_stress_test_breakdown(summary)

    # Raw data (collapsible)
    with st.expander("🔍 Raw Data"):
        col1, col2 = st.columns(2)

        with col1:
            st.subheader("Guardian Events")
            if events:
                st.json(events[-5:])  # Last 5 events
            else:
                st.info("No guardian events yet")

        with col2:
            st.subheader("Test Summary")
            if summary:
                st.json(summary)
            else:
                st.info("Test summary not available")

    # Auto-refresh timer
    st.sidebar.markdown("### Auto-refresh")
    if st.sidebar.button("Enable auto-refresh (5s)"):
        st.experimental_rerun()


if __name__ == "__main__":
    main()
