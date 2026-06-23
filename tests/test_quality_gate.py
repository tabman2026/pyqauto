from __future__ import annotations

import pandas as pd
import pytest

from astock_source_router.adapters.fake_adapter import FakeAdapter
from astock_source_router.core.errors import DataQualityError
from astock_source_router.core.features import (
    DAILY_KLINE,
    FULL_REALTIME_QUOTES,
    LITE_REALTIME_QUOTES,
    REALTIME_QUOTES,
)
from astock_source_router.core.schema import (
    add_source_columns,
    coerce_standard_types,
    ensure_dataframe,
    validate_dataframe,
)


def _realtime_df():
    df = FakeAdapter().fetch_realtime_quotes(["000001"])
    return add_source_columns(df, source="fake", latency_ms=1.0)


def test_quality_gate_detects_type_error():
    df = _realtime_df()
    df["last_price"] = df["last_price"].astype(object)
    df.loc[0, "last_price"] = "not-a-number"
    df = coerce_standard_types(df)

    report = validate_dataframe(REALTIME_QUOTES, df)

    assert not report.is_valid
    assert "field_type_error:last_price" in report.warnings


def test_quality_gate_detects_zero_price_and_amount():
    df = _realtime_df()
    df.loc[0, "last_price"] = 0
    df.loc[0, "amount"] = 0
    df = coerce_standard_types(df)

    report = validate_dataframe(REALTIME_QUOTES, df)

    assert not report.is_valid
    assert "zero_price:last_price" in report.warnings
    assert "zero_amount" in report.warnings


def test_quality_gate_detects_target_date_anomaly():
    df = FakeAdapter().fetch_daily_kline("000001", "20260611", "20260611")
    df = add_source_columns(df, source="fake", latency_ms=1.0)
    df = coerce_standard_types(df)

    report = validate_dataframe(
        DAILY_KLINE,
        df,
        context={"start_date": "20260101", "end_date": "20260131", "min_expected_rows": 1},
    )

    assert not report.is_valid
    assert "target_date_anomaly:after_end_date" in report.warnings


def test_quality_gate_detects_insufficient_rows():
    df = _realtime_df()
    df = coerce_standard_types(df)

    report = validate_dataframe(REALTIME_QUOTES, df, context={"min_expected_rows": 2})

    assert not report.is_valid
    assert "insufficient_rows:1/2" in report.warnings


def test_quality_gate_detects_stale_realtime_data():
    df = _realtime_df()
    df["data_timestamp"] = "2000-01-01T00:00:00+00:00"
    df = coerce_standard_types(df)

    report = validate_dataframe(REALTIME_QUOTES, df, context={"realtime_stale_after_seconds": 1})

    assert not report.is_valid
    assert "realtime_stale:data_timestamp_expired" in report.warnings


def test_lite_realtime_gate_does_not_replace_full_gate():
    df = _realtime_df().drop(columns=["pre_close", "open", "high", "low"])
    df = coerce_standard_types(df)

    full_report = validate_dataframe(FULL_REALTIME_QUOTES, df)
    lite_report = validate_dataframe(LITE_REALTIME_QUOTES, df)

    assert not full_report.is_valid
    assert set(full_report.missing_fields) == {"pre_close", "open", "high", "low"}
    assert lite_report.is_valid


def test_quality_gate_detects_blocked_html_response():
    with pytest.raises(DataQualityError):
        ensure_dataframe("<html>验证码 / 风控</html>")

    df = pd.DataFrame([{"date": "2026-06-11", "code": "000001", "name": "<html>captcha</html>"}])
    df = add_source_columns(df, source="fake", latency_ms=1.0)
    report = validate_dataframe(REALTIME_QUOTES, df)

    assert not report.is_valid
    assert "blocked_html_or_risk_control_response" in report.warnings
