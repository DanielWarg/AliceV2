"""
Voice Tools for Alice Orchestrator
MCP tools for local speech-to-text and text-to-speech
"""

import base64
import tempfile
from pathlib import Path
from typing import Any, Dict

import httpx
import structlog

logger = structlog.get_logger(__name__)

# Tool schemas
STT_TOOL_SCHEMA = {
    "name": "stt_local",
    "description": "Convert speech to text using local Whisper model",
    "parameters": {
        "type": "object",
        "properties": {
            "audio_data": {
                "type": "string",
                "description": "Base64 encoded WAV audio data",
            },
            "language": {
                "type": "string",
                "description": "Language code (e.g., 'sv', 'en')",
                "default": "sv",
            },
        },
        "required": ["audio_data"],
    },
}

TTS_TOOL_SCHEMA = {
    "name": "tts_local",
    "description": "Convert text to speech using local TTS model",
    "parameters": {
        "type": "object",
        "properties": {
            "text": {"type": "string", "description": "Text to convert to speech"},
            "voice": {
                "type": "string",
                "description": "Voice preset (alice_neutral, alice_happy, alice_empathetic)",
                "default": "alice_neutral",
            },
            "speed": {
                "type": "number",
                "description": "Speech rate (0.5-2.0)",
                "default": 1.0,
            },
        },
        "required": ["text"],
    },
}

SOCIAL_BENCHMARK_TOOL_SCHEMA = {
    "name": "social_benchmark",
    "description": "Run social intelligence benchmark with local agents",
    "parameters": {
        "type": "object",
        "properties": {
            "scenario": {
                "type": "string",
                "description": "Benchmark scenario (werewolf_light, negotiation, collaboration)",
                "default": "werewolf_light",
            },
            "rounds": {
                "type": "integer",
                "description": "Number of rounds to run",
                "default": 5,
            },
        },
    },
}


class VoiceTools:
    """Voice processing tools for local STT and TTS"""

    def __init__(self):
        self.stt_url = "http://voice:8001/api/stt"
        self.tts_url = "http://voice:8001/api/tts"
        self.benchmark_url = "http://voice:8001/api/benchmark"

    async def stt_local(self, audio_data: str, language: str = "sv") -> Dict[str, Any]:
        """Convert speech to text using local Whisper"""
        try:
            # Decode base64 audio
            audio_bytes = base64.b64decode(audio_data)

            # Create temporary WAV file
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as temp_file:
                temp_file.write(audio_bytes)
                temp_file_path = temp_file.name

            # Send to STT service
            async with httpx.AsyncClient(timeout=30.0) as client:
                with open(temp_file_path, "rb") as f:
                    files = {"audio": ("audio.wav", f, "audio/wav")}
                    data = {"language": language}

                    response = await client.post(self.stt_url, files=files, data=data)
                    response.raise_for_status()

                    result = response.json()

                    # Clean up temp file
                    Path(temp_file_path).unlink()

                    return {
                        "success": True,
                        "text": result.get("text", ""),
                        "confidence": result.get("confidence", 0.0),
                        "language": result.get("language", language),
                        "processing_time_ms": result.get("processing_time_ms", 0),
                    }

        except Exception as e:
            logger.error("STT processing failed", error=str(e))
            return {"success": False, "error": str(e), "text": "", "confidence": 0.0}

    async def tts_local(
        self, text: str, voice: str = "alice_neutral", speed: float = 1.0
    ) -> Dict[str, Any]:
        """Convert text to speech using local TTS"""
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    self.tts_url, json={"text": text, "voice": voice, "speed": speed}
                )
                response.raise_for_status()

                result = response.json()

                return {
                    "success": True,
                    "audio_data": result.get("audio_data", ""),  # Base64 encoded
                    "duration_ms": result.get("duration_ms", 0),
                    "processing_time_ms": result.get("processing_time_ms", 0),
                }

        except Exception as e:
            logger.error("TTS processing failed", error=str(e))
            return {"success": False, "error": str(e), "audio_data": ""}

    async def social_benchmark(
        self, scenario: str = "werewolf_light", rounds: int = 5
    ) -> Dict[str, Any]:
        """Run social intelligence benchmark"""
        try:
            async with httpx.AsyncClient(timeout=120.0) as client:
                response = await client.post(
                    self.benchmark_url, json={"scenario": scenario, "rounds": rounds}
                )
                response.raise_for_status()

                result = response.json()

                return {
                    "success": True,
                    "social_score": result.get("social_score", 0.0),
                    "consistency": result.get("consistency", 0.0),
                    "adaptation": result.get("adaptation", 0.0),
                    "tone": result.get("tone", 0.0),
                    "rounds_completed": result.get("rounds_completed", 0),
                    "processing_time_ms": result.get("processing_time_ms", 0),
                }

        except Exception as e:
            logger.error("Social benchmark failed", error=str(e))
            return {"success": False, "error": str(e), "social_score": 0.0}


# Global instance
voice_tools = VoiceTools()


# Tool registration functions
def get_voice_tools() -> Dict[str, Any]:
    """Get voice tool schemas and functions"""
    return {
        "stt_local": {"schema": STT_TOOL_SCHEMA, "function": voice_tools.stt_local},
        "tts_local": {"schema": TTS_TOOL_SCHEMA, "function": voice_tools.tts_local},
        "social_benchmark": {
            "schema": SOCIAL_BENCHMARK_TOOL_SCHEMA,
            "function": voice_tools.social_benchmark,
        },
    }
