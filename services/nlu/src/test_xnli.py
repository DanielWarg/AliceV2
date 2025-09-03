#!/usr/bin/env python3

import sys
import os
sys.path.append('/app/src')

from intent_validator import IntentValidator
from model_registry import NLURegistry

def test_xnli():
    print("=== XNLI TEST ===")
    
    # Create registry and validator
    registry = NLURegistry()
    validator = IntentValidator(registry)
    
    print(f"Enabled: {validator.enabled}")
    print(f"ONNX session: {validator._sess is not None}")
    print(f"Tokenizer: {validator._tokenizer is not None}")
    print(f"Threshold: {validator._ent_thresh}")
    
    # Test validation
    text = "Vad är vädret i Stockholm?"
    labels = ["weather.today", "smalltalk.time"]
    
    print(f"\nTesting: '{text}' with labels {labels}")
    result = validator.validate(text, labels)
    print(f"Result: {result}")
    
    # Test entailment directly
    if validator._tokenizer is not None:
        print("\nTesting entailment directly...")
        p1 = validator._entailment_prob(text, "väder idag, prognos idag, temperatur, weather today")
        p2 = validator._entailment_prob(text, "klockan, tid, datum, time")
        print(f"P1 (weather): {p1}")
        print(f"P2 (time): {p2}")

if __name__ == "__main__":
    test_xnli()
