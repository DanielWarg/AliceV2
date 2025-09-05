#!/usr/bin/env python3
"""
Predictive Event Logger
Captures user interaction patterns for ML-driven predictions
"""

import json
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

import structlog

logger = structlog.get_logger(__name__)


class PredictiveEventLogger:
    """Logs user events for predictive analysis"""

    def __init__(self, db_path: str = "data/predictive/events.db"):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _init_db(self):
        """Initialize SQLite database with predictive schema"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS user_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp REAL NOT NULL,
                    hour INTEGER NOT NULL,
                    weekday INTEGER NOT NULL,
                    event_type TEXT NOT NULL,
                    intent TEXT,
                    session_id TEXT,
                    context_data TEXT,  -- JSON blob
                    response_latency_ms REAL,
                    tool_used TEXT,
                    success BOOLEAN,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """
            )

            conn.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_timestamp ON user_events(timestamp)
            """
            )

            conn.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_hour_weekday ON user_events(hour, weekday)
            """
            )

            conn.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_intent ON user_events(intent)
            """
            )

    def log_interaction(
        self,
        event_type: str,
        intent: Optional[str] = None,
        session_id: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
        response_latency_ms: Optional[float] = None,
        tool_used: Optional[str] = None,
        success: bool = True,
    ):
        """Log a user interaction event"""

        now = datetime.now()
        timestamp = now.timestamp()
        hour = now.hour
        weekday = now.weekday()  # 0=Monday, 6=Sunday

        context_json = json.dumps(context or {})

        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute(
                    """
                    INSERT INTO user_events 
                    (timestamp, hour, weekday, event_type, intent, session_id, 
                     context_data, response_latency_ms, tool_used, success)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                    (
                        timestamp,
                        hour,
                        weekday,
                        event_type,
                        intent,
                        session_id,
                        context_json,
                        response_latency_ms,
                        tool_used,
                        success,
                    ),
                )

                logger.info(
                    "Predictive event logged",
                    event_type=event_type,
                    intent=intent,
                    hour=hour,
                    weekday=weekday,
                )

        except Exception as e:
            logger.error("Failed to log predictive event", error=str(e))

    def get_patterns(self, days_back: int = 30) -> List[Dict[str, Any]]:
        """Get user interaction patterns for the last N days"""

        cutoff_time = (datetime.now() - timedelta(days=days_back)).timestamp()

        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute(
                    """
                    SELECT 
                        hour,
                        weekday,
                        event_type,
                        intent,
                        COUNT(*) as frequency,
                        AVG(response_latency_ms) as avg_latency,
                        MAX(timestamp) as last_occurrence
                    FROM user_events 
                    WHERE timestamp >= ? AND success = 1
                    GROUP BY hour, weekday, event_type, intent
                    HAVING COUNT(*) >= 2
                    ORDER BY frequency DESC, last_occurrence DESC
                """,
                    (cutoff_time,),
                )

                patterns = []
                for row in cursor:
                    patterns.append(
                        {
                            "hour": row[0],
                            "weekday": row[1],
                            "event_type": row[2],
                            "intent": row[3],
                            "frequency": row[4],
                            "avg_latency": row[5],
                            "last_occurrence": row[6],
                            "pattern_strength": row[4] / days_back,  # frequency per day
                        }
                    )

                logger.info(f"Retrieved {len(patterns)} interaction patterns")
                return patterns

        except Exception as e:
            logger.error("Failed to get patterns", error=str(e))
            return []

    def get_recent_context(self, minutes_back: int = 60) -> List[Dict[str, Any]]:
        """Get recent interaction context for predictive analysis"""

        cutoff_time = (datetime.now() - timedelta(minutes=minutes_back)).timestamp()

        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute(
                    """
                    SELECT timestamp, event_type, intent, context_data, tool_used
                    FROM user_events 
                    WHERE timestamp >= ?
                    ORDER BY timestamp DESC
                    LIMIT 20
                """,
                    (cutoff_time,),
                )

                events = []
                for row in cursor:
                    try:
                        context_data = json.loads(row[3]) if row[3] else {}
                    except json.JSONDecodeError:
                        context_data = {}

                    events.append(
                        {
                            "timestamp": row[0],
                            "event_type": row[1],
                            "intent": row[2],
                            "context": context_data,
                            "tool_used": row[4],
                        }
                    )

                return events

        except Exception as e:
            logger.error("Failed to get recent context", error=str(e))
            return []

    def cleanup_old_events(self, days_keep: int = 90):
        """Clean up old events to keep database size manageable"""

        cutoff_time = (datetime.now() - timedelta(days=days_keep)).timestamp()

        try:
            with sqlite3.connect(self.db_path) as conn:
                result = conn.execute(
                    """
                    DELETE FROM user_events 
                    WHERE timestamp < ?
                """,
                    (cutoff_time,),
                )

                deleted_count = result.rowcount
                logger.info(f"Cleaned up {deleted_count} old predictive events")

        except Exception as e:
            logger.error("Failed to cleanup old events", error=str(e))

    def get_stats(self) -> Dict[str, Any]:
        """Get database statistics"""

        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute(
                    """
                    SELECT 
                        COUNT(*) as total_events,
                        COUNT(DISTINCT session_id) as unique_sessions,
                        MIN(timestamp) as earliest_event,
                        MAX(timestamp) as latest_event,
                        AVG(response_latency_ms) as avg_latency
                    FROM user_events
                """
                )

                row = cursor.fetchone()
                if row:
                    earliest = datetime.fromtimestamp(row[2]) if row[2] else None
                    latest = datetime.fromtimestamp(row[3]) if row[3] else None

                    return {
                        "total_events": row[0],
                        "unique_sessions": row[1],
                        "earliest_event": earliest.isoformat() if earliest else None,
                        "latest_event": latest.isoformat() if latest else None,
                        "avg_latency_ms": round(row[4], 2) if row[4] else 0,
                        "db_size_mb": (
                            self.db_path.stat().st_size / (1024 * 1024)
                            if self.db_path.exists()
                            else 0
                        ),
                    }

        except Exception as e:
            logger.error("Failed to get database stats", error=str(e))

        return {}


# Global event logger instance
_event_logger: Optional[PredictiveEventLogger] = None


def get_event_logger() -> PredictiveEventLogger:
    """Get or create global event logger instance"""
    global _event_logger
    if _event_logger is None:
        _event_logger = PredictiveEventLogger()
    return _event_logger
