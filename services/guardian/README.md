# Alice Guardian Service v2

Deterministisk säkerhetsdaemon som skyddar Alice från överbelastning av LLM-modeller.

## 🎯 Översikt

Guardian är Alice's regelbaserade säkerhetsystem som skyddar mot överbelastning av gpt-oss:20b modellen (13GB RAM). Det är deterministiskt - ingen AI i säkerhetsloopen - bara hårda trösklar och verifierbara regler.

## 🏗️ Arkitektur

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

## 🔧 Komponenter

### 1. Guardian Daemon (`src/core/guardian.py`)
- Kontinuerlig systemövervakning (1s intervall)
- Tillståndsmaskin: NORMAL → BROWNOUT → DEGRADED → EMERGENCY → LOCKDOWN
- Hysteresis: Förhindrar oscillation med 3-punkt measurement windows
- Cooldown: Kill rate limiting (max 3 kills/30min)

### 2. Brownout Manager (`src/core/brownout_manager.py`)
- Intelligent degradation: Model switch + Context reduction + Tool disable
- 4 Nivåer: NONE → LIGHT → MODERATE → HEAVY
- Gradvis nedtrappning istället för total avbrott

### 3. Kill Sequence (`src/core/kill_sequence.py`)
- Graceful Ollama shutdown med backoff
- Drain → SIGTERM → SIGKILL → Restart → Health gate
- Rate limiting och lockdown vid för många kills

### 4. API Server (`src/api/server.py`)
- FastAPI server på port :8787
- `/health` - Guardian status
- Control endpoints för degrade/stop-intake/resume

### 5. Guardian Gate Middleware (`src/api/middleware.py`)
- Admission control för Alice API
- Blockerar requests baserat på Guardian status
- 429/503 responses med retry-after headers

## 📊 Tillståndsmaskin

```
NORMAL ──5pt trigger──► BROWNOUT ──hard trigger──► EMERGENCY
   ▲                       │                          │
   │ 60s recovery           ▼ escalation               │
   └───────────────── DEGRADED ◄─────cooldown─────────┘
                          │
                          ▼ max kills
                      LOCKDOWN (1h)
```

### Trösklar
- **Soft Trigger**: 80% RAM/CPU (3 mätpunkter) → BROWNOUT
- **Hard Trigger**: 92% RAM/CPU (omedelbar) → EMERGENCY  
- **Recovery**: <70% RAM, <75% CPU i 45s → NORMAL

## 🚀 Användning

### Installation
```bash
cd v2/services/guardian
pip install -e .
```

### Starta Guardian
```bash
# Development
python src/guardian.py

# Production
python -m guardian.guardian

# Med miljövariabler
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
# Activate degradation
curl -X POST http://localhost:8787/api/guard/degrade

# Stop intake
curl -X POST http://localhost:8787/api/guard/stop-intake

# Resume intake  
curl -X POST http://localhost:8787/api/guard/resume-intake

# Set concurrency
curl -X POST http://localhost:8787/api/guard/set-concurrency \
  -H "Content-Type: application/json" \
  -d '{"concurrency": 5}'
```

## 🔧 Konfiguration

```python
config = GuardianConfig(
    # Trösklar
    ram_soft_pct=0.80,      # 80% för brownout
    ram_hard_pct=0.92,      # 92% för emergency
    ram_recovery_pct=0.70,  # 70% för recovery
    
    # Hysteresis
    measurement_window=3,    # 3 mätpunkter för trigger
    recovery_window_s=45.0,  # 45s återställning
    
    # Kill cooldown
    kill_cooldown_short_s=300.0,    # 5 min mellan kills
    max_kills_per_window=3,         # Max 3 kills/30min
    lockdown_duration_s=3600.0,     # 1h lockdown
    
    # Endpoints
    alice_base_url="http://localhost:8000",
    ollama_base_url="http://localhost:11434",
    guardian_port=8787
)
```

## 📈 Monitoring & Observability

Guardian loggar strukturerade metrics för observability:

```json
{
  "timestamp": "2024-08-31T16:30:00",
  "guardian_state": "brownout",
  "state_duration_s": 45.2,
  "ram_pct": 85.3,
  "cpu_pct": 78.1,
  "disk_pct": 42.5,
  "temp_c": 65.0,
  "ollama_pids": 2,
  "brownout_active": true,
  "brownout_level": "MODERATE"
}
```

## 🔗 Integration med Alice v2

### I Alice API Server
```typescript
import { GuardianClient } from '@alice/api'

const guardianClient = new GuardianClient({
  baseURL: 'http://localhost:8787'
})

// Check Guardian status
const status = await guardianClient.getStatus()
console.log(`Guardian state: ${status.status}`)
```

### Guardian Gate Middleware
```python
from guardian.api import GuardianGate

app.add_middleware(GuardianGate,
    guardian_url="http://localhost:8787/health",
    cache_ttl_ms=250,
    timeout_s=0.5
)
```

## 🧪 Testing

```bash
# Run tests
python -m pytest src/tests/

# Linting
ruff check src/

# Format
ruff format src/
```

## 💡 Fördelar vs v1

1. **Cleaner Architecture**: Separerad service med tydlig API
2. **Better Typing**: Full TypeScript integration
3. **Structured Logging**: JSON output för observability  
4. **Rate Limiting**: Smartare cooldown-logik
5. **Health Gates**: Validering före återstart
6. **Graceful Degradation**: Brownout manager för intelligent nedtrappning

Guardian v2 behåller alla robusta säkerhetsegenskaper från v1 medan det integrerar perfekt med den nya clean architecture! 🛡️