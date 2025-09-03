#!/usr/bin/env python3
"""
Find session ID that qualifies for canary routing
"""

import hashlib

def find_canary_session(percentage=5.0):
    """Find a session ID that qualifies for canary routing"""
    canary_threshold = (percentage / 100.0) * 0xffffffff
    
    i = 0
    while i < 1000:
        session_id = f"test_{i:03d}"
        session_hash = int(hashlib.md5(session_id.encode()).hexdigest()[:8], 16)
        if session_hash <= canary_threshold:
            print(f"Found qualifying session: {session_id} (hash: {session_hash})")
            print(f"Canary threshold: {canary_threshold}")
            print(f"Percentage: {percentage}%")
            return session_id
        i += 1
    
    print("No qualifying session found in first 1000")
    return None

if __name__ == "__main__":
    session = find_canary_session(5.0)
    if session:
        print(f"\nUse this session ID for testing: {session}")
