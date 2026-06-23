from __future__ import annotations

from astock_source_router.adapters.fake_adapter import BrokenAdapter, FakeAdapter
from astock_source_router.core.policy import SourcePolicy
from astock_source_router.core.router import MarketRouter


class MissingFieldAdapter(FakeAdapter):
    name = "missing_field"

    def fetch_realtime_quotes(self, codes=None):
        return super().fetch_realtime_quotes(codes=codes).drop(columns=["last_price"])


def test_fallback_to_second_source(test_config):
    policy = SourcePolicy({"realtime_quotes": ["broken", "fake"]})
    router = MarketRouter(
        config=test_config,
        source_policy=policy,
        adapters=[BrokenAdapter(), FakeAdapter()],
        auto_register=False,
    )
    df = router.get_realtime_quotes(["000001"])
    assert len(df) == 1
    assert df.loc[0, "source"] == "fake"
    report = router.health_report()
    assert not report.empty


def test_fallback_on_missing_required_field(test_config):
    policy = SourcePolicy({"realtime_quotes": ["missing_field", "fake"]})
    router = MarketRouter(
        config=test_config,
        source_policy=policy,
        adapters=[MissingFieldAdapter(), FakeAdapter()],
        auto_register=False,
    )

    result = router.fetch_result("realtime_quotes", codes=["000001"])

    assert result.source == "fake"
    assert result.fallback_trace[0]["status"] == "quality_failed"
    assert "last_price" in result.fallback_trace[0]["missing_fields"]
