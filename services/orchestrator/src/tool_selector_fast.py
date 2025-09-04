#!/usr/bin/env python3
"""
Fast deterministic tool selector using fuzzy matching
Replaces 3B model for EASY/MEDIUM intents to improve tool precision
"""

from typing import Optional

from rapidfuzz import fuzz

# Tool mapping with synonyms
TOOL_MAP = {
    "time.now": [
        "time",
        "klockan",
        "vad är klockan",
        "hur mycket är klockan",
        "tid",
        "time",
        "vilken tid",
        "nuvarande tid",
        "current time",
        "klockan?",
        "tid nu",
        "nuvarande tid",
        "vad är tiden?",
    ],
    "weather.lookup": [
        "weather",
        "väder",
        "temperaturen",
        "vädret",
        "weather lookup",
        "vad är vädret",
        "hur blir vädret",
        "vädret i",
        "weather in",
        "kolla vädret",
        "check weather",
        "temperatur",
        "regnar det",
    ],
    "memory.query": [
        "memory",
        "minns",
        "kom ihåg",
        "spara",
        "memory query",
        "kommer du ihåg",
        "vad sa vi",
        "minne",
        "remember",
        "vad pratade vi",
        "vad diskuterade vi",
        "spara detta",
    ],
    "greeting.hello": [
        "greeting",
        "hej",
        "hello",
        "hi",
        "tjena",
        "hallå",
        "god morgon",
        "god afton",
        "god kväll",
        "trevligt att träffas",
        "good morning",
        "good evening",
        "hej!",
        "hallå",
    ],
    "calendar.create_draft": [
        "calendar",
        "boka möte",
        "skapa möte",
        "boka tid",
        "calendar create draft",
        "schedule meeting",
        "book meeting",
        "boka konferensrum",
        "planera möte",
        "skapa kalender",
        "boka rum",
        "schedule appointment",
        "boka",
    ],
    "email.create_draft": [
        "email",
        "skicka email",
        "skicka mail",
        "maila till",
        "email create draft",
        "send email",
        "skriv ett mail",
        "skicka rapport",
        "email till",
        "skicka meddelande",
        "skriv email",
        "send mail",
        "maila",
    ],
}


def pick_tool(text: str) -> Optional[str]:
    """
    Pick the best tool using fuzzy matching
    Returns tool name if confidence > 80%, otherwise None
    """
    text_lower = text.lower().strip()

    best_tool = None
    best_score = 0

    # Check each tool's synonyms
    for tool, synonyms in TOOL_MAP.items():
        for synonym in synonyms:
            score = fuzz.partial_ratio(text_lower, synonym.lower())
            if score > best_score:
                best_score = score
                best_tool = tool

    print(f"🔍 Tool match: '{text}' → {best_tool} (score: {best_score})")

    if best_score >= 65:  # Lowered from 80 to catch more variants
        return best_tool

    print(f"❌ No tool match for: '{text}' (best score: {best_score})")
    return None


def get_tool_confidence(text: str, expected_tool: str) -> float:
    """
    Get confidence score for expected tool
    """
    text_lower = text.lower().strip()

    if expected_tool not in TOOL_MAP:
        return 0.0

    synonyms = TOOL_MAP[expected_tool]
    best_score = 0.0

    for synonym in synonyms:
        score = fuzz.partial_ratio(text_lower, synonym)
        best_score = max(best_score, score)

    return best_score / 100.0


# Test function
def test_tool_selector():
    """Test the tool selector with sample inputs"""
    test_cases = [
        ("Vad är klockan?", "time.now"),
        ("Vad är vädret i Stockholm?", "weather.lookup"),
        ("Hej!", "greeting.hello"),
        ("Boka ett möte imorgon", "calendar.create_draft"),
        ("Skicka ett mail till chef@företag.se", "email.create_draft"),
        ("Kommer du ihåg vad vi pratade om?", "memory.query"),
    ]

    print("🧪 Testing tool selector...")
    for text, expected in test_cases:
        result = pick_tool(text)
        confidence = get_tool_confidence(text, expected)
        status = "✅" if result == expected else "❌"
        print(
            f"{status} '{text}' → {result} (expected: {expected}, confidence: {confidence:.1%})"
        )


if __name__ == "__main__":
    test_tool_selector()
