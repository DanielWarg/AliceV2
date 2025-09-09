#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import argparse
import json
import random
from pathlib import Path

random.seed(7)

INPUTS = [
    "data/dpo_v1/processed/dpo_pairs.pku.v1.jsonl",
    "data/dpo_v1/processed/dpo_pairs.hh.v1.jsonl",
    "data/dpo_v1/processed/dpo_pairs.sv.translated.v1.jsonl",
    "data/dpo_v1/processed/dpo_pairs.sv.synth.v2.jsonl",
    "data/dpo_v1/processed/dpo_pairs.sv.mt_local.v1.jsonl",
    "data/dpo_v1/processed/dpo_pairs.sv.synth.v3.jsonl",
]


def load_jsonl(p: Path):
    with p.open("r", encoding="utf-8") as f:
        for line in f:
            yield json.loads(line)


def dedup(rows):
    seen = set()
    out = []
    for r in rows:
        k = (r["prompt"][:400], r["chosen"][:400])
        if k in seen:
            continue
        seen.add(k)
        out.append(r)
    return out


def write_jsonl(p: Path, rows):
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open("w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")


def split(rows, ratios=(0.8, 0.1, 0.1)):
    random.shuffle(rows)
    n = len(rows)
    n_tr = int(n * ratios[0])
    n_val = int(n * ratios[1])
    return rows[:n_tr], rows[n_tr : n_tr + n_val], rows[n_tr + n_val :]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--target", type=int, default=4000)
    args = ap.parse_args()

    rows = []
    for path in INPUTS:
        p = Path(path)
        if p.exists():
            rows.extend(load_jsonl(p))
    rows = dedup(rows)

    total = len(rows)
    if total >= args.target:
        rows = rows[: args.target]
    missing = max(0, args.target - total)

    write_jsonl(Path("data/dpo_v1/processed/dpo_pairs.v1.jsonl"), rows)
    tr, va, te = split(rows)
    write_jsonl(Path("data/dpo_v1/splits/v1/train.jsonl"), tr)
    write_jsonl(Path("data/dpo_v1/splits/v1/val.jsonl"), va)
    write_jsonl(Path("data/dpo_v1/splits/v1/test.jsonl"), te)

    # liten rapport
    def cnt(key):
        from collections import Counter

        return dict(Counter(r.get(key, "") for r in rows))

    print("✅ Combine klart")
    print("Total:", total, "(saknas", missing, "för att nå", args.target, ")")
    print("Lang:", cnt("lang"))
    print("Domain:", cnt("domain"))
    print("Källor:", cnt("source"))


if __name__ == "__main__":
    main()
