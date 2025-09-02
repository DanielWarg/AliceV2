"""
Learning API endpoints for Alice Smart Ingestion Module.

Provides endpoints for:
- /api/learn/ingest: Run ingestion pipeline
- /api/learn/snapshot: Create daily snapshot
- /api/learn/stats: Get learning statistics
"""

import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Any, Optional

from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel

from ..metrics.metrics import METRICS

router = APIRouter(prefix="/api/learn", tags=["learning"])

# Configuration
LEARN_ENABLED = os.environ.get("LEARN_ENABLED", "true").lower() == "true"
LEARN_INPUT_DIR = os.environ.get("LEARN_INPUT_DIR", "data/telemetry")
LEARN_TESTS_FILE = os.environ.get("LEARN_TESTS_FILE", "data/tests/results.jsonl")
LEARN_OUT_PARQUET = os.environ.get("LEARN_OUT_PARQUET", "data/learn/parquet")
LEARN_OUT_SNAPSHOT = os.environ.get("LEARN_OUT_SNAPSHOT", "data/learn/snapshots")
LEARN_LOG = os.environ.get("LEARN_LOG", "data/learn/logs/learn.jsonl")

class IngestResponse(BaseModel):
    v: str = "1"
    success: bool
    rows_raw: int
    rows_learnable: int
    learning_rate: float
    hard_intent: int
    tool_fail: int
    rag_miss: int
    message: str

class SnapshotResponse(BaseModel):
    v: str = "1"
    success: bool
    snapshot_file: str
    checksum: str
    rows: int
    message: str

class StatsResponse(BaseModel):
    v: str = "1"
    day: str
    rows_raw: int
    rows_learnable: int
    hard_intent: int
    tool_fail: int
    rag_miss: int
    learning_rate: float
    snapshot: Optional[str] = None

def run_ingest_script() -> Dict[str, Any]:
    """Run the ingestion script and return results."""
    if not LEARN_ENABLED:
        raise HTTPException(status_code=503, detail="Learning module disabled")
    
    # Find the ingest script
    script_path = Path(__file__).parent.parent.parent / "ingest" / "run_ingest.py"
    if not script_path.exists():
        raise HTTPException(status_code=500, detail="Ingest script not found")
    
    try:
        # Run the ingestion script
        result = subprocess.run([
            sys.executable, str(script_path),
            "--input", LEARN_INPUT_DIR,
            "--tests", LEARN_TESTS_FILE,
            "--parquet_out", LEARN_OUT_PARQUET,
            "--snapshot_out", LEARN_OUT_SNAPSHOT,
            "--log_out", LEARN_LOG
        ], capture_output=True, text=True, timeout=300)
        
        if result.returncode != 0:
            raise HTTPException(
                status_code=500, 
                detail=f"Ingestion failed: {result.stderr}"
            )
        
        # Parse the last log entry to get stats
        stats = parse_latest_stats()
        
        return {
            "success": True,
            "rows_raw": stats.get("rows_raw", 0),
            "rows_learnable": stats.get("rows_learnable", 0),
            "learning_rate": stats.get("learning_rate", 0.0),
            "hard_intent": stats.get("hard_intent", 0),
            "tool_fail": stats.get("tool_fail", 0),
            "rag_miss": stats.get("rag_miss", 0),
            "message": "Ingestion completed successfully"
        }
        
    except subprocess.TimeoutExpired:
        raise HTTPException(status_code=408, detail="Ingestion timed out")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ingestion error: {str(e)}")

def parse_latest_stats() -> Dict[str, Any]:
    """Parse the latest statistics from the log file."""
    log_path = Path(LEARN_LOG)
    if not log_path.exists():
        return {}
    
    try:
        # Read the last line of the log file
        with open(log_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
            if not lines:
                return {}
            
            # Parse the last line
            last_line = lines[-1].strip()
            return json.loads(last_line)
            
    except Exception as e:
        # Return empty stats if parsing fails
        return {}

def get_snapshot_info() -> Optional[Dict[str, Any]]:
    """Get information about the latest snapshot."""
    today = datetime.now().strftime('%Y-%m-%d')
    snapshot_dir = Path(LEARN_OUT_SNAPSHOT) / today
    
    snapshot_file = snapshot_dir / "dataset.jsonl.gz"
    checksum_file = snapshot_dir / "dataset.jsonl.gz.sha256"
    
    if not snapshot_file.exists():
        return None
    
    try:
        # Get file size and checksum
        file_size = snapshot_file.stat().st_size
        
        checksum = ""
        if checksum_file.exists():
            with open(checksum_file, 'r') as f:
                checksum = f.read().strip()
        
        # Count lines in the snapshot
        import gzip
        line_count = 0
        with gzip.open(snapshot_file, 'rt', encoding='utf-8') as f:
            for _ in f:
                line_count += 1
        
        return {
            "file": str(snapshot_file),
            "size_bytes": file_size,
            "checksum": checksum,
            "rows": line_count
        }
        
    except Exception:
        return None

@router.post("/ingest", response_model=IngestResponse)
async def ingest_data(background_tasks: BackgroundTasks):
    """Run the ingestion pipeline."""
    try:
        result = run_ingest_script()
        
        # Update metrics
        METRICS.learn_ingest_total.inc()
        METRICS.learn_rows_raw.set(result["rows_raw"])
        METRICS.learn_rows_learnable.set(result["rows_learnable"])
        METRICS.learn_hard_intent.set(result["hard_intent"])
        METRICS.learn_tool_fail.set(result["tool_fail"])
        METRICS.learn_rag_miss.set(result["rag_miss"])
        
        return IngestResponse(**result)
        
    except HTTPException:
        raise
    except Exception as e:
        METRICS.learn_ingest_errors.inc()
        raise HTTPException(status_code=500, detail=f"Ingestion failed: {str(e)}")

@router.post("/snapshot", response_model=SnapshotResponse)
async def create_snapshot(background_tasks: BackgroundTasks):
    """Create a daily snapshot."""
    try:
        # Run ingestion to create snapshot
        result = run_ingest_script()
        
        # Get snapshot info
        snapshot_info = get_snapshot_info()
        if not snapshot_info:
            raise HTTPException(status_code=500, detail="Failed to create snapshot")
        
        # Update metrics
        METRICS.learn_snapshot_total.inc()
        METRICS.learn_snapshot_rows.set(snapshot_info["rows"])
        
        return SnapshotResponse(
            success=True,
            snapshot_file=snapshot_info["file"],
            checksum=snapshot_info["checksum"],
            rows=snapshot_info["rows"],
            message="Snapshot created successfully"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        METRICS.learn_snapshot_errors.inc()
        raise HTTPException(status_code=500, detail=f"Snapshot failed: {str(e)}")

@router.get("/stats", response_model=StatsResponse)
async def get_stats():
    """Get learning statistics."""
    try:
        # Parse latest stats
        stats = parse_latest_stats()
        
        if not stats:
            # Return empty stats if no data
            return StatsResponse(
                day=datetime.now().strftime('%Y-%m-%d'),
                rows_raw=0,
                rows_learnable=0,
                hard_intent=0,
                tool_fail=0,
                rag_miss=0,
                learning_rate=0.0
            )
        
        # Get snapshot info
        snapshot_info = get_snapshot_info()
        snapshot_path = snapshot_info["file"] if snapshot_info else None
        
        return StatsResponse(
            day=stats.get("day", datetime.now().strftime('%Y-%m-%d')),
            rows_raw=stats.get("rows_raw", 0),
            rows_learnable=stats.get("rows_learnable", 0),
            hard_intent=stats.get("hard_intent", 0),
            tool_fail=stats.get("tool_fail", 0),
            rag_miss=stats.get("rag_miss", 0),
            learning_rate=stats.get("learning_rate", 0.0),
            snapshot=snapshot_path
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get stats: {str(e)}")

@router.delete("/forget/{session_id}")
async def forget_session(session_id: str):
    """Right-to-forget: Remove data for a specific session."""
    try:
        # This is a placeholder implementation
        # In a real implementation, you would:
        # 1. Search through parquet files for the session_id
        # 2. Remove matching rows
        # 3. Update snapshots
        # 4. Log the forget event
        
        # For now, just log the request
        forget_log = Path("data/learn/logs/forget.jsonl")
        forget_log.parent.mkdir(parents=True, exist_ok=True)
        
        forget_event = {
            "v": "1",
            "ts": datetime.now(timezone.utc).isoformat() + "Z",
            "session_id": session_id,
            "action": "forget_requested"
        }
        
        with open(forget_log, 'a', encoding='utf-8') as f:
            f.write(json.dumps(forget_event, ensure_ascii=False) + '\n')
        
        # Update metrics
        METRICS.learn_forget_total.inc()
        
        return {
            "v": "1",
            "success": True,
            "session_id": session_id,
            "message": "Forget request logged (implementation pending)"
        }
        
    except Exception as e:
        METRICS.learn_forget_errors.inc()
        raise HTTPException(status_code=500, detail=f"Forget failed: {str(e)}")
