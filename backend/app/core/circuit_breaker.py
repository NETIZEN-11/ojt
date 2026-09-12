"""Circuit Breaker pattern implementation for external provider failures."""

import asyncio
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, TypeVar

from app.core.config import get_settings
from app.core.logging import get_logger

settings = get_settings()
logger = get_logger(__name__)

T = TypeVar("T")


class CircuitState(Enum):
    CLOSED = "closed"      # Normal operation, requests go through
    OPEN = "open"          # Failing, requests blocked
    HALF_OPEN = "half_open"  # Testing if service recovered


@dataclass
class CircuitBreakerConfig:
    failure_threshold: int = 5          # Number of failures before opening
    success_threshold: int = 2          # Successes needed to close from half-open
    timeout: float = 30.0               # Seconds before trying half-open
    excluded_exceptions: tuple[type[Exception], ...] = ()  # Exceptions that don't count as failures


@dataclass
class CircuitBreakerStats:
    total_calls: int = 0
    successful_calls: int = 0
    failed_calls: int = 0
    consecutive_failures: int = 0
    consecutive_successes: int = 0
    last_failure_time: datetime | None = None
    last_success_time: datetime | None = None
    state_changes: list[dict[str, Any]] = field(default_factory=list)


class CircuitBreaker:
    def __init__(self, name: str, config: CircuitBreakerConfig | None = None):
        self.name = name
        self.config = config or CircuitBreakerConfig()
        self.state = CircuitState.CLOSED
        self.stats = CircuitBreakerStats()
        self._lock = asyncio.Lock()

    async def call(self, func: Callable[..., T], *args: Any, **kwargs: Any) -> T:
        """Execute function with circuit breaker protection."""
        async with self._lock:
            if self.state == CircuitState.OPEN:
                if self._should_attempt_reset():
                    await self._transition_to_half_open()
                else:
                    raise CircuitBreakerOpenError(
                        f"Circuit breaker '{self.name}' is OPEN. "
                        f"Retry after {self.config.timeout}s"
                    )

        try:
            if asyncio.iscoroutinefunction(func):
                result = await func(*args, **kwargs)
            else:
                result = func(*args, **kwargs)
            
            await self._on_success()
            return result
            
        except self.config.excluded_exceptions:
            raise
        except Exception as e:
            await self._on_failure()
            raise

    def _should_attempt_reset(self) -> bool:
        if self.stats.last_failure_time is None:
            return True
        elapsed = (datetime.utcnow() - self.stats.last_failure_time).total_seconds()
        return elapsed >= self.config.timeout

    async def _transition_to_half_open(self):
        logger.info("circuit_breaker_half_open", name=self.name)
        self.state = CircuitState.HALF_OPEN
        self.stats.consecutive_successes = 0
        self._record_state_change(CircuitState.HALF_OPEN)

    async def _on_success(self):
        async with self._lock:
            self.stats.total_calls += 1
            self.stats.successful_calls += 1
            self.stats.consecutive_failures = 0
            self.stats.last_success_time = datetime.utcnow()

            if self.state == CircuitState.HALF_OPEN:
                self.stats.consecutive_successes += 1
                if self.stats.consecutive_successes >= self.config.success_threshold:
                    await self._transition_to_closed()

    async def _on_failure(self):
        async with self._lock:
            self.stats.total_calls += 1
            self.stats.failed_calls += 1
            self.stats.consecutive_failures += 1
            self.stats.consecutive_successes = 0
            self.stats.last_failure_time = datetime.utcnow()

            if self.state == CircuitState.HALF_OPEN:
                # Any failure in half-open goes back to open
                await self._transition_to_open()
            elif self.state == CircuitState.CLOSED:
                if self.stats.consecutive_failures >= self.config.failure_threshold:
                    await self._transition_to_open()

    async def _transition_to_open(self):
        logger.warning("circuit_breaker_opened", name=self.name, 
                      consecutive_failures=self.stats.consecutive_failures)
        self.state = CircuitState.OPEN
        self._record_state_change(CircuitState.OPEN)

    async def _transition_to_closed(self):
        logger.info("circuit_breaker_closed", name=self.name)
        self.state = CircuitState.CLOSED
        self.stats.consecutive_failures = 0
        self._record_state_change(CircuitState.CLOSED)

    def _record_state_change(self, new_state: CircuitState):
        self.stats.state_changes.append({
            "from_state": self.state.value if hasattr(self, '_prev_state') else "unknown",
            "to_state": new_state.value,
            "timestamp": datetime.utcnow().isoformat(),
        })
        self._prev_state = self.state

    def get_stats(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "state": self.state.value,
            "total_calls": self.stats.total_calls,
            "successful_calls": self.stats.successful_calls,
            "failed_calls": self.stats.failed_calls,
            "consecutive_failures": self.stats.consecutive_failures,
            "consecutive_successes": self.stats.consecutive_successes,
            "success_rate": (
                self.stats.successful_calls / self.stats.total_calls 
                if self.stats.total_calls > 0 else 0
            ),
            "last_failure": self.stats.last_failure_time.isoformat() if self.stats.last_failure_time else None,
            "last_success": self.stats.last_success_time.isoformat() if self.stats.last_success_time else None,
        }

    def is_available(self) -> bool:
        return self.state != CircuitState.OPEN or self._should_attempt_reset()

    async def reset(self):
        """Manually reset the circuit breaker to closed state."""
        async with self._lock:
            await self._transition_to_closed()


class CircuitBreakerOpenError(Exception):
    """Raised when circuit breaker is open and call is rejected."""
    pass


class CircuitBreakerRegistry:
    """Registry for managing multiple circuit breakers."""
    
    def __init__(self):
        self._breakers: dict[str, CircuitBreaker] = {}
        self._lock = asyncio.Lock()

    async def get_or_create(
        self, 
        name: str, 
        config: CircuitBreakerConfig | None = None
    ) -> CircuitBreaker:
        async with self._lock:
            if name not in self._breakers:
                self._breakers[name] = CircuitBreaker(name, config)
            return self._breakers[name]

    async def get(self, name: str) -> CircuitBreaker | None:
        return self._breakers.get(name)

    async def get_all_stats(self) -> dict[str, dict[str, Any]]:
        return {name: breaker.get_stats() for name, breaker in self._breakers.items()}

    async def reset_all(self):
        for breaker in self._breakers.values():
            await breaker.reset()

    async def remove(self, name: str) -> bool:
        async with self._lock:
            if name in self._breakers:
                del self._breakers[name]
                return True
            return False


# Global registry instance
circuit_breaker_registry = CircuitBreakerRegistry()


def circuit_breaker(name: str, config: CircuitBreakerConfig | None = None):
    """Decorator to add circuit breaker protection to a function."""
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        async def wrapper(*args: Any, **kwargs: Any) -> T:
            breaker = await circuit_breaker_registry.get_or_create(name, config)
            return await breaker.call(func, *args, **kwargs)
        return wrapper
    return decorator