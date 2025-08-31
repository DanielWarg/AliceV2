from typing import Optional, Dict, Any
from prometheus_client import Counter

# Prometheus counter för tool errors
TOOL_ERROR_COUNTER = Counter(
    'alice_tool_error_total',
    'Total tool errors by tool and error class',
    ['tool', 'klass']
)

def classify_tool_error(status: Optional[int] = None, exc: Optional[Exception] = None) -> str:
    """Klassificera tool errors enligt standard schema"""
    if exc and "timeout" in str(exc).lower():
        return "timeout"
    if status == 429:
        return "429"
    if status and 500 <= status <= 599:
        return "5xx"
    if exc and "schema" in str(exc).lower():
        return "schema"
    return "other"

def record_tool_call(tool_name: str, success: bool, error_class: Optional[str] = None, 
                    latency_ms: Optional[float] = None) -> Dict[str, Any]:
    """Spela in tool call med klassificering och Prometheus metrics"""
    
    # Normalisera tool namn för att undvika hög cardinality
    normalized_tool = _normalize_tool_name(tool_name)
    
    # Spela in error om det finns
    if not success and error_class:
        TOOL_ERROR_COUNTER.labels(tool=normalized_tool, klass=error_class).inc()
    
    return {
        "name": tool_name,
        "normalized_name": normalized_tool,
        "ok": success,
        "klass": error_class,
        "lat_ms": latency_ms
    }

def _normalize_tool_name(tool_name: str) -> str:
    """Normalisera tool namn för Prometheus cardinality"""
    # Top tools som får egna labels
    top_tools = {
        "calendar.create", "calendar.read", "calendar.update",
        "email.send", "email.read", "email.draft",
        "web.search", "web.browse",
        "weather.current", "weather.forecast",
        "news.latest", "news.trending",
        "translate.swedish", "translate.english",
        "math.calculate", "math.estimate",
        "vision.rtsp", "vision.snapshot",
        "music.spotify", "music.search"
    }
    
    if tool_name in top_tools:
        return tool_name
    else:
        return "other"
