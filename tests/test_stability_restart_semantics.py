from __future__ import annotations

import pytest

from astock_source_router.adapters.fake_adapter import FakeAdapter
from astock_source_router.core.errors import AllSourcesFailedError
from astock_source_router.core.features import REALTIME_QUOTES
from astock_source_router.core.models import RouterConfig
from astock_source_router.core.policy import SourcePolicy
from pyqauto import QuoteRouter


class RestartFailingAdapter(FakeAdapter):
    name = "restart_failing"

    def __init__(self) -> None:
        super().__init__(fail_features={REALTIME_QUOTES})


def test_restart_restores_persisted_health_but_not_in_memory_recovery(tmp_path) -> None:
    config = RouterConfig(
        cache_dir=tmp_path / "cache",
        log_dir=tmp_path / "logs",
        enable_cache=False,
        enable_sqlite_audit=True,
        min_interval_seconds={"restart_failing": 0.0},
    )
    policy = SourcePolicy({REALTIME_QUOTES: ["restart_failing"]})
    router = QuoteRouter(
        config=config,
        source_policy=policy,
        adapters=[RestartFailingAdapter()],
        auto_register=False,
    )

    with pytest.raises(AllSourcesFailedError):
        router.realtime_quotes(["000001"])

    assert router.recovery_state(source="restart_failing", feature=REALTIME_QUOTES)[0]["state"] == "DEGRADED"
    assert router.source_health()["health"]

    restarted = QuoteRouter(
        config=config,
        source_policy=policy,
        adapters=[RestartFailingAdapter()],
        auto_register=False,
    )

    assert restarted.source_health()["health"]
    assert restarted.recovery_state(source="restart_failing", feature=REALTIME_QUOTES) == []
