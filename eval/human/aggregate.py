#!/usr/bin/env python3
import collections
import json
import sys
from pathlib import Path


def main():
    cand = Path("eval/human/ab_candidates.jsonl")
    judge = Path("eval/human/judgments.jsonl")
    rep = Path("eval/human/human_report.json")
    if not judge.exists():
        print("[aggregate] Saknar eval/human/judgments.jsonl")
        sys.exit(2)
    total = 0
    wins = collections.Counter()
    notes = []
    with judge.open("r", encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            j = json.loads(line)
            w = j.get("winner")
            if w in ("A", "B"):
                wins[w] += 1
                total += 1
            if j.get("notes"):
                notes.append(j["notes"])
    win_rate_B = (wins["B"] / total) if total else 0.0
    report = {
        "n_judgments": total,
        "wins": {"A": wins["A"], "B": wins["B"]},
        "win_rate_B": round(win_rate_B, 3),
        "notes_sample": notes[:10],
    }
    rep.parent.mkdir(parents=True, exist_ok=True)
    with rep.open("w", encoding="utf-8") as g:
        json.dump(report, g, ensure_ascii=False, indent=2)
    print("[aggregate]", report)


if __name__ == "__main__":
    main()
