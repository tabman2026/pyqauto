from __future__ import annotations

import pytest

from astock_source_router.adapters.fake_adapter import FakeAdapter
from astock_source_router.core.errors import AllSourcesFailedError
from astock_source_router.core.features import REALTIME_QUOTES
from astock_source_router.core.policy import SourcePolicy
from astock_source_router.core.router import MarketRouter


class RecoveringAdapter(FakeAdapter):
    name = "recovering"

    def __init__(self) -> None:
        super().__init__()
        self.should_fail = True

    def fetch_realtime_quotes(self, codes=None):
        if self.should_fail:
            raise RuntimeError("temporary source failure")
        return super().fetch_realtime_quotes(codes=codes)


def test_autonomy_degrades_failed_source_and_uses_recovery_window(test_config):
    adapter = RecoveringAdapter()
    policy = SourcePolicy({REALTIME_QUOTES: ["recovering"]})
    router = MarketRouter(
        config=test_config,
        source_policy=policy,
        adapters=[adapter],
        auto_register=False,
    )

    with pytest.raises(AllSourcesFailedError):
        router.fetch_result(REALTIME_QUOTES, codes=["000001"])

    degraded = router.recovery_state(source="recovering", feature=REALTIME_QUOTES)
    assert degraded[0]["state"] == "DEGRADED"
    assert degraded[0]["failure_count"] == 1
    assert router.source_weight_decay(source="recovering", feature=REALTIME_QUOTES)[0]["score"] == 0.9

    adapter.should_fail = False
    result = router.fetch_result(REALTIME_QUOTES, codes=["000001"])

    restored = router.recovery_state(source="recovering", feature=REALTIME_QUOTES)
    assert result.source == "recovering"
    assert restored[0]["state"] == "DEGRADED"
    assert restored[0]["failure_count"] == 0
    assert restored[0]["success_count"] == 1

    router.fetch_result(REALTIME_QUOTES, codes=["000001"])
    recovered = router.recovery_state(source="recovering", feature=REALTIME_QUOTES)
    assert recovered[0]["state"] == "NORMAL"
    assert recovered[0]["success_count"] == 2


def test_autonomy_status_exposes_l6_boundaries(test_config):
    router = MarketRouter(config=test_config, adapters=[FakeAdapter()], auto_register=False)

    status = router.autonomy_status()

    assert status["layer"] == "L6_AUTONOMOUS_CONTROL_LAYER"
    assert status["enabled"] is True
    assert status["safety_boundaries"] == {
        "trading_system": False,
        "strategy_or_prediction": False,
        "investment_advice": False,
        "broker_or_qmt_control": False,
        "auto_trade": False,
    }
