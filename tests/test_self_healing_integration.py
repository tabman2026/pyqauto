from __future__ import annotations

import pandas as pd
import pytest

from astock_source_router.adapters.fake_adapter import FakeAdapter
from astock_source_router.core.errors import AllSourcesFailedError
from astock_source_router.core.features import REALTIME_QUOTES
from astock_source_router.core.policy import SourcePolicy
from astock_source_router.core.router import MarketRouter


class SchemaDriftAdapter(FakeAdapter):
    name = "schema_drift_source"

    def __init__(self) -> None:
        super().__init__()
        self.has_schema_drift = True

    def fetch_realtime_quotes(self, codes=None):
        if self.has_schema_drift:
            return pd.DataFrame([{"code": "000001", "name": "schema drift sample"}])
        return super().fetch_realtime_quotes(codes=codes)


def test_schema_drift_decrease_unblocks_autonomy_state(test_config):
    adapter = SchemaDriftAdapter()
    policy = SourcePolicy({REALTIME_QUOTES: ["schema_drift_source"]})
    router = MarketRouter(
        config=test_config,
        source_policy=policy,
        adapters=[adapter],
        auto_register=False,
    )

    with pytest.raises(AllSourcesFailedError):
        router.fetch_result(REALTIME_QUOTES, codes=["000001"])

    blocked = router.recovery_state(source="schema_drift_source", feature=REALTIME_QUOTES)
    assert blocked[0]["state"] == "BLOCKED"
    assert blocked[0]["blocked_by_schema_drift"] is True

    adapter.has_schema_drift = False
    result = router.fetch_result(REALTIME_QUOTES, codes=["000001"])

    restored = router.recovery_state(source="schema_drift_source", feature=REALTIME_QUOTES)
    healing = router.autonomy_status()["self_healing"]
    assert result.source == "schema_drift_source"
    assert restored[0]["state"] == "NORMAL"
    assert restored[0]["blocked_by_schema_drift"] is False
    assert healing[0]["blocked"] is False
    assert healing[0]["last_action"] == "unblock_system"
