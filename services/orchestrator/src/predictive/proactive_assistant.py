#!/usr/bin/env python3
"""
Proactive Assistant Integration
Integrates predictive engine with Guardian for proactive suggestions
"""

import asyncio
import time
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

import structlog

from .event_logger import get_event_logger
from .prediction_engine import get_prediction_engine

logger = structlog.get_logger(__name__)


class ProactiveAssistant:
    """Proactive AI assistant that anticipates user needs"""

    def __init__(self):
        self.event_logger = get_event_logger()
        self.prediction_engine = get_prediction_engine()

        self.last_suggestion_time = None
        self.suggestion_cooldown_minutes = 15  # Minimum time between suggestions
        self.active_suggestions = []  # Current active suggestions

        self.is_enabled = True
        self.learning_mode = True  # Whether to log events for learning

    async def initialize(self):
        """Initialize the proactive assistant"""
        try:
            # Check if we need to train the model
            if self.prediction_engine.should_retrain():
                logger.info("Training predictive model...")
                success = self.prediction_engine.train()
                if success:
                    logger.info("Predictive model training completed")
                else:
                    logger.warn(
                        "Predictive model training failed - using fallback patterns"
                    )

            # Log initialization
            if self.learning_mode:
                self.event_logger.log_interaction(
                    event_type="system_start",
                    context={
                        "component": "proactive_assistant",
                        "learning_mode": self.learning_mode,
                    },
                )

            logger.info("Proactive Assistant initialized successfully")

        except Exception as e:
            logger.error("Failed to initialize Proactive Assistant", error=str(e))

    async def log_user_interaction(
        self,
        event_type: str,
        intent: Optional[str] = None,
        session_id: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
        response_latency_ms: Optional[float] = None,
        tool_used: Optional[str] = None,
        success: bool = True,
    ):
        """Log user interaction for predictive learning"""

        if not self.learning_mode:
            return

        try:
            # Add system context
            enhanced_context = context or {}
            enhanced_context.update(
                {
                    "timestamp": datetime.now().isoformat(),
                    "system_state": "normal",  # Could be enhanced with actual system state
                    "learning_session": session_id,
                }
            )

            self.event_logger.log_interaction(
                event_type=event_type,
                intent=intent,
                session_id=session_id,
                context=enhanced_context,
                response_latency_ms=response_latency_ms,
                tool_used=tool_used,
                success=success,
            )

            # Check if we should retrain after logging new data
            if self.prediction_engine.should_retrain():
                # Train in background
                asyncio.create_task(self._background_retrain())

        except Exception as e:
            logger.error("Failed to log user interaction", error=str(e))

    async def get_proactive_suggestions(
        self, context: Optional[Dict[str, Any]] = None, max_suggestions: int = 2
    ) -> List[Dict[str, Any]]:
        """Get proactive suggestions for the user"""

        if not self.is_enabled:
            return []

        try:
            # Check cooldown
            if self._is_in_cooldown():
                return []

            # Get predictions from ML engine
            predictions = self.prediction_engine.predict_next_action(
                top_k=max_suggestions
            )

            # Filter and enhance suggestions
            suggestions = []
            for pred in predictions:
                if pred["confidence"] > 0.2:  # Minimum confidence
                    suggestion = self._create_proactive_suggestion(pred, context)
                    suggestions.append(suggestion)

            # Update tracking
            self.active_suggestions = suggestions
            self.last_suggestion_time = datetime.now()

            if suggestions:
                logger.info(f"Generated {len(suggestions)} proactive suggestions")

            return suggestions

        except Exception as e:
            logger.error("Failed to get proactive suggestions", error=str(e))
            return []

    def _create_proactive_suggestion(
        self, prediction: Dict[str, Any], context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Create a proactive suggestion from prediction"""

        now = datetime.now()

        suggestion = {
            "id": f"proactive_{int(time.time())}_{prediction['intent']}",
            "type": "proactive_suggestion",
            "intent": prediction["intent"],
            "message": prediction["suggested_action"],
            "confidence": prediction["confidence"],
            "urgency": prediction["urgency"],
            "reasoning": prediction["reasoning"],
            "suggested_at": now.isoformat(),
            "expires_at": (
                now + timedelta(minutes=30)
            ).isoformat(),  # Suggestion expires in 30 min
            # Action metadata
            "action": {
                "type": "intent_suggestion",
                "intent": prediction["intent"],
                "auto_execute": False,  # Never auto-execute, always ask user
                "requires_confirmation": True,
            },
            # Display metadata
            "display": {
                "priority": self._map_urgency_to_priority(prediction["urgency"]),
                "icon": self._get_intent_icon(prediction["intent"]),
                "color": self._get_urgency_color(prediction["urgency"]),
                "dismissible": True,
            },
            # Context
            "context": context or {},
            "historical_frequency": prediction.get("historical_frequency", 0),
        }

        return suggestion

    def _is_in_cooldown(self) -> bool:
        """Check if we're in suggestion cooldown period"""
        if not self.last_suggestion_time:
            return False

        minutes_since_last = (
            datetime.now() - self.last_suggestion_time
        ).total_seconds() / 60
        return minutes_since_last < self.suggestion_cooldown_minutes

    def _map_urgency_to_priority(self, urgency: str) -> int:
        """Map urgency to numeric priority"""
        urgency_map = {"high": 1, "medium": 2, "low": 3}
        return urgency_map.get(urgency, 3)

    def _get_intent_icon(self, intent: str) -> str:
        """Get icon for intent"""
        icons = {
            "time.now": "⏰",
            "weather.lookup": "🌤️",
            "calendar.check": "📅",
            "email.check": "📧",
            "reminder.set": "⏰",
            "greeting.hello": "👋",
            "general": "💡",
        }
        return icons.get(intent, "🤖")

    def _get_urgency_color(self, urgency: str) -> str:
        """Get color for urgency level"""
        colors = {
            "high": "#ff4444",  # Red
            "medium": "#ffaa00",  # Orange
            "low": "#4488ff",  # Blue
        }
        return colors.get(urgency, "#888888")

    async def _background_retrain(self):
        """Retrain model in background"""
        try:
            logger.info("Starting background model retraining...")
            success = self.prediction_engine.train()
            if success:
                logger.info("Background model retraining completed successfully")
            else:
                logger.warn("Background model retraining failed")
        except Exception as e:
            logger.error("Background model retraining error", error=str(e))

    async def handle_suggestion_feedback(
        self,
        suggestion_id: str,
        action: str,  # 'accepted', 'dismissed', 'executed'
        context: Optional[Dict[str, Any]] = None,
    ):
        """Handle user feedback on suggestions"""

        try:
            # Log feedback for learning
            if self.learning_mode:
                self.event_logger.log_interaction(
                    event_type="suggestion_feedback",
                    context={
                        "suggestion_id": suggestion_id,
                        "feedback_action": action,
                        "context": context or {},
                    },
                    success=(action == "accepted" or action == "executed"),
                )

            # Remove from active suggestions if dismissed/executed
            if action in ["dismissed", "executed"]:
                self.active_suggestions = [
                    s for s in self.active_suggestions if s["id"] != suggestion_id
                ]

            logger.info(f"Processed suggestion feedback: {action} for {suggestion_id}")

        except Exception as e:
            logger.error("Failed to handle suggestion feedback", error=str(e))

    def get_stats(self) -> Dict[str, Any]:
        """Get proactive assistant statistics"""

        try:
            db_stats = self.event_logger.get_stats()

            return {
                "is_enabled": self.is_enabled,
                "learning_mode": self.learning_mode,
                "model_trained": self.prediction_engine.is_trained,
                "last_training": self.prediction_engine.last_training_time,
                "active_suggestions_count": len(self.active_suggestions),
                "suggestion_cooldown_minutes": self.suggestion_cooldown_minutes,
                "last_suggestion_time": (
                    self.last_suggestion_time.isoformat()
                    if self.last_suggestion_time
                    else None
                ),
                # Database stats
                "total_logged_events": db_stats.get("total_events", 0),
                "unique_sessions": db_stats.get("unique_sessions", 0),
                "db_size_mb": db_stats.get("db_size_mb", 0),
                "avg_latency_ms": db_stats.get("avg_latency_ms", 0),
                # Feature importance (top 5)
                "top_predictive_features": (
                    dict(
                        sorted(
                            self.prediction_engine.feature_importance.items(),
                            key=lambda x: x[1],
                            reverse=True,
                        )[:5]
                    )
                    if self.prediction_engine.feature_importance
                    else {}
                ),
            }

        except Exception as e:
            logger.error("Failed to get proactive assistant stats", error=str(e))
            return {}

    async def cleanup_old_data(self):
        """Cleanup old data to keep system lean"""
        try:
            self.event_logger.cleanup_old_events(days_keep=90)
            logger.info("Proactive assistant data cleanup completed")
        except Exception as e:
            logger.error("Failed to cleanup proactive assistant data", error=str(e))


# Global proactive assistant instance
_proactive_assistant: Optional[ProactiveAssistant] = None


def get_proactive_assistant() -> ProactiveAssistant:
    """Get or create global proactive assistant instance"""
    global _proactive_assistant
    if _proactive_assistant is None:
        _proactive_assistant = ProactiveAssistant()
    return _proactive_assistant
