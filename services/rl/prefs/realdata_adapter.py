#!/usr/bin/env python3
"""
T9 Real Data Adapter (PII-säker)
- Läser A/B/C-triples om de finns (maskade).
- Annars härleder pseudo-triples genom att matcha baseline vs adapter per prompt (eller convo_id),
  och syntetiserar en tredje kandidat C (t.ex. format-guardad/trim:ad variant).
- Sparar endast maskade snippets (inte råtext), plus längd. Räcker för vår heuristik.
"""

import argparse
import hashlib
import json
import re
import time
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

try:
    import yaml
except Exception:
    yaml = None

from services.rl.prefs.agents.pairwise import Candidate, Triple


def _load_yaml(path: str) -> Dict[str, Any]:
    if yaml is None:
        raise RuntimeError("pyyaml saknas (installera pyyaml).")
    return yaml.safe_load(open(path, "r", encoding="utf-8"))


def _utc_ts_of(ev: Dict[str, Any]) -> int:
    for k in ("ts", "timestamp", "time", "created_at"):
        if k in ev:
            v = ev[k]
            try:
                # ISO eller unix
                if isinstance(v, (int, float)) or (isinstance(v, str) and v.isdigit()):
                    return int(float(v))
                return int(
                    __import__("datetime")
                    .datetime.fromisoformat(str(v).replace("Z", "+00:00"))
                    .timestamp()
                )
            except Exception:
                pass
    return int(time.time())


def _redacter(patterns: List[str], max_chars: int):
    regs = [re.compile(p, re.I) for p in patterns]

    def redact(s: str) -> str:
        t = (s or "")[:max_chars]
        for r in regs:
            t = r.sub("[REDACTED]", t)
        t = re.sub(r"\d{4,}", "[NUM]", t)
        return t

    return redact


def _hash_prompt(p: str) -> str:
    return hashlib.sha256((p or "").encode("utf-8")).hexdigest()[:16]


def _read_ndjson(path: str) -> Iterable[Dict[str, Any]]:
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                yield json.loads(line)


def _pick_source(cfg) -> Optional[Tuple[str, str]]:
    for src in cfg.get("sources", []):
        if src["type"] == "file" and Path(src["path"]).exists():
            return ("file", src["path"])
    return None


def _make_c_variant(text: str) -> str:
    # "C" kandidat: strama formatet (trim + ev. balansera ```), PII-maskning sker separat
    t = (text or "")[:1200]
    # balansera code fences
    if t.count("```") % 2 != 0:
        t = t.rstrip() + "\n```"
    return t


def _candidate(id_: str, snippet: str, score: Optional[float] = None) -> Candidate:
    return Candidate(id=id_, text=snippet, score=score)


def from_triples_file(path: str, cfg: Dict[str, Any]) -> Iterable[Triple]:
    fp = cfg["fields"]
    red = _redacter(cfg["pii"]["redact"], cfg["pii"]["snippet_max_chars"])
    tprompt, tcands, twinner = (
        fp["triple_prompt"],
        fp["triple_candidates"],
        fp["triple_winner"],
    )
    for ev in _read_ndjson(path):
        prompt = red(ev.get(tprompt, "") or "")
        cands = []
        for c in ev.get(tcands, []):
            cid = c.get("id") or c.get("label") or "X"
            snippet = red(c.get("text", "") or "")
            cands.append(_candidate(cid, snippet))
        if len(cands) < 3:
            # fyll upp med dummy tomma så judge inte kraschar
            while len(cands) < 3:
                cands.append(_candidate(chr(ord("A") + len(cands)), ""))
        yield Triple(prompt=prompt, candidates=cands[:3], winner_id=ev.get(twinner))


def from_prod_responses(path: str, cfg: Dict[str, Any]) -> Iterable[Triple]:
    fp = cfg["fields"]
    red = _redacter(cfg["pii"]["redact"], cfg["pii"]["snippet_max_chars"])
    lookback = int(cfg.get("window", {}).get("lookback_hours", 48)) * 3600
    min_ts = int(time.time()) - lookback
    # gruppera baseline/adapter per prompt-hash eller convo_id
    buckets: Dict[str, Dict[str, str]] = {}
    for ev in _read_ndjson(path):
        ts = _utc_ts_of(ev)
        if ts < min_ts:
            continue
        ptxt = ev.get(fp["prompt"], "") or ""
        pid = ev.get(fp.get("convo_id", "conversation_id"), None) or _hash_prompt(ptxt)
        route = (ev.get(fp["route"], "") or "").lower()
        ans = ev.get(fp["answer"], "") or ""
        if pid not in buckets:
            buckets[pid] = {"prompt": red(ptxt)}
        if route in ("baseline", "control"):
            buckets[pid]["A"] = red(ans)
        elif route in ("adapter", "t7", "t8", "canary"):
            buckets[pid]["B"] = red(ans)

    # bygg pseudo-triples
    for pid, d in buckets.items():
        prompt = d.get("prompt", "")
        a = d.get("A")
        b = d.get("B")
        if not (a and b):
            continue
        c = _make_c_variant(b) if len(b) > len(a) else _make_c_variant(a)
        c = red(c)
        cands = [_candidate("A", a), _candidate("B", b), _candidate("C", c)]
        # winner_id okänd (kan sättas via verifier/AB senare)
        yield Triple(prompt=prompt, candidates=cands, winner_id=None)


def build_triples(cfg_path: str, out_path: str) -> int:
    cfg = _load_yaml(cfg_path)
    picked = _pick_source(cfg)
    if not picked:
        print("[t9-adapter] Ingen giltig källa hittades i config.")
        return 0
    kind, path = picked

    Path(out_path).parent.mkdir(parents=True, exist_ok=True)
    out = open(out_path, "w", encoding="utf-8")
    n = 0

    # 1) Föredra färdiga triples om filen är ab_triples.ndjson
    if Path(path).name == "ab_triples.ndjson":
        for t in from_triples_file(path, cfg):
            out.write(
                json.dumps(
                    {
                        "prompt": t.prompt,
                        "candidates": [
                            {"id": c.id, "text": c.text} for c in t.candidates
                        ],
                        "winner_id": t.winner_id,
                    },
                    ensure_ascii=False,
                )
                + "\n"
            )
            n += 1
    else:
        # 2) Annars härled pseudo-triples från prod_responses
        for t in from_prod_responses(path, cfg):
            out.write(
                json.dumps(
                    {
                        "prompt": t.prompt,
                        "candidates": [
                            {"id": c.id, "text": c.text} for c in t.candidates
                        ],
                        "winner_id": t.winner_id,
                    },
                    ensure_ascii=False,
                )
                + "\n"
            )
            n += 1

    out.close()
    print(f"[t9-adapter] wrote {n} triples -> {out_path}")
    return n


def load_triples_jsonl(path: str) -> List[Triple]:
    triples: List[Triple] = []
    if not Path(path).exists():
        return triples
    for line in open(path, "r", encoding="utf-8"):
        if not line.strip():
            continue
        ev = json.loads(line)
        cands = [
            Candidate(id=c["id"], text=c.get("text", ""))
            for c in ev.get("candidates", [])[:3]
        ]
        while len(cands) < 3:
            cands.append(Candidate(id=chr(ord("A") + len(cands)), text=""))
        triples.append(
            Triple(
                prompt=ev.get("prompt", ""),
                candidates=cands,
                winner_id=ev.get("winner_id"),
            )
        )
    return triples


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--cfg", default="ops/config/t9_realdata.yaml")
    ap.add_argument("--out", default=None)
    args = ap.parse_args()
    cfg = _load_yaml(args.cfg)
    outp = args.out or cfg["output"]["triples_path"]
    build_triples(args.cfg, outp)
