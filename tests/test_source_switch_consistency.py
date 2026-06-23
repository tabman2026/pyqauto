from __future__ import annotations

import pandas as pd

from astock_source_router.core.features import DAILY_KLINE, FULL_REALTIME_QUOTES, REALTIME_QUOTES
from astock_source_router.core.source_switch_consistency import (
    compare_source_switch,
    fixture_for_path,
    run_source_switch_consistency,
)


def test_fixture_source_switch_paths_have_no_block():
    report = run_source_switch_consistency(enabled=True)

    assert report["overall_status"] in {"PASS", "WARN"}
    assert report["has_block"] is False
    assert {item["path"] for item in report["results"]} == {
        "pytdx->easyquotation_sina",
        "easyquotation_sina->easyquotation_tencent",
        "akshare->baostock",
        "akshare_hist->akshare_stock_zh_a_daily_low_frequency",
    }


def test_adjust_type_conflict_blocks_daily_switch():
    left, right = fixture_for_path("akshare", "baostock", DAILY_KLINE)
    right["adjust_type"] = "qfq"

    result = compare_source_switch(
        left,
        right,
        left_source="akshare",
        right_source="baostock",
        feature=DAILY_KLINE,
    )

    assert result["status"] == "FAIL"
    assert result["has_block"] is True
    assert any(item["code"] == "adjust_type_conflict" for item in result["issues"])


def test_missing_realtime_last_price_blocks_switch():
    left, right = fixture_for_path("pytdx", "easyquotation_sina", REALTIME_QUOTES)
    right = right.drop(columns=["last_price"])

    result = compare_source_switch(
        left,
        right,
        left_source="pytdx",
        right_source="easyquotation_sina",
        feature=REALTIME_QUOTES,
    )

    assert result["has_block"] is True
    assert any(item["code"] == "missing_required_fields" for item in result["issues"])


def test_lite_source_as_full_blocks():
    df = pd.DataFrame(
        [
            {
                "date": "2026-06-12",
                "time": "10:00:00",
                "code": "000001",
                "last_price": 10.1,
                "volume": 1000,
                "amount": 100000,
                "pct_chg": 1.0,
            }
        ]
    )

    result = compare_source_switch(
        df,
        df,
        left_source="adata",
        right_source="easyquotation_sina",
        feature=FULL_REALTIME_QUOTES,
    )

    assert result["has_block"] is True
    assert any(item["code"] == "lite_realtime_used_as_full" for item in result["issues"])
