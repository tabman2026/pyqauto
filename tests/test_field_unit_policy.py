from __future__ import annotations

from astock_source_router.core.policy import DEFAULT_SOURCE_POLICY
from astock_source_router.core.unit_policy import (
    load_field_unit_policy,
    load_source_unit_policy,
    unit_assumption,
)


def test_field_unit_policy_freezes_standard_units():
    policy = load_field_unit_policy()
    units = policy["standard_units"]

    assert units["volume"]["standard_unit"] == "share"
    assert units["amount"]["standard_unit"] == "yuan"
    assert units["pct_chg"]["standard_unit"] == "percent"
    assert "raw_volume" in units["volume"]["required_fields"]
    assert "raw_amount" in units["amount"]["required_fields"]
    assert "pct_chg_derived" in units["pct_chg"]["required_fields"]


def test_source_unit_policy_covers_required_sources_without_high_confidence():
    policy = load_source_unit_policy()

    for source in ["pytdx", "easyquotation_sina", "easyquotation_tencent", "akshare", "baostock", "adata"]:
        assert source in policy

    high_confidence = []
    for source, source_rules in policy.items():
        if not isinstance(source_rules, dict):
            continue
        for feature, feature_rules in source_rules.items():
            if isinstance(feature_rules, dict) and feature_rules.get("confidence") == "high":
                high_confidence.append(f"{source}.{feature}")
    assert high_confidence == []


def test_unit_assumptions_for_warn_fields_are_not_silent():
    akshare_volume = unit_assumption("akshare", "daily_kline", "volume")
    sina_volume = unit_assumption("easyquotation_sina", "realtime_quotes", "volume")

    assert akshare_volume["canonical_unit"] == "lot"
    assert akshare_volume["confidence"] == "medium"
    assert sina_volume["canonical_unit"] == "unknown"
    assert sina_volume["confidence"] == "low"


def test_default_source_policy_order_is_not_changed():
    assert DEFAULT_SOURCE_POLICY["realtime_quotes"] == [
        "pytdx",
        "easyquotation_sina",
        "easyquotation_tencent",
    ]
    assert DEFAULT_SOURCE_POLICY["full_realtime_quotes"] == [
        "pytdx",
        "easyquotation_sina",
        "easyquotation_tencent",
    ]
    assert DEFAULT_SOURCE_POLICY["daily_kline"] == ["akshare", "baostock"]
    assert DEFAULT_SOURCE_POLICY["trade_calendar"] == ["akshare", "baostock"]
    assert DEFAULT_SOURCE_POLICY["lite_realtime_quotes"] == ["adata"]
