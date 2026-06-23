from __future__ import annotations

from astock_source_router.adapters.fake_adapter import FakeAdapter
from astock_source_router.core.policy import SourcePolicy
from astock_source_router.core.router import MarketRouter


def test_health_score_is_source_feature_scoped(test_config):
    policy = SourcePolicy({"realtime_quotes": ["fake"], "daily_kline": ["fake"]})
    router = MarketRouter(config=test_config, source_policy=policy, adapters=[FakeAdapter()], auto_register=False)

    router.get_realtime_quotes(["000001"])
    router.get_daily_kline("000001", "20260611", "20260611")
    report = router.health_report()

    keys = {(row["source"], row["feature"]) for row in report.to_dict("records")}
    assert ("fake", "realtime_quotes") in keys
    assert ("fake", "daily_kline") in keys
    assert {"avg_latency_ms", "p95_latency_ms", "empty_rate", "field_complete_rate"}.issubset(
        set(report.columns)
    )
