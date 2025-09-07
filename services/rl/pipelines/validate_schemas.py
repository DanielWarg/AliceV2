#!/usr/bin/env python3
"""
T1 Schema Validation - Test schemas against telemetry data
"""
import json
import random
from pathlib import Path
from typing import List, Dict, Any
from services.rl.pipelines.dataset_schemas import RawEvent
from services.rl.pipelines.utils_io import iter_jsonl

def load_sample_telemetry(telemetry_dir: Path, max_samples: int = 100) -> List[Dict[str, Any]]:
    """Load up to max_samples random telemetry events"""
    all_events = []
    
    for jsonl_file in telemetry_dir.glob("*.jsonl"):
        try:
            for event in iter_jsonl(jsonl_file):
                all_events.append(event)
        except Exception as e:
            print(f"Skippar {jsonl_file}: {e}")
            continue
    
    if len(all_events) > max_samples:
        return random.sample(all_events, max_samples)
    return all_events

def telemetry_to_raw_event(telemetry: Dict[str, Any]) -> RawEvent:
    """Convert telemetry format to RawEvent schema"""
    # Map telemetry fields to RawEvent
    return RawEvent(
        timestamp=telemetry.get("ts", "2025-09-01T00:00:00Z"),
        session_id=telemetry.get("session_id", "unknown"),
        text=telemetry.get("input_text", ""),
        intent=telemetry.get("route"),  # "planner", "chat", etc.
        tool_called=None,  # Telemetry has tool_calls list, would need processing
        tool_success=None,  # Not in telemetry format yet
        latency_ms=telemetry.get("e2e_full_ms"),
        energy_wh=telemetry.get("energy_wh"),
        policy_refusal=False,  # Not in telemetry format yet
        extra=telemetry  # Store original for debugging
    )

def main():
    telemetry_dir = Path("data/telemetry")
    if not telemetry_dir.exists():
        print(f"❌ Telemetry directory {telemetry_dir} does not exist")
        return False
    
    print("📊 Loading telemetry samples...")
    samples = load_sample_telemetry(telemetry_dir, 100)
    print(f"📝 Loaded {len(samples)} telemetry events")
    
    if len(samples) == 0:
        print("❌ No telemetry data found")
        return False
    
    success_count = 0
    error_count = 0
    
    print("🧪 Validating RawEvent schemas...")
    for i, telemetry in enumerate(samples):
        try:
            raw_event = telemetry_to_raw_event(telemetry)
            success_count += 1
            if i < 3:  # Show first 3 for debugging
                print(f"✅ Sample {i+1}: {raw_event.session_id}, {raw_event.intent}, {raw_event.latency_ms}ms")
        except Exception as e:
            error_count += 1
            if error_count <= 5:  # Show first 5 errors
                print(f"❌ Sample {i+1} failed: {e}")
    
    success_rate = success_count / len(samples) if samples else 0
    print(f"\n📈 Validation Results:")
    print(f"   ✅ Success: {success_count}/{len(samples)} ({success_rate:.1%})")
    print(f"   ❌ Errors: {error_count}/{len(samples)}")
    
    if success_rate >= 0.8:
        print("🎉 Schema validation PASSED (≥80% success rate)")
        return True
    else:
        print("🚨 Schema validation FAILED (<80% success rate)")
        return False

if __name__ == "__main__":
    import sys
    success = main()
    sys.exit(0 if success else 1)