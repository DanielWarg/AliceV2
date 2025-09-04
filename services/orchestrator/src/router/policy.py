"""
Router policy for choosing between micro, planner, and deep routes.
"""

import re
import structlog
from typing import Dict, Any, List, Tuple, Optional
from dataclasses import dataclass
import os

logger = structlog.get_logger(__name__)

@dataclass
class RouteDecision:
    """Route decision with reasoning"""
    route: str  # "micro", "planner", "deep"
    confidence: float  # 0.0 to 1.0
    reason: str
    features: Dict[str, Any]

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
            r"förklara|explain|analysera|analyze",  # Explanation/analysis
            r"sammanfatta|summarize|summary",  # Summarization
            r"jämför|compare|skillnad|difference",  # Comparison
            r"varför|why|orsak|cause",  # Reasoning
            r"hur fungerar|how does|process",  # Process explanation
            r"beräkna|calculate|math|matematik",  # Complex calculations
            r"rekommendera|recommend|suggest",  # Recommendations
            r"utveckla|develop|expand|utökad",  # Development/expansion
        ]
        
        # Compile patterns for efficiency
        self.micro_regex = [re.compile(pattern, re.IGNORECASE) for pattern in self.micro_patterns]
        self.planner_regex = [re.compile(pattern, re.IGNORECASE) for pattern in self.planner_patterns]
        self.deep_regex = [re.compile(pattern, re.IGNORECASE) for pattern in self.deep_patterns]
    
    def analyze_text(self, text: str) -> Dict[str, Any]:
        """Analyze text and extract features for routing"""
        text_lower = text.lower()
        text_length = len(text)
        word_count = len(text.split())
        
        # Count pattern matches
        micro_matches = sum(1 for pattern in self.micro_regex if pattern.search(text))
        planner_matches = sum(1 for pattern in self.planner_regex if pattern.search(text))
        deep_matches = sum(1 for pattern in self.deep_regex if pattern.search(text))
        
        # Additional features
        has_question_mark = "?" in text
        has_exclamation = "!" in text
        has_numbers = bool(re.search(r'\d', text))
        has_urls = bool(re.search(r'http[s]?://', text))
        
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
        """Decide which route to take based on text analysis"""
        features = self.analyze_text(text)
        
        # Calculate scores for each route
        micro_score = self._calculate_micro_score(features)
        planner_score = self._calculate_planner_score(features)
        deep_score = self._calculate_deep_score(features)
        
        # Enhanced micro routing for better tool precision
        # Prefer micro for EASY/MEDIUM scenarios to use fast tool selector
        if micro_score > 0.3:  # Lower threshold for micro
            micro_score *= 1.5  # Boost micro preference
            planner_score *= 0.5  # Reduce planner preference

        # Apply MICRO_MAX_SHARE cap with real tracking
        import os
        from ..utils.quota_tracker import get_quota_tracker
        
        micro_max_share = float(os.getenv("MICRO_MAX_SHARE", "0.2"))
        quota_tracker = get_quota_tracker("micro_routing")
        
        # Check if micro quota is exceeded
        if quota_tracker.is_quota_exceeded(micro_max_share):
            logger.info("MICRO quota exceeded - forcing planner route", 
                       current_share=quota_tracker.get_current_share(),
                       max_share=micro_max_share)
            # Force planner route by boosting planner score
            planner_score *= 3.0
            micro_score *= 0.1
        else:
            # Normal routing with slight micro preference for better precision
            if micro_score > 0.3:
                micro_score *= 1.2
        
        # Normalize scores
        total_score = micro_score + planner_score + deep_score
        if total_score > 0:
            micro_score /= total_score
            planner_score /= total_score
            deep_score /= total_score
        
        # Determine route with highest score
        scores = [
            ("micro", micro_score),
            ("planner", planner_score),
            ("deep", deep_score)
        ]
        
        best_route, best_score = max(scores, key=lambda x: x[1])
        
        # Generate reasoning
        reason = self._generate_reason(best_route, features, scores)
        
        # Record decision for quota tracking
        quota_tracker.record_decision(best_route)
        
        logger.info("Route decision made", 
                   route=best_route, 
                   confidence=best_score,
                   reason=reason,
                   features=features,
                   quota_share=quota_tracker.get_current_share())
        
        return RouteDecision(
            route=best_route,
            confidence=best_score,
            reason=reason,
            features=features
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
    
    def _generate_reason(self, route: str, features: Dict[str, Any], scores: List[Tuple[str, float]]) -> str:
        """Generate human-readable reason for route decision"""
        if route == "micro":
            if features["micro_matches"] > 0:
                return f"Enkel fråga/hälsning ({features['micro_matches']} micro-mönster)"
            elif features["text_length"] < 50:
                return f"Kort text ({features['text_length']} tecken)"
            else:
                return "Enkel interaktion"
        
        elif route == "planner":
            if features["planner_matches"] > 0:
                return f"Åtgärd/planering ({features['planner_matches']} planner-mönster)"
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
