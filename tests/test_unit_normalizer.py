from __future__ import annotations

import pandas as pd

from astock_source_router.core.unit_normalizer import (
    normalize_amount,
    normalize_daily_kline_units,
    normalize_pct_chg,
    normalize_realtime_units,
    normalize_volume,
)


def test_volume_lot_to_share():
    normalized = normalize_volume(123, "akshare", "daily_kline")

    assert normalized["raw_value"] == 123
    assert normalized["raw_unit"] == "lot"
    assert normalized["normalized_value"] == 12300
    assert normalized["normalized_unit"] == "share"
    assert normalized["conversion_factor"] == 100


def test_amount_wan_and_yi_yuan_to_yuan():
    wan = normalize_amount(12.3, "easyquotation_tencent", "realtime_quotes")
    yi = normalize_amount(2, "unit_test_yi_yuan", "amount_check")

    assert wan["normalized_value"] == 123000
    assert wan["normalized_unit"] == "yuan"
    assert wan["conversion_factor"] == 10000
    assert yi["normalized_value"] == 200000000
    assert yi["normalized_unit"] == "yuan"
    assert yi["conversion_factor"] == 100000000


def test_pct_chg_ratio_to_percent_and_derived():
    ratio = normalize_pct_chg(0.0123, "unit_test_ratio", function_name="pct_check")
    derived = normalize_pct_chg(None, "pytdx", close=10.1, pre_close=10.0, function_name="realtime_quotes")

    assert round(float(ratio["pct_chg"]), 6) == 1.23
    assert ratio["pct_chg_unit"] == "percent"
    assert bool(derived["pct_chg_derived"])
    assert round(float(derived["pct_chg"]), 6) == 1.0
    assert derived["pct_chg_formula"] == "(close - pre_close) / pre_close * 100"


def test_dataframe_normalizer_preserves_raw_and_warnings():
    df = pd.DataFrame(
        [
            {
                "date": "2026-06-11",
                "code": "000001",
                "open": 10.0,
                "high": 10.2,
                "low": 9.9,
                "close": 10.1,
                "pre_close": 10.0,
                "volume": 1000,
                "amount": 10100000,
                "pct_chg": 1.0,
                "adjust_type": "none",
                "field_warnings": ["existing_warning"],
            }
        ]
    )

    out = normalize_daily_kline_units(df, "akshare")

    assert out.at[0, "raw_volume"] == 1000
    assert out.at[0, "volume"] == 100000
    assert out.at[0, "volume_normalized"] == 100000
    assert out.at[0, "volume_normalized_unit"] == "share"
    assert out.at[0, "raw_amount"] == 10100000
    assert out.at[0, "amount_normalized_unit"] == "yuan"
    assert "existing_warning" in out.at[0, "field_warnings"]
    assert out.at[0, "source"] == "akshare"


def test_unknown_unit_is_not_forced_and_warns():
    df = pd.DataFrame(
        [
            {
                "date": "2026-06-11",
                "code": "000001",
                "open": 10.0,
                "high": 10.2,
                "low": 9.9,
                "close": 10.1,
                "pre_close": 10.0,
                "volume": 1000,
                "amount": 5,
                "pct_chg": 1.0,
                "adjust_type": "none",
            }
        ]
    )

    out = normalize_daily_kline_units(df, "unit_test_unknown")

    assert out.at[0, "volume"] == 1000
    assert out.at[0, "volume_normalized"] == 1000
    assert out.at[0, "volume_normalized_unit"] == "unknown"
    assert any("unit_unknown:volume" in warning for warning in out.at[0, "field_warnings"])
    assert any("unit_unknown:amount" in warning for warning in out.at[0, "field_warnings"])


def test_realtime_pytdx_pct_chg_is_marked_derived():
    df = pd.DataFrame(
        [
            {
                "date": "2026-06-12",
                "time": "10:00:00",
                "code": "000001",
                "last_price": 10.1,
                "pre_close": 10.0,
                "open": 10.0,
                "high": 10.2,
                "low": 9.9,
                "volume": 1000,
                "amount": 10100000,
                "pct_chg": 99.0,
            }
        ]
    )

    out = normalize_realtime_units(df, "pytdx")

    assert bool(out.at[0, "pct_chg_derived"])
    assert round(float(out.at[0, "pct_chg"]), 6) == 1.0
    assert out.at[0, "raw_pct_chg"] == 99.0
