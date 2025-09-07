# services/orchestrator/src/router/route_decider.py
"""
Intelligent route decision using LinUCB with fallback to rule-based routing
"""
from __future__ import annotations
import os
from typing import Dict, Any, Optional
from services.rl.online.linucb_router import LinUCBRouter

# Configuration
CANARY_SHARE = float(os.getenv("CANARY_SHARE", "0.05"))  # 5% canary traffic
ENABLE_LEARNING = os.getenv("ENABLE_RL_ROUTING", "true").lower() in ("1", "true", "yes")

class RouteDecider:
    """Intelligent routing with LinUCB + rule-based fallback"""
    
    def __init__(self):
        self.linucb_router = LinUCBRouter() if ENABLE_LEARNING else None
        self.total_decisions = 0
        self.canary_decisions = 0
        self.learning_enabled = ENABLE_LEARNING
        
        print(f"RouteDecider initialized: RL={'enabled' if self.learning_enabled else 'disabled'}, canary={CANARY_SHARE}")

    def decide_route(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Decide route for request with canary testing
        Returns: {route: str, source: str, canary: bool}
        """
        self.total_decisions += 1
        
        # Extract basic info for rule-based fallback
        intent = context.get("intent", "unknown")
        guardian_state = context.get("guardian_state", "NORMAL")
        text_len = context.get("len_chars", 0)
        
        # Rule-based baseline route
        baseline_route = self._baseline_route(intent, guardian_state, text_len)
        
        # Emergency override: always use micro
        if guardian_state == "EMERGENCY":
            return {
                "route": "micro",
                "source": "emergency_override",
                "canary": False,
                "context": context
            }
        
        # Decide if this request should use canary (RL routing)
        use_canary = self._should_use_canary()
        
        if use_canary and self.learning_enabled and self.linucb_router:
            self.canary_decisions += 1
            
            try:
                # Use LinUCB for route decision
                rl_route = self.linucb_router.select(context)
                
                return {
                    "route": rl_route,
                    "source": "linucb",
                    "canary": True,
                    "baseline": baseline_route,
                    "context": context
                }
            except Exception as e:
                print(f"LinUCB routing failed: {e}, falling back to baseline")
                return {
                    "route": baseline_route,
                    "source": "baseline_fallback",
                    "canary": False,
                    "context": context
                }
        else:
            # Use baseline routing
            return {
                "route": baseline_route,
                "source": "baseline",
                "canary": False,
                "context": context
            }

    def _baseline_route(self, intent: str, guardian_state: str, text_len: int) -> str:
        """Rule-based baseline routing logic"""
        
        # Emergency: always micro
        if guardian_state == "EMERGENCY":
            return "micro"
        
        # Simple/fast intents -> micro
        if intent in ["time.info", "weather.info", "smalltalk", "greeting"]:
            return "micro"
        
        # Long text or complex intents -> deep
        if text_len > 200 or intent in ["analysis", "complex", "research"]:
            # But not during brownout
            if guardian_state == "BROWNOUT":
                return "planner"
            return "deep"
        
        # Default: planner for most cases
        return "planner"

    def _should_use_canary(self) -> bool:
        """Decide if this request should use canary routing"""
        import random
        return random.random() < CANARY_SHARE

    def update_from_turn(self, decision: Dict[str, Any], reward: float) -> None:
        """Update router from turn result"""
        if not self.learning_enabled or not self.linucb_router:
            return
        
        # Only update if this was a canary decision
        if not decision.get("canary", False):
            return
        
        try:
            context = decision.get("context", {})
            route = decision.get("route", "micro")
            
            self.linucb_router.update(context, route, reward)
            
        except Exception as e:
            print(f"Error updating LinUCB router: {e}")

    def get_stats(self) -> Dict[str, Any]:
        """Get routing statistics"""
        stats = {
            "total_decisions": self.total_decisions,
            "canary_decisions": self.canary_decisions,
            "canary_rate": self.canary_decisions / max(1, self.total_decisions),
            "learning_enabled": self.learning_enabled,
            "canary_share_target": CANARY_SHARE,
        }
        
        if self.linucb_router:
            stats["linucb_stats"] = self.linucb_router.get_stats()
        
        return stats

    def save_state(self) -> bool:
        """Save router state"""
        if self.linucb_router:
            return self.linucb_router.save()
        return True