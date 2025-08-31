"""
Brownout Manager - Intelligent Feature Degradation
==================================================

Hanterar intelligent nedtrappning av funktioner före hard kill:
1. Modellbyte: gpt-oss:20b → gpt-oss:7b för svar
2. Sänk context window & RAG top_k
3. Stäng av tunga toolkedjor temporärt
4. TTS fallback till snabbare röst/prosodi
5. Feature flags för gradvis degradation

Designprinciper:
- Behåll funktionalitet men reducera resurskrav
- Gradvis degradation istället för total avbrott
- Automatisk återställning vid recovery
- Spårning av brownout-effektivitet
"""

import time
import asyncio
import logging
from datetime import datetime
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from enum import Enum
import httpx


class BrownoutLevel(Enum):
    """Brownout degradation levels"""
    NONE = 0        # Normal operation
    LIGHT = 1       # Minimal degradation
    MODERATE = 2    # Significant degradation  
    HEAVY = 3       # Maximum degradation


@dataclass
class BrownoutConfig:
    """Brownout configuration från GuardianConfig"""
    # Model settings
    model_primary: str = "gpt-oss:20b"
    model_fallback: str = "gpt-oss:7b"
    
    # Context window settings
    context_window_normal: int = 8
    context_window_reduced: int = 3
    
    # RAG settings
    rag_top_k_normal: int = 8
    rag_top_k_reduced: int = 3
    
    # Tool settings
    tools_to_disable: List[str] = None
    tools_heavy_disable: List[str] = None
    
    # Alice API settings
    alice_base_url: str = "http://localhost:8000"
    timeout_s: float = 5.0

    def __post_init__(self):
        if self.tools_to_disable is None:
            self.tools_to_disable = [
                "code_interpreter", 
                "file_search", 
                "web_search"
            ]
        if self.tools_heavy_disable is None:
            self.tools_heavy_disable = [
                "code_interpreter", 
                "file_search", 
                "web_search",
                "calendar", 
                "email"
            ]


@dataclass
class BrownoutState:
    """Current brownout state"""
    active: bool = False
    level: BrownoutLevel = BrownoutLevel.NONE
    activation_time: Optional[datetime] = None
    duration_s: float = 0.0
    config: Optional[BrownoutConfig] = None
    
    def update_duration(self):
        """Update duration if brownout is active"""
        if self.active and self.activation_time:
            self.duration_s = (datetime.now() - self.activation_time).total_seconds()


class BrownoutManager:
    """Manages intelligent system degradation during high resource usage"""
    
    def __init__(self, config: BrownoutConfig):
        self.config = config
        self.state = BrownoutState(config=config)
        self.logger = logging.getLogger("guardian.brownout")
        
    async def activate_brownout(self, level: BrownoutLevel) -> bool:
        """
        Activate brownout at specified level
        Returns True if successful, False otherwise
        """
        if level == BrownoutLevel.NONE:
            return await self.deactivate_brownout()
            
        self.logger.info(f"Activating brownout level {level.name}")
        
        try:
            success = True
            
            # Apply degradation based on level
            if level >= BrownoutLevel.LIGHT:
                # Model switch (most effective resource saving)
                if not await self._switch_model(self.config.model_fallback):
                    success = False
                    
            if level >= BrownoutLevel.MODERATE:
                # Context reduction
                if not await self._reduce_context_window(self.config.context_window_reduced):
                    success = False
                    
                # RAG reduction
                if not await self._reduce_rag_top_k(self.config.rag_top_k_reduced):
                    success = False
                    
                # Disable resource-heavy tools
                if not await self._disable_tools(self.config.tools_to_disable):
                    success = False
                    
            if level >= BrownoutLevel.HEAVY:
                # Disable additional tools
                if not await self._disable_tools(self.config.tools_heavy_disable):
                    success = False
            
            if success:
                self.state.active = True
                self.state.level = level
                self.state.activation_time = datetime.now()
                self.state.duration_s = 0.0
                self.logger.info(f"Brownout level {level.name} activated successfully")
            else:
                self.logger.error(f"Failed to fully activate brownout level {level.name}")
                
            return success
            
        except Exception as e:
            self.logger.error(f"Exception during brownout activation: {e}")
            return False
    
    async def deactivate_brownout(self) -> bool:
        """
        Deactivate brownout and restore normal operation
        Returns True if successful, False otherwise
        """
        if not self.state.active:
            return True
            
        self.logger.info("Deactivating brownout - restoring normal operation")
        
        try:
            success = True
            
            # Restore normal configuration
            if not await self._switch_model(self.config.model_primary):
                success = False
                
            if not await self._reduce_context_window(self.config.context_window_normal):
                success = False
                
            if not await self._reduce_rag_top_k(self.config.rag_top_k_normal):
                success = False
                
            # Re-enable all tools
            if not await self._enable_all_tools():
                success = False
            
            if success:
                self.state.update_duration()
                final_duration = self.state.duration_s
                
                self.state.active = False
                self.state.level = BrownoutLevel.NONE
                self.state.activation_time = None
                self.state.duration_s = 0.0
                
                self.logger.info(f"Brownout deactivated successfully after {final_duration:.1f}s")
            else:
                self.logger.error("Failed to fully deactivate brownout")
                
            return success
            
        except Exception as e:
            self.logger.error(f"Exception during brownout deactivation: {e}")
            return False
    
    def get_state(self) -> Dict[str, Any]:
        """Get current brownout state for API responses"""
        self.state.update_duration()
        return {
            "active": self.state.active,
            "level": self.state.level.name if self.state.active else "NONE",
            "activation_time": self.state.activation_time.isoformat() if self.state.activation_time else None,
            "duration_s": self.state.duration_s,
            "config": {
                "model_primary": self.config.model_primary,
                "model_fallback": self.config.model_fallback,
                "context_normal": self.config.context_window_normal,
                "context_reduced": self.config.context_window_reduced
            }
        }
    
    async def _switch_model(self, model_name: str) -> bool:
        """Switch LLM model"""
        try:
            async with httpx.AsyncClient(timeout=self.config.timeout_s) as client:
                response = await client.post(
                    f"{self.config.alice_base_url}/api/brain/model/switch",
                    json={"model": model_name}
                )
                if response.status_code == 200:
                    self.logger.debug(f"Model switched to {model_name}")
                    return True
                else:
                    self.logger.warning(f"Model switch failed: {response.status_code}")
                    return False
        except Exception as e:
            self.logger.error(f"Model switch error: {e}")
            return False
    
    async def _reduce_context_window(self, context_size: int) -> bool:
        """Reduce context window size"""
        try:
            async with httpx.AsyncClient(timeout=self.config.timeout_s) as client:
                response = await client.post(
                    f"{self.config.alice_base_url}/api/brain/context/set",
                    json={"context_window": context_size}
                )
                if response.status_code == 200:
                    self.logger.debug(f"Context window set to {context_size}")
                    return True
                else:
                    self.logger.warning(f"Context reduction failed: {response.status_code}")
                    return False
        except Exception as e:
            self.logger.error(f"Context reduction error: {e}")
            return False
    
    async def _reduce_rag_top_k(self, top_k: int) -> bool:
        """Reduce RAG top_k parameter"""
        try:
            async with httpx.AsyncClient(timeout=self.config.timeout_s) as client:
                response = await client.post(
                    f"{self.config.alice_base_url}/api/brain/rag/set",
                    json={"top_k": top_k}
                )
                if response.status_code == 200:
                    self.logger.debug(f"RAG top_k set to {top_k}")
                    return True
                else:
                    self.logger.warning(f"RAG reduction failed: {response.status_code}")
                    return False
        except Exception as e:
            self.logger.error(f"RAG reduction error: {e}")
            return False
    
    async def _disable_tools(self, tools: List[str]) -> bool:
        """Disable specified tools"""
        try:
            async with httpx.AsyncClient(timeout=self.config.timeout_s) as client:
                response = await client.post(
                    f"{self.config.alice_base_url}/api/brain/tools/disable",
                    json={"tools": tools}
                )
                if response.status_code == 200:
                    self.logger.debug(f"Tools disabled: {tools}")
                    return True
                else:
                    self.logger.warning(f"Tool disable failed: {response.status_code}")
                    return False
        except Exception as e:
            self.logger.error(f"Tool disable error: {e}")
            return False
    
    async def _enable_all_tools(self) -> bool:
        """Re-enable all tools"""
        try:
            async with httpx.AsyncClient(timeout=self.config.timeout_s) as client:
                response = await client.post(
                    f"{self.config.alice_base_url}/api/brain/tools/enable-all",
                    json={}
                )
                if response.status_code == 200:
                    self.logger.debug("All tools enabled")
                    return True
                else:
                    self.logger.warning(f"Tool enable failed: {response.status_code}")
                    return False
        except Exception as e:
            self.logger.error(f"Tool enable error: {e}")
            return False