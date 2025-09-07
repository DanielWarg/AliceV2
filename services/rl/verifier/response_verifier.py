#!/usr/bin/env python3
# Deterministisk verifierare: schema, policy & enkla claim-kontroller

import re, argparse, json, sys, yaml

def verify(text, cfg):
    reasons = []
    ok = True

    max_len = cfg.get("verifier",{}).get("max_len", 1400)
    if len(text) > max_len:
        ok = False
        reasons.append(f"max_len_exceeded:{len(text)}>{max_len}")

    if cfg.get("verifier",{}).get("lang_hint") == "sv":
        if not any(ch in text for ch in "åäöÅÄÖ"):
            if not re.search(r"\b(och|det|är|inte|att|som|för|men|så|på)\b", text, re.I):
                ok = False
                reasons.append("lang_check_failed: not clearly Swedish")

    banned = cfg.get("labeling",{}).get("banned_patterns", [])
    for pat in banned:
        if re.search(pat, text, re.I):
            ok = False
            reasons.append(f"banned_pattern:{pat}")

    policy_forbidden = cfg.get("verifier",{}).get("policy_forbidden", [])
    for word in policy_forbidden:
        if re.search(re.escape(word), text, re.I):
            ok = False
            reasons.append(f"policy_forbidden:{word}")

    if re.search(r"\b(temperatur|väder|grader)\b", text, re.I):
        reasons.append("claim_weather_detected: requires weather tool")
    if re.search(r"\b(\d+\s*[+\-*/]\s*\d+)\b", text):
        reasons.append("claim_math_detected: calculator recommended")

    return {"ok": ok and not any(r.startswith("claim_") for r in reasons),
            "reasons": reasons,
            "fix_hint": "Skriv på enkel svenska, kortfattat. Undvik spekulationer och hänvisa till verktyg vid väder/tid/beräkningar. Håll dig under maxlängd."}

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--text", required=True)
    ap.add_argument("--cfg", default="services/rl/prefs/config_prefs.yaml")
    args = ap.parse_args()
    with open(args.cfg, "r", encoding="utf-8") as f:
        cfg = yaml.safe_load(f)
    result = verify(args.text, cfg)
    print(json.dumps(result, ensure_ascii=False))

if __name__ == "__main__":
    main()