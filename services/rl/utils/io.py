"""
Robust I/O utilities for Alice RL system.

Handles JSONL reading with defensive parsing, compression support,
and efficient file discovery patterns.
"""

from __future__ import annotations

import gzip
import json
import pathlib
from typing import Any, Dict, Iterable, Iterator, List, Optional

import structlog

logger = structlog.get_logger(__name__)


def iter_jsonl(path: pathlib.Path, encoding: str = "utf-8") -> Iterator[Dict[str, Any]]:
    """
    Iterate over JSONL file with robust error handling.

    Args:
        path: Path to JSONL file (.jsonl, .jsonl.gz supported)
        encoding: Text encoding (default: utf-8)

    Yields:
        Parsed JSON objects as dicts

    Handles:
        - Gzipped files automatically
        - Malformed JSON lines (skips with warning)
        - Empty lines
        - Different encodings
    """
    if not path.exists():
        logger.warning("JSONL file not found", path=str(path))
        return

    # Choose opener based on file extension
    open_fn = gzip.open if path.suffix == ".gz" else open

    try:
        with open_fn(path, "rt", encoding=encoding) as f:
            line_num = 0
            parsed_count = 0
            error_count = 0

            for line in f:
                line_num += 1
                line = line.strip()

                if not line:
                    continue  # Skip empty lines

                try:
                    obj = json.loads(line)
                    parsed_count += 1
                    yield obj

                except json.JSONDecodeError as e:
                    error_count += 1
                    if error_count <= 10:  # Log first 10 errors only
                        logger.warning(
                            "Invalid JSON line",
                            path=str(path),
                            line_num=line_num,
                            error=str(e),
                            line_preview=line[:100],
                        )
                    continue

            logger.info(
                "JSONL processing complete",
                path=str(path),
                total_lines=line_num,
                parsed=parsed_count,
                errors=error_count,
            )

    except Exception as e:
        logger.error("Failed to read JSONL file", path=str(path), error=str(e))


def find_files(
    root: str | pathlib.Path, pattern: str = "*.jsonl*"
) -> List[pathlib.Path]:
    """
    Find files matching pattern recursively.

    Args:
        root: Root directory to search
        pattern: Glob pattern (e.g., "*.jsonl*", "events_*.jsonl.gz")

    Returns:
        Sorted list of matching file paths
    """
    root_path = pathlib.Path(root)

    if not root_path.exists():
        logger.warning("Root directory not found", root=str(root_path))
        return []

    if not root_path.is_dir():
        logger.warning("Root is not a directory", root=str(root_path))
        return []

    try:
        matches = sorted(root_path.rglob(pattern))
        logger.info(
            "File discovery complete",
            root=str(root_path),
            pattern=pattern,
            found=len(matches),
        )

        # Filter out non-files (just in case)
        files = [p for p in matches if p.is_file()]

        if len(files) != len(matches):
            logger.debug("Filtered non-files", total=len(matches), files=len(files))

        return files

    except Exception as e:
        logger.error(
            "File discovery failed", root=str(root_path), pattern=pattern, error=str(e)
        )
        return []


def load_jsonl_batch(
    paths: List[pathlib.Path], max_records: Optional[int] = None
) -> List[Dict[str, Any]]:
    """
    Load multiple JSONL files into memory efficiently.

    Args:
        paths: List of JSONL file paths
        max_records: Maximum records to load (None = no limit)

    Returns:
        List of all parsed records from all files
    """
    records = []
    total_files = len(paths)

    for i, path in enumerate(paths):
        logger.debug("Processing file", file=str(path), progress=f"{i+1}/{total_files}")

        for record in iter_jsonl(path):
            records.append(record)

            if max_records and len(records) >= max_records:
                logger.info(
                    "Reached max_records limit",
                    max_records=max_records,
                    files_processed=i + 1,
                )
                return records

    logger.info(
        "Batch loading complete", total_files=total_files, total_records=len(records)
    )

    return records


def write_jsonl(
    path: pathlib.Path,
    records: Iterable[Dict[str, Any]],
    compress: bool = False,
    encoding: str = "utf-8",
) -> int:
    """
    Write records to JSONL file.

    Args:
        path: Output path
        records: Iterable of dict records
        compress: Whether to gzip compress
        encoding: Text encoding

    Returns:
        Number of records written
    """
    # Ensure parent directory exists
    path.parent.mkdir(parents=True, exist_ok=True)

    # Choose opener and adjust extension
    if compress and not path.suffix.endswith(".gz"):
        path = path.with_suffix(path.suffix + ".gz")

    open_fn = gzip.open if compress else open

    try:
        with open_fn(path, "wt", encoding=encoding) as f:
            count = 0
            for record in records:
                json.dump(record, f, ensure_ascii=False)
                f.write("\n")
                count += 1

        logger.info(
            "JSONL write complete", path=str(path), records=count, compressed=compress
        )

        return count

    except Exception as e:
        logger.error("JSONL write failed", path=str(path), error=str(e))
        raise


def peek_jsonl_schema(
    paths: List[pathlib.Path], sample_size: int = 100
) -> Dict[str, Any]:
    """
    Peek at JSONL files to understand schema/structure.

    Args:
        paths: List of JSONL file paths
        sample_size: Number of records to sample

    Returns:
        Schema analysis dict with field frequencies and types
    """
    field_counts = {}
    field_types = {}
    total_records = 0

    for path in paths:
        sampled = 0

        for record in iter_jsonl(path):
            if sampled >= sample_size:
                break

            total_records += 1
            sampled += 1

            # Analyze fields in this record
            for field, value in record.items():
                field_counts[field] = field_counts.get(field, 0) + 1

                value_type = type(value).__name__
                if field not in field_types:
                    field_types[field] = {}
                field_types[field][value_type] = (
                    field_types[field].get(value_type, 0) + 1
                )

        if total_records >= sample_size:
            break

    # Calculate field frequencies
    field_freq = {field: count / total_records for field, count in field_counts.items()}

    analysis = {
        "total_records_sampled": total_records,
        "unique_fields": len(field_counts),
        "field_frequencies": field_freq,
        "field_types": field_types,
        "files_examined": len(paths),
    }

    # Find most common fields (>50% frequency)
    common_fields = {k: v for k, v in field_freq.items() if v > 0.5}
    analysis["common_fields"] = common_fields

    # Find rare fields (<10% frequency)
    rare_fields = {k: v for k, v in field_freq.items() if v < 0.1}
    analysis["rare_fields"] = rare_fields

    logger.info(
        "Schema analysis complete",
        files=len(paths),
        sample_size=total_records,
        unique_fields=len(field_counts),
        common=len(common_fields),
        rare=len(rare_fields),
    )

    return analysis


# Utility functions for specific data patterns
def extract_alice_events(record: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    Extract Alice-specific event data with defensive parsing.

    Args:
        record: Raw JSONL record

    Returns:
        Standardized Alice event dict or None if not an Alice event
    """
    # Check if this looks like an Alice event
    event_type = record.get("event_type") or record.get("type") or ""

    # Skip non-turn events
    if event_type and event_type not in {"turn", "turn_completed", "response", "chat"}:
        return None

    # Extract with defensive defaults
    standardized = {
        "event_type": event_type,
        "timestamp": record.get("timestamp") or record.get("ts"),
        "session_id": record.get("session_id") or record.get("sessionId"),
        "user_id": record.get("user_id") or record.get("userId"),
        "trace_id": record.get("trace_id") or record.get("traceId"),
    }

    # Copy remaining fields
    for key, value in record.items():
        if key not in standardized:
            standardized[key] = value

    return standardized
