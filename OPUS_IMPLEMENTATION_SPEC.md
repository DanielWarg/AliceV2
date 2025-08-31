# Alice v2 - Complete Implementation Specification för Opus
*Färdig bootstrap-spec med exakta commands, dependencies och roadmap*

**Target**: Opus AI implementerar Alice v2 enligt denna spec  
**Timeline**: 4-5 veckor total  
**Architecture**: Monorepo (turborepo + pnpm) med clean separation

---

# 🏗️ 0) Monorepo-struktur (turborepo + pnpm)

```
v2/
├─ turbo.json
├─ package.json
├─ pnpm-workspace.yaml
├─ .env.example
├─ docker-compose.yml
├─ services/
│  ├─ orchestrator/        # FastAPI (py) - LLM routing
│  ├─ guardian/            # FastAPI (py) + psutil - System safety
│  ├─ voice/               # ASR WS + TTS HTTP (py) - Voice pipeline
│  └─ dashboard/           # Streamlit (py) - Observability
├─ apps/
│  └─ web/                 # Next.js (ts) - Frontend interface
├─ packages/
│  ├─ api/                 # TypeScript SDK (fetch/WS)
│  ├─ ui/                  # shadcn/tailwind design system
│  └─ types/               # Shared TS types (Intent, Slots, etc.)
└─ tools/
   └─ scripts/             # One-liners, db/index helpers
```

## Root Configuration Files

**package.json (root)**
```json
{
  "name": "alice",
  "version": "2.0.0",
  "private": true,
  "packageManager": "pnpm@9",
  "scripts": {
    "dev": "turbo run dev --parallel",
    "dev:services": "concurrently \"uvicorn services/orchestrator/main:app --reload --port 8000\" \"uvicorn services/guardian/main:app --reload --port 8787\" \"uvicorn services/voice/main:app --reload --port 8001\"",
    "build": "turbo run build",
    "lint": "turbo run lint", 
    "test": "turbo run test",
    "format": "turbo run format",
    "install:all": "pnpm i && cd services/orchestrator && pip install -r requirements.txt && cd ../guardian && pip install -r requirements.txt && cd ../voice && pip install -r requirements.txt",
    "docker:up": "docker compose up -d",
    "docker:down": "docker compose down"
  },
  "devDependencies": {
    "turbo": "^2.0.0",
    "prettier": "^3.3.3",
    "typescript": "^5.5.4",
    "concurrently": "^8.2.2"
  }
}
```

**pnpm-workspace.yaml**
```yaml
packages:
  - "apps/*"
  - "packages/*"
```

**turbo.json**
```json
{
  "$schema": "https://turbo.build/schema.json",
  "pipeline": {
    "dev": { 
      "cache": false, 
      "persistent": true 
    },
    "build": { 
      "dependsOn": ["^build"], 
      "outputs": ["dist/**", ".next/**", "build/**"] 
    },
    "lint": {
      "dependsOn": ["^build"]
    },
    "test": {
      "dependsOn": ["^build"]
    },
    "format": {}
  }
}
```

**.env.example**
```bash
# === API Endpoints ===
API_BASE=http://localhost:8000
WS_ASR=ws://localhost:8001/ws/asr
OLLAMA_HOST=http://localhost:11434
REDIS_URL=redis://localhost:6379/0

# === Guardian Thresholds ===
GUARD_RAM_SOFT=0.80
GUARD_RAM_HARD=0.92
GUARD_RECOVER_RAM=0.70
GUARD_CPU_SOFT=0.80
GUARD_TEMP_C_HARD=85
GUARD_BATTERY_PCT_HARD=25

# === Voice Pipeline ===
ASR_VAD_START=0.5
ASR_VAD_STOP=0.35

# === Feature Flags ===
FEATURE_VISION=true
FEATURE_TTS=true
FEATURE_MEMORY_WRITE=true
FEATURE_PROACTIVE=false

# === Development ===
NODE_ENV=development
LOG_LEVEL=INFO
GUARDIAN_PORT=8787
```

---

# 📦 1) Dependencies per Service

## Python Services (Unified Pin-Set)

**services/orchestrator/requirements.txt**
```txt
fastapi==0.112.2
uvicorn[standard]==0.30.6
httpx==0.27.2
pydantic==2.8.2
redis==5.0.7
faiss-cpu==1.8.0
prometheus-client==0.20.0
python-dotenv==1.0.1
# langgraph==0.2.27  # Add when connecting LLM graph
```

**services/guardian/requirements.txt**
```txt
fastapi==0.112.2
uvicorn[standard]==0.30.6
psutil==6.0.0
prometheus-client==0.20.0
pydantic==2.8.2
python-dotenv==1.0.1
httpx==0.27.2
```

**services/voice/requirements.txt**
```txt
fastapi==0.112.2
uvicorn[standard]==0.30.6
websockets==12.0
soundfile==0.12.1
numpy==1.26.4
scipy==1.13.1
pydub==0.25.1
pydantic==2.8.2
python-dotenv==1.0.1
```

**services/dashboard/requirements.txt**
```txt
streamlit==1.37.0
websockets==12.0
requests==2.31.0
python-dotenv==1.0.1
plotly==5.17.0
```

## TypeScript Packages

**apps/web/package.json**
```json
{
  "name": "web",
  "private": true,
  "scripts": {
    "dev": "next dev -p 3000",
    "build": "next build", 
    "start": "next start -p 3000",
    "lint": "next lint"
  },
  "dependencies": {
    "next": "14.2.5",
    "react": "18.3.1",
    "react-dom": "18.3.1",
    "zustand": "^4.5.2",
    "tailwindcss": "^3.4.7",
    "class-variance-authority": "^0.7.0",
    "tailwind-merge": "^2.4.0",
    "framer-motion": "^11.3.8",
    "@alice/api": "workspace:*",
    "@alice/types": "workspace:*",
    "@alice/ui": "workspace:*"
  },
  "devDependencies": {
    "typescript": "^5.5.4",
    "@types/react": "^18.3.3",
    "@types/react-dom": "^18.3.0"
  }
}
```

**packages/api/package.json**
```json
{
  "name": "@alice/api",
  "version": "2.0.0",
  "main": "./dist/index.js",
  "types": "./dist/index.d.ts",
  "scripts": {
    "build": "tsup src/index.ts --format cjs,esm --dts",
    "dev": "tsup src/index.ts --format cjs,esm --dts --watch"
  },
  "dependencies": {
    "zod": "^3.23.8",
    "ws": "^8.18.0",
    "isomorphic-ws": "^5.0.0",
    "@alice/types": "workspace:*"
  },
  "devDependencies": {
    "tsup": "^8.2.3",
    "typescript": "^5.5.4"
  }
}
```

---

# 🚀 2) Minimal Implementation Stubs

## services/orchestrator/main.py (FastAPI + Hot-reload)

```python
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import os
import httpx
import time

app = FastAPI(title="Alice Orchestrator", version="2.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class IngestRequest(BaseModel):
    v: str = "1"
    session_id: str
    lang: str = "sv"
    text: str
    intent: str | None = None
    confidence: float | None = None
    slots: dict | None = None
    mood_score: float | None = None
    trace: dict | None = None

class ChatRequest(BaseModel):
    message: str
    session_id: str
    model: str = "auto"

@app.get("/health")
def health():
    return {
        "ok": True, 
        "service": "orchestrator",
        "mode": os.getenv("ALICE_MODE", "phase1"),
        "timestamp": time.time()
    }

@app.post("/api/orchestrator/ingest")
async def ingest(req: IngestRequest):
    # Phase 1: Always route to "micro" model
    # Phase 2+: Add Guardian check, resource awareness, model routing
    
    guardian_url = f"http://localhost:{os.getenv('GUARDIAN_PORT', '8787')}/guardian/health"
    try:
        async with httpx.AsyncClient(timeout=0.5) as client:
            guardian_resp = await client.get(guardian_url)
            guardian_state = guardian_resp.json()
            
            # Block if Guardian is not in good state
            if guardian_state.get("state") in ["EMERGENCY", "LOCKDOWN"]:
                raise HTTPException(status_code=503, detail="System under protection")
                
    except httpx.TimeoutException:
        # Guardian down - proceed with caution (Phase 1 behavior)
        pass
    
    return {
        "run_id": req.session_id,
        "route": "micro", 
        "accepted": True,
        "timestamp": time.time()
    }

@app.post("/api/chat")
async def chat(req: ChatRequest):
    # Phase 1: Simple echo response
    # Phase 2+: Add actual LLM integration
    return {
        "response": f"Echo: {req.message}",
        "model": "stub",
        "latency_ms": 50,
        "session_id": req.session_id
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000, reload=True)
```

## services/guardian/main.py (FastAPI + psutil)

```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import psutil
import time
import os
import asyncio
from typing import Literal

app = FastAPI(title="Alice Guardian", version="2.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Guardian State Management
GuardianState = Literal["NORMAL", "BROWNOUT", "DEGRADED", "EMERGENCY", "LOCKDOWN"]
BrownoutLevel = Literal["NONE", "LIGHT", "MODERATE", "HEAVY"]

class GuardianStatus(BaseModel):
    state: GuardianState
    ram_pct: float
    cpu_pct: float
    temp_c: float
    battery_pct: float
    brownout_level: BrownoutLevel
    reason: str
    since_s: float
    uptime_s: float

# Global state
STATE = {
    "state": "NORMAL",
    "brownout_level": "NONE", 
    "reason": "STARTUP",
    "last_transition": time.time(),
    "start_time": time.time()
}

def get_system_metrics():
    """Get current system metrics with safe fallbacks"""
    try:
        ram = psutil.virtual_memory().percent
        cpu = psutil.cpu_percent(interval=0.1)
        
        # Temperature (Mac-safe fallback)
        temp = 50.0
        try:
            temps = psutil.sensors_temperatures()
            if temps:
                temp = list(temps.values())[0][0].current
        except (AttributeError, KeyError, IndexError):
            pass
            
        # Battery (laptop-safe fallback) 
        battery_pct = 100.0
        try:
            battery = psutil.sensors_battery()
            if battery:
                battery_pct = battery.percent
        except (AttributeError, TypeError):
            pass
            
        return ram, cpu, temp, battery_pct
        
    except Exception:
        # Ultimate fallback
        return 50.0, 50.0, 50.0, 100.0

def evaluate_guardian_state() -> GuardianStatus:
    """Evaluate system state based on thresholds with hysteresis"""
    ram, cpu, temp, battery = get_system_metrics()
    
    # Load thresholds from environment
    ram_soft = float(os.getenv("GUARD_RAM_SOFT", "0.80")) * 100
    ram_hard = float(os.getenv("GUARD_RAM_HARD", "0.92")) * 100
    ram_recover = float(os.getenv("GUARD_RECOVER_RAM", "0.70")) * 100
    cpu_soft = float(os.getenv("GUARD_CPU_SOFT", "0.80")) * 100
    temp_hard = float(os.getenv("GUARD_TEMP_C_HARD", "85"))
    battery_hard = float(os.getenv("GUARD_BATTERY_PCT_HARD", "25"))
    
    current_state = STATE["state"]
    new_state = current_state
    new_brownout = STATE["brownout_level"]
    reason = STATE["reason"]
    
    # State transition logic with hysteresis
    if current_state in ("NORMAL", "DEGRADED"):
        if ram >= ram_hard or cpu >= ram_hard or temp >= temp_hard or battery <= battery_hard:
            new_state = "EMERGENCY"
            new_brownout = "HEAVY"
            reason = f"HARD_TRIGGER (RAM:{ram:.1f}% CPU:{cpu:.1f}% TEMP:{temp:.1f}°C BAT:{battery:.1f}%)"
        elif ram >= ram_soft or cpu >= cpu_soft:
            new_state = "BROWNOUT" 
            new_brownout = "LIGHT"
            reason = f"SOFT_TRIGGER (RAM:{ram:.1f}% CPU:{cpu:.1f}%)"
    
    elif current_state in ("BROWNOUT", "EMERGENCY"):
        if ram < ram_recover and cpu < ram_recover and temp < temp_hard - 10:
            new_state = "NORMAL"
            new_brownout = "NONE" 
            reason = f"RECOVERY (RAM:{ram:.1f}% CPU:{cpu:.1f}%)"
    
    # Update state if changed
    if new_state != current_state:
        STATE.update({
            "state": new_state,
            "brownout_level": new_brownout,
            "reason": reason,
            "last_transition": time.time()
        })
    
    now = time.time()
    return GuardianStatus(
        state=STATE["state"],
        ram_pct=round(ram, 1),
        cpu_pct=round(cpu, 1), 
        temp_c=round(temp, 1),
        battery_pct=round(battery, 1),
        brownout_level=STATE["brownout_level"],
        reason=STATE["reason"],
        since_s=round(now - STATE["last_transition"], 1),
        uptime_s=round(now - STATE["start_time"], 1)
    )

@app.get("/guardian/health", response_model=GuardianStatus)
def get_guardian_health():
    """Primary endpoint for Guardian status"""
    return evaluate_guardian_state()

@app.get("/health")
def health():
    """Simple health check"""
    return {"ok": True, "service": "guardian"}

@app.post("/api/guard/degrade")
def force_degrade():
    """Force brownout for testing"""
    STATE.update({
        "state": "BROWNOUT",
        "brownout_level": "MODERATE", 
        "reason": "MANUAL_TRIGGER",
        "last_transition": time.time()
    })
    return {"ok": True, "forced": "BROWNOUT"}

@app.post("/api/guard/recover")
def force_recover():
    """Force recovery for testing"""
    STATE.update({
        "state": "NORMAL",
        "brownout_level": "NONE",
        "reason": "MANUAL_RECOVERY", 
        "last_transition": time.time()
    })
    return {"ok": True, "forced": "NORMAL"}

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("GUARDIAN_PORT", "8787"))
    uvicorn.run(app, host="127.0.0.1", port=port, reload=True)
```

## services/voice/main.py (WebSocket ASR + TTS HTTP)

```python
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
import time
import base64
import json
import asyncio
import os

app = FastAPI(title="Alice Voice Service", version="2.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class TTSRequest(BaseModel):
    v: str = "1"
    lang: str = "sv"
    text: str
    voice: str = "alice_neutral"
    cache_ok: bool = True

class ASRConfig(BaseModel):
    language: str = "sv"
    model: str = "whisper-small"
    vad_start_threshold: float = 0.5
    vad_stop_threshold: float = 0.35

# WebSocket connection manager
class ConnectionManager:
    def __init__(self):
        self.active_connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def send_personal_message(self, message: dict, websocket: WebSocket):
        await websocket.send_json(message)

manager = ConnectionManager()

@app.get("/health")
def health():
    return {
        "ok": True,
        "service": "voice", 
        "connections": len(manager.active_connections)
    }

@app.websocket("/ws/asr")
async def websocket_asr(websocket: WebSocket):
    """
    WebSocket endpoint for real-time ASR
    Accepts audio chunks and returns partial/final transcripts
    """
    await manager.connect(websocket)
    
    audio_buffer = b""
    session_start = time.time()
    last_partial = time.time()
    
    try:
        while True:
            # Receive message from client
            message = await websocket.receive_text()
            data = json.loads(message)
            
            if data.get("type") == "audio":
                # Decode base64 audio chunk
                chunk = base64.b64decode(data["pcm_base64"])
                audio_buffer += chunk
                
                # Send partial transcript every 300ms (simulated)
                now = time.time()
                if now - last_partial > 0.3:
                    await manager.send_personal_message({
                        "event": "partial",
                        "text": "(processing...)",
                        "confidence": 0.8,
                        "timestamp": now - session_start
                    }, websocket)
                    last_partial = now
                    
            elif data.get("type") == "end":
                # Process final transcript (simulated)
                await asyncio.sleep(0.1)  # Simulate processing
                
                # Phase 1: Return Swedish test phrase
                # Phase 3: Replace with actual Whisper.cpp integration
                final_text = "hej alice vad är klockan"
                
                await manager.send_personal_message({
                    "event": "final", 
                    "text": final_text,
                    "confidence": 0.95,
                    "language": "sv",
                    "duration_s": time.time() - session_start,
                    "processing_time_ms": 120
                }, websocket)
                
                # Reset for next utterance
                audio_buffer = b""
                session_start = time.time()
                
            elif data.get("type") == "config":
                # Update ASR configuration
                config = ASRConfig(**data.get("config", {}))
                await manager.send_personal_message({
                    "event": "config_updated",
                    "config": config.dict()
                }, websocket)
                
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception as e:
        await manager.send_personal_message({
            "event": "error",
            "error": str(e)
        }, websocket)
        manager.disconnect(websocket)

@app.post("/api/tts")
def generate_tts(request: TTSRequest):
    """
    HTTP endpoint for Text-to-Speech
    Phase 1: Returns mock response
    Phase 3: Replace with actual Piper/VITS integration
    """
    
    # Simulate processing time based on text length
    processing_time = min(50 + len(request.text) * 2, 500)
    
    # Mock voice persona selection based on voice parameter
    voice_map = {
        "alice_neutral": "neutral_alice_v2.onnx",
        "alice_glad": "happy_alice_v2.onnx", 
        "alice_empatisk": "empathetic_alice_v2.onnx"
    }
    
    model_file = voice_map.get(request.voice, "neutral_alice_v2.onnx")
    
    return {
        "audio_url": f"/audio/tts_{hash(request.text) % 10000}.wav",
        "model": model_file,
        "latency_ms": processing_time,
        "cache_status": "HIT" if request.cache_ok else "MISS",
        "language": request.lang,
        "voice": request.voice,
        "duration_estimate_s": len(request.text) * 0.05  # ~50ms per character
    }

@app.get("/api/voice/config")
def get_voice_config():
    """Get current voice service configuration"""
    return {
        "asr": {
            "model": "whisper-small",
            "language": "sv", 
            "vad_thresholds": {
                "start": float(os.getenv("ASR_VAD_START", "0.5")),
                "stop": float(os.getenv("ASR_VAD_STOP", "0.35"))
            }
        },
        "tts": {
            "voices": list(voice_map.keys()),
            "cache_enabled": True,
            "supported_languages": ["sv", "en"]
        }
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8001, reload=True)
```

## packages/api/src/index.ts (TypeScript SDK)

```typescript
// packages/api/src/index.ts
export interface ChatRequest {
  message: string;
  session_id: string;
  model?: string;
}

export interface ChatResponse {
  response: string;
  model: string;
  latency_ms: number;
  session_id: string;
}

export interface GuardianStatus {
  state: 'NORMAL' | 'BROWNOUT' | 'DEGRADED' | 'EMERGENCY' | 'LOCKDOWN';
  ram_pct: number;
  cpu_pct: number;
  temp_c: number;
  battery_pct: number;
  brownout_level: 'NONE' | 'LIGHT' | 'MODERATE' | 'HEAVY';
  reason: string;
  since_s: number;
  uptime_s: number;
}

export interface TTSRequest {
  v?: string;
  lang?: string;
  text: string;
  voice?: string;
  cache_ok?: boolean;
}

export interface TTSResponse {
  audio_url: string;
  model: string;
  latency_ms: number;
  cache_status: 'HIT' | 'MISS';
  language: string;
  voice: string;
  duration_estimate_s: number;
}

export interface ASREvent {
  event: 'partial' | 'final' | 'error' | 'config_updated';
  text?: string;
  confidence?: number;
  timestamp?: number;
  language?: string;
  duration_s?: number;
  processing_time_ms?: number;
  error?: string;
}

export class AliceAPIClient {
  private baseURL: string;
  private wsURL: string;
  private ws: WebSocket | null = null;
  private eventHandlers: Map<string, ((event: ASREvent) => void)[]> = new Map();

  constructor(config: { baseURL: string; wsURL: string }) {
    this.baseURL = config.baseURL;
    this.wsURL = config.wsURL;
  }

  // HTTP Methods
  async chat(request: ChatRequest): Promise<ChatResponse> {
    const response = await fetch(`${this.baseURL}/api/chat`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(request),
    });

    if (!response.ok) {
      throw new Error(`Chat failed: ${response.statusText}`);
    }

    return response.json();
  }

  async getGuardianStatus(): Promise<GuardianStatus> {
    const response = await fetch(`${this.baseURL.replace('8000', '8787')}/guardian/health`);
    
    if (!response.ok) {
      throw new Error(`Guardian status failed: ${response.statusText}`);
    }

    return response.json();
  }

  async generateTTS(request: TTSRequest): Promise<TTSResponse> {
    const response = await fetch(`${this.baseURL.replace('8000', '8001')}/api/tts`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(request),
    });

    if (!response.ok) {
      throw new Error(`TTS failed: ${response.statusText}`);
    }

    return response.json();
  }

  // WebSocket Methods
  async connectWebSocket(): Promise<void> {
    return new Promise((resolve, reject) => {
      this.ws = new WebSocket(this.wsURL);
      
      this.ws.onopen = () => {
        console.log('WebSocket connected');
        resolve();
      };
      
      this.ws.onerror = (error) => {
        console.error('WebSocket error:', error);
        reject(error);
      };
      
      this.ws.onmessage = (event) => {
        try {
          const data: ASREvent = JSON.parse(event.data);
          this.emitEvent(data);
        } catch (err) {
          console.error('WebSocket message parse error:', err);
        }
      };
      
      this.ws.onclose = () => {
        console.log('WebSocket disconnected');
        this.ws = null;
      };
    });
  }

  sendAudioChunk(audioData: string): void {
    if (!this.ws || this.ws.readyState !== WebSocket.OPEN) {
      throw new Error('WebSocket not connected');
    }

    this.ws.send(JSON.stringify({
      type: 'audio',
      pcm_base64: audioData
    }));
  }

  endAudioStream(): void {
    if (!this.ws || this.ws.readyState !== WebSocket.OPEN) {
      throw new Error('WebSocket not connected');
    }

    this.ws.send(JSON.stringify({ type: 'end' }));
  }

  updateASRConfig(config: { language?: string; model?: string }): void {
    if (!this.ws || this.ws.readyState !== WebSocket.OPEN) {
      throw new Error('WebSocket not connected');
    }

    this.ws.send(JSON.stringify({
      type: 'config',
      config
    }));
  }

  // Event Handling
  on(event: string, handler: (event: ASREvent) => void): void {
    if (!this.eventHandlers.has(event)) {
      this.eventHandlers.set(event, []);
    }
    this.eventHandlers.get(event)!.push(handler);
  }

  off(event: string, handler?: (event: ASREvent) => void): void {
    if (!this.eventHandlers.has(event)) return;

    if (handler) {
      const handlers = this.eventHandlers.get(event)!;
      const index = handlers.indexOf(handler);
      if (index > -1) {
        handlers.splice(index, 1);
      }
    } else {
      this.eventHandlers.set(event, []);
    }
  }

  private emitEvent(event: ASREvent): void {
    // Emit to specific event handlers
    const handlers = this.eventHandlers.get(event.event) || [];
    handlers.forEach(handler => handler(event));

    // Emit to wildcard handlers
    const wildcardHandlers = this.eventHandlers.get('*') || [];
    wildcardHandlers.forEach(handler => handler(event));
  }

  disconnect(): void {
    if (this.ws) {
      this.ws.close();
      this.ws = null;
    }
    this.eventHandlers.clear();
  }

  isConnected(): boolean {
    return this.ws !== null && this.ws.readyState === WebSocket.OPEN;
  }
}

// Export everything
export * from '@alice/types';
```

---

# 🐳 3) Docker & Hot-reload Configuration

**docker-compose.yml**
```yaml
version: '3.8'

services:
  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    command: redis-server --appendonly yes
    volumes:
      - redis_data:/data

  ollama:
    image: ollama/ollama:latest
    ports:
      - "11434:11434"
    volumes:
      - ollama_data:/root/.ollama
    environment:
      - OLLAMA_HOST=0.0.0.0

  dashboard:
    build:
      context: ./services/dashboard
      dockerfile: Dockerfile
    ports:
      - "8501:8501"
    environment:
      - REDIS_URL=redis://redis:6379/0
      - API_BASE=http://host.docker.internal:8000
    depends_on:
      - redis

volumes:
  redis_data:
  ollama_data:
```

**Development Scripts (add to root package.json)**
```bash
# Quick Start Commands
pnpm install:all    # Install all dependencies
pnpm dev           # Start frontend only
pnpm dev:services  # Start all Python services with hot-reload
pnpm docker:up     # Start Redis + Ollama + Dashboard
```

---

# 🧪 4) Integration Testing Approach

## Backend Testing (Python)
```python
# tests/test_integration.py
import pytest
import httpx
import asyncio
import json
from websockets import connect

BASE_URL = "http://localhost:8000"
GUARDIAN_URL = "http://localhost:8787" 
VOICE_URL = "http://localhost:8001"

@pytest.mark.asyncio
async def test_health_endpoints():
    """Test all service health endpoints"""
    async with httpx.AsyncClient() as client:
        # Orchestrator health
        resp = await client.get(f"{BASE_URL}/health")
        assert resp.status_code == 200
        
        # Guardian health  
        resp = await client.get(f"{GUARDIAN_URL}/guardian/health")
        assert resp.status_code == 200
        data = resp.json()
        assert "state" in data
        assert "ram_pct" in data
        
        # Voice health
        resp = await client.get(f"{VOICE_URL}/health")
        assert resp.status_code == 200

@pytest.mark.asyncio
async def test_voice_websocket_flow():
    """Test WebSocket ASR flow"""
    uri = "ws://localhost:8001/ws/asr"
    
    async with connect(uri) as websocket:
        # Send audio chunk
        await websocket.send(json.dumps({
            "type": "audio",
            "pcm_base64": "dGVzdA=="  # "test" in base64
        }))
        
        # Send end signal
        await websocket.send(json.dumps({"type": "end"}))
        
        # Receive final transcript
        response = await websocket.recv()
        data = json.loads(response)
        assert data["event"] == "final"
        assert "text" in data

@pytest.mark.asyncio 
async def test_guardian_brownout():
    """Test Guardian brownout simulation"""
    async with httpx.AsyncClient() as client:
        # Force brownout
        resp = await client.post(f"{GUARDIAN_URL}/api/guard/degrade")
        assert resp.status_code == 200
        
        # Check state
        resp = await client.get(f"{GUARDIAN_URL}/guardian/health")
        data = resp.json()
        assert data["state"] == "BROWNOUT"
        
        # Force recovery
        resp = await client.post(f"{GUARDIAN_URL}/api/guard/recover") 
        assert resp.status_code == 200
        
        resp = await client.get(f"{GUARDIAN_URL}/guardian/health")
        data = resp.json()
        assert data["state"] == "NORMAL"
```

## Frontend Testing (Playwright)
```typescript
// tests/e2e/voice-flow.spec.ts
import { test, expect } from '@playwright/test';

test('complete voice flow', async ({ page }) => {
  await page.goto('http://localhost:3000');
  
  // Check Guardian status display
  await expect(page.locator('[data-testid=guardian-status]')).toBeVisible();
  
  // Start voice recording
  await page.click('[data-testid=voice-button]');
  
  // Simulate voice input (mock)
  await page.evaluate(() => {
    window.postMessage({ type: 'mock-audio-input', text: 'hej alice' }, '*');
  });
  
  // Check for transcript display
  await expect(page.locator('[data-testid=transcript]')).toContainText('hej alice');
  
  // Check for TTS response
  await expect(page.locator('[data-testid=alice-response]')).toBeVisible();
});
```

---

# 🗺️ 5) Implementation Roadmap (4-5 Veckor)

## Phase 1 - Foundation (Vecka 1)
**Deliverables:**
- [ ] Monorepo setup (turborepo + pnpm workspaces) 
- [ ] All service stubs running with hot-reload
- [ ] Docker compose (Redis + Ollama) working
- [ ] TypeScript SDK functional for basic HTTP/WS

**Commands:**
```bash
pnpm install:all
pnpm dev:services
pnpm --filter web dev  
docker compose up -d
```

**Acceptance Criteria:**
- [ ] `curl http://localhost:8000/health` returns 200
- [ ] `curl http://localhost:8787/guardian/health` shows system metrics
- [ ] WebSocket connection to `/ws/asr` accepts audio chunks
- [ ] Frontend displays Guardian status

## Phase 2 - Guardian Implementation (Vecka 2) 
**Deliverables:**
- [ ] Complete psutil-based system monitoring
- [ ] State machine with real thresholds (RAM/CPU/temp/battery)
- [ ] Admission control in orchestrator (429/503 responses)
- [ ] Dashboard showing red/yellow/green status

**Acceptance Criteria:**
- [ ] Brownout triggered at RAM >80% within 150ms
- [ ] Recovery to NORMAL at RAM <70% within 45s
- [ ] UI shows degradation banner during brownout
- [ ] Orchestrator blocks requests during EMERGENCY state

## Phase 3 - Voice Pipeline (Vecka 3-4)
**Deliverables:**
- [ ] Whisper.cpp integration for Swedish ASR
- [ ] Silero-VAD for voice activity detection
- [ ] Piper/VITS TTS with caching
- [ ] NLU stack (multilingual-e5 + intent classification)
- [ ] Real-time WebSocket audio streaming

**Acceptance Criteria:**
- [ ] Swedish WER ≤7% (clean audio) / ≤11% (noisy)
- [ ] TTS cached responses ≤120ms
- [ ] E2E voice latency P95 ≤2000ms
- [ ] VAD accurately detects speech start/stop

## Phase 4 - Frontend Integration (Vecka 5)
**Deliverables:**
- [ ] Complete Next.js voice interface
- [ ] Guardian-aware UX (brownout feedback)
- [ ] Real-time audio visualizer
- [ ] Performance dashboard (P50/P95, RAM, latency)

**Acceptance Criteria:**
- [ ] Three E2E flows working (quick/planner/deep)
- [ ] Guardian status visible in UI
- [ ] Voice recording/playback functional
- [ ] Responsive design (desktop + mobile)

---

# 🎯 Success Metrics & SLOs

## Technical SLOs
- **Voice Pipeline**: P95 latency <2000ms end-to-end
- **Guardian Protection**: 0 system crashes from overload
- **ASR Accuracy**: >90% for Swedish speech
- **TTS Quality**: Natural voice with mood adaptation
- **System Recovery**: <60s from emergency to normal

## User Experience Metrics
- **Graceful Degradation**: Brownout feedback instead of crashes
- **Real-time Feedback**: Partial transcripts <200ms
- **Multi-modal**: Voice + text + visual status
- **Swedish-first**: Native Swedish language support

---

**Detta är en komplett, plug-and-play spec för Opus! 🚀**

Allt som behövs finns här: exakta dependencies, implementationsstubbar, Docker config, test approach, och en detaljerad roadmap med pass/fail-kriterier. Opus kan starta direkt med Phase 1 och jobba steg-för-steg mot en fungerande Alice v2.