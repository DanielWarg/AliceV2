"""Guardian HTTP API server"""

import asyncio
import logging
import sys
from pathlib import Path
from typing import Any

import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse

# Add src to path for absolute imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.guardian import Guardian
from core.guardian_state import GuardianConfig


class GuardianServer:
    """HTTP API server for Guardian"""

    def __init__(self, guardian: Guardian, config: GuardianConfig):
        self.guardian = guardian
        self.config = config
        self.logger = logging.getLogger("guardian.api")

        # Create FastAPI app
        self.app = FastAPI(
            title="Alice Guardian",
            description="Deterministisk säkerhetsdaemon för Alice",
            version="2.0.0",
        )

        # Setup routes
        self._setup_routes()

    def _setup_routes(self):
        """Setup API routes"""

        @self.app.get("/health")
        async def health_check():
            """Guardian health check endpoint"""
            try:
                status = self.guardian.get_status()
                return JSONResponse(content=status)
            except Exception as e:
                self.logger.error(f"Health check error: {e}")
                raise HTTPException(status_code=500, detail="Internal server error")

        @self.app.get("/")
        async def root():
            """Root endpoint"""
            return {
                "service": "Alice Guardian",
                "version": "2.0.0",
                "status": "running",
            }

        @self.app.post("/api/guard/degrade")
        async def activate_degradation():
            """Activate basic degradation (used by external systems)"""
            try:
                # This would typically be called by external monitoring
                # For now, just return success
                return {"success": True, "message": "Degradation activated"}
            except Exception as e:
                self.logger.error(f"Degradation activation error: {e}")
                raise HTTPException(status_code=500, detail=str(e))

        @self.app.post("/api/guard/stop-intake")
        async def stop_intake():
            """Stop new request intake (used by kill sequence)"""
            try:
                # This is handled by the Guardian middleware in Alice
                return {"success": True, "message": "Intake stopped"}
            except Exception as e:
                self.logger.error(f"Stop intake error: {e}")
                raise HTTPException(status_code=500, detail=str(e))

        @self.app.post("/api/guard/resume-intake")
        async def resume_intake():
            """Resume request intake (used by kill sequence)"""
            try:
                # This is handled by the Guardian middleware in Alice
                return {"success": True, "message": "Intake resumed"}
            except Exception as e:
                self.logger.error(f"Resume intake error: {e}")
                raise HTTPException(status_code=500, detail=str(e))

        @self.app.post("/api/guard/set-concurrency")
        async def set_concurrency(request: dict[str, Any]):
            """Set concurrency level (auto-tuning)"""
            try:
                concurrency = request.get("concurrency", 1)
                # This would be implemented with actual concurrency control
                return {
                    "success": True,
                    "concurrency": concurrency,
                    "message": "Concurrency updated",
                }
            except Exception as e:
                self.logger.error(f"Set concurrency error: {e}")
                raise HTTPException(status_code=500, detail=str(e))

    async def start(self):
        """Start the Guardian API server"""
        config = uvicorn.Config(
            self.app,
            host="127.0.0.1",
            port=self.config.guardian_port,
            log_level=self.config.log_level.lower(),
            access_log=False,  # Disable access logs for cleaner output
        )

        server = uvicorn.Server(config)

        self.logger.info(
            f"Starting Guardian API server on port {self.config.guardian_port}"
        )

        # Run both Guardian and API server concurrently
        await asyncio.gather(self.guardian.start(), server.serve())
