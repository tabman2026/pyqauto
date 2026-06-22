"""State machine for the L5 runtime governance layer."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from enum import Enum
from typing import Any

from pyqauto.models import utc_now_iso


class SystemState(str, Enum):
    """Runtime states exposed by the governance layer."""

    NORMAL = "NORMAL"
    DEGRADED = "DEGRADED"
    READONLY = "READONLY"
    BLOCKED = "BLOCKED"
    RECOVERY = "RECOVERY"


@dataclass(frozen=True)
class StateTransition:
    """One state evaluation recorded by the runtime state machine."""

    from_state: SystemState
    to_state: SystemState
    reason: str
    changed_at: str
    trace_id: str | None = None
    changed: bool = True

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["from_state"] = self.from_state.value
        data["to_state"] = self.to_state.value
        return data


class RuntimeStateMachine:
    """Track system state and recovery transitions."""

    def __init__(self, initial_state: SystemState | str = SystemState.NORMAL) -> None:
        self._current_state = normalize_system_state(initial_state)
        self._history: list[StateTransition] = []

    @property
    def current_state(self) -> SystemState:
        return self._current_state

    def transition_to(
        self,
        next_state: SystemState | str,
        *,
        reason: str,
        trace_id: str | None = None,
    ) -> StateTransition:
        normalized_next = normalize_system_state(next_state)
        previous = self._current_state
        transition = StateTransition(
            from_state=previous,
            to_state=normalized_next,
            reason=reason,
            changed_at=utc_now_iso(),
            trace_id=trace_id,
            changed=previous != normalized_next,
        )
        self._current_state = normalized_next
        self._history.append(transition)
        return transition

    def apply_decision(
        self,
        decision_state: SystemState | str,
        *,
        reason: str,
        trace_id: str | None = None,
    ) -> StateTransition:
        """Apply a decision result, using RECOVERY after a severe state clears."""

        normalized_decision = normalize_system_state(decision_state)
        if normalized_decision == SystemState.NORMAL:
            if self._current_state in {
                SystemState.BLOCKED,
                SystemState.DEGRADED,
                SystemState.READONLY,
            }:
                return self.transition_to(
                    SystemState.RECOVERY,
                    reason=f"recovery check after {self._current_state.value}: {reason}",
                    trace_id=trace_id,
                )
            if self._current_state == SystemState.RECOVERY:
                return self.transition_to(
                    SystemState.NORMAL,
                    reason=f"recovery completed: {reason}",
                    trace_id=trace_id,
                )
        return self.transition_to(normalized_decision, reason=reason, trace_id=trace_id)

    def history(self) -> list[dict[str, Any]]:
        return [transition.to_dict() for transition in self._history]


def normalize_system_state(value: SystemState | str) -> SystemState:
    if isinstance(value, SystemState):
        return value
    return SystemState(str(value).upper())
