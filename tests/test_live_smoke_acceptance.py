from __future__ import annotations

from astock_source_router.core.features import (
    DAILY_KLINE,
    FULL_REALTIME_QUOTES,
    INDEX_REALTIME,
    LITE_REALTIME_QUOTES,
    REALTIME_QUOTES,
    TRADE_CALENDAR,
)
from astock_source_router.core.policy import DEFAULT_SOURCE_POLICY
from scripts.smoke_test_live import _live_acceptance_decision


def _result(source_name: str, feature: str, status: str) -> dict[str, object]:
    return {
        "source": source_name,
        "source_name": source_name,
        "batch": "primary",
        "feature": feature,
        "status": status,
    }


def test_default_policy_uses_live_verified_default_paths():
    assert DEFAULT_SOURCE_POLICY[DAILY_KLINE] == ["akshare", "baostock"]
    assert DEFAULT_SOURCE_POLICY[TRADE_CALENDAR] == ["akshare", "baostock"]
    assert DEFAULT_SOURCE_POLICY[REALTIME_QUOTES] == ["pytdx", "easyquotation_sina", "easyquotation_tencent"]
    assert DEFAULT_SOURCE_POLICY[FULL_REALTIME_QUOTES] == ["pytdx", "easyquotation_sina", "easyquotation_tencent"]
    assert DEFAULT_SOURCE_POLICY[LITE_REALTIME_QUOTES] == ["adata"]
    assert DEFAULT_SOURCE_POLICY[INDEX_REALTIME] == ["pytdx", "easyquotation_sina", "easyquotation_tencent", "akshare"]


def test_live_acceptance_partial_when_realtime_backup_is_missing():
    results = [
        _result("baostock", DAILY_KLINE, "PASS"),
        _result("akshare", DAILY_KLINE, "PASS"),
        _result("baostock", TRADE_CALENDAR, "PASS"),
        _result("akshare", TRADE_CALENDAR, "PASS"),
        _result("pytdx", REALTIME_QUOTES, "PASS"),
        _result("easyquotation_sina", REALTIME_QUOTES, "FAIL"),
        _result("easyquotation_tencent", REALTIME_QUOTES, "FAIL"),
        _result("pytdx", FULL_REALTIME_QUOTES, "PASS"),
        _result("easyquotation_sina", FULL_REALTIME_QUOTES, "FAIL"),
        _result("easyquotation_tencent", FULL_REALTIME_QUOTES, "FAIL"),
        _result("pytdx", INDEX_REALTIME, "PASS"),
        _result("easyquotation_sina", INDEX_REALTIME, "PASS"),
        _result("easyquotation_tencent", INDEX_REALTIME, "FAIL"),
    ]

    decision = _live_acceptance_decision(results, {"live_enabled": "PASS"})

    assert decision["verdict"] == "PARTIAL_PASS"
    assert decision["allow_task013"] is False
    assert decision["allow_task012_2"] is True
    assert decision["allow_s0_post_market_readonly_sandbox"] == "conditional"
    assert decision["allow_s0_realtime_sandbox"] is False
    assert decision["allow_s0_production"] is False


def test_live_acceptance_fails_when_post_market_coverage_is_missing():
    results = [
        _result("baostock", DAILY_KLINE, "PASS"),
        _result("baostock", TRADE_CALENDAR, "PASS"),
        _result("pytdx", REALTIME_QUOTES, "PASS"),
        _result("easyquotation_sina", REALTIME_QUOTES, "PASS"),
        _result("easyquotation_sina", FULL_REALTIME_QUOTES, "PASS"),
        _result("pytdx", FULL_REALTIME_QUOTES, "PASS"),
        _result("easyquotation_tencent", FULL_REALTIME_QUOTES, "PASS"),
        _result("pytdx", INDEX_REALTIME, "PASS"),
        _result("easyquotation_sina", INDEX_REALTIME, "PASS"),
        _result("easyquotation_tencent", INDEX_REALTIME, "PASS"),
    ]

    decision = _live_acceptance_decision(results, {"live_enabled": "PASS"})

    assert decision["verdict"] == "PARTIAL_PASS"
    assert decision["allow_task013"] is False
    assert decision["allow_task012_2"] is True
    assert decision["allow_s0_post_market_readonly_sandbox"] == "denied"
