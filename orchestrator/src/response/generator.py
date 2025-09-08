# Minimal generator-hook med verifier + 1-shot fix + T8 route controller + FormatGuard
import os

from .format_guard import preprocess_response
from .route_controller import report_outcome, want_adapter_route
from .verifier_client import self_correct, verify_text


def _gen_baseline(prompt: str) -> str:
    return f"Svar (baseline): {prompt}. Kort, svenskt svar."


def _gen_adapter(prompt: str) -> str:
    # Här skulle DPO/PEFT-adaptern aktiveras i verklig orchestrator.
    return f"Svar (adapter): {prompt}. Kort, svenskt svar med åäö och stramare stil."


def generate_response(prompt: str, runtime_metrics: dict | None = None) -> dict:
    runtime_metrics = runtime_metrics or {}
    use_adapter = want_adapter_route(runtime_metrics)

    raw = _gen_adapter(prompt) if use_adapter else _gen_baseline(prompt)

    # FormatGuard pre-processing (aktiveras med FORMATGUARD_ENABLED)
    format_guard_enabled = os.getenv("FORMATGUARD_ENABLED", "false").lower() == "true"
    formatguard_used = False
    formatguard_fixes = []

    if format_guard_enabled:
        # Pre-process innan verifier
        guard_result = preprocess_response(raw, enable_aggressive=False)
        if guard_result["changed"]:
            raw = guard_result["text"]
            formatguard_used = True
            formatguard_fixes = guard_result["fixes_applied"]

    v = verify_text(raw)

    retry_used = False
    text = raw
    if not v["ok"]:
        # Om FormatGuard inte var aktivt, försök det som sista utväg
        if not format_guard_enabled:
            guard_result = preprocess_response(raw, enable_aggressive=True)
            if guard_result["changed"]:
                potential_fix = guard_result["text"]
                v_fixed = verify_text(potential_fix)
                if v_fixed["ok"]:
                    text = potential_fix
                    formatguard_used = True
                    formatguard_fixes = guard_result["fixes_applied"]
                    v = v_fixed  # Uppdatera verifier status
                else:
                    # Fallback till self_correct om FormatGuard inte hjälpte
                    text = self_correct(raw, v.get("fix_hint", ""))
                    retry_used = True
            else:
                # FormatGuard hjälpte inte, kör self_correct
                text = self_correct(raw, v.get("fix_hint", ""))
                retry_used = True
        else:
            # FormatGuard var redan aktivt men hjälpte inte, kör self_correct
            text = self_correct(raw, v.get("fix_hint", ""))
            retry_used = True

    # enkel reward: verifier ok = 1, annars 0
    reward = 1.0 if v["ok"] else 0.0
    report_outcome(use_adapter, reward)

    return {
        "text": text,
        "route": "adapter" if use_adapter else "baseline",
        "retry_used": retry_used,
        "verifier_ok": v["ok"],
        "formatguard_used": formatguard_used,
        "formatguard_fixes": formatguard_fixes,
    }
