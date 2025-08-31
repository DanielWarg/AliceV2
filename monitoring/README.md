# Alice v2 Production HUD

Real-time monitoring dashboard för Alice v2 systemet med Guardian, SLO metrics och test trends.

## Features

**📊 Live System Status:**
- Guardian state (NORMAL/BROWNOUT/EMERGENCY/LOCKDOWN) 
- RAM/CPU usage med SLO-trösklar (80%/92%)
- API online/offline status
- Error budget burn rate (5xx/429 rates)

**📈 Real-time Charts:**
- Guardian state timeline med färgkodning (grön/gul/röd)
- Route latency trends (P50/P95 för micro/planner/deep)
- Error budget tracking över 5-min fönster  
- Request volume gauges

**🧪 Test Results:**
- Success rate trends från nightly validation
- Test scenario performance över tid
- SLO compliance tracking

**🎯 SLO Monitoring:**
- P95 latency vs thresholds (250ms/1.5s/3s)
- Brownout trigger ≤150ms validation
- Recovery time ≤60s tracking
- Production-tight alerting

## Quick Start

```bash
# Starta services
docker compose up -d guardian orchestrator

# Starta HUD
cd monitoring/
./start_hud.sh

# Öppna dashboard
open http://localhost:8501
```

## Data Sources

**Guardian Timeline:**
- `/data/telemetry/YYYY-MM-DD/guardian.jsonl`
- Real-time state transitions med timestamps
- RAM/CPU/temp/battery metrics

**Live Metrics:**
- `http://localhost:8000/api/status/simple` - Route latencies + error budgets
- `http://localhost:8787/health` - Guardian current state

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
- State transitions över tid (grön/gul/röd)
- RAM usage trend med 80%/92% threshold lines
- Brownout/recovery cycles

### 3. Latency Metrics
- P95 latency per route med SLO thresholds
- P50 vs P95 scatter plot
- Error budget burn rate bars
- Request volume gauge

### 4. Test Trends
- Success rate över tid (target: 95%)
- Recent test events
- SLO compliance history

## Auto-refresh

HUD:et refreshar automatiskt var 30s (konfigurerbart 10s-5min).
Cache:as API calls för performance.

## Production Usage

```bash
# Kontinuerlig monitoring
nohup streamlit run alice_hud.py &

# Docker deployment
docker run -p 8501:8501 -v /data:/data alice-hud

# Embedded i ops dashboard
iframe src="http://hud:8501" frameborder="0"
```

Perfect för DevOps-team som vill ha visuell kontroll över Alice v2:s hälsa och performance! 🎯