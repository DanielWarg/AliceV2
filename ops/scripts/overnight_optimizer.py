#!/usr/bin/env python3
"""
Overnight Auto-Stabilizer (8h):
- Var 10:e minut: ingest prod telemetry -> drift snapshot -> append history
- Varje timme: RCA (maskad), extrahera topporsaker och föreslå fixar
- Off-policy experiments: simulera FormatGuard max_chars (±10%) och räkna hur många fail som skulle trimmas bort
- Intent-förslag: extrahera vanliga svenska nyckelord i "unknown"/felmappade intents → bygg förslag till intent_regex
- Slutligen: skriv en morgonrapport (MD + JSON) i ops/suggestions/

Design:
- Ändrar ALDRIG prod-konfig. Alla förslag hamnar i ops/suggestions/*
- PII-säkert: använder redan maskad RCA och aggregerad telemetri
"""

import collections
import json
import re
import time
from datetime import datetime, UTC
from pathlib import Path

ROOT = Path(".")
RCA_DIR = ROOT / "data/ops/rca"
SUG_DIR = ROOT / "ops/suggestions"
SUG_DIR.mkdir(parents=True, exist_ok=True)


def _sh(cmd):
    import subprocess

    return subprocess.run(cmd, shell=True, capture_output=True, text=True)


def _read_json(p, default=None):
    try:
        return json.loads(Path(p).read_text(encoding="utf-8"))
    except Exception:
        return default


def _list_fail_samples(n_max=1000):
    p = RCA_DIR / "fail_samples.jsonl"
    out = []
    if not p.exists():
        return out
    with p.open("r", encoding="utf-8") as f:
        for i, line in enumerate(f):
            if not line.strip():
                continue
            try:
                ex = json.loads(line)
                out.append(ex)
                if len(out) >= n_max:
                    break
            except:
                pass
    return out


def _simulate_formatguard(samples, max_chars):
    # Räkna hur många som skulle gått under max_chars (och ev. sluppit max_len-exceeded)
    trimmed = 0
    for s in samples:
        L = s.get("len_chars", 0)
        if L > max_chars:
            trimmed += 1
    return {"would_trim": trimmed, "tested_max_chars": max_chars, "n": len(samples)}


def _propose_max_chars(samples, current=1200):
    # prova ±10% runt current och välj som maximerar "would_trim" (som proxy för att undvika max_len-fails)
    candidates = sorted({int(current * 0.9), current, int(current * 1.1)})
    sims = [_simulate_formatguard(samples, c) for c in candidates]
    # välj den som trimmar mest, men prioritera att inte höja om onödigt
    sims_sorted = sorted(
        sims, key=lambda x: (x["would_trim"], -x["tested_max_chars"]), reverse=True
    )
    best = (
        sims_sorted[0]
        if sims_sorted
        else {"tested_max_chars": current, "would_trim": 0}
    )
    return {
        "proposal_max_chars": best["tested_max_chars"],
        "baseline_max_chars": current,
        "estimated_trimmed": best["would_trim"],
    }


_SW_TOKEN = re.compile(r"[A-Za-zÅÄÖåäö]{3,}", re.UNICODE)
_STOP = set(
    "och det att som för men så på eller samt vara inte med den det är vi ni jag du han hon de dom här där".split()
)


def _extract_tokens(text):
    toks = _SW_TOKEN.findall(text.lower())
    return [t for t in toks if t not in _STOP and len(t) >= 3][:12]


def _propose_intent_regex(samples, top_k=12):
    # leta ord i maskade snippets för rader som har "intent":"unknown" eller ofta felmappas (heuristik: många claims)
    buckets = collections.Counter()
    for s in samples:
        intent = (s.get("intent") or "unknown").lower()
        if intent in ("unknown",):  # kan byggas ut
            snip = s.get("snippet_redacted", "")
            for tok in _extract_tokens(snip):
                buckets[tok] += 1
    common = [w for w, _ in buckets.most_common(top_k)]
    # Heuristiska domäner
    finance = [w for w in common if w.startswith(("pris", "inflation", "ränta", "sek"))]
    code = [
        w for w in common if w in ("kod", "python", "json", "stack", "fel", "trace")
    ]
    travel = [w for w in common if w in ("flyg", "tåg", "hotell", "resa", "resplan")]

    # bygg regex (enkla ord-kapslar)
    def rx(words):
        if not words:
            return None
        return [rf"\\b{re.escape(w)}\\b" for w in words][:8]

    proposals = {
        "finance": rx(finance) or [],
        "code": rx(code) or [],
        "travel": rx(travel) or [],
    }
    return proposals, common


def _summarize_rca_hist():
    h = _read_json(RCA_DIR / "reasons_hist.json", {"hist": {}, "top2": []})
    hist = h.get("hist", {})
    ordered = sorted(hist.items(), key=lambda x: x[1], reverse=True)
    top3 = ordered[:3]
    return {"hist": hist, "top3": top3}


def _read_drift_snapshot():
    r = _sh("python services/rl/drift/drift_watch.py")
    try:
        return json.loads(r.stdout.strip())
    except Exception:
        return {"ok": False, "snapshot": {}, "rolling": {}}


def run():
    start = time.time()
    end = start + 8 * 3600
    it = 0
    print(f"[overnight] STARTING 8-hour optimization @ {datetime.now(UTC).isoformat()}")
    print(f"[overnight] Will run until: {datetime.fromtimestamp(end, UTC).isoformat()}")
    
    # loopa 8h
    while time.time() < end:
        it += 1
        try:
            print(f"[overnight] === ITERATION {it} @ {datetime.now(UTC).isoformat()} ===")
            
            # Ingest telemetry
            result = _sh("python ops/scripts/ingest_prod_telemetry.py")
            if result.returncode != 0:
                print(f"[overnight] WARN: telemetry failed: {result.stderr}")
            else:
                print(f"[overnight] Telemetry OK: {result.stdout.strip()}")
            
            # Drift snapshot
            snap = _read_drift_snapshot()
            print(f"[overnight] Drift OK={snap.get('ok')}, VF={snap.get('snapshot',{}).get('verifier_fail')}")
            
            # Hourly RCA
            if it % 6 == 0:  # varje timme
                print(f"[overnight] Running hourly RCA sampling...")
                rca_result = _sh("python ops/scripts/rca_sample_failures.py --sample_size 100")
                print(f"[overnight] RCA result: {rca_result.stdout.strip()}")
            
            # History rollup
            rollup_result = _sh("python ops/scripts/drift_history_rollup.py")
            print(f"[overnight] Rollup OK")
            
            remaining_hours = (end - time.time()) / 3600
            print(f"[overnight] Iteration {it} complete, {remaining_hours:.1f}h remaining")
            print(f"[overnight] Sleeping 10min...")
            
        except Exception as e:
            print(f"[overnight] ERROR in iteration {it}: {e}")
            print(f"[overnight] Continuing despite error...")
            
        time.sleep(600)  # 10 minutes

    # efter 8h: producera förslag
    samples = _list_fail_samples(1000)
    maxchars_prop = _propose_max_chars(samples, current=1200)
    intent_prop, intent_common = _propose_intent_regex(samples, top_k=24)
    rca = _summarize_rca_hist()
    drift = _read_drift_snapshot()

    # skriv förslag
    (SUG_DIR / "intent_regex_suggestions.yaml").write_text(
        json.dumps(intent_prop, ensure_ascii=False, indent=2).replace('"', ""),
        encoding="utf-8",
    )
    (SUG_DIR / "formatguard_suggestion.json").write_text(
        json.dumps(maxchars_prop, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    # skriv morgonrapport
    report_md = SUG_DIR / "morning_report.md"
    report_md.write_text(
        f"""# Morning Report – Overnight Auto-Stabilizer
Genererad: {datetime.now(UTC).isoformat()}

## Drift (senaste snapshot)
- OK: {drift.get('ok')}
- PSI (snapshot): {drift.get('snapshot',{}).get('psi_intents')}
- KS  (snapshot): {drift.get('snapshot',{}).get('ks_length')}
- verifier_fail (snapshot): {drift.get('snapshot',{}).get('verifier_fail')}

## Topporsaker (RCA)
{chr(10).join([f"- {k}: {v}" for k,v in rca.get('top3',[])]) or "- (saknas)"}

## Förslag – FormatGuard
```json
{json.dumps(maxchars_prop, ensure_ascii=False, indent=2)}
```

*Rekommendation:* testa `proposal_max_chars` i staging och mät verifier\_fail.

## Förslag – Intent Regex (nya buckets)

```yaml
{(SUG_DIR/'intent_regex_suggestions.yaml').read_text(encoding='utf-8')}
```

## Vanliga tokens i okända intents

{", ".join(intent_common) or "(saknas)"}

## Åtgärdslista (checklista)

* [ ] Applicera FormatGuard `proposal_max_chars` i staging → smoke (30 min)
* [ ] Mappa intent-regex för finance/code/travel → se förslag ovan
* [ ] Kör halfday-loop; sikta på verifier_fail ≤ 1.0%
* [ ] Soak 72h → GO-check
  """,
        encoding="utf-8",
    )

    # JSON-sammanfattning
    (SUG_DIR / "morning_report.json").write_text(
        json.dumps(
            {
                "generated_utc": datetime.now(UTC).isoformat(),
                "drift_snapshot": drift.get("snapshot", {}),
                "rca_top3": rca.get("top3", []),
                "formatguard_suggestion": maxchars_prop,
                "intent_regex_suggestions": intent_prop,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    print(f"[overnight] wrote {SUG_DIR/'morning_report.md'} and suggestions.")


if __name__ == "__main__":
    run()
