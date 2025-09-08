import json
import re
from typing import Any, Dict, Tuple

import yaml

# ––– Helpers –––

SW_WORDS = r"\b(och|det|är|inte|att|som|för|men|så|på|en|ett|vi|du|jag|kan|ska|bör)\b"


def _looks_swedish(text: str) -> bool:
    return (
        any(ch in text for ch in "åäöÅÄÖ")
        or re.search(SW_WORDS, text, re.I) is not None
    )


def _balanced_fences(text: str) -> bool:
    return text.count("```") % 2 == 0


def _json_like(text: str) -> bool:
    t = text.strip()
    if t.startswith("{") and t.endswith("}"):
        return True
    # json code-fence
    return "```json" in t.lower()


def _extract_json(text: str) -> str:
    m = re.search(r"```json\s*(.*?)\s*```", text, re.I | re.S)
    if m:
        return m.group(1).strip()
    t = text.strip()
    if t.startswith("{"):
        return t
    return ""


def _repair_json(s: str) -> Tuple[str, bool]:
    """Very small repair: fix common trailing commas & brace/bracket mismatch."""
    fixed = re.sub(r",\s*([}]])", r"\1", s)  # drop trailing commas
    # balance braces
    open_b, close_b = fixed.count("{"), fixed.count("}")
    if open_b > close_b:
        fixed += "}" * (open_b - close_b)
    if close_b > open_b:
        fixed = "{" * (close_b - open_b) + fixed
    open_a, close_a = fixed.count("["), fixed.count("]")
    if open_a > close_a:
        fixed += "]" * (open_a - close_a)
    if close_a > open_a:
        fixed = "[" * (close_a - open_a) + fixed
    changed = fixed != s
    return fixed, changed


def _validate_markdown_rules(text: str, cfg: Dict[str, Any], reasons: list):
    max_headers = cfg.get("verifier", {}).get("max_markdown_headers", 12)
    headers = len(re.findall(r"^\s*#{1,6}\s", text, flags=re.M))
    if headers > max_headers:
        reasons.append(f"too_many_headers:{headers}>{max_headers}")
    if cfg.get("verifier", {}).get(
        "require_code_block_closure", True
    ) and not _balanced_fences(text):
        reasons.append("unbalanced_code_fences")


def _validate_json_schema(text: str, reasons: list) -> bool:
    """Optional JSON: if present, must parse; minimal schema: object with <= 32 keys; strings ≤ 8k chars."""
    raw = _extract_json(text)
    if not raw:  # no json present → not required
        return True
    try:
        obj = json.loads(raw)
        if not isinstance(obj, dict):
            reasons.append("json_not_object")
            return False
        if len(obj.keys()) > 32:
            reasons.append("json_too_many_keys")
            return False
        for k, v in obj.items():
            if isinstance(v, str) and len(v) > 8000:
                reasons.append("json_value_too_long")
                return False
        return True
    except json.JSONDecodeError:
        # try repair once
        fixed, changed = _repair_json(raw)
        if not changed:
            reasons.append("json_parse_error")
            return False
        try:
            obj = json.loads(fixed)
            return True
        except Exception:
            reasons.append("json_parse_error_after_repair")
            return False


def verify(text: str, cfg: Dict[str, Any]) -> Dict[str, Any]:
    reasons = []
    ok = True

    # length
    max_len = cfg.get("verifier", {}).get("max_len", 1400)
    if len(text) > max_len:
        ok = False
        reasons.append(f"max_len_exceeded:{len(text)}>{max_len}")

    # language
    if cfg.get("verifier", {}).get("lang_hint") == "sv" and not _looks_swedish(text):
        ok = False
        reasons.append("lang_check_failed: not clearly Swedish")

    # markdown rules
    _validate_markdown_rules(text, cfg, reasons)

    # banned/policy
    for pat in cfg.get("labeling", {}).get("banned_patterns", []):
        if re.search(pat, text, re.I):
            ok = False
            reasons.append(f"banned_pattern:{pat}")
    for word in cfg.get("verifier", {}).get("policy_forbidden", []):
        if re.search(re.escape(word), text, re.I):
            ok = False
            reasons.append(f"policy_forbidden:{word}")

    # claims that require tools
    if re.search(r"\b(temperatur|väder|grader)\b", text, re.I):
        reasons.append("claim_weather_detected: requires weather tool")
    if re.search(r"\b(\d+\s*[+\-*/]\s*\d+)\b", text):
        reasons.append("claim_math_detected: calculator recommended")
    if re.search(r"\b(klockan\s+är\s+\d{1,2}:\d{2})\b", text, re.I):
        reasons.append("claim_time_detected: datetime tool recommended")

    # optional JSON schema validation (if JSON is present)
    if not _validate_json_schema(text, reasons):
        ok = False

    # Final decision: claims without tools make it non-OK
    if any(r.startswith("claim_") for r in reasons):
        ok = False

    return {
        "ok": ok
        and len(
            [r for r in reasons if r.startswith("banned_") or r.startswith("policy_")]
        )
        == 0,
        "reasons": reasons,
        "fix_hint": "Korta svaret, skriv tydlig svenska, balansera ```-block, och använd verktyg för tid/väder/beräkningar. Om JSON används: håll den välformad.",
    }


def verify_response(prompt: str, answer: str, cfg: Dict[str, Any]) -> Dict[str, Any]:
    return verify(answer, cfg)


# CLI wrapper för manuella tester

if __name__ == "__main__":
    import argparse

    ap = argparse.ArgumentParser()
    ap.add_argument("--text", required=True)
    ap.add_argument("--cfg", default="services/rl/prefs/config_prefs.yaml")
    args = ap.parse_args()
    with open(args.cfg, "r", encoding="utf-8") as f:
        cfg = yaml.safe_load(f)
    print(json.dumps(verify(args.text, cfg), ensure_ascii=False))
