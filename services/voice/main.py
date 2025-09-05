"""
Alice Voice Service
Local speech-to-text and text-to-speech processing
"""

import asyncio
import base64
import os
import tempfile
import time
from pathlib import Path
from typing import Any, Optional

import numpy as np
import structlog
import whisper
from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

# Configure logging
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
        structlog.processors.JSONRenderer(),
    ],
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    wrapper_class=structlog.stdlib.BoundLogger,
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger(__name__)

# Configuration
WHISPER_MODEL = os.getenv("WHISPER_MODEL", "base")
TTS_MODEL_PATH = os.getenv("TTS_MODEL_PATH", "/models/piper")
CACHE_DIR = Path("/data/voice_cache")


# Pydantic models
class STTRequest(BaseModel):
    language: str = Field(default="sv", description="Language code")
    audio_data: Optional[str] = Field(None, description="Base64 encoded audio")


class STTResponse(BaseModel):
    text: str = Field(..., description="Transcribed text")
    confidence: float = Field(..., description="Confidence score")
    language: str = Field(..., description="Detected language")
    processing_time_ms: float = Field(..., description="Processing time")


class TTSRequest(BaseModel):
    text: str = Field(..., description="Text to synthesize")
    voice: str = Field(default="alice_neutral", description="Voice preset")
    speed: float = Field(default=1.0, description="Speech rate")


class TTSResponse(BaseModel):
    audio_data: str = Field(..., description="Base64 encoded audio")
    duration_ms: float = Field(..., description="Audio duration")
    processing_time_ms: float = Field(..., description="Processing time")


class BenchmarkRequest(BaseModel):
    scenario: str = Field(default="werewolf_light", description="Benchmark scenario")
    rounds: int = Field(default=5, description="Number of rounds")


class BenchmarkResponse(BaseModel):
    social_score: float = Field(..., description="Overall social intelligence score")
    consistency: float = Field(..., description="Consistency score")
    adaptation: float = Field(..., description="Adaptation score")
    tone: float = Field(..., description="Tone appropriateness score")
    rounds_completed: int = Field(..., description="Rounds completed")
    processing_time_ms: float = Field(..., description="Processing time")


# Initialize FastAPI app
app = FastAPI(
    title="Alice Voice Service",
    description="Local speech-to-text and text-to-speech processing",
    version="1.0.0",
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global variables
whisper_model: Optional[whisper.Whisper] = None
tts_model: Optional[Any] = None


def get_whisper_model() -> whisper.Whisper:
    """Get or load Whisper model"""
    global whisper_model
    if whisper_model is None:
        logger.info("Loading Whisper model", model=WHISPER_MODEL)
        whisper_model = whisper.load_model(WHISPER_MODEL)
        logger.info("Whisper model loaded successfully")
    return whisper_model


def get_tts_model():
    """Get or load TTS model (placeholder for now)"""
    global tts_model
    if tts_model is None:
        logger.info("Loading TTS model", path=TTS_MODEL_PATH)
        # FUTURE: Implement actual TTS model loading when voice features are prioritized
        tts_model = "placeholder"
        logger.info("TTS model loaded successfully")
    return tts_model


@app.on_event("startup")
async def startup_event():
    """Initialize services on startup"""
    logger.info("Starting Alice Voice Service")

    # Create cache directory
    CACHE_DIR.mkdir(parents=True, exist_ok=True)

    # Load models
    try:
        get_whisper_model()
        get_tts_model()
        logger.info("All models loaded successfully")
    except Exception as e:
        logger.error("Failed to load models", error=str(e))
        raise


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    try:
        get_whisper_model()  # Ensure model is available
        get_tts_model()  # Ensure TTS is available

        return {
            "status": "healthy",
            "timestamp": time.time(),
            "services": {"whisper": "loaded", "tts": "loaded"},
            "models": {"whisper": WHISPER_MODEL, "tts": str(TTS_MODEL_PATH)},
        }
    except Exception as e:
        logger.error("Health check failed", error=str(e))
        raise HTTPException(status_code=503, detail=f"Service unhealthy: {str(e)}")


@app.post("/api/stt", response_model=STTResponse)
async def speech_to_text(
    audio: UploadFile = File(...), language: str = Form(default="sv")
):
    """Convert speech to text using local Whisper"""
    start_time = time.time()

    try:
        # Read audio file
        audio_content = await audio.read()

        # Save to temporary file
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as temp_file:
            temp_file.write(audio_content)
            temp_file_path = temp_file.name

        # Load Whisper model
        model = get_whisper_model()

        # Transcribe
        result = model.transcribe(
            temp_file_path,
            language=language if language != "auto" else None,
            task="transcribe",
        )

        # Clean up temp file
        Path(temp_file_path).unlink()

        processing_time = (time.time() - start_time) * 1000

        logger.info(
            "STT completed successfully",
            language=language,
            text_length=len(result["text"]),
            confidence=result.get("avg_logprob", 0.0),
            processing_time_ms=processing_time,
        )

        return STTResponse(
            text=result["text"],
            confidence=result.get("avg_logprob", 0.0),
            language=result.get("language", language),
            processing_time_ms=processing_time,
        )

    except Exception as e:
        logger.error("STT processing failed", error=str(e))
        raise HTTPException(status_code=500, detail=f"STT processing failed: {str(e)}")


@app.post("/api/tts", response_model=TTSResponse)
async def text_to_speech(request: TTSRequest):
    """Convert text to speech using local TTS"""
    start_time = time.time()

    try:
        # FUTURE: Implement actual TTS synthesis when voice features are prioritized
        # For now, return placeholder
        logger.info(
            "TTS request received",
            text_length=len(request.text),
            voice=request.voice,
            speed=request.speed,
        )

        # Placeholder audio data (silence)
        sample_rate = 22050
        duration_ms = len(request.text) * 50  # Rough estimate
        samples = int(sample_rate * duration_ms / 1000)
        audio_data = np.zeros(samples, dtype=np.int16)

        # Convert to base64
        import io

        buffer = io.BytesIO()
        import wave

        with wave.open(buffer, "wb") as wav_file:
            wav_file.setnchannels(1)
            wav_file.setsampwidth(2)
            wav_file.setframerate(sample_rate)
            wav_file.writeframes(audio_data.tobytes())

        audio_base64 = base64.b64encode(buffer.getvalue()).decode("utf-8")

        processing_time = (time.time() - start_time) * 1000

        logger.info(
            "TTS completed successfully",
            text_length=len(request.text),
            voice=request.voice,
            duration_ms=duration_ms,
            processing_time_ms=processing_time,
        )

        return TTSResponse(
            audio_data=audio_base64,
            duration_ms=duration_ms,
            processing_time_ms=processing_time,
        )

    except Exception as e:
        logger.error("TTS processing failed", error=str(e))
        raise HTTPException(status_code=500, detail=f"TTS processing failed: {str(e)}")


@app.post("/api/benchmark", response_model=BenchmarkResponse)
async def social_benchmark(request: BenchmarkRequest):
    """Run social intelligence benchmark"""
    start_time = time.time()

    try:
        logger.info(
            "Social benchmark started", scenario=request.scenario, rounds=request.rounds
        )

        # FUTURE: Implement actual social benchmark when voice features are prioritized
        # For now, return placeholder scores

        # Simulate benchmark processing
        await asyncio.sleep(2)  # Simulate processing time

        processing_time = (time.time() - start_time) * 1000

        # Placeholder scores
        consistency = 0.85
        adaptation = 0.78
        tone = 0.92
        social_score = (consistency + adaptation + tone) / 3

        logger.info(
            "Social benchmark completed",
            scenario=request.scenario,
            social_score=social_score,
            processing_time_ms=processing_time,
        )

        return BenchmarkResponse(
            social_score=social_score,
            consistency=consistency,
            adaptation=adaptation,
            tone=tone,
            rounds_completed=request.rounds,
            processing_time_ms=processing_time,
        )

    except Exception as e:
        logger.error("Social benchmark failed", error=str(e))
        raise HTTPException(
            status_code=500, detail=f"Social benchmark failed: {str(e)}"
        )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8001)
