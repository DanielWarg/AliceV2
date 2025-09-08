#!/usr/bin/env python3
# Skapar enkel fejkhistorik för lokal renderingstest.
import json, time, random
from pathlib import Path

p = Path("data/ops/drift_history.jsonl"); p.parent.mkdir(parents=True, exist_ok=True)
now = int(time.time()) - 3600*6
rows=[]
psi=0.22; ks=0.18; vf=0.008

for i in range(60):
    rows.append({
        "ts": now + i*360,
        "psi_intents": max(0.0, psi + random.uniform(-0.05,0.05)),
        "ks_length":   max(0.0, ks  + random.uniform(-0.04,0.04)),
        "verifier_fail": max(0.0, vf + random.uniform(-0.006,0.006))
    })

with p.open("w",encoding="utf-8") as f:
    for r in rows:
        f.write(json.dumps(r)+"\n")

print(f"[fake] wrote ~{len(rows)} points → {p}")