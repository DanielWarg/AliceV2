# Alice v2 Load Generator

Real brownout testing for Guardian SLO validation. Measures trigger latency (≤150ms) and recovery time (≤60s).

## Quick Start

```bash
# Build and run loadgen
docker compose build loadgen
docker compose run --rm loadgen

# View results
cat data/telemetry/loadgen_*/result.txt        # PASS/FAIL
cat data/telemetry/loadgen_*/summary.json      # Detailed data

# Start HUD for visual monitoring
./run_hud.sh                                   # Latest run
./run_hud.sh /data/telemetry/loadgen_XYZ       # Specific run
```

## Components

**Stressors (burners/):**

- `deep_bomb.py` - Heavy Swedish prompts to Deep-LLM
- `memory_balloon.py` - Gradual RAM allocation (4GB default)
- `cpu_spin.py` - Controlled CPU pulses
- `tool_storm.py` - Planner + calendar/email tools
- `vision_stress.py` - RTSP camera requests if available

**Monitoring:**

- `watchers.py` - Measures Guardian brownout trigger/recovery
- `hud.py` - Streamlit dashboard with real-time visualization

## Security

- Emergency state (>10s) automatically interrupts load
- MAX_TEMP_C/MAX_BATTERY_PCT safety valves
- Gradual memory allocation, not "brutal allocation"
- Respectful timeouts and controlled intervals

## Environment Variables

```bash
API_BASE=http://orchestrator:8000
GUARD_HEALTH=http://orchestrator:8000/guardian/health
SLO_BROWNOUT_TRIGGER_MS=150    # Brownout trigger budget
RECOVER_S=60                   # Recovery time budget
MEMORY_BALLOON_GB=4            # RAM stress target
CPU_THREADS=4                  # CPU stress threads
DEEP_CONCURRENCY=2             # Deep-LLM parallelism
CAMERA_RTSP_URL=               # RTSP camera URL (optional)
```

## Expected Results

✅ **PASS Criteria:**

- Brownout trigger: ≤150ms after RAM >90%
- Recovery: ≤60s after load release
- Guardian: NORMAL→BROWNOUT→NORMAL cycle

❌ **FAIL Criteria:**

- Trigger >150ms or no brownout
- Recovery >60s or stuck in EMERGENCY
- System crash or unhandled errors

## HUD Dashboard

Streamlit dashboard shows:

- **Real-time timeline** with Guardian state transitions
- **SLO metrics** with PASS/FAIL status against budgets
- **Stress test breakdown** for all modules
- **Auto-refresh** every 5s during test

Dashboard: `http://localhost:8501` after `./run_hud.sh`
