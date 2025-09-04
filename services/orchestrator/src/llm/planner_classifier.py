"""
Simple classifier for planner tool selection using regex patterns.
This helps reduce complexity for the LLM by pre-classifying obvious cases.
"""

import re
from dataclasses import dataclass
from typing import Optional


@dataclass
class ClassificationResult:
    tool: str
    confidence: float
    reason: str
    use_llm: bool


class PlannerClassifier:
    """Simple regex-based classifier for tool selection"""

    def __init__(self):
        # High-confidence patterns (use classifier, skip LLM)
        self.high_confidence_patterns = {
            "calendar.create_draft": [
                r"boka\s+möte",
                r"skapa\s+möte",
                r"boka\s+tid",
                r"schedule\s+meeting",
                r"book\s+meeting",
                r"boka\s+konferensrum",
                r"planera\s+möte",
                r"skapa\s+kalender",
                r"boka\s+rum",
                r"schedule\s+appointment",
            ],
            "email.create_draft": [
                r"skicka\s+email",
                r"skicka\s+mail",
                r"maila\s+till",
                r"send\s+email",
                r"skriv\s+ett\s+mail",
                r"skicka\s+rapport",
                r"email\s+till",
                r"skicka\s+meddelande",
                r"skriv\s+email",
                r"send\s+mail",
            ],
            "weather.lookup": [
                r"vad\s+är\s+vädret",
                r"hur\s+blir\s+vädret",
                r"weather",
                r"väder",
                r"vädret\s+i",
                r"weather\s+in",
                r"kolla\s+vädret",
                r"check\s+weather",
            ],
            "memory.query": [
                r"kommer\s+du\s+ihåg",
                r"vad\s+sa\s+vi",
                r"minne",
                r"memory",
                r"kom\s+ihåg",
                r"remember",
                r"vad\s+pratade\s+vi",
                r"vad\s+diskuterade\s+vi",
            ],
            "time.now": [
                r"vad\s+är\s+klockan",
                r"hur\s+mycket\s+är\s+klockan",
                r"klockan",
                r"tid",
                r"time",
                r"vilken\s+tid",
                r"nuvarande\s+tid",
                r"current\s+time",
            ],
            "greeting.hello": [
                r"hej\b",
                r"hello\b",
                r"hi\b",
                r"tjena\b",
                r"hallå\b",
                r"god\s+morgon",
                r"god\s+afton",
                r"god\s+kväll",
                r"trevligt\s+att\s+träffas",
                r"good\s+morning",
                r"good\s+evening",
            ],
            "none": [
                r"tack\b",
                r"thanks\b",
                r"ja\b",
                r"nej\b",
                r"ok\b",
                r"okej\b",
                r"bra\s+jobbat",
                r"kan\s+du\s+hjälpa",
                r"help",
                r"hjälp",
            ],
        }

        # Compile patterns for efficiency
        self.compiled_patterns = {}
        for tool, patterns in self.high_confidence_patterns.items():
            self.compiled_patterns[tool] = [
                re.compile(pattern, re.IGNORECASE) for pattern in patterns
            ]

    def classify(self, text: str) -> ClassificationResult:
        """Classify text and determine if LLM is needed"""
        text_lower = text.lower().strip()

        # Check each tool's patterns
        best_match = None
        best_confidence = 0.0

        for tool, patterns in self.compiled_patterns.items():
            for pattern in patterns:
                if pattern.search(text_lower):
                    # Calculate confidence based on pattern specificity
                    confidence = self._calculate_confidence(pattern, text_lower)
                    if confidence > best_confidence:
                        best_confidence = confidence
                        best_match = tool

        # Determine if we should use LLM
        use_llm = (
            best_confidence < 0.7
        )  # Use LLM for uncertain cases (lowered threshold)

        if best_match:
            return ClassificationResult(
                tool=best_match,
                confidence=best_confidence,
                reason=f"Regex match: {best_match} (confidence: {best_confidence:.2f})",
                use_llm=use_llm,
            )
        else:
            return ClassificationResult(
                tool="none",
                confidence=0.0,
                reason="No pattern match",
                use_llm=True,  # Use LLM for unknown cases
            )

    def _calculate_confidence(self, pattern: re.Pattern, text: str) -> float:
        """Calculate confidence based on pattern specificity"""
        # Simple heuristic: longer patterns = higher confidence
        pattern_str = pattern.pattern
        base_confidence = min(len(pattern_str) / 20.0, 1.0)  # Cap at 1.0

        # Boost for exact matches
        if pattern.search(text):
            base_confidence += 0.2

        # Boost for multiple matches
        matches = len(pattern.findall(text))
        if matches > 1:
            base_confidence += 0.1 * matches

        return min(base_confidence, 1.0)


# Global classifier instance
_classifier: Optional[PlannerClassifier] = None


def get_planner_classifier() -> PlannerClassifier:
    """Get or create global classifier instance"""
    global _classifier
    if _classifier is None:
        _classifier = PlannerClassifier()
    return _classifier
