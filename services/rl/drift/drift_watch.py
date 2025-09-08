#!/usr/bin/env python3
import json
import os
import sys
import time
from typing import Any, Dict

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from ks import ks_stat
from psi import psi

DEFAULT_GATES = {"PSI_MAX": 0.20, "KS_MAX": 0.20, "VERIFIER_FAIL_MAX": 0.01}


def load_json(path: str) -> Dict[str, Any]:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def compute_snapshot(telemetry_path: str) -> Dict[str, Any]:
    tel = load_json(telemetry_path)
    length = tel.get("length_chars", [])
    base_len = tel.get("baseline_length_chars", length[:])
    ver = tel.get("verifier_ok", [])
    intents_base = tel.get("intent_hist_baseline", [1, 1, 1])
    intents_act = tel.get("intent_hist_actual", [1, 1, 1])

    m = {}
    m["psi_intents"] = float(round(psi(intents_base, intents_act), 6))
    m["ks_length"] = float(round(ks_stat(base_len or [0], length or [0]), 6))
    ok_cnt = sum(1 for x in ver if x)
    total = max(1, len(ver))
    m["verifier_fail"] = float(round(1.0 - ok_cnt / total, 6))
    m["n"] = total
    return m


def append_history(
    history_path: str, snapshot: Dict[str, Any], gates=DEFAULT_GATES
) -> None:
    ts = int(time.time())
    row = {
        "ts": ts,
        "psi_intents": snapshot["psi_intents"],
        "ks_length": snapshot["ks_length"],
        "verifier_fail": snapshot["verifier_fail"],
        "n": snapshot["n"],
        "gates": gates,
    }
    os.makedirs(os.path.dirname(history_path), exist_ok=True)
    with open(history_path, "a", encoding="utf-8") as f:
        f.write(json.dumps(row, ensure_ascii=False) + "\n")


def load_window(history_path: str, window_days: int = 7):
    if not os.path.exists(history_path):
        return []
    cutoff = time.time() - window_days * 86400
    rows = []
    with open(history_path, "r", encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            try:
                r = json.loads(line)
                if r.get("ts", 0) >= cutoff:
                    rows.append(r)
            except Exception:
                continue
    return rows


def summarize_window(rows):
    if not rows:
        return {"count": 0}

    def avg(k):
        vals = [r[k] for r in rows if k in r]
        return float(round(sum(vals) / len(vals), 6)) if vals else 0.0

    def p95(k):
        vals = sorted([r[k] for r in rows if k in r])
        if not vals:
            return 0.0
        idx = max(0, int(0.95 * len(vals)) - 1)
        return float(round(vals[idx], 6))

    return {
        "count": len(rows),
        "psi_intents_avg": avg("psi_intents"),
        "ks_length_avg": avg("ks_length"),
        "verifier_fail_avg": avg("verifier_fail"),
        "psi_intents_p95": p95("psi_intents"),
        "ks_length_p95": p95("ks_length"),
        "verifier_fail_p95": p95("verifier_fail"),
    }


def main():
    import argparse

    ap = argparse.ArgumentParser()
    ap.add_argument("--telemetry", default="data/ops/telemetry_window.json")
    ap.add_argument(
        "--report", default="data/rl/prefs/v1/report.json"
    )  # för bakåtkomp.
    ap.add_argument("--history", default="data/ops/drift_history.jsonl")
    ap.add_argument("--window_days", type=int, default=7)
    args = ap.parse_args()

    if not os.path.exists(args.telemetry):
        print(f"[drift_watch] Telemetri saknas: {args.telemetry}", file=sys.stderr)
        sys.exit(2)

    gates = DEFAULT_GATES
    snap = compute_snapshot(args.telemetry)
    append_history(args.history, snap, gates=gates)
    rows = load_window(args.history, args.window_days)
    roll = summarize_window(rows)

    ok = (
        snap["psi_intents"] <= gates["PSI_MAX"]
        and snap["ks_length"] <= gates["KS_MAX"]
        and snap["verifier_fail"] <= gates["VERIFIER_FAIL_MAX"]
    )
    out = {
        "ok": ok,
        "snapshot": snap,
        "rolling": roll,
        "gates": gates,
        "history_path": args.history,
    }
    print(json.dumps(out, ensure_ascii=False))
    sys.exit(0 if ok else 2)


if __name__ == "__main__":
    main()
