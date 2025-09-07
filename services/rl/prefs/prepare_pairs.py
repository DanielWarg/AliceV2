#!/usr/bin/env python3
import argparse
import json
import random
import re
from pathlib import Path


def score_phi(meta, cfg):
    phi = cfg.get("phi_weights", {})
    correctness = 1.0 if not meta.get("error") else 0.0
    brevity = (
        1.0
        if meta.get("len", 0)
        <= cfg.get("labeling", {}).get("brevity_target_chars", 450)
        else 0.5
    )
    energy = 1.0 if meta.get("len", 0) < 600 else 0.6
    latency = 1.0 if meta.get("fast_mode") else 0.7
    swedish = 1.0 if meta.get("lang", "sv").startswith("sv") else 0.3
    return (
        phi.get("correctness", 0) * correctness
        + phi.get("brevity", 0) * brevity
        + phi.get("energy", 0) * energy
        + phi.get("latency", 0) * latency
        + phi.get("style_swedish", 0) * swedish
    )


def load_cfg(cfg_path):
    import yaml

    with open(cfg_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--in", dest="inp", required=True, help="episodes jsonl")
    ap.add_argument("--out", dest="out", required=True, help="pairs jsonl")
    ap.add_argument("--cfg", dest="cfg", default="services/rl/prefs/config_prefs.yaml")
    args = ap.parse_args()

    cfg = load_cfg(args.cfg)
    outdir = Path(args.out).parent
    outdir.mkdir(parents=True, exist_ok=True)

    rng = random.Random(1337)
    patterns_banned = [
        re.compile(pat, re.I)
        for pat in cfg.get("labeling", {}).get("banned_patterns", [])
    ]

    total = 0
    kept = 0
    with open(args.inp, "r", encoding="utf-8") as fin, open(
        args.out, "w", encoding="utf-8"
    ) as fout:
        for line in fin:
            total += 1
            try:
                ex = json.loads(line)
            except:
                continue
            prompt = ex.get("prompt", "")
            a = ex.get("resp_a") or (
                ex.get("answer_short") or (ex.get("answer", "")[:400].strip())
            )
            b = ex.get("resp_b") or (
                ex.get("answer_long") or (ex.get("answer", "")[:800] + " Detaljer: ...")
            )
            if not a or not b:
                continue

            meta_a = {"len": len(a), "fast_mode": True, "lang": "sv", "error": False}
            meta_b = {"len": len(b), "fast_mode": False, "lang": "sv", "error": False}

            if any(p.search(a) or p.search(b) for p in patterns_banned):
                continue

            score_a = score_phi(meta_a, cfg)
            score_b = score_phi(meta_b, cfg)
            win_label = "A" if score_a >= score_b else "B"

            pair = {
                "prompt": prompt,
                "A": a,
                "B": b,
                "meta": {"A": meta_a, "B": meta_b},
                "win_label": win_label,
            }
            fout.write(json.dumps(pair, ensure_ascii=False) + "\n")
            kept += 1

    print(f"[prepare_pairs] total={total} kept={kept} → {args.out}")


if __name__ == "__main__":
    main()
