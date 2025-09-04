# Alice v2 Production HUD

Real-time monitoring dashboard for the Alice v2 system with Guardian, SLO metrics, and test trends.

## Features

**📊 Live System Status:**

- Guardian state (NORMAL/BROWNOUT/EMERGENCY/LOCKDOWN)
- RAM/CPU usage with SLO thresholds (80%/92%)
- API online/offline status
- Error budget burn rate (5xx/429 rates)

**📈 Real-time Charts:**

- Guardian state timeline with color coding (green/yellow/red)
- Route latency trends (P50/P95 for micro/planner/deep)
- Error budget tracking over 5-minute windows
- Request volume gauges

**🧪 Test Results:**

- Success rate trends from nightly validation
- Test scenario performance over time
- SLO compliance tracking

**🎯 SLO Monitoring:**

- P95 latency vs thresholds (250ms/1.5s/3s)
- Brownout trigger ≤150ms validation
- Recovery time ≤60s tracking
- Production-tight alerting

## Quick Start

```bash
# Start services
docker compose up -d guardian orchestrator

# Start HUD
cd monitoring/
./start_hud.sh

# Open dashboard
open http://localhost:8501
```

## Data Sources

**Guardian Timeline:**

- `/data/telemetry/YYYY-MM-DD/guardian.jsonl`
- Real-time state transitions with timestamps
- RAM/CPU/temp/battery metrics

**Live Metrics via dev-proxy (18000):**

- `http://localhost:18000/api/status/simple` - Route latencies + error budgets
- `http://localhost:18000/api/status/routes` - P50/P95 per route (requires X-Route in /api/chat)
- `http://localhost:18000/metrics` - Prometheus exporter
- `http://localhost:18000/guardian` - Guardian health proxy

**Test Results:**

- `/data/tests/results.jsonl` - Nightly validation outcomes
- Success rates, scenario performance, SLO compliance

## Dashboard Sections

### 1. Status Cards

- 🛡️ Guardian (current state + duration)
- 💾 RAM (usage % with soft/hard thresholds)
- 🚀 API (online/offline status)
- 📊 Errors (5xx rate percentage)

### 2. Guardian Timeline

- State transitions over time (green/yellow/red)
- RAM usage trend with 80%/92% threshold lines
- Brownout/recovery cycles

### 3. Latency Metrics

- P95 latency per route med SLO thresholds
- P50 vs P95 scatter plot
- Error budget burn rate bars
- Request volume gauge

### 4. Test Trends

- Success rate over time (target: 95%)
- Recent test events
- SLO compliance history

## Auto-refresh

The HUD refreshes automatically every 30s (configurable 10s-5min).
API calls are cached for performance.

## Production Usage

```bash
# Continuous monitoring
nohup streamlit run alice_hud.py &

# Docker deployment
docker run -p 8501:8501 -v /data:/data alice-hud

# Embedded in ops dashboard
iframe src="http://hud:8501" frameborder="0"
```

Perfect för DevOps-team som vill ha visuell kontroll över Alice v2:s hälsa och performance! 🎯
