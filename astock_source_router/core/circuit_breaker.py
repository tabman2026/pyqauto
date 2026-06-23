from __future__ import annotations

import time
from dataclasses import dataclass


@dataclass(slots=True)
class CircuitState:
    failures: int = 0
    opened_until: float = 0.0


class CircuitBreaker:
    """Per source-feature circuit breaker."""

    def __init__(self, failure_threshold: int = 3, cooldown_seconds: int = 300) -> None:
        self.failure_threshold = failure_threshold
        self.cooldown_seconds = cooldown_seconds
        self._states: dict[tuple[str, str], CircuitState] = {}

    def allow(self, source: str, feature: str) -> bool:
        state = self._states.get((source, feature))
        if state is None:
            return True
        if state.opened_until <= 0:
            return True
        return time.time() >= state.opened_until

    def record_success(self, source: str, feature: str) -> None:
        self._states[(source, feature)] = CircuitState()

    def record_failure(self, source: str, feature: str) -> None:
        key = (source, feature)
        state = self._states.setdefault(key, CircuitState())
        state.failures += 1
        if state.failures >= self.failure_threshold:
            state.opened_until = time.time() + self.cooldown_seconds

    def snapshot(self) -> dict[str, dict[str, float | int]]:
        return {
            f"{source}:{feature}": {
                "failures": state.failures,
                "opened_until": state.opened_until,
            }
            for (source, feature), state in self._states.items()
        }
