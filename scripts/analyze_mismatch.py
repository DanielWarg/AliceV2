#!/usr/bin/env python3
"""
Analyze intent mismatch causes
"""

import json
import collections

def analyze_mismatch():
    """Analyze intent mismatch causes from shadow events"""
    
    # Read shadow events
    with open('data/shadow_eval/shadow_events_2025-09-03.jsonl', 'r') as f:
        events = [json.loads(line) for line in f]
    
    # Filter mismatch events
    mismatch_events = [e for e in events if e.get('comparison', {}).get('intent_match') == False]
    
    print(f"Total events: {len(events)}")
    print(f"Mismatch events: {len(mismatch_events)}")
    print()
    
    # Analyze each mismatch
    causes = collections.Counter()
    
    for i, event in enumerate(mismatch_events):
        primary = event.get('primary_result', {})
        shadow = event.get('shadow_result', {})
        
        primary_tool = primary.get('tool', 'none')
        primary_intent = primary.get('intent', 'none')
        shadow_tool = shadow.get('tool', 'none')
        shadow_intent = shadow.get('intent', 'none')
        
        print(f"Mismatch {i+1}:")
        print(f"  Primary: tool='{primary_tool}', intent='{primary_intent}'")
        print(f"  Shadow:  tool='{shadow_tool}', intent='{shadow_intent}'")
        
        # Determine cause
        if primary_tool == shadow_tool:
            if primary_intent == 'none' and shadow_intent != 'none':
                cause = 'PRIMARY_NO_INTENT'
            elif primary_intent != 'none' and shadow_intent == 'none':
                cause = 'SHADOW_NO_INTENT'
            else:
                cause = 'INTENT_DIFFERENT'
        else:
            cause = 'TOOL_DIFFERENT'
        
        causes[cause] += 1
        print(f"  Cause: {cause}")
        print()
    
    print("Summary:")
    for cause, count in causes.items():
        print(f"  {cause}: {count}")
    
    return causes

if __name__ == "__main__":
    analyze_mismatch()
