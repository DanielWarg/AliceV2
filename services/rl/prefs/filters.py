#!/usr/bin/env python3
import argparse
import json
import re


def is_pii(text, patterns):
    for pat in patterns:
        if re.search(pat, text):
            return True
    return False


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--in", dest="inp", required=True)
    ap.add_argument("--out", dest="out", required=True)
    ap.add_argument("--cfg", dest="cfg", default="services/rl/prefs/config_prefs.yaml")
    args = ap.parse_args()

    import yaml

    with open(args.cfg, "r", encoding="utf-8") as f:
        cfg = yaml.safe_load(f)
    pii_pats = cfg.get("labeling", {}).get("pii_patterns", [])

    total = 0
    kept = 0
    with open(args.inp, "r", encoding="utf-8") as fin, open(
        args.out, "w", encoding="utf-8"
    ) as fout:
        for line in fin:
            total += 1
            ex = json.loads(line)
            a = ex.get("A", "")
            b = ex.get("B", "")
            if not a or not b or a.strip() == b.strip():
                continue
            text = a + " " + b
            if is_pii(text, pii_pats):
                continue
            fout.write(json.dumps(ex, ensure_ascii=False) + "\n")
            kept += 1
    print(f"[filters] total={total} kept={kept} → {args.out}")


if __name__ == "__main__":
    main()
