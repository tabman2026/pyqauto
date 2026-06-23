from __future__ import annotations

import importlib.util
import json
import os
import sqlite3
import sys
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from astock_source_router.adapters.pytdx_adapter import (  # noqa: E402
    ACTIVE_SERVER_POOL_PATH,
    load_pytdx_server_pool_records,
)
from astock_source_router.core.errors import AllSourcesFailedError  # noqa: E402
from astock_source_router.core.features import (  # noqa: E402
    FULL_REALTIME_QUOTES,
    INDEX_REALTIME,
    MINUTE_KLINE,
    REALTIME_QUOTES,
)
from astock_source_router.core.models import RouterConfig  # noqa: E402
from astock_source_router.core.router import MarketRouter  # noqa: E402

LOGS_DIR = PROJECT_ROOT / "logs"
JSON_REPORT_PATH = LOGS_DIR / "pytdx_runtime_failover_report.json"
MD_REPORT_PATH = PROJECT_ROOT / "PYTDX_RUNTIME_FAILOVER_REPORT.md"
TEMP_CONFIG_DIR = LOGS_DIR / "pytdx_runtime_failover_configs"
MAX_REPORT_ATTEMPTS = 8

FEATURE_CASES: dict[str, dict[str, Any]] = {
    REALTIME_QUOTES: {"codes": ["000001", "600519"]},
    FULL_REALTIME_QUOTES: {"codes": ["000001", "600519"]},
    INDEX_REALTIME: {"codes": ["000001", "399001", "399006", "000300"]},
    MINUTE_KLINE: {"code": "000001", "period": "5"},
}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _dependency_installed(name: str) -> bool:
    return importlib.util.find_spec(name) is not None


def _read_active_payload() -> dict[str, Any] | None:
    try:
        payload = json.loads(ACTIVE_SERVER_POOL_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return payload if isinstance(payload, dict) else {"servers": payload}


def _is_pass_server(server: dict[str, Any]) -> bool:
    return (
        str(server.get("grade") or server.get("role") or "").lower() != "disabled"
        and str(server.get("connect_status") or "").upper() == "PASS"
        and str(server.get("quote_status") or "").upper() == "PASS"
    )


def _role(server: dict[str, Any]) -> str:
    role = str(server.get("role", server.get("grade", "backup"))).lower()
    return "backup" if role == "backup_pool" else role


def _write_temp_config(name: str, payload: dict[str, Any], fake_roles: set[str]) -> Path:
    TEMP_CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    out = deepcopy(payload)
    servers = out.get("servers", [])
    for server in servers:
        if isinstance(server, dict) and _is_pass_server(server) and _role(server) in fake_roles:
            server["fake_fail"] = True
    path = TEMP_CONFIG_DIR / f"{name}.json"
    path.write_text(json.dumps(out, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    return path


def _write_all_fake_config(payload: dict[str, Any]) -> Path:
    TEMP_CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    out = deepcopy(payload)
    for server in out.get("servers", []):
        if isinstance(server, dict) and _is_pass_server(server):
            server["fake_fail"] = True
    path = TEMP_CONFIG_DIR / "all_pytdx_fake_fail.json"
    path.write_text(json.dumps(out, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    return path


def _router_with_config(active_path: Path) -> MarketRouter:
    os.environ["PYTDX_ACTIVE_SERVER_POOL_PATH"] = str(active_path)
    config = RouterConfig(
        cache_dir=PROJECT_ROOT / ".cache" / "pytdx_runtime_failover",
        log_dir=LOGS_DIR,
        enable_cache=False,
        enable_sqlite_audit=True,
        request_timeout_seconds=20.0,
        min_interval_seconds={
            "pytdx": 0.0,
            "easyquotation_sina": 0.0,
            "easyquotation_tencent": 0.0,
            "akshare": 0.0,
        },
    )
    return MarketRouter(config=config)


def _extract_pytdx_trace(result_trace: list[dict[str, Any]]) -> dict[str, Any] | None:
    for item in result_trace:
        if item.get("source") == "pytdx":
            metadata = item.get("pytdx_runtime_failover")
            if isinstance(metadata, dict):
                return metadata
            return item
    return None


def _short_text(value: Any, limit: int = 300) -> str | None:
    if value is None:
        return None
    text = str(value)
    return text if len(text) <= limit else text[:limit] + "...<truncated>"


def _compact_attempts(attempts: Any) -> list[dict[str, Any]]:
    if not isinstance(attempts, list):
        return []
    selected = attempts[:MAX_REPORT_ATTEMPTS]
    compacted = [
        {
            "endpoint": item.get("endpoint"),
            "role": item.get("role"),
            "latency_ms": item.get("latency_ms"),
            "status": item.get("status"),
            "error_type": item.get("error_type"),
            "error_message": _short_text(item.get("error_message"), 120),
        }
        for item in selected
        if isinstance(item, dict)
    ]
    if len(attempts) > MAX_REPORT_ATTEMPTS:
        compacted.append({"truncated_attempt_count": len(attempts) - MAX_REPORT_ATTEMPTS})
    return compacted


def _compact_pytdx_metadata(metadata: Any) -> dict[str, Any] | None:
    if not isinstance(metadata, dict):
        return None
    attempts = metadata.get("pytdx_failover_attempts") or metadata.get("attempted_servers") or []
    return {
        "selected_server": metadata.get("selected_server"),
        "selected_server_role": metadata.get("selected_server_role"),
        "selected_server_latency_ms": metadata.get("selected_server_latency_ms"),
        "failover_reason": metadata.get("failover_reason"),
        "failover_count": metadata.get("failover_count"),
        "pytdx_all_failed": metadata.get("pytdx_all_failed"),
        "attempt_count": len(attempts) if isinstance(attempts, list) else None,
        "attempts_sample": _compact_attempts(attempts),
    }


def _compact_trace(trace: Any) -> list[dict[str, Any]]:
    if not isinstance(trace, list):
        return []
    out: list[dict[str, Any]] = []
    for item in trace:
        if not isinstance(item, dict):
            continue
        compact = {
            "source": item.get("source"),
            "status": item.get("status"),
            "latency_ms": item.get("latency_ms"),
            "error_type": item.get("error_type"),
            "error_message": _short_text(item.get("error_message")),
            "fallback_reason": item.get("fallback_reason"),
        }
        metadata = _compact_pytdx_metadata(item.get("pytdx_runtime_failover"))
        if metadata is not None:
            compact["pytdx_runtime_failover"] = metadata
        out.append(compact)
    return out


def _run_feature_case(
    *,
    scenario: str,
    feature: str,
    kwargs: dict[str, Any],
    active_path: Path,
    expected_source: str | set[str],
    expected_role: str | None,
) -> dict[str, Any]:
    started = datetime.now(timezone.utc)
    try:
        router = _router_with_config(active_path)
        result = router.fetch_result(feature, **kwargs)
        trace = result.fallback_trace
        pytdx_trace = _extract_pytdx_trace(trace)
        selected_role = pytdx_trace.get("selected_server_role") if pytdx_trace else None
        expected_source_ok = (
            result.source in expected_source if isinstance(expected_source, set) else result.source == expected_source
        )
        expected_role_ok = expected_role is None or selected_role == expected_role
        status = "PASS" if expected_source_ok and expected_role_ok else "FAIL"
        return {
            "scenario": scenario,
            "feature": feature,
            "status": status,
            "selected_source": result.source,
            "selected_server": pytdx_trace.get("selected_server") if pytdx_trace else None,
            "selected_server_role": selected_role,
            "failover_count": pytdx_trace.get("failover_count") if pytdx_trace else None,
            "pytdx_all_failed": pytdx_trace.get("pytdx_all_failed") if pytdx_trace else None,
            "fallback_trace": _compact_trace(trace),
            "row_count": int(len(result.data)),
            "started_at": started.isoformat(),
            "finished_at": _now(),
        }
    except AllSourcesFailedError as exc:
        return {
            "scenario": scenario,
            "feature": feature,
            "status": "FAIL",
            "selected_source": None,
            "error_type": type(exc).__name__,
            "error_message": _short_text(exc),
            "fallback_trace": _compact_trace(exc.trace),
            "started_at": started.isoformat(),
            "finished_at": _now(),
        }
    except Exception as exc:
        return {
            "scenario": scenario,
            "feature": feature,
            "status": "FAIL",
            "selected_source": None,
            "error_type": type(exc).__name__,
            "error_message": _short_text(exc),
            "started_at": started.isoformat(),
            "finished_at": _now(),
        }


def _sqlite_trace_count() -> int:
    db_path = LOGS_DIR / "source_router.db"
    if not db_path.exists():
        return 0
    with sqlite3.connect(db_path) as conn:
        row = conn.execute("SELECT COUNT(*) FROM pytdx_runtime_failover_trace").fetchone()
    return int(row[0] or 0)


def _write_report(report: dict[str, Any]) -> None:
    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    JSON_REPORT_PATH.write_text(
        json.dumps(report, ensure_ascii=False, indent=2, default=str),
        encoding="utf-8",
    )
    lines = [
        "# PYTDX_RUNTIME_FAILOVER_REPORT",
        "",
        f"- created_at: {report['created_at']}",
        f"- live_enabled: {report['live_enabled']}",
        f"- overall_status: {report['overall_status']}",
        f"- active_config: {report.get('active_config')}",
        f"- sqlite_pytdx_trace_rows_after: {report.get('sqlite_pytdx_trace_rows_after')}",
        "",
        "## Cases",
        "",
        "| scenario | feature | status | selected_source | selected_server_role | failover_count |",
        "|---|---|---|---|---|---|",
    ]
    for item in report.get("cases", []):
        lines.append(
            "| "
            + " | ".join(
                str(item.get(key, ""))
                for key in [
                    "scenario",
                    "feature",
                    "status",
                    "selected_source",
                    "selected_server_role",
                    "failover_count",
                ]
            )
            + " |"
        )
    lines.extend(
        [
            "",
            "## Audit",
            "",
            f"- source_router_jsonl_exists: {report.get('source_router_jsonl_exists')}",
            f"- source_router_db_exists: {report.get('source_router_db_exists')}",
            f"- pytdx_runtime_failover_trace_table: {report.get('pytdx_runtime_failover_trace_table')}",
        ]
    )
    MD_REPORT_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    live_enabled = os.environ.get("ENABLE_PYTDX_FAILOVER_TEST") == "1"
    report: dict[str, Any] = {
        "created_at": _now(),
        "live_enabled": live_enabled,
        "active_config": str(ACTIVE_SERVER_POOL_PATH.relative_to(PROJECT_ROOT)),
        "cases": [],
        "forbidden_output_audit": {
            "s0_connected": False,
            "qmt_connected": False,
            "broker_connected": False,
            "auto_trading_enabled": False,
            "trading_advice_output": False,
            "candidate_pool_output": False,
            "strategy_signal_output": False,
            "buy_sell_point_output": False,
            "position_output": False,
            "return_or_winrate_output": False,
            "trading_plan_output": False,
        },
    }
    if not live_enabled:
        report["overall_status"] = "SKIP"
        report["skip_reason"] = "ENABLE_PYTDX_FAILOVER_TEST is not 1"
        _write_report(report)
        print(json.dumps(report, ensure_ascii=False, indent=2, default=str))
        return 0

    if not _dependency_installed("pytdx"):
        report["overall_status"] = "SKIP"
        report["skip_reason"] = "pytdx dependency is not installed"
        _write_report(report)
        print(json.dumps(report, ensure_ascii=False, indent=2, default=str))
        return 0

    active_payload = _read_active_payload()
    records, warnings = load_pytdx_server_pool_records()
    report["active_pool_warnings"] = warnings
    report["active_pool_candidate_count"] = len(records)
    if active_payload is None or len(records) < 3:
        report["overall_status"] = "FAIL"
        report["error"] = "active pool must contain at least primary, hot_backup, and backup candidates"
        _write_report(report)
        print(json.dumps(report, ensure_ascii=False, indent=2, default=str))
        return 1

    normal_path = ACTIVE_SERVER_POOL_PATH
    primary_fake_path = _write_temp_config("primary_fake_fail", active_payload, {"primary"})
    primary_hot_fake_path = _write_temp_config(
        "primary_hot_fake_fail",
        active_payload,
        {"primary", "hot_backup"},
    )
    all_fake_path = _write_all_fake_config(active_payload)

    previous_active_path = os.environ.get("PYTDX_ACTIVE_SERVER_POOL_PATH")
    try:
        for feature, kwargs in FEATURE_CASES.items():
            report["cases"].append(
                _run_feature_case(
                    scenario="normal_primary",
                    feature=feature,
                    kwargs=kwargs,
                    active_path=normal_path,
                    expected_source="pytdx",
                    expected_role="primary",
                )
            )
            report["cases"].append(
                _run_feature_case(
                    scenario="primary_fake_fail",
                    feature=feature,
                    kwargs=kwargs,
                    active_path=primary_fake_path,
                    expected_source="pytdx",
                    expected_role="hot_backup",
                )
            )
            report["cases"].append(
                _run_feature_case(
                    scenario="primary_hot_fake_fail",
                    feature=feature,
                    kwargs=kwargs,
                    active_path=primary_hot_fake_path,
                    expected_source="pytdx",
                    expected_role="backup",
                )
            )

        fallback_sources = {"easyquotation_sina", "easyquotation_tencent"}
        if not _dependency_installed("easyquotation"):
            for feature in [REALTIME_QUOTES, FULL_REALTIME_QUOTES, INDEX_REALTIME]:
                report["cases"].append(
                    {
                        "scenario": "all_pytdx_fake_fail",
                        "feature": feature,
                        "status": "SKIP",
                        "skip_reason": "easyquotation dependency is not installed",
                    }
                )
        else:
            for feature in [REALTIME_QUOTES, FULL_REALTIME_QUOTES, INDEX_REALTIME]:
                report["cases"].append(
                    _run_feature_case(
                        scenario="all_pytdx_fake_fail",
                        feature=feature,
                        kwargs=FEATURE_CASES[feature],
                        active_path=all_fake_path,
                        expected_source=fallback_sources,
                        expected_role=None,
                    )
                )
        report["cases"].append(
            {
                "scenario": "all_pytdx_fake_fail",
                "feature": MINUTE_KLINE,
                "status": "SKIP",
                "skip_reason": "minute_kline source policy is pytdx-only; no easyquotation minute fallback",
            }
        )
    finally:
        if previous_active_path is None:
            os.environ.pop("PYTDX_ACTIVE_SERVER_POOL_PATH", None)
        else:
            os.environ["PYTDX_ACTIVE_SERVER_POOL_PATH"] = previous_active_path

    report["source_router_jsonl_exists"] = (LOGS_DIR / "source_router.jsonl").exists()
    report["source_router_db_exists"] = (LOGS_DIR / "source_router.db").exists()
    report["sqlite_pytdx_trace_rows_after"] = _sqlite_trace_count()
    report["pytdx_runtime_failover_trace_table"] = report["sqlite_pytdx_trace_rows_after"] > 0
    failed = [item for item in report["cases"] if item.get("status") == "FAIL"]
    report["overall_status"] = "PASS" if not failed else "FAIL"
    _write_report(report)
    print(json.dumps(report, ensure_ascii=False, indent=2, default=str))
    return 0 if report["overall_status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
