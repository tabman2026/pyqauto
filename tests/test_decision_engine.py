from __future__ import annotations

from pyqauto.governance.decision_engine import DecisionEngine, decide
from pyqauto.governance.state_machine import SystemState


def test_decide_blocks_on_schema_drift() -> None:
    state = decide(
        {
            "schema_drift_count": 1,
            "schema_validation_result": {
                "status": "schema_drift",
                "schema_drift_fields": ["last_price"],
            },
        }
    )

    assert state == SystemState.BLOCKED


def test_decide_degrades_when_pytdx_fails_and_fallback_succeeds() -> None:
    state = decide(
        {
            "success": True,
            "attempts": [
                {"source": "pytdx", "source_level": "primary", "success": False},
                {"source": "easyquotation_sina", "source_level": None, "success": True},
            ],
            "fallback_chain": ["pytdx:primary"],
        }
    )

    assert state == SystemState.DEGRADED


def test_decide_readonly_when_all_sources_fail() -> None:
    state = decide(
        {
            "success": False,
            "attempts": [
                {"source": "pytdx", "source_level": "primary", "success": False},
                {"source": "easyquotation_sina", "source_level": None, "success": False},
            ],
            "fallback_chain": ["pytdx:primary", "easyquotation_sina"],
        }
    )

    assert state == SystemState.READONLY


def test_decide_normal_without_failures_or_drift() -> None:
    state = decide(
        {
            "success": True,
            "attempts": [
                {"source": "pytdx", "source_level": "primary", "success": True},
            ],
            "fallback_chain": [],
        }
    )

    assert state == SystemState.NORMAL


def test_decision_trace_explains_degraded_state() -> None:
    trace = DecisionEngine().evaluate(
        {
            "trace_id": "trace-1",
            "success": True,
            "attempts": [
                {"source": "pytdx", "source_level": "primary", "success": False},
                {"source": "easyquotation_tencent", "source_level": None, "success": True},
            ],
            "fallback_chain": ["pytdx:primary"],
            "schema_validation_result": {"status": "not_checked"},
        }
    )

    payload = trace.to_dict()
    assert payload["state"] == "DEGRADED"
    assert payload["why_this_state"]
    assert payload["failed_sources"] == ["pytdx:primary"]
    assert payload["fallback_chain"] == ["pytdx:primary"]
    assert payload["schema_validation_result"]["status"] == "not_checked"
