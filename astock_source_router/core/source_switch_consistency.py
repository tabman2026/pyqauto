from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

import pandas as pd

from astock_source_router.core.features import (
    DAILY_KLINE,
    FULL_REALTIME_QUOTES,
    INDEX_REALTIME,
    REALTIME_QUOTES,
)
from astock_source_router.core.policy import DEFAULT_SOURCE_POLICY
from astock_source_router.core.unit_normalizer import (
    normalize_daily_kline_units,
    normalize_index_units,
    normalize_realtime_units,
)

PRICE_TOLERANCE_ABS = 0.01
PRICE_TOLERANCE_PCT = 0.05
VOLUME_TOLERANCE_PCT = 5.0
AMOUNT_TOLERANCE_PCT = 5.0
PCT_CHG_TOLERANCE_ABS = 0.05
TIMESTAMP_LAG_TOLERANCE_SECONDS = 30.0

SWITCH_PATHS = [
    ("pytdx", "easyquotation_sina", REALTIME_QUOTES),
    ("easyquotation_sina", "easyquotation_tencent", FULL_REALTIME_QUOTES),
    ("akshare", "baostock", DAILY_KLINE),
    ("akshare_hist", "akshare_stock_zh_a_daily_low_frequency", DAILY_KLINE),
]


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def issue(severity: str, code: str, message: str, **details: Any) -> dict[str, Any]:
    return {
        "severity": severity,
        "code": code,
        "message": message,
        "details": details,
    }


def status_from_issues(issues: list[dict[str, Any]]) -> str:
    severities = {item.get("severity") for item in issues}
    if "BLOCK" in severities or "FAIL" in severities:
        return "FAIL"
    if "WARN" in severities:
        return "WARN"
    return "PASS"


def has_block(issues: list[dict[str, Any]]) -> bool:
    return any(item.get("severity") == "BLOCK" for item in issues)


def normalize_for_feature(df: pd.DataFrame, source: str, feature: str) -> pd.DataFrame:
    if feature == DAILY_KLINE:
        return normalize_daily_kline_units(df, source)
    if feature == INDEX_REALTIME:
        return normalize_index_units(df, source)
    return normalize_realtime_units(df, source)


def required_fields(feature: str) -> list[str]:
    if feature == DAILY_KLINE:
        return ["date", "code", "open", "high", "low", "close", "source", "adjust_type"]
    return ["date", "code", "last_price", "source", "data_timestamp"]


def price_fields(feature: str) -> list[str]:
    if feature == DAILY_KLINE:
        return ["open", "high", "low", "close", "pre_close"]
    return ["last_price", "open", "high", "low", "pre_close"]


def compare_key(feature: str) -> list[str]:
    return ["date", "code"] if feature == DAILY_KLINE else ["code"]


def _missing_required(df: pd.DataFrame, feature: str, side: str, issues: list[dict[str, Any]]) -> None:
    missing = [field for field in required_fields(feature) if field not in df.columns]
    if missing:
        severity = "BLOCK" if {"code", "date", "source", "last_price", "open", "high", "low", "close"} & set(missing) else "FAIL"
        issues.append(
            issue(
                severity,
                "missing_required_fields",
                f"{side} missing required fields",
                side=side,
                missing_fields=missing,
            )
        )


def _unit_checks(
    df: pd.DataFrame,
    feature: str,
    side: str,
    issues: list[dict[str, Any]],
    strong_unit_fields: set[str],
) -> None:
    for field, unit_field, expected in [
        ("volume", "volume_normalized_unit", "share"),
        ("amount", "amount_normalized_unit", "yuan"),
    ]:
        if field not in df.columns:
            continue
        units = set(df.get(unit_field, pd.Series(["unknown"])).dropna().astype(str))
        if not units or units == {"unknown"}:
            severity = "BLOCK" if field in strong_unit_fields else "WARN"
            issues.append(
                issue(
                    severity,
                    "unit_unknown",
                    f"{side} {field} unit is unknown",
                    side=side,
                    field=field,
                    feature=feature,
                )
            )
        elif units != {expected}:
            issues.append(
                issue(
                    "WARN",
                    "unit_not_standard",
                    f"{side} {field} normalized unit is not standard",
                    side=side,
                    field=field,
                    units=sorted(units),
                    expected=expected,
                )
            )


def _type_checks(df: pd.DataFrame, side: str, issues: list[dict[str, Any]]) -> None:
    for field in ["open", "high", "low", "close", "pre_close", "last_price", "volume", "amount", "pct_chg"]:
        if field not in df.columns:
            continue
        if pd.to_numeric(df[field], errors="coerce").isna().any():
            issues.append(issue("FAIL", "field_type_error", f"{side} {field} contains non-numeric values", field=field))


def _relative_diff_pct(left: pd.Series, right: pd.Series) -> pd.Series:
    denominator = left.abs().where(left.abs() > 1e-12, other=right.abs())
    denominator = denominator.where(denominator > 1e-12, other=1.0)
    return (left - right).abs() / denominator * 100


def _compare_numeric(
    joined: pd.DataFrame,
    field: str,
    issues: list[dict[str, Any]],
    *,
    kind: str,
) -> None:
    left_col = f"{field}_left"
    right_col = f"{field}_right"
    if left_col not in joined.columns or right_col not in joined.columns:
        return
    left = pd.to_numeric(joined[left_col], errors="coerce")
    right = pd.to_numeric(joined[right_col], errors="coerce")
    abs_diff = (left - right).abs()
    pct_diff = _relative_diff_pct(left, right)
    max_abs = float(abs_diff.max()) if len(abs_diff) else 0.0
    max_pct = float(pct_diff.max()) if len(pct_diff) else 0.0
    if kind == "price" and max_abs > PRICE_TOLERANCE_ABS and max_pct > PRICE_TOLERANCE_PCT:
        issues.append(
            issue("WARN", "price_diff_exceeds_tolerance", f"{field} price differs after switch", field=field, max_abs_diff=max_abs, max_pct_diff=max_pct)
        )
    elif kind == "volume" and max_pct > VOLUME_TOLERANCE_PCT:
        issues.append(issue("WARN", "volume_diff_exceeds_tolerance", "volume differs after switch", max_pct_diff=max_pct))
    elif kind == "amount" and max_pct > AMOUNT_TOLERANCE_PCT:
        issues.append(issue("WARN", "amount_diff_exceeds_tolerance", "amount differs after switch", max_pct_diff=max_pct))
    elif kind == "pct_chg" and max_abs > PCT_CHG_TOLERANCE_ABS:
        issues.append(issue("WARN", "pct_chg_diff_exceeds_tolerance", "pct_chg differs after switch", max_abs_diff=max_abs))


def _compare_timestamps(joined: pd.DataFrame, issues: list[dict[str, Any]]) -> None:
    if "data_timestamp_left" not in joined.columns or "data_timestamp_right" not in joined.columns:
        return
    left = pd.to_datetime(joined["data_timestamp_left"], errors="coerce", utc=True)
    right = pd.to_datetime(joined["data_timestamp_right"], errors="coerce", utc=True)
    valid = left.notna() & right.notna()
    if not valid.any():
        issues.append(issue("WARN", "timestamp_invalid", "data_timestamp cannot be compared"))
        return
    max_lag = float((left[valid] - right[valid]).abs().dt.total_seconds().max())
    if max_lag > TIMESTAMP_LAG_TOLERANCE_SECONDS:
        issues.append(issue("WARN", "timestamp_lag_exceeds_tolerance", "data_timestamp lag differs after switch", max_lag_seconds=max_lag))


def _compare_adjust_type(joined: pd.DataFrame, issues: list[dict[str, Any]]) -> None:
    if "adjust_type_left" not in joined.columns or "adjust_type_right" not in joined.columns:
        issues.append(issue("BLOCK", "adjust_type_missing", "daily_kline adjust_type missing during switch comparison"))
        return
    mismatch = joined["adjust_type_left"].astype(str) != joined["adjust_type_right"].astype(str)
    if mismatch.any():
        issues.append(
            issue(
                "BLOCK",
                "adjust_type_conflict",
                "daily_kline adjust_type conflicts across switch path",
                left_values=sorted(joined.loc[mismatch, "adjust_type_left"].astype(str).unique()),
                right_values=sorted(joined.loc[mismatch, "adjust_type_right"].astype(str).unique()),
            )
        )


def _warning_count(df: pd.DataFrame) -> int:
    if "field_warnings" not in df.columns:
        return 0
    total = 0
    for value in df["field_warnings"]:
        if isinstance(value, list):
            total += len(value)
        elif pd.notna(value) and str(value).strip():
            total += 1
    return total


def compare_source_switch(
    left: pd.DataFrame,
    right: pd.DataFrame,
    *,
    left_source: str,
    right_source: str,
    feature: str,
    path_name: str | None = None,
    strong_unit_fields: set[str] | None = None,
) -> dict[str, Any]:
    strong_unit_fields = strong_unit_fields or set()
    path_name = path_name or f"{left_source}->{right_source}:{feature}"
    issues: list[dict[str, Any]] = []
    if left_source == "adata" and feature in {REALTIME_QUOTES, FULL_REALTIME_QUOTES}:
        issues.append(issue("BLOCK", "lite_realtime_used_as_full", "adata lite source cannot be used for full realtime"))
    if right_source == "adata" and feature in {REALTIME_QUOTES, FULL_REALTIME_QUOTES}:
        issues.append(issue("BLOCK", "lite_realtime_used_as_full", "adata lite source cannot be used for full realtime"))

    left_norm = normalize_for_feature(left, left_source, feature)
    right_norm = normalize_for_feature(right, right_source, feature)
    _missing_required(left_norm, feature, "left", issues)
    _missing_required(right_norm, feature, "right", issues)
    _unit_checks(left_norm, feature, "left", issues, strong_unit_fields)
    _unit_checks(right_norm, feature, "right", issues, strong_unit_fields)
    _type_checks(left_norm, "left", issues)
    _type_checks(right_norm, "right", issues)

    keys = compare_key(feature)
    if not all(key in left_norm.columns and key in right_norm.columns for key in keys):
        joined = pd.DataFrame()
    else:
        joined = left_norm.merge(right_norm, on=keys, how="inner", suffixes=("_left", "_right"))
        if joined.empty:
            issues.append(issue("FAIL", "no_common_rows", "no common rows after source switch", keys=keys))

    if not joined.empty:
        for field in price_fields(feature):
            _compare_numeric(joined, field, issues, kind="price")
        _compare_numeric(joined, "volume", issues, kind="volume")
        _compare_numeric(joined, "amount", issues, kind="amount")
        _compare_numeric(joined, "pct_chg", issues, kind="pct_chg")
        if feature == DAILY_KLINE:
            _compare_adjust_type(joined, issues)
        else:
            _compare_timestamps(joined, issues)

    left_warning_count = _warning_count(left_norm)
    right_warning_count = _warning_count(right_norm)
    if right_warning_count > left_warning_count:
        issues.append(
            issue(
                "WARN",
                "field_warnings_expanded",
                "field_warnings expanded after source switch",
                left_warning_count=left_warning_count,
                right_warning_count=right_warning_count,
            )
        )

    status = status_from_issues(issues)
    return {
        "path": path_name,
        "feature": feature,
        "left_source": left_source,
        "right_source": right_source,
        "status": status,
        "has_block": has_block(issues),
        "issues": issues,
        "details": {
            "left_columns": list(left_norm.columns),
            "right_columns": list(right_norm.columns),
            "left_rows": int(len(left_norm)),
            "right_rows": int(len(right_norm)),
            "common_rows": int(len(joined)) if "joined" in locals() else 0,
        },
    }


def _sample_realtime(source: str, *, timestamp: str | None = None) -> pd.DataFrame:
    timestamp = timestamp or utc_now()
    base = {
        "date": "2026-06-12",
        "time": "10:00:00",
        "code": "000001",
        "name": "sample",
        "last_price": 10.1,
        "pre_close": 10.0,
        "open": 10.0,
        "high": 10.2,
        "low": 9.9,
        "pct_chg": 1.0,
        "data_timestamp": timestamp,
    }
    if source == "pytdx":
        base.update({"volume": 1000, "amount": 10100000})
    elif source == "easyquotation_tencent":
        base.update({"volume": 1000, "amount": 1010})
    else:
        base.update({"volume": 100000, "amount": 10100000})
    return pd.DataFrame([base])


def _sample_daily(source: str) -> pd.DataFrame:
    volume = 1000 if source in {"akshare", "akshare_hist"} else 100000
    return pd.DataFrame(
        [
            {
                "date": "2026-06-11",
                "code": "000001",
                "open": 10.0,
                "high": 10.2,
                "low": 9.9,
                "close": 10.1,
                "pre_close": 10.0,
                "volume": volume,
                "amount": 10100000,
                "turnover_rate": 1.2,
                "pct_chg": 1.0,
                "adjust_type": "none",
            }
        ]
    )


def fixture_for_path(left_source: str, right_source: str, feature: str) -> tuple[pd.DataFrame, pd.DataFrame]:
    if feature == DAILY_KLINE:
        return _sample_daily(left_source), _sample_daily(right_source)
    timestamp = utc_now()
    return _sample_realtime(left_source, timestamp=timestamp), _sample_realtime(right_source, timestamp=timestamp)


def run_source_switch_consistency(enabled: bool) -> dict[str, Any]:
    if not enabled:
        return {
            "created_at": utc_now(),
            "mode": "skip",
            "overall_status": "SKIP",
            "has_block": False,
            "summary": "Source switch consistency check skipped; set ENABLE_SOURCE_SWITCH_CONSISTENCY_TEST=1 to run fixture checks.",
            "results": [],
        }
    results = []
    for left_source, right_source, feature in SWITCH_PATHS:
        left, right = fixture_for_path(left_source, right_source, feature)
        results.append(
            compare_source_switch(
                left,
                right,
                left_source=left_source,
                right_source=right_source,
                feature=feature,
                path_name=f"{left_source}->{right_source}",
            )
        )
    statuses = {item["status"] for item in results}
    overall = "FAIL" if "FAIL" in statuses else "WARN" if "WARN" in statuses else "PASS"
    return {
        "created_at": utc_now(),
        "mode": "fixture",
        "overall_status": overall,
        "has_block": any(item["has_block"] for item in results),
        "summary": "Fixture source switch consistency completed without changing source policy or raw source data.",
        "default_source_policy": DEFAULT_SOURCE_POLICY,
        "switch_paths": SWITCH_PATHS,
        "results": results,
    }
