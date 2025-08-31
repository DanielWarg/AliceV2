"""
Alice System Guardian - Deterministisk säkerhetsdaemon
======================================================

Deterministisk övervakare som skyddar systemet från gpt-oss:20b överbelastning.
Ingen AI i säkerhetsloopen - bara hårda trösklar och verifierbara regler.

Ansvar:
- RAM/CPU/Disk monitoring (1s intervall)
- Tröskelbaserade åtgärder (soft degradation → hard kill)
- Emergency stop vid kritiska problem
- HTTP API för åtgärder

Kommunikation:
- HTTP endpoints för degrade/stop-intake
- JSON metrics loggning
- Health check på :8787
"""

import asyncio
import logging
import signal
import time
from collections import deque
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List

from .guardian_state import GuardianState, GuardianConfig
from .metrics import SystemMetrics, MetricsCollector
from .brownout_manager import BrownoutManager, BrownoutConfig, BrownoutLevel
from .kill_sequence import GracefulKillSequence, KillSequenceConfig


class Guardian:
    """Main Guardian daemon class"""
    
    def __init__(self, config: GuardianConfig):
        self.config = config
        self.logger = logging.getLogger("guardian.core")
        
        # State management
        self.state = GuardianState.NORMAL
        self.previous_state = GuardianState.NORMAL
        self.state_start_time = datetime.now()
        
        # Metrics collection
        self.metrics_collector = MetricsCollector()
        self.metrics_history: deque = deque(maxlen=config.flap_detection_window)
        
        # Hysteresis tracking
        self.soft_trigger_measurements: deque = deque(maxlen=config.measurement_window)
        self.recovery_start_time: Optional[datetime] = None
        
        # Kill sequence management
        self.kill_times: List[datetime] = []
        self.lockdown_until: Optional[datetime] = None
        
        # Components
        brownout_config = BrownoutConfig(
            model_primary=config.brownout_model_primary,
            model_fallback=config.brownout_model_fallback,
            context_window_normal=config.brownout_context_window,
            context_window_reduced=config.brownout_context_reduced,
            rag_top_k_normal=config.brownout_rag_top_k,
            rag_top_k_reduced=config.brownout_rag_reduced,
            alice_base_url=config.alice_base_url
        )
        self.brownout_manager = BrownoutManager(brownout_config)
        
        kill_config = KillSequenceConfig(
            alice_base_url=config.alice_base_url,
            health_check_url=f"{config.ollama_base_url}/api/health"
        )
        self.kill_sequence = GracefulKillSequence(kill_config)
        
        # Runtime flags
        self.running = False
        self.shutdown_requested = False
        
    async def start(self):
        """Start Guardian daemon"""
        self.logger.info("Starting Alice Guardian daemon")
        self.running = True
        
        # Setup signal handlers
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
        
        try:
            await self._main_loop()
        except Exception as e:
            self.logger.error(f"Guardian main loop error: {e}")
        finally:
            self.running = False
            self.logger.info("Guardian daemon stopped")
    
    def _signal_handler(self, signum, frame):
        """Handle shutdown signals"""
        self.logger.info(f"Received signal {signum}, shutting down...")
        self.shutdown_requested = True
    
    async def _main_loop(self):
        """Main monitoring loop"""
        while self.running and not self.shutdown_requested:
            try:
                # Collect system metrics
                metrics = self.metrics_collector.collect_metrics()
                self.metrics_history.append(metrics)
                
                # Check lockdown status
                if self._is_in_lockdown():
                    await asyncio.sleep(self.config.poll_interval_s)
                    continue
                
                # Evaluate system state
                new_state = await self._evaluate_system_state(metrics)
                
                # Handle state transitions
                if new_state != self.state:
                    await self._transition_to_state(new_state, metrics)
                
                # Update state duration
                self._update_state_duration()
                
                # Log metrics (structured logging for observability)
                if self.config.metrics_enabled:
                    self._log_metrics(metrics)
                
                await asyncio.sleep(self.config.poll_interval_s)
                
            except Exception as e:
                self.logger.error(f"Error in main loop: {e}")
                await asyncio.sleep(self.config.poll_interval_s)
    
    async def _evaluate_system_state(self, metrics: SystemMetrics) -> GuardianState:
        """Evaluate what state we should be in based on current metrics"""
        
        # Hard triggers (immediate response)
        if (metrics.ram_pct >= self.config.ram_hard_pct * 100 or 
            metrics.cpu_pct >= self.config.cpu_hard_pct * 100 or
            metrics.disk_pct >= self.config.disk_hard_pct * 100 or
            (metrics.temp_c and metrics.temp_c >= self.config.temp_hard_c)):
            return GuardianState.EMERGENCY
        
        # Soft triggers (with hysteresis)
        is_soft_trigger = (metrics.ram_pct >= self.config.ram_soft_pct * 100 or
                          metrics.cpu_pct >= self.config.cpu_soft_pct * 100)
        
        if is_soft_trigger:
            self.soft_trigger_measurements.append(True)
        else:
            self.soft_trigger_measurements.append(False)
        
        # Check for soft trigger activation
        if len(self.soft_trigger_measurements) == self.config.measurement_window:
            if all(self.soft_trigger_measurements):
                if self.state == GuardianState.NORMAL:
                    return GuardianState.BROWNOUT
                elif self.state == GuardianState.BROWNOUT:
                    return GuardianState.DEGRADED
        
        # Check for recovery
        is_recovery = (metrics.ram_pct <= self.config.ram_recovery_pct * 100 and
                      metrics.cpu_pct <= self.config.cpu_recovery_pct * 100)
        
        if is_recovery:
            if self.recovery_start_time is None:
                self.recovery_start_time = datetime.now()
            elif (datetime.now() - self.recovery_start_time).total_seconds() >= self.config.recovery_window_s:
                # Sufficient recovery time has passed
                if self.state in [GuardianState.BROWNOUT, GuardianState.DEGRADED]:
                    return GuardianState.NORMAL
        else:
            # Reset recovery timer if conditions worsen
            self.recovery_start_time = None
        
        # No state change
        return self.state
    
    async def _transition_to_state(self, new_state: GuardianState, metrics: SystemMetrics):
        """Handle transition to new state"""
        old_state = self.state
        self.logger.info(f"State transition: {old_state.value} → {new_state.value}")
        
        # Update state tracking
        self.previous_state = self.state
        self.state = new_state
        self.state_start_time = datetime.now()
        
        # Reset recovery timer on state change
        self.recovery_start_time = None
        
        # Execute state-specific actions
        if new_state == GuardianState.BROWNOUT:
            await self._activate_brownout(BrownoutLevel.MODERATE)
            
        elif new_state == GuardianState.DEGRADED:
            await self._activate_brownout(BrownoutLevel.HEAVY)
            
        elif new_state == GuardianState.EMERGENCY:
            await self._execute_emergency_procedure(metrics)
            
        elif new_state == GuardianState.NORMAL:
            await self._restore_normal_operation()
    
    async def _activate_brownout(self, level: BrownoutLevel):
        """Activate brownout at specified level"""
        if self.config.enable_brownout:
            success = await self.brownout_manager.activate_brownout(level)
            if success:
                self.logger.info(f"Brownout level {level.name} activated")
            else:
                self.logger.error(f"Failed to activate brownout level {level.name}")
        else:
            self.logger.info("Brownout disabled in configuration")
    
    async def _execute_emergency_procedure(self, metrics: SystemMetrics):
        """Execute emergency kill sequence"""
        self.logger.warning(f"EMERGENCY: RAM={metrics.ram_pct:.1f}% CPU={metrics.cpu_pct:.1f}%")
        
        # Check kill rate limiting
        if not self._can_execute_kill():
            self.logger.error("Kill rate limit exceeded, entering lockdown")
            self.state = GuardianState.LOCKDOWN
            self.lockdown_until = datetime.now() + timedelta(seconds=self.config.lockdown_duration_s)
            return
        
        # Execute kill sequence
        if self.config.enable_kill_ollama:
            success = await self.kill_sequence.execute_kill_sequence()
            if success:
                self.logger.info("Emergency kill sequence completed successfully")
                # Record kill time
                self.kill_times.append(datetime.now())
                # Return to normal after successful kill
                self.state = GuardianState.NORMAL
                self.state_start_time = datetime.now()
            else:
                self.logger.error("Emergency kill sequence failed")
                # Escalate to lockdown on failure
                self.state = GuardianState.LOCKDOWN
                self.lockdown_until = datetime.now() + timedelta(seconds=self.config.lockdown_duration_s)
        else:
            self.logger.warning("Kill sequence disabled in configuration")
    
    async def _restore_normal_operation(self):
        """Restore normal operation from degraded states"""
        self.logger.info("Restoring normal operation")
        
        # Deactivate brownout
        if self.brownout_manager.state.active:
            success = await self.brownout_manager.deactivate_brownout()
            if success:
                self.logger.info("Normal operation restored")
            else:
                self.logger.warning("Failed to fully restore normal operation")
    
    def _can_execute_kill(self) -> bool:
        """Check if we can execute kill based on rate limiting"""
        now = datetime.now()
        
        # Clean old kill times outside the long window
        cutoff_time = now - timedelta(seconds=self.config.kill_cooldown_long_s)
        self.kill_times = [t for t in self.kill_times if t > cutoff_time]
        
        # Check short cooldown (time since last kill)
        if self.kill_times:
            last_kill = max(self.kill_times)
            short_cooldown = timedelta(seconds=self.config.kill_cooldown_short_s)
            if now - last_kill < short_cooldown:
                return False
        
        # Check max kills in long window
        if len(self.kill_times) >= self.config.max_kills_per_window:
            return False
        
        return True
    
    def _is_in_lockdown(self) -> bool:
        """Check if system is in lockdown"""
        if self.lockdown_until is None:
            return False
        
        if datetime.now() < self.lockdown_until:
            return True
        else:
            # Lockdown expired, reset
            self.lockdown_until = None
            if self.state == GuardianState.LOCKDOWN:
                self.logger.info("Lockdown period expired, returning to normal")
                self.state = GuardianState.NORMAL
                self.state_start_time = datetime.now()
            return False
    
    def _update_state_duration(self):
        """Update metrics with current state duration"""
        if hasattr(self.metrics_history, '__iter__') and self.metrics_history:
            latest_metrics = self.metrics_history[-1]
            latest_metrics.degraded = self.state in [GuardianState.DEGRADED, GuardianState.EMERGENCY, GuardianState.LOCKDOWN]
            latest_metrics.emergency_mode = self.state in [GuardianState.EMERGENCY, GuardianState.LOCKDOWN]
            latest_metrics.intake_blocked = self.state in [GuardianState.EMERGENCY, GuardianState.LOCKDOWN]
    
    def _log_metrics(self, metrics: SystemMetrics):
        """Log structured metrics for observability"""
        log_data = {
            "timestamp": metrics.timestamp,
            "guardian_state": self.state.value,
            "state_duration_s": (datetime.now() - self.state_start_time).total_seconds(),
            "ram_pct": metrics.ram_pct,
            "cpu_pct": metrics.cpu_pct,
            "disk_pct": metrics.disk_pct,
            "temp_c": metrics.temp_c,
            "ollama_pids": len(metrics.ollama_pids),
            "brownout_active": self.brownout_manager.state.active,
            "brownout_level": self.brownout_manager.state.level.name if self.brownout_manager.state.active else None
        }
        self.logger.info("metrics", extra=log_data)
    
    def get_status(self) -> Dict[str, Any]:
        """Get complete Guardian status for API responses"""
        now = datetime.now()
        uptime_s = (now - self.state_start_time).total_seconds()
        
        # Get latest metrics
        latest_metrics = self.metrics_history[-1] if self.metrics_history else None
        
        status = {
            "status": self.state.value,
            "previous_state": self.previous_state.value,
            "uptime_s": uptime_s,
            "state_duration_s": (now - self.state_start_time).total_seconds(),
            "metrics": {
                "ram_pct": latest_metrics.ram_pct if latest_metrics else 0,
                "cpu_pct": latest_metrics.cpu_pct if latest_metrics else 0,
                "disk_pct": latest_metrics.disk_pct if latest_metrics else 0,
                "temp_c": latest_metrics.temp_c if latest_metrics else None,
                "ram_gb": latest_metrics.ram_gb if latest_metrics else 0,
                "ollama_pids": latest_metrics.ollama_pids if latest_metrics else [],
                "degraded": self.state in [GuardianState.DEGRADED, GuardianState.EMERGENCY, GuardianState.LOCKDOWN],
                "intake_blocked": self.state in [GuardianState.EMERGENCY, GuardianState.LOCKDOWN],
                "emergency_mode": self.state in [GuardianState.EMERGENCY, GuardianState.LOCKDOWN]
            }
        }
        
        # Add killswitch info
        status["killswitch"] = self.kill_sequence.get_status()
        
        # Add brownout info
        if self.brownout_manager.state.active:
            status["brownout"] = self.brownout_manager.get_state()
        
        return status