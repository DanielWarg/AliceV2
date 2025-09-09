#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import argparse
import datetime
import json
import random
import re
import uuid
from pathlib import Path
from typing import Any, Dict, Iterable, List, Tuple, Union

from datasets import Dataset, DatasetDict, load_from_disk

random.seed(42)

EMAIL_RE = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
PNR_RE = re.compile(
    r"\b(?:19|20)?\d{2}(0[1-9]|1[0-2])(0[1-9]|[12]\d|3[01])[- ]?\d{4}\b"
)
PHONE_RE = re.compile(r"\b(?:\+46|0)\d[\d\s-]{6,}\d\b")
ID_RE = re.compile(
    r"\b(?:ticket|case|ärende|id|ref|reference)\s*[:#]?\s*[A-Za-z0-9-]{5,}\b", re.I
)


def pii_mask(text: str) -> Tuple[str, bool]:
    before = text
    text = EMAIL_RE.sub("[MASK_EMAIL]", text)
    text = PNR_RE.sub("[MASK_PNR]", text)
    text = PHONE_RE.sub("[MASK_PHONE]", text)
    text = ID_RE.sub("[MASK_ID]", text)
    return text, (text != before)


def length_bucket(s: str) -> str:
    n = len(s.split())
    if n <= 120:
        return "S"
    if n <= 512:
        return "M"
    return "L"


def now_iso() -> str:
    return datetime.datetime.utcnow().replace(microsecond=0).isoformat() + "Z"


def make_id() -> str:
    return str(uuid.uuid4())


def norm(s: Union[str, None]) -> str:
    return re.sub(r"\s+", " ", (s or "")).strip()


def iter_examples(ds: Union[Dataset, DatasetDict]):
    if isinstance(ds, DatasetDict):
        for split in ds.values():
            for ex in split:
                yield ex
    else:
        for ex in ds:
            yield ex


def map_pku_to_pairs(ds: Union[Dataset, DatasetDict]) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    for ex in iter_examples(ds):
        prompt = ex.get("prompt") or ex.get("instruction") or ex.get("query") or ""
        r0 = ex.get("response_0") or ex.get("answer_0") or ex.get("completion_0") or ""
        r1 = ex.get("response_1") or ex.get("answer_1") or ex.get("completion_1") or ""
        bid = ex.get("better_response_id")
        if bid is None:
            bid = ex.get("preferred")
        if isinstance(bid, bool):  # vissa varianter
            bid = 0 if bid else 1
        if prompt and r0 and r1 and bid in (0, 1):
            chosen_resp = r0 if bid == 0 else r1
            rejected_resp = r1 if bid == 0 else r0
            p_masked, pm = pii_mask(norm(prompt))
            c_masked, cm = pii_mask(norm(chosen_resp))
            r_masked, rm = pii_mask(norm(rejected_resp))
            rows.append(
                {
                    "id": make_id(),
                    "domain": "policy_safety",
                    "lang": "en",
                    "length_bucket": length_bucket(p_masked + " " + c_masked),
                    "prompt": p_masked,
                    "chosen": c_masked,
                    "rejected": r_masked,
                    "source": "pku_saferlhf",
                    "judge": "pku_label",
                    "pii_masked": bool(pm or cm or rm),
                    "quality_score": 4,
                    "created_at": now_iso(),
                }
            )
    return rows


def dedup(rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    seen, out = set(), []
    for r in rows:
        k = (r["prompt"][:400], r["chosen"][:400])
        if k in seen:
            continue
        seen.add(k)
        out.append(r)
    return out


def write_jsonl(path: Path, rows: Iterable[Dict[str, Any]]):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")


def split_train_val_test(rows: List[Dict[str, Any]], ratios=(0.8, 0.1, 0.1)):
    random.shuffle(rows)
    n = len(rows)
    n_train = int(n * ratios[0])
    n_val = int(n * ratios[1])
    train = rows[:n_train]
    val = rows[n_train : n_train + n_val]
    test = rows[n_train + n_val :]
    return train, val, test


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--in",
        dest="in_dir",
        required=True,
        help="Path till data/dpo_v1/raw/pku (load_from_disk)",
    )
    ap.add_argument(
        "--out", dest="out_dir", required=True, help="Bas-katalog: data/dpo_v1"
    )
    ap.add_argument(
        "--target",
        type=int,
        default=1500,
        help="Max antal par att skriva (sample efter dedup)",
    )
    args = ap.parse_args()

    in_dir = Path(args.in_dir).resolve()
    out_dir = Path(args.out_dir).resolve()
    assert in_dir.exists(), f"Finns ej: {in_dir}"

    ds = load_from_disk(str(in_dir))
    rows = map_pku_to_pairs(ds)
    rows = dedup(rows)

    if args.target and len(rows) > args.target:
        rows = rows[: args.target]

    processed_path = out_dir / "processed" / "dpo_pairs.pku.v1.jsonl"
    write_jsonl(processed_path, rows)

    train, val, test = split_train_val_test(rows, ratios=(0.8, 0.1, 0.1))
    write_jsonl(out_dir / "splits" / "pku" / "train.jsonl", train)
    write_jsonl(out_dir / "splits" / "pku" / "val.jsonl", val)
    write_jsonl(out_dir / "splits" / "pku" / "test.jsonl", test)

    # Liten sammanfattning
    def bucketing(stats_rows):
        from collections import Counter

        b = Counter(r["length_bucket"] for r in stats_rows)
        return dict(b)

    print("✅ PKU → DPO klart")
    print("Totalt:", len(rows))
    print("Buckets:", bucketing(rows))
    print("Filer:")
    print(" ", processed_path)
    print(" ", out_dir / "splits" / "pku" / "train.jsonl")
    print(" ", out_dir / "splits" / "pku" / "val.jsonl")
    print(" ", out_dir / "splits" / "pku" / "test.jsonl")


if __name__ == "__main__":
    main()
