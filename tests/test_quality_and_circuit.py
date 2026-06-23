from __future__ import annotations

import pytest

from astock_source_router.adapters.fake_adapter import FakeAdapter
from astock_source_router.core.errors import AllSourcesFailedError
from astock_source_router.core.features import REALTIME_QUOTES
from astock_source_router.core.policy import SourcePolicy
from astock_source_router.core.router import MarketRouter


def test_empty_dataframe_fails_quality(test_config):
    policy = SourcePolicy({"realtime_quotes": ["fake"]})
    router = MarketRouter(
        config=test_config,
        source_policy=policy,
        adapters=[FakeAdapter(empty_features={REALTIME_QUOTES})],
        auto_register=False,
    )
    with pytest.raises(AllSourcesFailedError):
        router.get_realtime_quotes(["000001"])


def test_circuit_records_failures(test_config):
    policy = SourcePolicy({"realtime_quotes": ["fake"]})
    router = MarketRouter(
        config=test_config,
        source_policy=policy,
        adapters=[FakeAdapter(fail_features={REALTIME_QUOTES})],
        auto_register=False,
    )
    for _ in range(2):
        with pytest.raises(AllSourcesFailedError):
            router.get_realtime_quotes(["000001"])
    snapshot = router.circuit_breaker.snapshot()
    assert any(key.startswith("fake:realtime_quotes") for key in snapshot)
