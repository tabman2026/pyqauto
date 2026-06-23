from __future__ import annotations

import argparse
import importlib.metadata
import json
import platform
import shutil
import sqlite3
import subprocess
import sys
import time
from collections.abc import Callable
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
PACKAGE_ROOT = ROOT / "aquote-router"
if str(PACKAGE_ROOT) not in sys.path:
    sys.path.insert(0, str(PACKAGE_ROOT))

from aquote_router import QuoteRouter, __version__  # noqa: E402
from aquote_router.exceptions import QuoteRouterError  # noqa: E402

TEST_SYMBOLS = ["000001", "600000", "399001"]
STOCK_SYMBOLS = ["000001", "600000"]
INDEX_SYMBOLS = ["399001"]
KLINE_SYMBOLS = TEST_SYMBOLS

AUDIT_JSONL = ROOT / "logs" / "live_check_audit.jsonl"
AUDIT_SQLITE = ROOT / "logs" / "live_check_audit.sqlite3"
REPORT_PATH = ROOT / "LIVE_CHECK_REPORT.md"
SUMMARY_PATH = ROOT / "LIVE_CHECK_SUMMARY.json"
LOG_PATH = ROOT / "LIVE_CHECK_LOG.txt"

SOURCE_POLICY_PATH = PACKAGE_ROOT / "config" / "source_policy.example.yaml"
PYTDX_SERVERS_PATH = PACKAGE_ROOT / "config" / "pytdx_servers.example.json"

KLINE_API_NAMES = {"minute_kline", "daily_kline", "kline"}


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run local live checks for aquote-router real data sources."
    )
    parser.add_argument("--json", action="store_true", help="Print JSON summary.")
    parser.add_argument(
        "--skip-cli",
        action="store_true",
        help="Skip console-script CLI checks.",
    )
    parser.add_argument(
        "--count",
        type=int,
        default=10,
        help="K-line record count requested per live check.",
    )
    args = parser.parse_args()

    started_at = datetime.now(timezone.utc)
    log_lines: list[str] = []
    log_lines.append(f"Live check started at: {started_at.isoformat()}")
    log_lines.append(f"Project root: {ROOT}")
    log_lines.append(f"Package root: {PACKAGE_ROOT}")
    log_lines.append("")

    router = QuoteRouter.from_config(
        pytdx_servers_path=PYTDX_SERVERS_PATH,
        source_policy_path=SOURCE_POLICY_PATH,
        audit_jsonl_path=AUDIT_JSONL,
        audit_sqlite_path=AUDIT_SQLITE,
    )

    api_results: list[dict[str, Any]] = []
    api_results.append(
        _run_router_call(
            "realtime_quotes",
            f"realtime_quotes({TEST_SYMBOLS})",
            lambda: router.realtime_quotes(TEST_SYMBOLS),
            log_lines,
        )
    )
    api_results.append(
        _run_router_call(
            "full_realtime_quotes",
            f"full_realtime_quotes({TEST_SYMBOLS})",
            lambda: router.full_realtime_quotes(TEST_SYMBOLS),
            log_lines,
        )
    )
    api_results.append(
        _run_router_call(
            "index_realtime",
            f"index_realtime({INDEX_SYMBOLS})",
            lambda: router.index_realtime(INDEX_SYMBOLS),
            log_lines,
        )
    )
    for period in ("1m", "15m", "60m"):
        for symbol in KLINE_SYMBOLS:
            api_results.append(
                _run_router_call(
                    "minute_kline",
                    f"minute_kline({symbol}, period={period}, count={args.count})",
                    lambda symbol=symbol, period=period: router.minute_kline(
                        symbol, period=period, count=args.count
                    ),
                    log_lines,
                    expected_source="pytdx",
                    expected_period=period,
                )
            )
    for symbol in KLINE_SYMBOLS:
        api_results.append(
            _run_router_call(
                "daily_kline",
                f"daily_kline({symbol}, count={args.count})",
                lambda symbol=symbol: router.daily_kline(symbol, count=args.count),
                log_lines,
                expected_source="pytdx",
                expected_period="1d",
            )
        )
    for period in ("15m", "1d"):
        for symbol in KLINE_SYMBOLS:
            api_results.append(
                _run_router_call(
                    "kline",
                    f"kline({symbol}, period={period}, count={args.count})",
                    lambda symbol=symbol, period=period: router.kline(
                        symbol, period=period, count=args.count
                    ),
                    log_lines,
                    expected_source="pytdx",
                    expected_period=period,
                )
            )

    cli_results = [] if args.skip_cli else _run_cli_checks(log_lines)
    finished_at = datetime.now(timezone.utc)
    summary = _build_summary(
        started_at=started_at,
        finished_at=finished_at,
        api_results=api_results,
        cli_results=cli_results,
        kline_count=args.count,
    )
    _write_report(summary)
    _write_summary(summary)
    _write_log(log_lines, summary)

    if args.json:
        print(json.dumps(summary, ensure_ascii=False, indent=2))
    else:
        print(_plain_summary(summary))

    return 0


def _run_router_call(
    api_name: str,
    label: str,
    call: Callable[[], list[Any]],
    log_lines: list[str],
    *,
    expected_source: str | None = None,
    expected_period: str | None = None,
) -> dict[str, Any]:
    started = time.perf_counter()
    before_jsonl = _jsonl_count(AUDIT_JSONL)
    before_sqlite = _sqlite_counts(AUDIT_SQLITE)
    log_lines.append(f"[API] START {label}")
    try:
        records = call()
        rows = [record.to_dict() for record in records]
        validation = _validate_rows(
            api_name,
            rows,
            expected_source=expected_source,
            expected_period=expected_period,
        )
        status = "PASS" if validation["valid"] else "FAIL"
        reason = "live_source_ok" if validation["valid"] else validation["reason"]
        error_type = None
        error_code = None
    except Exception as exc:
        rows = []
        status = "FAIL"
        reason = f"{type(exc).__name__}: {exc}"
        error_type = type(exc).__name__
        error_code = getattr(exc, "code", None) if isinstance(exc, QuoteRouterError) else None
    after_jsonl = _jsonl_count(AUDIT_JSONL)
    after_sqlite = _sqlite_counts(AUDIT_SQLITE)
    audit_records = _read_jsonl_slice(AUDIT_JSONL, before_jsonl, after_jsonl)
    duration_ms = round((time.perf_counter() - started) * 1000, 3)
    audit_delta = {
        "jsonl_records": max(0, after_jsonl - before_jsonl),
        "sqlite_audit_rows": max(
            0,
            after_sqlite["quote_router_audit"] - before_sqlite["quote_router_audit"],
        ),
        "sqlite_attempt_rows": max(
            0,
            after_sqlite["quote_router_attempts"]
            - before_sqlite["quote_router_attempts"],
        ),
    }
    audit_written = audit_delta["jsonl_records"] > 0 and audit_delta["sqlite_audit_rows"] > 0
    row_sources = _row_sources(rows)
    audit_sources = _audit_sources(audit_records)
    trace_ids = _trace_ids(rows, audit_records)
    if status == "PASS" and not audit_written:
        status = "FAIL"
        reason = "audit_not_written"
    if status == "PASS" and not trace_ids:
        status = "FAIL"
        reason = "trace_id_not_recorded"

    log_lines.append(
        "[API] END "
        f"{label} status={status} rows={len(rows)} reason={reason} "
        f"duration_ms={duration_ms} trace_ids={trace_ids}"
    )
    if audit_records:
        log_lines.append(
            f"[API] AUDIT {label} records="
            + json.dumps(_compact_audit_records(audit_records), ensure_ascii=False)
        )
    log_lines.append("")

    return {
        "kind": "api",
        "api_name": api_name,
        "label": label,
        "status": status,
        "success": status == "PASS",
        "reason": reason,
        "error_type": error_type,
        "error_code": error_code,
        "duration_ms": duration_ms,
        "row_count": len(rows),
        "symbols": sorted({str(row.get("symbol")) for row in rows if row.get("symbol")}),
        "sources": row_sources,
        "audit_sources": audit_sources,
        "trace_ids": trace_ids,
        "audit_written": audit_written,
        "jsonl_audit_written": audit_delta["jsonl_records"] > 0,
        "sqlite_audit_written": audit_delta["sqlite_audit_rows"] > 0,
        "audit_delta": audit_delta,
        "expected_source": expected_source,
        "expected_period": expected_period,
    }


def _run_cli_checks(log_lines: list[str]) -> list[dict[str, Any]]:
    command_specs = [
        {
            "api_name": "diagnose",
            "label": "aquote-router diagnose --json",
            "args": ["diagnose", "--json"],
            "expects_records": False,
        },
        {
            "api_name": "realtime_quotes",
            "label": "aquote-router realtime 000001 600000 --json",
            "args": ["realtime", *STOCK_SYMBOLS, "--json"],
            "expects_records": True,
        },
        {
            "api_name": "index_realtime",
            "label": "aquote-router index 399001 --json",
            "args": ["index", "399001", "--json"],
            "expects_records": True,
        },
        {
            "api_name": "kline",
            "label": "aquote-router kline 000001 --period 15m --count 10 --json",
            "args": ["kline", "000001", "--period", "15m", "--count", "10", "--json"],
            "expects_records": True,
            "expected_source": "pytdx",
            "expected_period": "15m",
        },
        {
            "api_name": "kline",
            "label": "aquote-router kline 000001 --period 1d --count 10 --json",
            "args": ["kline", "000001", "--period", "1d", "--count", "10", "--json"],
            "expects_records": True,
            "expected_source": "pytdx",
            "expected_period": "1d",
        },
    ]
    executable = shutil.which("aquote-router")
    if not executable:
        reason = "aquote-router console script not found on PATH"
        return [
            {
                "kind": "cli",
                "api_name": spec["api_name"],
                "label": spec["label"],
                "status": "SKIP",
                "success": False,
                "reason": reason,
                "returncode": None,
                "row_count": 0,
                "sources": [],
                "trace_ids": [],
                "audit_written": False,
            }
            for spec in command_specs
        ]

    results = []
    for spec in command_specs:
        results.append(_run_cli_command(executable, spec, log_lines))
    return results


def _run_cli_command(
    executable: str,
    spec: dict[str, Any],
    log_lines: list[str],
) -> dict[str, Any]:
    before_jsonl = _jsonl_count(AUDIT_JSONL)
    before_sqlite = _sqlite_counts(AUDIT_SQLITE)
    command = [
        executable,
        "--config",
        str(SOURCE_POLICY_PATH),
        "--pytdx-servers",
        str(PYTDX_SERVERS_PATH),
        "--audit-jsonl",
        str(AUDIT_JSONL),
        "--audit-sqlite",
        str(AUDIT_SQLITE),
        *spec["args"],
    ]
    started = time.perf_counter()
    log_lines.append("[CLI] START " + spec["label"])
    result = subprocess.run(
        command,
        cwd=PACKAGE_ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=60,
        check=False,
    )
    duration_ms = round((time.perf_counter() - started) * 1000, 3)
    after_jsonl = _jsonl_count(AUDIT_JSONL)
    after_sqlite = _sqlite_counts(AUDIT_SQLITE)
    audit_records = _read_jsonl_slice(AUDIT_JSONL, before_jsonl, after_jsonl)
    stdout = result.stdout.strip()
    stderr = result.stderr.strip()
    rows: list[dict[str, Any]] = []
    payload: Any = None
    parse_error = None
    if stdout:
        try:
            payload = json.loads(stdout)
            if isinstance(payload, list):
                rows = [row for row in payload if isinstance(row, dict)]
        except json.JSONDecodeError as exc:
            parse_error = f"JSONDecodeError: {exc}"

    validation = {"valid": True, "reason": "cli_ok"}
    if result.returncode != 0:
        validation = {"valid": False, "reason": stderr or stdout or "non_zero_exit"}
    elif parse_error:
        validation = {"valid": False, "reason": parse_error}
    elif spec["expects_records"]:
        validation = _validate_rows(
            spec["api_name"],
            rows,
            expected_source=spec.get("expected_source"),
            expected_period=spec.get("expected_period"),
        )
    elif not isinstance(payload, dict):
        validation = {"valid": False, "reason": "diagnose_json_not_object"}

    audit_delta = {
        "jsonl_records": max(0, after_jsonl - before_jsonl),
        "sqlite_audit_rows": max(
            0,
            after_sqlite["quote_router_audit"] - before_sqlite["quote_router_audit"],
        ),
        "sqlite_attempt_rows": max(
            0,
            after_sqlite["quote_router_attempts"]
            - before_sqlite["quote_router_attempts"],
        ),
    }
    audit_expected = bool(spec["expects_records"])
    audit_written = (
        audit_delta["jsonl_records"] > 0 and audit_delta["sqlite_audit_rows"] > 0
    )
    status = "PASS" if validation["valid"] else "FAIL"
    reason = "cli_ok" if validation["valid"] else validation["reason"]
    if audit_expected and status == "PASS" and not audit_written:
        status = "FAIL"
        reason = "cli_audit_not_written"

    trace_ids = _trace_ids(rows, audit_records)
    log_lines.append(
        "[CLI] END "
        f"{spec['label']} status={status} returncode={result.returncode} "
        f"rows={len(rows)} reason={reason} duration_ms={duration_ms} "
        f"trace_ids={trace_ids}"
    )
    if stdout:
        log_lines.append(f"[CLI] STDOUT {spec['label']}: {_truncate(stdout, 2000)}")
    if stderr:
        log_lines.append(f"[CLI] STDERR {spec['label']}: {_truncate(stderr, 2000)}")
    log_lines.append("")

    return {
        "kind": "cli",
        "api_name": spec["api_name"],
        "label": spec["label"],
        "status": status,
        "success": status == "PASS",
        "reason": reason,
        "returncode": result.returncode,
        "duration_ms": duration_ms,
        "row_count": len(rows),
        "sources": _row_sources(rows),
        "audit_sources": _audit_sources(audit_records),
        "trace_ids": trace_ids,
        "audit_written": (not audit_expected) or audit_written,
        "jsonl_audit_written": audit_delta["jsonl_records"] > 0,
        "sqlite_audit_written": audit_delta["sqlite_audit_rows"] > 0,
        "audit_delta": audit_delta,
    }


def _validate_rows(
    api_name: str,
    rows: list[dict[str, Any]],
    *,
    expected_source: str | None,
    expected_period: str | None,
) -> dict[str, Any]:
    if not rows:
        return {"valid": False, "reason": "no_records_returned"}
    for row in rows:
        if not row.get("source"):
            return {"valid": False, "reason": "source_not_recorded"}
        if "source_level" not in row:
            return {"valid": False, "reason": "source_level_not_recorded"}
        if not row.get("trace_id"):
            return {"valid": False, "reason": "trace_id_not_recorded"}
        if expected_source and row.get("source") != expected_source:
            return {
                "valid": False,
                "reason": f"unexpected_source:{row.get('source')}",
            }
        if expected_period and row.get("period") != expected_period:
            return {
                "valid": False,
                "reason": f"unexpected_period:{row.get('period')}",
            }
        if api_name in KLINE_API_NAMES and row.get("source") != "pytdx":
            return {"valid": False, "reason": "kline_not_pytdx_only"}
    return {"valid": True, "reason": "ok"}


def _build_summary(
    *,
    started_at: datetime,
    finished_at: datetime,
    api_results: list[dict[str, Any]],
    cli_results: list[dict[str, Any]],
    kline_count: int,
) -> dict[str, Any]:
    all_results = api_results + cli_results
    grouped = _group_statuses(api_results)
    cli_grouped = _group_statuses(cli_results)
    package_metadata_version = _package_version("aquote-router")
    live_status = {
        "realtime_quotes": grouped.get("realtime_quotes", False),
        "full_realtime_quotes": grouped.get("full_realtime_quotes", False),
        "index_realtime": grouped.get("index_realtime", False),
        "minute_kline_1m": _all_labels_pass(api_results, "minute_kline", "period=1m"),
        "minute_kline_15m": _all_labels_pass(api_results, "minute_kline", "period=15m"),
        "minute_kline_60m": _all_labels_pass(api_results, "minute_kline", "period=60m"),
        "daily_kline": grouped.get("daily_kline", False),
        "kline_15m": _all_labels_pass(api_results, "kline", "period=15m"),
        "kline_1d": _all_labels_pass(api_results, "kline", "period=1d"),
        "kline_unified": _all_labels_pass(api_results, "kline", "period=15m")
        and _all_labels_pass(api_results, "kline", "period=1d"),
        "diagnose_json": cli_grouped.get("diagnose", False),
    }
    audit_status = {
        "jsonl_path": str(AUDIT_JSONL),
        "sqlite_path": str(AUDIT_SQLITE),
        "jsonl_exists": AUDIT_JSONL.exists(),
        "sqlite_exists": AUDIT_SQLITE.exists(),
        "jsonl_records_total": _jsonl_count(AUDIT_JSONL),
        "sqlite_counts": _sqlite_counts(AUDIT_SQLITE),
        "all_live_calls_audited": all(
            result.get("audit_written")
            for result in api_results
            if result["kind"] == "api"
        ),
    }
    acceptance = {
        "status": "PASS"
        if all(live_status.values()) and audit_status["all_live_calls_audited"]
        else "FAIL",
        "audit_conclusion": "JSONL and SQLite audit records were generated"
        if audit_status["jsonl_exists"] and audit_status["sqlite_exists"]
        else "audit outputs missing",
        "requires_v0_2_1": False,
        "no_public_api_change": True,
        "no_ci_integration": True,
        "kline_pytdx_only": _kline_results_are_pytdx_only(api_results),
        "no_trading_integration": True,
        "no_investment_advice": True,
    }
    blocking_failures = [
        result
        for result in all_results
        if result["status"] == "FAIL" and _is_probable_local_blocking_bug(result)
    ]
    if blocking_failures:
        acceptance["requires_v0_2_1"] = True
        acceptance["blocking_failures"] = [
            {
                "label": item["label"],
                "reason": item["reason"],
                "error_type": item.get("error_type"),
                "error_code": item.get("error_code"),
            }
            for item in blocking_failures
        ]

    return {
        "task": "任务018",
        "created_at": started_at.isoformat(),
        "finished_at": finished_at.isoformat(),
        "duration_seconds": round((finished_at - started_at).total_seconds(), 3),
        "mode": "live_check",
        "test_symbols": TEST_SYMBOLS,
        "kline_count": kline_count,
        "environment": {
            "python_executable": sys.executable,
            "python_version": platform.python_version(),
            "platform": platform.platform(),
            "aquote_router_import_version": __version__,
            "aquote_router_package_metadata_version": package_metadata_version,
            "aquote_router_console": shutil.which("aquote-router"),
        },
        "config": {
            "source_policy_path": str(SOURCE_POLICY_PATH),
            "pytdx_servers_path": str(PYTDX_SERVERS_PATH),
            "fallback_policy": {
                "realtime": "pytdx -> easyquotation_sina -> easyquotation_tencent",
                "kline": "pytdx only",
            },
        },
        "live_status": live_status,
        "audit_status": audit_status,
        "acceptance": acceptance,
        "results": all_results,
        "generated_files": [
            str(REPORT_PATH),
            str(SUMMARY_PATH),
            str(LOG_PATH),
            str(AUDIT_JSONL),
            str(AUDIT_SQLITE),
        ],
    }


def _write_report(summary: dict[str, Any]) -> None:
    status = summary["live_status"]
    audit = summary["audit_status"]
    acceptance = summary["acceptance"]
    lines = [
        "# Live Check Report",
        "",
        f"Created at: {summary['created_at']}",
        f"Finished at: {summary['finished_at']}",
        f"Mode: {summary['mode']}",
        "",
        "This is a local manual diagnostic report. It is not part of GitHub Actions CI.",
        "No trading, brokerage, account login, order placement, screening, timing,",
        "return promise, or investment advice workflow is included.",
        "",
        "## Acceptance",
        "",
        f"- Overall status: {acceptance['status']}",
        f"- Audit conclusion: {acceptance['audit_conclusion']}",
        f"- Requires v0.2.1: {acceptance['requires_v0_2_1']}",
        f"- K-line source rule: {'PASS' if acceptance['kline_pytdx_only'] else 'FAIL'}",
        "",
        "## Live Status",
        "",
        "| Check | Status |",
        "|---|---|",
    ]
    for key, value in status.items():
        lines.append(f"| {key} | {'PASS' if value else 'FAIL'} |")
    lines.extend(
        [
            "",
            "## Audit Outputs",
            "",
            f"- JSONL: `{audit['jsonl_path']}`",
            f"- SQLite: `{audit['sqlite_path']}`",
            f"- JSONL records total: {audit['jsonl_records_total']}",
            f"- SQLite rows: {json.dumps(audit['sqlite_counts'], ensure_ascii=False)}",
            f"- All live API calls audited: {audit['all_live_calls_audited']}",
            "",
            "## Results",
            "",
            "| Kind | Check | Status | Rows | Sources | Trace IDs | Reason |",
            "|---|---|---|---:|---|---|---|",
        ]
    )
    for result in summary["results"]:
        lines.append(
            "| {kind} | {label} | {status} | {rows} | {sources} | {trace_ids} | {reason} |".format(
                kind=result["kind"],
                label=_md_escape(result["label"]),
                status=result["status"],
                rows=result.get("row_count", 0),
                sources=_md_escape(json.dumps(result.get("sources", []), ensure_ascii=False)),
                trace_ids=_md_escape(", ".join(result.get("trace_ids", []))),
                reason=_md_escape(str(result.get("reason", ""))),
            )
        )
    lines.extend(
        [
            "",
            "## Notes",
            "",
            "- Realtime routing is checked through pytdx, then easyquotation Sina, then easyquotation Tencent.",
            "- K-line checks are accepted only when returned rows report `source=pytdx`.",
            "- Failed live source calls are recorded as diagnostic failures with the observed reason.",
        ]
    )
    REPORT_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _write_summary(summary: dict[str, Any]) -> None:
    SUMMARY_PATH.write_text(
        json.dumps(summary, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def _write_log(log_lines: list[str], summary: dict[str, Any]) -> None:
    LOG_PATH.write_text(
        "\n".join(log_lines)
        + "\n"
        + "Summary status: "
        + summary["acceptance"]["status"]
        + "\n",
        encoding="utf-8",
    )


def _plain_summary(summary: dict[str, Any]) -> str:
    status = summary["live_status"]
    passed = sum(1 for value in status.values() if value)
    total = len(status)
    return (
        f"Live check finished: {summary['acceptance']['status']} "
        f"({passed}/{total} checks passed). "
        f"Report: {REPORT_PATH}"
    )


def _jsonl_count(path: Path) -> int:
    if not path.exists():
        return 0
    with path.open("r", encoding="utf-8") as file:
        return sum(1 for line in file if line.strip())


def _read_jsonl_slice(path: Path, start: int, end: int) -> list[dict[str, Any]]:
    if not path.exists() or end <= start:
        return []
    records: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as file:
        for index, line in enumerate(file):
            if index < start:
                continue
            if index >= end:
                break
            try:
                records.append(json.loads(line))
            except json.JSONDecodeError:
                records.append({"parse_error": "JSONDecodeError", "raw": line.strip()})
    return records


def _sqlite_counts(path: Path) -> dict[str, int]:
    if not path.exists():
        return {"quote_router_audit": 0, "quote_router_attempts": 0}
    counts = {"quote_router_audit": 0, "quote_router_attempts": 0}
    try:
        with sqlite3.connect(path) as connection:
            for table in counts:
                if _sqlite_table_exists(connection, table):
                    counts[table] = int(
                        connection.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
                    )
    except sqlite3.Error:
        return counts
    return counts


def _sqlite_table_exists(connection: sqlite3.Connection, table: str) -> bool:
    row = connection.execute(
        "SELECT name FROM sqlite_master WHERE type = 'table' AND name = ?",
        (table,),
    ).fetchone()
    return row is not None


def _row_sources(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen: set[tuple[str | None, str | None]] = set()
    sources: list[dict[str, Any]] = []
    for row in rows:
        key = (row.get("source"), row.get("source_level"))
        if key in seen:
            continue
        seen.add(key)
        sources.append({"source": key[0], "source_level": key[1]})
    return sources


def _audit_sources(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    sources: list[dict[str, Any]] = []
    for record in records:
        sources.append(
            {
                "trace_id": record.get("trace_id"),
                "selected_source": record.get("selected_source"),
                "selected_source_level": record.get("selected_source_level"),
                "success": record.get("success"),
                "record_count": record.get("record_count"),
            }
        )
    return sources


def _trace_ids(rows: list[dict[str, Any]], audit_records: list[dict[str, Any]]) -> list[str]:
    seen: set[str] = set()
    trace_ids: list[str] = []
    for row in rows:
        trace_id = row.get("trace_id")
        if isinstance(trace_id, str) and trace_id and trace_id not in seen:
            seen.add(trace_id)
            trace_ids.append(trace_id)
    for record in audit_records:
        trace_id = record.get("trace_id")
        if isinstance(trace_id, str) and trace_id and trace_id not in seen:
            seen.add(trace_id)
            trace_ids.append(trace_id)
    return trace_ids


def _compact_audit_records(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        {
            "trace_id": record.get("trace_id"),
            "api_name": record.get("api_name"),
            "selected_source": record.get("selected_source"),
            "selected_source_level": record.get("selected_source_level"),
            "success": record.get("success"),
            "error_type": record.get("error_type"),
            "record_count": record.get("record_count"),
        }
        for record in records
    ]


def _group_statuses(results: list[dict[str, Any]]) -> dict[str, bool]:
    grouped: dict[str, list[bool]] = {}
    for result in results:
        grouped.setdefault(str(result["api_name"]), []).append(bool(result["success"]))
    return {key: bool(values) and all(values) for key, values in grouped.items()}


def _all_labels_pass(results: list[dict[str, Any]], api_name: str, label_part: str) -> bool:
    matched = [
        result
        for result in results
        if result["api_name"] == api_name and label_part in result["label"]
    ]
    return bool(matched) and all(result["success"] for result in matched)


def _kline_results_are_pytdx_only(results: list[dict[str, Any]]) -> bool:
    kline_results = [result for result in results if result["api_name"] in KLINE_API_NAMES]
    if not kline_results:
        return False
    for result in kline_results:
        if not result["success"]:
            continue
        for source in result.get("sources", []):
            if source.get("source") != "pytdx":
                return False
    return True


def _is_probable_local_blocking_bug(result: dict[str, Any]) -> bool:
    reason = str(result.get("reason", ""))
    network_markers = [
        "connection",
        "connect",
        "timed out",
        "timeout",
        "returned no",
        "all configured sources failed",
        "SourceUnavailableError",
        "PYTDX_CONNECT_FAILED",
        "EASYQUOTATION",
        "no_records_returned",
    ]
    if any(marker.lower() in reason.lower() for marker in network_markers):
        return False
    return result.get("error_type") in {
        "AttributeError",
        "ImportError",
        "ModuleNotFoundError",
        "TypeError",
        "ValueError",
        "JSONDecodeError",
    }


def _package_version(package_name: str) -> str | None:
    try:
        return importlib.metadata.version(package_name)
    except importlib.metadata.PackageNotFoundError:
        return None


def _truncate(value: str, limit: int) -> str:
    if len(value) <= limit:
        return value
    return value[:limit] + "...<truncated>"


def _md_escape(value: str) -> str:
    return value.replace("|", "\\|").replace("\n", " ")


if __name__ == "__main__":
    raise SystemExit(main())
