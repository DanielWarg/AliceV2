#!/usr/bin/env python3
import json, sys, statistics as st, os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from psi import psi, bucket
from ks import ks_stat

DEFAULT_GATES = {"PSI_MAX": 0.20, "KS_MAX": 0.20, "VERIFIER_FAIL_MAX": 0.01}

def load(path):
    return json.load(open(path, "r", encoding="utf-8"))

def main(report="data/rl/prefs/v1/report.json", telemetry="data/ops/telemetry_window.json"):
    gates = DEFAULT_GATES
    rep = load(report) if os.path.exists(report) else {}
    if not os.path.exists(telemetry):
        print(f"[drift_watch] Telemetri saknas: {telemetry}", file=sys.stderr)
        sys.exit(2)
    tel = load(telemetry)
    # Expect telemetry schema with arrays: length_chars, verifier_ok[], latency_ms[]
    length = tel.get("length_chars", [])
    ver = tel.get("verifier_ok", [])
    lat = tel.get("latency_ms", [])
    base_len = tel.get("baseline_length_chars", [])
    # PSI på intents (kräver intent_hist_{baseline,actual})
    p_base = tel.get("intent_hist_baseline", [1,1,1])
    p_act  = tel.get("intent_hist_actual", [1,1,1])

    psi_intents = psi(p_base, p_act)
    ks_len = ks_stat(base_len or [0], length or [0])
    verifier_fail = 1.0 - (sum(1 for x in ver if x)/max(1,len(ver)))

    status = {
        "psi_intents": round(psi_intents, 3),
        "ks_length": round(ks_len, 3),
        "verifier_fail": round(verifier_fail, 4),
    }
    ok = (psi_intents <= gates["PSI_MAX"] and
          ks_len <= gates["KS_MAX"] and
          verifier_fail <= gates["VERIFIER_FAIL_MAX"])
    print(json.dumps({"ok": ok, "metrics": status}, ensure_ascii=False))
    sys.exit(0 if ok else 2)

if __name__ == "__main__":
    import os
    main()