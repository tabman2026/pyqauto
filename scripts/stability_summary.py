from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

LOGS_DIR = PROJECT_ROOT / "logs"
SUMMARY_JSON_PATH = LOGS_DIR / "stability_5day_summary.json"
SUMMARY_MD_PATH = PROJECT_ROOT / "STABILITY_5DAY_SUMMARY.md"
REQUIRED_DAYS = 5


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _load_daily_reports() -> list[dict[str, Any]]:
    reports: list[dict[str, Any]] = []
    for path in sorted(LOGS_DIR.glob("stability_daily_*.json")):
        try:
            report = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            reports.append(
                {
                    "observation_date": path.stem.replace("stability_daily_", ""),
                    "source_path": str(path),
                    "daily_acceptance": {"status": "FAIL"},
                    "load_error": f"{type(exc).__name__}: {exc}",
                }
            )
            continue
        report["source_path"] = str(path)
        reports.append(report)
    by_date: dict[str, dict[str, Any]] = {}
    for report in reports:
        date_key = str(report.get("observation_date") or "")
        if date_key:
            by_date[date_key] = report
    return [by_date[key] for key in sorted(by_date)]


def _safe_get(report: dict[str, Any], *keys: str) -> Any:
    value: Any = report
    for key in keys:
        if not isinstance(value, dict):
            return None
        value = value.get(key)
    return value


def _daily_row(report: dict[str, Any]) -> dict[str, Any]:
    sections = report.get("source_sections") or {}
    gate = _safe_get(report, "official_live_smoke", "gate_results") or {}
    server_pool = report.get("pytdx_server_pool") or {}
    consistency = report.get("source_consistency") or {}
    audit_delta = _safe_get(report, "audit_log", "delta") or {}
    akshare = sections.get("akshare_post_close") or {}
    baostock = sections.get("baostock_backup") or {}
    easy = sections.get("easyquotation_fallback") or {}
    adata = sections.get("adata_lite") or {}
    acceptance = report.get("daily_acceptance") or {}
    forbidden = report.get("forbidden_output_audit") or {}
    trade_day = report.get("trade_day_status") or {}
    trigger = report.get("trigger_context") or {}
    return {
        "observation_date": report.get("observation_date"),
        "source_path": report.get("source_path"),
        "mode": report.get("mode"),
        "scheduled_task_triggered": trigger.get("scheduled_task_triggered"),
        "is_trading_day": trade_day.get("is_trading_day"),
        "counted_in_5day": bool(report.get("counted_in_5day")),
        "daily_acceptance": acceptance.get("status"),
        "overall_live_gate": gate.get("overall_live_gate"),
        "pytdx_available_server_count": server_pool.get("available_server_count"),
        "pytdx_server_pool_status": server_pool.get("server_pool_status"),
        "pytdx_primary_server": server_pool.get("primary_server"),
        "pytdx_hot_backup_server": server_pool.get("hot_backup_server"),
        "single_server_warning": server_pool.get("single_server_warning"),
        "easyquotation_fallback_ready": easy.get("fallback_ready"),
        "akshare_daily_status": _safe_get(akshare, "daily_kline", "status"),
        "akshare_calendar_status": _safe_get(akshare, "trade_calendar", "status"),
        "baostock_daily_status": _safe_get(baostock, "daily_kline", "status"),
        "baostock_calendar_status": _safe_get(baostock, "trade_calendar", "status"),
        "source_consistency_status": consistency.get("overall_status"),
        "source_consistency_has_fail": consistency.get("has_fail"),
        "adata_strictly_isolated_from_full": adata.get("strictly_isolated_from_full"),
        "audit_jsonl_written": audit_delta.get("jsonl_written"),
        "audit_sqlite_written": audit_delta.get("sqlite_written"),
        "audit_fallback_trace_rows_added": audit_delta.get("fallback_trace_rows_added"),
        "audit_health_score_rows_added": audit_delta.get("health_score_rows_added"),
        "forbidden_output_any": any(bool(value) for value in forbidden.values()),
    }


def _row_passes(row: dict[str, Any]) -> tuple[bool, list[str]]:
    failures: list[str] = []
    if not row.get("counted_in_5day"):
        failures.append("未计入 5 日观察")
    if row.get("daily_acceptance") != "PASS":
        failures.append("daily_acceptance 非 PASS")
    if row.get("overall_live_gate") != "PASS":
        failures.append("overall_live_gate 非 PASS")
    if int(row.get("pytdx_available_server_count") or 0) < 1:
        failures.append("pytdx 可用服务器少于 1 个")
    if not row.get("easyquotation_fallback_ready"):
        failures.append("easyquotation fallback 不可用")
    if row.get("akshare_daily_status") != "PASS" and row.get("baostock_daily_status") != "PASS":
        failures.append("AKShare 与 Baostock daily_kline 同时不可用")
    if row.get("akshare_calendar_status") != "PASS" or row.get("baostock_calendar_status") != "PASS":
        failures.append("trade_calendar 双源未同时可用")
    if row.get("source_consistency_has_fail"):
        failures.append("source consistency 有 FAIL")
    if not row.get("adata_strictly_isolated_from_full"):
        failures.append("adata lite 边界失败")
    if not row.get("audit_jsonl_written") or not row.get("audit_sqlite_written"):
        failures.append("审计日志未完整写入")
    if int(row.get("audit_fallback_trace_rows_added") or 0) <= 0:
        failures.append("fallback trace 未写入")
    if int(row.get("audit_health_score_rows_added") or 0) <= 0:
        failures.append("health score 未更新")
    if row.get("forbidden_output_any"):
        failures.append("出现禁止输出或禁止接入项")
    return not failures, failures


def _build_summary(daily_reports: list[dict[str, Any]]) -> dict[str, Any]:
    rows = [_daily_row(report) for report in daily_reports]
    counted_rows = [row for row in rows if row.get("counted_in_5day")]
    skipped_rows = [row for row in rows if not row.get("counted_in_5day")]
    last_rows = counted_rows[-REQUIRED_DAYS:]
    row_results = []
    for row in last_rows:
        passed, failures = _row_passes(row)
        row_results.append({**row, "passes_5day_rule": passed, "failures": failures})

    observed_days = len(last_rows)
    enough_days = observed_days >= REQUIRED_DAYS
    all_pass = enough_days and all(item["passes_5day_rule"] for item in row_results)
    all_single_server = enough_days and all(
        int(item.get("pytdx_available_server_count") or 0) == 1 for item in row_results
    )
    single_server_warning_preserved = not all_single_server or all(
        bool(item.get("single_server_warning")) for item in row_results
    )
    if not enough_days:
        status = "IN_PROGRESS"
        decision = "观察期未满 5 个交易日报告，不能形成 5 日通过结论。"
    elif all_pass and single_server_warning_preserved:
        status = "PASS"
        decision = "连续 5 个观察日报告满足任务014A规则，可作为后续 S0 只读沙盒稳定性基础。"
    else:
        status = "FAIL"
        decision = "最近 5 个观察日报告存在阻断项，稳定性观察失败或需重启观察窗口。"

    return {
        "created_at": _utc_now(),
        "required_trading_days": REQUIRED_DAYS,
        "observed_report_count": len(rows),
        "completed_trading_days": len(counted_rows),
        "skipped_report_count": len(skipped_rows),
        "evaluated_report_count": observed_days,
        "status": status,
        "decision": decision,
        "all_single_server": all_single_server,
        "single_server_warning_preserved": single_server_warning_preserved,
        "allow_enter_next_stage_s0_readonly_sandbox_basis": status == "PASS",
        "allow_s0_production": False,
        "daily_results": row_results,
        "skipped_results": skipped_rows[-20:],
    }


def _markdown_table_row(values: list[Any]) -> str:
    return "| " + " | ".join("" if value is None else str(value) for value in values) + " |"


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, default=str), encoding="utf-8")


def _write_markdown(summary: dict[str, Any]) -> None:
    rows = [
        "# STABILITY 5DAY SUMMARY",
        "",
        "## 结论",
        "",
        f"- 生成时间：`{summary['created_at']}`",
        f"- 需要交易日：`{summary['required_trading_days']}`",
        f"- 已完成交易日：`{summary['completed_trading_days']}`",
        f"- SKIP 日报数：`{summary['skipped_report_count']}`",
        f"- 已评估日报数：`{summary['evaluated_report_count']}`",
        f"- 状态：`{summary['status']}`",
        f"- 结论：{summary['decision']}",
        f"- 是否允许作为 S0 只读沙盒稳定基础：`{summary['allow_enter_next_stage_s0_readonly_sandbox_basis']}`",
        f"- 是否允许 S0 正式生产：`{summary['allow_s0_production']}`",
        "",
        "## 最近观察日",
        "",
        "| 日期 | 交易日 | 计入 | daily | overall | pytdx状态 | primary | hot backup | easy fallback | AK/Bao daily | consistency | audit |",
        "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for item in summary["daily_results"]:
        rows.append(
            _markdown_table_row(
                [
                    item.get("observation_date"),
                    item.get("is_trading_day"),
                    item.get("counted_in_5day"),
                    item.get("daily_acceptance"),
                    item.get("overall_live_gate"),
                    f"{item.get('pytdx_available_server_count')} / {item.get('pytdx_server_pool_status')}",
                    item.get("pytdx_primary_server"),
                    item.get("pytdx_hot_backup_server"),
                    item.get("easyquotation_fallback_ready"),
                    f"{item.get('akshare_daily_status')}/{item.get('baostock_daily_status')}",
                    item.get("source_consistency_status"),
                    f"jsonl={item.get('audit_jsonl_written')}, db={item.get('audit_sqlite_written')}",
                ]
            )
        )
    if summary["skipped_results"]:
        rows.extend(["", "## 未计入日报", ""])
        for item in summary["skipped_results"]:
            rows.append(
                f"- `{item.get('observation_date')}`: mode={item.get('mode')}, "
                f"trading_day={item.get('is_trading_day')}, daily={item.get('daily_acceptance')}"
            )
    failed_items = [item for item in summary["daily_results"] if item.get("failures")]
    if failed_items:
        rows.extend(["", "## 阻断项", ""])
        for item in failed_items:
            rows.append(f"- `{item.get('observation_date')}`: " + "；".join(item["failures"]))
    rows.extend(
        [
            "",
            "## 审计声明",
            "",
            "- 本汇总只读取每日稳定性观察 JSON，不联网。",
            "- 未接入 S0、QMT、券商账户或自动交易。",
            "- 未输出候选股池、策略信号、交易计划、买卖点、仓位、收益率或胜率。",
            "- 即使 5 日观察 PASS，S0 正式生产仍禁止。",
        ]
    )
    SUMMARY_MD_PATH.write_text("\n".join(rows) + "\n", encoding="utf-8")


def main() -> int:
    daily_reports = _load_daily_reports()
    summary = _build_summary(daily_reports)
    _write_json(SUMMARY_JSON_PATH, summary)
    _write_markdown(summary)
    print(json.dumps(summary, ensure_ascii=False, indent=2, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
