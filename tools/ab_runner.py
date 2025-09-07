#!/usr/bin/env python3
import json, os, time, hashlib, random
from pathlib import Path

"""
Skapar A/B-kandidater från fryst promptlista för manuell bedömning.
A = baseline (utan ny adapter), B = v2 (med ny adapter)
I den här stubben simuleras A/B-svar med enkla heurstiker så panelen kan bedöma formatet.
Koppla senare till riktiga endpoints/orchestrator om så önskas.
"""

random.seed(7)

def fake_gen(prompt, mode):
    if mode == "A":
        return f"SVAR (baseline): {prompt} — ett något längre och utförligare svar med fler resonemang."
    return f"SVAR (v2): {prompt} — kort, direkt, på svenska med åäö, och utan onödig utfyllnad."

def main():
    src = Path("eval/human/prompts_swe_testset.jsonl")
    out = Path("eval/human/ab_candidates.jsonl")
    out.parent.mkdir(parents=True, exist_ok=True)
    rows = []
    with src.open("r", encoding="utf-8") as f:
        for line in f:
            if not line.strip(): continue
            p = json.loads(line)["prompt"]
            A = fake_gen(p, "A")
            B = fake_gen(p, "B")
            rows.append({"prompt": p, "A": A, "B": B})
    with out.open("w", encoding="utf-8") as g:
        for r in rows:
            g.write(json.dumps(r, ensure_ascii=False) + "\n")
    print(f"[ab_runner] Skrev {len(rows)} A/B-exempel → {out}")

if __name__ == "__main__":
    main()