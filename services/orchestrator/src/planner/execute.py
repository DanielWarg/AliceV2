"""
Planner execution logic - validate schema and execute tool calls with fallback.
"""

import time
from typing import Any, Dict, Optional

import structlog
from pydantic import ValidationError

from ..tools.mcp_registry import get_mcp_registry
from ..utils.tool_errors import record_tool_call
from .schema import Plan, ToolStep

logger = structlog.get_logger(__name__)


class PlannerExecutor:
    """Execute planner-generated plans with validation and fallback"""

    def __init__(self):
        # Use MCP tool registry
        self.mcp_registry = get_mcp_registry()

        # Timeout settings for robust execution
        self.planner_timeout_ms = 600  # 600ms for planner generation
        self.tool_timeout_ms = 400  # 400ms for tool execution
        self.total_timeout_ms = 1500  # 1500ms total budget

        # Circuit breaker settings
        self.max_tool_failures = 3
        self.tool_failure_window_s = 30
        self.tool_failure_count = 0
        self.last_tool_failure_time = 0

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
        """Execute plan steps with fallback logic and timeout protection"""
        start_time = time.perf_counter()

        results = {
            "executed_steps": [],
            "failed_steps": [],
            "fallback_used": False,
            "final_response": plan.response,
            "total_time_ms": 0,
            "timeout_exceeded": False,
        }

        # Execute first few steps (limit for performance)
        steps_to_execute = plan.steps[:max_steps]

        for i, step in enumerate(steps_to_execute):
            # Check total timeout
            elapsed_time = (time.perf_counter() - start_time) * 1000
            if elapsed_time > self.total_timeout_ms:
                logger.warning(
                    "Total execution timeout exceeded",
                    elapsed_time_ms=elapsed_time,
                    total_timeout_ms=self.total_timeout_ms,
                )
                results["timeout_exceeded"] = True
                break

            step_result = self._execute_step(step, i)
            results["executed_steps"].append(step_result)

            # If step failed and we have a fallback, try it
            if not step_result["success"] and step_result.get("fallback_attempted"):
                results["fallback_used"] = True
                logger.info("Fallback used for step", step_index=i, tool=step.tool)

        results["total_time_ms"] = (time.perf_counter() - start_time) * 1000

        return results

    def _execute_step(self, step: ToolStep, step_index: int) -> Dict[str, Any]:
        """Execute a single step with fallback and timeout protection"""
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
            "fallback_success": False,
            "timeout_exceeded": False,
        }

        try:
            # Check if tool is available in MCP registry
            if not self.mcp_registry.get_tool_schema(step.tool):
                result["error"] = f"Tool {step.tool} not available"
                result["klass"] = "schema"
                record_tool_call(step.tool, False, "schema", 0)
                return result

            # Execute tool using MCP registry with timeout
            tool_response = self.mcp_registry.execute_tool(step.tool, step.args)

            result["latency_ms"] = (time.perf_counter() - start_time) * 1000

            # Check tool timeout
            if result["latency_ms"] > self.tool_timeout_ms:
                result["timeout_exceeded"] = True
                result["error"] = (
                    f"Tool execution timeout ({result['latency_ms']:.0f}ms > {self.tool_timeout_ms}ms)"
                )
                result["klass"] = "timeout"
                self._record_tool_failure()
                record_tool_call(step.tool, False, "timeout", result["latency_ms"])
                return result

            if tool_response["success"]:
                result["success"] = True
                result["response"] = tool_response["data"]
                result["klass"] = None
                self._reset_tool_failure_count()
                record_tool_call(step.tool, True, None, result["latency_ms"])
            else:
                result["error"] = tool_response["error"]
                result["klass"] = tool_response.get("klass", "unknown")
                self._record_tool_failure()
                record_tool_call(
                    step.tool, False, result["klass"], result["latency_ms"]
                )

                # Try fallback if available and circuit breaker not open
                if not self._is_tool_circuit_open():
                    fallback_tool = self.mcp_registry.get_tool_fallback(step.tool)
                    if fallback_tool:
                        result["fallback_attempted"] = True
                        fallback_result = self._execute_fallback(
                            fallback_tool, step, step_index
                        )
                        result["fallback_success"] = fallback_result["success"]
                        if fallback_result["success"]:
                            result["success"] = True
                            result["response"] = fallback_result["response"]
                            result["error"] = None
                            logger.info(
                                "Fallback successful",
                                original_tool=step.tool,
                                fallback_tool=fallback_tool,
                            )
                        else:
                            logger.warning(
                                "Fallback failed",
                                original_tool=step.tool,
                                fallback_tool=fallback_tool,
                                error=fallback_result["error"],
                            )
                else:
                    logger.warning(
                        "Tool circuit breaker open, skipping fallback", tool=step.tool
                    )

        except Exception as e:
            result["latency_ms"] = (time.perf_counter() - start_time) * 1000
            result["error"] = str(e)
            result["klass"] = "exception"
            self._record_tool_failure()
            record_tool_call(step.tool, False, "exception", result["latency_ms"])
            logger.error(
                "Step execution failed",
                step_index=step_index,
                tool=step.tool,
                error=str(e),
            )

        return result

    def _execute_fallback(
        self, fallback_tool: str, original_step: ToolStep, step_index: int
    ) -> Dict[str, Any]:
        """Execute fallback tool with timeout protection"""
        start_time = time.perf_counter()

        result = {"success": False, "response": None, "error": None, "latency_ms": 0}

        try:
            # Execute fallback with reduced timeout
            fallback_timeout_ms = min(
                self.tool_timeout_ms, 300
            )  # Max 300ms for fallback

            fallback_response = self.mcp_registry.execute_tool(
                fallback_tool, original_step.args
            )

            result["latency_ms"] = (time.perf_counter() - start_time) * 1000

            # Check fallback timeout
            if result["latency_ms"] > fallback_timeout_ms:
                result["error"] = (
                    f"Fallback timeout ({result['latency_ms']:.0f}ms > {fallback_timeout_ms}ms)"
                )
                return result

            if fallback_response["success"]:
                result["success"] = True
                result["response"] = fallback_response["data"]
            else:
                result["error"] = fallback_response["error"]

        except Exception as e:
            result["latency_ms"] = (time.perf_counter() - start_time) * 1000
            result["error"] = str(e)
            logger.error(
                "Fallback execution failed",
                fallback_tool=fallback_tool,
                original_tool=original_step.tool,
                error=str(e),
            )

        return result

    def _record_tool_failure(self):
        """Record a tool failure for circuit breaker"""
        current_time = time.time()

        # Reset if outside window
        if current_time - self.last_tool_failure_time > self.tool_failure_window_s:
            self.tool_failure_count = 0

        self.tool_failure_count += 1
        self.last_tool_failure_time = current_time

        logger.warning(
            "Tool failure recorded",
            failure_count=self.tool_failure_count,
            max_failures=self.max_tool_failures,
        )

    def _reset_tool_failure_count(self):
        """Reset tool failure count on success"""
        self.tool_failure_count = 0

    def _is_tool_circuit_open(self) -> bool:
        """Check if tool circuit breaker is open"""
        return self.tool_failure_count >= self.max_tool_failures


# Global planner executor instance
_planner_executor: Optional[PlannerExecutor] = None


def get_planner_executor() -> PlannerExecutor:
    """Get or create global planner executor instance"""
    global _planner_executor
    if _planner_executor is None:
        _planner_executor = PlannerExecutor()
    return _planner_executor
