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
JSON_REPORT_PATH = PROJECT_ROOT / "logs" / "latest_doc_calling_report.json"
MD_REPORT_PATH = PROJECT_ROOT / "LATEST_DOC_CALLING_REPORT.md"

SLEEP_SECONDS = 2.5
TARGET_CODES = ("000001", "600519")
TARGET_INDEX_CODES = ("000001", "399001")

FULL_REALTIME_DATA_FIELDS = [
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

LITE_REALTIME_DATA_FIELDS = [
    "code",
    "name",
    "last_price",
    "volume",
    "amount",
    "pct_chg",
]

DAILY_KLINE_DATA_FIELDS = [
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

AKSHARE_DAILY_MAPPING = {
    "日期": "date",
    "date": "date",
    "股票代码": "code",
    "代码": "code",
    "code": "code",
    "开盘": "open",
    "open": "open",
    "最高": "high",
    "high": "high",
    "最低": "low",
    "low": "low",
    "收盘": "close",
    "close": "close",
    "昨收": "pre_close",
    "pre_close": "pre_close",
    "成交量": "volume",
    "volume": "volume",
    "成交额": "amount",
    "amount": "amount",
    "turnover": "turnover_rate",
    "涨跌幅": "pct_chg",
    "pct_chg": "pct_chg",
    "换手率": "turnover_rate",
    "turnover_rate": "turnover_rate",
}

AKSHARE_REALTIME_MAPPING = {
    "代码": "code",
    "code": "code",
    "名称": "name",
    "name": "name",
    "最新价": "last_price",
    "最新": "last_price",
    "last_price": "last_price",
    "price": "last_price",
    "昨收": "pre_close",
    "pre_close": "pre_close",
    "今开": "open",
    "开盘": "open",
    "open": "open",
    "最高": "high",
    "high": "high",
    "最低": "low",
    "low": "low",
    "成交量": "volume",
    "volume": "volume",
    "成交额": "amount",
    "amount": "amount",
    "涨跌幅": "pct_chg",
    "pct_chg": "pct_chg",
}

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
    "turnover_ratio": "turnover_rate",
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
    "current": "last_price",
    "now": "last_price",
    "current_price": "last_price",
    "latest_price": "last_price",
    "last_price": "last_price",
    "最新价": "last_price",
    "现价": "last_price",
    "close": "last_price",
    "pre_close": "pre_close",
    "昨收": "pre_close",
    "open": "open",
    "今开": "open",
    "开盘": "open",
    "high": "high",
    "最高": "high",
    "low": "low",
    "最低": "low",
    "volume": "volume",
    "成交量": "volume",
    "amount": "amount",
    "成交额": "amount",
    "change_pct": "pct_chg",
    "pct_chg": "pct_chg",
    "涨跌幅": "pct_chg",
}


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _emit(console_output: list[str], text: str = "") -> None:
    print(text)
    console_output.append(text)


def _json_records(df: pd.DataFrame) -> list[dict[str, Any]]:
    if df.empty:
        return []
    return json.loads(df.to_json(orient="records", force_ascii=False, date_format="iso", default_handler=str))


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
    return df.rename(columns={column: mapping[str(column)] for column in df.columns if str(column) in mapping}).copy()


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


def _value_warnings(rows: pd.DataFrame, price_columns: list[str]) -> list[str]:
    warnings: list[str] = []
    if rows.empty:
        return warnings
    for column in price_columns:
        if column not in rows.columns:
            continue
        numeric = pd.to_numeric(rows[column], errors="coerce")
        if numeric.isna().any():
            warnings.append(f"field_type_error:{column}")
        if (numeric == 0).any():
            warnings.append(f"zero_price:{column}")
    if "amount" in rows.columns:
        amount = pd.to_numeric(rows["amount"], errors="coerce")
        if amount.isna().any():
            warnings.append("field_type_error:amount")
        if (amount == 0).any():
            warnings.append("zero_amount")
    return list(dict.fromkeys(warnings))


def _daily_mapping(df: pd.DataFrame, mapping: dict[str, str], requested_code: str | None = None) -> dict[str, Any]:
    if not isinstance(df, pd.DataFrame) or df.empty:
        return {
            "can_map": False,
            "missing_fields": DAILY_KLINE_DATA_FIELDS,
            "mapped_columns": [],
            "derived_fields": [],
            "value_warnings": ["empty_dataframe"],
        }
    out = _rename_columns(df, mapping)
    out = _derive_date_time(out)
    derived_fields: list[str] = []
    if "code" in out.columns:
        out["code"] = out["code"].map(_normalize_code_value)
    elif requested_code is not None:
        out["code"] = requested_code
        derived_fields.append("code_from_request")
    if "pre_close" not in out.columns and {"close", "pct_chg"}.issubset(out.columns):
        out["pre_close"] = _derive_pre_close_from_pct(out["close"], out["pct_chg"])
        derived_fields.append("pre_close_from_pct_chg")
    elif "pre_close" not in out.columns and "close" in out.columns:
        out["pre_close"] = pd.to_numeric(out["close"], errors="coerce").shift(1)
        derived_fields.append("pre_close_from_previous_close")
    if "pct_chg" not in out.columns and {"close", "pre_close"}.issubset(out.columns):
        pre_close = pd.to_numeric(out["pre_close"], errors="coerce").replace(0, pd.NA)
        close = pd.to_numeric(out["close"], errors="coerce")
        out["pct_chg"] = (close / pre_close - 1) * 100
        derived_fields.append("pct_chg_from_close_pre_close")
    missing = [field for field in DAILY_KLINE_DATA_FIELDS if field not in out.columns]
    rows_for_check = out
    if requested_code and "code" in out.columns:
        rows_for_check = out[out["code"] == requested_code].copy()
    warnings = _value_warnings(rows_for_check, ["open", "high", "low", "close", "pre_close"])
    if requested_code and rows_for_check.empty:
        warnings.append("target_code_missing")
    return {
        "can_map": not missing and not warnings,
        "missing_fields": missing,
        "mapped_columns": [str(column) for column in out.columns],
        "derived_fields": derived_fields,
        "value_warnings": list(dict.fromkeys(warnings)),
        "mapped_head": _json_records(out.head(5)),
    }


def _realtime_mapping(
    df: pd.DataFrame,
    mapping: dict[str, str],
    required_fields: list[str],
    price_fields: list[str],
    target_codes: tuple[str, ...] = (),
    require_all_targets: bool = False,
) -> dict[str, Any]:
    if not isinstance(df, pd.DataFrame) or df.empty:
        return {
            "can_map": False,
            "missing_fields": required_fields,
            "mapped_columns": [],
            "matched_target_codes": [],
            "value_warnings": ["empty_dataframe"],
        }
    out = _rename_columns(df, mapping)
    if "code" in out.columns:
        out["code"] = out["code"].map(_normalize_code_value)
    missing = [field for field in required_fields if field not in out.columns]
    rows_for_check = out
    matched_codes: list[str] = []
    if target_codes and "code" in out.columns:
        target_set = set(target_codes)
        rows_for_check = out[out["code"].isin(target_set)].copy()
        matched_codes = sorted(code for code in target_codes if code in set(rows_for_check["code"].dropna()))
    warnings = _value_warnings(rows_for_check, price_fields)
    if require_all_targets and len(matched_codes) != len(target_codes):
        warnings.append("target_codes_missing")
    return {
        "can_map": not missing and not warnings,
        "missing_fields": missing,
        "mapped_columns": [str(column) for column in out.columns],
        "matched_target_codes": matched_codes,
        "value_warnings": list(dict.fromkeys(warnings)),
        "mapped_head": _json_records(out.head(5)),
    }


def _empty_mapping() -> dict[str, Any]:
    return {"can_map": False, "missing_fields": [], "mapped_columns": [], "value_warnings": ["not_evaluated"]}


def _sleep_before_case(report: dict[str, Any]) -> None:
    if report.get("case_count", 0):
        time.sleep(SLEEP_SECONDS)
    report["case_count"] = int(report.get("case_count", 0)) + 1


def _run_case(
    report: dict[str, Any],
    *,
    provider: str,
    title: str,
    api: str,
    params: dict[str, Any],
    call: Callable[[], Any],
    intended_feature: str,
    daily_mapping: dict[str, str] | None = None,
    realtime_mapping: dict[str, str] | None = None,
    requested_code: str | None = None,
    target_codes: tuple[str, ...] = (),
    require_all_targets: bool = False,
    console_output: list[str],
) -> dict[str, Any]:
    _sleep_before_case(report)
    _emit(console_output, "")
    _emit(console_output, f"## {title}")
    _emit(console_output, f"api: {api}")
    _emit(console_output, f"params: {json.dumps(params, ensure_ascii=False)}")

    stdout_buffer = io.StringIO()
    stderr_buffer = io.StringIO()
    started_at = time.perf_counter()
    result: dict[str, Any] = {
        "provider": provider,
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
                "shape": None,
                "columns": [],
                "head": [],
                "tail": [],
                "daily_kline_mapping": _daily_mapping(pd.DataFrame(), daily_mapping or {}),
                "full_realtime_quotes_mapping": _realtime_mapping(
                    pd.DataFrame(),
                    realtime_mapping or {},
                    FULL_REALTIME_DATA_FIELDS,
                    ["last_price", "pre_close", "open", "high", "low"],
                ),
                "lite_realtime_quotes_mapping": _realtime_mapping(
                    pd.DataFrame(),
                    realtime_mapping or {},
                    LITE_REALTIME_DATA_FIELDS,
                    ["last_price"],
                ),
            }
        )
        _emit(console_output, f"status: FAIL ({type(exc).__name__}: {exc})")
        _emit(console_output, f"duration_ms: {duration_ms}")
        return result

    duration_ms = round((time.perf_counter() - started_at) * 1000, 3)
    result.update({"duration_ms": duration_ms, "captured_stdout": stdout_buffer.getvalue(), "captured_stderr": stderr_buffer.getvalue()})
    if not isinstance(data, pd.DataFrame):
        result.update(
            {
                "status": "FAIL",
                "reason": "non_dataframe_return",
                "returned_type": type(data).__name__,
                "returned_repr": repr(data)[:2000],
                "shape": None,
                "columns": [],
                "head": [],
                "tail": [],
                "daily_kline_mapping": _daily_mapping(pd.DataFrame(), daily_mapping or {}),
                "full_realtime_quotes_mapping": _empty_mapping(),
                "lite_realtime_quotes_mapping": _empty_mapping(),
            }
        )
        _emit(console_output, f"status: FAIL (non_dataframe_return: {type(data).__name__})")
        _emit(console_output, f"duration_ms: {duration_ms}")
        return result

    payload = _dataframe_payload(data)
    daily_eval = _daily_mapping(data, daily_mapping or {}, requested_code=requested_code)
    full_eval = _realtime_mapping(
        data,
        realtime_mapping or {},
        FULL_REALTIME_DATA_FIELDS,
        ["last_price", "pre_close", "open", "high", "low"],
        target_codes=target_codes,
        require_all_targets=require_all_targets,
    )
    lite_eval = _realtime_mapping(
        data,
        realtime_mapping or {},
        LITE_REALTIME_DATA_FIELDS,
        ["last_price"],
        target_codes=target_codes,
        require_all_targets=require_all_targets,
    )
    if intended_feature == "daily_kline":
        intended_ok = bool(daily_eval["can_map"])
    elif intended_feature == "full_realtime_quotes":
        intended_ok = bool(full_eval["can_map"])
    elif intended_feature == "lite_realtime_quotes":
        intended_ok = bool(lite_eval["can_map"])
    else:
        intended_ok = bool(full_eval["can_map"] or lite_eval["can_map"])
    if data.empty:
        status = "FAIL"
        reason = "empty_dataframe"
    elif intended_ok:
        status = "PASS"
        reason = "non_empty_dataframe_and_required_mapping_ok"
    else:
        status = "FAIL"
        reason = "required_mapping_failed"

    result.update(
        {
            "status": status,
            "reason": reason,
            **payload,
            "daily_kline_mapping": daily_eval,
            "full_realtime_quotes_mapping": full_eval,
            "lite_realtime_quotes_mapping": lite_eval,
        }
    )
    _emit(console_output, f"status: {status} ({reason})")
    _emit(console_output, f"duration_ms: {duration_ms}")
    _emit(console_output, f"shape: {tuple(payload['shape'])}")
    _emit(console_output, f"columns: {json.dumps(payload['columns'], ensure_ascii=False)}")
    _emit(console_output, f"can_map_full_realtime_quotes: {full_eval['can_map']}")
    _emit(console_output, f"can_map_lite_realtime_quotes: {lite_eval['can_map']}")
    _emit(console_output, f"can_map_daily_kline: {daily_eval['can_map']}")
    _emit(console_output, "head:")
    _emit(console_output, str(payload["head_text"]))
    _emit(console_output, "tail:")
    _emit(console_output, str(payload["tail_text"]))
    return result


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


def _write_markdown_report(report: dict[str, Any]) -> None:
    lines = [
        "# LATEST_DOC_CALLING_REPORT",
        "",
        f"生成时间：{report.get('created_at')}",
        "",
        "## 1. 调试范围",
        "",
        "本报告按最新官方文档示例重测 AKShare 与 adata 原始接口。脚本逐项调用、单项失败不中断、请求间 sleep 2.5 秒，不接入 S0，不包含任何交易建议。",
        "",
        "## 2. 文档核对",
        "",
        "- AKShare：`stock_zh_a_hist` 使用 6 位代码；`stock_zh_a_daily` 使用 `sh/sz` 前缀；`stock_zh_index_spot_em` 使用文档枚举 symbol；`stock_zh_index_spot_sina()` 无 symbol 参数。",
        "- adata：`get_market(stock_code=\"000001\", k_type=1, start_date=\"2024-01-01\")`；`list_market_current()` 先无参全量调用，再本地筛选目标代码。",
        "",
        "## 3. 环境与签名",
        "",
        "| 项目 | 结果 |",
        "|---|---|",
        f"| Python | {report.get('python', {}).get('version')} |",
        f"| Python executable | `{report.get('python', {}).get('executable')}` |",
        f"| Platform | {report.get('platform')} |",
        f"| akshare version | {report.get('akshare', {}).get('version')} |",
        f"| adata version | {report.get('adata', {}).get('version')} |",
        f"| adata get_market signature | `{report.get('adata_signatures', {}).get('get_market')}` |",
        f"| adata list_market_current signature | `{report.get('adata_signatures', {}).get('list_market_current')}` |",
        "",
        "## 4. 原始接口结果",
        "",
        "| provider | api | params | status | shape | columns | full | lite | daily | reason | error |",
        "|---|---|---|---:|---|---|---:|---:|---:|---|---|",
    ]
    for check in report.get("checks", []):
        shape = tuple(check.get("shape", [])) if check.get("shape") is not None else "-"
        columns = ", ".join(check.get("columns", []) or [])
        error = check.get("error") or {}
        lines.append(
            "| "
            + " | ".join(
                [
                    str(check.get("provider")),
                    str(check.get("api")),
                    json.dumps(check.get("params", {}), ensure_ascii=False),
                    str(check.get("status")),
                    str(shape),
                    columns,
                    str((check.get("full_realtime_quotes_mapping") or {}).get("can_map")),
                    str((check.get("lite_realtime_quotes_mapping") or {}).get("can_map")),
                    str((check.get("daily_kline_mapping") or {}).get("can_map")),
                    str(check.get("reason")),
                    f"{error.get('error_type')}: {error.get('error_message')}" if error else "-",
                ]
            )
            + " |"
        )
    lines.extend(["", "## 5. Head / Tail 抽样", ""])
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
    diagnosis = report.get("diagnosis", {})
    lines.extend(
        [
            "## 6. 审计结论",
            "",
            "| 裁决项 | 结论 |",
            "|---|---|",
            f"| AKShare hist | {diagnosis.get('akshare_hist')} |",
            f"| AKShare daily 备用接口 | {diagnosis.get('akshare_daily_backup')} |",
            f"| AKShare spot 全市场 | {diagnosis.get('akshare_spot_all')} |",
            f"| AKShare spot 分市场 | {diagnosis.get('akshare_spot_by_market')} |",
            f"| AKShare 指数东财 | {diagnosis.get('akshare_index_em')} |",
            f"| AKShare 指数新浪 | {diagnosis.get('akshare_index_sina')} |",
            f"| adata get_market | {diagnosis.get('adata_get_market')} |",
            f"| adata list_market_current 无参 | {diagnosis.get('adata_list_market_current')} |",
            f"| adata list_market_current code_list 签名确认 | {diagnosis.get('adata_list_market_current_code_list')} |",
            f"| adata 实时 full | {diagnosis.get('adata_realtime_full')} |",
            f"| adata 实时 lite | {diagnosis.get('adata_realtime_lite')} |",
            "| 是否强行判 PASS | 否 |",
            "| 是否接入 S0 | 否 |",
            "| 是否包含交易建议 | 否 |",
            "",
            "## 7. 验收结果",
            "",
            "- `logs/latest_doc_calling_report.json` 已使用 `ensure_ascii=False` 写入。",
            "- 每个接口均记录 PASS/FAIL/SKIP、异常摘要、shape、columns、head、tail、耗时和 full/lite/daily 映射可行性。",
            "",
        ]
    )
    MD_REPORT_PATH.write_text("\n".join(lines), encoding="utf-8")


def _build_diagnosis(report: dict[str, Any]) -> dict[str, Any]:
    checks = report.get("checks", [])
    adata_realtime = [
        check
        for check in checks
        if check.get("api")
        in {"adata.stock.market.list_market_current", "adata.stock.market.list_market_current_code_list"}
    ]
    adata_full = "SKIP"
    adata_lite = "SKIP"
    if adata_realtime:
        adata_full = "PASS" if any((check.get("full_realtime_quotes_mapping") or {}).get("can_map") for check in adata_realtime) else "FAIL"
        adata_lite = "PASS" if any((check.get("lite_realtime_quotes_mapping") or {}).get("can_map") for check in adata_realtime) else "FAIL"
    return {
        "akshare_hist": _case_status(checks, "ak.stock_zh_a_hist"),
        "akshare_daily_backup": _case_status(checks, "ak.stock_zh_a_daily"),
        "akshare_spot_all": _case_status(checks, "ak.stock_zh_a_spot_em"),
        "akshare_spot_by_market": _case_status(checks, "ak.stock_market_spot_em"),
        "akshare_index_em": _case_status(checks, "ak.stock_zh_index_spot_em"),
        "akshare_index_sina": _case_status(checks, "ak.stock_zh_index_spot_sina"),
        "adata_get_market": _case_status(checks, "adata.stock.market.get_market"),
        "adata_list_market_current": _case_status(checks, "adata.stock.market.list_market_current"),
        "adata_list_market_current_code_list": _case_status(
            checks,
            "adata.stock.market.list_market_current_code_list",
        ),
        "adata_realtime_full": adata_full,
        "adata_realtime_lite": adata_lite,
        "trading_advice_included": False,
        "s0_connected": False,
    }


def _append_import_failure(report: dict[str, Any], provider: str, exc: BaseException) -> None:
    report["checks"].append(
        {
            "provider": provider,
            "title": f"{provider} import",
            "api": f"{provider} import",
            "params": {},
            "intended_feature": "import",
            "status": "FAIL",
            "reason": "import_failed",
            "duration_ms": 0.0,
            "error": _exception_payload(exc),
            "shape": None,
            "columns": [],
            "head": [],
            "tail": [],
            "daily_kline_mapping": _empty_mapping(),
            "full_realtime_quotes_mapping": _empty_mapping(),
            "lite_realtime_quotes_mapping": _empty_mapping(),
        }
    )


def main() -> int:
    console_output: list[str] = []
    report: dict[str, Any] = {
        "created_at": _utc_now(),
        "python": {"executable": sys.executable, "version": sys.version},
        "platform": platform.platform(),
        "checks": [],
        "case_count": 0,
        "sleep_seconds_between_requests": SLEEP_SECONDS,
    }

    _emit(console_output, "# latest doc calling debug")
    try:
        import akshare as ak  # type: ignore
    except Exception as exc:
        report["akshare"] = {"status": "FAIL", "version": None, "file": None, "error": _exception_payload(exc)}
        _append_import_failure(report, "akshare", exc)
        _emit(console_output, f"akshare import: FAIL ({type(exc).__name__}: {exc})")
    else:
        report["akshare"] = {"status": "PASS", "version": getattr(ak, "__version__", None), "file": getattr(ak, "__file__", None)}
        _emit(console_output, f"akshare.__version__: {report['akshare']['version']}")
        for code in TARGET_CODES:
            report["checks"].append(
                _run_case(
                    report,
                    provider="akshare",
                    title=f"stock_zh_a_hist symbol={code}",
                    api="ak.stock_zh_a_hist",
                    params={"symbol": code, "period": "daily", "start_date": "20240101", "end_date": "20241231", "adjust": ""},
                    call=lambda code=code: ak.stock_zh_a_hist(
                        symbol=code,
                        period="daily",
                        start_date="20240101",
                        end_date="20241231",
                        adjust="",
                    ),
                    intended_feature="daily_kline",
                    daily_mapping=AKSHARE_DAILY_MAPPING,
                    requested_code=code,
                    console_output=console_output,
                )
            )
        for code, symbol in (("000001", "sz000001"), ("600519", "sh600519")):
            report["checks"].append(
                _run_case(
                    report,
                    provider="akshare",
                    title=f"stock_zh_a_daily symbol={symbol}",
                    api="ak.stock_zh_a_daily",
                    params={"symbol": symbol, "start_date": "20240101", "end_date": "20241231", "adjust": ""},
                    call=lambda symbol=symbol: ak.stock_zh_a_daily(
                        symbol=symbol,
                        start_date="20240101",
                        end_date="20241231",
                        adjust="",
                    ),
                    intended_feature="daily_kline",
                    daily_mapping=AKSHARE_DAILY_MAPPING,
                    requested_code=code,
                    console_output=console_output,
                )
            )
        report["checks"].append(
            _run_case(
                report,
                provider="akshare",
                title="stock_zh_a_spot_em",
                api="ak.stock_zh_a_spot_em",
                params={},
                call=ak.stock_zh_a_spot_em,
                intended_feature="full_realtime_quotes",
                realtime_mapping=AKSHARE_REALTIME_MAPPING,
                target_codes=TARGET_CODES,
                require_all_targets=True,
                console_output=console_output,
            )
        )
        for title, func in (
            ("stock_sh_a_spot_em", ak.stock_sh_a_spot_em),
            ("stock_sz_a_spot_em", ak.stock_sz_a_spot_em),
            ("stock_bj_a_spot_em", ak.stock_bj_a_spot_em),
        ):
            report["checks"].append(
                _run_case(
                    report,
                    provider="akshare",
                    title=title,
                    api="ak.stock_market_spot_em",
                    params={"function": title},
                    call=func,
                    intended_feature="full_realtime_quotes",
                    realtime_mapping=AKSHARE_REALTIME_MAPPING,
                    console_output=console_output,
                )
            )
        for symbol in ("沪深重要指数", "上证系列指数", "深证系列指数"):
            report["checks"].append(
                _run_case(
                    report,
                    provider="akshare",
                    title=f"stock_zh_index_spot_em symbol={symbol}",
                    api="ak.stock_zh_index_spot_em",
                    params={"symbol": symbol},
                    call=lambda symbol=symbol: ak.stock_zh_index_spot_em(symbol=symbol),
                    intended_feature="full_realtime_quotes",
                    realtime_mapping=AKSHARE_REALTIME_MAPPING,
                    target_codes=TARGET_INDEX_CODES if symbol == "沪深重要指数" else (),
                    console_output=console_output,
                )
            )
        report["checks"].append(
            _run_case(
                report,
                provider="akshare",
                title="stock_zh_index_spot_sina",
                api="ak.stock_zh_index_spot_sina",
                params={},
                call=ak.stock_zh_index_spot_sina,
                intended_feature="full_realtime_quotes",
                realtime_mapping=AKSHARE_REALTIME_MAPPING,
                target_codes=TARGET_INDEX_CODES,
                console_output=console_output,
            )
        )

    try:
        import adata  # type: ignore
    except Exception as exc:
        report["adata"] = {"status": "FAIL", "version": None, "file": None, "error": _exception_payload(exc)}
        _append_import_failure(report, "adata", exc)
        _emit(console_output, f"adata import: FAIL ({type(exc).__name__}: {exc})")
    else:
        market = adata.stock.market
        report["adata"] = {"status": "PASS", "version": getattr(adata, "__version__", None), "file": getattr(adata, "__file__", None)}
        report["adata_signatures"] = {
            "get_market": str(inspect.signature(market.get_market)) if hasattr(market, "get_market") else None,
            "list_market_current": str(inspect.signature(market.list_market_current)) if hasattr(market, "list_market_current") else None,
        }
        _emit(console_output, f"adata.__version__: {report['adata']['version']}")
        _emit(console_output, f"adata get_market signature: {report['adata_signatures']['get_market']}")
        _emit(console_output, f"adata list_market_current signature: {report['adata_signatures']['list_market_current']}")
        for code in TARGET_CODES:
            report["checks"].append(
                _run_case(
                    report,
                    provider="adata",
                    title=f"get_market stock_code={code}",
                    api="adata.stock.market.get_market",
                    params={"stock_code": code, "k_type": 1, "start_date": "2024-01-01"},
                    call=lambda code=code: market.get_market(stock_code=code, k_type=1, start_date="2024-01-01"),
                    intended_feature="daily_kline",
                    daily_mapping=ADATA_DAILY_MAPPING,
                    requested_code=code,
                    console_output=console_output,
                )
            )
        if hasattr(market, "list_market_current"):
            report["checks"].append(
                _run_case(
                    report,
                    provider="adata",
                    title="list_market_current no args",
                    api="adata.stock.market.list_market_current",
                    params={},
                    call=market.list_market_current,
                    intended_feature="lite_realtime_quotes",
                    realtime_mapping=ADATA_REALTIME_MAPPING,
                    target_codes=TARGET_CODES,
                    console_output=console_output,
                )
            )
            signature = inspect.signature(market.list_market_current)
            if "code_list" in signature.parameters:
                report["checks"].append(
                    _run_case(
                        report,
                        provider="adata",
                        title="list_market_current code_list signature-confirmed",
                        api="adata.stock.market.list_market_current_code_list",
                        params={"code_list": list(TARGET_CODES)},
                        call=lambda: market.list_market_current(code_list=list(TARGET_CODES)),
                        intended_feature="lite_realtime_quotes",
                        realtime_mapping=ADATA_REALTIME_MAPPING,
                        target_codes=TARGET_CODES,
                        require_all_targets=True,
                        console_output=console_output,
                    )
                )

    report["diagnosis"] = _build_diagnosis(report)
    report["console_output"] = console_output
    JSON_REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    JSON_REPORT_PATH.write_text(json.dumps(report, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    _write_markdown_report(report)
    _emit(console_output, "")
    _emit(console_output, f"json_report: {JSON_REPORT_PATH.relative_to(PROJECT_ROOT)}")
    _emit(console_output, f"markdown_report: {MD_REPORT_PATH.relative_to(PROJECT_ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
