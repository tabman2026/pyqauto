"""Live source schema probe runner."""

from __future__ import annotations

import json
import math
import uuid
from pathlib import Path
from typing import Any

from pyqauto.adapters.akshare_em_spot_adapter import (
    AKSHARE_EM_SPOT_FIELD_MAPPING,
    AkShareEmSpotAdapter,
)
from pyqauto.adapters.akshare_em_spot_adapter import (
    SOURCE_API as AKSHARE_SOURCE_API,
)
from pyqauto.adapters.base import BaseQuoteAdapter, code_for_symbol
from pyqauto.adapters.easyquotation_sina_adapter import (
    EASYQUOTATION_FIELD_MAPPING,
    EasyQuotationSinaAdapter,
)
from pyqauto.adapters.easyquotation_tencent_adapter import EasyQuotationTencentAdapter
from pyqauto.adapters.pytdx_adapter import (
    PYTDX_KLINE_FIELD_MAPPING,
    PYTDX_KLINE_PERIOD_CATEGORIES,
    PYTDX_QUOTE_FIELD_MAPPING,
    PytdxAdapter,
)
from pyqauto.policy import DEFAULT_PYTDX_SERVERS_PATH, load_pytdx_servers
from pyqauto.source_schema import (
    STANDARD_SCHEMA_VERSION,
    UNIT_RULES,
    first_row_sample,
    normalize_standard_symbol,
    raw_columns,
    raw_dtypes,
    raw_keys,
    raw_records,
    raw_row_count,
    utc_now_iso,
    write_raw_payload,
)

LIVE_PROBE_REPORT_PATH = Path("reports/latest/source_schema_probe_live.json")
LIVE_PROBE_LOG_PATH = Path("logs/source_schema_probe_live.jsonl")

REQUIRED_SAMPLE_SYMBOLS = ("600519.SH", "000001.SZ")
OPTIONAL_SAMPLE_SYMBOL_GROUPS = {
    "etf": ("513300.SH", "159001.SZ"),
    "beijing": ("430017.BJ", "831195.BJ"),
}
SAMPLE_SYMBOLS = (
    *REQUIRED_SAMPLE_SYMBOLS,
    *OPTIONAL_SAMPLE_SYMBOL_GROUPS["etf"],
    *OPTIONAL_SAMPLE_SYMBOL_GROUPS["beijing"],
)


def _sample_config(
    symbols: list[str] | tuple[str, ...] | None,
) -> tuple[tuple[str, ...], dict[str, tuple[str, ...]]]:
    if not symbols:
        return REQUIRED_SAMPLE_SYMBOLS, dict(OPTIONAL_SAMPLE_SYMBOL_GROUPS)
    required = tuple(dict.fromkeys(normalize_standard_symbol(symbol) for symbol in symbols))
    return required, {}


def _all_sample_symbols(
    required_sample_symbols: tuple[str, ...],
    optional_sample_symbol_groups: dict[str, tuple[str, ...]],
) -> tuple[str, ...]:
    values: list[str] = list(required_sample_symbols)
    for symbols in optional_sample_symbol_groups.values():
        values.extend(symbols)
    return tuple(dict.fromkeys(values))


def _contract_summary(probes: list[dict[str, Any]]) -> dict[str, Any]:
    sources = [_source_contract(probe) for probe in probes]
    return {
        "overall_status": _overall_status(probes),
        "sources": sources,
        "source_status": {
            _source_contract_key(source): source["source_status"] for source in sources
        },
        "schema_status": {
            _source_contract_key(source): source["schema_status"] for source in sources
        },
        "missing_fields": {
            _source_contract_key(source): source["missing_fields"] for source in sources
        },
        "schema_drift_fields": {
            _source_contract_key(source): source["schema_drift_fields"] for source in sources
        },
        "rejected_reason": {
            _source_contract_key(source): source["rejected_reason"] for source in sources
        },
        "error_message": {
            _source_contract_key(source): source["error_message"] for source in sources
        },
        "accepted_record_count": sum(source["accepted_record_count"] for source in sources),
        "rejected_record_count": sum(source["rejected_record_count"] for source in sources),
    }


def _source_contract(probe: dict[str, Any]) -> dict[str, Any]:
    validate_result = probe.get("validate_result")
    if not isinstance(validate_result, dict):
        validate_result = {}
    diagnose = validate_result.get("diagnose")
    if not isinstance(diagnose, dict):
        diagnose = {}
    source_status = str(probe.get("adapter_status") or "failed")
    schema_status = str(validate_result.get("adapter_status") or source_status)
    return {
        "source_name": probe.get("source_name"),
        "source_api": probe.get("source_api"),
        "source_status": source_status,
        "schema_status": schema_status,
        "missing_fields": list(validate_result.get("missing_fields") or []),
        "schema_drift_fields": list(diagnose.get("schema_drift_fields") or []),
        "rejected_reason": diagnose.get("rejection_reason"),
        "error_message": probe.get("error_message"),
        "accepted_record_count": int(probe.get("public_record_count") or 0),
        "rejected_record_count": int(probe.get("rejected_public_record_count") or 0),
    }


def _source_contract_key(source: dict[str, Any]) -> str:
    return f"{source.get('source_name')}::{source.get('source_api')}"


def run_source_schema_probe_live(
    *,
    report_path: str | Path = LIVE_PROBE_REPORT_PATH,
    log_path: str | Path = LIVE_PROBE_LOG_PATH,
    pytdx_servers_path: str | Path | None = DEFAULT_PYTDX_SERVERS_PATH,
    symbols: list[str] | tuple[str, ...] | None = None,
    adapters: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Run live provider schema probes and write JSON plus JSONL outputs."""

    injected_adapters = adapters or {}
    run_id = uuid.uuid4().hex
    generated_at = utc_now_iso()
    required_symbols, optional_symbol_groups = _sample_config(symbols)
    sample_symbols = _all_sample_symbols(required_symbols, optional_symbol_groups)
    pytdx_adapters, pytdx_error = _load_pytdx_adapters(
        pytdx_servers_path,
        injected=injected_adapters.get("pytdx"),
    )

    probes = [
        _probe_akshare(
            injected_adapters.get("akshare_em_spot"),
            sample_symbols=sample_symbols,
            required_sample_symbols=required_symbols,
            optional_sample_symbol_groups=optional_symbol_groups,
        ),
        _probe_pytdx_quote(
            pytdx_adapters,
            pytdx_error,
            sample_symbols=sample_symbols,
            required_sample_symbols=required_symbols,
            optional_sample_symbol_groups=optional_symbol_groups,
        ),
        _probe_pytdx_kline(
            pytdx_adapters,
            pytdx_error,
            sample_symbols=sample_symbols,
            required_sample_symbols=required_symbols,
            optional_sample_symbol_groups=optional_symbol_groups,
        ),
        _probe_easyquotation(
            injected_adapters.get("easyquotation_sina"),
            source_name="easyquotation_sina",
            provider_api="easyquotation.sina.stocks",
            default_adapter=EasyQuotationSinaAdapter(),
            sample_symbols=sample_symbols,
            required_sample_symbols=required_symbols,
            optional_sample_symbol_groups=optional_symbol_groups,
        ),
        _probe_easyquotation(
            injected_adapters.get("easyquotation_tencent"),
            source_name="easyquotation_tencent",
            provider_api="easyquotation.tencent.stocks",
            default_adapter=EasyQuotationTencentAdapter(),
            sample_symbols=sample_symbols,
            required_sample_symbols=required_symbols,
            optional_sample_symbol_groups=optional_symbol_groups,
        ),
    ]
    contract = _contract_summary(probes)
    payload = {
        "schema_version": STANDARD_SCHEMA_VERSION,
        "probe_type": "source_schema_probe_live",
        "run_id": run_id,
        "generated_at": generated_at,
        "checked_at": generated_at,
        **contract,
        "sample_symbols": {
            "required": list(required_symbols),
            "optional_groups": {
                key: list(value) for key, value in optional_symbol_groups.items()
            },
        },
        "probes": probes,
        "acceptance": _acceptance_summary(
            probes,
            required_sample_symbols=required_symbols,
        ),
        "audit": {
            "conclusion": _audit_conclusion(probes),
            "acceptance_result": _overall_status(probes),
            "boundary": (
                "read-only source schema validation; "
                "no investment advice or order execution"
            ),
        },
    }
    _write_live_report(payload, Path(report_path))
    _append_live_jsonl(probes, Path(log_path), run_id=run_id, generated_at=generated_at)
    return payload


def load_latest_live_probe_report(
    report_path: str | Path = LIVE_PROBE_REPORT_PATH,
) -> dict[str, Any] | None:
    """Load the latest live schema probe report for diagnostics."""

    path = Path(report_path)
    if not path.exists():
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    if isinstance(payload, dict):
        return payload
    return None


def summarize_live_probe_report(payload: dict[str, Any] | None) -> dict[str, Any]:
    """Return a compact diagnose-safe summary of the latest live probe report."""

    if not payload:
        return {"exists": False}
    probes = payload.get("probes")
    if not isinstance(probes, list):
        probes = []
    source_status = payload.get("source_status")
    if not isinstance(source_status, dict):
        source_status = {
            _probe_key(probe): probe.get("adapter_status")
            for probe in probes
            if isinstance(probe, dict)
        }
    return {
        "exists": True,
        "overall_status": payload.get("overall_status"),
        "checked_at": payload.get("checked_at") or payload.get("generated_at"),
        "generated_at": payload.get("generated_at"),
        "report_path": str(LIVE_PROBE_REPORT_PATH).replace("\\", "/"),
        "log_path": str(LIVE_PROBE_LOG_PATH).replace("\\", "/"),
        "source_status": source_status,
        "schema_status": payload.get("schema_status"),
        "accepted_record_count": payload.get("accepted_record_count"),
        "rejected_record_count": payload.get("rejected_record_count"),
        "drift": {
            _probe_key(probe): _probe_drift_summary(probe)
            for probe in probes
            if isinstance(probe, dict)
            and probe.get("adapter_status") in {"schema_drift", "field_missing"}
        },
        "acceptance": payload.get("acceptance"),
    }


def _probe_akshare(
    adapter: Any | None,
    *,
    sample_symbols: tuple[str, ...],
    required_sample_symbols: tuple[str, ...],
    optional_sample_symbol_groups: dict[str, tuple[str, ...]],
) -> dict[str, Any]:
    source_name = "akshare_em_spot"
    source_api = AKSHARE_SOURCE_API
    live_adapter = adapter or AkShareEmSpotAdapter()
    return _probe_batch_source(
        adapter=live_adapter,
        source_name=source_name,
        source_api=source_api,
        kind="quote",
        field_mapping=AKSHARE_EM_SPOT_FIELD_MAPPING,
        unit_rules=_unit_rules_for(source_name),
        fetch_raw=lambda: live_adapter.fetch_raw(symbols=list(sample_symbols)),
        normalize=lambda raw, fetch_time, raw_payload_path: live_adapter.normalize_to_standard(
            raw,
            symbols=list(sample_symbols),
            fetch_time=fetch_time,
            raw_payload_path=raw_payload_path,
            source_api=source_api,
        ),
        required_sample_symbols=required_sample_symbols,
        optional_sample_symbol_groups=optional_sample_symbol_groups,
    )


def _probe_easyquotation(
    adapter: Any | None,
    *,
    source_name: str,
    provider_api: str,
    default_adapter: BaseQuoteAdapter,
    sample_symbols: tuple[str, ...],
    required_sample_symbols: tuple[str, ...],
    optional_sample_symbol_groups: dict[str, tuple[str, ...]],
) -> dict[str, Any]:
    live_adapter = adapter or default_adapter
    return _probe_batch_source(
        adapter=live_adapter,
        source_name=source_name,
        source_api=provider_api,
        kind="quote",
        field_mapping=EASYQUOTATION_FIELD_MAPPING,
        unit_rules=_unit_rules_for(source_name),
        fetch_raw=lambda: live_adapter.fetch_raw(symbols=list(sample_symbols)),
        normalize=lambda raw, fetch_time, raw_payload_path: live_adapter.normalize_to_standard(
            raw,
            symbols=list(sample_symbols),
            fetch_time=fetch_time,
            raw_payload_path=raw_payload_path,
            source_api=provider_api,
        ),
        required_sample_symbols=required_sample_symbols,
        optional_sample_symbol_groups=optional_sample_symbol_groups,
    )


def _probe_pytdx_quote(
    adapters: list[BaseQuoteAdapter],
    load_error: str | None,
    *,
    sample_symbols: tuple[str, ...],
    required_sample_symbols: tuple[str, ...],
    optional_sample_symbol_groups: dict[str, tuple[str, ...]],
) -> dict[str, Any]:
    source_name = "pytdx"
    source_api = "pytdx.get_security_quotes"
    if load_error:
        return _error_probe(
            source_name,
            source_api,
            load_error,
            PYTDX_QUOTE_FIELD_MAPPING,
            required_sample_symbols=required_sample_symbols,
            optional_sample_symbol_groups=optional_sample_symbol_groups,
        )
    return _probe_pytdx_source(
        adapters=adapters,
        source_name=source_name,
        source_api=source_api,
        kind="quote",
        field_mapping=PYTDX_QUOTE_FIELD_MAPPING,
        fetch_with_adapter=lambda adapter: adapter.fetch_raw(
            source_api=source_api,
            symbols=list(sample_symbols),
        ),
        normalize=lambda adapter, raw, fetch_time, raw_payload_path: adapter.normalize_to_standard(
            raw,
            source_api=source_api,
            symbols=list(sample_symbols),
            fetch_time=fetch_time,
            raw_payload_path=raw_payload_path,
        ),
        required_sample_symbols=required_sample_symbols,
        optional_sample_symbol_groups=optional_sample_symbol_groups,
    )


def _probe_pytdx_kline(
    adapters: list[BaseQuoteAdapter],
    load_error: str | None,
    *,
    sample_symbols: tuple[str, ...],
    required_sample_symbols: tuple[str, ...],
    optional_sample_symbol_groups: dict[str, tuple[str, ...]],
) -> dict[str, Any]:
    source_name = "pytdx"
    source_api = "pytdx.get_security_bars"
    if load_error:
        return _error_probe(
            source_name,
            source_api,
            load_error,
            PYTDX_KLINE_FIELD_MAPPING,
            required_sample_symbols=required_sample_symbols,
            optional_sample_symbol_groups=optional_sample_symbol_groups,
        )

    def fetch_with_adapter(adapter: BaseQuoteAdapter) -> list[dict[str, Any]]:
        rows: list[dict[str, Any]] = []
        required_errors: list[str] = []
        category = PYTDX_KLINE_PERIOD_CATEGORIES["1d"]
        for symbol in sample_symbols:
            try:
                raw = adapter.fetch_raw(
                    source_api=source_api,
                    symbol=code_for_symbol(symbol),
                    period="1d",
                    count=2,
                    category=category,
                )
            except Exception as exc:
                if symbol in required_sample_symbols:
                    required_errors.append(f"{symbol}: {exc}")
                continue
            for row in raw_records(raw):
                row_with_symbol = dict(row)
                row_with_symbol["request_symbol"] = code_for_symbol(symbol)
                rows.append(row_with_symbol)
        if required_errors:
            raise RuntimeError("; ".join(required_errors))
        return rows

    def normalize(
        adapter: BaseQuoteAdapter,
        raw: Any,
        fetch_time: str,
        raw_payload_path: str | None,
    ) -> list[dict[str, Any]]:
        rows: list[dict[str, Any]] = []
        for row in raw_records(raw):
            request_symbol = str(row.get("request_symbol") or "")
            rows.extend(
                adapter.normalize_to_standard(
                    [row],
                    source_api=source_api,
                    symbol=request_symbol,
                    period="1d",
                    fetch_time=fetch_time,
                    raw_payload_path=raw_payload_path,
                )
            )
        return rows

    return _probe_pytdx_source(
        adapters=adapters,
        source_name=source_name,
        source_api=source_api,
        kind="kline",
        field_mapping=PYTDX_KLINE_FIELD_MAPPING,
        fetch_with_adapter=fetch_with_adapter,
        normalize=normalize,
        required_sample_symbols=required_sample_symbols,
        optional_sample_symbol_groups=optional_sample_symbol_groups,
    )


def _probe_pytdx_source(
    *,
    adapters: list[BaseQuoteAdapter],
    source_name: str,
    source_api: str,
    kind: str,
    field_mapping: dict[str, str | list[str]],
    fetch_with_adapter: Any,
    normalize: Any,
    required_sample_symbols: tuple[str, ...],
    optional_sample_symbol_groups: dict[str, tuple[str, ...]],
) -> dict[str, Any]:
    if not adapters:
        return _error_probe(
            source_name,
            source_api,
            "no enabled pytdx server configured",
            field_mapping,
            required_sample_symbols=required_sample_symbols,
            optional_sample_symbol_groups=optional_sample_symbol_groups,
        )
    errors: list[str] = []
    for adapter in adapters:
        try:
            return _probe_batch_source(
                adapter=adapter,
                source_name=source_name,
                source_api=source_api,
                kind=kind,
                field_mapping=field_mapping,
                unit_rules=_unit_rules_for(source_name),
                fetch_raw=lambda adapter=adapter: fetch_with_adapter(adapter),
                normalize=lambda raw, fetch_time, raw_payload_path, adapter=adapter: normalize(
                    adapter,
                    raw,
                    fetch_time,
                    raw_payload_path,
                ),
                adapter_meta={
                    "source_level": getattr(adapter, "source_level", None),
                    "server": _safe_pytdx_server(adapter),
                },
                propagate_errors=True,
                required_sample_symbols=required_sample_symbols,
                optional_sample_symbol_groups=optional_sample_symbol_groups,
            )
        except Exception as exc:
            errors.append(str(exc))
    return _error_probe(
        source_name,
        source_api,
        "all pytdx servers failed: " + "; ".join(errors),
        field_mapping,
        required_sample_symbols=required_sample_symbols,
        optional_sample_symbol_groups=optional_sample_symbol_groups,
    )


def _probe_batch_source(
    *,
    adapter: BaseQuoteAdapter,
    source_name: str,
    source_api: str,
    kind: str,
    field_mapping: dict[str, str | list[str]],
    unit_rules: list[dict[str, Any]],
    fetch_raw: Any,
    normalize: Any,
    adapter_meta: dict[str, Any] | None = None,
    propagate_errors: bool = False,
    required_sample_symbols: tuple[str, ...],
    optional_sample_symbol_groups: dict[str, tuple[str, ...]],
) -> dict[str, Any]:
    fetch_time = utc_now_iso()
    raw: Any = None
    raw_payload_path: str | None = None
    standard_rows: list[dict[str, Any]] = []
    error_message: str | None = None
    try:
        raw = fetch_raw()
        raw_payload_path = str(write_raw_payload(source_name, source_api, raw, fetch_time))
        standard_rows = normalize(raw, fetch_time, raw_payload_path)
        validation = adapter.validate_standard_output(
            standard_rows,
            kind=kind,
            field_mapping=field_mapping,
        ).to_dict()
        sample_results = _sample_results(
            standard_rows,
            required_sample_symbols=required_sample_symbols,
            optional_sample_symbol_groups=optional_sample_symbol_groups,
        )
        validation = _apply_sample_gate(
            validation,
            standard_rows,
            sample_results,
            required_sample_symbols=required_sample_symbols,
        )
        adapter_status = str(validation["adapter_status"])
    except Exception as exc:
        if propagate_errors:
            raise
        error_message = str(exc)
        validation = _failed_validation("failed", error_message)
        sample_results = _failed_sample_results(
            error_message,
            required_sample_symbols=required_sample_symbols,
            optional_sample_symbol_groups=optional_sample_symbol_groups,
        )
        adapter_status = "failed"

    probe = _base_probe(
        source_name=source_name,
        source_api=source_api,
        raw=raw,
        fetch_time=fetch_time,
        field_mapping=field_mapping,
        unit_rules=unit_rules,
        validate_result=validation,
        adapter_status=adapter_status,
        error_message=error_message,
        raw_payload_path=raw_payload_path,
        standard_rows=standard_rows,
        sample_results=sample_results,
    )
    if adapter_meta:
        probe["adapter_meta"] = adapter_meta
    return probe


def _base_probe(
    *,
    source_name: str,
    source_api: str,
    raw: Any,
    fetch_time: str,
    field_mapping: dict[str, str | list[str]],
    unit_rules: list[dict[str, Any]],
    validate_result: dict[str, Any],
    adapter_status: str,
    error_message: str | None,
    raw_payload_path: str | None,
    standard_rows: list[dict[str, Any]],
    sample_results: dict[str, Any],
) -> dict[str, Any]:
    is_valid = bool(validate_result.get("is_valid"))
    return {
        "source_name": source_name,
        "source_api": source_api,
        "raw_type": type(raw).__name__ if raw is not None else None,
        "raw_columns_or_keys": raw_columns(raw) or raw_keys(raw),
        "raw_dtypes": raw_dtypes(raw),
        "first_row_sample": first_row_sample(raw),
        "row_count": raw_row_count(raw),
        "fetch_time": fetch_time,
        "raw_to_standard_mapping": field_mapping,
        "unit_rules": unit_rules,
        "validate_result": validate_result,
        "adapter_status": adapter_status,
        "error_message": error_message,
        "raw_payload_path": raw_payload_path,
        "sample_results": sample_results,
        "standard_sample": _standard_sample(standard_rows) if is_valid else [],
        "public_record_count": len(standard_rows) if is_valid else 0,
        "rejected_public_record_count": 0 if is_valid else len(standard_rows),
    }


def _error_probe(
    source_name: str,
    source_api: str,
    error_message: str,
    field_mapping: dict[str, str | list[str]],
    *,
    required_sample_symbols: tuple[str, ...],
    optional_sample_symbol_groups: dict[str, tuple[str, ...]],
) -> dict[str, Any]:
    return _base_probe(
        source_name=source_name,
        source_api=source_api,
        raw=None,
        fetch_time=utc_now_iso(),
        field_mapping=field_mapping,
        unit_rules=_unit_rules_for(source_name),
        validate_result=_failed_validation("failed", error_message),
        adapter_status="failed",
        error_message=error_message,
        raw_payload_path=None,
        standard_rows=[],
        sample_results=_failed_sample_results(
            error_message,
            required_sample_symbols=required_sample_symbols,
            optional_sample_symbol_groups=optional_sample_symbol_groups,
        ),
    )


def _sample_results(
    rows: list[dict[str, Any]],
    *,
    required_sample_symbols: tuple[str, ...],
    optional_sample_symbol_groups: dict[str, tuple[str, ...]],
) -> dict[str, Any]:
    rows_by_symbol = {
        str(row.get("symbol")): row
        for row in rows
        if row.get("symbol") not in (None, "")
    }
    symbol_results: dict[str, Any] = {}
    for symbol in required_sample_symbols:
        row = rows_by_symbol.get(symbol)
        if row:
            symbol_results[symbol] = _row_sample_status(row)
        else:
            symbol_results[symbol] = {
                "status": "field_missing",
                "reason": "required sample symbol was not returned",
            }
    for symbols in optional_sample_symbol_groups.values():
        for symbol in symbols:
            row = rows_by_symbol.get(symbol)
            if row:
                symbol_results[symbol] = _row_sample_status(row)
            else:
                symbol_results[symbol] = {
                    "status": "unsupported",
                    "reason": "optional sample symbol was not returned",
                }

    groups = {
        "required": {
            "status": (
                "ok"
                if all(
                    symbol_results[symbol]["status"] == "ok"
                    for symbol in required_sample_symbols
                )
                else "field_missing"
            ),
            "symbols": list(required_sample_symbols),
        }
    }
    for group_name, symbols in optional_sample_symbol_groups.items():
        statuses = [symbol_results[symbol]["status"] for symbol in symbols]
        if "ok" in statuses:
            group_status = "ok"
        elif "schema_drift" in statuses:
            group_status = "schema_drift"
        elif "field_missing" in statuses:
            group_status = "field_missing"
        else:
            group_status = "unsupported"
        groups[group_name] = {
            "status": group_status,
            "symbols": list(symbols),
        }

    return {"symbols": symbol_results, "groups": groups}


def _row_sample_status(row: dict[str, Any]) -> dict[str, Any]:
    status = str(row.get("adapter_status") or "ok")
    return {
        "status": status,
        "symbol_raw": row.get("symbol_raw"),
        "market": row.get("market"),
    }


def _apply_sample_gate(
    validation: dict[str, Any],
    rows: list[dict[str, Any]],
    sample_results: dict[str, Any],
    *,
    required_sample_symbols: tuple[str, ...],
) -> dict[str, Any]:
    symbols = sample_results.get("symbols", {})
    missing_required = [
        symbol
        for symbol in required_sample_symbols
        if symbols.get(symbol, {}).get("status") != "ok"
    ]
    if not missing_required:
        return validation

    validation = dict(validation)
    diagnose = dict(validation.get("diagnose") or {})
    missing_fields = list(validation.get("missing_fields") or [])
    for symbol in missing_required:
        marker = f"sample_symbol:{symbol}"
        if marker not in missing_fields:
            missing_fields.append(marker)
    validation["is_valid"] = False
    status = str(validation.get("adapter_status") or "")
    validation["adapter_status"] = "schema_drift" if status == "schema_drift" else "field_missing"
    validation["missing_fields"] = missing_fields
    diagnose["missing_sample_symbols"] = missing_required
    diagnose["rejection_reason"] = (
        "required live sample symbols were not returned: " + ", ".join(missing_required)
    )
    validation["diagnose"] = diagnose
    for row in rows:
        row["adapter_status"] = validation["adapter_status"]
    return validation


def _failed_validation(status: str, error_message: str) -> dict[str, Any]:
    return {
        "is_valid": False,
        "adapter_status": status,
        "row_count": 0,
        "missing_fields": [],
        "diagnose": {
            "missing_fields": [],
            "schema_drift_fields": [],
            "rejection_reason": error_message,
        },
    }


def _failed_sample_results(
    error_message: str,
    *,
    required_sample_symbols: tuple[str, ...],
    optional_sample_symbol_groups: dict[str, tuple[str, ...]],
) -> dict[str, Any]:
    symbols: dict[str, Any] = {}
    for symbol in _all_sample_symbols(required_sample_symbols, optional_sample_symbol_groups):
        symbols[symbol] = {"status": "failed", "reason": error_message}
    groups = {
        "required": {
            "status": "failed",
            "symbols": list(required_sample_symbols),
        }
    }
    for group_name, group_symbols in optional_sample_symbol_groups.items():
        groups[group_name] = {
            "status": "failed",
            "symbols": list(group_symbols),
        }
    return {
        "symbols": symbols,
        "groups": groups,
    }


def _standard_sample(rows: list[dict[str, Any]], limit: int = 5) -> list[dict[str, Any]]:
    return [_json_safe(_public_standard_row(row)) for row in rows[:limit]]


def _public_standard_row(row: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in row.items() if not key.startswith("_")}


def _acceptance_summary(
    probes: list[dict[str, Any]],
    *,
    required_sample_symbols: tuple[str, ...],
) -> dict[str, Any]:
    overall_status = _overall_status(probes)
    return {
        "required_sources": [
            "akshare.stock_zh_a_spot_em",
            "pytdx.get_security_quotes",
            "pytdx.get_security_bars",
            "easyquotation.sina.stocks",
            "easyquotation.tencent.stocks",
        ],
        "required_sample_symbols": list(required_sample_symbols),
        "overall_status": overall_status,
        "passed": overall_status == "PASS",
        "source_status": {
            _probe_key(probe): probe.get("adapter_status") for probe in probes
        },
    }


def _overall_status(probes: list[dict[str, Any]]) -> str:
    ok_count = sum(1 for probe in probes if probe.get("adapter_status") == "ok")
    if probes and ok_count == len(probes):
        return "PASS"
    if ok_count > 0:
        return "WARN"
    return "FAIL"


def _audit_conclusion(probes: list[dict[str, Any]]) -> str:
    status = _overall_status(probes)
    if status == "PASS":
        return "live schema probe completed with all adapters validated"
    if status == "FAIL":
        return "live schema probe failed because all adapters were rejected or unavailable"
    return "live schema probe completed with one or more adapters rejected or unavailable"


def _write_live_report(payload: dict[str, Any], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(_json_safe(payload), ensure_ascii=False, indent=2), encoding="utf-8")


def _append_live_jsonl(
    probes: list[dict[str, Any]],
    path: Path,
    *,
    run_id: str,
    generated_at: str,
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as file:
        for probe in probes:
            payload = {
                "run_id": run_id,
                "generated_at": generated_at,
                **probe,
            }
            file.write(json.dumps(_json_safe(payload), ensure_ascii=False) + "\n")


def _load_pytdx_adapters(
    pytdx_servers_path: str | Path | None,
    *,
    injected: Any,
) -> tuple[list[BaseQuoteAdapter], str | None]:
    if injected is not None:
        if isinstance(injected, list):
            return injected, None
        return [injected], None
    try:
        servers = load_pytdx_servers(pytdx_servers_path)
    except Exception as exc:
        return [], str(exc)
    return [PytdxAdapter(server) for server in servers], None


def _unit_rules_for(source_name: str) -> list[dict[str, Any]]:
    source_rules = [rule for rule in UNIT_RULES if rule.get("source_name") == source_name]
    generic_rules = [rule for rule in UNIT_RULES if "source_name" not in rule]
    return [*source_rules, *generic_rules]


def _probe_key(probe: dict[str, Any]) -> str:
    return f"{probe.get('source_name')}::{probe.get('source_api')}"


def _probe_drift_summary(probe: dict[str, Any]) -> dict[str, Any]:
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


def _safe_pytdx_server(adapter: BaseQuoteAdapter) -> dict[str, Any] | None:
    server = getattr(adapter, "server", None)
    if server is None:
        return None
    return {
        "host": getattr(server, "host", None),
        "port": getattr(server, "port", None),
        "role": getattr(server, "role", None),
    }


def _json_safe(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(key): _json_safe(item) for key, item in value.items()}
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
