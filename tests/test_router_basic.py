from __future__ import annotations

from astock_source_router.adapters.fake_adapter import FakeAdapter
from astock_source_router.core.policy import SourcePolicy
from astock_source_router.core.router import MarketRouter


def test_router_realtime_success(test_config):
    policy = SourcePolicy({"realtime_quotes": ["fake"]})
    router = MarketRouter(config=test_config, source_policy=policy, adapters=[FakeAdapter()], auto_register=False)
    df = router.get_realtime_quotes(["000001"])
    assert len(df) == 1
    assert df.loc[0, "code"] == "000001"
    assert df.loc[0, "source"] == "fake"
    assert "source_latency_ms" in df.columns
    assert "data_timestamp" in df.columns


def test_router_daily_success(test_config):
    policy = SourcePolicy({"daily_kline": ["fake"]})
    router = MarketRouter(config=test_config, source_policy=policy, adapters=[FakeAdapter()], auto_register=False)
    df = router.get_daily_kline("000001", "20260611", "20260611")
    assert len(df) == 1
    assert df.loc[0, "adjust_type"] == "none"
    assert "data_timestamp" in df.columns
