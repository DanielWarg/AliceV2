"""
Circuit Breaker pattern implementation for service resilience.
Prevents cascading failures by cutting off calls to failing services.
"""

import time
import structlog
from typing import Optional, Callable, Any
from enum import Enum
from dataclasses import dataclass

logger = structlog.get_logger(__name__)

class CircuitState(Enum):
    CLOSED = "closed"      # Normal operation
    OPEN = "open"          # Service is failing, calls blocked
    HALF_OPEN = "half_open" # Testing if service recovered

@dataclass
class CircuitBreakerConfig:
    failure_threshold: int = 3          # Failures before opening
    recovery_timeout: float = 60.0      # Seconds before trying again
    success_threshold: int = 2          # Successes to close from half-open
    timeout: float = 2.0               # Call timeout in seconds

class CircuitBreaker:
    """Circuit breaker for protecting against failing services"""
    
    def __init__(self, name: str, config: Optional[CircuitBreakerConfig] = None):
        self.name = name
        self.config = config or CircuitBreakerConfig()
        
        # State tracking
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.success_count = 0
        self.last_failure_time = 0.0
        self.last_call_time = 0.0
        
        logger.info("Circuit breaker initialized", 
                   name=name, 
                   threshold=self.config.failure_threshold,
                   timeout=self.config.recovery_timeout)
    
    def call(self, func: Callable, *args, **kwargs) -> Any:
        """Execute function with circuit breaker protection"""
        self.last_call_time = time.time()
        
        # Check if circuit should transition states
        self._update_state()
        
        if self.state == CircuitState.OPEN:
            logger.warn("Circuit breaker OPEN - call blocked", 
                       name=self.name,
                       failures=self.failure_count)
            raise CircuitOpenError(f"Circuit {self.name} is OPEN")
        
        # Execute the call
        try:
            result = func(*args, **kwargs)
            self._on_success()
            return result
            
        except Exception as e:
            self._on_failure(e)
            raise
    
    def _update_state(self):
        """Update circuit state based on current conditions"""
        now = time.time()
        
        if self.state == CircuitState.OPEN:
            # Check if recovery timeout has passed
            if now - self.last_failure_time >= self.config.recovery_timeout:
                self.state = CircuitState.HALF_OPEN
                self.success_count = 0
                logger.info("Circuit breaker transitioning to HALF_OPEN", 
                           name=self.name)
        
        elif self.state == CircuitState.HALF_OPEN:
            # In half-open, we let limited calls through
            # Success/failure counts will determine next state
            pass
    
    def _on_success(self):
        """Handle successful call"""
        if self.state == CircuitState.HALF_OPEN:
            self.success_count += 1
            if self.success_count >= self.config.success_threshold:
                self.state = CircuitState.CLOSED
                self.failure_count = 0
                self.success_count = 0
                logger.info("Circuit breaker CLOSED - service recovered", 
                           name=self.name)
        else:
            # Reset failure count on success in closed state
            self.failure_count = 0
    
    def _on_failure(self, error: Exception):
        """Handle failed call"""
        self.failure_count += 1
        self.last_failure_time = time.time()
        
        logger.warn("Circuit breaker recorded failure", 
                   name=self.name,
                   failures=self.failure_count,
                   error=str(error))
        
        if self.state in [CircuitState.CLOSED, CircuitState.HALF_OPEN]:
            if self.failure_count >= self.config.failure_threshold:
                self.state = CircuitState.OPEN
                logger.error("Circuit breaker OPENED - service failing", 
                           name=self.name,
                           failures=self.failure_count)
    
    def get_stats(self) -> dict:
        """Get circuit breaker statistics"""
        return {
            "name": self.name,
            "state": self.state.value,
            "failure_count": self.failure_count,
            "success_count": self.success_count,
            "last_failure_time": self.last_failure_time,
            "last_call_time": self.last_call_time,
            "time_since_last_failure": time.time() - self.last_failure_time if self.last_failure_time else 0
        }

class CircuitOpenError(Exception):
    """Exception raised when circuit breaker is open"""
    pass

# Global circuit breakers for common services
_circuit_breakers = {}

def get_circuit_breaker(name: str, config: Optional[CircuitBreakerConfig] = None) -> CircuitBreaker:
    """Get or create a circuit breaker for a service"""
    if name not in _circuit_breakers:
        _circuit_breakers[name] = CircuitBreaker(name, config)
    return _circuit_breakers[name]

def get_all_circuit_stats() -> list:
    """Get statistics for all circuit breakers"""
    return [cb.get_stats() for cb in _circuit_breakers.values()]