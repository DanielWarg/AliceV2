#!/usr/bin/env python3
"""
Guardian Service Entry Point
============================

Deterministisk säkerhetsdaemon för Alice v2
Port :8787 - HTTP API för status och kontroll
"""

import asyncio
import logging
import os
import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from api.server import GuardianServer
from core.guardian import Guardian
from core.guardian_state import GuardianConfig


def setup_logging(config: GuardianConfig):
    """Setup structured logging"""
    log_level = getattr(logging, config.log_level.upper(), logging.INFO)

    if config.log_format == "structured":
        # JSON-like structured logging for production
        logging.basicConfig(
            level=log_level,
            format='{"timestamp":"%(asctime)s","level":"%(levelname)s","logger":"%(name)s","message":"%(message)s"}',
            datefmt="%Y-%m-%dT%H:%M:%S",
        )
    else:
        # Simple logging for development
        logging.basicConfig(
            level=log_level,
            format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )


async def main():
    """Main entry point"""
    # Load configuration (could be extended to load from file/env)
    config = GuardianConfig()

    # Override with environment variables if present
    if "ALICE_API_URL" in os.environ:
        config.alice_base_url = os.environ["ALICE_API_URL"]
    if "OLLAMA_API_URL" in os.environ:
        config.ollama_base_url = os.environ["OLLAMA_API_URL"]
    if "GUARDIAN_PORT" in os.environ:
        config.guardian_port = int(os.environ["GUARDIAN_PORT"])

    # Setup logging
    setup_logging(config)
    logger = logging.getLogger("guardian.main")

    logger.info("Starting Alice Guardian v2")
    logger.info(f"Alice API: {config.alice_base_url}")
    logger.info(f"Ollama API: {config.ollama_base_url}")
    logger.info(f"Guardian Port: {config.guardian_port}")

    try:
        # Create Guardian instance
        guardian = Guardian(config)

        # Create API server
        server = GuardianServer(guardian, config)

        # Start both Guardian daemon and API server
        await server.start()

    except KeyboardInterrupt:
        logger.info("Received interrupt signal, shutting down...")
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nGuardian shutdown complete")
        sys.exit(0)
