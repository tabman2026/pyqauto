from __future__ import annotations

from astock_source_router.autonomy import AutonomousControlLayer
from astock_source_router.autonomy.recovery_engine import BLOCKED, DEGRADED, NORMAL
from astock_source_router.core.health_score import HealthStat
from pyqauto.meta.conflict_resolver import READONLY


def test_v1_governance_state_set_is_frozen() -> None:
    assert {NORMAL, DEGRADED, READONLY, BLOCKED} == {
        "NORMAL",
        "DEGRADED",
        "READONLY",
        "BLOCKED",
    }


def test_v1_graph_score_model_is_frozen() -> None:
    stat = HealthStat(
        source="fake",
        feature="realtime_quotes",
        success_count=1,
        failure_count=0,
        latencies_ms=[4000.0],
        recent_successes=[True],
    )
    assert stat.score(timeout_ms=8000.0) == 90.0


def test_v1_autonomy_capabilities_are_frozen_and_non_strategy() -> None:
    status = AutonomousControlLayer().status()
    assert status["capabilities"] == [
        "system_auto_recovery",
        "anomaly_detection",
        "score_decay_model",
        "self_healing_mechanism",
    ]
    capability_text = " ".join(status["capabilities"]).lower()
    for forbidden in ("strategy", "prediction", "broker", "qmt", "order", "position"):
        assert forbidden not in capability_text
    assert all(value is False for value in status["safety_boundaries"].values())
