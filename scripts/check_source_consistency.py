from __future__ import annotations

import json
import os
import sys
import time
from collections.abc import Callable
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from astock_source_router.adapters.adata_adapter import ADataAdapter  # noqa: E402
from astock_source_router.adapters.akshare_adapter import AkShareAdapter  # noqa: E402
from astock_source_router.adapters.baostock_adapter import BaostockAdapter  # noqa: E402
from astock_source_router.adapters.easyquotation_adapter import EasyQuotationAdapter  # noqa: E402
from astock_source_router.adapters.pytdx_adapter import PytdxAdapter  # noqa: E402
from astock_source_router.core.errors import UnsupportedFeatureError  # noqa: E402
from astock_source_router.core.features import (  # noqa: E402
    FULL_REALTIME_QUOTES,
    LITE_REALTIME_QUOTES,
    REALTIME_QUOTES,
)
from astock_source_router.core.policy import DEFAULT_SOURCE_POLICY  # noqa: E402
from astock_source_router.core.schema import normalize_code  # noqa: E402

ENABLE_ENV_VARS = ("ENABLE_SOURCE_CONSISTENCY_TEST", "ENABLE_LIVE_SMOKE_TEST")
REPORT_PATH = PROJECT_ROOT / "logs" / "source_consistency_report.json"

TEST_CODES = ["000001", "600519"]
START_DATE = "2024-01-02"
END_DATE = "2024-12-31"
REQUEST_SLEEP_SECONDS = 1.2

TOLERANCE_POLICY = {
    "price_abs_diff": 0.01,
    "price_pct_diff": 0.05,
    "volume_pct_diff": 5.0,
    "amount_pct_diff": 5.0,
    "pct_chg_abs_diff": 0.05,
    "turnover_rate_abs_diff": 0.05,
    "realtime_timestamp_lag_seconds": 30.0,
}

INDEX_ALIAS_MAP = {
    "000001": {
        "name": "上证指数",
        "easyquotation_code": "sh000001",
        "akshare_code": "000001",
    },
    "399001": {
        "name": "深证成指",
        "easyquotation_code": "sz399001",
        "akshare_code": "399001",
    },
    "399006": {
        "name": "创业板指",
        "easyquotation_code": "sz399006",
        "akshare_code": "399006",
    },
    "000300": {
        "name": "沪深300",
        "easyquotation_code": "sh000300",
        "akshare_code": "000300",
    },
}

DAILY_REQUIRED_FIELDS = [
    "date",
    "code",
    "open",
    "high",
    "low",
    "close",
    "volume",
    "amount",
    "pct_chg",
    "turnover_rate",
]
FULL_REALTIME_REQUIRED_FIELDS = [
    "code",
    "name",
    "last_price",
    "open",
    "high",
    "low",
    "pre_close",
    "volume",
    "amount",
    "pct_chg",
]
INDEX_REQUIRED_FIELDS = ["code", "name", "last_price", "pct_chg", "volume", "amount"]
LITE_REALTIME_REQUIRED_FIELDS = ["date", "time", "code", "name", "last_price", "volume", "amount", "pct_chg"]
NUMERIC_FIELDS = {
    "open",
    "high",
    "low",
    "close",
    "last_price",
    "pre_close",
    "volume",
    "amount",
    "pct_chg",
    "turnover_rate",
}
SCALE_CANDIDATES = [0.0001, 0.001, 0.01, 0.1, 1.0, 10.0, 100.0, 1000.0, 10000.0]

_LAST_CALL_AT = 0.0


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _live_enabled() -> bool:
    return any(os.environ.get(name) == "1" for name in ENABLE_ENV_VARS)


def _enabled_by() -> list[str]:
    return [name for name in ENABLE_ENV_VARS if os.environ.get(name) == "1"]


def _json_scalar(value: Any) -> Any:
    if pd.isna(value):
        return None
    if hasattr(value, "item"):
        try:
            return value.item()
        except Exception:
            return str(value)
    return value


def _write_report(report: dict[str, Any]) -> None:
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text(json.dumps(report, ensure_ascii=False, indent=2, default=str), encoding="utf-8")


def _issue(severity: str, issue_code: str, message: str, **details: Any) -> dict[str, Any]:
    return {
        "severity": severity,
        "code": issue_code,
        "message": message,
        "details": details,
    }


def _status_from_issues(issues: list[dict[str, Any]]) -> str:
    severities = {item.get("severity") for item in issues}
    if "FAIL" in severities:
        return "FAIL"
    if "WARN" in severities:
        return "WARN"
    return "PASS"


def _result(
    check: str,
    status: str,
    summary: str,
    *,
    issues: list[dict[str, Any]] | None = None,
    details: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        "check": check,
        "status": status,
        "summary": summary,
        "issues": issues or [],
        "details": details or {},
    }


def _wait_between_requests() -> None:
    global _LAST_CALL_AT
    now = time.perf_counter()
    if _LAST_CALL_AT:
        remaining = REQUEST_SLEEP_SECONDS - (now - _LAST_CALL_AT)
        if remaining > 0:
            time.sleep(remaining)
    _LAST_CALL_AT = time.perf_counter()


def _fetch_source(source: str, feature: str, call: Callable[[], pd.DataFrame]) -> dict[str, Any]:
    _wait_between_requests()
    started_at = time.perf_counter()
    try:
        data = call()
        if data is None:
            data = pd.DataFrame()
        if not isinstance(data, pd.DataFrame):
            data = pd.DataFrame(data)
        return {
            "source": source,
            "feature": feature,
            "status": "PASS",
            "row_count": int(len(data)),
            "columns": list(data.columns),
            "elapsed_ms": round((time.perf_counter() - started_at) * 1000, 3),
            "data": data.copy(),
        }
    except Exception as exc:
        return {
            "source": source,
            "feature": feature,
            "status": "FAIL",
            "row_count": 0,
            "columns": [],
            "elapsed_ms": round((time.perf_counter() - started_at) * 1000, 3),
            "error_type": type(exc).__name__,
            "error_message": str(exc),
            "data": pd.DataFrame(),
        }


def _normalize_code_or_text(value: Any) -> str:
    try:
        return normalize_code(value)
    except Exception:
        return str(value).strip()


def _normalize_frame(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    if "code" in out.columns:
        out["code"] = out["code"].map(_normalize_code_or_text)
    if "date" in out.columns:
        out["date"] = pd.to_datetime(out["date"], errors="coerce").dt.strftime("%Y-%m-%d")
    if "time" in out.columns:
        out["time"] = out["time"].astype(str).str[:8]
    for field in NUMERIC_FIELDS.intersection(out.columns):
        out[field] = pd.to_numeric(out[field], errors="coerce")
    return out


def _missing_fields(df: pd.DataFrame, required_fields: list[str]) -> list[str]:
    return [field for field in required_fields if field not in df.columns]


def _null_value_fields(df: pd.DataFrame, fields: list[str]) -> list[str]:
    null_fields = []
    for field in fields:
        if field not in df.columns:
            continue
        series = df[field]
        if series.isna().any() or series.astype(str).str.strip().eq("").any():
            null_fields.append(field)
    return null_fields


def _numeric_problem_fields(df: pd.DataFrame, fields: list[str]) -> list[str]:
    problems = []
    for field in fields:
        if field not in df.columns:
            continue
        numeric = pd.to_numeric(df[field], errors="coerce")
        if numeric.isna().any():
            problems.append(field)
    return problems


def _zero_fields(df: pd.DataFrame, fields: list[str]) -> list[str]:
    zeros = []
    for field in fields:
        if field not in df.columns:
            continue
        numeric = pd.to_numeric(df[field], errors="coerce")
        if (numeric == 0).any():
            zeros.append(field)
    return zeros


def _relative_diff_pct(left: pd.Series, right: pd.Series) -> pd.Series:
    denominator = left.abs().where(left.abs() > 1e-12, other=right.abs())
    denominator = denominator.where(denominator > 1e-12, other=1.0)
    return (left - right).abs() / denominator * 100


def _best_scale(left: pd.Series, right: pd.Series) -> dict[str, Any]:
    left_num = pd.to_numeric(left, errors="coerce")
    right_num = pd.to_numeric(right, errors="coerce")
    valid = left_num.notna() & right_num.notna()
    if not valid.any():
        return {"scale": 1.0, "median_pct_diff": None}
    best_scale = 1.0
    best_score = float("inf")
    for scale in SCALE_CANDIDATES:
        diff = _relative_diff_pct(left_num[valid], right_num[valid] * scale)
        score = float(diff.median()) if len(diff) else float("inf")
        if score < best_score:
            best_score = score
            best_scale = scale
    return {"scale": best_scale, "median_pct_diff": round(best_score, 6)}


def _diff_samples(
    joined: pd.DataFrame,
    left_col: str,
    right_col: str,
    *,
    scale: float = 1.0,
    limit: int = 5,
) -> list[dict[str, Any]]:
    if left_col not in joined.columns or right_col not in joined.columns:
        return []
    left = pd.to_numeric(joined[left_col], errors="coerce")
    right = pd.to_numeric(joined[right_col], errors="coerce") * scale
    diff = pd.DataFrame(
        {
            "date": joined["date"] if "date" in joined.columns else pd.NA,
            "code": joined["code"] if "code" in joined.columns else pd.NA,
            "left": left,
            "right_scaled": right,
            "abs_diff": (left - right).abs(),
            "pct_diff": _relative_diff_pct(left, right),
        }
    )
    diff = diff.sort_values(["pct_diff", "abs_diff"], ascending=False).head(limit)
    return [
        {key: _json_scalar(value) for key, value in row.items()}
        for row in diff.to_dict(orient="records")
    ]


def _compare_price_field(
    joined: pd.DataFrame,
    field: str,
    left_col: str,
    right_col: str,
    issues: list[dict[str, Any]],
    *,
    context: str,
) -> None:
    if left_col not in joined.columns or right_col not in joined.columns:
        return
    left = pd.to_numeric(joined[left_col], errors="coerce")
    right = pd.to_numeric(joined[right_col], errors="coerce")
    abs_diff = (left - right).abs()
    pct_diff = _relative_diff_pct(left, right)
    max_abs = float(abs_diff.max()) if len(abs_diff) else 0.0
    max_pct = float(pct_diff.max()) if len(pct_diff) else 0.0
    if max_abs > TOLERANCE_POLICY["price_abs_diff"] and max_pct > TOLERANCE_POLICY["price_pct_diff"]:
        issues.append(
            _issue(
                "WARN",
                "price_diff_exceeds_tolerance",
                f"{context} {field} 差异超过价格阈值",
                field=field,
                max_abs_diff=round(max_abs, 6),
                max_pct_diff=round(max_pct, 6),
                samples=_diff_samples(joined, left_col, right_col),
            )
        )


def _compare_pct_chg_field(
    joined: pd.DataFrame,
    field: str,
    left_col: str,
    right_col: str,
    issues: list[dict[str, Any]],
    *,
    context: str,
) -> None:
    if left_col not in joined.columns or right_col not in joined.columns:
        return
    left = pd.to_numeric(joined[left_col], errors="coerce")
    right = pd.to_numeric(joined[right_col], errors="coerce")
    abs_diff = (left - right).abs()
    max_abs = float(abs_diff.max()) if len(abs_diff) else 0.0
    if max_abs > TOLERANCE_POLICY["pct_chg_abs_diff"]:
        issues.append(
            _issue(
                "WARN",
                "pct_chg_diff_exceeds_tolerance",
                f"{context} {field} 差异超过涨跌幅阈值",
                field=field,
                max_abs_diff=round(max_abs, 6),
                samples=_diff_samples(joined, left_col, right_col),
            )
        )


def _compare_turnover_rate_field(
    joined: pd.DataFrame,
    left_col: str,
    right_col: str,
    issues: list[dict[str, Any]],
    *,
    context: str,
) -> None:
    if left_col not in joined.columns or right_col not in joined.columns:
        return
    left = pd.to_numeric(joined[left_col], errors="coerce")
    right = pd.to_numeric(joined[right_col], errors="coerce")
    abs_diff = (left - right).abs()
    max_abs = float(abs_diff.max()) if len(abs_diff) else 0.0
    if max_abs > TOLERANCE_POLICY["turnover_rate_abs_diff"]:
        issues.append(
            _issue(
                "WARN",
                "turnover_rate_diff_exceeds_tolerance",
                f"{context} turnover_rate 差异超过换手率阈值",
                max_abs_diff=round(max_abs, 6),
                samples=_diff_samples(joined, left_col, right_col),
            )
        )


def _compare_scaled_field(
    joined: pd.DataFrame,
    field: str,
    left_col: str,
    right_col: str,
    issues: list[dict[str, Any]],
    unit_notes: list[dict[str, Any]],
    *,
    context: str,
    tolerance_key: str,
) -> None:
    if left_col not in joined.columns or right_col not in joined.columns:
        return
    scale_info = _best_scale(joined[left_col], joined[right_col])
    scale = float(scale_info["scale"])
    left = pd.to_numeric(joined[left_col], errors="coerce")
    right = pd.to_numeric(joined[right_col], errors="coerce") * scale
    pct_diff = _relative_diff_pct(left, right)
    max_pct = float(pct_diff.max()) if len(pct_diff) else 0.0
    unit_note = {
        "context": context,
        "field": field,
        "right_source_scale_to_left": scale,
        "median_pct_diff_after_scale": scale_info["median_pct_diff"],
        "assumption": "仅用于一致性比较，不改写任何源原始数据",
    }
    unit_notes.append(unit_note)
    if scale != 1.0:
        issues.append(
            _issue(
                "WARN",
                "unit_scale_inferred",
                f"{context} {field} 推断存在单位比例差异",
                **unit_note,
            )
        )
    if max_pct > TOLERANCE_POLICY[tolerance_key]:
        issues.append(
            _issue(
                "WARN",
                f"{field}_diff_exceeds_tolerance",
                f"{context} {field} 差异超过阈值",
                field=field,
                max_pct_diff_after_scale=round(max_pct, 6),
                scale=scale,
                samples=_diff_samples(joined, left_col, right_col, scale=scale),
            )
        )


def _fetch_daily_frames() -> dict[str, dict[str, Any]]:
    baostock = BaostockAdapter()
    akshare = AkShareAdapter()
    fetched: dict[str, dict[str, Any]] = {}
    for code in TEST_CODES:
        fetched[f"baostock:{code}"] = _fetch_source(
            "baostock",
            "daily_kline",
            lambda code=code: baostock.fetch_daily_kline(code, START_DATE, END_DATE),
        )
        fetched[f"akshare:{code}"] = _fetch_source(
            "akshare",
            "daily_kline",
            lambda code=code: akshare.fetch_daily_kline(code, START_DATE, END_DATE),
        )
    return fetched


def _run_daily_consistency() -> dict[str, Any]:
    issues: list[dict[str, Any]] = []
    unit_notes: list[dict[str, Any]] = []
    details: dict[str, Any] = {"codes": {}, "unit_notes": unit_notes}
    fetched = _fetch_daily_frames()
    for code in TEST_CODES:
        left_fetch = fetched[f"baostock:{code}"]
        right_fetch = fetched[f"akshare:{code}"]
        details["codes"][code] = {
            "baostock": {key: value for key, value in left_fetch.items() if key != "data"},
            "akshare": {key: value for key, value in right_fetch.items() if key != "data"},
        }
        for item in (left_fetch, right_fetch):
            if item["status"] != "PASS":
                issues.append(
                    _issue(
                        "FAIL",
                        "source_fetch_failed",
                        f"{item['source']} daily_kline 获取失败",
                        code=code,
                        error_type=item.get("error_type"),
                        error_message=item.get("error_message"),
                    )
                )
        if left_fetch["status"] != "PASS" or right_fetch["status"] != "PASS":
            continue

        left = _normalize_frame(left_fetch["data"])
        right = _normalize_frame(right_fetch["data"])
        if left.empty or right.empty:
            issues.append(
                _issue(
                    "FAIL",
                    "empty_dataframe",
                    "daily_kline 源返回空表，不能判为一致",
                    code=code,
                    baostock_rows=int(len(left)),
                    akshare_rows=int(len(right)),
                )
            )
            continue

        for source_name, frame in (("baostock", left), ("akshare", right)):
            missing = _missing_fields(frame, DAILY_REQUIRED_FIELDS)
            missing_without_turnover = [field for field in missing if field != "turnover_rate"]
            if missing_without_turnover:
                issues.append(
                    _issue(
                        "FAIL",
                        "missing_required_fields",
                        f"{source_name} daily_kline 缺少关键字段",
                        code=code,
                        missing_fields=missing_without_turnover,
                    )
                )
            if "turnover_rate" in missing:
                issues.append(
                    _issue(
                        "WARN",
                        "turnover_rate_missing",
                        f"{source_name} daily_kline 缺少 turnover_rate，按允许空值记录",
                        code=code,
                    )
                )
            numeric_problems = _numeric_problem_fields(
                frame,
                [field for field in DAILY_REQUIRED_FIELDS if field not in {"date", "code", "turnover_rate"}],
            )
            if numeric_problems:
                issues.append(
                    _issue(
                        "FAIL",
                        "numeric_field_invalid",
                        f"{source_name} daily_kline 存在非数值关键字段",
                        code=code,
                        fields=numeric_problems,
                    )
                )
            zero_prices = _zero_fields(frame, ["open", "high", "low", "close"])
            if zero_prices:
                issues.append(
                    _issue(
                        "FAIL",
                        "zero_price",
                        f"{source_name} daily_kline 存在异常 0 价格",
                        code=code,
                        fields=zero_prices,
                    )
                )

        left_dates = set(left["date"].dropna().astype(str)) if "date" in left.columns else set()
        right_dates = set(right["date"].dropna().astype(str)) if "date" in right.columns else set()
        missing_in_right = sorted(left_dates - right_dates)
        missing_in_left = sorted(right_dates - left_dates)
        if missing_in_right or missing_in_left:
            issues.append(
                _issue(
                    "FAIL",
                    "daily_date_set_mismatch",
                    "baostock 与 akshare daily_kline 日期集合不一致",
                    code=code,
                    baostock_only=missing_in_right[:20],
                    akshare_only=missing_in_left[:20],
                    baostock_only_count=len(missing_in_right),
                    akshare_only_count=len(missing_in_left),
                )
            )

        if "code" in left.columns and left["code"].dropna().ne(code).any():
            issues.append(_issue("FAIL", "code_mismatch", "baostock daily_kline code 不一致", code=code))
        if "code" in right.columns and right["code"].dropna().ne(code).any():
            issues.append(_issue("FAIL", "code_mismatch", "akshare daily_kline code 不一致", code=code))

        common_fields = [field for field in DAILY_REQUIRED_FIELDS if field in left.columns and field in right.columns]
        if not {"date", "code"}.issubset(common_fields):
            continue
        joined = pd.merge(
            left[common_fields],
            right[common_fields],
            on=["date", "code"],
            how="inner",
            suffixes=("_baostock", "_akshare"),
        )
        details["codes"][code]["common_row_count"] = int(len(joined))
        if joined.empty:
            issues.append(
                _issue(
                    "FAIL",
                    "no_common_daily_rows",
                    "baostock 与 akshare daily_kline 无共同日期，不能比较字段",
                    code=code,
                )
            )
            continue
        for field in ["open", "high", "low", "close"]:
            _compare_price_field(
                joined,
                field,
                f"{field}_baostock",
                f"{field}_akshare",
                issues,
                context=f"daily_kline {code} baostock vs akshare",
            )
        _compare_scaled_field(
            joined,
            "volume",
            "volume_baostock",
            "volume_akshare",
            issues,
            unit_notes,
            context=f"daily_kline {code} baostock vs akshare",
            tolerance_key="volume_pct_diff",
        )
        _compare_scaled_field(
            joined,
            "amount",
            "amount_baostock",
            "amount_akshare",
            issues,
            unit_notes,
            context=f"daily_kline {code} baostock vs akshare",
            tolerance_key="amount_pct_diff",
        )
        _compare_pct_chg_field(
            joined,
            "pct_chg",
            "pct_chg_baostock",
            "pct_chg_akshare",
            issues,
            context=f"daily_kline {code} baostock vs akshare",
        )
        if "turnover_rate_baostock" in joined.columns and "turnover_rate_akshare" in joined.columns:
            _compare_turnover_rate_field(
                joined,
                "turnover_rate_baostock",
                "turnover_rate_akshare",
                issues,
                context=f"daily_kline {code} baostock vs akshare",
            )

    status = _status_from_issues(issues)
    return _result(
        "daily_kline_consistency",
        status,
        "baostock daily_kline 与 akshare stock_zh_a_daily/备用日K字段一致性校验",
        issues=issues,
        details=details,
    )


def _run_trade_calendar_consistency() -> dict[str, Any]:
    issues: list[dict[str, Any]] = []
    baostock = BaostockAdapter()
    akshare = AkShareAdapter()
    left_fetch = _fetch_source(
        "baostock",
        "trade_calendar",
        lambda: baostock.fetch_trade_calendar(START_DATE, END_DATE),
    )
    right_fetch = _fetch_source(
        "akshare",
        "trade_calendar",
        lambda: akshare.fetch_trade_calendar(START_DATE, END_DATE),
    )
    details = {
        "baostock": {key: value for key, value in left_fetch.items() if key != "data"},
        "akshare": {key: value for key, value in right_fetch.items() if key != "data"},
    }
    for item in (left_fetch, right_fetch):
        if item["status"] != "PASS":
            issues.append(
                _issue(
                    "FAIL",
                    "source_fetch_failed",
                    f"{item['source']} trade_calendar 获取失败",
                    error_type=item.get("error_type"),
                    error_message=item.get("error_message"),
                )
            )
    if left_fetch["status"] == "PASS" and right_fetch["status"] == "PASS":
        left = _normalize_frame(left_fetch["data"])
        right = _normalize_frame(right_fetch["data"])
        if left.empty or right.empty:
            issues.append(
                _issue(
                    "FAIL",
                    "empty_dataframe",
                    "trade_calendar 源返回空表，不能判为一致",
                    baostock_rows=int(len(left)),
                    akshare_rows=int(len(right)),
                )
            )
        else:
            for source_name, frame in (("baostock", left), ("akshare", right)):
                missing = _missing_fields(frame, ["date", "is_trading_day"])
                if missing:
                    issues.append(
                        _issue(
                            "FAIL",
                            "missing_required_fields",
                            f"{source_name} trade_calendar 缺少关键字段",
                            missing_fields=missing,
                        )
                    )
            if "date" in left.columns and "is_trading_day" in left.columns:
                left_days = set(left[left["is_trading_day"].astype(bool)]["date"].dropna().astype(str))
            else:
                left_days = set()
            if "date" in right.columns and "is_trading_day" in right.columns:
                right_days = set(right[right["is_trading_day"].astype(bool)]["date"].dropna().astype(str))
            else:
                right_days = set()
            baostock_only = sorted(left_days - right_days)
            akshare_only = sorted(right_days - left_days)
            details["baostock_trading_day_count"] = len(left_days)
            details["akshare_trading_day_count"] = len(right_days)
            details["baostock_only_count"] = len(baostock_only)
            details["akshare_only_count"] = len(akshare_only)
            if baostock_only or akshare_only:
                issues.append(
                    _issue(
                        "WARN",
                        "trade_calendar_conflict",
                        "baostock 与 akshare 交易日集合存在差异，后续需人工裁决",
                        baostock_only=baostock_only[:50],
                        akshare_only=akshare_only[:50],
                        baostock_only_count=len(baostock_only),
                        akshare_only_count=len(akshare_only),
                    )
                )

    status = _status_from_issues(issues)
    return _result(
        "trade_calendar_consistency",
        status,
        "baostock trade_calendar 与 akshare tool_trade_date_hist_sina 交易日集合校验",
        issues=issues,
        details=details,
    )


def _rows_by_code(df: pd.DataFrame) -> dict[str, pd.Series]:
    if "code" not in df.columns:
        return {}
    rows: dict[str, pd.Series] = {}
    for _, row in df.iterrows():
        code = _normalize_code_or_text(row.get("code"))
        if code not in rows:
            rows[code] = row
    return rows


def _parse_quote_timestamp(row: pd.Series) -> datetime | None:
    date_value = row.get("date")
    time_value = row.get("time", "00:00:00")
    if pd.isna(date_value):
        return None
    parsed = pd.to_datetime(f"{date_value} {time_value}", errors="coerce")
    if pd.isna(parsed):
        return None
    return parsed.to_pydatetime()


def _compare_name(left: pd.Series, right: pd.Series, issues: list[dict[str, Any]], *, context: str) -> None:
    left_name = str(left.get("name", "")).strip()
    right_name = str(right.get("name", "")).strip()
    if left_name and right_name and left_name != right_name:
        issues.append(
            _issue(
                "WARN",
                "name_diff",
                f"{context} name 存在简称、简繁或来源差异",
                left_name=left_name,
                right_name=right_name,
            )
        )


def _compare_timestamp(
    left: pd.Series,
    right: pd.Series,
    issues: list[dict[str, Any]],
    *,
    context: str,
) -> None:
    left_ts = _parse_quote_timestamp(left)
    right_ts = _parse_quote_timestamp(right)
    if left_ts is None or right_ts is None:
        issues.append(
            _issue(
                "WARN",
                "realtime_timestamp_missing",
                f"{context} 无法解析实时数据时间戳",
                left_timestamp=None if left_ts is None else left_ts.isoformat(),
                right_timestamp=None if right_ts is None else right_ts.isoformat(),
            )
        )
        return
    lag = abs((left_ts - right_ts).total_seconds())
    if lag > TOLERANCE_POLICY["realtime_timestamp_lag_seconds"]:
        issues.append(
            _issue(
                "WARN",
                "realtime_timestamp_lag",
                f"{context} data_timestamp 差异超过阈值",
                lag_seconds=lag,
                left_timestamp=left_ts.isoformat(),
                right_timestamp=right_ts.isoformat(),
            )
        )


def _warn_old_quote_dates(
    rows: dict[str, pd.Series],
    issues: list[dict[str, Any]],
    *,
    source: str,
    check: str,
) -> None:
    today = datetime.now().strftime("%Y-%m-%d")
    for code, row in rows.items():
        quote_date = str(row.get("date", "")).strip()
        if quote_date and quote_date != today:
            issues.append(
                _issue(
                    "WARN",
                    "realtime_quote_date_not_today",
                    f"{source} {check} 返回日期不是当前自然日，按延迟/盘后数据记录",
                    code=code,
                    quote_date=quote_date,
                    current_date=today,
                )
            )


def _validate_realtime_source(
    source_name: str,
    df: pd.DataFrame,
    required_fields: list[str],
    target_codes: list[str],
    issues: list[dict[str, Any]],
    *,
    check: str,
) -> dict[str, pd.Series]:
    missing = _missing_fields(df, required_fields)
    if missing:
        issues.append(
            _issue(
                "FAIL",
                "missing_required_fields",
                f"{source_name} {check} 缺少关键字段，不能作为 full/default 一致性来源",
                missing_fields=missing,
            )
        )
    if df.empty:
        issues.append(_issue("FAIL", "empty_dataframe", f"{source_name} {check} 返回空表"))
        return {}
    numeric_fields = [field for field in required_fields if field in NUMERIC_FIELDS]
    numeric_problems = _numeric_problem_fields(df, numeric_fields)
    if numeric_problems:
        issues.append(
            _issue(
                "FAIL",
                "numeric_field_invalid",
                f"{source_name} {check} 存在非数值关键字段",
                fields=numeric_problems,
            )
        )
    null_fields = _null_value_fields(df, required_fields)
    if null_fields:
        issues.append(
            _issue(
                "FAIL",
                "null_required_values",
                f"{source_name} {check} 存在空关键字段值",
                fields=null_fields,
            )
        )
    zero_prices = _zero_fields(df, [field for field in ["last_price", "open", "high", "low", "pre_close"] if field in required_fields])
    if zero_prices:
        issues.append(
            _issue(
                "FAIL",
                "zero_price",
                f"{source_name} {check} 存在异常 0 价格",
                fields=zero_prices,
            )
        )
    rows = _rows_by_code(df)
    for code in target_codes:
        if code not in rows:
            issues.append(
                _issue(
                    "FAIL",
                    "target_code_missing",
                    f"{source_name} {check} 缺少目标代码",
                    code=code,
                    available_codes=sorted(rows.keys())[:20],
                )
            )
    _warn_old_quote_dates(rows, issues, source=source_name, check=check)
    return rows


def _one_row_join(left: pd.Series, right: pd.Series, code: str) -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "code": code,
                **{f"{field}_left": left.get(field) for field in set(left.index)},
                **{f"{field}_right": right.get(field) for field in set(right.index)},
            }
        ]
    )


def _compare_realtime_rows(
    left: pd.Series,
    right: pd.Series,
    code: str,
    issues: list[dict[str, Any]],
    unit_notes: list[dict[str, Any]],
    *,
    context: str,
    price_fields: list[str],
) -> None:
    joined = _one_row_join(left, right, code)
    _compare_name(left, right, issues, context=context)
    _compare_timestamp(left, right, issues, context=context)
    for field in price_fields:
        _compare_price_field(joined, field, f"{field}_left", f"{field}_right", issues, context=context)
    _compare_scaled_field(
        joined,
        "volume",
        "volume_left",
        "volume_right",
        issues,
        unit_notes,
        context=context,
        tolerance_key="volume_pct_diff",
    )
    _compare_scaled_field(
        joined,
        "amount",
        "amount_left",
        "amount_right",
        issues,
        unit_notes,
        context=context,
        tolerance_key="amount_pct_diff",
    )
    _compare_pct_chg_field(joined, "pct_chg", "pct_chg_left", "pct_chg_right", issues, context=context)


def _run_full_realtime_consistency() -> dict[str, Any]:
    issues: list[dict[str, Any]] = []
    unit_notes: list[dict[str, Any]] = []
    pytdx = PytdxAdapter()
    sina = EasyQuotationAdapter(provider="sina")
    tencent = EasyQuotationAdapter(provider="tencent")
    pytdx_fetch = _fetch_source(
        "pytdx",
        "full_realtime_quotes",
        lambda: pytdx.fetch_full_realtime_quotes(TEST_CODES),
    )
    sina_fetch = _fetch_source(
        "easyquotation_sina",
        "full_realtime_quotes",
        lambda: sina.fetch_full_realtime_quotes(TEST_CODES),
    )
    tencent_fetch = _fetch_source(
        "easyquotation_tencent",
        "full_realtime_quotes",
        lambda: tencent.fetch_full_realtime_quotes(TEST_CODES),
    )
    details = {
        "unit_notes": unit_notes,
        "pytdx": {key: value for key, value in pytdx_fetch.items() if key != "data"},
        "easyquotation_sina": {key: value for key, value in sina_fetch.items() if key != "data"},
        "easyquotation_tencent": {key: value for key, value in tencent_fetch.items() if key != "data"},
    }
    if pytdx_fetch["status"] != "PASS":
        issues.append(
            _issue(
                "FAIL",
                "source_fetch_failed",
                "pytdx full_realtime_quotes 获取失败，不能作为实时主源",
                error_type=pytdx_fetch.get("error_type"),
                error_message=pytdx_fetch.get("error_message"),
            )
        )

    backup_fetches = {
        "easyquotation_sina": sina_fetch,
        "easyquotation_tencent": tencent_fetch,
    }
    backup_pass_names = [name for name, item in backup_fetches.items() if item["status"] == "PASS"]
    if not backup_pass_names:
        issues.append(
            _issue(
                "FAIL",
                "backup_source_fetch_failed",
                "easyquotation_sina / easyquotation_tencent 均未通过 full_realtime_quotes，fallback 不满足要求",
            )
        )
    for name, item in backup_fetches.items():
        if item["status"] != "PASS":
            issues.append(
                _issue(
                    "WARN",
                    "backup_source_fetch_failed",
                    f"{name} full_realtime_quotes 获取失败，另一个 easyquotation 通道若 PASS 则不阻断",
                    error_type=item.get("error_type"),
                    error_message=item.get("error_message"),
                )
            )

    if pytdx_fetch["status"] == "PASS":
        primary = _normalize_frame(pytdx_fetch["data"])
        primary_rows = _validate_realtime_source(
            "pytdx",
            primary,
            FULL_REALTIME_REQUIRED_FIELDS,
            TEST_CODES,
            issues,
            check="full_realtime_quotes",
        )
        for backup_name in backup_pass_names:
            backup = _normalize_frame(backup_fetches[backup_name]["data"])
            backup_rows = _validate_realtime_source(
                backup_name,
                backup,
                FULL_REALTIME_REQUIRED_FIELDS,
                TEST_CODES,
                issues,
                check="full_realtime_quotes",
            )
            for code in TEST_CODES:
                if code not in primary_rows or code not in backup_rows:
                    continue
                _compare_realtime_rows(
                    primary_rows[code],
                    backup_rows[code],
                    code,
                    issues,
                    unit_notes,
                    context=f"full_realtime_quotes {code} pytdx vs {backup_name}",
                    price_fields=["last_price", "open", "high", "low", "pre_close"],
                )
    status = _status_from_issues(issues)
    return _result(
        "full_realtime_quotes_consistency",
        status,
        "pytdx 主源与 easyquotation 备源 full_realtime_quotes 字段一致性校验",
        issues=issues,
        details=details,
    )


def _run_index_realtime_consistency() -> dict[str, Any]:
    issues: list[dict[str, Any]] = []
    unit_notes: list[dict[str, Any]] = []
    target_codes = list(INDEX_ALIAS_MAP)
    sources = {
        "pytdx": _fetch_source(
            "pytdx",
            "index_realtime",
            lambda: PytdxAdapter().fetch_index_realtime(target_codes),
        ),
        "easyquotation_sina": _fetch_source(
            "easyquotation_sina",
            "index_realtime",
            lambda: EasyQuotationAdapter(provider="sina").fetch_index_realtime(target_codes),
        ),
        "easyquotation_tencent": _fetch_source(
            "easyquotation_tencent",
            "index_realtime",
            lambda: EasyQuotationAdapter(provider="tencent").fetch_index_realtime(target_codes),
        ),
        "akshare": _fetch_source(
            "akshare",
            "index_realtime",
            lambda: AkShareAdapter().fetch_index_realtime(target_codes),
        ),
    }
    details: dict[str, Any] = {
        "index_alias_map": INDEX_ALIAS_MAP,
        "unit_notes": unit_notes,
        "sources": {name: {key: value for key, value in fetched.items() if key != "data"} for name, fetched in sources.items()},
    }
    source_rows: dict[str, dict[str, pd.Series]] = {}
    pytdx_pass = sources["pytdx"]["status"] == "PASS"
    backup_names = ["easyquotation_sina", "easyquotation_tencent", "akshare"]
    backup_pass_names = [name for name in backup_names if sources[name]["status"] == "PASS"]

    if not pytdx_pass and len(backup_pass_names) < 2:
        issues.append(
            _issue(
                "FAIL",
                "index_realtime_no_primary_or_backup_combo",
                "pytdx 指数实时未通过，且 easyquotation/akshare 备源组合不足 2 个 PASS",
                backup_pass_sources=backup_pass_names,
            )
        )
    if pytdx_pass and not backup_pass_names:
        issues.append(
            _issue(
                "FAIL",
                "index_realtime_backup_missing",
                "pytdx 指数实时已通过，但没有任何指数 fallback 源 PASS",
            )
        )

    for source_name, fetched in sources.items():
        if fetched["status"] != "PASS":
            severity = "WARN"
            if source_name == "pytdx" and len(backup_pass_names) < 2:
                severity = "FAIL"
            issues.append(
                _issue(
                    severity,
                    "source_fetch_failed",
                    f"{source_name} index_realtime 获取失败",
                    error_type=fetched.get("error_type"),
                    error_message=fetched.get("error_message"),
                )
            )
            continue
        frame = _normalize_frame(fetched["data"])
        source_rows[source_name] = _validate_realtime_source(
            source_name,
            frame,
            INDEX_REQUIRED_FIELDS,
            target_codes,
            issues,
            check="index_realtime",
        )

    if pytdx_pass:
        pairs = [("pytdx", name) for name in backup_pass_names]
    else:
        pairs = [
            ("easyquotation_sina", "easyquotation_tencent"),
            ("easyquotation_sina", "akshare"),
            ("easyquotation_tencent", "akshare"),
        ]
    for left_name, right_name in pairs:
        left_rows = source_rows.get(left_name, {})
        right_rows = source_rows.get(right_name, {})
        for code in target_codes:
            if code not in left_rows or code not in right_rows:
                continue
            _compare_realtime_rows(
                left_rows[code],
                right_rows[code],
                code,
                issues,
                unit_notes,
                context=f"index_realtime {INDEX_ALIAS_MAP[code]['name']} {left_name} vs {right_name}",
                price_fields=["last_price"],
            )

    status = _status_from_issues(issues)
    return _result(
        "index_realtime_consistency",
        status,
        "pytdx 优先，easyquotation / akshare 指数实时 fallback 字段一致性校验",
        issues=issues,
        details=details,
    )


def _run_lite_boundary_check(live_enabled: bool) -> dict[str, Any]:
    issues: list[dict[str, Any]] = []
    details: dict[str, Any] = {
        "default_source_policy": DEFAULT_SOURCE_POLICY,
        "adata_supported_features": sorted(ADataAdapter.supported_features),
        "live_lite_fetch": None,
    }
    if "adata" in DEFAULT_SOURCE_POLICY.get(FULL_REALTIME_QUOTES, []):
        issues.append(
            _issue(
                "FAIL",
                "adata_in_full_policy",
                "adata 出现在 full_realtime_quotes 默认策略中，违反 lite-only 边界",
            )
        )
    if "adata" in DEFAULT_SOURCE_POLICY.get(REALTIME_QUOTES, []):
        issues.append(
            _issue(
                "FAIL",
                "adata_in_realtime_policy",
                "adata 出现在 realtime_quotes 默认策略中，违反 lite-only 边界",
            )
        )
    if DEFAULT_SOURCE_POLICY.get(LITE_REALTIME_QUOTES) != ["adata"]:
        issues.append(
            _issue(
                "FAIL",
                "lite_policy_changed",
                "lite_realtime_quotes 默认策略不是仅 adata",
                actual=DEFAULT_SOURCE_POLICY.get(LITE_REALTIME_QUOTES),
            )
        )
    adapter = ADataAdapter()
    if FULL_REALTIME_QUOTES in adapter.supported_features or REALTIME_QUOTES in adapter.supported_features:
        issues.append(
            _issue(
                "FAIL",
                "adata_adapter_full_capability_exposed",
                "ADataAdapter 对外暴露 full/realtime 能力，违反 lite-only 边界",
                supported_features=sorted(adapter.supported_features),
            )
        )
    if LITE_REALTIME_QUOTES not in adapter.supported_features:
        issues.append(
            _issue(
                "FAIL",
                "adata_lite_capability_missing",
                "ADataAdapter 未声明 lite_realtime_quotes 能力",
                supported_features=sorted(adapter.supported_features),
            )
        )
    try:
        adapter.fetch_full_realtime_quotes(TEST_CODES)
    except UnsupportedFeatureError:
        details["direct_full_call"] = "UnsupportedFeatureError"
    except Exception as exc:
        issues.append(
            _issue(
                "FAIL",
                "adata_full_call_unexpected_error",
                "直接调用 adata full_realtime_quotes 未返回明确 UnsupportedFeatureError",
                error_type=type(exc).__name__,
                error_message=str(exc),
            )
        )
    else:
        issues.append(
            _issue(
                "FAIL",
                "adata_full_call_allowed",
                "直接调用 adata full_realtime_quotes 未被拒绝",
            )
        )

    if live_enabled:
        fetched = _fetch_source(
            "adata",
            "lite_realtime_quotes",
            lambda: adapter.fetch_lite_realtime_quotes(TEST_CODES),
        )
        details["live_lite_fetch"] = {key: value for key, value in fetched.items() if key != "data"}
        if fetched["status"] != "PASS":
            issues.append(
                _issue(
                    "WARN",
                    "adata_lite_fetch_failed",
                    "adata lite_realtime_quotes live 获取失败；边界仍按 policy/capability 判定",
                    error_type=fetched.get("error_type"),
                    error_message=fetched.get("error_message"),
                )
            )
        else:
            frame = _normalize_frame(fetched["data"])
            missing = _missing_fields(frame, LITE_REALTIME_REQUIRED_FIELDS)
            if missing:
                issues.append(
                    _issue(
                        "FAIL",
                        "adata_lite_missing_fields",
                        "adata lite_realtime_quotes 缺少 lite 必需字段",
                        missing_fields=missing,
                    )
                )
            forbidden_full_fields = [field for field in ["open", "high", "low", "pre_close"] if field in frame.columns]
            if forbidden_full_fields:
                issues.append(
                    _issue(
                        "WARN",
                        "adata_lite_contains_full_fields",
                        "adata lite 输出包含 full 字段；不得因此升级为 full 使用",
                        fields=forbidden_full_fields,
                    )
                )

    status = _status_from_issues(issues)
    return _result(
        "full_lite_realtime_usage_boundary",
        status,
        "adata 仅允许进入 lite_realtime_quotes，禁止进入 full_realtime_quotes",
        issues=issues,
        details=details,
    )


def _skip_report() -> dict[str, Any]:
    results = [
        _result("daily_kline_consistency", "SKIP", "未启用 live 一致性校验"),
        _result("trade_calendar_consistency", "SKIP", "未启用 live 一致性校验"),
        _result("full_realtime_quotes_consistency", "SKIP", "未启用 live 一致性校验"),
        _result("index_realtime_consistency", "SKIP", "未启用 live 一致性校验"),
        _result("full_lite_realtime_usage_boundary", "SKIP", "未启用 live 一致性校验"),
    ]
    return {
        "created_at": _utc_now(),
        "mode": "skip",
        "live_enabled": False,
        "enabled_by": [],
        "overall_status": "SKIP",
        "summary": "默认不联网；设置 ENABLE_SOURCE_CONSISTENCY_TEST=1 或 ENABLE_LIVE_SMOKE_TEST=1 后执行真实源一致性校验。",
        "test_universe": {
            "codes": TEST_CODES,
            "start_date": START_DATE,
            "end_date": END_DATE,
            "index_alias_map": INDEX_ALIAS_MAP,
        },
        "tolerance_policy": TOLERANCE_POLICY,
        "gate_decision": {
            "task013_1_completed": False,
            "task013_1_passed": False,
            "allow_s0_readonly_sandbox": False,
            "allow_s0_production": False,
            "reason": "live consistency check skipped by default",
        },
        "results": results,
    }


def _gate_decision(overall_status: str, results: list[dict[str, Any]]) -> dict[str, Any]:
    has_fail = any(item["status"] == "FAIL" for item in results)
    if has_fail:
        return {
            "task013_1_completed": True,
            "task013_1_passed": False,
            "allow_s0_readonly_sandbox": False,
            "allow_s0_production": False,
            "reason": "存在关键字段或源一致性 FAIL",
        }
    return {
        "task013_1_completed": True,
        "task013_1_passed": True,
        "allow_s0_readonly_sandbox": True,
        "allow_s0_production": False,
        "reason": "无 FAIL；如有 WARN，仅作为一致性报警与人工复核项",
        "overall_status": overall_status,
    }


def _overall_status(results: list[dict[str, Any]]) -> str:
    statuses = {item["status"] for item in results}
    if "FAIL" in statuses:
        return "FAIL"
    if "WARN" in statuses:
        return "WARN"
    if statuses == {"SKIP"}:
        return "SKIP"
    return "PASS"


def _live_report() -> dict[str, Any]:
    results = [
        _run_daily_consistency(),
        _run_trade_calendar_consistency(),
        _run_full_realtime_consistency(),
        _run_index_realtime_consistency(),
        _run_lite_boundary_check(live_enabled=True),
    ]
    overall_status = _overall_status(results)
    return {
        "created_at": _utc_now(),
        "mode": "live",
        "live_enabled": True,
        "enabled_by": _enabled_by(),
        "overall_status": overall_status,
        "summary": "多源字段一致性校验完成；阈值仅用于报警，不产生交易判断。",
        "test_universe": {
            "codes": TEST_CODES,
            "start_date": START_DATE,
            "end_date": END_DATE,
            "index_alias_map": INDEX_ALIAS_MAP,
        },
        "tolerance_policy": TOLERANCE_POLICY,
        "default_source_policy": DEFAULT_SOURCE_POLICY,
        "gate_decision": _gate_decision(overall_status, results),
        "results": results,
    }


def main() -> int:
    report = _live_report() if _live_enabled() else _skip_report()
    _write_report(report)
    for item in report["results"]:
        print(f"{item['check']}: {item['status']} - {item['summary']}")
    print(f"overall_status: {report['overall_status']}")
    print(f"report_path: {REPORT_PATH}")
    return 1 if report["overall_status"] == "FAIL" else 0


if __name__ == "__main__":
    raise SystemExit(main())
