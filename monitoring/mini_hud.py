import streamlit as st
import json
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from pathlib import Path
import time
from datetime import datetime, timedelta

st.set_page_config(page_title="Alice v2 Mini HUD", layout="wide")
st.title("🤖 Alice v2 Mini HUD")

# Data paths
results_file = Path("data/tests/results.jsonl")
telemetry_dir = Path("data/telemetry")
guardian_files = list(telemetry_dir.glob("*/guardian.jsonl"))

# Load eval results
@st.cache_data(ttl=30)
def load_results():
    if results_file.exists():
        lines = results_file.read_text().strip().split('\n')
        return [json.loads(line) for line in lines if line]
    return []

# Load guardian logs
@st.cache_data(ttl=30)
def load_guardian():
    if guardian_files:
        latest = max(guardian_files, key=lambda x: x.stat().st_mtime)
        lines = latest.read_text().strip().split('\n')
        return [json.loads(line) for line in lines[-100:] if line]
    return []

# Auto-refresh
if st.button("🔄 Refresh") or 'last_refresh' not in st.session_state:
    st.session_state.last_refresh = time.time()
    st.cache_data.clear()

# Main dashboard
col1, col2 = st.columns(2)

with col1:
    st.subheader("📊 Eval Results")
    results = load_results()
    if results:
        df = pd.DataFrame(results)
        total = len(df)
        passed = df['ok'].sum()
        rate = (passed/total)*100 if total > 0 else 0
        
        st.metric("Pass Rate", f"{rate:.1f}%")
        st.metric("Total Tests", total)
        st.metric("Passed", passed)
        
        # Latency chart
        if 'lat_ms' in df.columns:
            fig = px.histogram(df, x='lat_ms', title="Response Latency Distribution")
            st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No eval results yet")

with col2:
    st.subheader("🛡️ Guardian Status")
    guardian_logs = load_guardian()
    if guardian_logs:
        df_guard = pd.DataFrame(guardian_logs)
        latest = df_guard.iloc[-1] if len(df_guard) > 0 else None
        
        if latest is not None:
            st.metric("State", latest.get('state', 'UNKNOWN'))
            st.metric("RAM %", f"{latest.get('ram_pct', 0):.1f}%")
            st.metric("CPU %", f"{latest.get('cpu_pct', 0):.1f}%")
            
            # State timeline
            if 'state' in df_guard.columns:
                state_counts = df_guard['state'].value_counts()
                fig = px.pie(values=state_counts.values, names=state_counts.index, title="Guardian States")
                st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No guardian logs yet")

# Raw data
with st.expander("📋 Raw Data"):
    if results:
        st.dataframe(pd.DataFrame(results))
    if guardian_logs:
        st.dataframe(pd.DataFrame(guardian_logs))

st.caption(f"Last updated: {datetime.now().strftime('%H:%M:%S')}")
