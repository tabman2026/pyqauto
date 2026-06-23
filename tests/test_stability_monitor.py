from __future__ import annotations

from datetime import datetime, timezone

from astock_source_router.adapters.fake_adapter import FakeAdapter
from astock_source_router.core.features import REALTIME_QUOTES
from astock_source_router.core.policy import SourcePolicy
from astock_source_router.core.router import MarketRouter
from pyqauto.stability import stability_status

STATUS_KEYS = {
    "system_uptime_score",
    "failure_rate_24h",
    "schema_drift_trend",
    "source_health_trend",
}
ROUTER_DECISION_KEYS = {
    "system_state",
    "recommended_source",
    "decision_reason",
    "winning_rule",
    "conflict_resolution_path",
    "module_contributions",
}


def test_stability_status_outputs_required_operational_fields() -> None:
    current_time = datetime(2026, 6, 23, 8, 0, tzinfo=timezone.utc)
    events = [
        {"created_at": "2026-06-23T01:00:00+00:00", "success": True, "latency_ms": 100.0},
        {"created_at": "2026-06-23T02:00:00+00:00", "success": False, "latency_ms": 200.0},
        {"created_at": "2026-06-23T03:00:00+00:00", "success": True, "latency_ms": 110.0},
        {"created_at": "2026-06-22T03:00:00+00:00", "success": False, "latency_ms": 120.0},
    ]
    health_rows = [
        {"source": "pytdx", "score": 95.0},
        {"source": "pytdx", "score": 90.0},
        {"source": "akshare", "score": 85.0},
        {"source": "efinance", "score": 60.0},
    ]

    status = stability_status(
        events=events,
        health_rows=health_rows,
        current_time=current_time,
    )

    assert set(status) == STATUS_KEYS
    assert status["failure_rate_24h"] == 0.3333
    assert status["system_uptime_score"] == 66.667
    assert status["schema_drift_trend"] == "stable"
    assert set(status["source_health_trend"]) == {"pytdx", "akshare", "efinance"}


def test_stability_layer_does_not_change_existing_router_behavior(test_config) -> None:
    router = MarketRouter(
        config=test_config,
        source_policy=SourcePolicy({REALTIME_QUOTES: ["fake"]}),
        adapters=[FakeAdapter()],
        auto_register=False,
    )

    assert set(router.meta_decision(context={"feature": REALTIME_QUOTES})) == ROUTER_DECISION_KEYS
    assert set(router.source_health()) == {"api_version", "sources", "health"}
    assert router.realtime_quotes(["000001"]).loc[0, "source"] == "fake"
