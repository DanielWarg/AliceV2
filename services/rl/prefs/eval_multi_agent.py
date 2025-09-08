#!/usr/bin/env python3
"""
T9 eval: kör på syntetiska triples (default) eller real-data via realdata_adapter (--realdata).
Output: data/rl/prefs/t9/multi_agent_report.json
"""

import json
import random
from pathlib import Path
from typing import List

from .agents.judge import judge
from .agents.pairwise import Candidate, Triple


def synth_triple(idx: int, sigma: float) -> Triple:
    import random

    true_scores = [random.gauss(mu, 1.0) for mu in (0.0, 0.3, 0.6)]
    ids = ["A", "B", "C"]
    texts = []
    for s in true_scores:
        L = max(80, int(600 - 120 * s + random.gauss(0, 60 * sigma)))
        texts.append("x" * L)
    cand = [
        Candidate(id=i, text=t, score=sc) for i, t, sc in zip(ids, texts, true_scores)
    ]
    winner_id = ids[true_scores.index(max(true_scores))]
    return Triple(prompt=f"Q{idx}", candidates=cand, winner_id=winner_id)


def eval_agents(
    cfg_path="ops/config/t9_agents.yaml",
    use_real=False,
    real_cfg="ops/config/t9_realdata.yaml",
):
    import yaml

    cfg = yaml.safe_load(open(cfg_path, "r", encoding="utf-8"))
    random.seed(int(cfg.get("seed", 9)))
    n = int(cfg.get("samples", 1000))
    sigma = float(cfg.get("noise_sigma", 0.8))
    agents = cfg.get("agents", [])
    report = {
        "seed": int(cfg.get("seed", 9)),
        "sigma": sigma,
        "agents": [],
        "mode": "real" if use_real else "synthetic",
    }

    triples: List[Triple] = []
    if use_real:
        from services.rl.prefs.realdata_adapter import build_triples, load_triples_jsonl

        rcfg = yaml.safe_load(open(real_cfg, "r", encoding="utf-8"))
        outp = rcfg["output"]["triples_path"]
        cnt = build_triples(real_cfg, outp)
        triples = load_triples_jsonl(outp)
        report["realdata_triples"] = cnt
    else:
        triples = [synth_triple(i, sigma) for i in range(n)]

    if use_real and len(triples) < int(
        yaml.safe_load(open(real_cfg, "r"))["window"].get("min_triples", 100)
    ):
        report["note"] = "Insufficient real triples, falling back to synthetic"
        triples = [synth_triple(i, sigma) for i in range(n)]
        report["mode"] = "synthetic_fallback"

    total = len(triples)
    for ag in agents:
        name = ag["name"]
        mode = f"{ag['ranker']}+{ag['aggregator']}".replace("+none", "-only")
        wins = 0
        for t in triples:
            out = judge(
                t,
                mode=(
                    "borda-only"
                    if mode == "borda-none"
                    else "borda+bt" if mode == "borda+bradley-terry" else "borda+bt"
                ),
            )
            # Om winner saknas i real-data, approximera "win" = kortast text (proxy) matchad
            if t.winner_id is None:
                true_winner = min(t.candidates, key=lambda c: len(c.text or "")).id
            else:
                true_winner = t.winner_id
            if out["winner_id"] == true_winner:
                wins += 1
        win_rate = wins / max(1, total)
        report["agents"].append(
            {"name": name, "mode": mode, "win_rate": round(win_rate, 4)}
        )

    Path("data/rl/prefs/t9").mkdir(parents=True, exist_ok=True)
    outp = Path(
        cfg.get("output", {}).get(
            "report_path", "data/rl/prefs/t9/multi_agent_report.json"
        )
    )
    outp.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False))
    return report


if __name__ == "__main__":
    import argparse

    ap = argparse.ArgumentParser()
    ap.add_argument("--realdata", action="store_true")
    ap.add_argument("--cfg", default="ops/config/t9_agents.yaml")
    ap.add_argument("--real_cfg", default="ops/config/t9_realdata.yaml")
    args = ap.parse_args()
    eval_agents(args.cfg, use_real=args.realdata, real_cfg=args.real_cfg)
