# Alice v2 Load Generator

Real brownout testing för Guardian SLO-validering. Mäter trigger-latency (≤150ms) och recovery-tid (≤60s).

## Quick Start

```bash
# Bygg och kör loadgen
docker compose build loadgen  
docker compose run --rm loadgen

# Visa resultat
cat data/telemetry/loadgen_*/result.txt        # PASS/FAIL
cat data/telemetry/loadgen_*/summary.json      # Detaljerad data

# Starta HUD för visuell monitoring
./run_hud.sh                                   # Senaste körning
./run_hud.sh /data/telemetry/loadgen_XYZ       # Specifik körning
```

## Komponenter

**Stressors (burners/):**
- `deep_bomb.py` - Tunga svenska prompts till Deep-LLM
- `memory_balloon.py` - Gradvis RAM-allokering (4GB default)
- `cpu_spin.py` - Kontrollerade CPU-pulser  
- `tool_storm.py` - Planner + kalender/email-verktyg
- `vision_stress.py` - RTSP kamera-requests om tillgänglig

**Monitoring:**
- `watchers.py` - Mäter Guardian brownout trigger/recovery
- `hud.py` - Streamlit dashboard med realtids-visualisering

## Säkerhet

- Emergency state (>10s) avbryter automatiskt last
- MAX_TEMP_C/MAX_BATTERY_PCT säkerhetsventiler
- Gradvis minnesallokering, ej "brutal allocation"
- Respektfulla timeouts och kontrollerade intervall

## Environment Variables

```bash
API_BASE=http://orchestrator:8000
GUARD_HEALTH=http://orchestrator:8000/guardian/health  
SLO_BROWNOUT_TRIGGER_MS=150    # Brownout trigger budget
RECOVER_S=60                   # Recovery time budget
MEMORY_BALLOON_GB=4            # RAM stress mål
CPU_THREADS=4                  # CPU stress trådar
DEEP_CONCURRENCY=2             # Deep-LLM parallellism
CAMERA_RTSP_URL=               # RTSP kamera URL (optional)
```

## Förväntat Resultat

✅ **PASS Kriterier:**
- Brownout trigger: ≤150ms efter RAM >90%
- Recovery: ≤60s efter load-release  
- Guardian: NORMAL→BROWNOUT→NORMAL cykel

❌ **FAIL Kriterier:**
- Trigger >150ms eller ingen brownout
- Recovery >60s eller fastnar i EMERGENCY
- Systemkrasch eller ohanterade fel

## HUD Dashboard

Streamlit-dashboard visar:
- **Realtids timeline** med Guardian state-övergångar
- **SLO metrics** med PASS/FAIL status mot budgets
- **Stress test breakdown** för alla moduler
- **Auto-refresh** varje 5s under test

Dashboard: `http://localhost:8501` efter `./run_hud.sh`