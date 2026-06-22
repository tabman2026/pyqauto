"""Test-only candidate normalizers for v0.4.0 adapter contracts.

These helpers are not public adapter APIs. They only exercise mock raw schema
contracts before a real adapter is implemented.
"""

from __future__ import annotations

import re
from typing import Any

CONTRACT_VERSION = "candidate.normalize.v0.4.0.mock"
SOURCE_LEVEL = "candidate_mock"

MODEL_FIELD_SEMANTICS = {
    "QuoteRecord.volume": "volume_shares",
    "QuoteRecord.amount": "amount_yuan",
    "KlineBar.volume": "volume_shares",
    "KlineBar.amount": "amount_yuan",
}

QUOTE_STANDARD_FIELDS = [
    "symbol",
    "name",
    "price",
    "open",
    "high",
    "low",
    "pre_close",
    "volume",
    "amount",
    "volume_shares",
    "amount_yuan",
    "datetime",
    "source",
    "source_level",
    "trace_id",
    "raw",
]

KLINE_STANDARD_FIELDS = [
    "symbol",
    "datetime",
    "open",
    "high",
    "low",
    "close",
    "volume",
    "amount",
    "volume_shares",
    "amount_yuan",
    "period",
    "source",
    "source_level",
    "trace_id",
    "raw",
]

QUOTE_CORE_FIELDS = ["symbol", "price"]
KLINE_CORE_FIELDS = ["symbol", "datetime", "open", "high", "low", "close", "period"]

EFINANCE_REALTIME_MAPPING = {
    "symbol": ["股票代码"],
    "name": ["股票名称"],
    "price": ["最新价"],
    "open": ["今开"],
    "high": ["最高"],
    "low": ["最低"],
    "pre_close": ["昨日收盘"],
    "volume_shares": ["成交量"],
    "amount_yuan": ["成交额"],
    "datetime": ["更新时间"],
}

EFINANCE_KLINE_MAPPING = {
    "symbol": ["股票代码"],
    "datetime": ["日期"],
    "open": ["开盘"],
    "high": ["最高"],
    "low": ["最低"],
    "close": ["收盘"],
    "volume_shares": ["成交量"],
    "amount_yuan": ["成交额"],
}

BAOSTOCK_KLINE_MAPPING = {
    "symbol": ["code"],
    "datetime": ["date"],
    "open": ["open"],
    "high": ["high"],
    "low": ["low"],
    "close": ["close"],
    "volume_shares": ["volume"],
    "amount_yuan": ["amount"],
}

MOOTDX_QUOTE_MAPPING = {
    "symbol": ["code"],
    "price": ["price"],
    "open": ["open"],
    "high": ["high"],
    "low": ["low"],
    "pre_close": ["last_close", "pre_close"],
    "volume_shares": ["vol"],
    "amount_yuan": ["amount"],
}

MOOTDX_KLINE_MAPPING = {
    "datetime": ["datetime"],
    "open": ["open"],
    "high": ["high"],
    "low": ["low"],
    "close": ["close"],
    "volume_shares": ["vol"],
    "amount_yuan": ["amount"],
}

FIELD_MAPPINGS = {
    ("efinance", "realtime"): EFINANCE_REALTIME_MAPPING,
    ("efinance", "kline"): EFINANCE_KLINE_MAPPING,
    ("baostock", "kline"): BAOSTOCK_KLINE_MAPPING,
    ("mootdx", "quote"): MOOTDX_QUOTE_MAPPING,
    ("mootdx", "kline"): MOOTDX_KLINE_MAPPING,
}

UNIT_RAW_FIELDS = {
    ("efinance", "realtime"): ("成交量", "成交额"),
    ("efinance", "kline"): ("成交量", "成交额"),
    ("baostock", "kline"): ("volume", "amount"),
    ("mootdx", "quote"): ("vol", "amount"),
    ("mootdx", "kline"): ("vol", "amount"),
}

EFINANCE_KLT_PERIODS = {
    1: "1m",
    5: "5m",
    15: "15m",
    30: "30m",
    60: "60m",
    101: "1d",
    102: "1w",
    103: "1mo",
}

BAOSTOCK_PERIODS = {
    "d": "1d",
    "5": "5m",
    "15": "15m",
    "30": "30m",
    "60": "60m",
    "w": "1w",
    "m": "1mo",
}

MOOTDX_PERIODS = {
    0: "5m",
    1: "15m",
    2: "30m",
    3: "60m",
    4: "1d",
    7: "1m",
    8: "1m",
    9: "1d",
}


def normalize_candidate_payload(
    payload: dict[str, Any],
    *,
    candidate: str,
    endpoint: str,
    kind: str,
) -> dict[str, Any]:
    """Normalize one mock candidate fixture into a contract report."""

    source = f"{candidate}_candidate"
    mapping = FIELD_MAPPINGS[(candidate, endpoint)]
    rows = _raw_rows(payload, candidate)
    public_records: list[dict[str, Any]] = []
    rejected_records: list[dict[str, Any]] = []
    candidate_records: list[dict[str, Any]] = []
    schema_drift_fields: list[str] = []
    missing_raw_fields: list[dict[str, Any]] = []
    row_reports: list[dict[str, Any]] = []
    unit_statuses: list[str] = []

    for index, row in enumerate(rows):
        record = _build_record(
            row,
            payload,
            candidate=candidate,
            endpoint=endpoint,
            kind=kind,
            source=source,
            index=index,
        )
        candidate_records.append(record)
        unit_status = record["unit_status"]
        unit_statuses.append(unit_status)

        row_schema_drift = _row_schema_drift(row, mapping)
        for item in row_schema_drift:
            if item["standard_field"] not in schema_drift_fields:
                schema_drift_fields.append(item["standard_field"])
            if item not in missing_raw_fields:
                missing_raw_fields.append(item)

        missing_core = _missing_core_fields(record, kind)
        reasons = []
        if missing_core:
            reasons.append("missing_core_fields: " + ", ".join(missing_core))
        if row_schema_drift:
            reasons.append(
                "schema_drift_fields: "
                + ", ".join(item["standard_field"] for item in row_schema_drift)
            )
        if unit_status == "unknown":
            reasons.append("unknown unit for volume_shares or amount_yuan")
        elif unit_status == "rejected":
            reasons.append("unit conversion rejected")

        row_report = {
            "row_index": index,
            "missing_core_fields": missing_core,
            "schema_drift_fields": [item["standard_field"] for item in row_schema_drift],
            "unit_status": unit_status,
        }
        if reasons:
            rejected_reason = "; ".join(reasons)
            row_report["rejected_reason"] = rejected_reason
            rejected_records.append(
                {
                    "row_index": index,
                    "source": source,
                    "unit_status": unit_status,
                    "schema_drift_fields": row_report["schema_drift_fields"],
                    "missing_core_fields": missing_core,
                    "rejected_reason": rejected_reason,
                    "record": record,
                }
            )
        else:
            public_records.append(record)
        row_reports.append(row_report)

    status = _report_status(public_records, rejected_records, rows)
    return {
        "contract_version": CONTRACT_VERSION,
        "candidate_normalizer": "test_only",
        "candidate_source": source,
        "source": source,
        "source_api": payload.get("source_api"),
        "kind": kind,
        "status": status,
        "unit_status": _report_unit_status(unit_statuses),
        "standard_fields": QUOTE_STANDARD_FIELDS if kind == "quote" else KLINE_STANDARD_FIELDS,
        "current_model_field_semantics": dict(MODEL_FIELD_SEMANTICS),
        "field_mapping": mapping,
        "field_mapping_doc": "docs/ADAPTER_FIELD_MAPPING_DRAFT_V040.md",
        "unit_rules_doc": "docs/ADAPTER_UNIT_RULES_DRAFT_V040.md",
        "raw_columns": _raw_columns(payload, rows),
        "schema_drift_fields": schema_drift_fields,
        "missing_raw_fields": missing_raw_fields,
        "row_reports": row_reports,
        "candidate_records": candidate_records,
        "public_records": public_records,
        "rejected_records": rejected_records,
        "rejected_count": len(rejected_records),
        "public_count": len(public_records),
    }


def _raw_rows(payload: dict[str, Any], candidate: str) -> list[dict[str, Any]]:
    if candidate == "baostock":
        result = payload.get("result")
        if not isinstance(result, dict):
            return []
        fields = [str(field) for field in result.get("fields", [])]
        rows = []
        for values in result.get("rows", []):
            if isinstance(values, list):
                rows.append(dict(zip(fields, values, strict=False)))
        return rows
    rows = payload.get("rows", [])
    return [dict(row) for row in rows if isinstance(row, dict)]


def _build_record(
    row: dict[str, Any],
    payload: dict[str, Any],
    *,
    candidate: str,
    endpoint: str,
    kind: str,
    source: str,
    index: int,
) -> dict[str, Any]:
    if kind == "quote":
        record = _build_quote(row, payload, candidate=candidate, endpoint=endpoint)
    else:
        record = _build_kline(row, payload, candidate=candidate, endpoint=endpoint)
    unit_status = _unit_status(payload, candidate=candidate, endpoint=endpoint)
    _apply_unit_fields(record, row, candidate=candidate, endpoint=endpoint, unit_status=unit_status)
    record.update(
        {
            "source": source,
            "source_level": SOURCE_LEVEL,
            "trace_id": f"candidate-{candidate}-{endpoint}-{index}",
            "raw": _raw_metadata(row, payload, candidate=candidate),
            "unit_status": unit_status,
            "metadata": _metadata(payload, candidate=candidate, endpoint=endpoint),
        }
    )
    return record


def _build_quote(
    row: dict[str, Any],
    payload: dict[str, Any],
    *,
    candidate: str,
    endpoint: str,
) -> dict[str, Any]:
    mapping = FIELD_MAPPINGS[(candidate, endpoint)]
    return {
        "symbol": _normalize_symbol(_first_present(row, mapping["symbol"])),
        "name": _first_present(row, mapping.get("name", [])),
        "price": _as_float(_first_present(row, mapping["price"])),
        "open": _as_float(_first_present(row, mapping.get("open", []))),
        "high": _as_float(_first_present(row, mapping.get("high", []))),
        "low": _as_float(_first_present(row, mapping.get("low", []))),
        "pre_close": _as_float(_first_present(row, mapping.get("pre_close", []))),
        "volume": None,
        "amount": None,
        "volume_shares": None,
        "amount_yuan": None,
        "datetime": _quote_datetime(row, payload, candidate=candidate),
    }


def _build_kline(
    row: dict[str, Any],
    payload: dict[str, Any],
    *,
    candidate: str,
    endpoint: str,
) -> dict[str, Any]:
    mapping = FIELD_MAPPINGS[(candidate, endpoint)]
    symbol = _first_present(row, mapping.get("symbol", []))
    if symbol is None:
        symbol = payload.get("request", {}).get("symbol")
    return {
        "symbol": _normalize_symbol(symbol),
        "datetime": _kline_datetime(row, payload, candidate=candidate),
        "open": _as_float(_first_present(row, mapping["open"])),
        "high": _as_float(_first_present(row, mapping["high"])),
        "low": _as_float(_first_present(row, mapping["low"])),
        "close": _as_float(_first_present(row, mapping["close"])),
        "volume": None,
        "amount": None,
        "volume_shares": None,
        "amount_yuan": None,
        "period": _period(payload, candidate=candidate),
    }


def _apply_unit_fields(
    record: dict[str, Any],
    row: dict[str, Any],
    *,
    candidate: str,
    endpoint: str,
    unit_status: str,
) -> None:
    volume_field, amount_field = UNIT_RAW_FIELDS[(candidate, endpoint)]
    if unit_status == "unknown":
        return
    volume = _as_float(row.get(volume_field))
    amount = _as_float(row.get(amount_field))
    record["volume"] = volume
    record["amount"] = amount
    record["volume_shares"] = volume
    record["amount_yuan"] = amount


def _unit_status(
    payload: dict[str, Any],
    *,
    candidate: str,
    endpoint: str,
) -> str:
    notes = payload.get("unit_notes", {})
    if not isinstance(notes, dict):
        return "unknown"
    volume_field, amount_field = UNIT_RAW_FIELDS[(candidate, endpoint)]
    values = [
        str(notes.get(volume_field, "")).lower(),
        str(notes.get(amount_field, "")).lower(),
    ]
    if any("reject" in value for value in values):
        return "rejected"
    if any("unknown" in value or not value for value in values):
        return "unknown"
    if any("convert" in value for value in values):
        return "converted"
    return "known"


def _row_schema_drift(
    row: dict[str, Any],
    mapping: dict[str, list[str]],
) -> list[dict[str, Any]]:
    drift = []
    for standard_field, raw_fields in mapping.items():
        if standard_field in {"name", "open", "high", "low", "pre_close", "datetime"}:
            continue
        has_raw_field = any(
            raw_field in row and row[raw_field] not in (None, "") for raw_field in raw_fields
        )
        if not has_raw_field:
            drift.append({"standard_field": standard_field, "raw_fields": list(raw_fields)})
    return drift


def _missing_core_fields(record: dict[str, Any], kind: str) -> list[str]:
    core_fields = QUOTE_CORE_FIELDS if kind == "quote" else KLINE_CORE_FIELDS
    missing = []
    for field in core_fields:
        value = record.get(field)
        if value in (None, ""):
            missing.append(field)
    return missing


def _report_status(
    public_records: list[dict[str, Any]],
    rejected_records: list[dict[str, Any]],
    rows: list[dict[str, Any]],
) -> str:
    if not rows:
        return "rejected"
    if public_records and rejected_records:
        return "partial"
    if public_records:
        return "accepted"
    return "rejected"


def _report_unit_status(unit_statuses: list[str]) -> str:
    if not unit_statuses:
        return "rejected"
    for status in ["rejected", "unknown", "converted"]:
        if status in unit_statuses:
            return status
    return "known"


def _raw_metadata(
    row: dict[str, Any],
    payload: dict[str, Any],
    *,
    candidate: str,
) -> dict[str, Any]:
    request = dict(payload.get("request", {}))
    metadata = {
        "row": dict(row),
        "request": request,
        "unit_notes": dict(payload.get("unit_notes", {})),
    }
    if candidate == "baostock":
        metadata["frequency"] = request.get("frequency")
        metadata["adjustflag"] = request.get("adjustflag") or row.get("adjustflag")
    return metadata


def _metadata(payload: dict[str, Any], *, candidate: str, endpoint: str) -> dict[str, Any]:
    request = payload.get("request", {})
    if not isinstance(request, dict):
        request = {}
    if candidate == "efinance" and endpoint == "kline":
        return {"klt": request.get("klt"), "fqt": request.get("fqt")}
    if candidate == "baostock":
        return {"frequency": request.get("frequency"), "adjustflag": request.get("adjustflag")}
    if candidate == "mootdx" and endpoint == "kline":
        return {"frequency": request.get("frequency"), "adjust": request.get("adjust")}
    return {}


def _quote_datetime(row: dict[str, Any], payload: dict[str, Any], *, candidate: str) -> Any:
    if candidate == "efinance":
        return row.get("更新时间")
    return payload.get("request", {}).get("datetime") or row.get("datetime")


def _kline_datetime(row: dict[str, Any], payload: dict[str, Any], *, candidate: str) -> Any:
    if candidate == "baostock":
        time_value = row.get("time")
        if time_value:
            return _baostock_time(str(time_value))
        return row.get("date")
    mapping = FIELD_MAPPINGS[(candidate, "kline")]
    return _first_present(row, mapping["datetime"])


def _baostock_time(value: str) -> str:
    if re.fullmatch(r"\d{17}", value):
        return (
            f"{value[0:4]}-{value[4:6]}-{value[6:8]} "
            f"{value[8:10]}:{value[10:12]}:{value[12:14]}"
        )
    return value


def _period(payload: dict[str, Any], *, candidate: str) -> str | None:
    request = payload.get("request", {})
    if not isinstance(request, dict):
        return None
    if candidate == "efinance":
        return EFINANCE_KLT_PERIODS.get(request.get("klt"))
    if candidate == "baostock":
        return BAOSTOCK_PERIODS.get(str(request.get("frequency")))
    if candidate == "mootdx":
        return MOOTDX_PERIODS.get(request.get("frequency"))
    return None


def _raw_columns(payload: dict[str, Any], rows: list[dict[str, Any]]) -> list[str]:
    columns = payload.get("columns")
    if isinstance(columns, list):
        return [str(column) for column in columns]
    if rows:
        return list(rows[0])
    return []


def _normalize_symbol(value: Any) -> str | None:
    if value in (None, ""):
        return None
    match = re.search(r"(\d{6})", str(value))
    if not match:
        return None
    return match.group(1)


def _first_present(row: dict[str, Any], raw_fields: list[str]) -> Any:
    for raw_field in raw_fields:
        if raw_field in row and row[raw_field] not in (None, ""):
            return row[raw_field]
    return None


def _as_float(value: Any) -> float | None:
    if value in (None, ""):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None
