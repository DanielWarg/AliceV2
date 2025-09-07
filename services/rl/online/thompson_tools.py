# services/rl/online/thompson_tools.py
"""
Thompson Sampling för intelligent tool-val per intent
"""
from __future__ import annotations
import os
import random
from typing import Dict, Any, List, Optional, Tuple
from services.rl.persistence.bandit_store import (
    ThompsonState, BetaArm, load_thompson, save_thompson, init_empty_thompson
)

# Configuration
SUCCESS_THRESHOLD = float(os.getenv("RL_THOMPSON_SUCCESS_THRESH", "0.7"))

class ThompsonTools:
    """Thompson Sampling tool selector per intent"""
    
    def __init__(self):
        self.update_count = 0
        
        # Try to load existing state
        self.state = load_thompson()
        if self.state is None:
            self.state = init_empty_thompson()
            print("Initialized new Thompson tool selector")
        else:
            total_policies = sum(len(tools) for tools in self.state.policies.values())
            print(f"Loaded Thompson tool selector with {len(self.state.policies)} intents, {total_policies} total policies")

    def _ensure_intent(self, intent: str) -> None:
        """Ensure intent exists in policies"""
        if intent not in self.state.policies:
            self.state.policies[intent] = {}

    def _ensure_tool(self, intent: str, tool: str) -> None:
        """Ensure tool exists for intent"""
        self._ensure_intent(intent)
        if tool not in self.state.policies[intent]:
            self.state.policies[intent][tool] = BetaArm()

    def select(self, intent: str, available_tools: Optional[List[str]] = None) -> Optional[str]:
        """Select best tool for intent using Thompson Sampling"""
        if intent not in self.state.policies or not self.state.policies[intent]:
            return None
        
        tools_dict = self.state.policies[intent]
        
        # Filter by available tools if provided
        if available_tools is not None:
            tools_dict = {t: arm for t, arm in tools_dict.items() if t in available_tools}
        
        if not tools_dict:
            return None
        
        # Sample from each tool's Beta distribution
        samples = {}
        for tool_name, arm in tools_dict.items():
            try:
                # Use random.betavariate for sampling
                sample = random.betavariate(arm.alpha, arm.beta)
                samples[tool_name] = sample
            except ValueError:
                # Handle edge cases where alpha or beta might be 0
                samples[tool_name] = 0.5
        
        # Return tool with highest sample
        return max(samples.items(), key=lambda x: x[1])[0]

    def update(self, intent: str, tool: str, reward: float) -> None:
        """Update Beta parameters after observing reward"""
        self._ensure_tool(intent, tool)
        
        # Clip reward to [0, 1]
        reward = max(0.0, min(1.0, float(reward)))
        
        arm = self.state.policies[intent][tool]
        
        # Interpret reward as success probability
        # reward >= threshold -> success (update alpha)
        # reward < threshold -> failure (update beta)
        if reward >= SUCCESS_THRESHOLD:
            # Success: increase alpha by reward weight
            arm.alpha += reward
            arm.beta += (1.0 - reward)  # Smaller beta increase for high confidence
        else:
            # Failure: increase beta more than alpha
            arm.alpha += reward * 0.5  # Smaller alpha increase
            arm.beta += (1.0 - reward)
        
        arm.pulls += 1
        arm.reward_sum += reward
        
        self.update_count += 1

    def get_stats(self) -> Dict[str, Any]:
        """Get tool selector statistics"""
        stats = {
            "total_updates": self.update_count,
            "intents": {}
        }
        
        for intent, tools in self.state.policies.items():
            intent_stats = {
                "num_tools": len(tools),
                "tools": {}
            }
            
            for tool_name, arm in tools.items():
                avg_reward = arm.reward_sum / max(1, arm.pulls)
                expected_success = arm.alpha / (arm.alpha + arm.beta)
                
                intent_stats["tools"][tool_name] = {
                    "pulls": arm.pulls,
                    "avg_reward": avg_reward,
                    "alpha": arm.alpha,
                    "beta": arm.beta,
                    "expected_success": expected_success
                }
            
            stats["intents"][intent] = intent_stats
        
        return stats

    def get_tool_probabilities(self, intent: str, num_samples: int = 1000) -> Dict[str, float]:
        """Get empirical probabilities of selecting each tool"""
        if intent not in self.state.policies or not self.state.policies[intent]:
            return {}
        
        tools = list(self.state.policies[intent].keys())
        if not tools:
            return {}
        
        # Count selections over many samples
        selection_counts = {tool: 0 for tool in tools}
        
        for _ in range(num_samples):
            selected = self.select(intent)
            if selected:
                selection_counts[selected] += 1
        
        # Convert to probabilities
        return {tool: count / num_samples for tool, count in selection_counts.items()}

    def get_top_tools(self, intent: str, k: int = 3) -> List[Tuple[str, float]]:
        """Get top k tools for intent by expected success rate"""
        if intent not in self.state.policies:
            return []
        
        tools_with_success = []
        for tool_name, arm in self.state.policies[intent].items():
            expected_success = arm.alpha / (arm.alpha + arm.beta)
            tools_with_success.append((tool_name, expected_success))
        
        # Sort by expected success rate
        tools_with_success.sort(key=lambda x: x[1], reverse=True)
        
        return tools_with_success[:k]

    def save(self) -> bool:
        """Save current state to disk"""
        return save_thompson(self.state)

    def add_new_tool(self, intent: str, tool: str) -> None:
        """Add a new tool for an intent with default Beta(1,1)"""
        self._ensure_tool(intent, tool)

    def remove_tool(self, intent: str, tool: str) -> bool:
        """Remove a tool from an intent"""
        if intent in self.state.policies and tool in self.state.policies[intent]:
            del self.state.policies[intent][tool]
            # Clean up empty intents
            if not self.state.policies[intent]:
                del self.state.policies[intent]
            return True
        return False


# Test Thompson tools if run directly
if __name__ == "__main__":
    print("Testing Thompson Tools...")
    
    selector = ThompsonTools()
    
    # Add some tools for different intents
    test_cases = [
        ("time.info", "time_tool", 0.9),
        ("time.info", "calendar_tool", 0.3),
        ("time.info", "web_search_tool", 0.4),
        ("weather.info", "weather_tool", 0.95),
        ("weather.info", "web_search_tool", 0.6),
        ("email.send", "email_tool", 0.8),
        ("email.send", "calendar_tool", 0.2),
    ]
    
    print("Running training simulation...")
    
    # Simulate multiple updates
    for intent, tool, base_reward in test_cases:
        for _ in range(10):
            # Add some noise to reward
            noise = random.uniform(-0.1, 0.1)
            reward = max(0.0, min(1.0, base_reward + noise))
            selector.update(intent, tool, reward)
    
    print(f"Stats after training: {selector.get_stats()}")
    
    # Test selections
    for intent in ["time.info", "weather.info", "email.send"]:
        print(f"\nIntent: {intent}")
        selection = selector.select(intent)
        print(f"Selected tool: {selection}")
        
        probs = selector.get_tool_probabilities(intent, num_samples=100)
        print(f"Selection probabilities: {probs}")
        
        top_tools = selector.get_top_tools(intent)
        print(f"Top tools: {top_tools}")
    
    # Save state
    selector.save()
    print("\nThompson tools state saved!")