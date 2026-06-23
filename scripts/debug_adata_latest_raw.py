from __future__ import annotations

import contextlib
import inspect
import io
import json
import platform
import sys
import time
import traceback
from collections.abc import Callable
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
JSON_REPORT_PATH = PROJECT_ROOT / "logs" / "adata_latest_raw_debug_report.json"
MD_REPORT_PATH = PROJECT_ROOT / "ADATA_LATEST_RAW_DEBUG_REPORT.md"

TARGET_STOCK_CODES = ("000001", "600519")
GET_MARKET_START_DATE = "2024-01-01"

DAILY_REQUIRED_FIELDS = [
    "date",
    "code",
    "open",
    "high",
    "low",
    "close",
    "pre_close",
    "volume",
    "amount",
]
REALTIME_REQUIRED_FIELDS = [
    "date",
    "time",
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
]

ADATA_DAILY_MAPPING = {
    "trade_date": "date",
    "date": "date",
    "trade_time": "trade_time",
    "stock_code": "code",
    "code": "code",
    "open": "open",
    "high": "high",
    "low": "low",
    "close": "close",
    "pre_close": "pre_close",
    "volume": "volume",
    "amount": "amount",
    "turnover": "turnover_rate",
    "turnover_rate": "turnover_rate",
    "change_pct": "pct_chg",
    "pct_chg": "pct_chg",
}

ADATA_REALTIME_MAPPING = {
    "trade_date": "date",
    "date": "date",
    "trade_time": "trade_time",
    "time": "time",
    "stock_code": "code",
    "code": "code",
    "short_name": "name",
    "stock_name": "name",
    "name": "name",
    "price": "last_price",
    "now": "last_price",
    "current_price": "last_price",
    "last_price": "last_price",
    "close": "last_price",
    "pre_close": "pre_close",
    "open": "open",
    "high": "high",
    "low": "low",
    "volume": "volume",
    "amount": "amount",
    "turnover": "turnover_rate",
    "turnover_rate": "turnover_rate",
    "change_pct": "pct_chg",
    "pct_chg": "pct_chg",
}


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _emit(console_output: list[str], text: str = "") -> None:
    print(text)
    console_output.append(text)


def _json_records(df: pd.DataFrame) -> list[dict[str, Any]]:
    if df.empty:
        return []
    return json.loads(
        df.to_json(
            orient="records",
            force_ascii=False,
            date_format="iso",
            default_handler=str,
        )
    )


def _dataframe_payload(df: pd.DataFrame) -> dict[str, Any]:
    return {
        "shape": [int(df.shape[0]), int(df.shape[1])],
        "columns": [str(column) for column in df.columns],
        "dtypes": {str(column): str(dtype) for column, dtype in df.dtypes.items()},
        "head": _json_records(df.head(5)),
        "tail": _json_records(df.tail(5)),
        "head_text": df.head(5).to_string(index=False),
        "tail_text": df.tail(5).to_string(index=False),
    }


def _short_repr(value: object, limit: int = 2000) -> str:
    text = repr(value)
    if len(text) <= limit:
        return text
    return f"{text[:limit]}...<truncated>"


def _exception_payload(exc: BaseException) -> dict[str, Any]:
    trace = traceback.format_exception(type(exc), exc, exc.__traceback__)
    return {
        "error_type": type(exc).__name__,
        "error_message": str(exc),
        "traceback_tail": "".join(trace[-5:]),
    }


def _normalize_code_value(value: object) -> str | None:
    digits = "".join(ch for ch in str(value) if ch.isdigit())
    if len(digits) < 6:
        return None
    return digits[-6:]


def _rename_columns(df: pd.DataFrame, mapping: dict[str, str]) -> pd.DataFrame:
    rename_map = {column: mapping[str(column)] for column in df.columns if str(column) in mapping}
    return df.rename(columns=rename_map).copy()


def _derive_date_time(out: pd.DataFrame) -> pd.DataFrame:
    if "date" not in out.columns and "trade_time" in out.columns:
        parsed = pd.to_datetime(out["trade_time"], errors="coerce")
        out["date"] = parsed.dt.strftime("%Y-%m-%d")
        out["time"] = parsed.dt.strftime("%H:%M:%S")
    elif "date" in out.columns:
        out["date"] = pd.to_datetime(out["date"], errors="coerce").dt.strftime("%Y-%m-%d")
    if "time" not in out.columns and "trade_time" in out.columns:
        parsed = pd.to_datetime(out["trade_time"], errors="coerce")
        out["time"] = parsed.dt.strftime("%H:%M:%S")
    return out


def _derive_pre_close_from_pct(price: pd.Series, pct_chg: pd.Series) -> pd.Series:
    pct = pd.to_numeric(pct_chg, errors="coerce") / 100
    price_num = pd.to_numeric(price, errors="coerce")
    return price_num / (1 + pct.replace(-1, pd.NA))


def _zero_value_warnings(rows_for_check: pd.DataFrame, price_columns: list[str]) -> list[str]:
    warnings: list[str] = []
    if rows_for_check.empty:
        return warnings
    for column in price_columns:
        if column not in rows_for_check.columns:
            continue
        numeric = pd.to_numeric(rows_for_check[column], errors="coerce")
        if numeric.isna().any():
            warnings.append(f"field_type_error:{column}")
        if (numeric == 0).any():
            warnings.append(f"zero_price:{column}")
    if "amount" in rows_for_check.columns:
        amount = pd.to_numeric(rows_for_check["amount"], errors="coerce")
        if amount.isna().any():
            warnings.append("field_type_error:amount")
        if (amount == 0).any():
            warnings.append("zero_amount")
    return list(dict.fromkeys(warnings))


def _daily_mapping_evaluation(df: pd.DataFrame, *, requested_code: str | None = None) -> dict[str, Any]:
    if not isinstance(df, pd.DataFrame) or df.empty:
        return {
            "contains_required_fields": False,
            "can_map": False,
            "missing_fields": DAILY_REQUIRED_FIELDS,
            "mapped_columns": [],
            "derived_fields": [],
            "value_warnings": ["empty_dataframe"],
        }
    out = _rename_columns(df, ADATA_DAILY_MAPPING)
    out = _derive_date_time(out)
    if "code" in out.columns:
        out["code"] = out["code"].map(_normalize_code_value)
    elif requested_code is not None:
        out["code"] = requested_code
    derived_fields: list[str] = []
    if "pre_close" not in out.columns and {"close", "pct_chg"}.issubset(out.columns):
        out["pre_close"] = _derive_pre_close_from_pct(out["close"], out["pct_chg"])
        derived_fields.append("pre_close")
    missing = [field for field in DAILY_REQUIRED_FIELDS if field not in out.columns]
    rows_for_check = out
    if requested_code and "code" in out.columns:
        rows_for_check = out[out["code"] == requested_code].copy()
    value_warnings = _zero_value_warnings(rows_for_check, ["open", "high", "low", "close", "pre_close"])
    if rows_for_check.empty:
        value_warnings.append("target_code_missing")
    return {
        "contains_required_fields": not missing,
        "can_map": not missing and not value_warnings,
        "missing_fields": missing,
        "mapped_columns": [str(column) for column in out.columns],
        "derived_fields": derived_fields,
        "value_warnings": list(dict.fromkeys(value_warnings)),
        "mapped_head": _json_records(out.head(5)),
    }


def _realtime_mapping_evaluation(df: pd.DataFrame, *, target_codes: tuple[str, ...]) -> dict[str, Any]:
    if not isinstance(df, pd.DataFrame) or df.empty:
        return {
            "contains_required_fields": False,
            "can_map": False,
            "missing_fields": REALTIME_REQUIRED_FIELDS,
            "mapped_columns": [],
            "matched_target_codes": [],
            "derived_fields": [],
            "value_warnings": ["empty_dataframe"],
        }
    out = _rename_columns(df, ADATA_REALTIME_MAPPING)
    out = _derive_date_time(out)
    if "code" in out.columns:
        out["code"] = out["code"].map(_normalize_code_value)
    derived_fields: list[str] = []
    if "pre_close" not in out.columns and {"last_price", "pct_chg"}.issubset(out.columns):
        out["pre_close"] = _derive_pre_close_from_pct(out["last_price"], out["pct_chg"])
        derived_fields.append("pre_close")
    if "time" not in out.columns:
        out["time"] = datetime.now().strftime("%H:%M:%S")
        derived_fields.append("time")
    if "date" not in out.columns:
        out["date"] = datetime.now().strftime("%Y-%m-%d")
        derived_fields.append("date")
    missing = [field for field in REALTIME_REQUIRED_FIELDS if field not in out.columns]
    matched_codes: list[str] = []
    rows_for_check = out
    if "code" in out.columns:
        target_set = set(target_codes)
        rows_for_check = out[out["code"].isin(target_set)].copy()
        matched_codes = sorted(code for code in target_codes if code in set(rows_for_check["code"].dropna()))
    value_warnings = _zero_value_warnings(
        rows_for_check,
        ["last_price", "pre_close", "open", "high", "low"],
    )
    if len(matched_codes) != len(target_codes):
        value_warnings.append("target_codes_missing")
    return {
        "contains_required_fields": not missing,
        "can_map": not missing and not value_warnings,
        "missing_fields": missing,
        "mapped_columns": [str(column) for column in out.columns],
        "matched_target_codes": matched_codes,
        "derived_fields": derived_fields,
        "value_warnings": list(dict.fromkeys(value_warnings)),
        "mapped_head": _json_records(out.head(5)),
    }


def _load_router_live_reference() -> dict[str, Any]:
    path = PROJECT_ROOT / "logs" / "smoke_test_report.json"
    if not path.exists():
        return {"available": False, "reason": "logs/smoke_test_report.json not found"}
    try:
        report = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        return {"available": False, "reason": f"{type(exc).__name__}: {exc}"}

    def find_result(feature: str) -> dict[str, Any] | None:
        for item in report.get("results", []):
            if item.get("source_name") == "adata" and item.get("feature") == feature:
                return {
                    "status": item.get("status"),
                    "row_count": item.get("row_count"),
                    "reason": item.get("reason"),
                    "params": item.get("params"),
                    "missing_fields": item.get("missing_fields"),
                    "warnings": item.get("warnings"),
                    "fallback_trace": item.get("fallback_trace"),
                }
        return None

    return {
        "available": True,
        "path": str(path.relative_to(PROJECT_ROOT)),
        "created_at": report.get("created_at"),
        "live_enabled": report.get("live_enabled"),
        "adata_daily_kline": find_result("daily_kline"),
        "adata_realtime_quotes": find_result("realtime_quotes"),
        "adata_index_realtime": find_result("index_realtime"),
    }


def _list_market_current_call(market_module: Any, report: dict[str, Any]) -> pd.DataFrame:
    func = market_module.list_market_current
    signature = inspect.signature(func)
    report["list_market_current_signature"] = str(signature)
    params = signature.parameters
    code_list = list(TARGET_STOCK_CODES)
    if "code_list" in params:
        report["list_market_current_mode"] = "code_list"
        return func(code_list=code_list)
    if "stock_codes" in params:
        report["list_market_current_mode"] = "stock_codes"
        return func(stock_codes=code_list)
    if "stock_code" in params:
        report["list_market_current_mode"] = "stock_code"
        frames = [func(stock_code=code) for code in code_list]
        return pd.concat(frames, ignore_index=True)
    report["list_market_current_mode"] = "full_market_then_filter"
    df = func()
    if isinstance(df, pd.DataFrame) and "stock_code" in df.columns:
        return df[df["stock_code"].astype(str).isin(code_list)].copy()
    if isinstance(df, pd.DataFrame) and "code" in df.columns:
        return df[df["code"].astype(str).str.extract(r"(\d{6})", expand=False).isin(code_list)].copy()
    return df


def _run_case(
    *,
    title: str,
    api: str,
    params: dict[str, Any],
    call: Callable[[], Any],
    intended_feature: str,
    console_output: list[str],
    requested_code: str | None = None,
) -> dict[str, Any]:
    _emit(console_output, "")
    _emit(console_output, f"## {title}")
    _emit(console_output, f"api: {api}")
    _emit(console_output, f"params: {json.dumps(params, ensure_ascii=False)}")

    stdout_buffer = io.StringIO()
    stderr_buffer = io.StringIO()
    started_at = time.perf_counter()
    result: dict[str, Any] = {
        "title": title,
        "api": api,
        "params": params,
        "intended_feature": intended_feature,
        "started_at": _utc_now(),
    }
    try:
        with contextlib.redirect_stdout(stdout_buffer), contextlib.redirect_stderr(stderr_buffer):
            data = call()
    except Exception as exc:
        duration_ms = round((time.perf_counter() - started_at) * 1000, 3)
        result.update(
            {
                "status": "FAIL",
                "reason": "exception",
                "duration_ms": duration_ms,
                "captured_stdout": stdout_buffer.getvalue(),
                "captured_stderr": stderr_buffer.getvalue(),
                "error": _exception_payload(exc),
                "daily_kline_mapping": _daily_mapping_evaluation(pd.DataFrame()),
                "realtime_quotes_mapping": _realtime_mapping_evaluation(
                    pd.DataFrame(),
                    target_codes=TARGET_STOCK_CODES,
                ),
            }
        )
        _emit(console_output, f"status: FAIL ({type(exc).__name__}: {exc})")
        _emit(console_output, f"duration_ms: {duration_ms}")
        return result

    duration_ms = round((time.perf_counter() - started_at) * 1000, 3)
    result.update(
        {
            "duration_ms": duration_ms,
            "captured_stdout": stdout_buffer.getvalue(),
            "captured_stderr": stderr_buffer.getvalue(),
        }
    )
    if not isinstance(data, pd.DataFrame):
        result.update(
            {
                "status": "FAIL",
                "reason": "non_dataframe_return",
                "returned_type": type(data).__name__,
                "returned_repr": _short_repr(data),
                "daily_kline_mapping": _daily_mapping_evaluation(pd.DataFrame()),
                "realtime_quotes_mapping": _realtime_mapping_evaluation(
                    pd.DataFrame(),
                    target_codes=TARGET_STOCK_CODES,
                ),
            }
        )
        _emit(console_output, f"status: FAIL (non_dataframe_return: {type(data).__name__})")
        _emit(console_output, f"duration_ms: {duration_ms}")
        return result

    dataframe_payload = _dataframe_payload(data)
    daily_mapping = _daily_mapping_evaluation(data, requested_code=requested_code)
    realtime_mapping = _realtime_mapping_evaluation(data, target_codes=TARGET_STOCK_CODES)
    intended_mapping = daily_mapping if intended_feature == "daily_kline" else realtime_mapping
    if data.empty:
        status = "FAIL"
        reason = "empty_dataframe"
    elif intended_mapping["can_map"]:
        status = "PASS"
        reason = "non_empty_dataframe_and_required_mapping_ok"
    else:
        status = "FAIL"
        reason = "required_mapping_failed"
    result.update(
        {
            "status": status,
            "reason": reason,
            **dataframe_payload,
            "contains_standard_mapping_fields": bool(intended_mapping["contains_required_fields"]),
            "daily_kline_mapping": daily_mapping,
            "realtime_quotes_mapping": realtime_mapping,
        }
    )
    _emit(console_output, f"status: {status} ({reason})")
    _emit(console_output, f"duration_ms: {duration_ms}")
    _emit(console_output, f"shape: {tuple(dataframe_payload['shape'])}")
    _emit(console_output, f"columns: {json.dumps(dataframe_payload['columns'], ensure_ascii=False)}")
    _emit(console_output, f"can_map_daily_kline: {daily_mapping['can_map']}")
    _emit(console_output, f"can_map_realtime_quotes: {realtime_mapping['can_map']}")
    _emit(console_output, "head:")
    _emit(console_output, str(dataframe_payload["head_text"]))
    _emit(console_output, "tail:")
    _emit(console_output, str(dataframe_payload["tail_text"]))
    return result


def _skip_case(title: str, api: str, reason: str) -> dict[str, Any]:
    return {
        "title": title,
        "api": api,
        "params": {},
        "status": "SKIP",
        "reason": reason,
        "duration_ms": 0.0,
        "shape": None,
        "columns": [],
        "head": [],
        "tail": [],
        "daily_kline_mapping": {"can_map": False, "reason": reason},
        "realtime_quotes_mapping": {"can_map": False, "reason": reason},
    }


def _case_status(checks: list[dict[str, Any]], api: str) -> str:
    api_checks = [check for check in checks if check.get("api") == api]
    if not api_checks:
        return "SKIP"
    if all(check.get("status") == "PASS" for check in api_checks):
        return "PASS"
    if any(check.get("status") == "PASS" for check in api_checks):
        return "PARTIAL_PASS"
    if all(check.get("status") == "SKIP" for check in api_checks):
        return "SKIP"
    return "FAIL"


def _build_diagnosis(report: dict[str, Any]) -> dict[str, Any]:
    checks = report.get("checks", [])
    get_market_status = _case_status(checks, "adata.stock.market.get_market")
    realtime_status = _case_status(checks, "adata.stock.market.list_market_current")
    index_status = _case_status(checks, "adata.stock.market.index_realtime")
    router_reference = report.get("router_live_reference", {})
    router_daily_status = (router_reference.get("adata_daily_kline") or {}).get("status")
    router_realtime_status = (router_reference.get("adata_realtime_quotes") or {}).get("status")
    layer_findings: list[str] = []
    if get_market_status == "PASS" and router_daily_status == "FAIL":
        layer_findings.append(
            "adata get_market 原始接口 PASS，但 router live daily_kline FAIL；"
            "证据指向 adapter / 字段映射 / 质量闸门问题。"
        )
    if realtime_status == "PASS" and router_realtime_status == "FAIL":
        layer_findings.append(
            "adata list_market_current 原始接口 PASS，但 router live realtime_quotes FAIL；"
            "证据指向 adapter / 字段映射 / 质量闸门问题。"
        )
    if not layer_findings:
        layer_findings.append("需结合本轮修复后的 live smoke test 再确认 router 层状态。")
    return {
        "raw_get_market_verdict": get_market_status,
        "raw_list_market_current_verdict": realtime_status,
        "raw_index_realtime_verdict": index_status,
        "router_live_adata_daily_kline_status": router_daily_status,
        "router_live_adata_realtime_quotes_status": router_realtime_status,
        "layer_conclusion": " ".join(layer_findings),
        "trading_advice_included": False,
        "s0_connected": False,
    }


def _markdown_table_row(values: list[object]) -> str:
    return "| " + " | ".join(str(value).replace("\n", "<br>") for value in values) + " |"


def _write_markdown_report(report: dict[str, Any]) -> None:
    diagnosis = report["diagnosis"]
    adata_info = report.get("adata", {})
    lines = [
        "# ADATA_LATEST_RAW_DEBUG_REPORT",
        "",
        f"生成时间：{report.get('created_at')}",
        "",
        "## 1. 调试目标",
        "",
        "本报告按 adata 最新已安装版本直接调用原始接口，不修改 S0，不包含任何交易建议。",
        "",
        "## 2. 环境与版本",
        "",
        "| 项目 | 结果 |",
        "|---|---|",
        _markdown_table_row(["Python", report.get("python", {}).get("version")]),
        _markdown_table_row(["Python executable", f"`{report.get('python', {}).get('executable')}`"]),
        _markdown_table_row(["Platform", report.get("platform")]),
        _markdown_table_row(["adata.__version__", adata_info.get("version")]),
        _markdown_table_row(["adata.__file__", f"`{adata_info.get('file')}`"]),
        _markdown_table_row(["list_market_current signature", report.get("list_market_current_signature")]),
        _markdown_table_row(["list_market_current mode", report.get("list_market_current_mode")]),
        "",
        "## 3. 原始接口结果",
        "",
        "| api | params | status | shape | columns | daily_kline 映射 | realtime_quotes 映射 | reason | error |",
        "|---|---|---:|---|---|---:|---:|---|---|",
    ]
    for check in report.get("checks", []):
        shape = tuple(check.get("shape", [])) if check.get("shape") is not None else "-"
        columns = ", ".join(check.get("columns", []) or [])
        error = check.get("error") or {}
        daily_mapping = check.get("daily_kline_mapping") or {}
        realtime_mapping = check.get("realtime_quotes_mapping") or {}
        lines.append(
            _markdown_table_row(
                [
                    check.get("api"),
                    json.dumps(check.get("params", {}), ensure_ascii=False),
                    check.get("status"),
                    shape,
                    columns,
                    daily_mapping.get("can_map"),
                    realtime_mapping.get("can_map"),
                    check.get("reason"),
                    f"{error.get('error_type')}: {error.get('error_message')}" if error else "-",
                ]
            )
        )
    lines.extend(["", "## 4. Head / Tail 抽样", ""])
    for check in report.get("checks", []):
        lines.extend(
            [
                f"### {check.get('title')}",
                "",
                "head:",
                "",
                "```text",
                str(check.get("head_text", "")),
                "```",
                "",
                "tail:",
                "",
                "```text",
                str(check.get("tail_text", "")),
                "```",
                "",
            ]
        )
    lines.extend(
        [
            "## 5. 审计结论",
            "",
            "| 裁决项 | 结论 |",
            "|---|---|",
            _markdown_table_row(["adata get_market()", diagnosis["raw_get_market_verdict"]]),
            _markdown_table_row(["adata list_market_current()", diagnosis["raw_list_market_current_verdict"]]),
            _markdown_table_row(["adata 指数实时接口", diagnosis["raw_index_realtime_verdict"]]),
            _markdown_table_row(["分层判断", diagnosis["layer_conclusion"]]),
            _markdown_table_row(["是否强行判 PASS", "否"]),
            _markdown_table_row(["是否接入 S0", "否"]),
            _markdown_table_row(["是否包含交易建议", "否"]),
            "",
            "## 6. 验收结果",
            "",
            "- `logs/adata_latest_raw_debug_report.json` 已使用 `ensure_ascii=False` 写入。",
            "- 每个接口均记录状态、异常摘要、shape、columns、head、tail、耗时和映射可行性。",
            "",
        ]
    )
    MD_REPORT_PATH.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    console_output: list[str] = []
    report: dict[str, Any] = {
        "created_at": _utc_now(),
        "python": {"executable": sys.executable, "version": sys.version},
        "platform": platform.platform(),
        "checks": [],
        "router_live_reference": _load_router_live_reference(),
    }

    _emit(console_output, "# adata latest raw debug")
    try:
        import adata  # type: ignore
    except Exception as exc:
        report["adata"] = {
            "status": "FAIL",
            "version": None,
            "file": None,
            "error": _exception_payload(exc),
        }
        _emit(console_output, f"adata import: FAIL ({type(exc).__name__}: {exc})")
    else:
        report["adata"] = {
            "status": "PASS",
            "version": getattr(adata, "__version__", None),
            "file": getattr(adata, "__file__", None),
        }
        _emit(console_output, f"adata.__version__: {report['adata']['version']}")
        _emit(console_output, f"adata.__file__: {report['adata']['file']}")
        market = adata.stock.market

        for code in TARGET_STOCK_CODES:
            time.sleep(1.0)
            params = {"stock_code": code, "k_type": 1, "start_date": GET_MARKET_START_DATE}
            report["checks"].append(
                _run_case(
                    title=f"get_market stock_code={code}",
                    api="adata.stock.market.get_market",
                    params=params,
                    call=lambda code=code: market.get_market(
                        stock_code=code,
                        k_type=1,
                        start_date=GET_MARKET_START_DATE,
                    ),
                    intended_feature="daily_kline",
                    console_output=console_output,
                    requested_code=code,
                )
            )

        if hasattr(market, "list_market_current"):
            time.sleep(1.0)
            report["checks"].append(
                _run_case(
                    title="list_market_current 000001/600519",
                    api="adata.stock.market.list_market_current",
                    params={"target_codes": list(TARGET_STOCK_CODES)},
                    call=lambda: _list_market_current_call(market, report),
                    intended_feature="realtime_quotes",
                    console_output=console_output,
                )
            )
        else:
            report["checks"].append(
                _skip_case(
                    "list_market_current",
                    "adata.stock.market.list_market_current",
                    "adata.stock.market.list_market_current not available",
                )
            )

        index_current_candidates = [
            name
            for name in dir(market)
            if "index" in name.lower() and ("current" in name.lower() or "spot" in name.lower())
        ]
        if hasattr(market, "list_market_index_current"):
            time.sleep(1.0)
            report["checks"].append(
                _run_case(
                    title="list_market_index_current",
                    api="adata.stock.market.index_realtime",
                    params={},
                    call=market.list_market_index_current,
                    intended_feature="realtime_quotes",
                    console_output=console_output,
                )
            )
        else:
            report["index_realtime_candidates"] = index_current_candidates
            report["checks"].append(
                _skip_case(
                    "adata index realtime",
                    "adata.stock.market.index_realtime",
                    "no supported adata index realtime API found; get_market_index is historical kline, not realtime",
                )
            )

    report["diagnosis"] = _build_diagnosis(report)
    _emit(console_output, "")
    _emit(console_output, f"json_report: {JSON_REPORT_PATH.relative_to(PROJECT_ROOT)}")
    _emit(console_output, f"markdown_report: {MD_REPORT_PATH.relative_to(PROJECT_ROOT)}")
    report["console_output"] = console_output

    JSON_REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    JSON_REPORT_PATH.write_text(
        json.dumps(report, ensure_ascii=False, indent=2, default=str),
        encoding="utf-8",
    )
    _write_markdown_report(report)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
