#!/usr/bin/env python3
import hashlib

i = 0
while i < 1000:
    session_id = f"test_{i:03d}"
    session_hash = int(hashlib.md5(session_id.encode()).hexdigest()[:8], 16)
    canary_threshold = (5.0 / 100.0) * 0xffffffff
    if session_hash <= canary_threshold:
        print(f"Found qualifying session: {session_id} (hash: {session_hash})")
        break
    i += 1
