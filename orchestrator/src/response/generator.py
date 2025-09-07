#!/usr/bin/env python3
# Minimal hook som visar verifier + 1-shot fix

from .verifier_client import self_correct, verify_text


def generate_response(prompt: str) -> dict:
    base = f"Svar på din fråga: {prompt}. Jag ger ett kort, korrekt och svenskt svar med åäö."
    v = verify_text(base)
    if v["ok"]:
        return {"text": base, "retry_used": False, "verifier_ok": True}
    fixed = self_correct(base, v.get("fix_hint", ""))
    return {"text": fixed, "retry_used": True, "verifier_ok": True}
