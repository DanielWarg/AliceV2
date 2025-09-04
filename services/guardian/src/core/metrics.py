"""System metrics collection for Guardian"""

import time
from dataclasses import dataclass

import psutil


@dataclass
class SystemMetrics:
    """System metrics snapshot"""

    timestamp: float
    ram_pct: float
    ram_gb: float
    cpu_pct: float
    disk_pct: float
    temp_c: float | None
    ollama_pids: list[int]
    degraded: bool = False
    intake_blocked: bool = False
    emergency_mode: bool = False


class MetricsCollector:
    """Collects and manages system metrics"""

    def __init__(self):
        self.last_cpu_times = None

    def collect_metrics(self) -> SystemMetrics:
        """Collect current system metrics"""
        timestamp = time.time()

        # RAM metrics
        memory = psutil.virtual_memory()
        ram_pct = memory.percent
        ram_gb = memory.used / (1024**3)

        # CPU metrics (averaged over short interval for responsiveness)
        cpu_pct = psutil.cpu_percent(interval=0.1)

        # Disk metrics (root partition)
        disk = psutil.disk_usage("/")
        disk_pct = disk.percent

        # Temperature (if available)
        temp_c = None
        try:
            temps = psutil.sensors_temperatures()
            if temps:
                # Try to get CPU temperature
                for name, entries in temps.items():
                    if entries and "cpu" in name.lower():
                        temp_c = entries[0].current
                        break
                # Fallback to first available temperature
                if temp_c is None:
                    for entries in temps.values():
                        if entries:
                            temp_c = entries[0].current
                            break
        except (AttributeError, OSError):
            pass

        # Ollama process detection
        ollama_pids = self._find_ollama_pids()

        return SystemMetrics(
            timestamp=timestamp,
            ram_pct=ram_pct,
            ram_gb=ram_gb,
            cpu_pct=cpu_pct,
            disk_pct=disk_pct,
            temp_c=temp_c,
            ollama_pids=ollama_pids,
        )

    def _find_ollama_pids(self) -> list[int]:
        """Find all Ollama-related process PIDs"""
        pids = []
        try:
            for proc in psutil.process_iter(["pid", "name", "cmdline"]):
                try:
                    proc_info = proc.info
                    name = proc_info.get("name", "").lower()
                    cmdline = " ".join(proc_info.get("cmdline", [])).lower()

                    if "ollama" in name or "ollama" in cmdline:
                        pids.append(proc_info["pid"])
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
        except Exception:
            pass

        return pids
