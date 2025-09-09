#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import argparse
import datetime
import json
import random
import re
import uuid
from pathlib import Path
from typing import Any, Dict, List, Tuple, Union

from datasets import Dataset, DatasetDict, load_from_disk

random.seed(42)

# --- PII-maskning (svenska m.m.) ---

EMAIL_RE = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
PNR_RE = re.compile(
    r"\b(?:19|20)?\d{2}(0[1-9]|1[0-2])(0[1-9]|[12]\d|3[01])[- ]?\d{4}\b"
)
PHONE_RE = re.compile(r"\b(?:\+46|0)\d[\d\s-]{6,}\d\b")
ID_RE = re.compile(
    r"\b(?:ticket|case|ärende|id|ref|reference)\s*[:#]?\s*[A-Za-z0-9-]{5,}\b", re.I
)


def pii_mask(text: str) -> Tuple[str, bool]:
    before = text or ""
    text = EMAIL_RE.sub("[MASK_EMAIL]", before)
    text = PNR_RE.sub("[MASK_PNR]", text)
    text = PHONE_RE.sub("[MASK_PHONE]", text)
    text = ID_RE.sub("[MASK_ID]", text)
    return text, (text != before)


# --- Hjälpfunktioner ---

PAIR_RE = re.compile(
    r"(?:^|\n)(?:Human:|H:)\s*(.*?)(?:\n+)(?:Assistant:|A:)\s*(.*?)(?=\n(?:Human:|H:)|\Z)",
    re.S,
)


def extract_last_pair(dialog: str) -> Tuple[str, str]:
    if not dialog:
        return "", ""
    pairs = PAIR_RE.findall(dialog)
    if not pairs:
        # Fallback: försök enkel split
        mH = re.search(r"(?:Human:|H:)\s*", dialog)
        mA = re.search(r"(?:Assistant:|A:)\s*", dialog)
        if mH and mA and mA.start() > mH.start():
            return dialog[mH.end() : mA.start()].strip(), dialog[mA.end() :].strip()
        return "", ""
    prompt, resp = pairs[-1]
    return re.sub(r"\s+", " ", prompt).strip(), re.sub(r"\s+", " ", resp).strip()


def length_bucket(text: str) -> str:
    n = len((text or "").split())
    if n <= 120:
        return "S"
    if n <= 512:
        return "M"
    return "L"


def now_iso() -> str:
    return datetime.datetime.utcnow().replace(microsecond=0).isoformat() + "Z"


def make_id() -> str:
    return str(uuid.uuid4())


def dedup(rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    seen, out = set(), []
    for r in rows:
        k = (r["prompt"][:400], r["chosen"][:400])
        if k in seen:
            continue
        seen.add(k)
        out.append(r)
    return out


def iter_examples(ds: Union[Dataset, DatasetDict]):
    if isinstance(ds, DatasetDict):
        for split in ds.values():
            for ex in split:
                yield ex
    else:
        for ex in ds:
            yield ex


# --- Mappning HH-RLHF → {prompt, chosen, rejected} ---


def map_hh(ds: Union[Dataset, DatasetDict]) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    for ex in iter_examples(ds):
        chosen_raw = ex.get("chosen") or ""
        rejected_raw = ex.get("rejected") or ""
        # Prompten är densamma för chosen/rejected; extrahera ur "chosen"
        prompt, chosen_resp = extract_last_pair(chosen_raw)
        _, rejected_resp = extract_last_pair(rejected_raw)
        if not prompt or not chosen_resp or not rejected_resp:
            continue
        # Filtrera orimliga outliers
        if len(chosen_resp) < 2 or len(rejected_resp) < 2:
            continue
        # PII-maskning
        p_masked, pm = pii_mask(prompt)
        c_masked, cm = pii_mask(chosen_resp)
        r_masked, rm = pii_mask(rejected_resp)
        # Grov domän-etikett (helpful/harmless)
        src = ex.get("source") or ""
        domain = "policy_safety" if "harmless" in src.lower() else "general_assistant"
        rows.append(
            {
                "id": make_id(),
                "domain": domain,
                "lang": "en",
                "length_bucket": length_bucket(p_masked + " " + c_masked),
                "prompt": p_masked,
                "chosen": c_masked,
                "rejected": r_masked,
                "source": "hh_rlhf",
                "judge": "anthropic_hh",
                "pii_masked": bool(pm or cm or rm),
                "quality_score": 4,
                "created_at": now_iso(),
            }
        )
    return rows


def write_jsonl(path: Path, rows: List[Dict[str, Any]]):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")


def split_rows(rows: List[Dict[str, Any]], ratios=(0.8, 0.1, 0.1)):
    random.shuffle(rows)
    n = len(rows)
    n_tr = int(n * ratios[0])
    n_val = int(n * ratios[1])
    return rows[:n_tr], rows[n_tr : n_tr + n_val], rows[n_tr + n_val :]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--in",
        dest="in_dir",
        required=True,
        help="Path till data/dpo_v1/raw/hh_rlhf (load_from_disk)",
    )
    ap.add_argument(
        "--out", dest="out_dir", required=True, help="Bas-katalog: data/dpo_v1"
    )
    ap.add_argument(
        "--target",
        type=int,
        default=1000,
        help="Max antal par att skriva (efter dedup)",
    )
    args = ap.parse_args()

    in_dir = Path(args.in_dir).resolve()
    out_dir = Path(args.out_dir).resolve()
    assert in_dir.exists(), f"Saknas: {in_dir}"

    ds = load_from_disk(str(in_dir))
    rows = map_hh(ds)
    rows = dedup(rows)

    if args.target and len(rows) > args.target:
        rows = rows[: args.target]

    processed = out_dir / "processed" / "dpo_pairs.hh.v1.jsonl"
    write_jsonl(processed, rows)

    tr, va, te = split_rows(rows)
    write_jsonl(out_dir / "splits" / "hh" / "train.jsonl", tr)
    write_jsonl(out_dir / "splits" / "hh" / "val.jsonl", va)
    write_jsonl(out_dir / "splits" / "hh" / "test.jsonl", te)

    from collections import Counter

    print("✅ HH → DPO klart")
    print("Totalt:", len(rows))
    print("Buckets:", dict(Counter(r["length_bucket"] for r in rows)))
    print("Filer:")
    print(" ", processed)
    print(" ", out_dir / "splits" / "hh" / "train.jsonl")
    print(" ", out_dir / "splits" / "hh" / "val.jsonl")
    print(" ", out_dir / "splits" / "hh" / "test.jsonl")


if __name__ == "__main__":
    main()
