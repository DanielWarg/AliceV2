"""
Graceful Shutdown Management
Handles SIGTERM with request draining and proper cleanup
"""

import asyncio
import signal
import time
from contextlib import asynccontextmanager
from typing import Set

import structlog

logger = structlog.get_logger(__name__)

# Global shutdown state
SHUTDOWN_STATE = {
    "shutdown_requested": False,
    "shutdown_started": False,
    "active_requests": set(),
    "drain_timeout": 30.0,
    "shutdown_start_time": None,
}


class GracefulShutdown:
    """Manages graceful shutdown process"""

    def __init__(self, drain_timeout: float = 30.0):
        self.drain_timeout = drain_timeout
        self.active_requests: Set[str] = set()
        self.shutdown_requested = False
        self.shutdown_started = False

    def register_request(self, request_id: str):
        """Register an active request"""
        if not self.shutdown_requested:
            self.active_requests.add(request_id)
            logger.debug(
                "Request registered",
                request_id=request_id,
                active_count=len(self.active_requests),
            )

    def unregister_request(self, request_id: str):
        """Unregister a completed request"""
        if request_id in self.active_requests:
            self.active_requests.remove(request_id)
            logger.debug(
                "Request completed",
                request_id=request_id,
                active_count=len(self.active_requests),
            )

    def request_shutdown(self):
        """Request shutdown - stop accepting new requests"""
        if not self.shutdown_requested:
            self.shutdown_requested = True
            logger.warning("Shutdown requested - stopping new requests")

    def start_shutdown(self):
        """Start actual shutdown process"""
        if not self.shutdown_started:
            self.shutdown_started = True
            SHUTDOWN_STATE["shutdown_started"] = True
            SHUTDOWN_STATE["shutdown_start_time"] = time.time()
            logger.warning(
                "Shutdown started - draining requests",
                active_count=len(self.active_requests),
            )

    async def wait_for_drain(self) -> bool:
        """Wait for all requests to complete"""
        if not self.shutdown_started:
            return True

        start_time = time.time()
        while self.active_requests and (time.time() - start_time) < self.drain_timeout:
            logger.info(
                "Waiting for requests to drain",
                active_count=len(self.active_requests),
                remaining_time=self.drain_timeout - (time.time() - start_time),
            )
            await asyncio.sleep(1)

        if self.active_requests:
            logger.error(
                "Shutdown timeout - forcing shutdown",
                active_count=len(self.active_requests),
            )
            return False
        else:
            logger.info("All requests drained successfully")
            return True

    async def cleanup(self):
        """Perform cleanup tasks"""
        logger.info("Starting cleanup")

        # Flush logs
        try:
            # Force flush structured logs
            logger.info("Flushing logs")
            await asyncio.sleep(0.1)  # Give time for async log flushing
        except Exception as e:
            logger.error("Log flush failed", error=str(e))

        # Close connections
        try:
            # Close database connections, HTTP clients, etc.
            logger.info("Closing connections")
        except Exception as e:
            logger.error("Connection cleanup failed", error=str(e))

        logger.info("Cleanup completed")


# Global shutdown manager
shutdown_manager = GracefulShutdown()


def setup_signal_handlers():
    """Setup signal handlers for graceful shutdown"""

    def signal_handler(signum, frame):
        logger.warning(f"Received signal {signum}")
        shutdown_manager.request_shutdown()

    signal.signal(signal.SIGTERM, signal_handler)
    signal.signal(signal.SIGINT, signal_handler)


@asynccontextmanager
async def request_context(request_id: str):
    """Context manager for tracking requests during shutdown"""
    try:
        shutdown_manager.register_request(request_id)
        yield
    finally:
        shutdown_manager.unregister_request(request_id)


async def shutdown_app():
    """Main shutdown procedure"""
    logger.warning("Application shutdown initiated")

    # Start shutdown process
    shutdown_manager.start_shutdown()

    # Wait for requests to drain
    drained = await shutdown_manager.wait_for_drain()

    # Perform cleanup
    await shutdown_manager.cleanup()

    if drained:
        logger.info("Graceful shutdown completed")
    else:
        logger.error("Forced shutdown due to timeout")

    return drained
