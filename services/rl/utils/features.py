"""
Feature engineering utilities for Alice RL system.

Implements hashing trick for categorical features and robust numeric scaling.
Designed for online learning with stable, reproducible features.
"""

from __future__ import annotations

import hashlib
from typing import Any, Dict, List, Optional, Tuple

import structlog

logger = structlog.get_logger(__name__)


def _signed_hash(s: str) -> int:
    """
    Create signed hash for hashing trick.

    Args:
        s: String to hash

    Returns:
        Signed integer hash
    """
    h = hashlib.sha256(s.encode("utf-8")).hexdigest()
    return int(h[:8], 16)


class FeatureMaker:
    """
    Feature engineering with hashing trick for categoricals and z-score for numerics.

    Designed for online learning scenarios where new categories may appear.
    Uses consistent hashing to ensure same features across train/test/prod.
    """

    def __init__(
        self,
        dim: int = 64,
        numeric_keys: Optional[List[str]] = None,
        categorical_keys: Optional[List[str]] = None,
        interaction_pairs: Optional[List[Tuple[str, str]]] = None,
    ):
        """
        Initialize feature maker.

        Args:
            dim: Hash dimension for categorical features
            numeric_keys: List of numeric feature names
            categorical_keys: List of categorical feature names
            interaction_pairs: List of (key1, key2) pairs for interaction features
        """
        self.dim = dim

        # Default feature sets based on Alice telemetry
        self.numeric_keys = numeric_keys or [
            "text_len",  # Length of input text
            "latency_ms",  # Response latency
            "cost_usd",  # LLM API cost
            "intent_confidence",  # NLU confidence if available
            "word_count",  # Number of words
            "cache_miss_score",  # How close was cache miss
        ]

        self.categorical_keys = categorical_keys or [
            "intent",  # NLU detected intent
            "lang",  # Language (sv, en, etc)
            "guardian_state",  # NORMAL, CAUTION, LOCKDOWN
            "time_of_day",  # morning, afternoon, evening, night
            "session_length",  # short, medium, long
            "route",  # micro, planner, deep (for training only)
        ]

        # Feature interactions (multiplicative combinations)
        self.interaction_pairs = interaction_pairs or [
            ("intent", "lang"),  # Intent-language combo
            ("intent", "guardian_state"),  # Intent-security combo
            ("latency_ms", "route"),  # Route performance
        ]

        # Learned statistics for numeric features
        self.means: Dict[str, float] = {}
        self.stds: Dict[str, float] = {}
        self.fitted = False

    def fit_numeric(self, rows: List[Dict[str, Any]]) -> None:
        """
        Fit numeric feature scaling parameters.

        Args:
            rows: List of record dicts for fitting
        """
        if not rows:
            logger.warning("No rows provided for fitting")
            return

        from statistics import mean, pstdev

        for key in self.numeric_keys:
            # Extract values with defensive defaults
            values = []
            for row in rows:
                val = row.get(key, 0.0)
                if val is None:
                    val = 0.0
                try:
                    values.append(float(val))
                except (ValueError, TypeError):
                    values.append(0.0)

            # Calculate robust statistics
            if values:
                m = mean(values)
                s = pstdev(values) if len(values) > 1 else 1.0

                # Prevent division by zero
                if s < 1e-6:
                    s = 1.0

                self.means[key] = m
                self.stds[key] = s

                logger.debug(
                    "Fitted numeric feature", key=key, mean=m, std=s, count=len(values)
                )
            else:
                self.means[key] = 0.0
                self.stds[key] = 1.0

        self.fitted = True
        logger.info(
            "Numeric fitting complete",
            features=len(self.numeric_keys),
            samples=len(rows),
        )

    def _extract_categorical_value(self, row: Dict[str, Any], key: str) -> str:
        """Extract and normalize categorical value."""
        val = row.get(key, "")

        if val is None:
            return "unknown"

        # Convert to string and normalize
        str_val = str(val).lower().strip()

        if not str_val:
            return "unknown"

        # Specific normalization for known keys
        if key == "time_of_day":
            # Extract hour if timestamp available
            timestamp = row.get("timestamp")
            if timestamp:
                try:
                    import datetime

                    if isinstance(timestamp, (int, float)):
                        dt = datetime.datetime.fromtimestamp(
                            timestamp / 1000.0
                        )  # Assume ms
                    else:
                        dt = datetime.datetime.fromisoformat(
                            str(timestamp).replace("Z", "+00:00")
                        )

                    hour = dt.hour
                    if 5 <= hour < 12:
                        return "morning"
                    elif 12 <= hour < 17:
                        return "afternoon"
                    elif 17 <= hour < 22:
                        return "evening"
                    else:
                        return "night"
                except Exception:
                    pass

            return "unknown"

        elif key == "session_length":
            # Estimate based on available data
            text_len = row.get("text_len", 0)
            if text_len < 50:
                return "short"
            elif text_len < 200:
                return "medium"
            else:
                return "long"

        return str_val

    def transform(self, row: Dict[str, Any]) -> List[float]:
        """
        Transform a single row into feature vector.

        Args:
            row: Dict with raw features

        Returns:
            Dense feature vector
        """
        if not self.fitted:
            logger.warning("FeatureMaker not fitted - using defaults")

        # Feature vector: [categorical_hash_features] + [numeric_features] + [interactions]
        total_dim = self.dim + len(self.numeric_keys) + len(self.interaction_pairs)
        x = [0.0] * total_dim

        # 1. Categorical features using hashing trick
        for key in self.categorical_keys:
            val = self._extract_categorical_value(row, key)

            if val == "unknown":
                continue

            # Hash to feature space
            feature_name = f"{key}={val}"
            idx = _signed_hash(feature_name) % self.dim

            # Sign based on value hash for better distribution
            sign = 1.0 if ((_signed_hash(val) % 2) == 0) else -1.0
            x[idx] += sign

        # 2. Numeric features (z-score normalized)
        for i, key in enumerate(self.numeric_keys):
            val = row.get(key, 0.0)
            if val is None:
                val = 0.0

            try:
                val = float(val)
            except (ValueError, TypeError):
                val = 0.0

            # Normalize using fitted stats
            mean = self.means.get(key, 0.0)
            std = self.stds.get(key, 1.0)

            normalized = (val - mean) / std

            # Clip extreme values to prevent instability
            normalized = max(-10.0, min(10.0, normalized))

            x[self.dim + i] = normalized

        # 3. Interaction features
        for i, (key1, key2) in enumerate(self.interaction_pairs):
            # For categorical x categorical
            if key1 in self.categorical_keys and key2 in self.categorical_keys:
                val1 = self._extract_categorical_value(row, key1)
                val2 = self._extract_categorical_value(row, key2)

                if val1 != "unknown" and val2 != "unknown":
                    interaction_name = f"{key1}={val1}*{key2}={val2}"
                    interaction_hash = _signed_hash(interaction_name) % self.dim
                    # Use value between -1 and 1
                    x[self.dim + len(self.numeric_keys) + i] = (
                        1.0 if (interaction_hash % 2 == 0) else -1.0
                    )

            # For numeric x categorical
            elif key1 in self.numeric_keys and key2 in self.categorical_keys:
                val1 = row.get(key1, 0.0)
                val2 = self._extract_categorical_value(row, key2)

                if val2 != "unknown":
                    try:
                        val1 = float(val1 or 0.0)
                        mean1 = self.means.get(key1, 0.0)
                        std1 = self.stds.get(key1, 1.0)
                        norm_val1 = (val1 - mean1) / std1

                        # Hash categorical to get coefficient
                        coeff = (
                            1.0 if (_signed_hash(f"{key2}={val2}") % 2 == 0) else -1.0
                        )
                        x[self.dim + len(self.numeric_keys) + i] = norm_val1 * coeff
                    except (ValueError, TypeError):
                        x[self.dim + len(self.numeric_keys) + i] = 0.0

            # For other combinations, use simple product if both numeric
            else:
                val1 = row.get(key1, 0.0)
                val2 = row.get(key2, 0.0)

                try:
                    val1 = float(val1 or 0.0)
                    val2 = float(val2 or 0.0)

                    # Normalize both if numeric
                    if key1 in self.numeric_keys:
                        mean1 = self.means.get(key1, 0.0)
                        std1 = self.stds.get(key1, 1.0)
                        val1 = (val1 - mean1) / std1

                    if key2 in self.numeric_keys:
                        mean2 = self.means.get(key2, 0.0)
                        std2 = self.stds.get(key2, 1.0)
                        val2 = (val2 - mean2) / std2

                    x[self.dim + len(self.numeric_keys) + i] = val1 * val2

                except (ValueError, TypeError):
                    x[self.dim + len(self.numeric_keys) + i] = 0.0

        return x

    def serialize(self) -> Dict[str, Any]:
        """Serialize feature maker for saving."""
        return {
            "version": "1.0",
            "dim": self.dim,
            "numeric_keys": self.numeric_keys,
            "categorical_keys": self.categorical_keys,
            "interaction_pairs": self.interaction_pairs,
            "means": self.means,
            "stds": self.stds,
            "fitted": self.fitted,
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "FeatureMaker":
        """Deserialize feature maker from dict."""
        fm = cls(
            dim=d.get("dim", 64),
            numeric_keys=d.get("numeric_keys", []),
            categorical_keys=d.get("categorical_keys", []),
            interaction_pairs=d.get("interaction_pairs", []),
        )
        fm.means = d.get("means", {})
        fm.stds = d.get("stds", {})
        fm.fitted = d.get("fitted", False)
        return fm

    def feature_names(self) -> List[str]:
        """Get human-readable feature names for debugging."""
        names = []

        # Categorical hash features
        for i in range(self.dim):
            names.append(f"hash_{i}")

        # Numeric features
        for key in self.numeric_keys:
            names.append(f"num_{key}")

        # Interaction features
        for key1, key2 in self.interaction_pairs:
            names.append(f"interact_{key1}*{key2}")

        return names

    def analyze_features(
        self, rows: List[Dict[str, Any]], sample_size: int = 1000
    ) -> Dict[str, Any]:
        """
        Analyze feature distribution for debugging.

        Args:
            rows: Sample of rows to analyze
            sample_size: Max samples to analyze

        Returns:
            Feature analysis dict
        """
        if not rows:
            return {"error": "No rows provided"}

        import random

        sample = random.sample(rows, min(len(rows), sample_size))

        # Transform all samples
        features_matrix = [self.transform(row) for row in sample]

        if not features_matrix:
            return {"error": "No features generated"}

        import statistics

        feature_stats = {}
        for i in range(len(features_matrix[0])):
            values = [x[i] for x in features_matrix]
            feature_stats[f"feature_{i}"] = {
                "mean": statistics.mean(values),
                "stdev": statistics.pstdev(values) if len(values) > 1 else 0.0,
                "min": min(values),
                "max": max(values),
                "nonzero_count": sum(1 for v in values if abs(v) > 1e-10),
            }

        return {
            "samples_analyzed": len(sample),
            "feature_dimension": len(features_matrix[0]),
            "feature_stats": feature_stats,
            "sparsity": sum(
                1
                for stats in feature_stats.values()
                if stats["nonzero_count"] / len(sample) < 0.1
            )
            / len(feature_stats),
        }
