"""
Quota tracking system for routing decisions.
Maintains sliding window of routing choices to enforce quotas.
"""

import time
import structlog
from typing import Dict, List, Tuple, Optional
from collections import deque
from threading import Lock

logger = structlog.get_logger(__name__)

class QuotaTracker:
    """Tracks routing quotas with sliding window"""
    
    def __init__(self, name: str, window_size: int = 100, window_time: float = 300.0):
        self.name = name
        self.window_size = window_size  # Number of requests to track
        self.window_time = window_time  # Time window in seconds
        
        # Sliding window of (timestamp, route_type) tuples
        self.decisions: deque = deque(maxlen=window_size)
        self.lock = Lock()
        
        logger.info("Quota tracker initialized", 
                   name=name, 
                   window_size=window_size,
                   window_time=window_time)
    
    def record_decision(self, route_type: str):
        """Record a routing decision"""
        
        with self.lock:
            now = time.time()
            self.decisions.append((now, route_type))
            self._cleanup_old_entries(now)
            
            # Log quota status periodically
            if len(self.decisions) % 20 == 0:
                stats = self.get_stats()
                logger.info("Quota tracker stats", 
                           name=self.name,
                           total_decisions=len(self.decisions),
                           **stats)
    
    def is_quota_exceeded(self, max_share: float, route_type: str = "micro") -> bool:
        """Check if quota is exceeded for given route type"""
        
        with self.lock:
            now = time.time()
            self._cleanup_old_entries(now)
            
            if len(self.decisions) < 10:  # Need minimum decisions for quota
                return False
            
            route_count = sum(1 for _, rt in self.decisions if rt == route_type)
            current_share = route_count / len(self.decisions)
            
            exceeded = current_share > max_share
            
            if exceeded:
                logger.warn("Quota EXCEEDED", 
                           name=self.name,
                           route_type=route_type,
                           current_share=current_share,
                           max_share=max_share,
                           recent_decisions=len(self.decisions))
            
            return exceeded
    
    def get_current_share(self, route_type: str = "micro") -> float:
        """Get current share for route type"""
        
        with self.lock:
            now = time.time()
            self._cleanup_old_entries(now)
            
            if not self.decisions:
                return 0.0
            
            route_count = sum(1 for _, rt in self.decisions if rt == route_type)
            return route_count / len(self.decisions)
    
    def _cleanup_old_entries(self, now: float):
        """Remove entries older than window_time"""
        
        cutoff_time = now - self.window_time
        
        while self.decisions and self.decisions[0][0] < cutoff_time:
            self.decisions.popleft()
    
    def get_stats(self) -> Dict[str, float]:
        """Get comprehensive quota statistics"""
        
        with self.lock:
            now = time.time()
            self._cleanup_old_entries(now)
            
            if not self.decisions:
                return {
                    "total_decisions": 0,
                    "micro_share": 0.0,
                    "planner_share": 0.0,
                    "deep_share": 0.0,
                    "other_share": 0.0
                }
            
            total = len(self.decisions)
            route_counts = {}
            
            for _, route_type in self.decisions:
                route_counts[route_type] = route_counts.get(route_type, 0) + 1
            
            return {
                "total_decisions": total,
                "micro_share": route_counts.get("micro", 0) / total,
                "planner_share": route_counts.get("planner", 0) / total,
                "deep_share": route_counts.get("deep", 0) / total,
                "other_share": sum(count for route, count in route_counts.items() 
                                 if route not in ["micro", "planner", "deep"]) / total,
                "window_age_seconds": now - self.decisions[0][0] if self.decisions else 0
            }
    
    def reset(self):
        """Clear all tracking data"""
        with self.lock:
            self.decisions.clear()
            logger.info("Quota tracker reset", name=self.name)

# Global quota trackers
_quota_trackers: Dict[str, QuotaTracker] = {}
_trackers_lock = Lock()

def get_quota_tracker(name: str, window_size: int = 100, window_time: float = 300.0) -> QuotaTracker:
    """Get or create quota tracker"""
    
    with _trackers_lock:
        if name not in _quota_trackers:
            _quota_trackers[name] = QuotaTracker(name, window_size, window_time)
        return _quota_trackers[name]

def get_all_quota_stats() -> Dict[str, Dict[str, float]]:
    """Get stats for all quota trackers"""
    
    with _trackers_lock:
        return {name: tracker.get_stats() for name, tracker in _quota_trackers.items()}