from __future__ import annotations

from pyqauto.meta import meta_explain


def test_meta_explain_returns_decision_trace_conflict_path_and_contributions() -> None:
    explanation = meta_explain(
        governance={"system_state": "NORMAL"},
        graph={"best_source": "pytdx", "overall_reliability_score": 97.0},
        autonomy={"recovery": []},
    )

    assert [step["step"] for step in explanation["decision_trace"]] == [
        "state_aggregation",
        "conflict_resolution",
    ]
    assert explanation["conflict_resolution_path"][3]["rule"] == "GRAPH_SCORE"
    assert explanation["conflict_resolution_path"][3]["matched"] is True
    assert explanation["module_contributions"]["graph"]["recommended_source"] == "pytdx"
    assert explanation["decision_reason"]


def test_meta_explain_shows_blocked_resolution_path() -> None:
    explanation = meta_explain(
        governance={"system_state": "BLOCKED"},
        graph={"best_source": "pytdx", "overall_reliability_score": 97.0},
        autonomy={"recovery": []},
    )

    assert explanation["decision_trace"][1]["winning_rule"] == "BLOCKED"
    assert explanation["conflict_resolution_path"][0]["matched"] is True
    assert explanation["module_contributions"]["governance"]["effect"] == "blocks"
