from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

import pandas as pd

from astock_source_router.core.unit_policy import (
    AMOUNT_FIELD,
    PCT_CHG_FIELD,
    PRICE_FIELDS,
    VOLUME_FIELD,
    canonical_unit,
    conversion_factor,
    is_unknown_unit,
    normalize_adjust_type,
    target_unit,
    unit_assumption,
)

PCT_CHG_FORMULA = "(close - pre_close) / pre_close * 100"


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _to_number(value: object) -> float | None:
    try:
        numeric = pd.to_numeric(pd.Series([value]), errors="coerce").iloc[0]
    except Exception:
        return None
    if pd.isna(numeric):
        return None
    return float(numeric)


def _warnings_to_list(value: object) -> list[str]:
    if isinstance(value, list):
        return [str(item) for item in value]
    if isinstance(value, tuple | set):
        return [str(item) for item in value]
    try:
        if pd.isna(value):
            return []
    except Exception:
        pass
    text = str(value).strip()
    return [] if not text else [text]


def _ensure_warning_column(out: pd.DataFrame) -> pd.DataFrame:
    if "field_warnings" not in out.columns:
        out["field_warnings"] = [[] for _ in range(len(out))]
    else:
        out["field_warnings"] = out["field_warnings"].map(_warnings_to_list)
    return out


def _append_warning(out: pd.DataFrame, warning: str) -> None:
    if out.empty:
        return
    out["field_warnings"] = out["field_warnings"].map(
        lambda warnings: warnings if warning in warnings else [*warnings, warning]
    )


def _normalize_time_columns(out: pd.DataFrame, realtime: bool) -> None:
    if "date" in out.columns:
        parsed = pd.to_datetime(out["date"], errors="coerce")
        invalid = parsed.isna() & out["date"].notna()
        if invalid.any():
            _append_warning(out, "time_format_warning:date")
        out["date"] = parsed.dt.strftime("%Y-%m-%d")
    if "time" in out.columns:
        text = out["time"].astype(str).str.strip()
        extracted = text.str.extract(r"(\d{2}:\d{2}:\d{2})", expand=False)
        invalid = extracted.isna() & out["time"].notna()
        if invalid.any():
            _append_warning(out, "time_format_warning:time")
        out["time"] = extracted.fillna(text.str[:8])
    if "data_timestamp" in out.columns:
        parsed = pd.to_datetime(out["data_timestamp"], errors="coerce", utc=True)
        if parsed.isna().any():
            _append_warning(out, "time_format_warning:data_timestamp")
        out["data_timestamp"] = parsed.map(lambda value: value.isoformat() if pd.notna(value) else pd.NA)
    else:
        out["data_timestamp"] = _utc_now()
    if "request_time" in out.columns:
        parsed = pd.to_datetime(out["request_time"], errors="coerce", utc=True)
        if parsed.isna().any():
            _append_warning(out, "time_format_warning:request_time")
        out["request_time"] = parsed.map(lambda value: value.isoformat() if pd.notna(value) else pd.NA)
    else:
        out["request_time"] = _utc_now()
    if realtime and "data_timestamp" in out.columns:
        timestamps = pd.to_datetime(out["data_timestamp"], errors="coerce", utc=True)
        if timestamps.notna().any():
            max_lag = (datetime.now(timezone.utc) - timestamps.max().to_pydatetime()).total_seconds()
            if max_lag > 15 * 60:
                _append_warning(out, "timestamp_lag_warning:data_timestamp")


def _base_result(
    value: object,
    source: str,
    function_name: str,
    field_name: str,
) -> dict[str, Any]:
    assumption = unit_assumption(source, function_name, field_name)
    raw_unit = assumption["canonical_unit"]
    factor = conversion_factor(field_name, raw_unit)
    numeric = _to_number(value)
    warnings: list[str] = []
    if factor is None or is_unknown_unit(assumption["unit"]):
        normalized = numeric if numeric is not None else value
        normalized_unit = "unknown"
        factor_out: float | None = None
        warnings.append(f"unit_unknown:{field_name}:{source}:{function_name}")
    else:
        normalized = numeric * factor if numeric is not None else value
        normalized_unit = target_unit(field_name)
        factor_out = factor
    return {
        "raw_value": value,
        "raw_unit": raw_unit,
        "normalized_value": normalized,
        "normalized_unit": normalized_unit,
        "conversion_factor": factor_out,
        "unit_source": assumption["unit_source"],
        "unit_confidence": assumption["confidence"],
        "warnings": warnings,
    }


def normalize_price(value: object, source: str, field_name: str) -> dict[str, Any]:
    if field_name not in PRICE_FIELDS:
        raise ValueError(f"not a price field: {field_name}")
    return _base_result(value, source, "realtime_quotes", field_name)


def normalize_volume(value: object, source: str, function_name: str) -> dict[str, Any]:
    return _base_result(value, source, function_name, VOLUME_FIELD)


def normalize_amount(value: object, source: str, function_name: str) -> dict[str, Any]:
    return _base_result(value, source, function_name, AMOUNT_FIELD)


def normalize_pct_chg(
    value: object,
    source: str,
    close: object | None = None,
    pre_close: object | None = None,
    function_name: str = "realtime_quotes",
) -> dict[str, Any]:
    assumption = unit_assumption(source, function_name, PCT_CHG_FIELD)
    unit = canonical_unit(assumption["unit"], PCT_CHG_FIELD)
    warnings: list[str] = []
    close_num = _to_number(close)
    pre_close_num = _to_number(pre_close)
    can_derive = close_num is not None and pre_close_num not in {None, 0.0}
    if unit == "percent_derived" or (value is None and can_derive):
        if can_derive:
            normalized = (close_num - pre_close_num) / pre_close_num * 100
            derived = True
            source_name = "derived"
        else:
            normalized = _to_number(value)
            derived = True
            source_name = "derived_missing_price"
            warnings.append(f"pct_chg_derive_warning:{source}:{function_name}")
    else:
        factor = conversion_factor(PCT_CHG_FIELD, unit)
        numeric = _to_number(value)
        if factor is None or is_unknown_unit(assumption["unit"]):
            normalized = numeric if numeric is not None else value
            warnings.append(f"unit_unknown:pct_chg:{source}:{function_name}")
        else:
            normalized = numeric * factor if numeric is not None else value
        derived = False
        source_name = source
    return {
        "raw_value": value,
        "pct_chg": normalized,
        "pct_chg_unit": "percent" if not warnings else "unknown",
        "pct_chg_source": source_name,
        "pct_chg_derived": derived,
        "pct_chg_formula": PCT_CHG_FORMULA if derived else "",
        "pct_chg_warning": ";".join(warnings),
        "unit_confidence": assumption["confidence"],
        "conversion_factor": conversion_factor(PCT_CHG_FIELD, unit),
        "warnings": warnings,
    }


def _normalize_price_columns(out: pd.DataFrame, source: str, function_name: str, fields: set[str]) -> None:
    for field in fields.intersection(out.columns):
        assumption = unit_assumption(source, function_name, field)
        raw_unit = assumption["canonical_unit"]
        factor = conversion_factor(field, raw_unit)
        out[f"raw_{field}"] = out[field]
        out[f"raw_{field}_unit"] = raw_unit
        out[f"{field}_unit"] = target_unit(field) if factor is not None else "unknown"
        out[f"{field}_normalized_unit"] = target_unit(field) if factor is not None else "unknown"
        out[f"{field}_unit_source"] = assumption["unit_source"]
        out[f"{field}_unit_confidence"] = assumption["confidence"]
        out[f"{field}_conversion_factor"] = factor
        numeric = pd.to_numeric(out[field], errors="coerce")
        if factor is None:
            out[f"{field}_normalized"] = numeric
            _append_warning(out, f"unit_unknown:{field}:{source}:{function_name}")
        else:
            out[f"{field}_normalized"] = numeric * factor
            out[field] = out[f"{field}_normalized"]


def _normalize_amount_or_volume(out: pd.DataFrame, source: str, function_name: str, field: str) -> None:
    if field not in out.columns:
        return
    assumption = unit_assumption(source, function_name, field)
    raw_unit = assumption["canonical_unit"]
    factor = conversion_factor(field, raw_unit)
    out[f"raw_{field}"] = out[field]
    out[f"raw_{field}_unit"] = raw_unit
    out[f"{field}_unit_source"] = assumption["unit_source"]
    out[f"{field}_unit_confidence"] = assumption["confidence"]
    out[f"{field}_conversion_factor"] = factor
    numeric = pd.to_numeric(out[field], errors="coerce")
    if factor is None or is_unknown_unit(assumption["unit"]):
        out[f"{field}_unit"] = "unknown"
        out[f"{field}_normalized"] = numeric
        out[f"{field}_normalized_unit"] = "unknown"
        _append_warning(out, f"unit_unknown:{field}:{source}:{function_name}")
    else:
        out[f"{field}_unit"] = target_unit(field)
        out[f"{field}_normalized"] = numeric * factor
        out[f"{field}_normalized_unit"] = target_unit(field)
        out[field] = out[f"{field}_normalized"]


def _normalize_pct_column(out: pd.DataFrame, source: str, function_name: str, price_field: str) -> None:
    if PCT_CHG_FIELD not in out.columns:
        return
    raw_values = out[PCT_CHG_FIELD].copy()
    normalized_rows = []
    for index, value in raw_values.items():
        normalized_rows.append(
            normalize_pct_chg(
                value,
                source,
                close=out.at[index, price_field] if price_field in out.columns else None,
                pre_close=out.at[index, "pre_close"] if "pre_close" in out.columns else None,
                function_name=function_name,
            )
        )
    out["raw_pct_chg"] = raw_values
    out[PCT_CHG_FIELD] = [item["pct_chg"] for item in normalized_rows]
    out["pct_chg_unit"] = [item["pct_chg_unit"] for item in normalized_rows]
    out["pct_chg_source"] = [item["pct_chg_source"] for item in normalized_rows]
    out["pct_chg_derived"] = [item["pct_chg_derived"] for item in normalized_rows]
    out["pct_chg_formula"] = [item["pct_chg_formula"] for item in normalized_rows]
    out["pct_chg_warning"] = [item["pct_chg_warning"] for item in normalized_rows]
    for warning in sorted({warning for item in normalized_rows for warning in item["warnings"]}):
        _append_warning(out, warning)


def _normalize_common(out: pd.DataFrame, source: str, function_name: str, realtime: bool) -> pd.DataFrame:
    out = out.copy()
    _ensure_warning_column(out)
    if "source" not in out.columns:
        out["source"] = source
    if "source_status" not in out.columns:
        out["source_status"] = "ok"
    if "source_latency_ms" not in out.columns:
        out["source_latency_ms"] = pd.NA
    _normalize_time_columns(out, realtime=realtime)
    return out


def normalize_daily_kline_units(df: pd.DataFrame, source: str) -> pd.DataFrame:
    out = _normalize_common(df, source, "daily_kline", realtime=False)
    _normalize_price_columns(out, source, "daily_kline", {"open", "high", "low", "close", "pre_close"})
    _normalize_amount_or_volume(out, source, "daily_kline", VOLUME_FIELD)
    _normalize_amount_or_volume(out, source, "daily_kline", AMOUNT_FIELD)
    _normalize_pct_column(out, source, "daily_kline", "close")
    if "adjust_type" not in out.columns:
        out["adjust_type"] = "unknown"
        _append_warning(out, "adjust_type_unknown:missing")
    else:
        out["adjust_type"] = out["adjust_type"].map(normalize_adjust_type)
        if out["adjust_type"].eq("unknown").any():
            _append_warning(out, "adjust_type_unknown:value")
    return out


def normalize_realtime_units(df: pd.DataFrame, source: str) -> pd.DataFrame:
    out = _normalize_common(df, source, "realtime_quotes", realtime=True)
    _normalize_price_columns(out, source, "realtime_quotes", {"last_price", "pre_close", "open", "high", "low"})
    _normalize_amount_or_volume(out, source, "realtime_quotes", VOLUME_FIELD)
    _normalize_amount_or_volume(out, source, "realtime_quotes", AMOUNT_FIELD)
    _normalize_pct_column(out, source, "realtime_quotes", "last_price")
    return out


def normalize_index_units(df: pd.DataFrame, source: str) -> pd.DataFrame:
    out = _normalize_common(df, source, "index_realtime", realtime=True)
    _normalize_price_columns(out, source, "index_realtime", {"last_price", "pre_close", "open", "high", "low"})
    _normalize_amount_or_volume(out, source, "index_realtime", VOLUME_FIELD)
    _normalize_amount_or_volume(out, source, "index_realtime", AMOUNT_FIELD)
    _normalize_pct_column(out, source, "index_realtime", "last_price")
    return out
