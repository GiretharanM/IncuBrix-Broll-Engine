import time
import logging
from enum import Enum
from typing import Callable, Any, Dict, Optional, List

logger = logging.getLogger(__name__)

class CircuitState(Enum):
    CLOSED = "CLOSED"      # Normal operation: requests pass through
    OPEN = "OPEN"          # Tripped: fail immediately without hitting provider
    HALF_OPEN = "HALF_OPEN"# Testing if provider has recovered

class CircuitBreakerOpenException(Exception):
    def __init__(self, provider_name: str, retry_after_seconds: float):
        super().__init__(f"Circuit breaker for provider '{provider_name}' is OPEN. Retry in {retry_after_seconds:.1f}s.")
        self.provider_name = provider_name
        self.retry_after_seconds = retry_after_seconds

class CircuitBreaker:
    """
    Production-grade circuit breaker to prevent cascading failures
    when external stock footage providers (Pexels, Pixabay) experience downtime or timeouts.
    """
    def __init__(
        self,
        name: str,
        failure_threshold: int = 2,
        recovery_timeout_seconds: float = 30.0,
    ):
        self.name = name
        self.failure_threshold = failure_threshold
        self.recovery_timeout_seconds = recovery_timeout_seconds
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.success_count = 0
        self.last_failure_time = 0.0
        self.last_state_change = time.time()

    def call(self, func: Callable, *args, **kwargs) -> Any:
        now = time.time()

        if self.state == CircuitState.OPEN:
            elapsed = now - self.last_failure_time
            if elapsed > self.recovery_timeout_seconds:
                logger.info(f"CircuitBreaker[{self.name}]: Recovery timeout elapsed. Probing in HALF_OPEN state.")
                self.state = CircuitState.HALF_OPEN
                self.last_state_change = now
            else:
                retry_after = self.recovery_timeout_seconds - elapsed
                logger.warning(f"CircuitBreaker[{self.name}]: Circuit is OPEN. Failing fast (retry after {retry_after:.1f}s).")
                raise CircuitBreakerOpenException(self.name, retry_after)

        try:
            result = func(*args, **kwargs)
            self._on_success()
            return result
        except Exception as e:
            self._on_failure(e)
            raise e

    def _on_success(self):
        self.failure_count = 0
        if self.state == CircuitState.HALF_OPEN:
            logger.info(f"CircuitBreaker[{self.name}]: Probe succeeded. Resetting circuit to CLOSED.")
            self.state = CircuitState.CLOSED
            self.last_state_change = time.time()
        self.success_count += 1

    def _on_failure(self, error: Exception):
        self.failure_count += 1
        self.last_failure_time = time.time()
        logger.warning(
            f"CircuitBreaker[{self.name}]: Execution failure ({self.failure_count}/{self.failure_threshold}): {error}"
        )

        if self.failure_count >= self.failure_threshold:
            if self.state != CircuitState.OPEN:
                logger.error(
                    f"CircuitBreaker[{self.name}]: Failure threshold ({self.failure_threshold}) reached. Circuit tripped to OPEN."
                )
                self.state = CircuitState.OPEN
                self.last_state_change = time.time()

    def force_open(self):
        self.state = CircuitState.OPEN
        self.last_failure_time = time.time()

    def reset(self):
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.last_failure_time = 0.0

    def get_status(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "state": self.state.value,
            "failure_count": self.failure_count,
            "success_count": self.success_count,
            "threshold": self.failure_threshold,
        }
