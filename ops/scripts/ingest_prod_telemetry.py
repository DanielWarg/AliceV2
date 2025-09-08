#!/usr/bin/env python3
"""
Läser prod-loggar (NDJSON/JSONL), aggregerar PII-säker telemetri enligt schema i ops/config/telemetry_sources.yaml,
och skriver fönstret till data/ops/telemetry_window.json.
- Sparar INTE rå text. Räknar endast längd, intents, verifier_ok, policy_breach, latency.
- Fallback-intent med regex om fält saknas.
- Stöd för flera källor; första existerande används.
- Valfri S3/GCS läsning om 'enabled: true' (kräver boto3/google-cloud-storage).
"""

import argparse
import datetime
import json
import re
import sys
import time
from pathlib import Path

try:
    import yaml
except Exception:
    print("[ingest] pyyaml saknas; installera pyyaml i CI/venv.", file=sys.stderr)
    sys.exit(2)

INTENTS = ["time", "weather", "email", "summary", "qa", "chitchat", "hard"]


def load_cfg():
    with open("ops/config/telemetry_sources.yaml", "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def _detect_intent(text, cfg):
    pats = cfg.get("intent_regex", {})
    for key, arr in pats.items():
        for pat in arr:
            if re.search(pat, text, re.I):
                return key
    return "qa"


def _utc_ts_of(event):
    # godtycklig tidskällemappning; försök tolka ISO fält, annars nu
    for k in ("ts", "timestamp", "time", "created_at"):
        if k in event:
            v = event[k]
            try:
                return int(
                    datetime.datetime.fromisoformat(
                        str(v).replace("Z", "+00:00")
                    ).timestamp()
                )
            except Exception:
                try:
                    return int(v) if str(v).isdigit() else int(float(v))
                except Exception:
                    pass
    return int(time.time())


def _len_chars(s):
    return len(s or "")


def _read_local(path):
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                yield json.loads(line)


def _read_s3(cfg):
    import boto3

    s3 = boto3.client("s3")
    obj = s3.get_object(Bucket=cfg["s3"]["bucket"], Key=cfg["s3"]["key"])
    for line in obj["Body"].iter_lines():
        if line:
            yield json.loads(line.decode("utf-8"))


def _read_gcs(cfg):
    from google.cloud import storage

    client = storage.Client()
    bucket = client.get_bucket(cfg["gcs"]["bucket"])
    blob = bucket.get_blob(cfg["gcs"]["blob"])
    data = blob.download_as_text()
    for line in data.splitlines():
        if line.strip():
            yield json.loads(line)


def _pick_source(cfg):
    for src in cfg.get("sources", []):
        if src["type"] == "file" and Path(src["path"]).exists():
            return ("file", src["path"])
    if cfg.get("s3", {}).get("enabled"):
        return ("s3", None)
    if cfg.get("gcs", {}).get("enabled"):
        return ("gcs", None)
    return (None, None)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="data/ops/telemetry_window.json")
    args = ap.parse_args()

    cfg = load_cfg()
    window_cfg = cfg.get("window", {})
    fields = cfg.get("fields", {})

    src_type, src_path = _pick_source(cfg)
    if src_type is None:
        print(
            "[ingest] Ingen källa hittades i ops/config/telemetry_sources.yaml",
            file=sys.stderr,
        )
        sys.exit(2)

    now = int(time.time())
    lookback = int(window_cfg.get("lookback_hours", 24)) * 3600
    min_ts = now - lookback
    max_events = int(window_cfg.get("max_events", 20000))
    min_events = int(window_cfg.get("min_events", 500))

    # Buffertar (PII-säkra)
    length_chars = []
    baseline_length_chars = []  # om loggen markerar baseline-route
    verifier_ok = []
    latency_ms = []
    intents_hist = {k: 0 for k in INTENTS}
    intents_hist_baseline = {k: 0 for k in INTENTS}

    seen = 0
    kept = 0

    # Reader
    if src_type == "file":
        reader = _read_local(src_path)
    elif src_type == "s3":
        reader = _read_s3(cfg)
    elif src_type == "gcs":
        reader = _read_gcs(cfg)
    else:
        print("[ingest] Okänd källa", file=sys.stderr)
        sys.exit(2)

    for ev in reader:
        seen += 1
        if seen > max_events:
            break

        ts = _utc_ts_of(ev)
        if ts < min_ts:
            continue

        # Fältnamn
        f_prompt = fields.get("prompt", "prompt")
        f_answer = fields.get("answer", "answer")
        f_intent = fields.get("intent", "intent")
        f_ver = fields.get("verifier_ok", "verifier_ok")
        f_policy = fields.get("policy_breach", "policy_breach")
        f_lat = fields.get("latency_ms", "latency_ms")
        f_route = fields.get("route", "route")

        prompt = ev.get(f_prompt, "") or ""
        answer = ev.get(f_answer, "") or ""

        # Vi lagrar aldrig prompt/answer – bara längd och intent
        L = _len_chars(answer or prompt)
        length_chars.append(L)

        # intent
        intent = ev.get(f_intent) or _detect_intent((prompt + " " + answer)[:800], cfg)
        if intent not in intents_hist:
            intent = "qa"
        intents_hist[intent] += 1

        # baseline route?
        route = (ev.get(f_route) or "").lower()
        if "baseline" in route:
            baseline_length_chars.append(L)
            intents_hist_baseline[intent] += 1

        # verifier & policy
        v_ok = bool(ev.get(f_ver, True))
        verifier_ok.append(v_ok)
        # policy_breach räknas inte i windowfilen direkt (watchdog tar från annan källa/rapport)

        # latency
        lat = ev.get(f_lat)
        if isinstance(lat, (int, float)) and lat >= 0:
            latency_ms.append(int(lat))

        kept += 1

    # Om det saknas baselinehistogram, approximera med aktuell fördelning (för PSI/KS baseline)
    def to_list(hist):
        return [hist[k] for k in INTENTS]

    if sum(intents_hist_baseline.values()) == 0:
        intents_hist_baseline = {k: max(1, v) for k, v in intents_hist.items()}

    out = {
        "length_chars": length_chars,
        "baseline_length_chars": baseline_length_chars or length_chars[:],  # fallback
        "intent_hist_baseline": to_list(intents_hist_baseline),
        "intent_hist_actual": to_list(intents_hist),
        "verifier_ok": verifier_ok,
        "latency_ms": latency_ms,
    }

    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)

    print(f"[ingest] seen={seen} kept={kept} → {args.out}")


if __name__ == "__main__":
    main()
