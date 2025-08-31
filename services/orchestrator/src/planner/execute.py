"""
Planner execution logic - validate schema and execute tool calls with fallback.
"""

import json
import time
import structlog
from typing import Dict, Any, List, Optional
from pydantic import ValidationError
from .schema import Plan, ToolStep, PLANNER_SCHEMA
from ..utils.tool_errors import classify_tool_error, record_tool_call

logger = structlog.get_logger(__name__)

class PlannerExecutor:
    """Execute planner-generated plans with validation and fallback"""
    
    def __init__(self):
        # Mock tool registry (in real implementation, this would be dynamic)
        self.available_tools = {
            "calendar.create": {
                "description": "Create calendar event",
                "fallback": "email.draft"
            },
            "email.draft": {
                "description": "Draft email",
                "fallback": None
            },
            "weather.get": {
                "description": "Get weather information",
                "fallback": None
            },
            "time.get": {
                "description": "Get current time",
                "fallback": None
            }
        }
    
    def validate_plan(self, plan_data: Dict[str, Any]) -> Optional[Plan]:
        """Validate plan against schema"""
        try:
            plan = Plan(**plan_data)
            logger.info("Plan validation successful", plan_length=len(plan.steps))
            return plan
        except ValidationError as e:
            logger.warning("Plan validation failed", errors=str(e))
            return None
    
    def execute_plan(self, plan: Plan, max_steps: int = 2) -> Dict[str, Any]:
        """Execute plan steps with fallback logic"""
        results = {
            "executed_steps": [],
            "failed_steps": [],
            "fallback_used": False,
            "final_response": plan.response
        }
        
        # Execute first few steps (limit for performance)
        steps_to_execute = plan.steps[:max_steps]
        
        for i, step in enumerate(steps_to_execute):
            step_result = self._execute_step(step, i)
            results["executed_steps"].append(step_result)
            
            # If step failed and we have a fallback, try it
            if not step_result["success"] and step_result.get("fallback_attempted"):
                results["fallback_used"] = True
                logger.info("Fallback used for step", step_index=i, tool=step.tool)
        
        return results
    
    def _execute_step(self, step: ToolStep, step_index: int) -> Dict[str, Any]:
        """Execute a single step with fallback"""
        start_time = time.perf_counter()
        
        result = {
            "step_index": step_index,
            "tool": step.tool,
            "args": step.args,
            "reason": step.reason,
            "success": False,
            "response": None,
            "error": None,
            "latency_ms": 0,
            "fallback_attempted": False,
            "fallback_success": False
        }
        
        try:
            # Check if tool is available
            if step.tool not in self.available_tools:
                result["error"] = f"Tool {step.tool} not available"
                result["klass"] = "schema"
                record_tool_call(step.tool, False, "schema", 0)
                return result
            
            # Execute tool (mock implementation)
            tool_response = self._mock_tool_execution(step)
            
            if tool_response["success"]:
                result["success"] = True
                result["response"] = tool_response["data"]
                result["klass"] = None
                record_tool_call(step.tool, True, None, result["latency_ms"])
            else:
                result["error"] = tool_response["error"]
                result["klass"] = tool_response["klass"]
                record_tool_call(step.tool, False, tool_response["klass"], result["latency_ms"])
                
                # Try fallback if available
                fallback_tool = self.available_tools[step.tool].get("fallback")
                if fallback_tool:
                    result["fallback_attempted"] = True
                    fallback_result = self._execute_fallback(fallback_tool, step, step_index)
                    result["fallback_success"] = fallback_result["success"]
                    if fallback_result["success"]:
                        result["success"] = True
                        result["response"] = fallback_result["response"]
                        result["fallback_tool"] = fallback_tool
                        logger.info("Fallback successful", 
                                   original_tool=step.tool, 
                                   fallback_tool=fallback_tool)
        
        except Exception as e:
            result["error"] = str(e)
            result["klass"] = "other"
            record_tool_call(step.tool, False, "other", result["latency_ms"])
            logger.error("Step execution failed", step_index=step_index, error=str(e))
        
        finally:
            result["latency_ms"] = round((time.perf_counter() - start_time) * 1000, 1)
        
        return result
    
    def _mock_tool_execution(self, step: ToolStep) -> Dict[str, Any]:
        """Mock tool execution (replace with real tool calls)"""
        # Simulate different tool behaviors
        if step.tool == "calendar.create":
            return {
                "success": True,
                "data": {"event_id": "evt_123", "status": "created"},
                "error": None,
                "klass": None
            }
        elif step.tool == "email.draft":
            return {
                "success": True,
                "data": {"draft_id": "draft_456", "subject": "Meeting request"},
                "error": None,
                "klass": None
            }
        elif step.tool == "weather.get":
            return {
                "success": True,
                "data": {"temperature": 22, "condition": "sunny"},
                "error": None,
                "klass": None
            }
        elif step.tool == "time.get":
            return {
                "success": True,
                "data": {"time": "14:30", "date": "2025-08-31"},
                "error": None,
                "klass": None
            }
        else:
            return {
                "success": False,
                "data": None,
                "error": f"Tool {step.tool} not implemented",
                "klass": "schema"
            }
    
    def _execute_fallback(self, fallback_tool: str, original_step: ToolStep, step_index: int) -> Dict[str, Any]:
        """Execute fallback tool"""
        start_time = time.perf_counter()
        
        try:
            # Execute fallback with same args
            fallback_step = ToolStep(
                tool=fallback_tool,
                args=original_step.args,
                reason=f"Fallback for {original_step.tool}: {original_step.reason}"
            )
            
            fallback_response = self._mock_tool_execution(fallback_step)
            
            latency_ms = round((time.perf_counter() - start_time) * 1000, 1)
            record_tool_call(fallback_tool, fallback_response["success"], 
                           fallback_response.get("klass"), latency_ms)
            
            return {
                "success": fallback_response["success"],
                "response": fallback_response.get("data"),
                "error": fallback_response.get("error"),
                "latency_ms": latency_ms
            }
            
        except Exception as e:
            logger.error("Fallback execution failed", fallback_tool=fallback_tool, error=str(e))
            return {
                "success": False,
                "response": None,
                "error": str(e),
                "latency_ms": round((time.perf_counter() - start_time) * 1000, 1)
            }

# Global planner executor instance
_planner_executor: Optional[PlannerExecutor] = None

def get_planner_executor() -> PlannerExecutor:
    """Get or create global planner executor instance"""
    global _planner_executor
    if _planner_executor is None:
        _planner_executor = PlannerExecutor()
    return _planner_executor
