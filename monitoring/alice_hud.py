#!/usr/bin/env python3
"""
Alice v2 Production HUD - Real-time system monitoring
====================================================

Streamlit dashboard reading:
- Guardian JSONL logs (/data/telemetry/YYYY-MM-DD/guardian.jsonl)
- Live status API (P50/P95, error budgets, Guardian state)
- Test results (/data/tests/results.jsonl)

Shows:
- Guardian state timeline (GREEN/YELLOW/RED)
- Route latency trends (P50/P95 per micro/planner/deep)
- Error budget burn rate
- SLO compliance over time
- Test success rates

Usage: streamlit run alice_hud.py
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import json
import pathlib
import requests
import time
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional

# Configuration
st.set_page_config(
    page_title="Alice v2 HUD",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded"
)

# API endpoints
ORCHESTRATOR_BASE = "http://localhost:8000"
GUARDIAN_BASE = "http://localhost:8787"
TELEMETRY_DIR = pathlib.Path("/data/telemetry")
TEST_RESULTS_DIR = pathlib.Path("/data/tests")

# SLO thresholds
SLO_THRESHOLDS = {
    "fast_p95_ms": 250,
    "planner_p95_ms": 1500, 
    "deep_p95_ms": 3000,
    "error_budget_5xx": 0.01,  # 1% 5xx rate
    "error_budget_429": 0.05,  # 5% 429 rate
    "brownout_trigger_ms": 150,
    "recovery_time_s": 60
}

# Color scheme
COLORS = {
    "NORMAL": "#28a745",      # Green
    "BROWNOUT": "#ffc107",    # Yellow  
    "EMERGENCY": "#dc3545",   # Red
    "LOCKDOWN": "#6f42c1",    # Purple
    "unknown": "#6c757d"      # Gray
}

@st.cache_data(ttl=30)  # Cache for 30 seconds
def load_guardian_timeline(hours_back: int = 24) -> pd.DataFrame:
    """Load Guardian state timeline from JSONL logs"""
    timeline_data = []
    
    # Load last N days of logs
    for days_ago in range(hours_back // 24 + 1):
        date = (datetime.now() - timedelta(days=days_ago)).strftime("%Y-%m-%d")
        log_file = TELEMETRY_DIR / date / "guardian.jsonl"
        
        if log_file.exists():
            with open(log_file, 'r') as f:
                for line in f:
                    try:
                        event = json.loads(line.strip())
                        if 'ts' in event:
                            event['timestamp'] = pd.to_datetime(event['ts'])
                            timeline_data.append(event)
                    except (json.JSONDecodeError, KeyError):
                        continue
    
    if not timeline_data:
        return pd.DataFrame()
    
    df = pd.DataFrame(timeline_data)
    
    # Filter to recent hours
    cutoff = datetime.now() - timedelta(hours=hours_back)
    df = df[df['timestamp'] >= cutoff].sort_values('timestamp')
    
    return df

@st.cache_data(ttl=10)  # Cache for 10 seconds
def get_live_status() -> Dict[str, Any]:
    """Get current system status from APIs"""
    try:
        # Get orchestrator status
        response = requests.get(f"{ORCHESTRATOR_BASE}/api/status/simple", timeout=5)
        if response.status_code == 200:
            return response.json()
    except requests.RequestException:
        pass
    
    return {"ok": False, "error": "API unavailable"}

@st.cache_data(ttl=10)
def get_guardian_status() -> Dict[str, Any]:
    """Get current Guardian status"""
    try:
        response = requests.get(f"{GUARDIAN_BASE}/health", timeout=5)
        if response.status_code == 200:
            return response.json()
    except requests.RequestException:
        pass
    
    return {"state": "unknown", "error": "Guardian unavailable"}

@st.cache_data(ttl=60)  # Cache for 1 minute
def load_test_results(hours_back: int = 168) -> pd.DataFrame:
    """Load test results from JSONL logs"""
    results_file = TEST_RESULTS_DIR / "results.jsonl"
    
    if not results_file.exists():
        return pd.DataFrame()
    
    results = []
    cutoff = datetime.now() - timedelta(hours=hours_back)
    
    with open(results_file, 'r') as f:
        for line in f:
            try:
                result = json.loads(line.strip())
                if 'timestamp' in result:
                    timestamp = pd.to_datetime(result['timestamp'])
                    if timestamp >= cutoff:
                        results.append(result)
            except (json.JSONDecodeError, KeyError):
                continue
    
    return pd.DataFrame(results) if results else pd.DataFrame()

def create_guardian_timeline_chart(df: pd.DataFrame) -> go.Figure:
    """Create Guardian state timeline chart"""
    fig = go.Figure()
    
    if df.empty:
        fig.add_annotation(
            text="No Guardian timeline data available",
            xref="paper", yref="paper", x=0.5, y=0.5,
            showarrow=False, font=dict(size=16, color="gray")
        )
        return fig
    
    # State timeline
    for state in df['state'].unique():
        state_data = df[df['state'] == state]
        fig.add_trace(go.Scatter(
            x=state_data['timestamp'],
            y=state_data.get('ram_pct', 0),
            mode='markers+lines',
            name=f'Guardian {state}',
            marker=dict(
                color=COLORS.get(state, COLORS['unknown']),
                size=8
            ),
            line=dict(color=COLORS.get(state, COLORS['unknown'])),
            hovertemplate='<b>%{fullData.name}</b><br>' +
                         'Time: %{x}<br>' +
                         'RAM: %{y:.1f}%<br>' +
                         '<extra></extra>'
        ))
    
    # Add SLO threshold lines
    fig.add_hline(y=80, line_dash="dash", line_color="orange", 
                  annotation_text="RAM Soft (80%)")
    fig.add_hline(y=92, line_dash="dash", line_color="red",
                  annotation_text="RAM Hard (92%)")
    
    fig.update_layout(
        title="Guardian State Timeline",
        xaxis_title="Time",
        yaxis_title="RAM Usage (%)",
        showlegend=True,
        height=400
    )
    
    return fig

def create_latency_chart(status_data: Dict[str, Any]) -> go.Figure:
    """Create route latency chart"""
    fig = make_subplots(
        rows=2, cols=2,
        subplot_titles=('P95 Latency by Route', 'P50 vs P95', 
                       'Error Budget', 'Request Volume'),
        specs=[[{"secondary_y": False}, {"secondary_y": False}],
               [{"secondary_y": False}, {"secondary_y": False}]]
    )
    
    if not status_data.get("ok"):
        fig.add_annotation(
            text="Status API unavailable",
            xref="paper", yref="paper", x=0.5, y=0.5,
            showarrow=False, font=dict(size=16, color="red")
        )
        return fig
    
    routes = status_data.get("metrics", {}).get("routes", {})
    
    # P95 Latency by Route
    route_names = []
    p95_values = []
    p50_values = []
    thresholds = []
    
    for route_name, route_data in routes.items():
        if route_data.get("count", 0) > 0:
            route_names.append(route_name)
            p95_values.append(route_data.get("p95_ms", 0))
            p50_values.append(route_data.get("p50_ms", 0))
            
            # Get SLO threshold for this route
            threshold = SLO_THRESHOLDS.get(f"{route_name}_p95_ms", 1000)
            thresholds.append(threshold)
    
    if route_names:
        # P95 bars
        fig.add_trace(
            go.Bar(x=route_names, y=p95_values, name="P95", 
                   marker_color="lightcoral"),
            row=1, col=1
        )
        
        # SLO thresholds
        fig.add_trace(
            go.Scatter(x=route_names, y=thresholds, 
                      mode='markers', name="SLO Threshold",
                      marker=dict(color="red", symbol="line-ew", size=15)),
            row=1, col=1
        )
        
        # P50 vs P95 scatter
        fig.add_trace(
            go.Scatter(x=p50_values, y=p95_values, 
                      mode='markers+text', text=route_names,
                      name="Routes", marker=dict(size=12)),
            row=1, col=2
        )
    
    # Error budget
    error_budget = status_data.get("metrics", {}).get("error_budget", {})
    r5xx_rate = error_budget.get("r5xx_rate", 0) * 100  # Convert to %
    r429_rate = error_budget.get("r429_rate", 0) * 100
    
    fig.add_trace(
        go.Bar(x=["5xx Errors", "429 Rate Limits"], 
               y=[r5xx_rate, r429_rate],
               name="Error %", marker_color=["red", "orange"]),
        row=2, col=1
    )
    
    # Request volume
    total_requests = error_budget.get("total", 0)
    fig.add_trace(
        go.Indicator(
            mode="gauge+number",
            value=total_requests,
            title={'text': "Requests (5min)"},
            gauge={'axis': {'range': [0, max(100, total_requests * 1.2)]},
                   'bar': {'color': "lightblue"},
                   'steps': [{'range': [0, total_requests], 'color': "lightgray"}]}
        ),
        row=2, col=2
    )
    
    fig.update_layout(height=600, showlegend=True)
    return fig

def create_metrics_cards():
    """Create metrics summary cards"""
    status = get_live_status()
    guardian = get_guardian_status()
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        # Guardian Status
        state = guardian.get("state", "unknown")
        state_color = COLORS.get(state, COLORS["unknown"])
        
        st.markdown(f"""
        <div style="padding: 1rem; border-radius: 0.5rem; background: {state_color}20; border: 2px solid {state_color};">
            <h3 style="margin: 0; color: {state_color};">🛡️ Guardian</h3>
            <h2 style="margin: 0; color: {state_color};">{state}</h2>
            <p style="margin: 0; color: {state_color};">
                Since: {guardian.get('since_s', 0):.1f}s
            </p>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        # RAM Status
        ram_pct = guardian.get("ram_pct", 0)
        ram_color = "red" if ram_pct >= 92 else "orange" if ram_pct >= 80 else "green"
        
        st.markdown(f"""
        <div style="padding: 1rem; border-radius: 0.5rem; background: {ram_color}20; border: 2px solid {ram_color};">
            <h3 style="margin: 0; color: {ram_color};">💾 RAM</h3>
            <h2 style="margin: 0; color: {ram_color};">{ram_pct:.1f}%</h2>
            <p style="margin: 0; color: {ram_color};">
                Soft: 80% | Hard: 92%
            </p>
        </div>
        """, unsafe_allow_html=True)
    
    with col3:
        # API Status
        api_ok = status.get("ok", False)
        api_color = "green" if api_ok else "red"
        api_status = "ONLINE" if api_ok else "OFFLINE"
        
        st.markdown(f"""
        <div style="padding: 1rem; border-radius: 0.5rem; background: {api_color}20; border: 2px solid {api_color};">
            <h3 style="margin: 0; color: {api_color};">🚀 API</h3>
            <h2 style="margin: 0; color: {api_color};">{api_status}</h2>
            <p style="margin: 0; color: {api_color};">
                Status endpoint
            </p>
        </div>
        """, unsafe_allow_html=True)
    
    with col4:
        # Error Budget
        if status.get("ok"):
            error_budget = status.get("metrics", {}).get("error_budget", {})
            r5xx_rate = error_budget.get("r5xx_rate", 0) * 100
            
            budget_color = "red" if r5xx_rate > 1 else "orange" if r5xx_rate > 0.5 else "green"
            
            st.markdown(f"""
            <div style="padding: 1rem; border-radius: 0.5rem; background: {budget_color}20; border: 2px solid {budget_color};">
                <h3 style="margin: 0; color: {budget_color};">📊 Errors</h3>
                <h2 style="margin: 0; color: {budget_color};">{r5xx_rate:.2f}%</h2>
                <p style="margin: 0; color: {budget_color};">
                    5xx error rate
                </p>
            </div>
            """, unsafe_allow_html=True)
        else:
            st.markdown("""
            <div style="padding: 1rem; border-radius: 0.5rem; background: gray20; border: 2px solid gray;">
                <h3 style="margin: 0; color: gray;">📊 Errors</h3>
                <h2 style="margin: 0; color: gray;">N/A</h2>
                <p style="margin: 0; color: gray;">API offline</p>
            </div>
            """, unsafe_allow_html=True)

def main():
    st.title("🤖 Alice v2 Production HUD")
    st.caption("Real-time monitoring of Guardian, SLO metrics, and system health")
    
    # Auto-refresh
    if st.sidebar.button("🔄 Refresh", use_container_width=True):
        st.cache_data.clear()
        st.rerun()
    
    # Auto-refresh interval
    refresh_interval = st.sidebar.selectbox(
        "Auto-refresh interval",
        [10, 30, 60, 300],
        index=1,
        format_func=lambda x: f"{x}s"
    )
    
    # Time range selector
    hours_back = st.sidebar.selectbox(
        "Time range",
        [1, 4, 12, 24, 48, 168],
        index=3,
        format_func=lambda x: f"{x}h" if x < 168 else "7 days"
    )
    
    # Metrics cards
    create_metrics_cards()
    
    st.divider()
    
    # Main charts
    col1, col2 = st.columns([2, 1])
    
    with col1:
        # Guardian timeline
        guardian_df = load_guardian_timeline(hours_back)
        guardian_chart = create_guardian_timeline_chart(guardian_df)
        st.plotly_chart(guardian_chart, use_container_width=True)
        
        # Latency and error metrics
        status = get_live_status()
        latency_chart = create_latency_chart(status)
        st.plotly_chart(latency_chart, use_container_width=True)
    
    with col2:
        # System info
        st.subheader("📋 System Info")
        guardian = get_guardian_status()
        
        if guardian.get("state") != "unknown":
            st.json({
                "guardian_state": guardian.get("state"),
                "brownout_level": guardian.get("brownout_level"),
                "reason": guardian.get("reason"),
                "ram_pct": guardian.get("ram_pct"),
                "cpu_pct": guardian.get("cpu_pct"),
                "temp_c": guardian.get("temp_c"),
                "battery_pct": guardian.get("battery_pct")
            })
        else:
            st.error("Guardian unavailable")
        
        # Recent events
        st.subheader("⚡ Recent Events")
        if not guardian_df.empty:
            recent = guardian_df.tail(5)[['timestamp', 'state', 'reason', 'ram_pct']]
            recent['timestamp'] = recent['timestamp'].dt.strftime('%H:%M:%S')
            st.dataframe(recent, use_container_width=True)
        else:
            st.info("No recent events")
    
    # Test results section
    st.divider()
    st.subheader("🧪 Test Results Trend")
    
    test_df = load_test_results(hours_back)
    if not test_df.empty:
        # Success rate over time
        fig_tests = go.Figure()
        
        test_df['timestamp'] = pd.to_datetime(test_df['timestamp'])
        test_df['success_rate'] = test_df.get('success_rate', 0) * 100
        
        fig_tests.add_trace(go.Scatter(
            x=test_df['timestamp'],
            y=test_df['success_rate'],
            mode='lines+markers',
            name='Success Rate %',
            line=dict(color='green')
        ))
        
        fig_tests.add_hline(y=95, line_dash="dash", line_color="orange",
                           annotation_text="Target: 95%")
        
        fig_tests.update_layout(
            title="Test Success Rate Over Time",
            xaxis_title="Time",
            yaxis_title="Success Rate (%)",
            height=300
        )
        
        st.plotly_chart(fig_tests, use_container_width=True)
    else:
        st.info("No test results available")
    
    # Footer
    st.divider()
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.caption("🔗 [Status API](http://localhost:8000/api/status/simple)")
    with col2:
        st.caption("🛡️ [Guardian](http://localhost:8787/health)")
    with col3:
        st.caption(f"📊 Last updated: {datetime.now().strftime('%H:%M:%S')}")
    
    # Auto-refresh
    time.sleep(refresh_interval)
    st.rerun()

if __name__ == "__main__":
    main()