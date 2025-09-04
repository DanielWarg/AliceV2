import os
import time
from typing import Optional


class EnergyMeter:
    """Enkel energimätare för per-turn energy tracking"""

    def __init__(self, watts_idle: Optional[float] = None):
        # Default till 6W idle för MacBook, kan override via env
        self._w_idle = watts_idle or float(os.getenv("ENERGY_BASE_WATTS", "6.0"))
        self._t0: Optional[float] = None

    def start(self) -> None:
        """Starta energimätning"""
        self._t0 = time.perf_counter()

    def stop(self) -> float:
        """Stoppa och returnera energy consumption i Wh"""
        if self._t0 is None:
            return 0.0

        dt = time.perf_counter() - self._t0
        # Enkel approximation: idle-watts * tid -> Wh
        wh = (self._w_idle * dt) / 3600.0
        return round(wh, 4)

    def __enter__(self):
        self.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        return self.stop()
