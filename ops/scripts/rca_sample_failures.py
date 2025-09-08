#!/usr/bin/env python3
"""
T8 RCA Failure Sampling - PII-säker analys av prod-fails

Läser prod-logs och samplar failure-cases för root cause analysis.
Maskerar PII men bevarar strukturell information för debugging.
"""

import argparse
import hashlib
import json
import re
import time
from pathlib import Path
from typing import Any, Dict, List


def mask_pii(text: str) -> str:
    """
    Enkel PII-masking för RCA-analys.
    Ersätter emails, telefon, personnummer med hash-placeholders.
    """
    if not text:
        return text

    # Email pattern
    text = re.sub(
        r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b",
        lambda m: f"EMAIL_{hashlib.md5(m.group().encode()).hexdigest()[:8]}",
        text,
    )

    # Phone pattern (swedish)
    text = re.sub(
        r"\b(?:\+46|0)\s?(?:\d{1,3}\s?){2,4}\d{1,3}\b",
        lambda m: f"PHONE_{hashlib.md5(m.group().encode()).hexdigest()[:8]}",
        text,
    )

    # PersonNummer pattern
    text = re.sub(
        r"\b\d{6}[-]?\d{4}\b",
        lambda m: f"PNR_{hashlib.md5(m.group().encode()).hexdigest()[:8]}",
        text,
    )

    return text


def extract_failure_features(record: Dict[str, Any]) -> Dict[str, Any]:
    """
    Extraherar strukturell info från failure-records för RCA.
    """
    features = {}

    # Timing
    features["ts"] = record.get("ts", int(time.time()))
    features["latency_ms"] = record.get("latency_ms", 0)

    # Routes och modeller
    features["route"] = record.get("route", "unknown")
    features["model"] = record.get("model", "unknown")

    # Response strukturer
    resp_raw = record.get("response_raw", "")
    resp_final = record.get("response_final", "")

    features["response_length"] = len(resp_raw)
    features["edit_distance"] = abs(len(resp_final) - len(resp_raw))

    # Verifier errors
    verifier_err = record.get("verifier_errors", [])
    features["verifier_error_count"] = len(verifier_err)
    features["verifier_error_types"] = list(
        set([err.get("type", "unknown") for err in verifier_err])
    )

    # Intent categories
    features["intent"] = record.get("intent", "unknown")

    # Formatted outputs (PII-maskade)
    features["response_masked"] = mask_pii(resp_raw)[:500]  # första 500 chars
    features["verifier_summary"] = mask_pii(str(verifier_err))[:200]

    return features


def sample_failures(
    log_path: str, sample_size: int = 100, lookback_hours: int = 24
) -> List[Dict[str, Any]]:
    """
    Samplar failure-cases från prod logs för RCA.
    """
    if not Path(log_path).exists():
        return []

    cutoff_ts = time.time() - lookback_hours * 3600
    failures = []

    with open(log_path, "r", encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            try:
                record = json.loads(line)

                # Filter på failures
                ts = record.get("ts", 0)
                if ts < cutoff_ts:
                    continue

                # Failure criteria
                is_failure = (
                    not record.get("verifier_ok", True)
                    or record.get("policy_breach", False)
                    or record.get("latency_ms", 0) > 5000
                )

                if is_failure:
                    features = extract_failure_features(record)
                    failures.append(features)

            except Exception:
                continue

    # Sampla för att hålla nere storleken
    if len(failures) > sample_size:
        # Stratified sampling över intent+route
        strata = {}
        for f in failures:
            key = f"{f['intent']}_{f['route']}"
            strata.setdefault(key, []).append(f)

        sampled = []
        per_stratum = max(1, sample_size // len(strata))

        for stratum_failures in strata.values():
            sampled.extend(stratum_failures[:per_stratum])

        failures = sampled[:sample_size]

    return failures


def generate_rca_report(failures: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Genererar RCA-rapport med failure-mönster.
    """
    if not failures:
        return {"error": "No failures found", "count": 0}

    # Aggregera mönster
    patterns = {
        "total_failures": len(failures),
        "routes": {},
        "intents": {},
        "verifier_errors": {},
        "latency_issues": 0,
        "avg_latency": 0,
    }

    total_latency = 0
    for f in failures:
        # Route distribution
        route = f.get("route", "unknown")
        patterns["routes"][route] = patterns["routes"].get(route, 0) + 1

        # Intent distribution
        intent = f.get("intent", "unknown")
        patterns["intents"][intent] = patterns["intents"].get(intent, 0) + 1

        # Verifier error types
        for err_type in f.get("verifier_error_types", []):
            patterns["verifier_errors"][err_type] = (
                patterns["verifier_errors"].get(err_type, 0) + 1
            )

        # Latency
        lat = f.get("latency_ms", 0)
        total_latency += lat
        if lat > 3000:
            patterns["latency_issues"] += 1

    patterns["avg_latency"] = round(total_latency / len(failures), 2) if failures else 0

    # Top failure examples (maskade)
    top_examples = []
    for i, f in enumerate(failures[:5]):
        example = {
            "case_id": f"FAIL_{i+1}",
            "route": f.get("route"),
            "intent": f.get("intent"),
            "latency_ms": f.get("latency_ms"),
            "verifier_errors": f.get("verifier_error_count", 0),
            "response_snippet": f.get("response_masked", "")[:200],
        }
        top_examples.append(example)

    return {
        "timestamp": int(time.time()),
        "analysis_window_hours": 24,
        "patterns": patterns,
        "top_examples": top_examples,
        "recommendations": generate_recommendations(patterns),
    }


def generate_recommendations(patterns: Dict[str, Any]) -> List[str]:
    """
    Auto-generera rekommendationer baserat på failure-mönster.
    """
    recs = []

    # Route-baserade rekommendationer
    routes = patterns.get("routes", {})
    if routes.get("adapter", 0) > routes.get("baseline", 0):
        recs.append(
            "HIGH_ADAPTER_FAILURES: Consider lowering PREFS_CANARY_SHARE or disabling T8_ONLINE_ADAPTATION"
        )

    # Verifier-baserade rekommendationer
    verifier_errs = patterns.get("verifier_errors", {})
    if verifier_errs.get("format_error", 0) > 10:
        recs.append(
            "FORMAT_ISSUES: Enable FormatGuard pre-processing to auto-fix common formatting"
        )

    if verifier_errs.get("policy_violation", 0) > 5:
        recs.append("POLICY_VIOLATIONS: Review safety filters and content policies")

    # Latency-baserade rekommendationer
    if patterns.get("latency_issues", 0) > patterns.get("total_failures", 1) * 0.3:
        recs.append(
            "LATENCY_DEGRADATION: Check model serving infrastructure and timeout configs"
        )

    # Intent-baserade rekommendationer
    intents = patterns.get("intents", {})
    top_intent = max(intents.items(), key=lambda x: x[1])[0] if intents else None
    if top_intent and intents[top_intent] > patterns.get("total_failures", 1) * 0.4:
        recs.append(
            f"INTENT_CONCENTRATION: Most failures in '{top_intent}' - review specialized handling"
        )

    return recs


def main():
    ap = argparse.ArgumentParser(description="T8 RCA Failure Sampling")
    ap.add_argument(
        "--log_path",
        default="data/logs/prod_requests.jsonl",
        help="Path to production logs",
    )
    ap.add_argument(
        "--output",
        default="data/ops/rca_failures.json",
        help="Output path for RCA report",
    )
    ap.add_argument(
        "--sample_size", type=int, default=100, help="Max number of failures to sample"
    )
    ap.add_argument(
        "--lookback_hours", type=int, default=24, help="Hours to look back for failures"
    )

    args = ap.parse_args()

    print(f"[RCA] Sampling failures from {args.log_path}")
    print(f"[RCA] Lookback: {args.lookback_hours}h, Max samples: {args.sample_size}")

    failures = sample_failures(args.log_path, args.sample_size, args.lookback_hours)
    report = generate_rca_report(failures)

    # Skriv rapport
    Path(args.output).parent.mkdir(parents=True, exist_ok=True)
    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    print(f"[RCA] Found {len(failures)} failures")
    print(f"[RCA] Report written to {args.output}")

    # Print summary
    if report.get("patterns"):
        patterns = report["patterns"]
        print(f"[RCA] Route distribution: {patterns.get('routes', {})}")
        print(
            f"[RCA] Top verifier errors: {list(patterns.get('verifier_errors', {}).keys())[:3]}"
        )
        print(f"[RCA] Avg latency: {patterns.get('avg_latency', 0)}ms")

        recs = report.get("recommendations", [])
        if recs:
            print("[RCA] Top recommendations:")
            for rec in recs[:3]:
                print(f"  - {rec}")


if __name__ == "__main__":
    main()
