from __future__ import annotations

from astock_source_router.core.data_usage_guard import assess_data_usage


def test_after_close_data_is_not_allowed_for_intraday():
    decision = assess_data_usage(
        target_trade_date="2026-06-11",
        request_time="2026-06-11T16:00:00+08:00",
        data_time="2026-06-11T15:45:00+08:00",
        usage_mode="intraday",
    )

    assert not decision.allow_intraday
    assert decision.allow_after_close
    assert decision.reason == "after_close_or_non_intraday_data_not_allowed_for_intraday"


def test_after_close_usage_requires_visible_time():
    decision = assess_data_usage(
        target_trade_date="2026-06-11",
        request_time="2026-06-11T14:30:00+08:00",
        data_time="2026-06-11T14:00:00+08:00",
        usage_mode="after_close",
    )

    assert not decision.allow_after_close
    assert decision.reason == "after_close_data_not_visible_yet"


def test_backtest_records_data_visibility():
    decision = assess_data_usage(
        target_trade_date="2026-06-11",
        request_time="2026-06-12T09:00:00+08:00",
        data_time="2026-06-11T15:45:00+08:00",
        usage_mode="backtest",
    )

    assert decision.allow_backtest
    assert decision.to_dict()["target_trade_date"] == "2026-06-11"
