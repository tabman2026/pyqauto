from __future__ import annotations

from astock_source_router.adapters.fake_adapter import FakeAdapter
from astock_source_router.core.policy import SourcePolicy
from astock_source_router.core.router import MarketRouter


def test_realtime_quotes_standard_fields(test_config):
    policy = SourcePolicy({"realtime_quotes": ["fake"]})
    router = MarketRouter(config=test_config, source_policy=policy, adapters=[FakeAdapter()], auto_register=False)

    df = router.get_realtime_quotes(["000001"])

    assert list(df.columns) == [
        "date",
        "time",
        "code",
        "name",
        "last_price",
        "pre_close",
        "open",
        "high",
        "low",
        "volume",
        "amount",
        "pct_chg",
        "source",
        "source_latency_ms",
        "source_status",
        "data_timestamp",
    ]
    assert df.loc[0, "source_status"] == "ok"
