#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import argparse
import datetime
import json
import random
import re
import uuid
from pathlib import Path
from typing import Any, Dict, List

from transformers import AutoModelForSeq2SeqLM, AutoTokenizer, pipeline

random.seed(42)

EMAIL_RE = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
PNR_RE = re.compile(
    r"\b(?:19|20)?\d{2}(0[1-9]|1[0-2])(0[1-9]|[12]\d|3[01])[- ]?\d{4}\b"
)
PHONE_RE = re.compile(r"\b(?:\+46|0)\d[\d\s-]{6,}\d\b")
ID_RE = re.compile(
    r"\b(?:ticket|case|ärende|id|ref|reference)\s*[:#]?\s*[A-Za-z0-9-]{5,}\b", re.I
)

MASK_TOKENS = ["[MASK_EMAIL]", "[MASK_PNR]", "[MASK_PHONE]", "[MASK_ID]"]
PH_MAP = {m: f"<PH{i}>" for i, m in enumerate(MASK_TOKENS)}
REV_MAP = {v: k for k, v in PH_MAP.items()}


def now_iso():
    return datetime.datetime.utcnow().replace(microsecond=0).isoformat() + "Z"


def protect_masks(text: str) -> str:
    out = text
    for m, ph in PH_MAP.items():
        out = out.replace(m, ph)
    return out


def restore_masks(text: str) -> str:
    out = text
    for ph, m in REV_MAP.items():
        out = out.replace(ph, m)
    return out


def load_jsonl(path: Path) -> List[Dict[str, Any]]:
    rows = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            rows.append(json.loads(line))
    return rows


def save_jsonl(path: Path, rows: List[Dict[str, Any]]):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")


def sample_rows(rows: List[Dict[str, Any]], n: int) -> List[Dict[str, Any]]:
    if len(rows) <= n:
        return rows
    return random.sample(rows, n)


def build_translator():
    model_name = "Helsinki-NLP/opus-mt-en-sv"
    tok = AutoTokenizer.from_pretrained(model_name)
    mdl = AutoModelForSeq2SeqLM.from_pretrained(model_name)
    return pipeline(
        "translation", model=mdl, tokenizer=tok, src_lang="en", tgt_lang="sv"
    )


def tr(p, pipe):
    p = protect_masks(p)
    out = pipe(p, max_length=1024)[0]["translation_text"]
    return restore_masks(out)


def translate_pair(row, pipe):
    def t(s):
        return tr(s, pipe) if s else s

    return {
        "id": str(uuid.uuid4()),
        "domain": row.get("domain", "general_assistant"),
        "lang": "sv",
        "length_bucket": row.get("length_bucket", "M"),
        "prompt": t(row["prompt"]),
        "chosen": t(row["chosen"]),
        "rejected": t(row["rejected"]),
        "source": (row.get("source", "") + "+mt_en2sv")[:64],
        "judge": row.get("judge", "mt_transfer"),
        "pii_masked": bool(
            any(
                tok in (row["prompt"] + row["chosen"] + row["rejected"])
                for tok in MASK_TOKENS
            )
        ),
        "quality_score": 3,
        "created_at": now_iso(),
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--hh", required=True)
    ap.add_argument("--pku", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--n_hh", type=int, default=100)
    ap.add_argument("--n_pku", type=int, default=100)
    args = ap.parse_args()

    hh_rows = load_jsonl(Path(args.hh))
    pku_rows = load_jsonl(Path(args.pku))
    hh_s = sample_rows(hh_rows, args.n_hh)
    pku_s = sample_rows(pku_rows, args.n_pku)

    pipe = build_translator()

    out_rows = []
    for r in hh_s + pku_s:
        out_rows.append(translate_pair(r, pipe))

    save_jsonl(Path(args.out), out_rows)
    print("✅ EN→SV klart:", len(out_rows), "par skrev till", args.out)


if __name__ == "__main__":
    main()
