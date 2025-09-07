# services/orchestrator/src/tools/tool_selector.py
"""
Intelligent tool selection using Thompson Sampling with fallback to LoRA/regex
"""
from __future__ import annotations
import os
from typing import Dict, Any, Optional, List
from services.rl.online.thompson_tools import ThompsonTools

# Configuration
CANARY_SHARE = float(os.getenv("CANARY_SHARE", "0.05"))  # 5% canary traffic
ENABLE_LEARNING = os.getenv("ENABLE_RL_TOOLS", "true").lower() in ("1", "true", "yes")

class ToolSelector:
    """Intelligent tool selection with Thompson Sampling + rule-based fallback"""
    
    def __init__(self):
        self.thompson_tools = ThompsonTools() if ENABLE_LEARNING else None
        self.total_decisions = 0
        self.canary_decisions = 0
        self.learning_enabled = ENABLE_LEARNING
        
        print(f"ToolSelector initialized: RL={'enabled' if self.learning_enabled else 'disabled'}, canary={CANARY_SHARE}")

    def select_tool(
        self, 
        intent: str, 
        context: Dict[str, Any],
        available_tools: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Select tool for intent with canary testing
        Returns: {tool: str, source: str, canary: bool}
        """
        self.total_decisions += 1
        
        # Rule-based baseline tool
        baseline_tool = self._baseline_tool(intent, context, available_tools)
        
        # Decide if this request should use canary (RL tool selection)
        use_canary = self._should_use_canary()
        
        if use_canary and self.learning_enabled and self.thompson_tools:
            self.canary_decisions += 1
            
            try:
                # Use Thompson Sampling for tool selection
                rl_tool = self.thompson_tools.select(intent, available_tools)
                
                if rl_tool:
                    return {
                        "tool": rl_tool,
                        "source": "thompson",
                        "canary": True,
                        "baseline": baseline_tool,
                        "intent": intent,
                        "context": context
                    }
                else:
                    # No learned tools for this intent, use baseline
                    return {
                        "tool": baseline_tool,
                        "source": "baseline_no_rl",
                        "canary": False,
                        "intent": intent,
                        "context": context
                    }
            except Exception as e:
                print(f"Thompson tool selection failed: {e}, falling back to baseline")
                return {
                    "tool": baseline_tool,
                    "source": "baseline_fallback",
                    "canary": False,
                    "intent": intent,
                    "context": context
                }
        else:
            # Use baseline tool selection
            return {
                "tool": baseline_tool,
                "source": "baseline",
                "canary": False,
                "intent": intent,
                "context": context
            }

    def _baseline_tool(
        self, 
        intent: str, 
        context: Dict[str, Any], 
        available_tools: Optional[List[str]] = None
    ) -> str:
        """Rule-based baseline tool selection"""
        
        # Simple intent -> tool mapping
        tool_mapping = {
            "time.info": "time_tool",
            "weather.info": "weather_tool",  
            "email.send": "email_tool",
            "email.read": "email_tool",
            "calendar.create": "calendar_tool",
            "calendar.read": "calendar_tool",
            "web.search": "web_search_tool",
            "web.scrape": "web_scrape_tool",
            "home.control": "home_assistant_tool",
            "analysis": "analysis_tool",
            "code.generate": "code_tool",
            "translate": "translate_tool",
        }
        
        # Direct mapping
        if intent in tool_mapping:
            tool = tool_mapping[intent]
            if available_tools is None or tool in available_tools:
                return tool
        
        # Fallback based on intent category
        if intent.startswith("time"):
            return "time_tool"
        elif intent.startswith("weather"):
            return "weather_tool"
        elif intent.startswith("email"):
            return "email_tool"
        elif intent.startswith("calendar"):
            return "calendar_tool"
        elif intent.startswith("web"):
            return "web_search_tool"
        elif intent.startswith("home"):
            return "home_assistant_tool"
        
        # Check available tools for generic selection
        if available_tools:
            # Prefer general purpose tools
            for preferred in ["general_tool", "assistant_tool", "default_tool"]:
                if preferred in available_tools:
                    return preferred
            # Return first available tool
            return available_tools[0]
        
        # Ultimate fallback
        return "unknown"

    def _should_use_canary(self) -> bool:
        """Decide if this request should use canary tool selection"""
        import random
        return random.random() < CANARY_SHARE

    def update_from_turn(self, decision: Dict[str, Any], reward: float) -> None:
        """Update tool selector from turn result"""
        if not self.learning_enabled or not self.thompson_tools:
            return
        
        # Only update if this was a canary decision
        if not decision.get("canary", False):
            return
        
        try:
            intent = decision.get("intent", "unknown")
            tool = decision.get("tool", "unknown")
            
            self.thompson_tools.update(intent, tool, reward)
            
        except Exception as e:
            print(f"Error updating Thompson tools: {e}")

    def get_stats(self) -> Dict[str, Any]:
        """Get tool selection statistics"""
        stats = {
            "total_decisions": self.total_decisions,
            "canary_decisions": self.canary_decisions,
            "canary_rate": self.canary_decisions / max(1, self.total_decisions),
            "learning_enabled": self.learning_enabled,
            "canary_share_target": CANARY_SHARE,
        }
        
        if self.thompson_tools:
            stats["thompson_stats"] = self.thompson_tools.get_stats()
        
        return stats

    def save_state(self) -> bool:
        """Save tool selector state"""
        if self.thompson_tools:
            return self.thompson_tools.save()
        return True

    def add_tool_for_intent(self, intent: str, tool: str) -> None:
        """Add a new tool option for an intent"""
        if self.thompson_tools:
            self.thompson_tools.add_new_tool(intent, tool)

    def get_tool_recommendations(self, intent: str, k: int = 3) -> List[tuple[str, float]]:
        """Get top k tool recommendations for an intent"""
        if self.thompson_tools:
            return self.thompson_tools.get_top_tools(intent, k)
        return []