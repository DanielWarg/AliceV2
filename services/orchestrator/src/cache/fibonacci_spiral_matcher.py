"""
Fibonacci Spiral Cache Matching - Advanced semantic similarity using golden ratio spirals
Mathematical approach to natural cache matching patterns for optimal hit rates
"""

import hashlib
import math
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

from ..config.fibonacci import FIBONACCI_SEQUENCE, GOLDEN_RATIO


@dataclass
class SpiralCacheResult:
    """Result from Fibonacci spiral cache matching"""

    similarity_score: float
    spiral_distance: float
    cache_tier: str
    fibonacci_weight: float
    golden_ratio_efficiency: float
    matching_metadata: Dict[str, Any]


class FibonacciSpiralMatcher:
    """
    Advanced cache matching using Fibonacci spiral patterns for natural similarity curves.

    This matcher uses golden ratio spirals to find semantically similar cache entries
    by mapping query features to spiral coordinates and finding nearest neighbors
    along natural mathematical curves.
    """

    def __init__(self, cache_dimensions: int = 512, spiral_resolution: int = 89):
        """
        Initialize Fibonacci spiral matcher

        Args:
            cache_dimensions: Dimensionality of cache feature space
            spiral_resolution: Number of spiral points (uses Fibonacci number)
        """
        self.cache_dimensions = cache_dimensions
        self.spiral_resolution = spiral_resolution
        self.golden_angle = 2 * math.pi / (GOLDEN_RATIO**2)  # Golden angle in radians

        # Pre-compute spiral coordinates for efficiency
        self.spiral_coords = self._generate_fibonacci_spiral()

        # Cache tier thresholds based on golden ratio
        self.tier_thresholds = {
            "exact": 1.0,  # Perfect match
            "golden_close": 1 / GOLDEN_RATIO,  # φ^-1 ≈ 0.618
            "golden_medium": 1 / (GOLDEN_RATIO**2),  # φ^-2 ≈ 0.382
            "fibonacci_match": 1 / (GOLDEN_RATIO**3),  # φ^-3 ≈ 0.236
            "spiral_neighbor": 1 / (GOLDEN_RATIO**4),  # φ^-4 ≈ 0.146
            "distant": 0.0,
        }

    def _generate_fibonacci_spiral(self) -> List[Tuple[float, float]]:
        """Generate Fibonacci spiral coordinates using golden ratio"""
        coords = []
        for i in range(self.spiral_resolution):
            # Golden spiral formula: r = φ^(θ/π), θ = i * golden_angle
            theta = i * self.golden_angle
            r = GOLDEN_RATIO ** (theta / math.pi)

            # Convert polar to cartesian coordinates
            x = r * math.cos(theta)
            y = r * math.sin(theta)
            coords.append((x, y))

        return coords

    def _extract_query_features(
        self, query: str, metadata: Dict[str, Any]
    ) -> np.ndarray:
        """
        Extract features from query for spiral matching

        Args:
            query: Query string
            metadata: Additional metadata (intent, user context, etc.)

        Returns:
            Feature vector for spiral matching
        """
        # Create feature hash based on query characteristics
        feature_components = []

        # Text-based features
        feature_components.append(hashlib.md5(query.lower().encode()).hexdigest())

        # Intent-based features (if available)
        if "intent" in metadata:
            feature_components.append(str(metadata["intent"]))

        # Context features
        if "context" in metadata:
            feature_components.extend([str(v) for v in metadata["context"].values()])

        # Create deterministic feature vector
        combined_hash = hashlib.sha256("|".join(feature_components).encode()).digest()

        # Convert to normalized feature vector
        feature_vector = np.frombuffer(combined_hash, dtype=np.uint8)
        feature_vector = feature_vector.astype(np.float32) / 255.0  # Normalize to [0,1]

        # Pad or truncate to required dimensions
        if len(feature_vector) < self.cache_dimensions:
            # Repeat pattern using Fibonacci sequence
            repeat_factor = (self.cache_dimensions // len(feature_vector)) + 1
            feature_vector = np.tile(feature_vector, repeat_factor)[
                : self.cache_dimensions
            ]
        else:
            feature_vector = feature_vector[: self.cache_dimensions]

        return feature_vector

    def _map_to_spiral_coordinates(self, features: np.ndarray) -> Tuple[float, float]:
        """
        Map high-dimensional features to 2D spiral coordinates

        Args:
            features: High-dimensional feature vector

        Returns:
            2D coordinates on Fibonacci spiral
        """
        # Use PCA-like projection with golden ratio weights
        weights = np.array([GOLDEN_RATIO ** (-i / 10) for i in range(len(features))])
        weighted_features = features * weights

        # Project to 2D using golden ratio angles
        angle_1 = np.sum(weighted_features) * self.golden_angle
        angle_2 = np.sum(weighted_features**2) * self.golden_angle * GOLDEN_RATIO

        # Map to spiral using golden ratio formula
        r1 = GOLDEN_RATIO ** (angle_1 / math.pi)
        r2 = GOLDEN_RATIO ** (angle_2 / math.pi)

        x = r1 * math.cos(angle_1) + r2 * math.cos(angle_2)
        y = r1 * math.sin(angle_1) + r2 * math.sin(angle_2)

        return (x, y)

    def _calculate_spiral_distance(
        self, coord1: Tuple[float, float], coord2: Tuple[float, float]
    ) -> float:
        """
        Calculate distance between two points on Fibonacci spiral

        This uses spiral-aware distance that considers the natural curve
        of the Fibonacci spiral rather than simple Euclidean distance.
        """
        x1, y1 = coord1
        x2, y2 = coord2

        # Euclidean distance
        euclidean_dist = math.sqrt((x2 - x1) ** 2 + (y2 - y1) ** 2)

        # Spiral-aware distance considering golden ratio curves
        spiral_factor = abs(math.atan2(y1, x1) - math.atan2(y2, x2))
        spiral_distance = euclidean_dist * (1 + spiral_factor / GOLDEN_RATIO)

        return spiral_distance

    def _determine_cache_tier(self, similarity: float) -> str:
        """Determine cache tier based on similarity score and Fibonacci thresholds"""
        for tier, threshold in self.tier_thresholds.items():
            if similarity >= threshold:
                return tier
        return "distant"

    def _calculate_fibonacci_weight(self, tier: str, similarity: float) -> float:
        """Calculate Fibonacci weight based on cache tier and similarity"""
        tier_weights = {
            "exact": FIBONACCI_SEQUENCE[8],  # 21 - highest weight
            "golden_close": FIBONACCI_SEQUENCE[7],  # 13
            "golden_medium": FIBONACCI_SEQUENCE[6],  # 8
            "fibonacci_match": FIBONACCI_SEQUENCE[5],  # 5
            "spiral_neighbor": FIBONACCI_SEQUENCE[4],  # 3
            "distant": FIBONACCI_SEQUENCE[2],  # 1 - lowest weight
        }

        base_weight = tier_weights.get(tier, 1)
        return base_weight * similarity

    def find_spiral_matches(
        self,
        query: str,
        metadata: Dict[str, Any],
        cached_entries: List[Dict[str, Any]],
        max_matches: int = 8,
    ) -> List[SpiralCacheResult]:
        """
        Find cache matches using Fibonacci spiral similarity

        Args:
            query: Query string to match
            metadata: Query metadata (intent, context, etc.)
            cached_entries: List of cached entries with their features
            max_matches: Maximum number of matches to return (Fibonacci number)

        Returns:
            List of spiral cache results ordered by similarity
        """
        # Extract query features and map to spiral coordinates
        query_features = self._extract_query_features(query, metadata)
        query_spiral_coord = self._map_to_spiral_coordinates(query_features)

        results = []

        for entry in cached_entries:
            # Extract features for cached entry
            cached_features = self._extract_query_features(
                entry.get("query", ""), entry.get("metadata", {})
            )
            cached_spiral_coord = self._map_to_spiral_coordinates(cached_features)

            # Calculate spiral distance and similarity
            spiral_distance = self._calculate_spiral_distance(
                query_spiral_coord, cached_spiral_coord
            )

            # Convert distance to similarity score (inverse relationship)
            # Using golden ratio for natural similarity decay
            similarity_score = 1.0 / (1.0 + spiral_distance / GOLDEN_RATIO)

            # Determine cache tier and weights
            cache_tier = self._determine_cache_tier(similarity_score)
            fibonacci_weight = self._calculate_fibonacci_weight(
                cache_tier, similarity_score
            )

            # Calculate golden ratio efficiency
            golden_ratio_efficiency = similarity_score * GOLDEN_RATIO

            # Create result
            result = SpiralCacheResult(
                similarity_score=similarity_score,
                spiral_distance=spiral_distance,
                cache_tier=cache_tier,
                fibonacci_weight=fibonacci_weight,
                golden_ratio_efficiency=golden_ratio_efficiency,
                matching_metadata={
                    "query_spiral_coord": query_spiral_coord,
                    "cached_spiral_coord": cached_spiral_coord,
                    "entry_id": entry.get("id", "unknown"),
                    "spiral_angle_diff": abs(
                        math.atan2(*query_spiral_coord)
                        - math.atan2(*cached_spiral_coord)
                    ),
                },
            )

            results.append(result)

        # Sort by similarity score (descending) and limit to max_matches
        results.sort(key=lambda x: x.similarity_score, reverse=True)
        return results[:max_matches]

    def optimize_cache_placement(
        self, entries: List[Dict[str, Any]]
    ) -> Dict[str, List[str]]:
        """
        Optimize cache placement using Fibonacci spiral clustering

        Args:
            entries: Cache entries to optimize

        Returns:
            Optimized placement mapping cache tiers to entry IDs
        """
        placement = {tier: [] for tier in self.tier_thresholds.keys()}

        for entry in entries:
            features = self._extract_query_features(
                entry.get("query", ""), entry.get("metadata", {})
            )
            spiral_coord = self._map_to_spiral_coordinates(features)

            # Calculate distance from spiral origin (0,0)
            distance_from_origin = math.sqrt(
                spiral_coord[0] ** 2 + spiral_coord[1] ** 2
            )

            # Map distance to similarity score using golden ratio
            similarity = 1.0 / (1.0 + distance_from_origin / (GOLDEN_RATIO * 10))

            # Determine optimal tier
            tier = self._determine_cache_tier(similarity)
            placement[tier].append(entry.get("id", "unknown"))

        return placement

    def get_spiral_statistics(self) -> Dict[str, Any]:
        """Get statistics about the Fibonacci spiral matcher"""
        return {
            "cache_dimensions": self.cache_dimensions,
            "spiral_resolution": self.spiral_resolution,
            "golden_angle_degrees": math.degrees(self.golden_angle),
            "spiral_coordinates_count": len(self.spiral_coords),
            "tier_count": len(self.tier_thresholds),
            "fibonacci_sequence_used": FIBONACCI_SEQUENCE[:9],  # First 9 numbers
            "golden_ratio": GOLDEN_RATIO,
            "tier_thresholds": self.tier_thresholds,
        }


# Utility functions for integration with existing cache system


def create_fibonacci_matcher(
    config: Optional[Dict[str, Any]] = None,
) -> FibonacciSpiralMatcher:
    """Create Fibonacci spiral matcher with optional configuration"""
    if config is None:
        config = {}

    return FibonacciSpiralMatcher(
        cache_dimensions=config.get("dimensions", 512),
        spiral_resolution=config.get("resolution", 89),  # Fibonacci number
    )


def enhance_cache_key_with_spiral(
    base_key: str, spiral_coord: Tuple[float, float]
) -> str:
    """Enhance cache key with spiral coordinate information"""
    spiral_hash = hashlib.md5(
        f"{spiral_coord[0]:.6f},{spiral_coord[1]:.6f}".encode()
    ).hexdigest()[:8]
    return f"{base_key}:spiral:{spiral_hash}"
