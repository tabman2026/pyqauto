from __future__ import annotations

import contextlib
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
JSON_REPORT_PATH = PROJECT_ROOT / "logs" / "akshare_latest_realtime_debug_report.json"
MD_REPORT_PATH = PROJECT_ROOT / "AKSHARE_LATEST_REALTIME_DEBUG_REPORT.md"

AKSHARE_INDEX_SYMBOLS = ("沪深重要指数", "上证系列指数", "深证系列指数")
TARGET_STOCK_CODES = ("000001", "600519")
TARGET_INDEX_CODES = ("000001", "399001")

REALTIME_REQUIRED_FIELDS = [
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

AKSHARE_REALTIME_MAPPING = {
    "代码": "code",
    "code": "code",
    "名称": "name",
    "name": "name",
    "最新价": "last_price",
    "last_price": "last_price",
    "price": "last_price",
    "最新": "last_price",
    "昨收": "pre_close",
    "pre_close": "pre_close",
    "previous_close": "pre_close",
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
    "change_pct": "pct_chg",
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


def _mapped_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    rename_map = {
        column: AKSHARE_REALTIME_MAPPING[str(column)]
        for column in df.columns
        if str(column) in AKSHARE_REALTIME_MAPPING
    }
    out = df.rename(columns=rename_map).copy()
    if "code" in out.columns:
        out["code"] = out["code"].map(_normalize_code_value)
    return out


def _zero_value_warnings(mapped: pd.DataFrame, rows_for_check: pd.DataFrame) -> list[str]:
    warnings: list[str] = []
    if rows_for_check.empty:
        return warnings
    for column in ["last_price", "pre_close", "open", "high", "low"]:
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
    if "code" in mapped.columns and mapped["code"].isna().any():
        warnings.append("invalid_code_format")
    return list(dict.fromkeys(warnings))


def _mapping_evaluation(
    df: pd.DataFrame,
    *,
    target_codes: tuple[str, ...] = (),
    require_all_target_codes: bool = False,
) -> dict[str, Any]:
    if not isinstance(df, pd.DataFrame) or df.empty:
        return {
            "contains_required_fields": False,
            "can_map": False,
            "missing_fields": REALTIME_REQUIRED_FIELDS,
            "mapped_columns": [],
            "target_codes": list(target_codes),
            "matched_target_codes": [],
            "value_warnings": ["empty_dataframe"],
        }

    mapped = _mapped_dataframe(df)
    missing = [field for field in REALTIME_REQUIRED_FIELDS if field not in mapped.columns]
    matched_codes: list[str] = []
    rows_for_check = mapped
    if target_codes and "code" in mapped.columns:
        target_set = set(target_codes)
        rows_for_check = mapped[mapped["code"].isin(target_set)].copy()
        matched_codes = sorted(code for code in target_codes if code in set(rows_for_check["code"].dropna()))
    value_warnings = _zero_value_warnings(mapped, rows_for_check)
    target_ok = True
    if require_all_target_codes:
        target_ok = len(matched_codes) == len(target_codes)
        if not target_ok:
            value_warnings.append("target_codes_missing")
    can_map = not missing and target_ok and not value_warnings
    return {
        "contains_required_fields": not missing,
        "can_map": can_map,
        "missing_fields": missing,
        "mapped_columns": [str(column) for column in mapped.columns],
        "target_codes": list(target_codes),
        "matched_target_codes": matched_codes,
        "value_warnings": list(dict.fromkeys(value_warnings)),
        "mapped_head": _json_records(mapped.head(5)),
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
            if item.get("source_name") == "akshare" and item.get("feature") == feature:
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
        "akshare_realtime_quotes": find_result("realtime_quotes"),
        "akshare_index_realtime": find_result("index_realtime"),
    }


def _run_case(
    *,
    title: str,
    api: str,
    params: dict[str, Any],
    call: Callable[[], Any],
    intended_feature: str,
    console_output: list[str],
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
                "realtime_quotes_mapping": _mapping_evaluation(pd.DataFrame()),
                "index_realtime_mapping": _mapping_evaluation(pd.DataFrame()),
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
                "realtime_quotes_mapping": _mapping_evaluation(pd.DataFrame()),
                "index_realtime_mapping": _mapping_evaluation(pd.DataFrame()),
            }
        )
        _emit(console_output, f"status: FAIL (non_dataframe_return: {type(data).__name__})")
        _emit(console_output, f"duration_ms: {duration_ms}")
        return result

    dataframe_payload = _dataframe_payload(data)
    realtime_mapping = _mapping_evaluation(
        data,
        target_codes=TARGET_STOCK_CODES,
        require_all_target_codes=api == "stock_zh_a_spot_em",
    )
    index_mapping = _mapping_evaluation(
        data,
        target_codes=TARGET_INDEX_CODES if params.get("symbol") == "沪深重要指数" else (),
        require_all_target_codes=params.get("symbol") == "沪深重要指数",
    )
    intended_mapping = realtime_mapping if intended_feature == "realtime_quotes" else index_mapping
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
            "realtime_quotes_mapping": realtime_mapping,
            "index_realtime_mapping": index_mapping,
        }
    )

    _emit(console_output, f"status: {status} ({reason})")
    _emit(console_output, f"duration_ms: {duration_ms}")
    _emit(console_output, f"shape: {tuple(dataframe_payload['shape'])}")
    _emit(console_output, f"columns: {json.dumps(dataframe_payload['columns'], ensure_ascii=False)}")
    _emit(console_output, f"can_map_realtime_quotes: {realtime_mapping['can_map']}")
    _emit(console_output, f"can_map_index_realtime: {index_mapping['can_map']}")
    _emit(console_output, "head:")
    _emit(console_output, str(dataframe_payload["head_text"]))
    _emit(console_output, "tail:")
    _emit(console_output, str(dataframe_payload["tail_text"]))
    return result


def _case_status(checks: list[dict[str, Any]], api: str) -> str:
    api_checks = [check for check in checks if check.get("api") == api]
    if not api_checks:
        return "SKIP"
    if all(check.get("status") == "PASS" for check in api_checks):
        return "PASS"
    if any(check.get("status") == "PASS" for check in api_checks):
        return "PARTIAL_PASS"
    return "FAIL"


def _build_diagnosis(report: dict[str, Any]) -> dict[str, Any]:
    checks = report.get("checks", [])
    spot_status = _case_status(checks, "stock_zh_a_spot_em")
    index_status = _case_status(checks, "stock_zh_index_spot_em")
    router_reference = report.get("router_live_reference", {})
    router_realtime_status = (router_reference.get("akshare_realtime_quotes") or {}).get("status")
    router_index_status = (router_reference.get("akshare_index_realtime") or {}).get("status")
    layer_findings: list[str] = []
    if spot_status == "PASS" and router_realtime_status == "FAIL":
        layer_findings.append(
            "AKShare stock_zh_a_spot_em 原始接口 PASS，但 router live realtime_quotes FAIL；"
            "证据指向 adapter / 字段映射 / 质量闸门问题。"
        )
    if index_status == "PASS" and router_index_status == "FAIL":
        layer_findings.append(
            "AKShare stock_zh_index_spot_em 原始接口 PASS，但 router live index_realtime FAIL；"
            "证据指向 adapter / 字段映射 / 质量闸门问题。"
        )
    if not layer_findings:
        layer_findings.append("需结合本轮修复后的 live smoke test 再确认 router 层状态。")
    return {
        "raw_stock_zh_a_spot_em_verdict": spot_status,
        "raw_stock_zh_index_spot_em_verdict": index_status,
        "router_live_akshare_realtime_quotes_status": router_realtime_status,
        "router_live_akshare_index_realtime_status": router_index_status,
        "layer_conclusion": " ".join(layer_findings),
        "trading_advice_included": False,
        "s0_connected": False,
    }


def _markdown_table_row(values: list[object]) -> str:
    return "| " + " | ".join(str(value).replace("\n", "<br>") for value in values) + " |"


def _write_markdown_report(report: dict[str, Any]) -> None:
    diagnosis = report["diagnosis"]
    akshare_info = report.get("akshare", {})
    lines = [
        "# AKSHARE_LATEST_REALTIME_DEBUG_REPORT",
        "",
        f"生成时间：{report.get('created_at')}",
        "",
        "## 1. 调试目标",
        "",
        "本报告按 AKShare 最新已安装版本直接调用实时原始接口，不修改 S0，不包含任何交易建议。",
        "",
        "## 2. 环境与版本",
        "",
        "| 项目 | 结果 |",
        "|---|---|",
        _markdown_table_row(["Python", report.get("python", {}).get("version")]),
        _markdown_table_row(["Python executable", f"`{report.get('python', {}).get('executable')}`"]),
        _markdown_table_row(["Platform", report.get("platform")]),
        _markdown_table_row(["akshare.__version__", akshare_info.get("version")]),
        _markdown_table_row(["akshare.__file__", f"`{akshare_info.get('file')}`"]),
        "",
        "## 3. 原始接口结果",
        "",
        "| api | params | status | shape | columns | realtime_quotes 映射 | index_realtime 映射 | reason | error |",
        "|---|---|---:|---|---|---:|---:|---|---|",
    ]
    for check in report.get("checks", []):
        shape = tuple(check.get("shape", [])) if check.get("shape") is not None else "-"
        columns = ", ".join(check.get("columns", []) or [])
        error = check.get("error") or {}
        realtime_mapping = check.get("realtime_quotes_mapping") or {}
        index_mapping = check.get("index_realtime_mapping") or {}
        lines.append(
            _markdown_table_row(
                [
                    check.get("api"),
                    json.dumps(check.get("params", {}), ensure_ascii=False),
                    check.get("status"),
                    shape,
                    columns,
                    realtime_mapping.get("can_map"),
                    index_mapping.get("can_map"),
                    check.get("reason"),
                    f"{error.get('error_type')}: {error.get('error_message')}" if error else "-",
                ]
            )
        )
    lines.extend(
        [
            "",
            "## 4. Head / Tail 抽样",
            "",
        ]
    )
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
            _markdown_table_row(["AKShare stock_zh_a_spot_em()", diagnosis["raw_stock_zh_a_spot_em_verdict"]]),
            _markdown_table_row(["AKShare stock_zh_index_spot_em()", diagnosis["raw_stock_zh_index_spot_em_verdict"]]),
            _markdown_table_row(["分层判断", diagnosis["layer_conclusion"]]),
            _markdown_table_row(["是否强行判 PASS", "否"]),
            _markdown_table_row(["是否接入 S0", "否"]),
            _markdown_table_row(["是否包含交易建议", "否"]),
            "",
            "## 6. 验收结果",
            "",
            "- `logs/akshare_latest_realtime_debug_report.json` 已使用 `ensure_ascii=False` 写入。",
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

    _emit(console_output, "# AKShare latest realtime raw debug")
    try:
        import akshare as ak  # type: ignore
    except Exception as exc:
        report["akshare"] = {
            "status": "FAIL",
            "version": None,
            "file": None,
            "error": _exception_payload(exc),
        }
        _emit(console_output, f"akshare import: FAIL ({type(exc).__name__}: {exc})")
    else:
        report["akshare"] = {
            "status": "PASS",
            "version": getattr(ak, "__version__", None),
            "file": getattr(ak, "__file__", None),
        }
        _emit(console_output, f"akshare.__version__: {report['akshare']['version']}")
        _emit(console_output, f"akshare.__file__: {report['akshare']['file']}")

        report["checks"].append(
            _run_case(
                title="stock_zh_a_spot_em",
                api="stock_zh_a_spot_em",
                params={},
                call=ak.stock_zh_a_spot_em,
                intended_feature="realtime_quotes",
                console_output=console_output,
            )
        )
        for symbol in AKSHARE_INDEX_SYMBOLS:
            time.sleep(1.0)
            report["checks"].append(
                _run_case(
                    title=f"stock_zh_index_spot_em symbol={symbol}",
                    api="stock_zh_index_spot_em",
                    params={"symbol": symbol},
                    call=lambda symbol=symbol: ak.stock_zh_index_spot_em(symbol=symbol),
                    intended_feature="index_realtime",
                    console_output=console_output,
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
