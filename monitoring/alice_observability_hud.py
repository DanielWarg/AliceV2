#!/usr/bin/env python3
"""
Alice v2 Observability HUD
Comprehensive dashboard för RAM peak, energy, tool errors, och SLO monitoring
"""

import streamlit as st
import pandas as pd
import json
import os
import time
from datetime import datetime, timedelta
import plotly.graph_objects as go
import plotly.express as px
from typing import Dict, List, Any
import requests

# Page config
st.set_page_config(
    page_title="Alice v2 Observability HUD",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
<style>
    .metric-card {
        background-color: #f0f2f6;
        padding: 1rem;
        border-radius: 0.5rem;
        border-left: 4px solid #1f77b4;
    }
    .status-normal { color: #28a745; }
    .status-brownout { color: #ffc107; }
    .status-emergency { color: #dc3545; }
</style>
""", unsafe_allow_html=True)

def load_jsonl_data(filename: str) -> List[Dict[str, Any]]:
    """Ladda data från JSONL fil"""
    data = []
    if os.path.exists(filename):
        with open(filename, 'r', encoding='utf-8') as f:
            for line in f:
                try:
                    data.append(json.loads(line.strip()))
                except json.JSONDecodeError:
                    continue
    return data

def get_guardian_status() -> Dict[str, Any]:
    """Hämta Guardian status"""
    try:
        response = requests.get("http://localhost:8787/health", timeout=5)
        if response.status_code == 200:
            return response.json()
        else:
            return {"state": "ERROR", "error": f"HTTP {response.status_code}"}
    except Exception as e:
        return {"state": "ERROR", "error": str(e)}

def get_orchestrator_status() -> Dict[str, Any]:
    """Hämta Orchestrator status"""
    try:
        response = requests.get("http://localhost:8000/api/status/simple", timeout=5)
        if response.status_code == 200:
            return response.json()
        else:
            return {"status": "ERROR", "error": f"HTTP {response.status_code}"}
    except Exception as e:
        return {"status": "ERROR", "error": str(e)}

def create_ram_peak_chart(events_data: List[Dict[str, Any]]) -> go.Figure:
    """Skapa RAM peak chart"""
    if not events_data:
        return go.Figure().add_annotation(text="Ingen data tillgänglig", x=0.5, y=0.5)
    
    df = pd.DataFrame([
        {
            'timestamp': event.get('ts', ''),
            'proc_mb': event.get('ram_peak_mb', {}).get('proc_mb', 0),
            'sys_mb': event.get('ram_peak_mb', {}).get('sys_mb', 0)
        }
        for event in events_data
        if 'ram_peak_mb' in event
    ])
    
    if df.empty:
        return go.Figure().add_annotation(text="Ingen RAM data", x=0.5, y=0.5)
    
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    df = df.sort_values('timestamp')
    
    fig = go.Figure()
    
    fig.add_trace(go.Scatter(
        x=df['timestamp'],
        y=df['proc_mb'],
        mode='lines+markers',
        name='Process RAM (MB)',
        line=dict(color='#1f77b4', width=2),
        marker=dict(size=6)
    ))
    
    fig.add_trace(go.Scatter(
        x=df['timestamp'],
        y=df['sys_mb'],
        mode='lines+markers',
        name='System RAM (MB)',
        line=dict(color='#ff7f0e', width=2),
        marker=dict(size=6)
    ))
    
    fig.update_layout(
        title="RAM Peak per Turn",
        xaxis_title="Tid",
        yaxis_title="RAM (MB)",
        height=400,
        showlegend=True
    )
    
    return fig

def create_energy_chart(events_data: List[Dict[str, Any]]) -> go.Figure:
    """Skapa energy consumption chart"""
    if not events_data:
        return go.Figure().add_annotation(text="Ingen data tillgänglig", x=0.5, y=0.5)
    
    df = pd.DataFrame([
        {
            'timestamp': event.get('ts', ''),
            'energy_wh': event.get('energy_wh', 0)
        }
        for event in events_data
        if 'energy_wh' in event
    ])
    
    if df.empty:
        return go.Figure().add_annotation(text="Ingen energy data", x=0.5, y=0.5)
    
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    df = df.sort_values('timestamp')
    
    fig = go.Figure()
    
    fig.add_trace(go.Scatter(
        x=df['timestamp'],
        y=df['energy_wh'],
        mode='lines+markers',
        name='Energy (Wh)',
        line=dict(color='#2ca02c', width=2),
        marker=dict(size=6)
    ))
    
    fig.update_layout(
        title="Energy Consumption per Turn",
        xaxis_title="Tid",
        yaxis_title="Energy (Wh)",
        height=400,
        showlegend=True
    )
    
    return fig

def create_tool_errors_chart(events_data: List[Dict[str, Any]]) -> go.Figure:
    """Skapa tool errors chart"""
    if not events_data:
        return go.Figure().add_annotation(text="Ingen data tillgänglig", x=0.5, y=0.5)
    
    # Samla tool errors
    error_counts = {}
    for event in events_data:
        if 'tool_calls' in event:
            for tool_call in event['tool_calls']:
                if not tool_call.get('ok', True):
                    error_class = tool_call.get('klass', 'unknown')
                    error_counts[error_class] = error_counts.get(error_class, 0) + 1
    
    if not error_counts:
        return go.Figure().add_annotation(text="Inga tool errors", x=0.5, y=0.5)
    
    fig = go.Figure(data=[
        go.Bar(
            x=list(error_counts.keys()),
            y=list(error_counts.values()),
            marker_color=['#d62728', '#ff7f0e', '#2ca02c', '#9467bd', '#8c564b']
        )
    ])
    
    fig.update_layout(
        title="Tool Errors by Class",
        xaxis_title="Error Class",
        yaxis_title="Count",
        height=400
    )
    
    return fig

def create_latency_chart(events_data: List[Dict[str, Any]]) -> go.Figure:
    """Skapa latency chart per route"""
    if not events_data:
        return go.Figure().add_annotation(text="Ingen data tillgänglig", x=0.5, y=0.5)
    
    df = pd.DataFrame([
        {
            'timestamp': event.get('ts', ''),
            'route': event.get('route', 'unknown'),
            'e2e_full_ms': event.get('e2e_full_ms', 0)
        }
        for event in events_data
        if 'e2e_full_ms' in event
    ])
    
    if df.empty:
        return go.Figure().add_annotation(text="Ingen latency data", x=0.5, y=0.5)
    
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    df = df.sort_values('timestamp')
    
    fig = go.Figure()
    
    colors = {'micro': '#1f77b4', 'planner': '#ff7f0e', 'deep': '#2ca02c'}
    
    for route in df['route'].unique():
        route_data = df[df['route'] == route]
        fig.add_trace(go.Scatter(
            x=route_data['timestamp'],
            y=route_data['e2e_full_ms'],
            mode='lines+markers',
            name=f'{route} (ms)',
            line=dict(color=colors.get(route, '#9467bd'), width=2),
            marker=dict(size=6)
        ))
    
    fig.update_layout(
        title="Latency per Route",
        xaxis_title="Tid",
        yaxis_title="Latency (ms)",
        height=400,
        showlegend=True
    )
    
    return fig

def main():
    st.title("🤖 Alice v2 Observability HUD")
    st.markdown("Real-time monitoring av RAM peak, energy, tool errors och SLO compliance")
    
    # Sidebar för konfiguration
    st.sidebar.header("Konfiguration")
    
    # Auto-refresh
    auto_refresh = st.sidebar.checkbox("Auto-refresh (30s)", value=True)
    if auto_refresh:
        time.sleep(1)  # Liten paus för refresh
        st.rerun()
    
    # Data sources
    st.sidebar.subheader("Data Sources")
    events_file = st.sidebar.text_input(
        "Events JSONL file",
        value="data/telemetry/events_2025-08-31.jsonl"
    )
    
    guardian_file = st.sidebar.text_input(
        "Guardian JSONL file", 
        value="data/telemetry/guardian_2025-08-31.jsonl"
    )
    
    # Ladda data
    events_data = load_jsonl_data(events_file)
    guardian_data = load_jsonl_data(guardian_file)
    
    # Status row
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        guardian_status = get_guardian_status()
        state = guardian_status.get('state', 'UNKNOWN')
        
        if state == 'NORMAL':
            status_color = 'status-normal'
            status_icon = '🟢'
        elif state == 'BROWNOUT':
            status_color = 'status-brownout'
            status_icon = '🟡'
        else:
            status_color = 'status-emergency'
            status_icon = '🔴'
        
        st.metric(
            label="Guardian Status",
            value=f"{status_icon} {state}",
            delta=None
        )
    
    with col2:
        orchestrator_status = get_orchestrator_status()
        status = orchestrator_status.get('status', 'UNKNOWN')
        st.metric(
            label="Orchestrator Status",
            value=f"🟢 {status}" if status == 'healthy' else f"🔴 {status}",
            delta=None
        )
    
    with col3:
        if events_data:
            latest_event = events_data[-1]
            ram_peak = latest_event.get('ram_peak_mb', {})
            proc_mb = ram_peak.get('proc_mb', 0)
            st.metric(
                label="Latest RAM Peak",
                value=f"{proc_mb:.1f} MB",
                delta=None
            )
        else:
            st.metric(label="Latest RAM Peak", value="N/A", delta=None)
    
    with col4:
        if events_data:
            latest_event = events_data[-1]
            energy_wh = latest_event.get('energy_wh', 0)
            st.metric(
                label="Latest Energy",
                value=f"{energy_wh:.4f} Wh",
                delta=None
            )
        else:
            st.metric(label="Latest Energy", value="N/A", delta=None)
    
    # Charts row 1
    st.subheader("📊 Performance Metrics")
    
    col1, col2 = st.columns(2)
    
    with col1:
        ram_fig = create_ram_peak_chart(events_data)
        st.plotly_chart(ram_fig, use_container_width=True)
    
    with col2:
        energy_fig = create_energy_chart(events_data)
        st.plotly_chart(energy_fig, use_container_width=True)
    
    # Charts row 2
    col1, col2 = st.columns(2)
    
    with col1:
        latency_fig = create_latency_chart(events_data)
        st.plotly_chart(latency_fig, use_container_width=True)
    
    with col2:
        errors_fig = create_tool_errors_chart(events_data)
        st.plotly_chart(errors_fig, use_container_width=True)
    
    # SLO Compliance
    st.subheader("🎯 SLO Compliance")
    
    if events_data:
        # Beräkna SLO metrics
        micro_latencies = [
            event['e2e_full_ms'] 
            for event in events_data 
            if event.get('route') == 'micro'
        ]
        planner_latencies = [
            event['e2e_full_ms'] 
            for event in events_data 
            if event.get('route') == 'planner'
        ]
        deep_latencies = [
            event['e2e_full_ms'] 
            for event in events_data 
            if event.get('route') == 'deep'
        ]
        
        def p95(values):
            if not values:
                return 0
            sorted_values = sorted(values)
            index = int(len(sorted_values) * 0.95)
            return sorted_values[index]
        
        p95_micro = p95(micro_latencies)
        p95_planner = p95(planner_latencies)
        p95_deep = p95(deep_latencies)
        
        # SLO thresholds
        slo_micro = p95_micro <= 250
        slo_planner = p95_planner <= 1500
        slo_deep = p95_deep <= 3000
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric(
                label="Micro P95",
                value=f"{p95_micro} ms",
                delta="✅ Pass" if slo_micro else "❌ Fail",
                delta_color="normal" if slo_micro else "inverse"
            )
        
        with col2:
            st.metric(
                label="Planner P95",
                value=f"{p95_planner} ms",
                delta="✅ Pass" if slo_planner else "❌ Fail",
                delta_color="normal" if slo_planner else "inverse"
            )
        
        with col3:
            st.metric(
                label="Deep P95",
                value=f"{p95_deep} ms",
                delta="✅ Pass" if slo_deep else "❌ Fail",
                delta_color="normal" if slo_deep else "inverse"
            )
    
    # Raw data
    st.subheader("📋 Raw Data")
    
    if events_data:
        # Visa senaste events
        recent_events = events_data[-10:]  # Senaste 10
        
        for event in recent_events:
            with st.expander(f"Event {event.get('ts', 'unknown')} - {event.get('route', 'unknown')}"):
                st.json(event)
    else:
        st.info("Ingen events data tillgänglig")
    
    # Footer
    st.markdown("---")
    st.markdown(
        f"*HUD uppdaterad: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | "
        f"Events: {len(events_data)} | Guardian records: {len(guardian_data)}*"
    )

if __name__ == "__main__":
    main()
