from __future__ import annotations

from astock_source_router.adapters.fake_adapter import FakeAdapter
from astock_source_router.core.policy import SourcePolicy
from astock_source_router.core.router import MarketRouter


def test_daily_kline_standard_fields(test_config):
    policy = SourcePolicy({"daily_kline": ["fake"]})
    router = MarketRouter(config=test_config, source_policy=policy, adapters=[FakeAdapter()], auto_register=False)

    df = router.get_daily_kline("000001", "20260611", "20260611")

    assert list(df.columns) == [
        "date",
        "code",
        "open",
        "high",
        "low",
        "close",
        "pre_close",
        "volume",
        "amount",
        "turnover_rate",
        "pct_chg",
        "adjust_type",
        "source",
        "source_latency_ms",
        "source_status",
        "data_timestamp",
    ]
    assert df.loc[0, "source"] == "fake"
