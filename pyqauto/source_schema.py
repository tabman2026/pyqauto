"""Raw source schema probing and standard quote normalization helpers."""

from __future__ import annotations

import json
import math
import re
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

STANDARD_SCHEMA_VERSION = "quote.v1"

STANDARD_QUOTE_FIELDS = [
    "symbol",
    "symbol_raw",
    "market",
    "name",
    "trade_time",
    "fetch_time",
    "last_price",
    "pre_close",
    "open",
    "high",
    "low",
    "change",
    "pct_chg",
    "volume_shares",
    "amount_yuan",
    "turnover_rate",
    "source_name",
    "source_api",
    "schema_version",
    "adapter_status",
    "raw_payload_path",
]

QUOTE_CORE_FIELDS = [
    "symbol",
    "symbol_raw",
    "market",
    "fetch_time",
    "last_price",
    "pre_close",
    "open",
    "high",
    "low",
    "volume_shares",
    "amount_yuan",
    "source_name",
    "source_api",
    "schema_version",
]

KLINE_CORE_FIELDS = [
    "symbol",
    "symbol_raw",
    "market",
    "trade_time",
    "fetch_time",
    "last_price",
    "open",
    "high",
    "low",
    "volume_shares",
    "amount_yuan",
    "source_name",
    "source_api",
    "schema_version",
]

PROBE_REPORT_PATH = Path("reports/latest/source_schema_probe.json")
PROBE_LOG_PATH = Path("logs/source_schema_probe.jsonl")
LIVE_PROBE_REPORT_PATH = Path("reports/latest/source_schema_probe_live.json")
LIVE_PROBE_LOG_PATH = Path("logs/source_schema_probe_live.jsonl")
RAW_PAYLOAD_DIR = Path("reports/latest/raw_payloads")

UNIT_RULES = [
    {
        "source_name": "akshare_em_spot",
        "source_api": "akshare.stock_zh_a_spot_em",
        "raw_field": "成交量",
        "raw_unit": "手",
        "standard_field": "volume_shares",
        "conversion": "multiply_by_100",
    },
    {
        "source_name": "akshare_em_spot",
        "source_api": "akshare.stock_zh_a_spot_em",
        "raw_field": "成交额",
        "raw_unit": "元",
        "standard_field": "amount_yuan",
        "conversion": "keep_yuan",
    },
    {
        "source_name": "easyquotation_tencent",
        "source_api": "easyquotation.tencent.stocks",
        "raw_field": "价格/成交量(手)/成交额",
        "raw_unit": "price/hand/yuan",
        "standard_field": "volume_shares",
        "conversion": "parse_second_part_and_multiply_by_100",
    },
    {
        "source_name": "easyquotation_tencent",
        "source_api": "easyquotation.tencent.stocks",
        "raw_field": "价格/成交量(手)/成交额",
        "raw_unit": "price/hand/yuan",
        "standard_field": "amount_yuan",
        "conversion": "parse_third_part_keep_yuan",
    },
    {
        "standard_field": "pct_chg",
        "standard_unit": "percent_number",
        "example": "4.8 means 4.8%",
    },
    {
        "standard_field": "symbol",
        "standard_format": "600519.SH / 000001.SZ / 430017.BJ",
    },
]


@dataclass(frozen=True)
class StandardValidationResult:
    """Validation result for standard adapter output."""

    is_valid: bool
    adapter_status: str
    row_count: int
    missing_fields: list[str]
    diagnose: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def utc_now_iso() -> str:
    """Return a compact UTC timestamp for probe and standard rows."""

    return datetime.now(timezone.utc).isoformat(timespec="milliseconds")


def normalize_standard_symbol(value: Any) -> str:
    """Normalize an A-share code to 600519.SH / 000001.SZ / 430017.BJ."""

    code = normalize_symbol_code(value)
    return f"{code}.{market_for_code(code)}"


def normalize_symbol_code(value: Any) -> str:
    """Extract a six-digit A-share code from common raw provider formats."""

    raw = str(value or "").strip().upper()
    match = re.search(r"(\d{6})", raw)
    if not match:
        return raw
    return match.group(1)


def market_for_code(value: Any) -> str:
    """Return SH/SZ/BJ for a normalized or raw A-share code."""

    code = normalize_symbol_code(value)
    if code.startswith(("4", "8")):
        return "BJ"
    if code.startswith(("5", "6", "9")):
        return "SH"
    return "SZ"


def as_float(value: Any) -> float | None:
    """Best-effort float conversion that keeps missing values as None."""

    if value in (None, ""):
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    if math.isnan(number) or math.isinf(number):
        return None
    return number


def first_present(row: dict[str, Any], keys: tuple[str, ...]) -> Any:
    """Return the first non-empty value for candidate raw keys."""

    for key in keys:
        if key in row and row[key] not in (None, ""):
            return row[key]
    return None


def pct_change(last_price: Any, pre_close: Any) -> float | None:
    """Calculate percentage change as a percent number, not a ratio."""

    last = as_float(last_price)
    pre = as_float(pre_close)
    if last is None or pre in (None, 0):
        return None
    return (last / pre - 1) * 100


def price_change(last_price: Any, pre_close: Any) -> float | None:
    """Calculate price change from last price and previous close."""

    last = as_float(last_price)
    pre = as_float(pre_close)
    if last is None or pre is None:
        return None
    return last - pre


def build_standard_row(
    *,
    symbol_raw: Any,
    source_name: str,
    source_api: str,
    fetch_time: str,
    name: Any = None,
    trade_time: Any = None,
    last_price: Any = None,
    pre_close: Any = None,
    open_price: Any = None,
    high: Any = None,
    low: Any = None,
    change: Any = None,
    pct_chg: Any = None,
    volume_shares: Any = None,
    amount_yuan: Any = None,
    turnover_rate: Any = None,
    raw_payload_path: str | None = None,
    raw_row: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build one standard quote row with all public standard fields present."""

    code = normalize_symbol_code(symbol_raw)
    valid_code = bool(re.fullmatch(r"\d{6}", code))
    last_price_value = as_float(last_price)
    pre_close_value = as_float(pre_close)
    change_value = as_float(change)
    if change_value is None:
        change_value = price_change(last_price_value, pre_close_value)
    pct_value = as_float(pct_chg)
    if pct_value is None:
        pct_value = pct_change(last_price_value, pre_close_value)

    row: dict[str, Any] = {
        "symbol": normalize_standard_symbol(code) if valid_code else None,
        "symbol_raw": code if valid_code else None,
        "market": market_for_code(code) if valid_code else None,
        "name": None if name in (None, "") else str(name),
        "trade_time": str(trade_time) if trade_time not in (None, "") else fetch_time,
        "fetch_time": fetch_time,
        "last_price": last_price_value,
        "pre_close": pre_close_value,
        "open": as_float(open_price),
        "high": as_float(high),
        "low": as_float(low),
        "change": change_value,
        "pct_chg": pct_value,
        "volume_shares": as_float(volume_shares),
        "amount_yuan": as_float(amount_yuan),
        "turnover_rate": as_float(turnover_rate),
        "source_name": source_name,
        "source_api": source_api,
        "schema_version": STANDARD_SCHEMA_VERSION,
        "adapter_status": "ok",
        "raw_payload_path": raw_payload_path,
    }
    if raw_row is not None:
        row["_raw"] = dict(raw_row)
    return row


def validate_standard_rows(
    rows: list[dict[str, Any]],
    *,
    kind: str = "quote",
    field_mapping: dict[str, str | list[str]] | None = None,
) -> StandardValidationResult:
    """Validate standard rows and report missing core fields without filling zero."""

    core_fields = KLINE_CORE_FIELDS if kind == "kline" else QUOTE_CORE_FIELDS
    missing_fields: list[str] = []
    row_diagnose: list[dict[str, Any]] = []
    schema_drift_fields: list[str] = []
    mapping = field_mapping or {}
    if not rows:
        missing_fields = list(core_fields)
    for index, row in enumerate(rows):
        missing_standard = [field for field in STANDARD_QUOTE_FIELDS if field not in row]
        missing_core = [
            field
            for field in core_fields
            if field not in row or _is_missing(row.get(field))
        ]
        for field in [*missing_standard, *missing_core]:
            if field not in missing_fields:
                missing_fields.append(field)
        for field in missing_core:
            if _raw_mapping_missing(row, mapping, field) and field not in schema_drift_fields:
                schema_drift_fields.append(field)
        if missing_standard or missing_core:
            row_diagnose.append(
                {
                    "row_index": index,
                    "missing_standard_fields": missing_standard,
                    "missing_core_fields": missing_core,
                }
            )

    status = "ok" if rows and not missing_fields else "field_missing"
    if status != "ok" and schema_drift_fields:
        status = "schema_drift"
    for row in rows:
        row["adapter_status"] = status

    diagnose = {
        "kind": kind,
        "standard_fields": list(STANDARD_QUOTE_FIELDS),
        "core_fields": list(core_fields),
        "missing_fields": missing_fields,
        "schema_drift_fields": schema_drift_fields,
        "field_mapping": mapping,
        "raw_to_standard_mapping": mapping,
        "rejection_reason": _rejection_reason(status, missing_fields, schema_drift_fields),
        "row_diagnose": row_diagnose,
    }
    return StandardValidationResult(
        is_valid=status == "ok",
        adapter_status=status,
        row_count=len(rows),
        missing_fields=missing_fields,
        diagnose=diagnose,
    )


def inspect_raw_schema(
    *,
    source_name: str,
    source_api: str,
    raw: Any = None,
    fetch_time: str | None = None,
    error_message: str | None = None,
    field_mapping: dict[str, str | list[str]] | None = None,
    unit_rules: list[dict[str, Any]] | None = None,
    report_path: str | Path = PROBE_REPORT_PATH,
    log_path: str | Path = PROBE_LOG_PATH,
) -> dict[str, Any]:
    """Inspect a raw payload and write the latest JSON report plus JSONL log."""

    fetch_time = fetch_time or utc_now_iso()
    raw_payload_path = None
    if raw is not None:
        raw_payload_path = str(write_raw_payload(source_name, source_api, raw, fetch_time))

    probe = {
        "source_name": source_name,
        "source_api": source_api,
        "raw_type": type(raw).__name__ if raw is not None else None,
        "raw_columns_or_keys": raw_columns(raw) or raw_keys(raw),
        "raw_columns": raw_columns(raw),
        "raw_keys": raw_keys(raw),
        "raw_dtypes": raw_dtypes(raw),
        "first_row_sample": first_row_sample(raw),
        "row_count": raw_row_count(raw),
        "fetch_time": fetch_time,
        "error_message": error_message,
        "field_mapping": field_mapping or {},
        "raw_to_standard_mapping": field_mapping or {},
        "unit_rules": unit_rules or [],
        "raw_payload_path": raw_payload_path,
    }
    _write_probe_report(probe, Path(report_path))
    _append_jsonl(probe, Path(log_path))
    return probe


def raw_records(raw: Any) -> list[dict[str, Any]]:
    """Convert supported raw payload shapes to a list of dict rows."""

    if raw is None:
        return []
    if _is_dataframe_like(raw):
        records = raw.to_dict("records")
        return [dict(record) for record in records]
    if isinstance(raw, list):
        return [dict(item) for item in raw if isinstance(item, dict)]
    if isinstance(raw, tuple):
        return [dict(item) for item in raw if isinstance(item, dict)]
    if isinstance(raw, dict):
        if all(isinstance(value, dict) for value in raw.values()):
            rows = []
            for key, value in raw.items():
                row = dict(value)
                row.setdefault("code", key)
                row.setdefault("symbol", key)
                row["_raw_key"] = key
                rows.append(row)
            return rows
        return [dict(raw)]
    return []


def raw_columns(raw: Any) -> list[str]:
    """Return DataFrame columns or nested row keys for dict/list payloads."""

    if raw is None:
        return []
    if _is_dataframe_like(raw):
        return [str(column) for column in raw.columns]
    columns: list[str] = []
    for row in raw_records(raw):
        for key in row:
            if key not in columns and not key.startswith("_"):
                columns.append(key)
    return columns


def raw_keys(raw: Any) -> list[str]:
    """Return top-level raw keys when the payload is a mapping."""

    if isinstance(raw, dict):
        return [str(key) for key in raw.keys()]
    return raw_columns(raw)


def raw_dtypes(raw: Any) -> dict[str, str]:
    """Return raw dtype information for probe diagnostics."""

    if raw is None:
        return {}
    if _is_dataframe_like(raw):
        return {str(key): str(value) for key, value in raw.dtypes.items()}
    dtypes: dict[str, str] = {}
    for row in raw_records(raw):
        for key, value in row.items():
            if key.startswith("_") or key in dtypes or value is None:
                continue
            dtypes[key] = type(value).__name__
    return dtypes


def first_row_sample(raw: Any) -> dict[str, Any] | None:
    """Return the first row sample in JSON-safe form."""

    records = raw_records(raw)
    if not records:
        return None
    return _json_safe(records[0])


def raw_row_count(raw: Any) -> int:
    """Return raw row count for supported payload shapes."""

    if raw is None:
        return 0
    if _is_dataframe_like(raw):
        return int(len(raw))
    if isinstance(raw, (list, tuple)):
        return len(raw)
    if isinstance(raw, dict):
        if all(isinstance(value, dict) for value in raw.values()):
            return len(raw)
        return 1
    return 0


def source_schema_diagnostics() -> dict[str, Any]:
    """Return offline source schema mappings for diagnose output."""

    return {
        "schema_version": STANDARD_SCHEMA_VERSION,
        "standard_fields": list(STANDARD_QUOTE_FIELDS),
        "unit_rules": list(UNIT_RULES),
        "report_path": str(PROBE_REPORT_PATH).replace("\\", "/"),
        "log_path": str(PROBE_LOG_PATH).replace("\\", "/"),
        "live_report_path": str(LIVE_PROBE_REPORT_PATH).replace("\\", "/"),
        "live_log_path": str(LIVE_PROBE_LOG_PATH).replace("\\", "/"),
        "latest_live_probe": _latest_live_probe_summary(),
    }


def write_raw_payload(
    source_name: str,
    source_api: str,
    raw: Any,
    fetch_time: str,
    *,
    output_dir: str | Path = RAW_PAYLOAD_DIR,
    max_rows: int = 200,
) -> Path:
    """Write a bounded raw payload sample and return its relative path."""

    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    safe_api = re.sub(r"[^A-Za-z0-9_.-]+", "_", source_api)
    timestamp = re.sub(r"[^0-9]+", "", fetch_time)[:17]
    path = output_path / f"{source_name}_{safe_api}_{timestamp}.json"
    payload = {
        "source_name": source_name,
        "source_api": source_api,
        "fetch_time": fetch_time,
        "row_count": raw_row_count(raw),
        "truncated": raw_row_count(raw) > max_rows,
        "rows": raw_records(raw)[:max_rows],
    }
    path.write_text(json.dumps(_json_safe(payload), ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def _write_probe_report(probe: dict[str, Any], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    existing: dict[str, Any] = {"probes": []}
    if path.exists():
        try:
            loaded = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            loaded = {}
        if isinstance(loaded, dict) and isinstance(loaded.get("probes"), list):
            existing = loaded

    key = (probe["source_name"], probe["source_api"])
    probes = [
        item
        for item in existing.get("probes", [])
        if (item.get("source_name"), item.get("source_api")) != key
    ]
    probes.append(probe)
    payload = {
        "schema_version": STANDARD_SCHEMA_VERSION,
        "generated_at": utc_now_iso(),
        "probes": probes,
    }
    path.write_text(json.dumps(_json_safe(payload), ensure_ascii=False, indent=2), encoding="utf-8")


def _append_jsonl(payload: dict[str, Any], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as file:
        file.write(json.dumps(_json_safe(payload), ensure_ascii=False) + "\n")


def _is_dataframe_like(value: Any) -> bool:
    return hasattr(value, "columns") and hasattr(value, "dtypes") and hasattr(value, "to_dict")


def _is_missing(value: Any) -> bool:
    if value is None or value == "":
        return True
    if isinstance(value, float):
        return math.isnan(value) or math.isinf(value)
    return False


def _raw_mapping_missing(
    row: dict[str, Any],
    field_mapping: dict[str, str | list[str]],
    standard_field: str,
) -> bool:
    raw_row = row.get("_raw")
    if not isinstance(raw_row, dict):
        return False
    raw_candidates = field_mapping.get(standard_field)
    if raw_candidates is None:
        return False
    if isinstance(raw_candidates, str):
        candidates = [raw_candidates]
    else:
        candidates = [str(candidate) for candidate in raw_candidates]
    return not any(candidate in raw_row for candidate in candidates)


def _rejection_reason(
    status: str,
    missing_fields: list[str],
    schema_drift_fields: list[str],
) -> str | None:
    if status == "ok":
        return None
    if schema_drift_fields:
        return "raw schema did not expose mapped fields: " + ", ".join(schema_drift_fields)
    if missing_fields:
        return "standard output missing required fields: " + ", ".join(missing_fields)
    return "standard output rejected by schema drift guard"


def _latest_live_probe_summary() -> dict[str, Any]:
    if not LIVE_PROBE_REPORT_PATH.exists():
        return {"exists": False}
    try:
        payload = json.loads(LIVE_PROBE_REPORT_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {"exists": False, "error": "live probe report could not be read"}
    if not isinstance(payload, dict):
        return {"exists": False, "error": "live probe report is not a JSON object"}

    probes = payload.get("probes")
    if not isinstance(probes, list):
        probes = []
    adapter_status = payload.get("source_status")
    if not isinstance(adapter_status, dict):
        adapter_status = {
            _probe_summary_key(probe): probe.get("adapter_status")
            for probe in probes
            if isinstance(probe, dict)
        }
    return {
        "exists": True,
        "overall_status": payload.get("overall_status"),
        "checked_at": payload.get("checked_at") or payload.get("generated_at"),
        "generated_at": payload.get("generated_at"),
        "adapter_status": adapter_status,
        "source_status": adapter_status,
        "schema_status": payload.get("schema_status"),
        "accepted_record_count": payload.get("accepted_record_count"),
        "rejected_record_count": payload.get("rejected_record_count"),
        "drift": {
            _probe_summary_key(probe): _live_probe_drift_summary(probe)
            for probe in probes
            if isinstance(probe, dict)
            and probe.get("adapter_status") in {"schema_drift", "field_missing"}
        },
        "acceptance": payload.get("acceptance"),
    }


def _probe_summary_key(probe: dict[str, Any]) -> str:
    return f"{probe.get('source_name')}::{probe.get('source_api')}"


def _live_probe_drift_summary(probe: dict[str, Any]) -> dict[str, Any]:
    validate_result = probe.get("validate_result")
    if not isinstance(validate_result, dict):
        validate_result = {}
    diagnose = validate_result.get("diagnose")
    if not isinstance(diagnose, dict):
        diagnose = {}
    return {
        "missing_fields": validate_result.get("missing_fields", []),
        "schema_drift_fields": diagnose.get("schema_drift_fields", []),
        "rejection_reason": diagnose.get("rejection_reason"),
    }


def _json_safe(value: Any) -> Any:
    if isinstance(value, dict):
        return {
            str(key): _json_safe(item)
            for key, item in value.items()
            if not str(key).startswith("_")
        }
    if isinstance(value, list):
        return [_json_safe(item) for item in value]
    if isinstance(value, tuple):
        return [_json_safe(item) for item in value]
    if hasattr(value, "item"):
        try:
            return _json_safe(value.item())
        except (TypeError, ValueError):
            pass
    if isinstance(value, float) and (math.isnan(value) or math.isinf(value)):
        return None
    try:
        json.dumps(value, ensure_ascii=False)
    except TypeError:
        return str(value)
    return value
