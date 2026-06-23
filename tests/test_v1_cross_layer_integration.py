from __future__ import annotations

from datetime import datetime, timezone

import pandas as pd
import pytest

from astock_source_router.adapters.fake_adapter import FakeAdapter
from astock_source_router.core.errors import AllSourcesFailedError
from astock_source_router.core.features import REALTIME_QUOTES
from astock_source_router.core.policy import SourcePolicy
from pyqauto import QuoteRouter
from pyqauto.stability import stability_status


class PrimaryFakeAdapter(FakeAdapter):
    name = "primary"


class FallbackFakeAdapter(FakeAdapter):
    name = "fallback"


class FailingPrimaryAdapter(FakeAdapter):
    name = "primary"

    def __init__(self) -> None:
        super().__init__(fail_features={REALTIME_QUOTES})


class FailingFallbackAdapter(FakeAdapter):
    name = "fallback"

    def __init__(self) -> None:
        super().__init__(fail_features={REALTIME_QUOTES})


class RecoveringPrimaryAdapter(FakeAdapter):
    name = "recovering"

    def __init__(self) -> None:
        super().__init__()
        self.fail_next = True

    def fetch_realtime_quotes(self, codes=None):
        if self.fail_next:
            raise RuntimeError("temporary failure")
        return super().fetch_realtime_quotes(codes=codes)


class SchemaDriftAdapter(FakeAdapter):
    name = "schema_drift"

    def fetch_realtime_quotes(self, codes=None):
        return pd.DataFrame([{"code": "000001", "name": "schema drift sample"}])


def _router(test_config, adapters: list[FakeAdapter], sources: list[str]) -> QuoteRouter:
    return QuoteRouter(
        config=test_config,
        source_policy=SourcePolicy({REALTIME_QUOTES: sources}),
        adapters=adapters,
        auto_register=False,
    )


def test_scenario_a_all_normal_selects_highest_reliability_source(test_config) -> None:
    router = _router(test_config, [PrimaryFakeAdapter()], ["primary"])

    data = router.realtime_quotes(["000001"])
    decision = router.meta_decision({"feature": REALTIME_QUOTES})

    assert router.status()["system_state"] == "NORMAL"
    assert data.loc[0, "source"] == "primary"
    assert decision["system_state"] == "NORMAL"
    assert decision["recommended_source"] == "primary"


def test_scenario_b_primary_failure_fallback_success_is_degraded_and_explainable(test_config) -> None:
    router = _router(
        test_config,
        [FailingPrimaryAdapter(), FallbackFakeAdapter()],
        ["primary", "fallback"],
    )

    data = router.realtime_quotes(["000001"])
    decision = router.meta_decision({"feature": REALTIME_QUOTES})
    explanation = router.meta_explain({"feature": REALTIME_QUOTES})

    assert data.loc[0, "source"] == "fallback"
    assert router.status()["system_state"] == "DEGRADED"
    assert decision["system_state"] == "RECOVERY"
    assert decision["recommended_source"] == "fallback"
    assert explanation["module_contributions"]["autonomy"]["active_recovery_count"] == 1


def test_scenario_c_schema_drift_rejects_public_records(test_config) -> None:
    adapter = SchemaDriftAdapter()
    router = _router(test_config, [adapter], ["schema_drift"])

    raw = adapter.fetch_realtime_quotes(["000001"])
    validation = adapter.validate_standard_output(REALTIME_QUOTES, raw)

    with pytest.raises(AllSourcesFailedError):
        router.realtime_quotes(["000001"])

    assert validation["is_valid"] is False
    assert validation["public_record_count"] == 0
    assert validation["rejected_record_count"] == 1
    assert router.status()["system_state"] == "BLOCKED"


def test_scenario_d_all_sources_fail_blocks_recommendation(test_config) -> None:
    router = _router(
        test_config,
        [FailingPrimaryAdapter(), FailingFallbackAdapter()],
        ["primary", "fallback"],
    )

    with pytest.raises(AllSourcesFailedError):
        router.realtime_quotes(["000001"])

    selection = router.select_best_source({"feature": REALTIME_QUOTES})
    decision = router.meta_decision({"feature": REALTIME_QUOTES})

    assert router.status()["system_state"] == "READONLY"
    assert selection["recommended_source"] is None
    assert selection["selection_status"] == "blocked"
    assert decision["recommended_source"] is None


def test_scenario_e_recovery_window_does_not_return_to_normal_after_one_success(test_config) -> None:
    adapter = RecoveringPrimaryAdapter()
    router = _router(test_config, [adapter], ["recovering"])

    with pytest.raises(AllSourcesFailedError):
        router.realtime_quotes(["000001"])
    adapter.fail_next = False
    router.realtime_quotes(["000001"])

    recovery = router.recovery_state(source="recovering", feature=REALTIME_QUOTES)[0]
    decision = router.meta_decision({"feature": REALTIME_QUOTES})

    assert recovery["state"] == "DEGRADED"
    assert recovery["success_count"] == 1
    assert decision["system_state"] == "RECOVERY"


def test_scenario_f_sustained_recovery_returns_to_normal(test_config) -> None:
    adapter = RecoveringPrimaryAdapter()
    router = _router(test_config, [adapter], ["recovering"])

    with pytest.raises(AllSourcesFailedError):
        router.realtime_quotes(["000001"])
    adapter.fail_next = False
    router.realtime_quotes(["000001"])
    router.realtime_quotes(["000001"])

    recovery = router.recovery_state(source="recovering", feature=REALTIME_QUOTES)[0]
    decision = router.meta_decision({"feature": REALTIME_QUOTES})

    assert recovery["state"] == "NORMAL"
    assert recovery["success_count"] == 2
    assert decision["system_state"] == "NORMAL"


def test_scenario_g_stability_long_term_degradation_is_observational_only(test_config) -> None:
    router = _router(test_config, [PrimaryFakeAdapter()], ["primary"])
    before = router.realtime_quotes(["000001"])
    before_selection = router.select_best_source({"feature": REALTIME_QUOTES})

    report = stability_status(
        events=[
            {"created_at": "2026-06-23T01:00:00+00:00", "success": True, "latency_ms": 100.0},
            {"created_at": "2026-06-23T02:00:00+00:00", "success": True, "latency_ms": 120.0},
            {
                "created_at": "2026-06-23T03:00:00+00:00",
                "success": False,
                "latency_ms": 1800.0,
                "missing_fields": ["last_price"],
                "attempted_sources": ["primary", "fallback"],
            },
            {
                "created_at": "2026-06-23T04:00:00+00:00",
                "success": False,
                "latency_ms": 2200.0,
                "schema_drift": True,
                "attempted_sources": ["primary", "fallback"],
            },
        ],
        current_time=datetime(2026, 6, 23, 5, 0, tzinfo=timezone.utc),
    )
    after = router.realtime_quotes(["000001"])
    after_selection = router.select_best_source({"feature": REALTIME_QUOTES})

    assert report["schema_drift_trend"] == "increasing"
    assert before.loc[0, "source"] == after.loc[0, "source"] == "primary"
    assert before_selection["recommended_source"] == after_selection["recommended_source"] == "primary"
