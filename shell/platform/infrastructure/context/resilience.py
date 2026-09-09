"""Polityki retry i circuit breaker dla komunikacji między usługami."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum


class CircuitState(StrEnum):
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


class CircuitOpenError(RuntimeError):
    """Rzucony, gdy obwód zależności jest otwarty i żądanie odrzucane lokalnie."""


@dataclass(frozen=True, slots=True)
class RetryPolicy:
    max_attempts: int = 1
    initial_delay: float = 0.1
    max_delay: float = 1.0
    jitter: float = 0.0
    retryable_methods: frozenset[str] = field(default_factory=lambda: frozenset({"GET"}))
    retryable_statuses: frozenset[int] = field(
        default_factory=lambda: frozenset({429, 502, 503, 504})
    )

    def __post_init__(self) -> None:
        if self.max_attempts < 1:
            raise ValueError("max_attempts musi być co najmniej 1")
        if self.initial_delay < 0 or self.max_delay < 0 or self.jitter < 0:
            raise ValueError("opóźnienia retry i jitter nie mogą być ujemne")
        if self.max_delay < self.initial_delay:
            raise ValueError("max_delay nie może być mniejsze niż initial_delay")


@dataclass(frozen=True, slots=True)
class CircuitBreakerPolicy:
    failure_threshold: int = 5
    recovery_timeout: float = 15.0

    def __post_init__(self) -> None:
        if self.failure_threshold < 1:
            raise ValueError("failure_threshold musi być co najmniej 1")
        if self.recovery_timeout < 0:
            raise ValueError("recovery_timeout nie może być ujemne")


class CircuitBreaker:
    def __init__(self, policy: CircuitBreakerPolicy) -> None:
        self._policy = policy
        self._state = CircuitState.CLOSED
        self._failures = 0
        self._opened_at: float | None = None
        self._half_open_probe = False

    @property
    def state(self) -> CircuitState:
        return self._state

    def allow_request(self, now: float) -> bool:
        if self._state is CircuitState.CLOSED:
            return True
        if self._state is CircuitState.OPEN:
            if self._opened_at is None or now - self._opened_at < self._policy.recovery_timeout:
                return False
            self._state = CircuitState.HALF_OPEN
        if self._state is CircuitState.HALF_OPEN:
            if self._half_open_probe:
                return False
            self._half_open_probe = True
            return True
        return False

    def record_success(self) -> None:
        self._state = CircuitState.CLOSED
        self._failures = 0
        self._opened_at = None
        self._half_open_probe = False

    def record_failure(self, now: float) -> None:
        self._half_open_probe = False
        if self._state is CircuitState.HALF_OPEN:
            self._open(now)
            return
        self._failures += 1
        if self._failures >= self._policy.failure_threshold:
            self._open(now)

    def _open(self, now: float) -> None:
        self._state = CircuitState.OPEN
        self._opened_at = now
        self._failures = 0