from __future__ import annotations

from pyqauto.meta import meta_decision, meta_state, system_brain


def test_meta_decision_recommends_graph_source_when_system_is_normal() -> None:
    decision = meta_decision(
        governance={"system_state": "NORMAL"},
        graph={
            "ranked_sources": [
                {"source": "pytdx", "reliability_score": 98.5},
                {"source": "easyquotation_sina", "reliability_score": 90.0},
            ],
            "overall_reliability_score": 94.25,
        },
        autonomy={"recovery": []},
    )

    assert decision["system_state"] == "NORMAL"
    assert decision["recommended_source"] == "pytdx"
    assert decision["winning_rule"] == "GRAPH_SCORE"
    assert "Reliability graph selected" in decision["decision_reason"]


def test_meta_decision_blocks_source_selection_on_blocked_state() -> None:
    decision = meta_decision(
        governance={"system_state": "BLOCKED"},
        graph={"ranked_sources": [{"source": "pytdx", "reliability_score": 100.0}]},
        autonomy={"recovery": []},
    )

    assert decision["system_state"] == "BLOCKED"
    assert decision["recommended_source"] is None
    assert decision["winning_rule"] == "BLOCKED"


def test_meta_state_returns_three_subsystems_and_merged_state() -> None:
    state = meta_state(
        governance={"system_state": "NORMAL"},
        graph={"best_source": "easyquotation_tencent", "graph_score": 88.0},
        autonomy={"recovery": []},
    )

    assert state["governance"]["state"] == "NORMAL"
    assert state["graph"]["recommended_source"] == "easyquotation_tencent"
    assert state["autonomy"]["state"] == "NORMAL"
    assert state["merged"]["graph_score"] == 88.0


def test_system_brain_exposes_global_view_and_safety_boundaries() -> None:
    brain = system_brain(
        governance={"system_state": "NORMAL"},
        graph={"best_source": "fake", "overall_reliability_score": 100.0},
        autonomy={"recovery": []},
    )

    assert brain["role"] == "pyqauto_meta_control_plane"
    assert brain["system_state"] == "NORMAL"
    assert brain["meta_state"]["merged"]["graph_recommended_source"] == "fake"
    assert all(value is False for value in brain["safety_boundaries"].values())
