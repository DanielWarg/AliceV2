import re
from typing import Optional

# Svenska lexikon för deterministisk intent-klassificering
RE_WEATHER = re.compile(
    r"\b(väder|regn|snö|vind|blås|grader|temperatur|prognos|väderlek|paraply|vädret|klockan|tid)\b",
    re.I,
)
RE_CAL = re.compile(
    r"\b(möte|boka|kalender|påminn|event|träff|schemalägg|imorgon|nästa vecka|kl\.?\s?\d{1,2})\b",
    re.I,
)
RE_EMAIL = re.compile(
    r"\b(mail|mejl|e-post|skicka|brev|ämne|subject|inbox|mottagare|agenda)\b", re.I
)
RE_MEMORY = re.compile(
    r"\b(kom ihåg|spara detta|notera|minne|minnas|glöm|kommer ihåg|strategisk|plan|mål|prestationer)\b",
    re.I,
)
RE_GREETING = re.compile(
    r"\b(hej|tjena|hallå|god morgon|god kväll|god natt|tack)\b", re.I
)


def guard_intent_sv(text: str) -> Optional[str]:
    """
    Deterministic intent classification using Swedish regex patterns.
    Returns intent name or None if no clear match.
    """
    # Email patterns (högst prioritet för "agenda")
    if RE_EMAIL.search(text):
        return "email.create_draft"

    # Weather patterns
    if RE_WEATHER.search(text):
        return "weather.lookup"

    # Calendar patterns
    if RE_CAL.search(text):
        return "calendar.create_draft"

    # Memory patterns
    if RE_MEMORY.search(text):
        return "memory.query"

    # Greeting patterns
    if RE_GREETING.search(text):
        return "greeting.hello"

    return None


def intent_to_tool(intent: str) -> str:
    """
    Map intent to specific tool name for eval harness.
    """
    tool_map = {
        "weather.lookup": "weather.lookup",
        "calendar.create_draft": "calendar.create_draft",
        "email.create_draft": "email.create_draft",
        "memory.query": "memory.query",
        "greeting.hello": "none",  # Greeting behöver ingen tool
        "time.now": "time.now",
    }
    return tool_map.get(intent, "none")


def grammar_for(text: str) -> str:
    """
    Return intent-scoped grammar based on text content.
    """
    if RE_WEATHER.search(text):
        return 'root ::= ("weather"|"none")'
    elif RE_CAL.search(text):
        return 'root ::= ("calendar"|"none")'
    elif RE_EMAIL.search(text):
        return 'root ::= ("email"|"none")'
    elif RE_MEMORY.search(text):
        return 'root ::= ("memory"|"none")'
    elif RE_GREETING.search(text):
        return 'root ::= ("greeting"|"none")'
    else:
        return (
            'root ::= ("time"|"weather"|"memory"|"greeting"|"calendar"|"email"|"none")'
        )
