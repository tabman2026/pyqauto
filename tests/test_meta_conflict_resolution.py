from __future__ import annotations

from pyqauto.meta import meta_decision


def test_blocked_priority_overrides_readonly_recovery_and_graph() -> None:
    decision = meta_decision(
        governance={"system_state": "BLOCKED"},
        graph={"best_source": "pytdx", "overall_reliability_score": 99.0},
        autonomy={"recovery": [{"source": "pytdx", "feature": "realtime_quotes", "state": "DEGRADED"}]},
    )

    assert decision["system_state"] == "BLOCKED"
    assert decision["recommended_source"] is None
    assert decision["conflict_resolution_path"][0] == {
        "rule": "BLOCKED",
        "matched": True,
        "detail": "governance or autonomy reported a blocking state",
    }


def test_readonly_priority_overrides_autonomy_recovery_and_graph() -> None:
    decision = meta_decision(
        governance={"system_state": "READONLY"},
        graph={"best_source": "pytdx", "overall_reliability_score": 99.0},
        autonomy={"recovery": [{"source": "pytdx", "feature": "realtime_quotes", "state": "DEGRADED"}]},
    )

    assert decision["system_state"] == "READONLY"
    assert decision["recommended_source"] is None
    assert decision["winning_rule"] == "READONLY"


def test_autonomy_recovery_priority_keeps_graph_source_as_candidate() -> None:
    decision = meta_decision(
        governance={"system_state": "NORMAL"},
        graph={"best_source": "easyquotation_sina", "overall_reliability_score": 91.0},
        autonomy={"recovery": [{"source": "pytdx", "feature": "realtime_quotes", "state": "DEGRADED"}]},
    )

    assert decision["system_state"] == "RECOVERY"
    assert decision["recommended_source"] == "easyquotation_sina"
    assert decision["winning_rule"] == "AUTONOMY_RECOVERY"


def test_graph_score_priority_wins_when_no_higher_conflict_exists() -> None:
    decision = meta_decision(
        governance={"system_state": "NORMAL"},
        graph={
            "ranked_sources": [
                {"source": "easyquotation_tencent", "reliability_score": 93.0},
                {"source": "pytdx", "reliability_score": 89.0},
            ],
            "overall_reliability_score": 91.0,
        },
        autonomy={"recovery": []},
    )

    assert decision["system_state"] == "NORMAL"
    assert decision["recommended_source"] == "easyquotation_tencent"
    assert decision["winning_rule"] == "GRAPH_SCORE"
