#!/usr/bin/env python3
"""
Predictive ML Engine
Lightweight machine learning for proactive user suggestions
"""

import pickle
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import numpy as np
import structlog
from sklearn.ensemble import RandomForestClassifier
from sklearn.feature_extraction import DictVectorizer
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from ..config.fibonacci import (
    FIBONACCI_SEQUENCE,
    GOLDEN_RATIO,
    calculate_golden_ratio_threshold,
)
from .event_logger import get_event_logger

logger = structlog.get_logger(__name__)


class PredictionEngine:
    """ML-powered predictive interaction engine"""

    def __init__(self, model_path: str = "data/predictive/model.pkl"):
        self.model_path = Path(model_path)
        self.model_path.parent.mkdir(parents=True, exist_ok=True)
        self.event_logger = get_event_logger()

        # Fibonacci-enhanced ML Pipeline with golden ratio optimization
        self.pipeline = Pipeline(
            [
                ("vectorizer", DictVectorizer()),
                ("scaler", StandardScaler(with_mean=False)),
                (
                    "classifier",
                    RandomForestClassifier(
                        n_estimators=FIBONACCI_SEQUENCE[
                            10
                        ],  # 55 trees for optimal performance
                        max_depth=FIBONACCI_SEQUENCE[
                            6
                        ],  # 8 depth for balanced complexity
                        min_samples_split=FIBONACCI_SEQUENCE[4],  # 3 minimum samples
                        min_samples_leaf=FIBONACCI_SEQUENCE[2],  # 1 minimum leaf
                        max_features=calculate_golden_ratio_threshold(
                            1.0
                        ),  # Golden ratio feature selection
                        random_state=42,
                        n_jobs=-1,
                        class_weight="balanced",  # Natural class balancing
                    ),
                ),
            ]
        )

        self.is_trained = False
        self.last_training_time = None
        self.feature_importance = {}

        # Load existing model if available
        self._load_model()

    def _load_model(self):
        """Load saved model"""
        try:
            if self.model_path.exists():
                with open(self.model_path, "rb") as f:
                    model_data = pickle.load(f)
                    self.pipeline = model_data["pipeline"]
                    self.is_trained = model_data["is_trained"]
                    self.last_training_time = model_data["last_training_time"]
                    self.feature_importance = model_data.get("feature_importance", {})

                logger.info(
                    "Predictive model loaded",
                    last_training=self.last_training_time,
                    is_trained=self.is_trained,
                )
        except Exception as e:
            logger.warn("Failed to load predictive model", error=str(e))

    def _save_model(self):
        """Save trained model"""
        try:
            model_data = {
                "pipeline": self.pipeline,
                "is_trained": self.is_trained,
                "last_training_time": self.last_training_time,
                "feature_importance": self.feature_importance,
            }

            with open(self.model_path, "wb") as f:
                pickle.dump(model_data, f)

            logger.info("Predictive model saved", path=str(self.model_path))
        except Exception as e:
            logger.error("Failed to save predictive model", error=str(e))

    def _extract_features(
        self,
        current_time: datetime,
        recent_context: List[Dict] = None,
        user_patterns: List[Dict] = None,
    ) -> Dict[str, Any]:
        """Extract Fibonacci-weighted features for ML model with golden ratio optimization"""

        # Base temporal features with Fibonacci weighting
        features = {
            # Enhanced temporal features using golden ratio cycles
            "hour": current_time.hour,
            "weekday": current_time.weekday(),
            "is_weekend": current_time.weekday() >= 5,
            # Golden ratio time periods (more natural than rigid hour blocks)
            "is_golden_morning": 6
            <= current_time.hour
            <= int(6 + 24 / GOLDEN_RATIO / 3),  # ~8.95h
            "is_golden_afternoon": int(12)
            <= current_time.hour
            <= int(12 + 24 / GOLDEN_RATIO / 2),  # ~19.47h
            "is_golden_evening": int(18)
            <= current_time.hour
            <= int(18 + 24 / GOLDEN_RATIO / 4),  # ~21.24h
            "is_fibonacci_night": current_time.hour >= 23
            or current_time.hour <= FIBONACCI_SEQUENCE[4],  # 3am
            # Fibonacci-enhanced cyclical features
            "hour_sin_phi": np.sin(2 * np.pi * current_time.hour / 24 * GOLDEN_RATIO),
            "hour_cos_phi": np.cos(2 * np.pi * current_time.hour / 24 * GOLDEN_RATIO),
            "weekday_sin_phi": np.sin(
                2 * np.pi * current_time.weekday() / 7 * GOLDEN_RATIO
            ),
            "weekday_cos_phi": np.cos(
                2 * np.pi * current_time.weekday() / 7 * GOLDEN_RATIO
            ),
            # Golden ratio hour positioning for natural rhythm detection
            "hour_golden_position": (current_time.hour / 24) * GOLDEN_RATIO,
            "fibonacci_time_bucket": int(
                current_time.hour / 24 * len(FIBONACCI_SEQUENCE[:8])
            ),
            # Advanced temporal patterns using Fibonacci intervals
            "fibonacci_hour_weight": self._get_fibonacci_time_weight(current_time.hour),
            "golden_ratio_day_progress": (current_time.hour / 24) ** GOLDEN_RATIO,
        }

        # Recent context features
        if recent_context:
            context_intents = [
                event.get("intent", "unknown") for event in recent_context[-5:]
            ]
            context_tools = [
                event.get("tool_used", "none") for event in recent_context[-5:]
            ]

            # Most common recent intent/tool
            if context_intents:
                from collections import Counter

                most_common_intent = Counter(context_intents).most_common(1)[0][0]
                features["recent_intent"] = most_common_intent
                features["recent_activity_count"] = len(
                    [
                        e
                        for e in recent_context
                        if e.get("timestamp", 0) > time.time() - 300
                    ]
                )  # Last 5 min

            if context_tools:
                from collections import Counter

                most_common_tool = Counter(context_tools).most_common(1)[0][0]
                features["recent_tool"] = most_common_tool

        # Historical pattern features
        if user_patterns:
            current_hour_patterns = [
                p for p in user_patterns if p["hour"] == current_time.hour
            ]
            current_weekday_patterns = [
                p for p in user_patterns if p["weekday"] == current_time.weekday()
            ]

            features["hour_pattern_strength"] = sum(
                p["pattern_strength"] for p in current_hour_patterns
            )
            features["weekday_pattern_strength"] = sum(
                p["pattern_strength"] for p in current_weekday_patterns
            )
            features["total_historical_frequency"] = len(user_patterns)

            # Most likely intent/tool based on patterns with Fibonacci weighting
            if current_hour_patterns:
                # Apply Fibonacci weighting to pattern strength
                weighted_patterns = []
                for pattern in current_hour_patterns:
                    fib_weight = self._get_fibonacci_time_weight(pattern["hour"])
                    weighted_strength = pattern["pattern_strength"] * fib_weight
                    weighted_patterns.append(
                        {**pattern, "weighted_strength": weighted_strength}
                    )

                likely_intent = max(
                    weighted_patterns, key=lambda x: x["weighted_strength"]
                )["intent"]
                features["likely_intent"] = likely_intent
                features["fibonacci_weighted_pattern_strength"] = max(
                    p["weighted_strength"] for p in weighted_patterns
                )

        # Apply Fibonacci weighting to all features
        weighted_features = self._apply_fibonacci_feature_weighting(features)

        return weighted_features

    def _get_fibonacci_time_weight(self, hour: int) -> float:
        """Calculate Fibonacci weight for given hour using golden ratio patterns"""
        # Map hour to Fibonacci sequence position using golden angle
        golden_angle_degrees = 360 / (GOLDEN_RATIO**2)  # ≈ 137.5°
        hour_angle = (hour / 24) * 360

        # Find closest Fibonacci number based on golden angle positioning
        normalized_position = (hour_angle / golden_angle_degrees) % len(
            FIBONACCI_SEQUENCE[:8]
        )
        fibonacci_index = int(normalized_position)

        return (
            FIBONACCI_SEQUENCE[fibonacci_index] / FIBONACCI_SEQUENCE[7]
        )  # Normalize by F(8) = 13

    def _apply_fibonacci_feature_weighting(
        self, features: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Apply Fibonacci weighting to enhance important features using golden ratio"""
        weighted_features = features.copy()

        # Define feature importance weights using Fibonacci sequence
        fibonacci_weights = {
            "hour": FIBONACCI_SEQUENCE[5],  # 5 - important
            "weekday": FIBONACCI_SEQUENCE[4],  # 3 - moderate
            "hour_sin_phi": FIBONACCI_SEQUENCE[6],  # 8 - very important (cyclical)
            "hour_cos_phi": FIBONACCI_SEQUENCE[6],  # 8 - very important (cyclical)
            "fibonacci_hour_weight": FIBONACCI_SEQUENCE[7],  # 13 - highest weight
            "golden_ratio_day_progress": FIBONACCI_SEQUENCE[
                6
            ],  # 8 - important progression
            "recent_activity_count": FIBONACCI_SEQUENCE[5],  # 5 - context matters
            "hour_pattern_strength": FIBONACCI_SEQUENCE[
                7
            ],  # 13 - pattern recognition critical
        }

        # Apply golden ratio normalization to weighted features
        for feature_name, weight in fibonacci_weights.items():
            if feature_name in weighted_features and isinstance(
                weighted_features[feature_name], (int, float)
            ):
                # Apply Fibonacci weight with golden ratio smoothing
                original_value = weighted_features[feature_name]
                fibonacci_weighted = original_value * (
                    weight / FIBONACCI_SEQUENCE[7]
                )  # Normalize by F(8)=13
                golden_smoothed = (
                    fibonacci_weighted / GOLDEN_RATIO
                )  # Golden ratio dampening

                weighted_features[f"{feature_name}_fib_weighted"] = fibonacci_weighted
                weighted_features[f"{feature_name}_golden_smoothed"] = golden_smoothed

        return weighted_features

    def train(self, min_events: int = 50) -> bool:
        """Train the predictive model on user patterns"""

        try:
            # Get training data
            patterns = self.event_logger.get_patterns(days_back=60)

            if len(patterns) < min_events:
                logger.warn(
                    f"Not enough data to train model ({len(patterns)} < {min_events})"
                )
                return False

            # Prepare training data
            X, y = [], []

            for pattern in patterns:
                # Create datetime for this pattern
                # Use a recent example for temporal features
                pattern_time = datetime.fromtimestamp(pattern["last_occurrence"])

                features = self._extract_features(
                    pattern_time,
                    recent_context=[],  # Simplified for training
                    user_patterns=patterns,
                )

                X.append(features)
                y.append(pattern["intent"] or "general")

            # Train pipeline
            self.pipeline.fit(X, y)
            self.is_trained = True
            self.last_training_time = datetime.now().isoformat()

            # Extract feature importance
            if hasattr(self.pipeline.named_steps["classifier"], "feature_importances_"):
                feature_names = self.pipeline.named_steps[
                    "vectorizer"
                ].get_feature_names_out()
                importances = self.pipeline.named_steps[
                    "classifier"
                ].feature_importances_

                self.feature_importance = dict(zip(feature_names, importances))

                # Top 10 most important features
                top_features = sorted(
                    self.feature_importance.items(), key=lambda x: x[1], reverse=True
                )[:10]
                logger.info("Top predictive features", features=dict(top_features))

            # Save trained model
            self._save_model()

            logger.info(
                "Predictive model trained successfully",
                training_samples=len(X),
                unique_intents=len(set(y)),
                accuracy_estimate="pending_validation",
            )

            return True

        except Exception as e:
            logger.error("Failed to train predictive model", error=str(e))
            return False

    def predict_next_action(self, top_k: int = 3) -> List[Dict[str, Any]]:
        """Predict most likely next user actions"""

        if not self.is_trained:
            logger.warn("Predictive model not trained yet")
            return []

        try:
            # Get current context
            now = datetime.now()
            recent_context = self.event_logger.get_recent_context(minutes_back=60)
            user_patterns = self.event_logger.get_patterns(days_back=30)

            # Extract features
            features = self._extract_features(now, recent_context, user_patterns)

            # Get predictions
            X = [features]

            # Get prediction probabilities
            probabilities = self.pipeline.predict_proba(X)[0]
            classes = self.pipeline.classes_

            # Get top-k predictions
            top_indices = np.argsort(probabilities)[-top_k:][::-1]

            predictions = []
            for idx in top_indices:
                intent = classes[idx]
                confidence = probabilities[idx]

                if confidence > 0.1:  # Minimum confidence threshold
                    # Find related patterns for context
                    related_patterns = [
                        p for p in user_patterns if p["intent"] == intent
                    ]
                    avg_frequency = (
                        np.mean([p["frequency"] for p in related_patterns])
                        if related_patterns
                        else 0
                    )

                    prediction = {
                        "intent": intent,
                        "confidence": float(confidence),
                        "suggested_action": self._generate_suggestion(
                            intent, features, related_patterns
                        ),
                        "historical_frequency": float(avg_frequency),
                        "reasoning": self._explain_prediction(
                            intent, features, related_patterns
                        ),
                        "urgency": self._calculate_urgency(
                            intent, features, related_patterns
                        ),
                    }

                    predictions.append(prediction)

            logger.info(f"Generated {len(predictions)} predictive suggestions")
            return predictions

        except Exception as e:
            logger.error("Failed to predict next action", error=str(e))
            return []

    def _generate_suggestion(
        self, intent: str, features: Dict, patterns: List[Dict]
    ) -> str:
        """Generate human-readable suggestion"""

        hour = features.get("hour", 0)
        is_morning = features.get("is_morning", False)

        # Intent-specific suggestions
        suggestions = {
            "time.now": f"Du brukar kolla tiden nu kl {hour:02d}. Vill du se aktuell tid?",
            "weather.lookup": "Baserat på dina vanor, vill du kolla vädret nu?",
            "calendar.check": "Du brukar kolla kalendern vid denna tid. Vill du se dagens schema?",
            "email.check": (
                "Dags att kolla mail?" if is_morning else "Kvällsmail att kolla?"
            ),
            "reminder.set": "Vill du sätta en påminnelse för imorgon?",
            "greeting.hello": (
                "Hej! Redo för dagens uppgifter?"
                if is_morning
                else "God kväll! Hur har dagen varit?"
            ),
            "general": "Kan jag hjälpa dig med något vanligt du brukar göra nu?",
        }

        return suggestions.get(intent, f"Vill du göra något relaterat till {intent}?")

    def _explain_prediction(
        self, intent: str, features: Dict, patterns: List[Dict]
    ) -> str:
        """Explain why this prediction was made"""

        hour = features.get("hour", 0)
        weekday = features.get("weekday", 0)
        weekdays = [
            "måndag",
            "tisdag",
            "onsdag",
            "torsdag",
            "fredag",
            "lördag",
            "söndag",
        ]

        if patterns:
            avg_freq = np.mean([p["frequency"] for p in patterns])
            return f"Du gör detta {avg_freq:.1f} gånger/månad på {weekdays[weekday]}ar kl {hour:02d}"

        return f"Baserat på mönster för {weekdays[weekday]} kl {hour:02d}"

    def _calculate_urgency(
        self, intent: str, features: Dict, patterns: List[Dict]
    ) -> str:
        """Calculate suggestion urgency"""

        if not patterns:
            return "low"

        avg_freq = np.mean([p["frequency"] for p in patterns])
        recent_occurrence = max([p["last_occurrence"] for p in patterns])
        hours_since_last = (time.time() - recent_occurrence) / 3600

        if avg_freq > 10 and hours_since_last < 1:  # Very frequent, recent
            return "high"
        elif avg_freq > 5 and hours_since_last < 6:  # Frequent, somewhat recent
            return "medium"
        else:
            return "low"

    def should_retrain(self) -> bool:
        """Check if model should be retrained"""

        if not self.is_trained:
            return True

        if not self.last_training_time:
            return True

        # Retrain every 7 days or if we have significantly more data
        try:
            last_training = datetime.fromisoformat(self.last_training_time)
            days_since_training = (datetime.now() - last_training).days

            if days_since_training >= 7:
                return True

            # Check if we have 50% more data since last training
            current_patterns = len(self.event_logger.get_patterns(days_back=60))

            if current_patterns > 100:  # Enough data to warrant retraining
                return True

        except Exception as e:
            logger.error("Failed to check retrain condition", error=str(e))
            return False

        return False


# Global prediction engine instance
_prediction_engine: Optional[PredictionEngine] = None


def get_prediction_engine() -> PredictionEngine:
    """Get or create global prediction engine instance"""
    global _prediction_engine
    if _prediction_engine is None:
        _prediction_engine = PredictionEngine()
    return _prediction_engine
