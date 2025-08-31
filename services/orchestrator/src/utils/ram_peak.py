import psutil
from typing import Dict

def ram_peak_mb() -> Dict[str, float]:
    """Mät RAM-användning för process och system"""
    try:
        # Process RAM (RSS - Resident Set Size)
        pm = psutil.Process().memory_info().rss  # bytes
        proc_mb = round(pm / 1024 / 1024, 1)
        
        # System RAM
        sys = psutil.virtual_memory().used
        sys_mb = round(sys / 1024 / 1024, 1)
        
        return {
            "proc_mb": proc_mb,
            "sys_mb": sys_mb
        }
    except Exception:
        # Fallback om psutil inte fungerar
        return {"proc_mb": 0.0, "sys_mb": 0.0}
