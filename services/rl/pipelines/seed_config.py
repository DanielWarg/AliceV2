#!/usr/bin/env python3
"""
Seed management for reproducible RL pipeline builds
Frozen seeds for T1-T6 hardening phase
"""

import os
import random
import numpy as np
from typing import Dict, Any

# FROZEN SEEDS FOR T1-T6 HARDENING - DO NOT CHANGE
T1_T6_FROZEN_SEED = int(os.getenv("SEED", "20250907"))

# Component-specific seeds derived from main seed
COMPONENT_SEEDS = {
    "dataset_split": T1_T6_FROZEN_SEED,
    "episode_shuffle": T1_T6_FROZEN_SEED + 1,
    "reward_noise": T1_T6_FROZEN_SEED + 2,
    "pii_mask": T1_T6_FROZEN_SEED + 3,
    "validation_sample": T1_T6_FROZEN_SEED + 4,
    "bandit_init": T1_T6_FROZEN_SEED + 5,
    "lora_training": T1_T6_FROZEN_SEED + 6,
    "drift_test": T1_T6_FROZEN_SEED + 10,
    "categorical_test": T1_T6_FROZEN_SEED + 11,
    "integration_test": T1_T6_FROZEN_SEED + 12,
    "reward_validation": T1_T6_FROZEN_SEED + 13,
    "winsorize_test": T1_T6_FROZEN_SEED + 14,
    "clean_test": T1_T6_FROZEN_SEED + 15
}


def set_global_seeds(base_seed: int = T1_T6_FROZEN_SEED) -> Dict[str, int]:
    """
    Set all global random seeds for reproducibility
    
    Args:
        base_seed: Base seed for all components
        
    Returns:
        Dictionary of seeds set for each component
    """
    # Python random
    random.seed(base_seed)
    
    # NumPy
    np.random.seed(base_seed)
    
    # Update component seeds if base seed changed
    seeds_used = {}
    for component, seed_offset in COMPONENT_SEEDS.items():
        actual_seed = base_seed + (seed_offset - T1_T6_FROZEN_SEED)
        seeds_used[component] = actual_seed
    
    return seeds_used


def get_component_seed(component: str) -> int:
    """
    Get reproducible seed for specific component
    
    Args:
        component: Component name from COMPONENT_SEEDS
        
    Returns:
        Deterministic seed for this component
    """
    if component not in COMPONENT_SEEDS:
        raise ValueError(f"Unknown component: {component}. Available: {list(COMPONENT_SEEDS.keys())}")
    
    return COMPONENT_SEEDS[component]


def create_seed_manifest() -> Dict[str, Any]:
    """
    Create manifest of all seeds used in current build
    """
    seeds_used = set_global_seeds()
    
    return {
        "base_seed": T1_T6_FROZEN_SEED,
        "frozen_for_t1_t6": True,
        "component_seeds": seeds_used,
        "reproducibility_guaranteed": True,
        "seed_source": "SEED environment variable or hardcoded default",
        "created_at": "2025-09-07T00:00:00Z"
    }


def validate_reproducibility(expected_hash: str, actual_hash: str) -> bool:
    """
    Validate that build produces expected hash
    
    Args:
        expected_hash: Expected output hash
        actual_hash: Actual output hash
        
    Returns:
        True if hashes match (reproducible)
    """
    return expected_hash == actual_hash


# Context manager for component-specific seeding
class ComponentSeed:
    """Context manager for component-specific random seeding"""
    
    def __init__(self, component: str):
        self.component = component
        self.original_state = None
        self.original_np_state = None
        
    def __enter__(self):
        # Save original states
        self.original_state = random.getstate()
        self.original_np_state = np.random.get_state()
        
        # Set component seed
        seed = get_component_seed(self.component)
        random.seed(seed)
        np.random.seed(seed)
        
        return seed
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        # Restore original states
        random.setstate(self.original_state)
        np.random.set_state(self.original_np_state)


if __name__ == "__main__":
    import json
    
    # Test reproducibility
    print("Testing seed reproducibility...")
    
    # Set seeds and generate some random numbers
    set_global_seeds()
    test_values_1 = [random.random() for _ in range(5)]
    test_np_values_1 = np.random.random(5).tolist()
    
    # Reset and generate again
    set_global_seeds()
    test_values_2 = [random.random() for _ in range(5)]
    test_np_values_2 = np.random.random(5).tolist()
    
    # Check reproducibility
    reproducible = (test_values_1 == test_values_2) and (test_np_values_1 == test_np_values_2)
    
    print(f"Reproducible: {reproducible}")
    print(f"Python random values match: {test_values_1 == test_values_2}")
    print(f"NumPy random values match: {test_np_values_1 == test_np_values_2}")
    
    # Generate manifest
    manifest = create_seed_manifest()
    print("\nSeed manifest:")
    print(json.dumps(manifest, indent=2))