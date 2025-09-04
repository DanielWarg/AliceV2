import json
import os
import pathlib
from datetime import datetime, timedelta, timezone

LOG_DIR = pathlib.Path(os.getenv("LOG_DIR", "/data/telemetry"))
OUT_DIR = pathlib.Path(os.getenv("DATASETS_DIR", "/data/datasets"))
OUT_DIR.mkdir(parents=True, exist_ok=True)


def iso_now():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def day_dir(day: datetime):
    return LOG_DIR / day.strftime("%Y-%m-%d")


def iter_jsonl(path: pathlib.Path):
    if not path.exists():
        return
    with path.open() as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                yield json.loads(line)
            except Exception:
                continue


def pii_ok(ev: dict) -> bool:
    scopes = ev.get("consent_scopes") or []
    return bool(ev.get("pii_masked", True)) and (
        "train:anon" in scopes or "basic_logging" in scopes
    )


def slo_ok(ev: dict) -> bool:
    q = (ev.get("quality") or {}).get("automatic") or {}
    return (
        bool(q.get("slo_ok", True))
        and bool(q.get("tool_success", True))
        and (q.get("error_class") in (None, ""))
    )


def implicit_positive(ev: dict) -> bool:
    imp = (ev.get("quality") or {}).get("implicit") or {}
    return (
        bool(imp.get("user_continues_flow"))
        or (imp.get("no_followup_within_s") or 0) >= 30
    )


def curate(day: datetime):
    src = day_dir(day)
    # read both subdir file and flat daily file
    events = list(iter_jsonl(src / "events.jsonl")) + list(
        iter_jsonl(LOG_DIR / f"events_{day.strftime('%Y-%m-%d')}.jsonl")
    )

    # BRONZE: rå (maskad) chat-turns med output_text
    bronze = [e for e in events if e.get("output_text") and pii_ok(e)]
    # SILVER: bronze + SLO OK + tool success
    silver = [e for e in bronze if slo_ok(e)]
    # GOLD: silver + implicit/explicit positiv feedback
    gold = [
        e
        for e in silver
        if implicit_positive(e)
        or ((e.get("quality") or {}).get("explicit") or {}).get("thumbs_up")
    ]

    # Exports: RAG-chunks + finetune-instruct (endast consent)
    exports_rag = []
    exports_ft = []
    for e in gold:
        if "rag:index" in (e.get("consent_scopes") or []):
            txt = (e.get("output_text") or "").strip()
            if txt:
                exports_rag.append(
                    {
                        "id": f"{e.get('trace_id','')[:8]}#{e.get('session_id','')[:8]}",
                        "text": txt,
                        "source": "chat",
                        "lang": e.get("lang", "sv"),
                        "ts": e.get("ts") or iso_now(),
                        "consent": "rag:index",
                    }
                )
        inp = (e.get("input_text") or "").strip()
        out = (e.get("output_text") or "").strip()
        if inp and out and len(out) >= 12:
            exports_ft.append(
                {
                    "prompt": f"[SV] {inp}",
                    "completion": f"[SV] {out}",
                    "route": e.get("route"),
                    "ok": True,
                }
            )

    stamp = day.strftime("%Y%m%d")
    (OUT_DIR / "bronze").mkdir(parents=True, exist_ok=True)
    (OUT_DIR / "silver").mkdir(parents=True, exist_ok=True)
    (OUT_DIR / "gold").mkdir(parents=True, exist_ok=True)
    (OUT_DIR / "exports").mkdir(parents=True, exist_ok=True)

    def dump(path: pathlib.Path, rows):
        with open(path, "w", encoding="utf-8") as f:
            for r in rows:
                f.write(json.dumps(r, ensure_ascii=False) + "\n")

    dump(OUT_DIR / "bronze" / f"turns-{stamp}.jsonl", bronze)
    dump(OUT_DIR / "silver" / f"turns-{stamp}.jsonl", silver)
    dump(OUT_DIR / "gold" / f"turns-{stamp}.jsonl", gold)
    dump(OUT_DIR / "exports" / f"rag-chunks-{stamp}.jsonl", exports_rag)
    dump(OUT_DIR / "exports" / f"finetune-instruct-{stamp}.jsonl", exports_ft)

    summary = {
        "v": "1",
        "ts": iso_now(),
        "day": stamp,
        "counts": {
            "events": len(events),
            "bronze": len(bronze),
            "silver": len(silver),
            "gold": len(gold),
            "rag_chunks": len(exports_rag),
            "finetune_pairs": len(exports_ft),
        },
    }
    print(json.dumps(summary, ensure_ascii=False))


if __name__ == "__main__":
    d = datetime.now(timezone.utc) - timedelta(days=1)
    curate(d)
