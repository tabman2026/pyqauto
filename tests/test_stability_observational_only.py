from __future__ import annotations

from datetime import datetime, timezone

from astock_source_router.adapters.fake_adapter import FakeAdapter
from astock_source_router.core.features import REALTIME_QUOTES
from astock_source_router.core.policy import SourcePolicy
from pyqauto import QuoteRouter
from pyqauto.stability import stability_status


def test_stability_report_does_not_mutate_router_selection_or_results(test_config) -> None:
    router = QuoteRouter(
        config=test_config,
        source_policy=SourcePolicy({REALTIME_QUOTES: ["fake"]}),
        adapters=[FakeAdapter()],
        auto_register=False,
    )

    before = router.realtime_quotes(["000001"])
    selection_before = router.select_best_source({"feature": REALTIME_QUOTES})
    report = stability_status(
        events=[
            {"created_at": "2026-06-23T01:00:00+00:00", "success": True, "latency_ms": 100.0},
            {"created_at": "2026-06-23T02:00:00+00:00", "success": True, "latency_ms": 120.0},
            {
                "created_at": "2026-06-23T03:00:00+00:00",
                "success": False,
                "latency_ms": 1800.0,
                "missing_fields": ["last_price"],
            },
            {
                "created_at": "2026-06-23T04:00:00+00:00",
                "success": False,
                "latency_ms": 2200.0,
                "schema_drift": True,
            },
        ],
        current_time=datetime(2026, 6, 23, 5, 0, tzinfo=timezone.utc),
    )
    after = router.realtime_quotes(["000001"])
    selection_after = router.select_best_source({"feature": REALTIME_QUOTES})

    assert report["schema_drift_trend"] == "increasing"
    assert before.loc[0, "source"] == "fake"
    assert after.loc[0, "source"] == "fake"
    assert selection_before["recommended_source"] == selection_after["recommended_source"] == "fake"
