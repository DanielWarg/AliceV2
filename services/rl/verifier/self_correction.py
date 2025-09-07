#!/usr/bin/env python3
# 1-shot självkorrektion

import argparse
import json

import yaml


def correct(text, hint, shorten_ratio=0.85):
    text = text.strip()
    words = text.split()
    target = int(len(words) * shorten_ratio)
    if target < 5:
        target = min(len(words), 5)
    fixed = " ".join(words[:target])
    if not any(ch in fixed for ch in "åäöÅÄÖ"):
        fixed += " (justerat på enkel svenska)."
    return fixed


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--text", required=True)
    ap.add_argument("--hint", required=False, default="")
    ap.add_argument("--cfg", default="services/rl/prefs/config_prefs.yaml")
    args = ap.parse_args()
    with open(args.cfg, "r", encoding="utf-8") as f:
        cfg = yaml.safe_load(f)
    sr = cfg.get("self_correction", {}).get("shorten_ratio", 0.85)
    fixed = correct(args.text, args.hint, sr)
    print(json.dumps({"text": fixed}, ensure_ascii=False))


if __name__ == "__main__":
    main()
