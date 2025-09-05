#!/usr/bin/env python3
"""
Alice Shadow Mode & Self-Awareness Dashboard
Real-time visualization of Alice's dual AI processing and self-learning
"""

import json
from datetime import datetime, timedelta
from pathlib import Path

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

st.set_page_config(
    page_title="🔄 Alice Shadow Mode HUD",
    page_icon="🔄",
    layout="wide",
    initial_sidebar_state="expanded",
)


def load_shadow_events():
    """Load shadow mode evaluation events"""
    events = []
    shadow_dir = Path("data/shadow_eval")

    if not shadow_dir.exists():
        return pd.DataFrame()

    # Load today's and yesterday's events
    for days_back in [0, 1, 2]:
        date = datetime.now() - timedelta(days=days_back)
        file_path = shadow_dir / f"shadow_events_{date.strftime('%Y-%m-%d')}.jsonl"

        if file_path.exists():
            with open(file_path, "r") as f:
                for line in f:
                    try:
                        event = json.loads(line.strip())
                        events.append(event)
                    except (json.JSONDecodeError, KeyError):
                        continue

    if not events:
        return pd.DataFrame()

    # Convert to DataFrame
    df = pd.DataFrame(events)
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    return df


def analyze_self_awareness_metrics(df):
    """Analyze Alice's self-awareness through shadow mode data"""
    if df.empty:
        return {}

    total_comparisons = len(df)
    intent_matches = (
        df["comparison"].apply(lambda x: x.get("intent_match", False)).sum()
    )
    tool_matches = (
        df["comparison"].apply(lambda x: x.get("tool_choice_same", False)).sum()
    )
    schema_ok_both = (
        df["comparison"].apply(lambda x: x.get("schema_ok_both", False)).sum()
    )
    canary_eligible = df["canary_eligible"].sum()
    canary_routed = df["canary_routed"].sum()

    # Latency analysis
    latency_deltas = df["comparison"].apply(lambda x: x.get("latency_delta_ms", 0))
    avg_latency_delta = latency_deltas.mean()

    return {
        "total_comparisons": total_comparisons,
        "intent_accuracy": (
            intent_matches / total_comparisons * 100 if total_comparisons > 0 else 0
        ),
        "tool_consistency": (
            tool_matches / total_comparisons * 100 if total_comparisons > 0 else 0
        ),
        "schema_quality": (
            schema_ok_both / total_comparisons * 100 if total_comparisons > 0 else 0
        ),
        "canary_eligible_rate": (
            canary_eligible / total_comparisons * 100 if total_comparisons > 0 else 0
        ),
        "canary_success_rate": (
            canary_routed / total_comparisons * 100 if total_comparisons > 0 else 0
        ),
        "avg_latency_delta_ms": avg_latency_delta,
        "performance_improvement": (
            "v2 Faster" if avg_latency_delta < 0 else "v1 Faster"
        ),
    }


def plot_self_awareness_timeline(df):
    """Timeline of Alice's self-awareness development"""
    if df.empty:
        return None

    # Group by hour and calculate metrics
    df["hour"] = df["timestamp"].dt.floor("H")
    hourly_metrics = (
        df.groupby("hour")
        .agg(
            {
                "comparison": [
                    lambda x: sum(comp.get("intent_match", False) for comp in x)
                    / len(x)
                    * 100,
                    lambda x: sum(comp.get("tool_choice_same", False) for comp in x)
                    / len(x)
                    * 100,
                    lambda x: sum(comp.get("latency_delta_ms", 0) for comp in x)
                    / len(x),
                ]
            }
        )
        .round(2)
    )

    hourly_metrics.columns = [
        "Intent Match %",
        "Tool Consistency %",
        "Avg Latency Delta ms",
    ]
    hourly_metrics = hourly_metrics.reset_index()

    fig = go.Figure()

    fig.add_trace(
        go.Scatter(
            x=hourly_metrics["hour"],
            y=hourly_metrics["Intent Match %"],
            name="Intent Accuracy",
            line=dict(color="#00ff00", width=3),
        )
    )

    fig.add_trace(
        go.Scatter(
            x=hourly_metrics["hour"],
            y=hourly_metrics["Tool Consistency %"],
            name="Tool Consistency",
            line=dict(color="#0066ff", width=3),
        )
    )

    fig.update_layout(
        title="🧠 Alice Self-Awareness Development Over Time",
        xaxis_title="Time",
        yaxis_title="Accuracy %",
        height=400,
        hovermode="x unified",
    )

    return fig


def plot_planner_comparison(df):
    """Compare planner v1 vs v2 performance"""
    if df.empty:
        return None

    # Extract planner metrics
    planner_data = []
    for _, row in df.iterrows():
        primary = row["primary_result"]
        shadow = row["shadow_result"]

        planner_data.append(
            {
                "Version": "v1 (Primary)",
                "Latency_ms": primary.get("total_time_ms", 0),
                "Tool": primary.get("tool", "none"),
                "Schema_OK": primary.get("schema_ok", False),
                "Session": row["session_id"],
            }
        )

        planner_data.append(
            {
                "Version": "v2 (Shadow)",
                "Latency_ms": shadow.get("total_time_ms", 0),
                "Tool": shadow.get("tool", "none"),
                "Schema_OK": shadow.get("schema_ok", False),
                "Session": row["session_id"],
            }
        )

    planner_df = pd.DataFrame(planner_data)

    fig = px.box(
        planner_df,
        x="Version",
        y="Latency_ms",
        title="⚡ Planner Performance Comparison",
        color="Version",
        points="all",
    )

    fig.update_layout(height=400)
    return fig


# Main Dashboard
st.title("🔄 Alice Shadow Mode & Self-Awareness Dashboard")
st.markdown("**Real-time monitoring of Alice's dual AI processing and learning**")

# Load data
df = load_shadow_events()

if df.empty:
    st.warning(
        "🔍 No shadow mode data found. Make sure shadow mode is enabled and generating data."
    )
    st.code(
        """
    Environment variables needed:
    PLANNER_SHADOW_ENABLED=1
    PLANNER_CANARY_ENABLED=1
    """
    )
else:
    # Calculate metrics
    metrics = analyze_self_awareness_metrics(df)

    # Main metrics row
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric("🧠 Intent Accuracy", f"{metrics['intent_accuracy']:.1f}%")
        st.metric("📊 Total Comparisons", metrics["total_comparisons"])

    with col2:
        st.metric("🔧 Tool Consistency", f"{metrics['tool_consistency']:.1f}%")
        st.metric("✅ Schema Quality", f"{metrics['schema_quality']:.1f}%")

    with col3:
        st.metric("🚀 Canary Eligible", f"{metrics['canary_eligible_rate']:.1f}%")
        st.metric("🎯 Canary Success", f"{metrics['canary_success_rate']:.1f}%")

    with col4:
        delta_color = "inverse" if metrics["avg_latency_delta_ms"] < 0 else "normal"
        st.metric(
            "⚡ Latency Delta",
            f"{metrics['avg_latency_delta_ms']:.2f}ms",
            delta=metrics["performance_improvement"],
            delta_color=delta_color,
        )

    st.markdown("---")

    # Charts
    col1, col2 = st.columns(2)

    with col1:
        timeline_fig = plot_self_awareness_timeline(df)
        if timeline_fig:
            st.plotly_chart(timeline_fig, use_container_width=True)

    with col2:
        comparison_fig = plot_planner_comparison(df)
        if comparison_fig:
            st.plotly_chart(comparison_fig, use_container_width=True)

    # Self-awareness insights
    st.markdown("---")
    st.subheader("🤖 Alice's Self-Awareness Insights")

    if metrics["intent_accuracy"] > 95:
        st.success("🎯 Alice shows excellent self-consistency in intent recognition!")
    elif metrics["intent_accuracy"] > 85:
        st.info("🔄 Alice is developing good self-awareness with room for improvement")
    else:
        st.warning(
            "⚠️ Alice's dual processing shows significant variations - learning in progress"
        )

    if metrics["avg_latency_delta_ms"] < -10:
        st.success("🚀 Shadow planner (v2) is consistently faster than primary (v1)")
    elif abs(metrics["avg_latency_delta_ms"]) < 10:
        st.info("⚖️ Both planners show similar performance")
    else:
        st.warning("🐌 Shadow planner (v2) is slower than primary (v1)")

    # Recent events table
    st.markdown("---")
    st.subheader("📋 Recent Shadow Mode Events")

    if len(df) > 0:
        recent_df = df.tail(10)[
            ["timestamp", "session_id", "canary_eligible", "canary_routed"]
        ].copy()
        recent_df["comparison_summary"] = df.tail(10)["comparison"].apply(
            lambda x: f"Intent: {x.get('intent_match', False)}, Tool: {x.get('tool_choice_same', False)}, Δ: {x.get('latency_delta_ms', 0):.1f}ms"
        )
        st.dataframe(recent_df, use_container_width=True)

    # Configuration status
    st.sidebar.header("🔧 Configuration")
    st.sidebar.info(
        f"""
    **Shadow Mode Status**: ✅ Active
    **Data Points**: {len(df)}
    **Time Range**: {df['timestamp'].min().strftime('%Y-%m-%d %H:%M') if not df.empty else 'N/A'} to {df['timestamp'].max().strftime('%Y-%m-%d %H:%M') if not df.empty else 'N/A'}
    """
    )

    # Auto-refresh
    if st.sidebar.button("🔄 Refresh Data"):
        st.rerun()

    if st.sidebar.checkbox("Auto-refresh (10s)", value=False):
        st.rerun()

# Footer
st.markdown("---")
st.markdown(
    "**🔄 Shadow Mode Dashboard** - Monitoring Alice's self-awareness and dual AI processing capabilities"
)
