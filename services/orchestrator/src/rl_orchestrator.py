# services/orchestrator/src/rl_orchestrator.py
"""
RL-powered orchestrator som integrerar LinUCB routing och Thompson tool selection
"""
from __future__ import annotations
import time
from typing import Dict, Any, Optional
from services.orchestrator.src.router.route_decider import RouteDecider
from services.orchestrator.src.tools.tool_selector import ToolSelector
from services.rl.rewards.phi_reward import compute_phi_total

class RLOrchestrator:
    """Orchestrator med RL-baserad routing och tool-selection"""
    
    def __init__(self):
        self.route_decider = RouteDecider()
        self.tool_selector = ToolSelector()
        self.turn_count = 0
        self.save_interval = 30  # Save state every 30 turns
        
        print("RLOrchestrator initialized with RL routing and tool selection")

    def process_turn(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Process a complete turn with RL decision making and learning"""
        turn_start = time.time()
        self.turn_count += 1
        
        # Extract context from request
        context = self._extract_context(request)
        
        # 1. Route Decision (LinUCB)
        route_decision = self.route_decider.decide_route(context)
        route = route_decision["route"]
        
        # 2. Tool Selection (Thompson Sampling)
        intent = context.get("intent", "unknown")
        tool_decision = self.tool_selector.select_tool(intent, context)
        tool = tool_decision["tool"]
        
        # 3. Execute the turn (placeholder - integrate with your actual execution)
        execution_result = self._execute_turn(request, route, tool, context)
        
        # 4. Calculate φ-reward from turn results
        reward_result = self._calculate_phi_reward(execution_result)
        reward = reward_result.get("total", 0.0)
        
        # 5. Update RL models with observed reward
        if reward is not None:
            self.route_decider.update_from_turn(route_decision, reward)
            self.tool_selector.update_from_turn(tool_decision, reward)
        
        # 6. Periodic state saving
        if self.turn_count % self.save_interval == 0:
            self._save_states()
        
        # 7. Prepare response
        turn_time = time.time() - turn_start
        
        response = {
            "result": execution_result.get("result", ""),
            "route": route,
            "tool": tool,
            "reward": reward,
            "turn_time_ms": turn_time * 1000,
            "turn_id": self.turn_count,
            "rl_info": {
                "route_decision": route_decision,
                "tool_decision": tool_decision,
                "reward_components": reward_result,
                "canary": route_decision.get("canary", False) or tool_decision.get("canary", False)
            }
        }
        
        return response

    def _extract_context(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Extract context features for RL decision making"""
        text = request.get("text", "")
        intent = request.get("intent", "unknown")
        
        # Extract features similar to episode format
        context = {
            "intent": intent,
            "intent_conf": request.get("intent_conf", 0.5),
            "len_chars": len(text),
            "has_question": "?" in text,
            "cache_hint": request.get("cache_hit", False),
            "guardian_state": request.get("guardian_state", "NORMAL"),
            "prev_tool_error": request.get("prev_tool_error", False),
        }
        
        return context

    def _execute_turn(
        self, 
        request: Dict[str, Any], 
        route: str, 
        tool: str, 
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Execute the turn with chosen route and tool
        This is a placeholder - integrate with your actual orchestrator logic
        """
        
        # Simulate execution time based on route
        if route == "micro":
            execution_time = 0.15  # Fast
        elif route == "planner":  
            execution_time = 0.5   # Medium
        else:  # deep
            execution_time = 1.2   # Slow
        
        time.sleep(execution_time)  # Simulate processing
        
        # Mock result based on route and tool
        success = True
        if context.get("guardian_state") == "EMERGENCY":
            success = False
        
        result = {
            "result": f"Mock response from {route} route using {tool}",
            "success": success,
            "route_used": route,
            "tool_used": tool,
            "execution_time_ms": execution_time * 1000,
            "schema_ok": True,
            "tool_success": success,
            "safety_ok": True,
            "energy_wh": execution_time * 0.001,  # Mock energy usage
        }
        
        return result

    def _calculate_phi_reward(self, execution_result: Dict[str, Any]) -> Dict[str, Optional[float]]:
        """Calculate φ-weighted reward from execution result"""
        
        # Extract metrics from execution result
        latency_ms = execution_result.get("execution_time_ms", 1000.0)
        energy_wh = execution_result.get("energy_wh", 0.001)
        safety_ok = execution_result.get("safety_ok", True)
        tool_success = execution_result.get("tool_success", True)
        schema_ok = execution_result.get("schema_ok", True)
        
        # Calculate φ-reward using T3 logic
        reward_components = compute_phi_total(
            latency_ms=latency_ms,
            energy_wh=energy_wh,
            safety_ok=safety_ok,
            tool_success=tool_success,
            schema_ok=schema_ok,
        )
        
        return reward_components

    def _save_states(self) -> None:
        """Save RL model states to disk"""
        try:
            route_saved = self.route_decider.save_state()
            tool_saved = self.tool_selector.save_state()
            print(f"Turn {self.turn_count}: Saved RL states (route: {route_saved}, tools: {tool_saved})")
        except Exception as e:
            print(f"Error saving RL states: {e}")

    def get_rl_stats(self) -> Dict[str, Any]:
        """Get comprehensive RL statistics"""
        return {
            "turn_count": self.turn_count,
            "route_stats": self.route_decider.get_stats(),
            "tool_stats": self.tool_selector.get_stats(),
        }

    def force_save(self) -> Dict[str, bool]:
        """Force save all RL states"""
        return {
            "route_saved": self.route_decider.save_state(),
            "tool_saved": self.tool_selector.save_state(),
        }

# Global instance for use in orchestrator
rl_orchestrator = RLOrchestrator()


# Example usage/testing
if __name__ == "__main__":
    print("Testing RLOrchestrator...")
    
    orchestrator = RLOrchestrator()
    
    # Test requests
    test_requests = [
        {
            "text": "What time is it?",
            "intent": "time.info",
            "intent_conf": 0.9,
            "guardian_state": "NORMAL"
        },
        {
            "text": "Send an email to John about the meeting tomorrow",
            "intent": "email.send", 
            "intent_conf": 0.8,
            "guardian_state": "NORMAL"
        },
        {
            "text": "Analyze this complex dataset and provide insights on market trends over the last 5 years",
            "intent": "analysis",
            "intent_conf": 0.7,
            "guardian_state": "BROWNOUT"
        }
    ]
    
    # Process test requests
    for i, request in enumerate(test_requests):
        print(f"\n--- Turn {i+1} ---")
        print(f"Request: {request['text'][:50]}...")
        
        response = orchestrator.process_turn(request)
        
        print(f"Route: {response['route']} (canary: {response['rl_info']['route_decision']['canary']})")
        print(f"Tool: {response['tool']} (canary: {response['rl_info']['tool_decision']['canary']})") 
        print(f"Reward: {response['reward']:.3f}")
        print(f"Turn time: {response['turn_time_ms']:.1f}ms")
    
    # Show final stats
    print(f"\nFinal RL stats:")
    stats = orchestrator.get_rl_stats()
    print(f"Total turns: {stats['turn_count']}")
    print(f"Route canary rate: {stats['route_stats']['canary_rate']:.2%}")
    print(f"Tool canary rate: {stats['tool_stats']['canary_rate']:.2%}")
    
    # Force save
    save_result = orchestrator.force_save()
    print(f"States saved: {save_result}")