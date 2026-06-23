from __future__ import annotations

from pathlib import Path

from astock_source_router.adapters.fake_adapter import FakeAdapter
from astock_source_router.core.features import DAILY_KLINE, REALTIME_QUOTES
from astock_source_router.core.policy import SourcePolicy
from astock_source_router.core.router import MarketRouter
from astock_source_router.core.schema import REQUIRED_COLUMNS

API_DECISION_KEYS = {
    "system_state",
    "recommended_source",
    "decision_reason",
    "winning_rule",
    "conflict_resolution_path",
    "module_contributions",
}
API_EXPLAIN_KEYS = {
    "decision_trace",
    "conflict_resolution_path",
    "module_contributions",
    "decision_reason",
}
SOURCE_HEALTH_KEYS = {"api_version", "sources", "health"}
STABILITY_STATUS_KEYS = {
    "system_uptime_score",
    "failure_rate_24h",
    "schema_drift_trend",
    "source_health_trend",
}
DIAGNOSE_KEYS = {
    "api_version",
    "router",
    "registered_sources",
    "source_policy",
    "cache_enabled",
    "sqlite_audit_enabled",
    "autonomy",
    "source_health",
    "safety_boundaries",
}


def _v1_router(test_config) -> MarketRouter:
    policy = SourcePolicy(
        {
            REALTIME_QUOTES: ["fake"],
            DAILY_KLINE: ["fake"],
        }
    )
    return MarketRouter(config=test_config, source_policy=policy, adapters=[FakeAdapter()], auto_register=False)


def test_v1_public_router_methods_exist() -> None:
    for method_name in (
        "meta_decision",
        "meta_explain",
        "source_health",
        "kline",
        "realtime_quotes",
        "stability_status",
        "diagnose",
    ):
        assert callable(getattr(MarketRouter, method_name))


def test_v1_api_return_keys_are_frozen(test_config) -> None:
    router = _v1_router(test_config)

    assert set(router.meta_decision(context={"feature": REALTIME_QUOTES})) == API_DECISION_KEYS
    assert set(router.meta_explain(context={"feature": REALTIME_QUOTES})) == API_EXPLAIN_KEYS
    assert set(router.source_health()) == SOURCE_HEALTH_KEYS
    assert set(router.stability_status()) == STABILITY_STATUS_KEYS
    assert set(router.diagnose()) == DIAGNOSE_KEYS


def test_v1_realtime_and_kline_return_standard_dataframes(test_config) -> None:
    router = _v1_router(test_config)

    quotes = router.realtime_quotes(["000001"])
    assert REQUIRED_COLUMNS[REALTIME_QUOTES] == [
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
    assert set(REQUIRED_COLUMNS[REALTIME_QUOTES]).issubset(quotes.columns)
    assert quotes.loc[0, "source"] == "fake"

    bars = router.kline("000001", start_date="20260611", end_date="20260611", period="daily")
    assert REQUIRED_COLUMNS[DAILY_KLINE] == [
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
    assert set(REQUIRED_COLUMNS[DAILY_KLINE]).issubset(bars.columns)
    assert bars.loc[0, "source"] == "fake"


def test_v1_freeze_documents_exist() -> None:
    for relative_path in (
        "docs/V1_API_FREEZE.md",
        "docs/ADAPTER_CONTRACT_V1.md",
        "docs/SYSTEM_BEHAVIOR_FREEZE.md",
        "docs/V1_ARCHITECTURE.md",
    ):
        assert Path(relative_path).read_text(encoding="utf-8")
