"""
Fibonacci AI Architecture - Router policy for natural routing decisions.
Using the golden ratio and Fibonacci principles for optimal load distribution.
"""

import os
import re
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

import structlog

from ..config.fibonacci import (
    GOLDEN_RATIO,
    calculate_golden_ratio_threshold,
    get_fibonacci_weight,
)

logger = structlog.get_logger(__name__)


@dataclass
class RouteDecision:
    """Fibonacci-enhanced route decision with golden ratio confidence"""

    route: str  # "micro", "planner", "deep", "hybrid", "orchestrated"
    confidence: float  # 0.0 to 1.0, adjusted by golden ratio
    reason: str
    features: Dict[str, Any]
    fibonacci_weight: int  # Fibonacci number for this route
    golden_ratio_adjustment: float  # Golden ratio optimization


class RouterPolicy:
    """Policy for routing requests to appropriate LLM"""

    def __init__(self):
        # Micro route patterns (simple, fast responses)
        self.micro_patterns = [
            r"hej|hello|hi|tjena|hallå",  # Greetings
            r"vad är klockan|hur mycket är klockan|tid",  # Time
            r"vad är vädret|väder|weather",  # Weather fast-route
            r"tack|thanks",  # Thanks
            r"vem är du|vad kan du|kan du",  # Capability questions
            r"ja|nej|ok|okej",  # Simple responses
            r"minne|kom ihåg|påminn|memory|note",  # Simple memory ops
        ]

        # Planner route patterns (actions, tools, planning)
        self.planner_patterns = [
            r"boka|skapa|schedule|book",  # Booking
            r"skicka|send|mail|email",  # Sending
            r"visa|show|display|kamera|camera",  # Display/show
            r"planera|plan|schedule",  # Planning
            r"hitta|find|search|sök",  # Search
            r"kopiera|copy|flytta|move",  # File operations
            r"skapa|create|new",  # Creation
            r"ta bort|delete|remove",  # Deletion
            r"ändra|change|modify|update",  # Modification
        ]

        # Deep route patterns (complex reasoning, analysis)
        self.deep_patterns = [
            r"förklara|explain|analysera|analyze|beskriv|describe",  # Explanation/analysis
            r"sammanfatta|summarize|summary|summering",  # Summarization
            r"jämför|compare|skillnad|difference|kontrast",  # Comparison
            r"varför|why|orsak|cause|anledning",  # Reasoning
            r"hur fungerar|how does|process|fungerar|mechanism",  # Process explanation
            r"beräkna|calculate|math|matematik|räkna",  # Complex calculations
            r"rekommendera|recommend|suggest|föreslå|råd",  # Recommendations
            r"utveckla|develop|expand|utökad|detaljerad",  # Development/expansion
            r"kvant|quantum|fysik|physics|teori|theory",  # Complex topics
            r"maskininlärning|machine learning|ai|artificial intelligence|djupinlärning",  # AI/ML topics
        ]

        # Compile patterns for efficiency
        self.micro_regex = [
            re.compile(pattern, re.IGNORECASE) for pattern in self.micro_patterns
        ]
        self.planner_regex = [
            re.compile(pattern, re.IGNORECASE) for pattern in self.planner_patterns
        ]
        self.deep_regex = [
            re.compile(pattern, re.IGNORECASE) for pattern in self.deep_patterns
        ]

    def analyze_text(self, text: str) -> Dict[str, Any]:
        """Analyze text and extract features for routing"""
        text_length = len(text)
        word_count = len(text.split())

        # Count pattern matches
        micro_matches = sum(1 for pattern in self.micro_regex if pattern.search(text))
        planner_matches = sum(
            1 for pattern in self.planner_regex if pattern.search(text)
        )
        deep_matches = sum(1 for pattern in self.deep_regex if pattern.search(text))

        # Additional features
        has_question_mark = "?" in text
        has_exclamation = "!" in text
        has_numbers = bool(re.search(r"\d", text))
        has_urls = bool(re.search(r"http[s]?://", text))

        return {
            "text_length": text_length,
            "word_count": word_count,
            "micro_matches": micro_matches,
            "planner_matches": planner_matches,
            "deep_matches": deep_matches,
            "has_question_mark": has_question_mark,
            "has_exclamation": has_exclamation,
            "has_numbers": has_numbers,
            "has_urls": has_urls,
            "is_long_text": text_length > 200,  # Threshold for deep processing
        }

    def decide_route(self, text: str) -> RouteDecision:
        """Fibonacci-enhanced route decision using natural progression"""
        features = self.analyze_text(text)

        # Calculate base scores for each route
        micro_score = self._calculate_micro_score(features)
        planner_score = self._calculate_planner_score(features)
        deep_score = self._calculate_deep_score(features)

        # Apply Fibonacci weights to create natural progression
        micro_weight = get_fibonacci_weight("micro")
        planner_weight = get_fibonacci_weight("planner")
        deep_weight = get_fibonacci_weight("deep")

        # Fibonacci-weighted scoring
        micro_fibonacci = micro_score * micro_weight
        planner_fibonacci = planner_score * planner_weight
        deep_fibonacci = deep_score * deep_weight

        # Golden ratio optimization for simple queries
        if (
            micro_score > calculate_golden_ratio_threshold(1.0)
            and features["text_length"] < 34
        ):  # Fibonacci threshold
            micro_fibonacci *= GOLDEN_RATIO  # Natural boost using phi

        # Apply MICRO_MAX_SHARE cap with Fibonacci-based tracking
        from ..utils.quota_tracker import get_quota_tracker

        micro_max_share = float(
            os.getenv("MICRO_MAX_SHARE", "0.3")
        )  # Increased to golden ratio proportion
        quota_tracker = get_quota_tracker("micro_routing")

        # Check if micro quota is exceeded using Fibonacci thresholds
        if quota_tracker.is_quota_exceeded(micro_max_share):
            logger.info(
                "MICRO quota exceeded - Fibonacci cascade to planner",
                current_share=quota_tracker.get_current_share(),
                max_share=micro_max_share,
            )
            # Fibonacci cascade: micro(1) -> planner(2) -> deep(3)
            planner_fibonacci *= get_fibonacci_weight("hybrid")  # 5
            micro_fibonacci *= calculate_golden_ratio_threshold(0.1)
        else:
            # Natural Fibonacci progression - let weights decide
            pass

        # Golden ratio normalization
        total_fibonacci = micro_fibonacci + planner_fibonacci + deep_fibonacci
        if total_fibonacci > 0:
            micro_final = micro_fibonacci / total_fibonacci
            planner_final = planner_fibonacci / total_fibonacci
            deep_final = deep_fibonacci / total_fibonacci
        else:
            # Fallback to Fibonacci defaults
            micro_final = micro_weight / (micro_weight + planner_weight + deep_weight)
            planner_final = planner_weight / (
                micro_weight + planner_weight + deep_weight
            )
            deep_final = deep_weight / (micro_weight + planner_weight + deep_weight)

        # Determine route with Fibonacci weights
        scores = [
            ("micro", micro_final, micro_weight),
            ("planner", planner_final, planner_weight),
            ("deep", deep_final, deep_weight),
        ]

        best_route, best_score, best_weight = max(scores, key=lambda x: x[1])

        # Generate reasoning
        reason = self._generate_reason(best_route, features, scores)

        # Record decision for quota tracking
        quota_tracker.record_decision(best_route)

        logger.info(
            "Route decision made",
            route=best_route,
            confidence=best_score,
            reason=reason,
            features=features,
            quota_share=quota_tracker.get_current_share(),
        )

        # Calculate golden ratio adjustment
        golden_adjustment = (
            best_score * GOLDEN_RATIO
            if best_route == "micro" and features["text_length"] < 34
            else 1.0
        )

        return RouteDecision(
            route=best_route,
            confidence=best_score,
            reason=reason,
            features=features,
            fibonacci_weight=best_weight,
            golden_ratio_adjustment=golden_adjustment,
        )

    def _calculate_micro_score(self, features: Dict[str, Any]) -> float:
        """Calculate score for micro route"""
        score = 0.0

        # Pattern matches
        score += features["micro_matches"] * 2.0

        # Short text preference
        if features["text_length"] < 50:
            score += 1.0
        elif features["text_length"] < 100:
            score += 0.5

        # Simple questions
        if features["has_question_mark"] and features["word_count"] < 10:
            score += 1.0

        # Greetings and simple interactions
        if features["micro_matches"] > 0 and features["word_count"] < 5:
            score += 2.0

        return score

    def _calculate_planner_score(self, features: Dict[str, Any]) -> float:
        """Calculate score for planner route"""
        score = 0.0

        # Pattern matches
        score += features["planner_matches"] * 2.0

        # Action-oriented text
        if features["planner_matches"] > 0:
            score += 1.5

        # Medium length text
        if 50 <= features["text_length"] <= 200:
            score += 0.5

        # Questions about actions
        if features["has_question_mark"] and features["planner_matches"] > 0:
            score += 1.0

        return score

    def _calculate_deep_score(self, features: Dict[str, Any]) -> float:
        """Calculate score for deep route"""
        score = 0.0

        # Pattern matches
        score += features["deep_matches"] * 2.0

        # Long text preference
        if features["text_length"] > 200:
            score += 2.0
        elif features["text_length"] > 100:
            score += 1.0

        # Complex reasoning patterns
        if features["deep_matches"] > 0:
            score += 1.5

        # URLs or complex content
        if features["has_urls"]:
            score += 1.0

        # Numbers (potential calculations)
        if features["has_numbers"] and features["deep_matches"] > 0:
            score += 0.5

        return score

    def _generate_reason(
        self, route: str, features: Dict[str, Any], scores: List[Tuple[str, float]]
    ) -> str:
        """Generate human-readable reason for route decision"""
        if route == "micro":
            if features["micro_matches"] > 0:
                return (
                    f"Enkel fråga/hälsning ({features['micro_matches']} micro-mönster)"
                )
            elif features["text_length"] < 50:
                return f"Kort text ({features['text_length']} tecken)"
            else:
                return "Enkel interaktion"

        elif route == "planner":
            if features["planner_matches"] > 0:
                return (
                    f"Åtgärd/planering ({features['planner_matches']} planner-mönster)"
                )
            else:
                return "Målgången interaktion"

        elif route == "deep":
            if features["deep_matches"] > 0:
                return f"Komplex analys ({features['deep_matches']} deep-mönster)"
            elif features["text_length"] > 200:
                return f"Lång text ({features['text_length']} tecken)"
            else:
                return "Komplex fråga"

        return "Standard routing"


# Global router policy instance
_router_policy: Optional[RouterPolicy] = None


def get_router_policy() -> RouterPolicy:
    """Get or create global router policy instance"""
    global _router_policy
    if _router_policy is None:
        _router_policy = RouterPolicy()
    return _router_policy
