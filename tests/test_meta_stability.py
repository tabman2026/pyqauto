from __future__ import annotations

from astock_source_router.adapters.fake_adapter import FakeAdapter
from astock_source_router.core.features import REALTIME_QUOTES
from astock_source_router.core.policy import SourcePolicy
from astock_source_router.core.router import MarketRouter
from pyqauto.meta import meta_decision, meta_explain

DECISION_KEYS = {
    "system_state",
    "recommended_source",
    "decision_reason",
    "winning_rule",
    "conflict_resolution_path",
    "module_contributions",
}
EXPLAIN_KEYS = {
    "decision_trace",
    "conflict_resolution_path",
    "module_contributions",
    "decision_reason",
}
CONFLICT_RULES = [
    "BLOCKED",
    "READONLY",
    "AUTONOMY_RECOVERY",
    "GRAPH_SCORE",
    "GOVERNANCE_NORMAL",
]


def test_meta_decision_contract_and_conflict_path_are_stable() -> None:
    decision = meta_decision(
        governance={"system_state": "NORMAL"},
        graph={"best_source": "fake", "overall_reliability_score": 100.0},
        autonomy={"recovery": []},
    )

    assert set(decision) == DECISION_KEYS
    assert [item["rule"] for item in decision["conflict_resolution_path"]] == CONFLICT_RULES
    assert decision["winning_rule"] == "GRAPH_SCORE"
    assert decision["recommended_source"] == "fake"


def test_meta_explain_contract_is_stable_and_read_only() -> None:
    explanation = meta_explain(
        governance={"system_state": "BLOCKED"},
        graph={"best_source": "fake", "overall_reliability_score": 100.0},
        autonomy={"recovery": []},
    )

    assert set(explanation) == EXPLAIN_KEYS
    assert [step["step"] for step in explanation["decision_trace"]] == [
        "state_aggregation",
        "conflict_resolution",
    ]
    assert explanation["decision_trace"][1]["system_state"] == "BLOCKED"
    for forbidden_key in ("trade", "order", "position", "strategy", "prediction"):
        assert forbidden_key not in explanation


def test_router_meta_api_uses_graph_candidate_without_strategy_behavior(test_config) -> None:
    router = MarketRouter(
        config=test_config,
        source_policy=SourcePolicy({REALTIME_QUOTES: ["fake"]}),
        adapters=[FakeAdapter()],
        auto_register=False,
    )

    decision = router.meta_decision(context={"feature": REALTIME_QUOTES})
    assert set(decision) == DECISION_KEYS
    assert decision["system_state"] == "NORMAL"
    assert decision["recommended_source"] == "fake"
    assert decision["module_contributions"]["graph"]["effect"] == "recommends_source"
    for key in ("trade", "order", "position", "strategy", "prediction"):
        assert key not in decision
