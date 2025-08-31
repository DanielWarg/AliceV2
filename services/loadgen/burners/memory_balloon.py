"""
Memory Balloon - Gradual RAM allocation to trigger Guardian thresholds
======================================================================
"""

import numpy as np
import time
import os
import psutil
from typing import Dict, Any, List

# Configuration
MEMORY_BALLOON_GB = float(os.getenv("MEMORY_BALLOON_GB", "4.0"))
BLOCK_SIZE_MB = 256  # Allocate in 256MB chunks
ALLOCATION_DELAY_S = 0.2  # Delay between allocations

def get_memory_stats() -> Dict[str, float]:
    """Get current memory statistics"""
    memory = psutil.virtual_memory()
    return {
        "total_gb": memory.total / (1024**3),
        "available_gb": memory.available / (1024**3),
        "used_gb": memory.used / (1024**3),
        "percent": memory.percent
    }

def run(gb: float = None, hold_seconds: int = 60) -> Dict[str, Any]:
    """
    Run memory balloon stress test
    
    Args:
        gb: Amount of RAM to allocate in GB (default from env)
        hold_seconds: How long to hold the allocated memory
        
    Returns:
        Test results with allocation stats
    """
    gb = gb or MEMORY_BALLOON_GB
    block_size_bytes = BLOCK_SIZE_MB * 1024 * 1024
    target_bytes = int(gb * 1024 * 1024 * 1024)
    
    print(f"🎈 Starting Memory Balloon: {gb:.1f}GB target, hold for {hold_seconds}s")
    
    # Get baseline memory stats
    baseline_stats = get_memory_stats()
    print(f"   Baseline RAM: {baseline_stats['used_gb']:.1f}GB "
          f"({baseline_stats['percent']:.1f}%)")
    
    start_time = time.perf_counter()
    memory_blocks: List[np.ndarray] = []
    allocated_bytes = 0
    allocation_start = time.perf_counter()
    
    try:
        # Gradual allocation phase
        while allocated_bytes < target_bytes:
            try:
                # Allocate block and fill with data to ensure it's committed
                block = np.random.random(block_size_bytes // 8).astype(np.float64)
                # Touch the memory to ensure it's actually allocated
                block[0] = time.time()
                block[-1] = time.time()
                
                memory_blocks.append(block)
                allocated_bytes += block_size_bytes
                
                # Progress update
                current_stats = get_memory_stats()
                progress_pct = (allocated_bytes / target_bytes) * 100
                
                print(f"   Allocated: {allocated_bytes/(1024**3):.1f}GB "
                      f"({progress_pct:.1f}%), RAM: {current_stats['percent']:.1f}%")
                
                # Check if we've hit Guardian thresholds
                if current_stats['percent'] > 90:
                    print(f"   🟡 RAM > 90% - Guardian should trigger brownout soon")
                elif current_stats['percent'] > 85:
                    print(f"   ⚠️  RAM > 85% - Approaching brownout threshold")
                
                time.sleep(ALLOCATION_DELAY_S)
                
            except MemoryError:
                print(f"   ❌ Memory allocation failed at {allocated_bytes/(1024**3):.1f}GB")
                break
                
        allocation_time = time.perf_counter() - allocation_start
        
        # Hold phase - keep memory allocated
        print(f"   Holding {allocated_bytes/(1024**3):.1f}GB for {hold_seconds}s...")
        hold_start = time.perf_counter()
        
        while time.perf_counter() - hold_start < hold_seconds:
            # Periodically touch memory blocks to prevent swapping
            if memory_blocks and int(time.time()) % 10 == 0:
                for i, block in enumerate(memory_blocks[::10]):  # Touch every 10th block
                    block[0] = time.time()
                    
            # Report current memory status
            if int(time.perf_counter() - hold_start) % 15 == 0:  # Every 15s
                current_stats = get_memory_stats()
                remaining = hold_seconds - (time.perf_counter() - hold_start)
                print(f"   Holding... RAM: {current_stats['percent']:.1f}%, "
                      f"{remaining:.0f}s remaining")
                
            time.sleep(1)
        
        # Final stats before cleanup
        peak_stats = get_memory_stats()
        total_time = time.perf_counter() - start_time
        
    finally:
        # Cleanup phase
        print(f"   🧹 Releasing {len(memory_blocks)} memory blocks...")
        cleanup_start = time.perf_counter()
        memory_blocks.clear()  # Release references
        cleanup_time = time.perf_counter() - cleanup_start
        
        # Force garbage collection
        import gc
        gc.collect()
        
        # Final memory stats
        final_stats = get_memory_stats()
        
    result_summary = {
        "test_type": "memory_balloon",
        "target_gb": gb,
        "allocated_gb": allocated_bytes / (1024**3),
        "hold_seconds": hold_seconds,
        "allocation_time_s": round(allocation_time, 2),
        "cleanup_time_s": round(cleanup_time, 2),
        "total_time_s": round(total_time, 2),
        "memory_stats": {
            "baseline": baseline_stats,
            "peak": peak_stats,
            "final": final_stats
        },
        "blocks_allocated": len(memory_blocks) if 'memory_blocks' in locals() else 0
    }
    
    print(f"   Completed: {allocated_bytes/(1024**3):.1f}GB allocated, "
          f"peak RAM: {peak_stats['percent']:.1f}%")
    
    return result_summary