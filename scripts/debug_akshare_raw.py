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
JSON_REPORT_PATH = PROJECT_ROOT / "logs" / "akshare_raw_debug_report.json"
MD_REPORT_PATH = PROJECT_ROOT / "AKSHARE_RAW_DEBUG_REPORT.md"

HIST_SYMBOLS = ("000001", "600519")
HIST_ADJUSTS = ("", "qfq", "hfq")
HIST_START_DATE = "20240101"
HIST_END_DATE = "20241231"


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


def _run_case(
    *,
    title: str,
    api: str,
    params: dict[str, Any],
    call: Callable[[], Any],
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
            }
        )
        _emit(console_output, f"status: FAIL ({type(exc).__name__}: {exc})")
        _emit(console_output, f"duration_ms: {duration_ms}")
        if result["captured_stdout"]:
            _emit(console_output, "captured_stdout:")
            _emit(console_output, str(result["captured_stdout"]).rstrip())
        if result["captured_stderr"]:
            _emit(console_output, "captured_stderr:")
            _emit(console_output, str(result["captured_stderr"]).rstrip())
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
            }
        )
        _emit(console_output, f"status: FAIL (non_dataframe_return: {type(data).__name__})")
        _emit(console_output, f"duration_ms: {duration_ms}")
        _emit(console_output, f"returned_repr: {result['returned_repr']}")
        return result

    dataframe_payload = _dataframe_payload(data)
    status = "PASS" if not data.empty else "FAIL"
    reason = "non_empty_dataframe" if status == "PASS" else "empty_dataframe"
    result.update({"status": status, "reason": reason, **dataframe_payload})

    _emit(console_output, f"status: {status} ({reason})")
    _emit(console_output, f"duration_ms: {duration_ms}")
    _emit(console_output, f"shape: {tuple(dataframe_payload['shape'])}")
    _emit(console_output, f"columns: {json.dumps(dataframe_payload['columns'], ensure_ascii=False)}")
    _emit(console_output, "head:")
    _emit(console_output, str(dataframe_payload["head_text"]))
    _emit(console_output, "tail:")
    _emit(console_output, str(dataframe_payload["tail_text"]))
    if result["captured_stdout"]:
        _emit(console_output, "captured_stdout:")
        _emit(console_output, str(result["captured_stdout"]).rstrip())
    if result["captured_stderr"]:
        _emit(console_output, "captured_stderr:")
        _emit(console_output, str(result["captured_stderr"]).rstrip())
    return result


def _load_router_live_reference() -> dict[str, Any]:
    path = PROJECT_ROOT / "logs" / "smoke_test_report.json"
    if not path.exists():
        return {"available": False, "reason": "logs/smoke_test_report.json not found"}
    try:
        report = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        return {
            "available": False,
            "reason": f"{type(exc).__name__}: {exc}",
        }

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
        "akshare_daily_kline": find_result("daily_kline"),
        "akshare_trade_calendar": find_result("trade_calendar"),
    }


def _hist_verdict(checks: list[dict[str, Any]]) -> str:
    if not checks:
        return "FAIL"
    pass_count = sum(check.get("status") == "PASS" for check in checks)
    if pass_count == len(checks):
        return "PASS"
    if pass_count > 0:
        return "PARTIAL_PASS"
    return "FAIL"


def _single_verdict(checks: list[dict[str, Any]]) -> str:
    if checks and all(check.get("status") == "PASS" for check in checks):
        return "PASS"
    return "FAIL"


def _build_diagnosis(report: dict[str, Any]) -> dict[str, Any]:
    checks = report.get("checks", [])
    hist_checks = [check for check in checks if check.get("api") == "stock_zh_a_hist"]
    calendar_checks = [check for check in checks if check.get("api") == "tool_trade_date_hist_sina"]
    hist_pass_count = sum(check.get("status") == "PASS" for check in hist_checks)
    hist_fail_count = sum(check.get("status") == "FAIL" for check in hist_checks)
    calendar_pass_count = sum(check.get("status") == "PASS" for check in calendar_checks)
    hist_status = _hist_verdict(hist_checks)
    calendar_status = _single_verdict(calendar_checks)
    router_reference = report.get("router_live_reference", {})
    router_daily_status = (router_reference.get("akshare_daily_kline") or {}).get("status")

    if hist_status == "PASS" and router_daily_status == "FAIL":
        layer_conclusion = (
            "AKShare 原始 stock_zh_a_hist 全部 PASS，但 router live daily_kline FAIL；"
            "本轮证据指向 adapter / 字段映射 / 质量闸门 / smoke 参数差异问题，而不是原始接口整体不可用。"
        )
    elif hist_status == "FAIL":
        layer_conclusion = (
            "AKShare 原始 stock_zh_a_hist 全部 FAIL；本轮证据指向 AKShare 版本 / 网络 / 源站 / IP / 日期范围问题，"
            "不能把 router live daily_kline FAIL 直接归因于 adapter 或质量闸门。"
        )
    elif hist_status == "PARTIAL_PASS" and router_daily_status == "FAIL":
        layer_conclusion = (
            "AKShare 原始 stock_zh_a_hist 部分 PASS、部分 FAIL；router live daily_kline FAIL 需要按失败的 symbol/adjust/日期范围继续定位，"
            "不能强行判定原始接口完全可用。"
        )
    elif hist_status == "PASS":
        layer_conclusion = "AKShare 原始 stock_zh_a_hist 全部 PASS；未观察到 router daily_kline FAIL 对照，需结合最新 live smoke 再定层级。"
    else:
        layer_conclusion = "AKShare 原始 stock_zh_a_hist 未形成可放行结论。"

    return {
        "raw_stock_zh_a_hist_verdict": hist_status,
        "raw_stock_zh_a_hist_pass_count": hist_pass_count,
        "raw_stock_zh_a_hist_fail_count": hist_fail_count,
        "raw_stock_zh_a_hist_total": len(hist_checks),
        "raw_trade_calendar_verdict": calendar_status,
        "raw_trade_calendar_pass_count": calendar_pass_count,
        "raw_trade_calendar_total": len(calendar_checks),
        "router_live_akshare_daily_kline_status": router_daily_status,
        "layer_conclusion": layer_conclusion,
        "s0_realtime_default_restored": False,
        "trading_advice_included": False,
    }


def _markdown_table_row(values: list[object]) -> str:
    return "| " + " | ".join(str(value).replace("\n", "<br>") for value in values) + " |"


def _write_markdown_report(report: dict[str, Any]) -> None:
    diagnosis = report["diagnosis"]
    akshare_info = report.get("akshare", {})
    router_reference = report.get("router_live_reference", {})
    hist_checks = [check for check in report.get("checks", []) if check.get("api") == "stock_zh_a_hist"]
    calendar_checks = [
        check for check in report.get("checks", []) if check.get("api") == "tool_trade_date_hist_sina"
    ]

    lines = [
        "# AKSHARE_RAW_DEBUG_REPORT",
        "",
        f"生成时间：{report.get('created_at')}",
        "",
        "## 1. 调试目标",
        "",
        "本报告只排查 AKShare 原始接口，不修改 MarketRouter，不调整 S0，不恢复 AKShare 实时默认链路，不包含任何交易建议。",
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
        "## 3. stock_zh_a_hist 原始接口结果",
        "",
        "| symbol | adjust | status | shape | columns | reason | error |",
        "|---|---|---:|---|---|---|---|",
    ]

    for check in hist_checks:
        shape = tuple(check.get("shape", [])) if check.get("shape") is not None else "-"
        columns = ", ".join(check.get("columns", []) or [])
        error = check.get("error") or {}
        lines.append(
            _markdown_table_row(
                [
                    check.get("params", {}).get("symbol"),
                    check.get("params", {}).get("adjust") or "<none>",
                    check.get("status"),
                    shape,
                    columns,
                    check.get("reason"),
                    f"{error.get('error_type')}: {error.get('error_message')}" if error else "-",
                ]
            )
        )

    lines.extend(
        [
            "",
            "## 4. 交易日历原始接口结果",
            "",
            "| api | status | shape | columns | reason | error |",
            "|---|---:|---|---|---|---|",
        ]
    )
    for check in calendar_checks:
        shape = tuple(check.get("shape", [])) if check.get("shape") is not None else "-"
        columns = ", ".join(check.get("columns", []) or [])
        error = check.get("error") or {}
        lines.append(
            _markdown_table_row(
                [
                    check.get("api"),
                    check.get("status"),
                    shape,
                    columns,
                    check.get("reason"),
                    f"{error.get('error_type')}: {error.get('error_message')}" if error else "-",
                ]
            )
        )

    lines.extend(
        [
            "",
            "## 5. 与最新 router live smoke 对照",
            "",
            "| 项目 | 结果 |",
            "|---|---|",
            _markdown_table_row(["smoke report", router_reference.get("path")]),
            _markdown_table_row(["smoke created_at", router_reference.get("created_at")]),
            _markdown_table_row(["live_enabled", router_reference.get("live_enabled")]),
            _markdown_table_row(
                [
                    "AKShare router daily_kline",
                    (router_reference.get("akshare_daily_kline") or {}).get("status"),
                ]
            ),
            _markdown_table_row(
                [
                    "AKShare router daily_kline reason",
                    (router_reference.get("akshare_daily_kline") or {}).get("reason"),
                ]
            ),
            _markdown_table_row(
                [
                    "AKShare router trade_calendar",
                    (router_reference.get("akshare_trade_calendar") or {}).get("status"),
                ]
            ),
            "",
            "## 6. 审计结论",
            "",
            "| 裁决项 | 结论 |",
            "|---|---|",
            _markdown_table_row(
                [
                    "AKShare 原始 stock_zh_a_hist 是否可用",
                    f"{diagnosis['raw_stock_zh_a_hist_verdict']} ({diagnosis['raw_stock_zh_a_hist_pass_count']}/{diagnosis['raw_stock_zh_a_hist_total']} PASS)",
                ]
            ),
            _markdown_table_row(
                [
                    "AKShare 交易日历是否可用",
                    f"{diagnosis['raw_trade_calendar_verdict']} ({diagnosis['raw_trade_calendar_pass_count']}/{diagnosis['raw_trade_calendar_total']} PASS)",
                ]
            ),
            _markdown_table_row(["分层判断", diagnosis["layer_conclusion"]]),
            _markdown_table_row(["是否强行判 PASS", "否"]),
            _markdown_table_row(["是否恢复 AKShare 实时默认链路", "否"]),
            _markdown_table_row(["是否包含交易建议", "否"]),
            "",
            "## 7. 验收结果",
            "",
            "- `logs/akshare_raw_debug_report.json` 已使用 `ensure_ascii=False` 写入。",
            "- 单个 AKShare 原始接口失败不会中断后续接口测试，失败项记录 `FAIL` 与异常摘要。",
            "- 本报告由 `scripts/debug_akshare_raw.py` 生成；最终验收命令结果以本次任务最终回复为准。",
            "",
        ]
    )
    MD_REPORT_PATH.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    console_output: list[str] = []
    report: dict[str, Any] = {
        "created_at": _utc_now(),
        "python": {
            "executable": sys.executable,
            "version": sys.version,
        },
        "platform": platform.platform(),
        "checks": [],
        "router_live_reference": _load_router_live_reference(),
    }

    _emit(console_output, "# AKShare raw debug")
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

        for symbol in HIST_SYMBOLS:
            for adjust in HIST_ADJUSTS:
                params = {
                    "symbol": symbol,
                    "period": "daily",
                    "start_date": HIST_START_DATE,
                    "end_date": HIST_END_DATE,
                    "adjust": adjust,
                }
                title = f"stock_zh_a_hist symbol={symbol} adjust={adjust or '<none>'}"
                report["checks"].append(
                    _run_case(
                        title=title,
                        api="stock_zh_a_hist",
                        params=params,
                        call=lambda params=params: ak.stock_zh_a_hist(**params),
                        console_output=console_output,
                    )
                )

        report["checks"].append(
            _run_case(
                title="tool_trade_date_hist_sina",
                api="tool_trade_date_hist_sina",
                params={},
                call=ak.tool_trade_date_hist_sina,
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
