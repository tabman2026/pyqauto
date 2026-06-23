from __future__ import annotations

import re
from collections.abc import Iterable
from datetime import datetime, timezone

import pandas as pd

from astock_source_router.core.errors import DataQualityError
from astock_source_router.core.features import (
    DAILY_KLINE,
    FULL_REALTIME_QUOTES,
    INDEX_REALTIME,
    LITE_REALTIME_QUOTES,
    MINUTE_KLINE,
    REALTIME_QUOTES,
    STOCK_BASIC,
    TRADE_CALENDAR,
)
from astock_source_router.core.models import QualityReport

FULL_REALTIME_REQUIRED_COLUMNS = [
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

LITE_REALTIME_REQUIRED_COLUMNS = [
    "code",
    "name",
    "last_price",
    "volume",
    "amount",
    "pct_chg",
    "source",
    "source_latency_ms",
    "source_status",
    "data_timestamp",
]

REQUIRED_COLUMNS: dict[str, list[str]] = {
    REALTIME_QUOTES: FULL_REALTIME_REQUIRED_COLUMNS,
    FULL_REALTIME_QUOTES: FULL_REALTIME_REQUIRED_COLUMNS,
    LITE_REALTIME_QUOTES: LITE_REALTIME_REQUIRED_COLUMNS,
    INDEX_REALTIME: [
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
    ],
    DAILY_KLINE: [
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
    ],
    TRADE_CALENDAR: ["date", "is_trading_day", "source", "source_latency_ms", "source_status"],
    MINUTE_KLINE: [
        "datetime",
        "code",
        "open",
        "high",
        "low",
        "close",
        "volume",
        "amount",
        "source",
        "source_latency_ms",
        "source_status",
    ],
    STOCK_BASIC: ["code", "name", "exchange", "source", "source_latency_ms", "source_status"],
}

NUMERIC_COLUMNS = {
    "last_price",
    "pre_close",
    "open",
    "high",
    "low",
    "close",
    "volume",
    "amount",
    "pct_chg",
    "turnover_rate",
    "source_latency_ms",
}

NUMERIC_REQUIRED_COLUMNS: dict[str, set[str]] = {
    REALTIME_QUOTES: {
        "last_price",
        "pre_close",
        "open",
        "high",
        "low",
        "volume",
        "amount",
        "pct_chg",
        "source_latency_ms",
    },
    FULL_REALTIME_QUOTES: {
        "last_price",
        "pre_close",
        "open",
        "high",
        "low",
        "volume",
        "amount",
        "pct_chg",
        "source_latency_ms",
    },
    LITE_REALTIME_QUOTES: {
        "last_price",
        "volume",
        "amount",
        "pct_chg",
        "source_latency_ms",
    },
    INDEX_REALTIME: {
        "last_price",
        "pre_close",
        "open",
        "high",
        "low",
        "volume",
        "amount",
        "pct_chg",
        "source_latency_ms",
    },
    DAILY_KLINE: {
        "open",
        "high",
        "low",
        "close",
        "pre_close",
        "volume",
        "amount",
        "turnover_rate",
        "pct_chg",
        "source_latency_ms",
    },
}

PRICE_COLUMNS: dict[str, set[str]] = {
    REALTIME_QUOTES: {"last_price", "pre_close", "open", "high", "low"},
    FULL_REALTIME_QUOTES: {"last_price", "pre_close", "open", "high", "low"},
    LITE_REALTIME_QUOTES: {"last_price"},
    INDEX_REALTIME: {"last_price", "pre_close", "open", "high", "low"},
    DAILY_KLINE: {"open", "high", "low", "close", "pre_close"},
}

AMOUNT_REQUIRED_FEATURES = {
    REALTIME_QUOTES,
    FULL_REALTIME_QUOTES,
    LITE_REALTIME_QUOTES,
    INDEX_REALTIME,
    DAILY_KLINE,
}

BLOCKED_RESPONSE_PATTERNS = (
    "<html",
    "<!doctype html",
    "captcha",
    "验证码",
    "风控",
    "访问过于频繁",
    "access denied",
    "forbidden",
    "security check",
    "verify",
)


def normalize_code(code: str | int) -> str:
    """Normalize stock code to 6 digits.

    Supports inputs like 000001, sz000001, SZ.000001, sh.600519.
    """

    raw = str(code).strip().upper()
    match = re.search(r"(\d{6})", raw)
    if not match:
        raise ValueError(f"Invalid A-share code: {code!r}")
    return match.group(1)


def normalize_codes(codes: Iterable[str | int] | str | int | None) -> list[str]:
    if codes is None:
        return []
    if isinstance(codes, (str, int)):
        return [normalize_code(codes)]
    return [normalize_code(code) for code in codes]


def date_to_yyyymmdd(value: str | int | datetime) -> str:
    if isinstance(value, datetime):
        return value.strftime("%Y%m%d")
    text = str(value).strip()
    digits = re.sub(r"\D", "", text)
    if len(digits) != 8:
        raise ValueError(f"Invalid date: {value!r}")
    return digits


def date_to_iso(value: str | int | datetime) -> str:
    digits = date_to_yyyymmdd(value)
    return f"{digits[:4]}-{digits[4:6]}-{digits[6:]}"


def ensure_dataframe(data: object) -> pd.DataFrame:
    if isinstance(data, pd.DataFrame):
        return data.copy()
    if isinstance(data, list):
        return pd.DataFrame(data)
    if isinstance(data, dict):
        return pd.DataFrame([data])
    if isinstance(data, str):
        lowered = data.strip().lower()
        if any(pattern in lowered for pattern in BLOCKED_RESPONSE_PATTERNS):
            raise DataQualityError("blocked_html_or_risk_control_response")
    raise TypeError(f"Expected DataFrame/list/dict, got {type(data)!r}")


def add_source_columns(df: pd.DataFrame, source: str, latency_ms: float) -> pd.DataFrame:
    out = df.copy()
    out["source"] = source
    out["source_latency_ms"] = round(float(latency_ms), 3)
    if "source_status" not in out.columns:
        out["source_status"] = "ok"
    if "data_timestamp" not in out.columns:
        out["data_timestamp"] = datetime.now(timezone.utc).isoformat()
    return out


def coerce_standard_types(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    if "code" in out.columns:
        out["code"] = out["code"].map(lambda x: normalize_code(x) if pd.notna(x) else x)
    if "date" in out.columns:
        out["date"] = out["date"].astype(str).str[:10]
    if "datetime" in out.columns:
        out["datetime"] = out["datetime"].astype(str)
    if "data_timestamp" in out.columns:
        out["data_timestamp"] = out["data_timestamp"].astype(str)
    for col in NUMERIC_COLUMNS.intersection(out.columns):
        out[col] = pd.to_numeric(out[col], errors="coerce")
    if "is_trading_day" in out.columns:
        out["is_trading_day"] = out["is_trading_day"].astype(bool)
    return out


def _contains_blocked_response(df: pd.DataFrame) -> bool:
    if df.empty:
        return False
    object_cols = df.select_dtypes(include=["object", "string"]).columns
    for col in object_cols:
        values = df[col].dropna().astype(str).str.lower()
        if values.empty:
            continue
        if values.map(lambda value: any(pattern in value for pattern in BLOCKED_RESPONSE_PATTERNS)).any():
            return True
    return False


def _parse_iso_date(value: object) -> str | None:
    try:
        return date_to_iso(value)  # type: ignore[arg-type]
    except Exception:
        try:
            parsed = pd.to_datetime(value, errors="coerce")
        except Exception:
            return None
        if pd.isna(parsed):
            return None
        return parsed.strftime("%Y-%m-%d")


def _validate_target_dates(df: pd.DataFrame, context: dict[str, object], warnings: list[str]) -> None:
    if "date" not in df.columns or df.empty:
        return
    parsed_dates = pd.to_datetime(df["date"], errors="coerce")
    if parsed_dates.isna().any():
        warnings.append("target_date_anomaly:invalid_date")
        return

    start_date = context.get("start_date")
    end_date = context.get("end_date")
    if start_date is None and end_date is None:
        return
    start_iso = _parse_iso_date(start_date) if start_date is not None else None
    end_iso = _parse_iso_date(end_date) if end_date is not None else None
    normalized = parsed_dates.dt.strftime("%Y-%m-%d")
    if start_iso is not None and (normalized < start_iso).any():
        warnings.append("target_date_anomaly:before_start_date")
    if end_iso is not None and (normalized > end_iso).any():
        warnings.append("target_date_anomaly:after_end_date")


def _validate_realtime_freshness(
    feature: str,
    df: pd.DataFrame,
    context: dict[str, object],
    warnings: list[str],
) -> None:
    if feature not in (
        REALTIME_QUOTES,
        FULL_REALTIME_QUOTES,
        LITE_REALTIME_QUOTES,
        INDEX_REALTIME,
        MINUTE_KLINE,
    ):
        return
    if "data_timestamp" not in df.columns or df.empty:
        return
    stale_after_seconds = float(context.get("realtime_stale_after_seconds", 15 * 60))
    timestamps = pd.to_datetime(df["data_timestamp"], errors="coerce", utc=True)
    if timestamps.isna().any():
        warnings.append("realtime_stale:invalid_data_timestamp")
        return
    latest = timestamps.max().to_pydatetime()
    age_seconds = (datetime.now(timezone.utc) - latest).total_seconds()
    if age_seconds > stale_after_seconds:
        warnings.append("realtime_stale:data_timestamp_expired")


def validate_dataframe(
    feature: str,
    df: pd.DataFrame,
    *,
    context: dict[str, object] | None = None,
) -> QualityReport:
    context = context or {}
    row_count = int(len(df))
    warnings: list[str] = []
    missing = [col for col in REQUIRED_COLUMNS.get(feature, []) if col not in df.columns]
    if row_count == 0:
        warnings.append("empty_dataframe")
    if missing:
        warnings.append("missing_required_columns")
    if _contains_blocked_response(df):
        warnings.append("blocked_html_or_risk_control_response")

    for col in NUMERIC_REQUIRED_COLUMNS.get(feature, set()).intersection(df.columns):
        numeric = pd.to_numeric(df[col], errors="coerce")
        if numeric.isna().any():
            warnings.append(f"field_type_error:{col}")

    for col in PRICE_COLUMNS.get(feature, set()).intersection(df.columns):
        numeric = pd.to_numeric(df[col], errors="coerce")
        if (numeric == 0).any():
            warnings.append(f"zero_price:{col}")

    if feature in AMOUNT_REQUIRED_FEATURES and "amount" in df.columns:
        amount = pd.to_numeric(df["amount"], errors="coerce")
        if (amount == 0).any():
            warnings.append("zero_amount")

    min_expected_rows = int(context.get("min_expected_rows", 0) or 0)
    if min_expected_rows > 0 and 0 < row_count < min_expected_rows:
        warnings.append(f"insufficient_rows:{row_count}/{min_expected_rows}")

    _validate_target_dates(df, context, warnings)
    _validate_realtime_freshness(feature, df, context, warnings)

    warnings = list(dict.fromkeys(warnings))
    return QualityReport(
        is_valid=(row_count > 0 and not warnings),
        row_count=row_count,
        missing_fields=missing,
        warnings=warnings,
    )


def safe_pct_chg(last_price: pd.Series, pre_close: pd.Series) -> pd.Series:
    pre = pd.to_numeric(pre_close, errors="coerce").replace(0, pd.NA)
    last = pd.to_numeric(last_price, errors="coerce")
    return (last / pre - 1) * 100


def derive_pre_close_from_pct(close: pd.Series, pct_chg: pd.Series) -> pd.Series:
    pct = pd.to_numeric(pct_chg, errors="coerce") / 100
    close_num = pd.to_numeric(close, errors="coerce")
    return close_num / (1 + pct.replace(-1, pd.NA))
