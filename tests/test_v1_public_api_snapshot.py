from __future__ import annotations

import inspect

import pandas as pd

from astock_source_router.adapters.fake_adapter import FakeAdapter
from astock_source_router.core.features import (
    DAILY_KLINE,
    FULL_REALTIME_QUOTES,
    INDEX_REALTIME,
    MINUTE_KLINE,
    REALTIME_QUOTES,
)
from astock_source_router.core.policy import SourcePolicy
from astock_source_router.core.router import MarketRouter
from pyqauto import QuoteRouter

PUBLIC_API_SIGNATURES = {
    "realtime_quotes": "(self, codes: 'list[str] | tuple[str, ...] | str | None' = None) -> 'pd.DataFrame'",
    "full_realtime_quotes": "(self, codes: 'list[str] | tuple[str, ...] | str | None' = None) -> 'pd.DataFrame'",
    "index_realtime": "(self, codes: 'list[str] | tuple[str, ...] | str | None' = None) -> 'pd.DataFrame'",
    "minute_kline": "(self, code: 'str', *, period: 'str' = '5', adjust: 'str' = '') -> 'pd.DataFrame'",
    "daily_kline": "(self, code: 'str', *, start_date: 'str', end_date: 'str', adjust: 'str' = '') -> 'pd.DataFrame'",
    "kline": "(self, code: 'str', *, start_date: 'str | None' = None, end_date: 'str | None' = None, period: 'str' = 'daily', adjust: 'str' = '') -> 'pd.DataFrame'",
    "status": "(self) -> 'dict[str, Any]'",
    "health": "(self) -> 'dict[str, Any]'",
    "decision_trace": "(self) -> 'dict[str, Any]'",
    "get_system_state": "(self) -> 'str'",
    "source_health": "(self) -> 'dict[str, Any]'",
    "source_scores": "(self, feature: 'str | None' = None) -> 'dict[str, Any]'",
    "select_best_source": "(self, context: 'dict[str, Any] | None' = None) -> 'dict[str, Any]'",
    "reliability_graph": "(self) -> 'dict[str, Any]'",
    "autonomy_status": "(self) -> 'dict[str, object]'",
    "recovery_state": "(self, source: 'str | None' = None, feature: 'str | None' = None) -> 'list[dict[str, object]]'",
    "anomaly_report": "(self, source: 'str | None' = None, feature: 'str | None' = None) -> 'list[dict[str, object]]'",
    "source_weight_decay": "(self, source: 'str | None' = None, feature: 'str | None' = None) -> 'list[dict[str, object]]'",
    "meta_decision": "(self, context: 'dict[str, Any] | None' = None) -> 'dict[str, Any]'",
    "meta_state": "(self, context: 'dict[str, Any] | None' = None) -> 'dict[str, Any]'",
    "meta_explain": "(self, context: 'dict[str, Any] | None' = None) -> 'dict[str, Any]'",
    "system_brain": "(self, context: 'dict[str, Any] | None' = None) -> 'dict[str, Any]'",
    "stability_status": "(self, *, current_time: 'datetime | None' = None) -> 'dict[str, Any]'",
}


def _router(test_config) -> QuoteRouter:
    return QuoteRouter(
        config=test_config,
        source_policy=SourcePolicy(
            {
                REALTIME_QUOTES: ["fake"],
                FULL_REALTIME_QUOTES: ["fake"],
                INDEX_REALTIME: ["fake"],
                MINUTE_KLINE: ["fake"],
                DAILY_KLINE: ["fake"],
            }
        ),
        adapters=[FakeAdapter()],
        auto_register=False,
    )


def test_pyqauto_quote_router_is_public_alias_for_single_implementation() -> None:
    assert QuoteRouter is MarketRouter


def test_v1_public_api_signature_snapshot() -> None:
    assert len(PUBLIC_API_SIGNATURES) == 23
    for name, signature in PUBLIC_API_SIGNATURES.items():
        assert callable(getattr(QuoteRouter, name))
        assert str(inspect.signature(getattr(QuoteRouter, name))) == signature


def test_v1_public_api_return_shape_snapshot(test_config) -> None:
    router = _router(test_config)

    assert isinstance(router.realtime_quotes(["000001"]), pd.DataFrame)
    assert isinstance(router.full_realtime_quotes(["000001"]), pd.DataFrame)
    assert isinstance(router.index_realtime(["000001"]), pd.DataFrame)
    assert isinstance(router.minute_kline("000001"), pd.DataFrame)
    assert isinstance(
        router.daily_kline("000001", start_date="20260611", end_date="20260611"),
        pd.DataFrame,
    )
    assert isinstance(
        router.kline("000001", start_date="20260611", end_date="20260611"),
        pd.DataFrame,
    )

    assert set(router.status()) == {
        "api_version",
        "system_state",
        "state",
        "registered_sources",
        "active_recovery",
        "latest_decision_trace",
        "safety_boundaries",
    }
    assert set(router.health()) == {"api_version", "system_state", "source_health", "autonomy"}
    assert set(router.decision_trace()) == {
        "api_version",
        "system_state",
        "feature",
        "ranked_sources",
        "recovery",
        "anomalies",
    }
    assert router.get_system_state() == "NORMAL"
    assert set(router.source_health()) == {"api_version", "sources", "health"}
    assert set(router.source_scores()) == {
        "api_version",
        "feature",
        "overall_reliability_score",
        "ranked_sources",
    }
    assert set(router.select_best_source({"feature": REALTIME_QUOTES})) == {
        "api_version",
        "feature",
        "system_state",
        "recommended_source",
        "best_source",
        "selection_status",
        "ranked_sources",
        "reason",
    }
    assert set(router.reliability_graph()) == {
        "api_version",
        "system_state",
        "features",
        "source_health",
    }
    assert set(router.autonomy_status()) == {
        "layer",
        "enabled",
        "capabilities",
        "safety_boundaries",
        "recovery",
        "anomalies",
        "decay",
        "self_healing",
    }
    assert router.recovery_state() == router.autonomy_status()["recovery"]
    assert router.anomaly_report() == router.autonomy_status()["anomalies"]
    assert router.source_weight_decay() == router.autonomy_status()["decay"]
    assert set(router.meta_decision({"feature": REALTIME_QUOTES})) == {
        "system_state",
        "recommended_source",
        "decision_reason",
        "winning_rule",
        "conflict_resolution_path",
        "module_contributions",
    }
    assert set(router.meta_state({"feature": REALTIME_QUOTES})) == {
        "governance",
        "graph",
        "autonomy",
        "merged",
    }
    assert set(router.meta_explain({"feature": REALTIME_QUOTES})) == {
        "decision_trace",
        "conflict_resolution_path",
        "module_contributions",
        "decision_reason",
    }
    assert set(router.system_brain({"feature": REALTIME_QUOTES})) == {
        "role",
        "system_state",
        "recommended_source",
        "decision_reason",
        "meta_state",
        "meta_decision",
        "meta_explain",
        "safety_boundaries",
    }
    assert set(router.stability_status()) == {
        "system_uptime_score",
        "failure_rate_24h",
        "schema_drift_trend",
        "source_health_trend",
    }
