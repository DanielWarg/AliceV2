from prometheus_client import Counter, Gauge

injection_suspected_total = Counter(
    "alice_injection_suspected_total", "Injection suspects"
)
tool_denied_total = Counter("alice_tool_denied_total", "Tool denials", ["reason"])
high_risk_confirm_total = Counter(
    "alice_high_risk_confirm_total", "High-risk confirmations", ["decision"]
)
security_mode_gauge = Gauge("alice_security_mode", "Security mode as gauge", ["mode"])


def set_mode(mode: str):
    for m in ("NORMAL", "STRICT", "LOCKDOWN"):
        security_mode_gauge.labels(mode=m).set(1 if m == mode else 0)
