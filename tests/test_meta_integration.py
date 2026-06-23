from __future__ import annotations

from typing import Any

from astock_source_router.autonomy import AutonomousControlLayer
from pyqauto.meta import MetaControlPlane


class FakeGovernance:
    def status(self) -> dict[str, Any]:
        return {
            "system_state": "NORMAL",
            "latest_decision_trace": {"why_this_state": "test fixture is normal"},
        }


class FakeReliabilityGraph:
    def select_best_source(self, context: dict[str, Any] | None = None) -> dict[str, Any]:
        assert context == {"feature": "realtime_quotes"}
        return {
            "best_source": "easyquotation_sina",
            "selection_status": "selected",
            "ranked_sources": [
                {"source": "easyquotation_sina", "reliability_score": 95.0},
                {"source": "pytdx", "reliability_score": 72.0},
            ],
        }

    def source_scores(self) -> dict[str, Any]:
        return {
            "overall_reliability_score": 83.5,
            "ranked_sources": [
                {"source": "easyquotation_sina", "reliability_score": 95.0},
                {"source": "pytdx", "reliability_score": 72.0},
            ],
        }


def test_meta_control_plane_integrates_public_subsystem_objects() -> None:
    autonomy = AutonomousControlLayer()
    autonomy.record_attempt(
        source="pytdx",
        feature="realtime_quotes",
        success=False,
        status="failed",
        error_type="TimeoutError",
    )
    plane = MetaControlPlane(
        governance=FakeGovernance(),
        graph=FakeReliabilityGraph(),
        autonomy=autonomy,
    )

    decision = plane.meta_decision(context={"feature": "realtime_quotes"})
    explanation = plane.meta_explain(context={"feature": "realtime_quotes"})

    assert decision["system_state"] == "RECOVERY"
    assert decision["recommended_source"] == "easyquotation_sina"
    assert decision["winning_rule"] == "AUTONOMY_RECOVERY"
    assert explanation["module_contributions"]["autonomy"]["active_recovery_count"] == 1
