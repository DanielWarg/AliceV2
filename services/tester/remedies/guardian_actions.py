"""
Safe Remediation Actions for Alice v2
Autonomous parameter adjustment and service recovery
"""

import asyncio
import httpx
import json
import time
from typing import Dict, List, Any, Optional, Tuple
from pathlib import Path
from dataclasses import dataclass, asdict


@dataclass
class RemediationAction:
    """Record of a remediation action taken"""
    timestamp: str
    failure_type: str
    action_type: str
    parameter: str
    old_value: Any
    new_value: Any
    reasoning: str
    success: bool
    rollback_command: Optional[str] = None


class SafeRemediationEngine:
    """Applies safe, rule-based remediation for test failures"""
    
    def __init__(self, config):
        self.config = config
        self.applied_actions: List[RemediationAction] = []
        self.cooldown_until = {}  # Track cooldown periods per parameter
        
    async def apply_remediation(self, failure_type: str, failed_scenarios: List[str], 
                               test_results: List[Dict]) -> Optional[RemediationAction]:
        """Apply safe remediation for identified failure pattern"""
        
        if not self.config.REMEDIATION_ENABLED:
            print("🔒 Remediation disabled by configuration")
            return None
            
        # Check if we're in cooldown for this failure type
        if self._in_cooldown(failure_type):
            remaining = self.cooldown_until.get(failure_type, 0) - time.time()
            print(f"⏳ Remediation cooldown active for {failure_type}: {remaining:.0f}s remaining")
            return None
            
        # Check daily remediation limit
        if self._at_remediation_limit():
            print("🚫 Daily remediation limit reached")
            return None
            
        print(f"🔧 Analyzing remediation options for {failure_type}")
        
        # Route to specific remediation handler
        action = None
        if failure_type == "asr_wer_degradation":
            action = await self._remediate_asr_accuracy(test_results)
        elif failure_type == "asr_latency_high":
            action = await self._remediate_asr_latency(test_results)
        elif failure_type == "nlu_accuracy_low":
            action = await self._remediate_nlu_accuracy(test_results)
        elif failure_type == "llm_latency_high":
            action = await self._remediate_llm_latency(test_results)
        elif failure_type == "tool_failure_rate":
            action = await self._remediate_tool_failures(test_results)
        elif failure_type == "guardian_slow_response":
            action = await self._remediate_guardian_response(test_results)
        elif failure_type == "memory_usage_high":
            action = await self._remediate_memory_usage(test_results)
        elif failure_type == "vision_rtsp_issues":
            action = await self._remediate_vision_connectivity(test_results)
        else:
            print(f"❓ No remediation handler for failure type: {failure_type}")
            
        if action and action.success:
            self.applied_actions.append(action)
            self._set_cooldown(failure_type)
            print(f"✅ Remediation applied: {action.action_type}")
            return action
        elif action:
            print(f"❌ Remediation failed: {action.reasoning}")
            
        return None
    
    async def _remediate_asr_accuracy(self, test_results: List[Dict]) -> RemediationAction:
        """Improve ASR accuracy by adjusting VAD and timeout parameters"""
        
        # Analyze failure pattern
        noisy_failures = [r for r in test_results if "noise" in r.get("scenario_id", "")]
        clean_failures = [r for r in test_results if "clean" in r.get("scenario_id", "")]
        
        if len(noisy_failures) > len(clean_failures):
            # Noise-specific issues - adjust VAD sensitivity
            return await self._adjust_vad_for_noise()
        else:
            # General accuracy issues - adjust end-of-speech timeout
            return await self._adjust_eos_timeout()
    
    async def _adjust_vad_for_noise(self) -> RemediationAction:
        """Adjust Voice Activity Detection for better noise handling"""
        
        current_start = await self._get_current_parameter("vad_start_threshold", 0.5)
        current_stop = await self._get_current_parameter("vad_stop_threshold", 0.35)
        
        # Make VAD more sensitive (lower thresholds) for noisy environments
        new_start = max(current_start - 0.1, self.config.REMEDIATION_RANGES["vad_start_threshold"]["min"])
        new_stop = max(current_stop - 0.05, self.config.REMEDIATION_RANGES["vad_stop_threshold"]["min"])
        
        success = await self._set_voice_parameter("vad_start_threshold", new_start)
        if success:
            await self._set_voice_parameter("vad_stop_threshold", new_stop)
            
        return RemediationAction(
            timestamp=time.strftime("%Y-%m-%d %H:%M:%S"),
            failure_type="asr_wer_degradation",
            action_type="adjust_vad_sensitivity",
            parameter="vad_thresholds",
            old_value={"start": current_start, "stop": current_stop},
            new_value={"start": new_start, "stop": new_stop},
            reasoning=f"Lowered VAD thresholds for better noise handling",
            success=success,
            rollback_command=f"POST /api/voice/config vad_start_threshold={current_start}&vad_stop_threshold={current_stop}"
        )
    
    async def _adjust_eos_timeout(self) -> RemediationAction:
        """Adjust end-of-speech timeout for better transcript completion"""
        
        current_timeout = await self._get_current_parameter("vad_eos_timeout_ms", 700)
        
        # Increase timeout to allow for longer pauses
        new_timeout = min(current_timeout + 150, self.config.REMEDIATION_RANGES["vad_eos_timeout_ms"]["max"])
        
        success = await self._set_voice_parameter("vad_eos_timeout_ms", new_timeout)
        
        return RemediationAction(
            timestamp=time.strftime("%Y-%m-%d %H:%M:%S"),
            failure_type="asr_wer_degradation",
            action_type="increase_eos_timeout",
            parameter="vad_eos_timeout_ms",
            old_value=current_timeout,
            new_value=new_timeout,
            reasoning=f"Increased EOS timeout from {current_timeout}ms to {new_timeout}ms for better completion",
            success=success,
            rollback_command=f"POST /api/voice/config vad_eos_timeout_ms={current_timeout}"
        )
    
    async def _remediate_llm_latency(self, test_results: List[Dict]) -> RemediationAction:
        """Reduce LLM latency by optimizing context and parameters"""
        
        # Check if planner latency is the issue
        planner_slow = any("planner" in r.get("scenario_id", "") for r in test_results)
        
        if planner_slow:
            return await self._reduce_rag_context()
        else:
            return await self._optimize_llm_parameters()
    
    async def _reduce_rag_context(self) -> RemediationAction:
        """Reduce RAG context size for faster LLM processing"""
        
        current_k = await self._get_current_parameter("rag_top_k", 5)
        
        # Reduce number of retrieved documents
        new_k = max(current_k - 2, self.config.REMEDIATION_RANGES["rag_top_k"]["min"])
        
        success = await self._set_orchestrator_parameter("rag_top_k", new_k)
        
        return RemediationAction(
            timestamp=time.strftime("%Y-%m-%d %H:%M:%S"),
            failure_type="llm_latency_high",
            action_type="reduce_rag_context",
            parameter="rag_top_k", 
            old_value=current_k,
            new_value=new_k,
            reasoning=f"Reduced RAG top_k from {current_k} to {new_k} for faster processing",
            success=success,
            rollback_command=f"POST /api/orchestrator/config rag_top_k={current_k}"
        )
    
    async def _remediate_memory_usage(self, test_results: List[Dict]) -> RemediationAction:
        """Reduce memory usage by cleaning caches and reducing limits"""
        
        actions_taken = []
        
        # Clear TTS cache
        cache_cleared = await self._clear_tts_cache()
        if cache_cleared:
            actions_taken.append("tts_cache_cleared")
        
        # Reduce RAG top_k
        rag_reduced = await self._reduce_rag_context()
        if rag_reduced.success:
            actions_taken.append("rag_context_reduced")
            
        # Disable deep LLM temporarily if severe
        severe_usage = any(r.get("ram_peak_mb", 0) > self.config.MAX_RAM_MB * 0.9 for r in test_results)
        if severe_usage:
            deep_disabled = await self._disable_deep_llm_temporarily()
            if deep_disabled:
                actions_taken.append("deep_llm_disabled")
        
        success = len(actions_taken) > 0
        
        return RemediationAction(
            timestamp=time.strftime("%Y-%m-%d %H:%M:%S"),
            failure_type="memory_usage_high",
            action_type="reduce_memory_usage",
            parameter="memory_optimization",
            old_value="standard_limits",
            new_value=actions_taken,
            reasoning=f"Applied {len(actions_taken)} memory optimization actions",
            success=success,
            rollback_command="Manual rollback required - check logs"
        )
    
    async def _remediate_tool_failures(self, test_results: List[Dict]) -> RemediationAction:
        """Improve tool reliability by adjusting timeouts and enabling fallbacks"""
        
        # Identify which tools are failing
        failing_tools = set()
        for result in test_results:
            if result.get("tool_success", 1.0) < self.config.SLO_TOOL_SUCCESS_RATE:
                scenario_id = result.get("scenario_id", "")
                if "email" in scenario_id:
                    failing_tools.add("email")
                elif "calendar" in scenario_id:
                    failing_tools.add("calendar")
                elif "home_assistant" in scenario_id:
                    failing_tools.add("home_assistant")
        
        actions_taken = []
        
        # Increase timeouts for failing tools
        for tool in failing_tools:
            timeout_increased = await self._increase_tool_timeout(tool)
            if timeout_increased:
                actions_taken.append(f"{tool}_timeout_increased")
                
        # Enable circuit breaker for failing tools
        for tool in failing_tools:
            breaker_enabled = await self._enable_circuit_breaker(tool)
            if breaker_enabled:
                actions_taken.append(f"{tool}_circuit_breaker")
        
        success = len(actions_taken) > 0
        
        return RemediationAction(
            timestamp=time.strftime("%Y-%m-%d %H:%M:%S"),
            failure_type="tool_failure_rate",
            action_type="improve_tool_reliability",
            parameter="tool_resilience",
            old_value=list(failing_tools),
            new_value=actions_taken,
            reasoning=f"Applied resilience improvements for {len(failing_tools)} tools",
            success=success
        )
    
    # === Parameter Adjustment Helpers ===
    
    async def _get_current_parameter(self, param_name: str, default_value: Any) -> Any:
        """Get current parameter value from appropriate service"""
        try:
            if param_name.startswith("vad_") or param_name.startswith("asr_"):
                url = f"{self.config.VOICE_SERVICE_URL}/api/voice/config"
            elif param_name.startswith("rag_") or param_name.startswith("llm_"):
                url = f"{self.config.API_BASE}/api/orchestrator/config"
            elif param_name.startswith("guardian_"):
                url = f"{self.config.GUARDIAN_URL}/guardian/config"
            else:
                return default_value
                
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(url)
                if response.status_code == 200:
                    config_data = response.json()
                    return config_data.get(param_name, default_value)
                    
        except Exception as e:
            print(f"⚠️  Error getting parameter {param_name}: {e}")
            
        return default_value
    
    async def _set_voice_parameter(self, param_name: str, value: Any) -> bool:
        """Set voice service parameter"""
        try:
            url = f"{self.config.VOICE_SERVICE_URL}/api/voice/config"
            data = {param_name: value}
            
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.post(url, json=data)
                return response.status_code == 200
                
        except Exception as e:
            print(f"❌ Error setting voice parameter {param_name}: {e}")
            return False
    
    async def _set_orchestrator_parameter(self, param_name: str, value: Any) -> bool:
        """Set orchestrator parameter"""
        try:
            url = f"{self.config.API_BASE}/api/orchestrator/config"
            data = {param_name: value}
            
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.post(url, json=data)
                return response.status_code == 200
                
        except Exception as e:
            print(f"❌ Error setting orchestrator parameter {param_name}: {e}")
            return False
    
    async def _clear_tts_cache(self) -> bool:
        """Clear TTS cache to free memory"""
        try:
            url = f"{self.config.VOICE_SERVICE_URL}/api/tts/cache/clear"
            
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(url)
                return response.status_code == 200
                
        except Exception as e:
            print(f"❌ Error clearing TTS cache: {e}")
            return False
    
    async def _disable_deep_llm_temporarily(self) -> bool:
        """Temporarily disable deep LLM to free memory"""
        try:
            url = f"{self.config.API_BASE}/api/orchestrator/models/deep/disable"
            data = {"duration_minutes": 30, "reason": "memory_pressure"}
            
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.post(url, json=data)
                return response.status_code == 200
                
        except Exception as e:
            print(f"❌ Error disabling deep LLM: {e}")
            return False
    
    async def _increase_tool_timeout(self, tool_name: str) -> bool:
        """Increase timeout for specific tool"""
        try:
            url = f"{self.config.API_BASE}/api/tools/{tool_name}/config"
            
            # Get current timeout
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(url)
                if response.status_code == 200:
                    config = response.json()
                    current_timeout = config.get("timeout_ms", 5000)
                    new_timeout = min(current_timeout + 2000, 15000)  # Cap at 15s
                    
                    # Update timeout
                    update_data = {"timeout_ms": new_timeout}
                    response = await client.post(url, json=update_data)
                    return response.status_code == 200
                    
        except Exception as e:
            print(f"❌ Error increasing timeout for {tool_name}: {e}")
            
        return False
    
    async def _enable_circuit_breaker(self, tool_name: str) -> bool:
        """Enable circuit breaker for tool"""
        try:
            url = f"{self.config.API_BASE}/api/tools/{tool_name}/circuit-breaker"
            data = {
                "enabled": True,
                "failure_threshold": 3,
                "recovery_timeout_s": 60
            }
            
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.post(url, json=data)
                return response.status_code == 200
                
        except Exception as e:
            print(f"❌ Error enabling circuit breaker for {tool_name}: {e}")
            return False
    
    # === Safety & Rate Limiting ===
    
    def _in_cooldown(self, failure_type: str) -> bool:
        """Check if failure type is in cooldown period"""
        cooldown_end = self.cooldown_until.get(failure_type, 0)
        return time.time() < cooldown_end
    
    def _set_cooldown(self, failure_type: str):
        """Set cooldown period for failure type"""
        self.cooldown_until[failure_type] = time.time() + self.config.REMEDIATION_COOLDOWN_S
    
    def _at_remediation_limit(self) -> bool:
        """Check if we've hit the daily remediation limit"""
        today = time.strftime("%Y-%m-%d")
        today_actions = [a for a in self.applied_actions if a.timestamp.startswith(today)]
        return len(today_actions) >= self.config.MAX_REMEDIATIONS_PER_CYCLE * 24  # Rough daily limit
    
    def get_remediation_history(self) -> List[Dict]:
        """Get history of all remediation actions"""
        return [asdict(action) for action in self.applied_actions]


# === Analysis Functions ===

def analyze_failures(test_results: List[Dict]) -> Dict[str, List[str]]:
    """Analyze test failures and group by failure type"""
    failure_groups = {}
    
    for result in test_results:
        if result.get("slo_pass", True):
            continue  # Not a failure
            
        scenario_id = result.get("scenario_id", "")
        
        # Categorize failure type
        failure_type = None
        
        # ASR/Voice failures
        if result.get("wer", 0) > 0.1:  # High WER
            failure_type = "asr_wer_degradation"
        elif result.get("asr_final_ms", 0) > 1000:  # Slow ASR
            failure_type = "asr_latency_high"
            
        # NLU failures
        elif result.get("intent_accuracy", 1.0) < 0.9:
            failure_type = "nlu_accuracy_low"
            
        # LLM latency failures
        elif result.get("llm_first_ms", 0) > 2000:
            failure_type = "llm_latency_high"
            
        # Tool failures
        elif result.get("tool_success", 1.0) < 0.9:
            failure_type = "tool_failure_rate"
            
        # Guardian failures
        elif result.get("guardian_response_ms", 0) > 200:
            failure_type = "guardian_slow_response"
            
        # Memory issues
        elif result.get("ram_peak_mb", 0) > 14000:  # High memory usage
            failure_type = "memory_usage_high"
            
        # Vision issues
        elif "vision" in scenario_id or "rtsp" in scenario_id:
            failure_type = "vision_rtsp_issues"
            
        # Default categorization
        if failure_type is None:
            failure_type = "general_performance"
            
        # Group scenarios by failure type
        if failure_type not in failure_groups:
            failure_groups[failure_type] = []
        failure_groups[failure_type].append(scenario_id)
    
    return failure_groups


async def apply_safe_remediation(failure_type: str, failed_scenarios: List[str], 
                                config) -> Optional[RemediationAction]:
    """Apply safe remediation for a specific failure type"""
    engine = SafeRemediationEngine(config)
    
    # Create mock test results for remediation analysis
    test_results = [{"scenario_id": scenario, "slo_pass": False} for scenario in failed_scenarios]
    
    return await engine.apply_remediation(failure_type, failed_scenarios, test_results)