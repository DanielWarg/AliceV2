# Alice Guardian Service v2

Deterministic security daemon that protects Alice from LLM model overload.

## 🎯 Overview

Guardian is Alice's rule-based security system that protects against overload of the gpt-oss:20b model (13GB RAM). It is deterministic - no AI in the security loop - only hard thresholds and verifiable rules.

## 🏗️ Architecture

```
┌─────────────────┐    HTTP     ┌─────────────────┐
│   Alice Server  │◄──────────► │  Guardian       │
│   :8000         │             │  :8787          │
└─────────────────┘             └─────────────────┘
         ▲                               │
         │ admission control             │ system monitoring
         ▼                               ▼
┌─────────────────┐             ┌─────────────────┐
│ Guardian Gate   │             │ psutil metrics  │
│ Middleware      │             │ (RAM/CPU/Disk)  │
└─────────────────┘             └─────────────────┘
```

## 🔧 Components

### 1. Guardian Daemon (`src/core/guardian.py`)

- Continuous system monitoring (1s interval)
- State machine: NORMAL → BROWNOUT → DEGRADED → EMERGENCY → LOCKDOWN
- Hysteresis: Prevents oscillation with 3-point measurement windows
- Cooldown: Kill rate limiting (max 3 kills/30min)

### 2. Brownout Manager (`src/core/brownout_manager.py`)

- Intelligent degradation: Model switch + Context reduction + Tool disable
- 4 Levels: NONE → LIGHT → MODERATE → HEAVY
- Gradual reduction instead of total outage

### 3. Kill Sequence (`src/core/kill_sequence.py`)

- Graceful Ollama shutdown with backoff
- Drain → SIGTERM → SIGKILL → Restart → Health gate
- Rate limiting and lockdown on too many kills

### 4. API Server (`src/api/server.py`)

- FastAPI server on port :8787
- `/health` - Guardian status
- Control endpoints for degrade/stop-intake/resume

### 5. Guardian Gate Middleware (`src/api/middleware.py`)

- Admission control for Alice API
- Blocks requests based on Guardian status
- 429/503 responses with retry-after headers

## 📊 State Machine

```
NORMAL ──5pt trigger──► BROWNOUT ──hard trigger──► EMERGENCY
   ▲                       │                          │
   │ 60s recovery           ▼ escalation               │
   └───────────────── DEGRADED ◄─────cooldown─────────┘
                          │
                          ▼ max kills
                      LOCKDOWN (1h)
```

### Thresholds

- **Soft Trigger**: 80% RAM/CPU (3 measurement points) → BROWNOUT
- **Hard Trigger**: 92% RAM/CPU (immediate) → EMERGENCY
- **Recovery**: <70% RAM, <75% CPU in 45s → NORMAL

## 🚀 Usage

### Installation

```bash
cd v2/services/guardian
pip install -e .
```

### Start Guardian

```bash
# Development
python src/guardian.py

# Production
python -m guardian.guardian

# With environment variables
ALICE_API_URL=http://localhost:8000 \
GUARDIAN_PORT=8787 \
python src/guardian.py
```

### API Endpoints

#### Health Check

```bash
curl http://localhost:8787/health
```

#### Control Endpoints

```bash
# Degrade system
curl -X POST http://localhost:8787/degrade \
  -H "Content-Type: application/json" \
  -d '{"level": "MODERATE"}'

# Stop intake
curl -X POST http://localhost:8787/stop-intake

# Resume normal operation
curl -X POST http://localhost:8787/resume
```

## 🔒 Security Features

### Deterministic Logic

- No AI or machine learning in security decisions
- Hard-coded thresholds and rules
- Verifiable behavior and predictable responses

### Rate Limiting

- Maximum 3 kills per 30 minutes
- Cooldown periods between actions
- Lockdown mode after threshold exceeded

### Resource Protection

- RAM usage monitoring with soft/hard triggers
- CPU usage tracking and throttling
- Disk space monitoring
- Temperature and battery awareness

## 📊 Monitoring

### Metrics

- Guardian state transitions
- Resource usage trends
- Kill sequence statistics
- Recovery time measurements

### Health Checks

- System resource status
- Guardian daemon health
- API endpoint availability
- Middleware functionality

## 🚨 Emergency Procedures

### Automatic Actions

- Immediate model shutdown on hard triggers
- Graceful degradation on soft triggers
- System recovery monitoring
- Lockdown activation on repeated failures

### Manual Override

- Emergency stop via API
- Force recovery procedures
- System reset capabilities
- Maintenance mode activation

---

**Guardian v2** - Deterministic protection for Alice AI Assistant 🛡️
