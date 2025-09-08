# 🎙️ Voice Pipeline Reactivation Guide
*Enterprise-Grade Swedish Voice Integration for Alice v2 Production AI System*

## 🎯 Overview

Voice pipeline reactivation för Alice v2 **enterprise-grade AI assistant** - den sista kritiska komponenten för att komplettera ett redan produktionsklart system med T1-T9 RL/ML optimization, Guardian protection, och självförbättrande intelligens.

**System Context**: Alice v2 är en **production-ready, självförbättrande AI-assistent** med:
- ✅ T1-T9 RL/ML Systems (LinUCB routing, Thompson Sampling, φ-Fibonacci optimization)
- ✅ Guardian brownout protection med NORMAL/BROWNOUT/EMERGENCY states  
- ✅ NLU Swedish processing (88%+ accuracy) med E5-embeddings + XNLI
- ✅ Smart Cache (L1/L2/L3) med semantic matching
- ✅ Enterprise security med PII-masking och policy enforcement
- ✅ Full observability med P50/P95 telemetry och energy tracking

**Current Issue**: Voice service i restart loop blockerar access till hela det magiska systemet
**Target**: Enterprise-grade Swedish voice som kompletterar befintlig AI-arkitektur

---

## 🏗️ Architecture Overview

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   Web Frontend  │    │  Alice Voice     │    │  Swedish Models │
│   (React/WS)    │◄──►│  Service 8001    │◄──►│ Whisper + Piper │
└─────────────────┘    └──────────────────┘    └─────────────────┘
                                │
                                ▼
          ┌─────────────────────────────────────────────────────────────┐
          │                Alice v2 Enterprise Core                     │
          │                                                             │
          │  NLU Svenska     Orchestrator      Guardian Protection      │
          │  (E5+XNLI)   ►   (LangGraph)   ►   (Brownout States)      │
          │     │                 │                    │               │
          │     ▼                 ▼                    ▼               │
          │  LinUCB Router    Tool Registry    Smart Cache L1/L2/L3    │
          │  (RL Bandits)     (MCP Tools)     (Semantic Matching)     │
          │     │                 │                    │               │
          │     ▼                 ▼                    ▼               │
          │  φ-Fibonacci      Memory/RAG       Security/PII           │
          │  Optimization     (FAISS+Redis)    (Policy Engine)        │
          └─────────────────────────────────────────────────────────────┘
                                │
                                ▼
                    ┌──────────────────────────┐
                    │    Telemetry/Energy      │
                    │   P50/P95/Observability  │
                    └──────────────────────────┘
```

**Enterprise Integration Components**:
- **ASR→NLU Integration**: Whisper.cpp → Alice NLU svenska processing (88%+ accuracy)
- **TTS Response Generation**: Piper svenska → Guardian-protected responses  
- **VAD+Guardian**: Real-time speech detection med brownout state awareness
- **Enterprise Caching**: TTS cache integration med Smart Cache L1/L2/L3 layers
- **RL-Optimized Streaming**: WebSocket med φ-Fibonacci latency optimization
- **Telemetry Integration**: Voice metrics → P50/P95 observability system

---

## 📁 File Structure

```
services/voice/
├── requirements.txt          # Python dependencies
├── app.py                   # FastAPI + WebSocket main server
├── asr.py                   # Whisper.cpp ASR wrapper
├── tts.py                   # Piper TTS with caching
├── vad.py                   # Voice Activity Detection
├── cache.py                 # LRU/disk cache for TTS clips
├── alice_integration.py     # Alice v2 system integration clients
└── models/                  # Voice models directory
    ├── piper/
    │   ├── sv_SE-medium.onnx    # Swedish TTS model
    │   └── sv_SE-medium.json    # Model configuration
    └── whisper-small-int8.bin   # Swedish ASR model

scripts/
└── voice_dev_setup.sh       # Model download automation

docker/
└── Dockerfile.voice         # Container build specification
```

---

## 🐳 Docker Configuration

### services.voice addition to docker-compose.yml

```yaml
services:
  alice-voice:
    build:
      context: .
      dockerfile: docker/Dockerfile.voice
    container_name: alice-voice
    restart: unless-stopped
    ports: ["8001:8001"]
    environment:
      - VAD_THRESHOLD=0.6
      - ASR_IMPL=whispercpp           # whispercpp|fasterwhisper
      - WHISPER_MODEL=models/whisper-small-int8.bin
      - PIPER_MODEL=models/piper/sv_SE-medium.onnx
      - PIPER_CONFIG=models/piper/sv_SE-medium.json
      - TTS_CACHE_DIR=/app/.tts_cache
      - MAX_STREAM_SEC=90
    volumes:
      - ./services/voice:/app
    healthcheck:
      test: ["CMD", "bash", "-lc", "curl -s http://localhost:8001/health | grep -q ok"]
      interval: 10s
      timeout: 3s
      retries: 10
      start_period: 20s
    depends_on:
      - alice-orchestrator
      - alice-guardian
```

### Dockerfile.voice

```dockerfile
FROM python:3.11-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl jq sox ffmpeg git build-essential \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY services/voice/requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt

COPY services/voice /app
RUN mkdir -p /app/.tts_cache /app/models

EXPOSE 8001
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8001", "--workers", "1"]
```

---

## 📋 Python Dependencies

```txt
# services/voice/requirements.txt
fastapi==0.111.0
uvicorn==0.30.6
httpx==0.27.2
numpy==1.26.4
soundfile==0.12.1
pydub==0.25.1
torch==2.3.1
torchaudio==2.3.1
onnxruntime==1.18.1
webrtcvad==2.0.10
aiofiles==23.2.1
```

**Architecture Decision**: Vi använder **whisper.cpp** via subprocess (stabilt, CPU-vänligt) som standard. **faster-whisper** kan aktiveras senare via `ASR_IMPL=fasterwhisper`.

---

## 🛠️ Core Implementation

### FastAPI Main Server with Alice v2 Integration (app.py)

```python
# services/voice/app.py
import os, io, time, asyncio, httpx
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel
from asr import transcribe_pcm_stream, transcribe_wav_bytes
from tts import synthesize_wav_cached
from vad import VadGate
from alice_integration import GuardianClient, NLUClient, TelemetryLogger

app = FastAPI(title="Alice Voice Enterprise", version="2.0.0")
_vad = VadGate(float(os.getenv("VAD_THRESHOLD", "0.6")))
_MAX_STREAM_SEC = int(os.getenv("MAX_STREAM_SEC", "90"))

# Alice v2 Enterprise Integration
_guardian = GuardianClient(os.getenv("GUARDIAN_URL", "http://localhost:8787"))
_nlu = NLUClient(os.getenv("NLU_URL", "http://localhost:9002"))
_telemetry = TelemetryLogger(os.getenv("ORCHESTRATOR_URL", "http://localhost:8001"))

class TTSIn(BaseModel):
    text: str

@app.get("/health")
async def health():
    """Health check with Guardian system status integration"""
    guardian_status = await _guardian.get_system_status()
    return {
        "ok": True,
        "asr": "ready",
        "tts": "ready", 
        "version": "2.0.0",
        "alice_integration": {
            "guardian_state": guardian_status.get("state", "unknown"),
            "nlu_healthy": await _nlu.health_check(),
            "telemetry_active": _telemetry.is_active()
        }
    }

@app.post("/tts")
async def tts_endpoint(inp: TTSIn):
    """Generate Swedish TTS with Guardian brownout protection"""
    start_time = time.time()
    
    # Check Guardian state before processing
    guardian_status = await _guardian.get_system_status()
    if guardian_status.get("state") == "EMERGENCY":
        raise HTTPException(status_code=503, detail="System in emergency state")
    
    try:
        wav = await synthesize_wav_cached(inp.text)
        
        # Log telemetry to Alice system
        await _telemetry.log_voice_event({
            "event": "tts_generation",
            "text_length": len(inp.text),
            "duration_ms": (time.time() - start_time) * 1000,
            "guardian_state": guardian_status.get("state")
        })
        
        return StreamingResponse(io.BytesIO(wav), media_type="audio/wav")
        
    except Exception as e:
        await _telemetry.log_voice_error("tts_generation", str(e))
        raise HTTPException(status_code=500, detail="TTS generation failed")

@app.post("/asr")
async def asr_endpoint(raw: bytes):
    """Transcribe Swedish audio with NLU integration"""
    start_time = time.time()
    
    try:
        # Step 1: ASR - Audio to text
        text = await transcribe_wav_bytes(raw)
        
        # Step 2: NLU - Extract intent and mood from Alice NLU system
        nlu_result = await _nlu.process_text(text)
        
        # Log to Alice telemetry system
        await _telemetry.log_voice_event({
            "event": "asr_transcription", 
            "audio_duration_estimate": len(raw) / 32000,  # ~16kHz mono
            "transcribed_length": len(text),
            "duration_ms": (time.time() - start_time) * 1000,
            "nlu_intent": nlu_result.get("intent"),
            "nlu_confidence": nlu_result.get("confidence")
        })
        
        return JSONResponse({
            "text": text,
            "language": "sv",
            "alice_nlu": nlu_result,
            "processing_time_ms": (time.time() - start_time) * 1000
        })
        
    except Exception as e:
        await _telemetry.log_voice_error("asr_transcription", str(e))
        raise HTTPException(status_code=500, detail="ASR transcription failed")

@app.websocket("/ws/stream")
async def ws_stream(ws: WebSocket):
    """Real-time streaming ASR with VAD"""
    await ws.accept()
    started = time.time()
    pcm_buffer = bytearray()
    
    try:
        await ws.send_json({"event":"ready", "timestamp": started})
        
        while True:
            if time.time() - started > _MAX_STREAM_SEC:
                await ws.send_json({"event":"timeout"})
                break
                
            chunk = await ws.receive_bytes()
            pcm_buffer.extend(chunk)
            
            if _vad.is_speech(chunk):
                # Send partial transcription every ~1 second
                if len(pcm_buffer) > 32000:  # ~1s @16k mono
                    partial = await transcribe_pcm_stream(bytes(pcm_buffer))
                    await ws.send_json({
                        "event": "partial",
                        "text": partial,
                        "timestamp": time.time()
                    })
                    pcm_buffer.clear()
                    
    except WebSocketDisconnect:
        pass
    finally:
        # Final transcription of remaining buffer
        if pcm_buffer:
            final = await transcribe_pcm_stream(bytes(pcm_buffer))
            await ws.send_json({
                "event": "final",
                "text": final,
                "timestamp": time.time()
            })
        await ws.close()
```

### ASR Implementation (asr.py)

```python
# services/voice/asr.py
import os, subprocess, tempfile, asyncio
import wave, io

ASR_IMPL = os.getenv("ASR_IMPL", "whispercpp")
WHISPER_MODEL = os.getenv("WHISPER_MODEL", "models/whisper-small-int8.bin")

async def transcribe_wav_bytes(wav_bytes: bytes) -> str:
    """Transcribe WAV audio bytes to Swedish text"""
    if ASR_IMPL == "whispercpp":
        return await _whispercpp_transcribe(wav_bytes)
    else:
        # Future: faster-whisper implementation
        return await _whispercpp_transcribe(wav_bytes)

async def transcribe_pcm_stream(pcm_bytes: bytes) -> str:
    """Transcribe PCM stream with WAV header wrapper"""
    # Convert PCM to WAV format for whisper.cpp
    wav_buf = io.BytesIO()
    with wave.open(wav_buf, 'wb') as wf:
        wf.setnchannels(1)      # Mono
        wf.setsampwidth(2)      # 16-bit
        wf.setframerate(16000)  # 16kHz
        wf.writeframes(pcm_bytes)
    
    return await transcribe_wav_bytes(wav_buf.getvalue())

async def _whispercpp_transcribe(wav_bytes: bytes) -> str:
    """Execute whisper.cpp binary for transcription"""
    with tempfile.NamedTemporaryFile(suffix=".wav") as tmp:
        tmp.write(wav_bytes)
        tmp.flush()
        
        cmd = [
            "main",                # whisper.cpp binary name
            "-m", WHISPER_MODEL,   # Model path
            "-f", tmp.name,        # Input file
            "-l", "sv",           # Swedish language
            "-nt"                 # No timestamps (faster)
        ]
        
        proc = await asyncio.create_subprocess_exec(
            *cmd, 
            stdout=subprocess.PIPE, 
            stderr=subprocess.PIPE
        )
        
        stdout, stderr = await proc.communicate()
        
        if proc.returncode != 0:
            print(f"Whisper error: {stderr.decode()}")
            return ""
            
        text = stdout.decode("utf-8", errors="ignore").strip()
        return text
```

### TTS Implementation (tts.py)

```python
# services/voice/tts.py
import os, hashlib, subprocess, tempfile, asyncio
import aiofiles

PIPER_MODEL = os.getenv("PIPER_MODEL", "models/piper/sv_SE-medium.onnx")
PIPER_CONFIG = os.getenv("PIPER_CONFIG", "models/piper/sv_SE-medium.json")
CACHE_DIR = os.getenv("TTS_CACHE_DIR", "/app/.tts_cache")

# Ensure cache directory exists
os.makedirs(CACHE_DIR, exist_ok=True)

def _cache_key(text: str) -> str:
    """Generate cache key from text"""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()

async def synthesize_wav_cached(text: str) -> bytes:
    """Generate Swedish TTS with intelligent caching"""
    cache_key = _cache_key(text)
    cache_path = os.path.join(CACHE_DIR, f"{cache_key}.wav")
    
    # Check cache first
    if os.path.exists(cache_path):
        async with aiofiles.open(cache_path, "rb") as f:
            return await f.read()
    
    # Generate new audio
    wav_data = await _piper_synthesize(text)
    
    # Save to cache
    async with aiofiles.open(cache_path, "wb") as f:
        await f.write(wav_data)
    
    return wav_data

async def _piper_synthesize(text: str) -> bytes:
    """Execute Piper TTS binary for Swedish synthesis"""
    with tempfile.NamedTemporaryFile(suffix=".wav") as tmp:
        cmd = [
            "piper",                # Piper binary
            "--model", PIPER_MODEL, # Swedish model
            "--config", PIPER_CONFIG,
            "--output_file", tmp.name,
        ]
        
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        
        stdout, stderr = await proc.communicate(input=text.encode("utf-8"))
        
        if proc.returncode != 0:
            print(f"Piper error: {stderr.decode()}")
            return b""
        
        # Read generated audio file
        with open(tmp.name, "rb") as f:
            return f.read()
```

### Alice v2 Integration Clients (alice_integration.py)

```python
# services/voice/alice_integration.py
import httpx
import asyncio
import json
from typing import Dict, Any, Optional

class GuardianClient:
    """Integration with Alice v2 Guardian brownout protection system"""
    
    def __init__(self, guardian_url: str):
        self.guardian_url = guardian_url
        self.client = httpx.AsyncClient(timeout=1.0)
        
    async def get_system_status(self) -> Dict[str, Any]:
        """Get current Guardian system state (NORMAL/BROWNOUT/EMERGENCY)"""
        try:
            response = await self.client.get(f"{self.guardian_url}/status")
            if response.status_code == 200:
                return response.json()
            return {"state": "unknown", "error": f"HTTP {response.status_code}"}
        except Exception as e:
            return {"state": "error", "error": str(e)}
    
    async def report_voice_metrics(self, metrics: Dict[str, Any]) -> bool:
        """Report voice service metrics to Guardian for brownout decisions"""
        try:
            response = await self.client.post(
                f"{self.guardian_url}/metrics/voice",
                json=metrics
            )
            return response.status_code == 200
        except Exception:
            return False

class NLUClient:
    """Integration with Alice v2 NLU Swedish processing system"""
    
    def __init__(self, nlu_url: str):
        self.nlu_url = nlu_url
        self.client = httpx.AsyncClient(timeout=2.0)
        
    async def health_check(self) -> bool:
        """Check if NLU service is responsive"""
        try:
            response = await self.client.get(f"{self.nlu_url}/health")
            return response.status_code == 200
        except Exception:
            return False
    
    async def process_text(self, text: str) -> Dict[str, Any]:
        """Process Swedish text through Alice NLU system"""
        try:
            response = await self.client.post(
                f"{self.nlu_url}/process",
                json={
                    "text": text,
                    "language": "sv",
                    "source": "voice_asr"
                }
            )
            
            if response.status_code == 200:
                result = response.json()
                return {
                    "intent": result.get("intent", "unknown"),
                    "confidence": result.get("confidence", 0.0),
                    "mood_score": result.get("mood_score", 0.5),
                    "slots": result.get("slots", {}),
                    "route_hint": result.get("route_hint", "micro")
                }
            else:
                return {"intent": "nlu_error", "confidence": 0.0}
                
        except Exception as e:
            return {"intent": "nlu_exception", "confidence": 0.0, "error": str(e)}

class TelemetryLogger:
    """Integration with Alice v2 telemetry and observability system"""
    
    def __init__(self, orchestrator_url: str):
        self.orchestrator_url = orchestrator_url
        self.client = httpx.AsyncClient(timeout=1.0)
        self.active = True
        
    def is_active(self) -> bool:
        return self.active
    
    async def log_voice_event(self, event_data: Dict[str, Any]) -> bool:
        """Log voice event to Alice telemetry system"""
        try:
            telemetry_data = {
                "timestamp": event_data.get("timestamp", asyncio.get_event_loop().time()),
                "service": "voice",
                "event_type": event_data.get("event", "unknown"),
                "data": event_data,
                "source": "alice_voice_service"
            }
            
            response = await self.client.post(
                f"{self.orchestrator_url}/telemetry/voice",
                json=telemetry_data
            )
            
            return response.status_code == 200
            
        except Exception:
            return False
    
    async def log_voice_error(self, operation: str, error_msg: str) -> bool:
        """Log voice service error to Alice monitoring"""
        return await self.log_voice_event({
            "event": "voice_error",
            "operation": operation,
            "error_message": error_msg,
            "severity": "error"
        })

class CacheIntegration:
    """Integration with Alice v2 Smart Cache L1/L2/L3 system"""
    
    def __init__(self, cache_url: str):
        self.cache_url = cache_url
        self.client = httpx.AsyncClient(timeout=0.5)
    
    async def get_cached_tts(self, text_hash: str) -> Optional[bytes]:
        """Check Alice Smart Cache for pre-generated TTS"""
        try:
            response = await self.client.get(f"{self.cache_url}/tts/{text_hash}")
            if response.status_code == 200:
                return response.content
            return None
        except Exception:
            return None
    
    async def cache_tts_result(self, text_hash: str, audio_data: bytes) -> bool:
        """Store TTS result in Alice Smart Cache system"""
        try:
            response = await self.client.put(
                f"{self.cache_url}/tts/{text_hash}",
                content=audio_data,
                headers={"Content-Type": "audio/wav"}
            )
            return response.status_code == 200
        except Exception:
            return False
```

### Voice Activity Detection (vad.py)

```python
# services/voice/vad.py
import webrtcvad

class VadGate:
    """Voice Activity Detection using WebRTC VAD"""
    
    def __init__(self, threshold: float = 0.6):
        self.vad = webrtcvad.Vad(2)  # Aggressiveness 0-3
        self.threshold = threshold

    def is_speech(self, pcm_bytes: bytes) -> bool:
        """Detect if audio frame contains speech"""
        # WebRTC VAD expects 20ms frames @16kHz mono, 16-bit
        frame_size = 640  # 20ms * 16kHz * 2 bytes
        
        if len(pcm_bytes) < frame_size:
            # Pad with zeros if frame too short
            frame = pcm_bytes + b"\x00" * (frame_size - len(pcm_bytes))
        else:
            frame = pcm_bytes[:frame_size]
        
        try:
            return self.vad.is_speech(frame, 16000)
        except Exception as e:
            print(f"VAD error: {e}")
            return False
```

---

## 🚀 Setup & Deployment

### Model Download Script

```bash
#!/usr/bin/env bash
# scripts/voice_dev_setup.sh
set -euo pipefail

cd "$(dirname "$0")/.."
VOICE_DIR="services/voice/models"
mkdir -p "$VOICE_DIR/piper"

echo "🎙️ Setting up Alice Voice Pipeline models..."

# Download Piper Swedish TTS model
if [ ! -f "$VOICE_DIR/piper/sv_SE-medium.onnx" ]; then
    echo "📥 Downloading Piper Swedish TTS model..."
    curl -L -o "$VOICE_DIR/piper/sv_SE-medium.onnx" \
        "https://huggingface.co/rhasspy/piper-voices/resolve/main/sv/sv_SE/medium/sv_SE-medium.onnx"
    curl -L -o "$VOICE_DIR/piper/sv_SE-medium.json" \
        "https://huggingface.co/rhasspy/piper-voices/resolve/main/sv/sv_SE/medium/sv_SE-medium.onnx.json"
    echo "✅ Piper Swedish model downloaded"
fi

# Download Whisper.cpp model
if [ ! -f "$VOICE_DIR/whisper-small-int8.bin" ]; then
    echo "📥 Downloading Whisper ASR model..."
    curl -L -o "$VOICE_DIR/whisper-small-int8.bin" \
        "https://ggml.ggerganov.com/ggml-model-whisper-small-q5_1.bin"
    echo "✅ Whisper model downloaded"
fi

echo "🎯 Voice pipeline models ready!"
echo "Next steps:"
echo "  make voice-dev    # Build and start voice service"
echo "  make voice-test   # Test TTS and health endpoints"
```

### Makefile Integration

```make
# Makefile additions
.PHONY: voice-setup voice-dev voice-up voice-logs voice-test voice-restart

voice-setup:
	@echo "🎙️ Setting up voice pipeline..."
	bash scripts/voice_dev_setup.sh

voice-dev: voice-setup
	@echo "🚀 Building and starting voice service..."
	docker compose build alice-voice
	docker compose up -d alice-voice

voice-up:
	@echo "▶️ Starting voice service..."
	docker compose up -d alice-voice

voice-restart:
	@echo "🔄 Restarting voice service..."
	docker compose restart alice-voice

voice-logs:
	@echo "📋 Voice service logs..."
	docker compose logs -f alice-voice

voice-test:
	@echo "🧪 Testing voice pipeline..."
	@echo "Health check:"
	curl -sS http://localhost:8001/health | jq .
	@echo "\n🔊 TTS Test:"
	curl -sS -X POST http://localhost:8001/tts \
		-H 'Content-Type: application/json' \
		-d '{"text":"Hej! Jag är Alice, din svenska AI-assistent."}' \
		-o /tmp/alice_tts_test.wav
	@if command -v afplay >/dev/null 2>&1; then \
		echo "Playing test audio..."; \
		afplay /tmp/alice_tts_test.wav; \
	else \
		echo "Audio saved to /tmp/alice_tts_test.wav"; \
	fi

voice-down:
	@echo "⏹️ Stopping voice service..."
	docker compose stop alice-voice
```

---

## 🔧 Ollama Watchdog Integration

För att säkerställa att Ollama aldrig igen orsakar systemkrascher:

### Watchdog Service Structure

```
services/watchdog/
├── requirements.txt
├── ollama_watchdog.py
└── health_monitor.py

docker/
└── Dockerfile.watchdog
```

### Watchdog Implementation

```python
# services/watchdog/ollama_watchdog.py
import os, time, httpx, sys
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

OLLAMA_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
ORCH_FLAG_URL = os.getenv("ORCH_FLAG_URL", "http://localhost:8001/admin/micro/disable")
CHECK_INTERVAL = int(os.getenv("CHECK_INTERVAL", "5"))
FAILURE_THRESHOLD = int(os.getenv("FAILURE_THRESHOLD", "30"))

def check_ollama_health() -> bool:
    """Check if Ollama service is responsive"""
    try:
        response = httpx.get(f"{OLLAMA_URL}/api/version", timeout=2.0)
        return response.status_code == 200
    except Exception as e:
        logger.warning(f"Ollama health check failed: {e}")
        return False

def flag_orchestrator_disable():
    """Signal orchestrator to disable micro route"""
    try:
        response = httpx.post(ORCH_FLAG_URL, timeout=1.0)
        if response.status_code == 200:
            logger.info("Successfully flagged orchestrator to disable micro route")
        else:
            logger.error(f"Failed to flag orchestrator: {response.status_code}")
    except Exception as e:
        logger.error(f"Error flagging orchestrator: {e}")

def main():
    """Main watchdog loop"""
    logger.info("🐕 Ollama Watchdog started")
    bad_since = None
    
    while True:
        is_healthy = check_ollama_health()
        
        if not is_healthy:
            if bad_since is None:
                bad_since = time.time()
                logger.warning("Ollama appears unhealthy - starting timer")
            
            # After threshold seconds of failure, flag orchestrator
            elapsed = time.time() - bad_since
            if elapsed > FAILURE_THRESHOLD:
                logger.error(f"Ollama unhealthy for {elapsed:.1f}s - flagging orchestrator")
                flag_orchestrator_disable()
                bad_since = None  # Reset timer after flagging
                
        else:
            if bad_since is not None:
                logger.info("Ollama recovered - clearing failure timer")
                bad_since = None
        
        time.sleep(CHECK_INTERVAL)

if __name__ == "__main__":
    main()
```

### Docker Compose Integration

```yaml
# Add to docker-compose.yml
services:
  alice-watchdog:
    build:
      context: .
      dockerfile: docker/Dockerfile.watchdog
    container_name: alice-watchdog
    restart: unless-stopped
    environment:
      - OLLAMA_BASE_URL=http://alice-ollama:11434
      - ORCH_FLAG_URL=http://alice-orchestrator:8000/admin/micro/disable
      - CHECK_INTERVAL=5
      - FAILURE_THRESHOLD=30
    depends_on:
      - alice-ollama
      - alice-orchestrator
    healthcheck:
      test: ["CMD", "python", "-c", "import httpx; httpx.get('http://localhost:11434/api/version')"]
      interval: 30s
      timeout: 5s
      retries: 3
```

---

## 🌐 Frontend Integration Hooks

Voice pipeline är designad för enkel integration med framtida React/Next.js frontend:

### WebSocket Integration Example

```typescript
// Frontend WebSocket client example
class AliceVoiceClient {
    private ws: WebSocket | null = null;
    private audioContext: AudioContext;
    
    constructor() {
        this.audioContext = new AudioContext();
    }
    
    connect(): Promise<void> {
        return new Promise((resolve, reject) => {
            this.ws = new WebSocket("ws://localhost:8001/ws/stream");
            
            this.ws.onopen = () => {
                console.log("🎙️ Voice pipeline connected");
                resolve();
            };
            
            this.ws.onmessage = (event) => {
                const data = JSON.parse(event.data);
                this.handleVoiceEvent(data);
            };
            
            this.ws.onerror = reject;
        });
    }
    
    private handleVoiceEvent(event: any) {
        switch(event.event) {
            case "ready":
                console.log("Voice pipeline ready");
                break;
            case "partial":
                this.onPartialTranscription(event.text);
                break;
            case "final":
                this.onFinalTranscription(event.text);
                break;
        }
    }
    
    sendAudioChunk(pcmData: ArrayBuffer) {
        if (this.ws?.readyState === WebSocket.OPEN) {
            this.ws.send(pcmData);
        }
    }
}
```

### TTS Integration Example

```typescript
// Frontend TTS client example
async function playAliceResponse(text: string): Promise<void> {
    const response = await fetch("http://localhost:8001/tts", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ text })
    });
    
    if (response.ok) {
        const audioBlob = await response.blob();
        const audioUrl = URL.createObjectURL(audioBlob);
        const audio = new Audio(audioUrl);
        
        return new Promise((resolve) => {
            audio.onended = () => {
                URL.revokeObjectURL(audioUrl);
                resolve();
            };
            audio.play();
        });
    }
}
```

---

## ✅ Implementation Steps

### Phase 1: Core Setup (Week 1)

1. **Model Preparation**
   ```bash
   make voice-setup    # Download Swedish models
   ```

2. **Service Deployment**
   ```bash
   make voice-dev      # Build and start voice service
   make voice-test     # Verify TTS functionality
   ```

3. **Health Verification**
   ```bash
   curl http://localhost:8001/health
   # Expected: {"ok": true, "asr": "ready", "tts": "ready"}
   ```

### Phase 2: Integration (Week 2)

1. **Orchestrator Integration**
   - Add voice service endpoints to orchestrator routing
   - Implement admin flag endpoint for watchdog
   - Test full pipeline integration

2. **Watchdog Deployment**
   ```bash
   docker compose up -d alice-watchdog
   ```

3. **End-to-End Testing**
   - WebSocket streaming test
   - TTS generation and playback
   - ASR accuracy validation with Swedish content

### Phase 3: Optimization (Week 3)

1. **Performance Tuning**
   - TTS cache optimization
   - VAD threshold adjustment for Swedish speech patterns
   - Latency optimization (<2s target)

2. **Production Readiness**
   - Error handling and recovery mechanisms
   - Monitoring and logging enhancement
   - Resource usage optimization

---

## 🎯 Success Criteria

### Performance Targets
- **TTS Latency**: <2 seconds for typical responses
- **ASR Accuracy**: >90% for clear Swedish speech
- **Service Uptime**: 99.9% availability
- **Cache Hit Rate**: >80% for repeated phrases

### Quality Targets
- **Swedish Language Support**: Native speaker quality TTS
- **Real-time Streaming**: <100ms perceived delay in conversations
- **Resource Efficiency**: <512MB memory usage per service
- **Error Recovery**: Automatic restart and health reporting

### Integration Targets
- **Orchestrator Integration**: Seamless routing to voice endpoints
- **Frontend Ready**: WebSocket and REST APIs ready for UI
- **Monitoring**: Complete health checks and telemetry
- **Production Deploy**: Docker compose one-command deployment

---

## 🔗 Links & References

- **Swedish TTS Models**: [Piper Voices](https://huggingface.co/rhasspy/piper-voices)
- **Swedish ASR**: [Whisper.cpp](https://github.com/ggerganov/whisper.cpp)
- **Voice Activity Detection**: [WebRTC VAD](https://github.com/wiseman/py-webrtcvad)
- **Audio Processing**: [SoX](https://sox.sourceforge.net/)

---

*Created: 2025-09-08 | Voice Pipeline Reactivation*  
*Status: Ready for Implementation | Priority: HIGHEST after Frontend*  
*Target: Production-ready Swedish voice pipeline for Alice v2*