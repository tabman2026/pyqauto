from __future__ import annotations

import time

import pytest

from astock_source_router.adapters.fake_adapter import FakeAdapter
from astock_source_router.core.errors import AllSourcesFailedError
from astock_source_router.core.policy import SourcePolicy
from astock_source_router.core.router import MarketRouter


class RecoveringAdapter(FakeAdapter):
    name = "recovering"

    def __init__(self) -> None:
        super().__init__()
        self.calls = 0

    def fetch_realtime_quotes(self, codes=None):
        self.calls += 1
        if self.calls <= 2:
            raise RuntimeError("temporary failure")
        return super().fetch_realtime_quotes(codes=codes)


def test_circuit_breaker_cools_down_and_allows_probe(test_config):
    adapter = RecoveringAdapter()
    policy = SourcePolicy({"realtime_quotes": ["recovering"]})
    router = MarketRouter(config=test_config, source_policy=policy, adapters=[adapter], auto_register=False)

    for _ in range(2):
        with pytest.raises(AllSourcesFailedError):
            router.get_realtime_quotes(["000001"])

    with pytest.raises(AllSourcesFailedError) as opened:
        router.get_realtime_quotes(["000001"])
    assert opened.value.trace[0]["status"] == "circuit_open"

    time.sleep(test_config.circuit_cooldown_seconds + 0.1)
    df = router.get_realtime_quotes(["000001"])

    assert len(df) == 1
    assert adapter.calls == 3
