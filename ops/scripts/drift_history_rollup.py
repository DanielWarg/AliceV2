#!/usr/bin/env python3
import argparse
import json
import os
import time
from pathlib import Path


def load_history(path):
    rows = []
    if not os.path.exists(path):
        return rows
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                try:
                    rows.append(json.loads(line))
                except:
                    pass
    return rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--history", default="data/ops/drift_history.jsonl")
    ap.add_argument("--out", default="data/ops/drift_rollup.json")
    args = ap.parse_args()

    rows = load_history(args.history)
    Path(os.path.dirname(args.out)).mkdir(parents=True, exist_ok=True)
    if not rows:
        json.dump(
            {"count": 0},
            open(args.out, "w", encoding="utf-8"),
            ensure_ascii=False,
            indent=2,
        )
        print("[rollup] no history yet")
        return

    # enkel komprimering: dagsbucket + min/avg/max
    buckets = {}
    for r in rows:
        day = time.strftime("%Y-%m-%d", time.gmtime(r.get("ts", 0)))
        b = buckets.setdefault(day, {"n": 0, "psi": [], "ks": [], "vf": []})
        b["n"] += 1
        b["psi"].append(r["psi_intents"])
        b["ks"].append(r["ks_length"])
        b["vf"].append(r["verifier_fail"])
    out = {}
    for day, b in sorted(buckets.items()):

        def agg(xs):
            xs = sorted(xs)
            avg = sum(xs) / len(xs)
            p95 = xs[int(0.95 * len(xs)) - 1] if xs else 0.0
            return {
                "min": xs[0],
                "avg": round(avg, 6),
                "p95": p95,
                "max": xs[-1],
                "n": len(xs),
            }

        out[day] = {
            "psi_intents": agg(b["psi"]),
            "ks_length": agg(b["ks"]),
            "verifier_fail": agg(b["vf"]),
            "events": b["n"],
        }
    json.dump(
        {"days": out, "total_points": len(rows)},
        open(args.out, "w", encoding="utf-8"),
        ensure_ascii=False,
        indent=2,
    )
    print(f"[rollup] wrote {args.out} with {len(rows)} points")


if __name__ == "__main__":
    main()
