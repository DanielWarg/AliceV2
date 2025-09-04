#!/usr/bin/env python3
"""
Test → Alice Smart Ingestion Module (v1)

Läser riktig testtrafik (eval-harness + e2e) och producerar lärbar, kuraterad träningssignal
för Alice – utan mocks. Matar observability, förbättrar NLU/planerare, och producerar
säkra, versionerade datapack.
"""

import argparse
import gzip
import hashlib
import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

import pandas as pd
import structlog

# Configure logging
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
        structlog.processors.JSONRenderer(),
    ],
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    wrapper_class=structlog.stdlib.BoundLogger,
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger()

# PII masking patterns
EMAIL_PATTERN = r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b"
PHONE_PATTERN = r"\b(?:\+46|0)[\s-]?[0-9]{1,3}[\s-]?[0-9]{3,4}[\s-]?[0-9]{3,4}\b"
SSN_PATTERN = r"\b\d{6}[-+]?\d{4}\b"


class LearnIngestion:
    """Main ingestion pipeline for Alice learning data."""

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.stats = {
            "rows_raw": 0,
            "rows_learnable": 0,
            "hard_intent": 0,
            "tool_fail": 0,
            "rag_miss": 0,
            "dropped_low_conf": 0,
            "dropped_low_margin": 0,
            "dropped_strict": 0,
            "dropped_redteam": 0,
        }

    def mask_pii(self, text: str, policy: str = "bronze") -> str:
        """Mask PII according to policy level."""
        if not text or policy == "gold":
            return text

        masked = text

        # Email masking
        if self.config.get("LEARN_MASK_EMAIL", True):
            masked = re.sub(EMAIL_PATTERN, "[EMAIL]", masked)

        # Phone masking
        if self.config.get("LEARN_MASK_PHONE", True):
            masked = re.sub(PHONE_PATTERN, "[PHONE]", masked)

        # SSN masking
        if self.config.get("LEARN_MASK_SSN", True):
            masked = re.sub(SSN_PATTERN, "[SSN]", masked)

        return masked

    def normalize_event(self, event: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Normalize a telemetry event to learning schema v1."""
        try:
            # Extract basic fields
            normalized = {
                "v": "1",
                "ts": event.get("ts", datetime.now(timezone.utc).isoformat() + "Z"),
                "trace_id": event.get("trace_id", ""),
                "session_id": event.get("session_id", ""),
                "route": event.get("route", "unknown"),
                "lang": event.get("lang", "sv"),
            }

            # User and response text (with PII masking)
            user_text = event.get("user_text", "")
            response_text = event.get("response_text", "")

            normalized["user_text"] = self.mask_pii(user_text) if user_text else None
            normalized["response_text"] = response_text if response_text else None

            # NLU data
            nlu_data = event.get("nlu", {})
            normalized["nlu"] = {
                "intent": nlu_data.get("intent", "unknown"),
                "conf": nlu_data.get("confidence", 0.0),
                "margin": nlu_data.get("margin", 0.0),
                "slots": nlu_data.get("slots", {}),
            }

            # Timings
            timings = event.get("timings", {})
            normalized["timings"] = {
                "ttft_ms": timings.get("ttft_ms", 0),
                "full_ms": timings.get("full_ms", 0),
                "p50_route_ms": timings.get("p50_route_ms", 0),
                "p95_route_ms": timings.get("p95_route_ms", 0),
            }

            # RAG data
            rag_data = event.get("rag", {})
            normalized["rag"] = {
                "top_k": rag_data.get("top_k", 0),
                "hits": rag_data.get("hits", 0),
            }

            # Tools
            tools = event.get("tools", [])
            normalized["tools"] = []
            for tool in tools:
                normalized["tools"].append(
                    {
                        "name": tool.get("name", "unknown"),
                        "ok": tool.get("ok", True),
                        "klass": tool.get("error_class"),
                        "lat_ms": tool.get("latency_ms", 0),
                    }
                )

            # Security
            security = event.get("security", {})
            normalized["security"] = {
                "mode": security.get("mode", "NORMAL"),
                "inj_score": security.get("injection_score", 0.0),
                "sanitised": security.get("sanitised", False),
                "system_prompt_sha256": security.get("system_prompt_sha256", ""),
            }

            # Resources
            resources = event.get("resources", {})
            normalized["resources"] = {
                "ram_peak_mb": resources.get("ram_peak_mb", {}),
                "energy_wh": resources.get("energy_wh", 0.0),
            }

            # Outcome
            outcome = event.get("outcome", {})
            normalized["outcome"] = {
                "ok": outcome.get("ok", True),
                "error": outcome.get("error"),
                "labels": outcome.get("labels", []),
                "redteam": outcome.get("redteam", False),
            }

            # Consent
            consent = event.get("consent", {})
            normalized["consent"] = {
                "scopes": consent.get("scopes", []),
                "pii_masked": consent.get("pii_masked", True),
            }

            return normalized

        except Exception as e:
            logger.error("Failed to normalize event", error=str(e), event=event)
            return None

    def is_learnable(self, row: Dict[str, Any]) -> bool:
        """Check if a normalized row meets learnability criteria."""
        # Must be successful
        if not row.get("outcome", {}).get("ok", True):
            return False

        # Must meet confidence threshold
        min_conf = float(self.config.get("LEARN_MIN_CONF", 0.60))
        if row.get("nlu", {}).get("conf", 0.0) < min_conf:
            self.stats["dropped_low_conf"] += 1
            return False

        # Must meet margin threshold
        min_margin = float(self.config.get("LEARN_MIN_MARGIN", 0.05))
        if row.get("nlu", {}).get("margin", 0.0) < min_margin:
            self.stats["dropped_low_margin"] += 1
            return False

        # Must not be in strict mode (if configured)
        if self.config.get("LEARN_DENY_STRICT", True):
            if row.get("security", {}).get("mode") in ["STRICT", "LOCKDOWN"]:
                self.stats["dropped_strict"] += 1
                return False

        # Must not be redteam
        if row.get("outcome", {}).get("redteam", False):
            self.stats["dropped_redteam"] += 1
            return False

        return True

    def add_learning_labels(self, row: Dict[str, Any]) -> Dict[str, Any]:
        """Add learning labels to identify hard cases."""
        labels = row.get("outcome", {}).get("labels", [])

        # Hard intent (low margin)
        if row.get("nlu", {}).get("margin", 1.0) < 0.08:
            labels.append("hard_intent")
            self.stats["hard_intent"] += 1

        # Tool failures
        tools = row.get("tools", [])
        if any(not tool.get("ok", True) for tool in tools):
            labels.append("tool_fail")
            self.stats["tool_fail"] += 1

        # RAG misses
        if row.get("rag", {}).get("hits", 0) == 0:
            labels.append("rag_miss")
            self.stats["rag_miss"] += 1

        # Update labels
        row["outcome"]["labels"] = labels
        return row

    def read_telemetry_files(self, input_dir: str) -> List[Dict[str, Any]]:
        """Read all telemetry events from JSONL files."""
        events = []
        input_path = Path(input_dir)

        if not input_path.exists():
            logger.warning("Input directory does not exist", path=input_dir)
            return events

        # Find all events.jsonl files
        for jsonl_file in input_path.rglob("events.jsonl"):
            logger.info("Reading telemetry file", file=str(jsonl_file))
            try:
                with open(jsonl_file, "r", encoding="utf-8") as f:
                    for line_num, line in enumerate(f, 1):
                        try:
                            event = json.loads(line.strip())
                            events.append(event)
                        except json.JSONDecodeError as e:
                            logger.warning(
                                "Invalid JSON in telemetry",
                                file=str(jsonl_file),
                                line=line_num,
                                error=str(e),
                            )
            except Exception as e:
                logger.error(
                    "Failed to read telemetry file", file=str(jsonl_file), error=str(e)
                )

        logger.info("Read telemetry events", count=len(events))
        return events

    def read_test_results(self, tests_file: str) -> List[Dict[str, Any]]:
        """Read test results from eval harness."""
        events = []
        tests_path = Path(tests_file)

        if not tests_path.exists():
            logger.warning("Tests file does not exist", path=tests_file)
            return events

        try:
            with open(tests_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            # Extract events from test results
            if isinstance(data, dict):
                # Single test result
                if "events" in data:
                    events.extend(data["events"])
                else:
                    events.append(data)
            elif isinstance(data, list):
                # Multiple test results
                for result in data:
                    if "events" in result:
                        events.extend(result["events"])
                    else:
                        events.append(result)

        except Exception as e:
            logger.error("Failed to read test results", file=tests_file, error=str(e))

        logger.info("Read test events", count=len(events))
        return events

    def write_parquet(self, rows: List[Dict[str, Any]], output_dir: str, date: str):
        """Write normalized data to parquet files."""
        if not rows:
            logger.warning("No rows to write to parquet")
            return

        output_path = Path(output_dir) / date
        output_path.mkdir(parents=True, exist_ok=True)

        # Convert to DataFrame
        df = pd.DataFrame(rows)

        # Write parquet
        parquet_file = output_path / f"learn_{date}.parquet"
        df.to_parquet(parquet_file, index=False)

        logger.info("Wrote parquet file", file=str(parquet_file), rows=len(rows))

    def write_snapshot(self, rows: List[Dict[str, Any]], output_dir: str, date: str):
        """Write daily snapshot as compressed JSONL."""
        if not rows:
            logger.warning("No rows to write to snapshot")
            return

        output_path = Path(output_dir) / date
        output_path.mkdir(parents=True, exist_ok=True)

        # Write compressed JSONL
        snapshot_file = output_path / "dataset.jsonl.gz"
        with gzip.open(snapshot_file, "wt", encoding="utf-8") as f:
            for row in rows:
                f.write(json.dumps(row, ensure_ascii=False) + "\n")

        # Calculate checksum
        with open(snapshot_file, "rb") as f:
            checksum = hashlib.sha256(f.read()).hexdigest()

        # Write checksum file
        checksum_file = output_path / "dataset.jsonl.gz.sha256"
        with open(checksum_file, "w") as f:
            f.write(checksum)

        logger.info(
            "Wrote snapshot", file=str(snapshot_file), rows=len(rows), checksum=checksum
        )

    def log_stats(self, log_file: str):
        """Log ingestion statistics."""
        if not self.stats["rows_raw"]:
            return

        learning_rate = self.stats["rows_learnable"] / self.stats["rows_raw"]

        stats_entry = {
            "v": "1",
            "ts": datetime.now(timezone.utc).isoformat() + "Z",
            "day": datetime.now().strftime("%Y-%m-%d"),
            "rows_raw": self.stats["rows_raw"],
            "rows_learnable": self.stats["rows_learnable"],
            "hard_intent": self.stats["hard_intent"],
            "tool_fail": self.stats["tool_fail"],
            "rag_miss": self.stats["rag_miss"],
            "learning_rate": learning_rate,
            "dropped_low_conf": self.stats["dropped_low_conf"],
            "dropped_low_margin": self.stats["dropped_low_margin"],
            "dropped_strict": self.stats["dropped_strict"],
            "dropped_redteam": self.stats["dropped_redteam"],
        }

        # Ensure log directory exists
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)

        # Append to log file
        with open(log_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(stats_entry, ensure_ascii=False) + "\n")

        logger.info("Ingestion completed", **stats_entry)

    def run(
        self,
        input_dir: str,
        tests_file: str,
        parquet_out: str,
        snapshot_out: str,
        log_out: str,
    ):
        """Run the complete ingestion pipeline."""
        logger.info("Starting Alice learning ingestion")

        # Read input data
        telemetry_events = self.read_telemetry_files(input_dir)
        test_events = self.read_test_results(tests_file)

        all_events = telemetry_events + test_events
        self.stats["rows_raw"] = len(all_events)

        logger.info("Processing events", total=len(all_events))

        # Process events
        learnable_rows = []
        for event in all_events:
            normalized = self.normalize_event(event)
            if normalized and self.is_learnable(normalized):
                labeled = self.add_learning_labels(normalized)
                learnable_rows.append(labeled)

        self.stats["rows_learnable"] = len(learnable_rows)

        # Write outputs
        date = datetime.now().strftime("%Y-%m-%d")
        self.write_parquet(learnable_rows, parquet_out, date)
        self.write_snapshot(learnable_rows, snapshot_out, date)
        self.log_stats(log_out)

        logger.info(
            "Ingestion pipeline completed",
            raw=self.stats["rows_raw"],
            learnable=self.stats["rows_learnable"],
        )


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Alice Learning Ingestion Pipeline")
    parser.add_argument(
        "--input", default="data/telemetry", help="Input telemetry directory"
    )
    parser.add_argument(
        "--tests", default="data/tests/results.jsonl", help="Test results file"
    )
    parser.add_argument(
        "--parquet_out", default="data/learn/parquet", help="Parquet output directory"
    )
    parser.add_argument(
        "--snapshot_out",
        default="data/learn/snapshots",
        help="Snapshot output directory",
    )
    parser.add_argument(
        "--log_out", default="data/learn/logs/learn.jsonl", help="Statistics log file"
    )
    parser.add_argument("--config", help="Configuration file (JSON)")

    args = parser.parse_args()

    # Load configuration
    config = {
        "LEARN_ENABLED": True,
        "LEARN_PII_POLICY": "bronze",
        "LEARN_MASK_EMAIL": True,
        "LEARN_MASK_PHONE": True,
        "LEARN_MASK_SSN": True,
        "LEARN_MIN_CONF": 0.60,
        "LEARN_MIN_MARGIN": 0.05,
        "LEARN_DENY_STRICT": True,
    }

    # Override with environment variables
    for key in config:
        env_val = os.environ.get(key)
        if env_val is not None:
            if isinstance(config[key], bool):
                config[key] = env_val.lower() in ("true", "1", "yes")
            elif isinstance(config[key], float):
                config[key] = float(env_val)
            else:
                config[key] = env_val

    # Override with config file
    if args.config:
        try:
            with open(args.config, "r") as f:
                file_config = json.load(f)
                config.update(file_config)
        except Exception as e:
            logger.error("Failed to load config file", file=args.config, error=str(e))
            sys.exit(1)

    # Run ingestion
    try:
        ingestion = LearnIngestion(config)
        ingestion.run(
            input_dir=args.input,
            tests_file=args.tests,
            parquet_out=args.parquet_out,
            snapshot_out=args.snapshot_out,
            log_out=args.log_out,
        )
    except Exception as e:
        logger.error("Ingestion failed", error=str(e))
        sys.exit(1)


if __name__ == "__main__":
    main()
