# services/rl/pipelines/utils_io.py
from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any, Dict, Iterable, Iterator

EMAIL_RE = re.compile(r"([A-Za-z0-9._%+-]+)@([A-Za-z0-9.-]+\.[A-Za-z]{2,})")
PHONE_RE = re.compile(r"\+?\d[\d\s\-()]{6,}\d")


def iter_jsonl(path: Path) -> Iterator[Dict[str, Any]]:
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                yield json.loads(line)
            except json.JSONDecodeError:
                # Skippa korrupt rad – logg kan läggas senare
                continue


def write_jsonl(path: Path, rows: Iterable[Dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")


def mask_pii(text: str) -> str:
    if not text:
        return text
    text = EMAIL_RE.sub("[email]", text)
    text = PHONE_RE.sub("[phone]", text)
    return text


def canonical_key(text_masked: str, intent: str | None, tool: str | None) -> str:
    base = (text_masked or "").strip().lower()
    it = (intent or "").strip().lower()
    tl = (tool or "").strip().lower() if tool else ""
    return hashlib.sha256(f"{base}||{it}||{tl}".encode("utf-8")).hexdigest()
