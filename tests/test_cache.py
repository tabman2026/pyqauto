from __future__ import annotations

from astock_source_router.adapters.fake_adapter import FakeAdapter
from astock_source_router.core.models import RouterConfig
from astock_source_router.core.policy import SourcePolicy
from astock_source_router.core.router import MarketRouter


def test_cache_hit(tmp_path):
    config = RouterConfig(
        cache_dir=tmp_path / "cache",
        log_dir=tmp_path / "logs",
        enable_cache=True,
        realtime_cache_seconds=60,
        min_interval_seconds={"fake": 0.0},
    )
    policy = SourcePolicy({"realtime_quotes": ["fake"]})
    router = MarketRouter(config=config, source_policy=policy, adapters=[FakeAdapter()], auto_register=False)
    df1 = router.get_realtime_quotes(["000001"])
    df2 = router.get_realtime_quotes(["000001"])
    assert len(df1) == 1
    assert len(df2) == 1
