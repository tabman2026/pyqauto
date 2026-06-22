from __future__ import annotations

from pyqauto.governance.state_machine import RuntimeStateMachine, SystemState


def test_state_machine_records_direct_transitions() -> None:
    machine = RuntimeStateMachine()

    transition = machine.transition_to(
        SystemState.DEGRADED,
        reason="primary source failed",
        trace_id="trace-1",
    )

    assert machine.current_state == SystemState.DEGRADED
    assert transition.from_state == SystemState.NORMAL
    assert transition.to_state == SystemState.DEGRADED
    assert machine.history()[0]["to_state"] == "DEGRADED"


def test_state_machine_uses_recovery_before_returning_to_normal() -> None:
    machine = RuntimeStateMachine()
    machine.transition_to(SystemState.BLOCKED, reason="schema drift")

    recovery = machine.apply_decision(SystemState.NORMAL, reason="schema clear")
    normal = machine.apply_decision(SystemState.NORMAL, reason="second clean check")

    assert recovery.to_state == SystemState.RECOVERY
    assert normal.to_state == SystemState.NORMAL
    assert machine.current_state == SystemState.NORMAL
