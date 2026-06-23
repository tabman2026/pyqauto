from __future__ import annotations

import importlib.metadata
import json
import os
import platform
import sqlite3
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import scripts.check_source_consistency as source_consistency  # noqa: E402
import scripts.pytdx_server_pool_refresh as pytdx_server_pool_refresh  # noqa: E402
import scripts.smoke_test_live as live_smoke  # noqa: E402
from astock_source_router.adapters.adata_adapter import ADataAdapter  # noqa: E402
from astock_source_router.adapters.akshare_adapter import AkShareAdapter  # noqa: E402
from astock_source_router.core.errors import (  # noqa: E402
    AllSourcesFailedError,
    UnsupportedFeatureError,
)
from astock_source_router.core.features import (  # noqa: E402
    DAILY_KLINE,
    FULL_REALTIME_QUOTES,
    INDEX_REALTIME,
    LITE_REALTIME_QUOTES,
    MINUTE_KLINE,
    REALTIME_QUOTES,
    TRADE_CALENDAR,
)
from astock_source_router.core.models import RouterConfig  # noqa: E402
from astock_source_router.core.policy import DEFAULT_SOURCE_POLICY  # noqa: E402
from astock_source_router.core.router import MarketRouter  # noqa: E402

LOGS_DIR = PROJECT_ROOT / "logs"
REPORTS_DIR = PROJECT_ROOT / "reports"
SCHEDULE_CONFIG_PATH = PROJECT_ROOT / "config" / "stability_watch_schedule.json"
LIVE_ENV_VAR = "ENABLE_STABILITY_WATCH"
WATCH_VERSION = "task014B_v1"
WATCH_SOURCE_TIMEOUT_SECONDS = 45.0
TEST_STOCK_CODES = ["000001", "600519"]
TEST_INDEX_CODES = ["000001", "399001", "399006", "000300"]
DAILY_KLINE_KWARGS = {"code": "000001", "start_date": "20240102", "end_date": "20240102"}
TRADE_CALENDAR_KWARGS = {"start_date": "20240102", "end_date": "20240105"}
FEATURE_KWARGS: dict[str, dict[str, Any]] = {
    REALTIME_QUOTES: {"codes": TEST_STOCK_CODES},
    FULL_REALTIME_QUOTES: {"codes": TEST_STOCK_CODES},
    INDEX_REALTIME: {"codes": TEST_INDEX_CODES},
    MINUTE_KLINE: {"code": "000001", "period": "5"},
    DAILY_KLINE: DAILY_KLINE_KWARGS,
    TRADE_CALENDAR: TRADE_CALENDAR_KWARGS,
    LITE_REALTIME_QUOTES: {"codes": TEST_STOCK_CODES},
}
AUDIT_TABLES = [
    "source_request_log",
    "source_fallback_trace",
    "source_failure_event",
    "source_health_score",
]
NETWORK_PERMISSION_PATTERNS = ("WinError 10013", "PermissionError", "Access is denied")


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _observation_date() -> str:
    return datetime.now().strftime("%Y%m%d")


def _observation_date_iso() -> str:
    return datetime.now().strftime("%Y-%m-%d")


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, default=str), encoding="utf-8")


def _markdown_table_row(values: list[Any]) -> str:
    return "| " + " | ".join("" if value is None else str(value) for value in values) + " |"


def _status_is_pass(status: Any) -> bool:
    return str(status).upper() == "PASS"


def _dependency_status(package_name: str) -> dict[str, Any]:
    try:
        return {"installed": True, "version": importlib.metadata.version(package_name)}
    except importlib.metadata.PackageNotFoundError:
        return {"installed": False, "version": None}
    except Exception as exc:
        return {"installed": False, "version": None, "error": f"{type(exc).__name__}: {exc}"}


def _trigger_context() -> dict[str, Any]:
    trigger = os.environ.get("STABILITY_WATCH_TRIGGER") or "manual_python"
    scheduled = (
        os.environ.get("STABILITY_WATCH_SCHEDULED_TASK") == "1"
        or trigger == "windows_scheduled_task"
    )
    return {
        "trigger": trigger,
        "scheduled_task_triggered": scheduled,
        "enable_stability_watch": os.environ.get(LIVE_ENV_VAR),
        "runner": "scripts/run_stability_watch_windows.bat"
        if trigger.startswith("windows_")
        else "python",
    }


def _load_schedule_config() -> dict[str, Any]:
    if not SCHEDULE_CONFIG_PATH.exists():
        return {"exists": False, "status": "MISSING"}
    try:
        payload = json.loads(SCHEDULE_CONFIG_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return {"exists": True, "status": "FAIL", "error": f"{type(exc).__name__}: {exc}"}
    if not isinstance(payload, dict):
        return {"exists": True, "status": "FAIL", "error": "schedule config must be a JSON object"}
    return {"exists": True, "status": "PASS", **payload}


def _contains_network_permission_error(text: str) -> bool:
    return any(pattern.lower() in text.lower() for pattern in NETWORK_PERMISSION_PATTERNS)


def _find_network_permission_errors(value: Any, *, path: str = "$") -> list[dict[str, str]]:
    matches: list[dict[str, str]] = []
    if isinstance(value, dict):
        for key, child in value.items():
            if key in {"same_day_previous_runs", "previous_same_day_runs"}:
                continue
            matches.extend(_find_network_permission_errors(child, path=f"{path}.{key}"))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            matches.extend(_find_network_permission_errors(child, path=f"{path}[{index}]"))
    elif isinstance(value, str) and _contains_network_permission_error(value):
        matches.append({"path": path, "text": value[:500]})
    return matches[:20]


def _previous_run_summary(report: dict[str, Any]) -> dict[str, Any]:
    acceptance = report.get("daily_acceptance") or {}
    return {
        "created_at": report.get("created_at"),
        "observation_date": report.get("observation_date"),
        "mode": report.get("mode"),
        "daily_acceptance": acceptance.get("status"),
        "blocking_failures": acceptance.get("blocking_failures") or [],
        "warnings": acceptance.get("warnings") or [],
        "local_network_permission_errors": _find_network_permission_errors(report),
    }


def _load_previous_same_day_report(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return payload if isinstance(payload, dict) else None


def _jsonable_sample(df: pd.DataFrame, limit: int = 5) -> list[dict[str, Any]]:
    if df.empty:
        return []
    return json.loads(df.head(limit).to_json(orient="records", force_ascii=False, date_format="iso"))


def _audit_snapshot() -> dict[str, Any]:
    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    jsonl_path = LOGS_DIR / "source_router.jsonl"
    sqlite_path = LOGS_DIR / "source_router.db"
    jsonl_lines = 0
    if jsonl_path.exists():
        with jsonl_path.open("r", encoding="utf-8") as f:
            jsonl_lines = sum(1 for _ in f)

    table_counts = {table: 0 for table in AUDIT_TABLES}
    sqlite_error = None
    if sqlite_path.exists():
        try:
            with sqlite3.connect(sqlite_path) as conn:
                for table in AUDIT_TABLES:
                    table_counts[table] = int(
                        conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
                    )
        except sqlite3.Error as exc:
            sqlite_error = f"{type(exc).__name__}: {exc}"

    return {
        "jsonl_exists": jsonl_path.exists(),
        "jsonl_bytes": int(jsonl_path.stat().st_size) if jsonl_path.exists() else 0,
        "jsonl_lines": jsonl_lines,
        "sqlite_exists": sqlite_path.exists(),
        "sqlite_tables": table_counts,
        "sqlite_error": sqlite_error,
    }


def _audit_delta(before: dict[str, Any], after: dict[str, Any]) -> dict[str, Any]:
    before_tables = before.get("sqlite_tables", {})
    after_tables = after.get("sqlite_tables", {})
    return {
        "jsonl_written": int(after.get("jsonl_bytes") or 0) > int(before.get("jsonl_bytes") or 0),
        "jsonl_lines_added": int(after.get("jsonl_lines") or 0) - int(before.get("jsonl_lines") or 0),
        "sqlite_written": after_tables.get("source_request_log", 0)
        > before_tables.get("source_request_log", 0),
        "request_rows_added": after_tables.get("source_request_log", 0)
        - before_tables.get("source_request_log", 0),
        "fallback_trace_rows_added": after_tables.get("source_fallback_trace", 0)
        - before_tables.get("source_fallback_trace", 0),
        "failure_event_rows_added": after_tables.get("source_failure_event", 0)
        - before_tables.get("source_failure_event", 0),
        "health_score_rows_added": after_tables.get("source_health_score", 0)
        - before_tables.get("source_health_score", 0),
    }


def _audit_written_status(audit: dict[str, Any]) -> bool:
    delta = audit.get("delta") or {}
    return bool(delta.get("jsonl_written") or delta.get("sqlite_written"))


def _fallback_triggered(trace: list[dict[str, Any]]) -> bool:
    attempted = [item for item in trace if item.get("source") not in {None, "<none>", "cache"}]
    if len(attempted) <= 1:
        return False
    return any(item.get("status") not in {"success", "hit", "cache_hit"} for item in attempted[:-1])


def _codes_present(data: pd.DataFrame, codes: list[str]) -> dict[str, bool]:
    if data.empty or "code" not in data.columns:
        return {code: False for code in codes}
    present = set(data["code"].astype(str).str.extract(r"(\d{6})", expand=False).dropna())
    return {code: code in present for code in codes}


def _source_feature_status(
    smoke_report: dict[str, Any],
    source_name: str,
    feature: str,
) -> dict[str, Any]:
    matches = [
        item
        for item in smoke_report.get("results", [])
        if item.get("source_name") == source_name and item.get("feature") == feature
    ]
    if not matches:
        return {"status": "MISSING", "row_count": 0}
    item = matches[0]
    return {
        "status": item.get("status"),
        "row_count": int(item.get("row_count") or 0),
        "reason": item.get("reason"),
        "warnings": item.get("warnings") or [],
        "audit_written": item.get("audit_written"),
        "jsonl_audit_written": item.get("jsonl_audit_written"),
        "sqlite_audit_written": item.get("sqlite_audit_written"),
    }


def _trade_day_status() -> dict[str, Any]:
    today_iso = _observation_date_iso()
    today_key = today_iso.replace("-", "")
    config = RouterConfig(
        cache_dir=PROJECT_ROOT / ".cache" / "stability_trade_calendar",
        log_dir=LOGS_DIR,
        request_timeout_seconds=20.0,
        enable_cache=False,
        enable_sqlite_audit=True,
    )
    router = MarketRouter(config=config)
    try:
        result = router.fetch_result(TRADE_CALENDAR, start_date=today_key, end_date=today_key)
        data = result.data
        matched = data[data["date"].astype(str).str[:10] == today_iso] if "date" in data.columns else data
        if matched.empty:
            return {
                "status": "PASS",
                "date": today_iso,
                "is_trading_day": False,
                "counted_in_5day": False,
                "source": result.source,
                "row_count": int(len(data)),
                "reason": "today_not_in_trade_calendar_result",
                "fallback_trace": result.fallback_trace,
            }
        is_trading_day = bool(matched["is_trading_day"].astype(bool).iloc[0])
        return {
            "status": "PASS",
            "date": today_iso,
            "is_trading_day": is_trading_day,
            "counted_in_5day": is_trading_day,
            "source": result.source,
            "row_count": int(len(data)),
            "reason": "trade_day" if is_trading_day else "non_trading_day",
            "fallback_trace": result.fallback_trace,
        }
    except AllSourcesFailedError as exc:
        trace = [dict(item) for item in exc.trace]
        errors = _find_network_permission_errors(trace)
        return {
            "status": "FAIL",
            "date": today_iso,
            "is_trading_day": False,
            "counted_in_5day": False,
            "source": None,
            "row_count": 0,
            "reason": "trade_calendar_unavailable",
            "fallback_trace": trace,
            "local_network_permission_error": bool(errors),
            "network_permission_errors": errors,
        }
    except Exception as exc:
        text = f"{type(exc).__name__}: {exc}"
        return {
            "status": "FAIL",
            "date": today_iso,
            "is_trading_day": False,
            "counted_in_5day": False,
            "source": None,
            "row_count": 0,
            "reason": "trade_calendar_exception",
            "error_type": type(exc).__name__,
            "error_message": str(exc),
            "local_network_permission_error": _contains_network_permission_error(text),
        }


def _run_default_chain_checks() -> dict[str, Any]:
    config = RouterConfig(
        cache_dir=PROJECT_ROOT / ".cache" / "stability_watch",
        log_dir=LOGS_DIR,
        request_timeout_seconds=20.0,
        enable_cache=False,
        enable_sqlite_audit=True,
    )
    router = MarketRouter(config=config)
    results: dict[str, Any] = {}
    for feature, kwargs in FEATURE_KWARGS.items():
        started = time.perf_counter()
        try:
            result = router.fetch_result(feature, **kwargs)
            elapsed_ms = (time.perf_counter() - started) * 1000
            results[feature] = {
                "status": "PASS",
                "selected_source": result.source,
                "row_count": int(len(result.data)),
                "elapsed_ms": round(elapsed_ms, 3),
                "router_latency_ms": round(float(result.latency_ms), 3),
                "fallback_triggered": _fallback_triggered(result.fallback_trace),
                "fallback_trace": result.fallback_trace,
                "codes_present": _codes_present(result.data, kwargs.get("codes", [])),
                "sample": _jsonable_sample(result.data),
                "error_type": None,
                "error_message": None,
            }
        except AllSourcesFailedError as exc:
            trace = [dict(item) for item in exc.trace]
            results[feature] = {
                "status": "FAIL",
                "selected_source": None,
                "row_count": 0,
                "elapsed_ms": round((time.perf_counter() - started) * 1000, 3),
                "router_latency_ms": None,
                "fallback_triggered": _fallback_triggered(trace),
                "fallback_trace": trace,
                "codes_present": {},
                "sample": [],
                "error_type": type(exc).__name__,
                "error_message": str(exc),
            }
        except Exception as exc:
            results[feature] = {
                "status": "FAIL",
                "selected_source": None,
                "row_count": 0,
                "elapsed_ms": round((time.perf_counter() - started) * 1000, 3),
                "router_latency_ms": None,
                "fallback_triggered": False,
                "fallback_trace": [],
                "codes_present": {},
                "sample": [],
                "error_type": type(exc).__name__,
                "error_message": str(exc),
            }
    return results


def _run_pytdx_server_pool() -> dict[str, Any]:
    dependency = pytdx_server_pool_refresh._dependency_status()
    active_config = pytdx_server_pool_refresh.load_active_server_pool_config()
    servers = active_config.get("servers") or []
    available = [
        item
        for item in servers
        if item.get("quote_status") == "PASS" and item.get("grade") != "disabled"
    ]
    latencies = [float(item["latency_ms"]) for item in available if item.get("latency_ms") is not None]
    available_count = int(active_config.get("available_server_count") or len(available))
    return {
        "dependency": dependency,
        "active_config_exists": active_config.get("exists"),
        "active_config_status": active_config.get("load_status", "PASS" if active_config.get("exists") else "MISSING"),
        "active_config_generated_at": active_config.get("generated_at"),
        "active_config_path": str(pytdx_server_pool_refresh.ACTIVE_CONFIG_PATH.relative_to(PROJECT_ROOT)),
        "servers": servers,
        "available_server_count": available_count,
        "primary_server": active_config.get("primary_server"),
        "hot_backup_server": active_config.get("hot_backup_server"),
        "fastest_server": active_config.get("primary_server"),
        "avg_latency_ms": round(sum(latencies) / len(latencies), 3) if latencies else None,
        "below_two_servers": available_count < 2,
        "single_server_warning": available_count == 1,
        "server_pool_status": active_config.get("server_pool_status"),
        "server_pool_ready": bool(active_config.get("server_pool_ready")),
        "allow_pytdx_realtime_primary_candidate": bool(dependency.get("installed") and available_count >= 1),
        "zero_pass_fallback_to_easyquotation": available_count == 0,
    }


def _run_official_live_smoke() -> dict[str, Any]:
    results: list[dict[str, Any]] = []
    previous_timeout = live_smoke.LIVE_REQUEST_TIMEOUT_SECONDS
    live_smoke.LIVE_REQUEST_TIMEOUT_SECONDS = WATCH_SOURCE_TIMEOUT_SECONDS
    try:
        for source in live_smoke.LIVE_SOURCE_DEFINITIONS:
            checks = list(live_smoke.REQUIRED_INTERFACE_CHECKS)
            if source["source_name"] in {"pytdx", "mootdx"}:
                checks.extend(live_smoke.OPTIONAL_INTERFACE_CHECKS)
            for feature in checks:
                results.append(live_smoke._run_source_feature(source, feature))
    finally:
        live_smoke.LIVE_REQUEST_TIMEOUT_SECONDS = previous_timeout

    source_summary = live_smoke._source_summary(results)
    interface_summary = live_smoke._interface_summary(results)
    acceptance_decision = live_smoke._live_acceptance_decision(results, {"live_enabled": "PASS"})
    gate_results = {"live_enabled": "PASS", **acceptance_decision["gate_results"]}
    report = {
        "created_at": _utc_now(),
        "mode": "live",
        "live_enabled": True,
        "python": {"executable": sys.executable, "version": sys.version},
        "operating_system": {
            "platform": platform.platform(),
            "system": platform.system(),
            "release": platform.release(),
            "machine": platform.machine(),
        },
        "dependencies": live_smoke._installed_dependencies(),
        "source_summary": source_summary,
        "interface_summary": interface_summary,
        "gate_results": gate_results,
        "live_acceptance_decision": acceptance_decision,
        "allow_task013": acceptance_decision["allow_task013"],
        "allow_task013_1": acceptance_decision["allow_task013_1"],
        "allow_task012_2": acceptance_decision["allow_task012_2"],
        "allow_s0_post_market_readonly_sandbox": acceptance_decision[
            "allow_s0_post_market_readonly_sandbox"
        ],
        "allow_s0_realtime_sandbox": acceptance_decision["allow_s0_realtime_sandbox"],
        "allow_s0_production": acceptance_decision["allow_s0_production"],
        "results": results,
    }
    live_smoke._write_report(report)
    return report


def _run_source_consistency() -> dict[str, Any]:
    report = source_consistency._live_report()
    source_consistency._write_report(report)
    return report


def _remote_disconnected(exc: BaseException) -> bool:
    text = f"{type(exc).__name__}: {exc}"
    return "RemoteDisconnected" in text or "remote end closed connection" in text.lower()


def _run_akshare_daily_endpoint_probe() -> dict[str, Any]:
    status = {
        "hist_status": "SKIP",
        "daily_fallback_status": "SKIP",
        "current_daily_path": "unknown",
        "remote_disconnected": False,
        "errors": [],
    }
    try:
        import akshare as ak  # type: ignore
    except Exception as exc:
        status["errors"].append({"stage": "import", "error_type": type(exc).__name__, "error_message": str(exc)})
        return status

    try:
        hist = ak.stock_zh_a_hist(
            symbol="000001",
            period="daily",
            start_date="20240102",
            end_date="20240102",
            adjust="",
        )
        if hist is not None and not hist.empty:
            status["hist_status"] = "PASS"
            status["current_daily_path"] = "akshare_hist"
            return status
        status["hist_status"] = "FAIL"
        status["errors"].append({"stage": "stock_zh_a_hist", "error_message": "empty_dataframe"})
    except Exception as exc:
        status["hist_status"] = "FAIL"
        status["remote_disconnected"] = _remote_disconnected(exc)
        status["errors"].append({"stage": "stock_zh_a_hist", "error_type": type(exc).__name__, "error_message": str(exc)})

    try:
        df = AkShareAdapter().fetch_daily_kline(**DAILY_KLINE_KWARGS)
        if df is not None and not df.empty:
            status["daily_fallback_status"] = "PASS"
            status["current_daily_path"] = "stock_zh_a_daily_low_frequency_fallback"
        else:
            status["daily_fallback_status"] = "FAIL"
            status["errors"].append({"stage": "adapter_daily_fallback", "error_message": "empty_dataframe"})
    except Exception as exc:
        status["daily_fallback_status"] = "FAIL"
        status["remote_disconnected"] = bool(status["remote_disconnected"] or _remote_disconnected(exc))
        status["errors"].append({"stage": "adapter_daily_fallback", "error_type": type(exc).__name__, "error_message": str(exc)})
    return status


def _run_adata_boundary_probe() -> dict[str, Any]:
    adapter = ADataAdapter()
    result = {
        "supported_features": sorted(adapter.supported_features),
        "full_realtime_direct_call": "UNKNOWN",
        "adata_in_full_policy": "adata" in DEFAULT_SOURCE_POLICY.get(FULL_REALTIME_QUOTES, []),
        "adata_in_realtime_policy": "adata" in DEFAULT_SOURCE_POLICY.get(REALTIME_QUOTES, []),
        "lite_policy_only_adata": DEFAULT_SOURCE_POLICY.get(LITE_REALTIME_QUOTES) == ["adata"],
        "lite_only_boundary_status": "PASS",
    }
    try:
        adapter.fetch_full_realtime_quotes(TEST_STOCK_CODES)
    except UnsupportedFeatureError:
        result["full_realtime_direct_call"] = "UnsupportedFeatureError"
    except Exception as exc:
        result["full_realtime_direct_call"] = f"FAIL_UNEXPECTED_{type(exc).__name__}: {exc}"
    else:
        result["full_realtime_direct_call"] = "FAIL_ALLOWED"

    if (
        result["adata_in_full_policy"]
        or result["adata_in_realtime_policy"]
        or not result["lite_policy_only_adata"]
        or result["full_realtime_direct_call"] != "UnsupportedFeatureError"
    ):
        result["lite_only_boundary_status"] = "FAIL"
    return result


def _source_consistency_summary(report: dict[str, Any]) -> dict[str, Any]:
    warnings: list[dict[str, Any]] = []
    failures: list[dict[str, Any]] = []
    volume_100x_unit_diff = False
    pct_chg_over_threshold = False
    index_volume_unit_diff = False
    for item in report.get("results", []):
        check = str(item.get("check"))
        for issue in item.get("issues", []) or []:
            row = {
                "check": check,
                "severity": issue.get("severity"),
                "code": issue.get("code"),
                "message": issue.get("message"),
                "details": issue.get("details") or {},
            }
            if issue.get("severity") == "FAIL":
                failures.append(row)
            elif issue.get("severity") == "WARN":
                warnings.append(row)
            details = issue.get("details") or {}
            if issue.get("code") == "pct_chg_diff_exceeds_tolerance":
                pct_chg_over_threshold = True
            if details.get("field") == "volume" and issue.get("code") == "unit_scale_inferred":
                scale = float(details.get("right_source_scale_to_left") or 1.0)
                if scale in {0.01, 100.0}:
                    volume_100x_unit_diff = True
                if check == "index_realtime_consistency":
                    index_volume_unit_diff = True
    return {
        "overall_status": report.get("overall_status"),
        "has_fail": bool(failures),
        "warn_count": len(warnings),
        "fail_count": len(failures),
        "volume_100x_unit_diff_present": volume_100x_unit_diff,
        "pct_chg_over_threshold_present": pct_chg_over_threshold,
        "index_volume_unit_diff_present": index_volume_unit_diff,
        "new_fail_present": bool(failures),
        "warnings": warnings[:20],
        "failures": failures[:20],
    }


def _build_source_sections(
    smoke_report: dict[str, Any],
    default_chain: dict[str, Any],
    akshare_probe: dict[str, Any],
    adata_boundary: dict[str, Any],
) -> dict[str, Any]:
    easy_sina_realtime = _source_feature_status(smoke_report, "easyquotation_sina", REALTIME_QUOTES)
    easy_tencent_realtime = _source_feature_status(smoke_report, "easyquotation_tencent", REALTIME_QUOTES)
    easy_sina_full = _source_feature_status(smoke_report, "easyquotation_sina", FULL_REALTIME_QUOTES)
    easy_tencent_full = _source_feature_status(smoke_report, "easyquotation_tencent", FULL_REALTIME_QUOTES)
    easy_sina_index = _source_feature_status(smoke_report, "easyquotation_sina", INDEX_REALTIME)
    easy_tencent_index = _source_feature_status(smoke_report, "easyquotation_tencent", INDEX_REALTIME)

    pytdx_realtime = default_chain.get(REALTIME_QUOTES, {})
    pytdx_full = default_chain.get(FULL_REALTIME_QUOTES, {})
    pytdx_index = default_chain.get(INDEX_REALTIME, {})
    pytdx_minute = default_chain.get(MINUTE_KLINE, {})
    return {
        "pytdx_realtime": {
            "realtime_quotes": {
                "status": pytdx_realtime.get("status"),
                "selected_source": pytdx_realtime.get("selected_source"),
                "codes_present": pytdx_realtime.get("codes_present"),
            },
            "full_realtime_quotes": {
                "status": pytdx_full.get("status"),
                "selected_source": pytdx_full.get("selected_source"),
                "codes_present": pytdx_full.get("codes_present"),
            },
            "index_realtime": {
                "status": pytdx_index.get("status"),
                "selected_source": pytdx_index.get("selected_source"),
                "codes_present": pytdx_index.get("codes_present"),
            },
            "minute_kline": {
                "status": pytdx_minute.get("status"),
                "selected_source": pytdx_minute.get("selected_source"),
                "row_count": pytdx_minute.get("row_count"),
            },
            "fallback_triggered": any(
                bool(default_chain.get(feature, {}).get("fallback_triggered"))
                for feature in [REALTIME_QUOTES, FULL_REALTIME_QUOTES, INDEX_REALTIME]
            ),
        },
        "easyquotation_fallback": {
            "easyquotation_sina": {
                REALTIME_QUOTES: easy_sina_realtime,
                FULL_REALTIME_QUOTES: easy_sina_full,
                INDEX_REALTIME: easy_sina_index,
            },
            "easyquotation_tencent": {
                REALTIME_QUOTES: easy_tencent_realtime,
                FULL_REALTIME_QUOTES: easy_tencent_full,
                INDEX_REALTIME: easy_tencent_index,
            },
            "fallback_ready": any(
                _status_is_pass(item.get("status"))
                for item in [
                    easy_sina_realtime,
                    easy_tencent_realtime,
                    easy_sina_full,
                    easy_tencent_full,
                ]
            ),
        },
        "akshare_post_close": {
            "daily_kline": _source_feature_status(smoke_report, "akshare", DAILY_KLINE),
            "trade_calendar": _source_feature_status(smoke_report, "akshare", TRADE_CALENDAR),
            "daily_endpoint_probe": akshare_probe,
        },
        "baostock_backup": {
            "daily_kline": _source_feature_status(smoke_report, "baostock", DAILY_KLINE),
            "trade_calendar": _source_feature_status(smoke_report, "baostock", TRADE_CALENDAR),
        },
        "adata_lite": {
            "lite_realtime_quotes": _source_feature_status(smoke_report, "adata", LITE_REALTIME_QUOTES),
            "boundary_probe": adata_boundary,
            "strictly_isolated_from_full": adata_boundary.get("lite_only_boundary_status") == "PASS",
        },
    }


def _forbidden_output_audit() -> dict[str, bool]:
    return {
        "candidate_pool_output": False,
        "strategy_signal_output": False,
        "buy_point_output": False,
        "sell_point_output": False,
        "position_output": False,
        "return_output": False,
        "winrate_output": False,
        "trading_plan_output": False,
        "qmt_connected": False,
        "broker_connected": False,
        "auto_order_enabled": False,
        "auto_trading_enabled": False,
        "s0_connected": False,
        "trading_advice_output": False,
    }


def _daily_acceptance(report: dict[str, Any], audit: dict[str, Any]) -> dict[str, Any]:
    blockers: list[str] = []
    warnings: list[str] = []
    smoke_gate = report["official_live_smoke"].get("gate_results", {})
    source_sections = report["source_sections"]
    server_pool = report["pytdx_server_pool"]
    consistency = report["source_consistency"]
    forbidden = report["forbidden_output_audit"]
    local_network = report.get("local_network_permission_error") or {}

    if smoke_gate.get("overall_live_gate") != "PASS":
        blockers.append("overall_live_gate 不是 PASS")
    if int(server_pool.get("available_server_count") or 0) < 1:
        blockers.append("pytdx 可用服务器少于 1 个")
    if server_pool.get("single_server_warning"):
        warnings.append("pytdx 当前只有 1 个可用服务器，必须保留 single_server_warning")
    if server_pool.get("server_pool_ready"):
        warnings.append("pytdx server_pool_ready 已建立，仍需继续 5 日稳定性观察")
    if not source_sections["easyquotation_fallback"].get("fallback_ready"):
        blockers.append("easyquotation fallback 没有任何可用通道")

    ak_daily = source_sections["akshare_post_close"]["daily_kline"]
    bs_daily = source_sections["baostock_backup"]["daily_kline"]
    if not _status_is_pass(ak_daily.get("status")) and not _status_is_pass(bs_daily.get("status")):
        blockers.append("AKShare 与 Baostock daily_kline 同时失败")
    elif not _status_is_pass(ak_daily.get("status")):
        warnings.append("AKShare daily_kline 失败，本日依赖 Baostock backup")

    ak_calendar = source_sections["akshare_post_close"]["trade_calendar"]
    bs_calendar = source_sections["baostock_backup"]["trade_calendar"]
    if not _status_is_pass(ak_calendar.get("status")) or not _status_is_pass(bs_calendar.get("status")):
        blockers.append("trade_calendar 双源未同时可用")
    if consistency.get("has_fail"):
        blockers.append("source consistency 出现 FAIL")
    if not source_sections["adata_lite"].get("strictly_isolated_from_full"):
        blockers.append("adata lite 边界失败或进入 full")

    if not audit["delta"].get("jsonl_written"):
        blockers.append("source_router.jsonl 未写入")
    if not audit["delta"].get("sqlite_written"):
        blockers.append("source_router.db 未写入 source_request_log")
    if int(audit["delta"].get("fallback_trace_rows_added") or 0) <= 0:
        blockers.append("fallback trace 未写入 SQLite")
    if int(audit["delta"].get("health_score_rows_added") or 0) <= 0:
        blockers.append("health score 未写入 SQLite")
    if int(audit["delta"].get("failure_event_rows_added") or 0) > 0:
        warnings.append("本日记录了 failure event，请结合 fallback trace 复核")

    if local_network.get("current_run_present"):
        warnings.append("检测到 local_network_permission_error：需提升联网权限或放行防火墙后重跑")
    if any(forbidden.values()):
        blockers.append("出现禁止输出或禁止接入项")

    return {
        "status": "PASS" if not blockers else "FAIL",
        "blocking_failures": blockers,
        "warnings": warnings,
        "allow_enter_5day_observation": not blockers,
        "allow_independent_project_use": not blockers,
        "allow_s0_production": False,
    }


def _build_warn_fail_lists(report: dict[str, Any]) -> tuple[list[str], list[str]]:
    acceptance = report.get("daily_acceptance") or {}
    warnings = list(acceptance.get("warnings") or [])
    failures = list(acceptance.get("blocking_failures") or [])
    consistency = report.get("source_consistency") or {}
    for item in consistency.get("warnings") or []:
        warnings.append(f"source_consistency WARN: {item.get('check')} {item.get('code')}")
    for item in consistency.get("failures") or []:
        failures.append(f"source_consistency FAIL: {item.get('check')} {item.get('code')}")
    local_network = report.get("local_network_permission_error") or {}
    if local_network.get("present"):
        warnings.append("local_network_permission_error 已记录，若重跑成功仍保留本警告")
    return list(dict.fromkeys(warnings)), list(dict.fromkeys(failures))


def _write_live_markdown(report: dict[str, Any], path: Path) -> None:
    gate = report["official_live_smoke"].get("gate_results", {})
    sections = report["source_sections"]
    consistency = report["source_consistency"]
    audit_delta = report["audit_log"]["delta"]
    acceptance = report["daily_acceptance"]
    pool = report["pytdx_server_pool"]
    rows = [
        f"# STABILITY DAILY {report['observation_date']}",
        "",
        "## 结论",
        "",
        f"- 生成时间：`{report['created_at']}`",
        f"- 是否由定时任务触发：`{report['trigger_context']['scheduled_task_triggered']}`",
        f"- 是否交易日：`{report['trade_day_status']['is_trading_day']}`",
        f"- 是否计入 5 日观察：`{report['counted_in_5day']}`",
        f"- daily_acceptance：`{acceptance['status']}`",
        f"- overall_live_gate：`{gate.get('overall_live_gate')}`",
        f"- source_consistency：`{consistency.get('overall_status')}`",
        f"- 是否允许 S0 正式生产：`{acceptance['allow_s0_production']}`",
        "",
        "## pytdx server pool",
        "",
        "| 可用服务器 | primary | hot_backup | single_server_warning | 状态 |",
        "| ---: | --- | --- | --- | --- |",
        _markdown_table_row(
            [
                pool.get("available_server_count"),
                pool.get("primary_server"),
                pool.get("hot_backup_server"),
                pool.get("single_server_warning"),
                pool.get("server_pool_status"),
            ]
        ),
        "",
        "## 默认链路",
        "",
        "| feature | status | selected_source | row_count | fallback_triggered |",
        "| --- | --- | --- | ---: | --- |",
    ]
    for feature, item in report["default_chain_checks"].items():
        rows.append(
            _markdown_table_row(
                [
                    feature,
                    item.get("status"),
                    item.get("selected_source"),
                    item.get("row_count"),
                    item.get("fallback_triggered"),
                ]
            )
        )
    rows.extend(
        [
            "",
            "## 关键源状态",
            "",
            "| 项目 | 状态 | 说明 |",
            "| --- | --- | --- |",
            _markdown_table_row(
                [
                    "easyquotation fallback",
                    sections["easyquotation_fallback"].get("fallback_ready"),
                    "至少一个通道可用即满足本日 fallback 基础",
                ]
            ),
            _markdown_table_row(
                [
                    "AKShare daily/calendar",
                    f"{sections['akshare_post_close']['daily_kline'].get('status')} / "
                    f"{sections['akshare_post_close']['trade_calendar'].get('status')}",
                    sections["akshare_post_close"]["daily_endpoint_probe"].get("current_daily_path"),
                ]
            ),
            _markdown_table_row(
                [
                    "Baostock backup",
                    f"{sections['baostock_backup']['daily_kline'].get('status')} / "
                    f"{sections['baostock_backup']['trade_calendar'].get('status')}",
                    "盘后 backup",
                ]
            ),
            _markdown_table_row(
                [
                    "adata lite",
                    sections["adata_lite"]["lite_realtime_quotes"].get("status"),
                    f"strictly_isolated={sections['adata_lite'].get('strictly_isolated_from_full')}",
                ]
            ),
            "",
            "## 一致性与审计",
            "",
            "| 项目 | 结果 |",
            "| --- | --- |",
            _markdown_table_row(["source_consistency_overall", consistency.get("overall_status")]),
            _markdown_table_row(["WARN 数", consistency.get("warn_count")]),
            _markdown_table_row(["FAIL 数", consistency.get("fail_count")]),
            _markdown_table_row(["source_router.jsonl 写入", audit_delta.get("jsonl_written")]),
            _markdown_table_row(["source_router.db 写入", audit_delta.get("sqlite_written")]),
            _markdown_table_row(["fallback trace rows added", audit_delta.get("fallback_trace_rows_added")]),
            _markdown_table_row(["failure event rows added", audit_delta.get("failure_event_rows_added")]),
            _markdown_table_row(["health score rows added", audit_delta.get("health_score_rows_added")]),
            "",
            "## 禁止项审计",
            "",
            "- 是否生成候选股池：否",
            "- 是否生成策略信号：否",
            "- 是否生成买点：否",
            "- 是否生成卖点：否",
            "- 是否生成仓位：否",
            "- 是否生成收益率：否",
            "- 是否生成胜率：否",
            "- 是否生成交易计划：否",
            "- 是否接入 QMT：否",
            "- 是否接入券商账户：否",
            "- 是否自动下单：否",
            "- 是否自动交易：否",
            "- 本报告只用于行情源稳定性观察，不构成交易建议。",
        ]
    )
    if report.get("warn_list"):
        rows.extend(["", "## WARN", ""])
        rows.extend(f"- {item}" for item in report["warn_list"])
    if report.get("fail_list"):
        rows.extend(["", "## FAIL", ""])
        rows.extend(f"- {item}" for item in report["fail_list"])
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(rows) + "\n", encoding="utf-8")


def _write_skip_markdown(report: dict[str, Any], path: Path) -> None:
    rows = [
        f"# STABILITY DAILY {report['observation_date']}",
        "",
        "## 结论",
        "",
        f"- 生成时间：`{report['created_at']}`",
        f"- mode：`{report['mode']}`",
        f"- reason：`{report['reason']}`",
        f"- 是否由定时任务触发：`{report['trigger_context']['scheduled_task_triggered']}`",
        f"- 是否交易日：`{report['trade_day_status'].get('is_trading_day')}`",
        f"- 是否计入 5 日观察：`{report['counted_in_5day']}`",
        f"- daily_acceptance：`{report['daily_acceptance']['status']}`",
        f"- 是否允许 S0 正式生产：`{report['daily_acceptance']['allow_s0_production']}`",
        "",
        "## 审计声明",
        "",
        "- SKIP 不计入 5 日观察。",
        "- 未接入 S0、QMT、券商账户或自动交易。",
        "- 未输出候选股池、策略信号、交易计划、买卖点、仓位、收益率或胜率。",
    ]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(rows) + "\n", encoding="utf-8")


def _write_markdown(report: dict[str, Any], path: Path) -> None:
    if report.get("mode") == "live":
        _write_live_markdown(report, path)
    else:
        _write_skip_markdown(report, path)


def _skip_report(
    reason: str,
    *,
    live_enabled: bool,
    trigger_context: dict[str, Any],
    trade_day_status: dict[str, Any] | None = None,
) -> dict[str, Any]:
    trade_day_status = trade_day_status or {
        "status": "SKIP",
        "date": _observation_date_iso(),
        "is_trading_day": False,
        "counted_in_5day": False,
        "reason": reason,
    }
    report = {
        "watch_version": WATCH_VERSION,
        "created_at": _utc_now(),
        "observation_date": _observation_date(),
        "mode": "skip",
        "live_enabled": live_enabled,
        "reason": reason,
        "trigger_context": trigger_context,
        "schedule_config": _load_schedule_config(),
        "trade_day_status": trade_day_status,
        "counted_in_5day": False,
        "dependencies": {
            package: _dependency_status(package)
            for package in ["pytdx", "akshare", "baostock", "easyquotation", "adata"]
        },
        "pytdx_server_pool": _run_pytdx_server_pool(),
        "default_source_policy": DEFAULT_SOURCE_POLICY,
        "daily_acceptance": {
            "status": "SKIP",
            "blocking_failures": [],
            "warnings": [reason],
            "allow_enter_5day_observation": False,
            "allow_independent_project_use": True,
            "allow_s0_production": False,
        },
        "forbidden_output_audit": _forbidden_output_audit(),
        "audit_log_written": False,
    }
    report["local_network_permission_error"] = {
        "present": bool(_find_network_permission_errors(report)),
        "current_run_present": bool(_find_network_permission_errors(report)),
        "classification": "local_network_permission_error"
        if _find_network_permission_errors(report)
        else None,
        "action": "提升联网权限或放行防火墙后重跑" if _find_network_permission_errors(report) else None,
        "matches": _find_network_permission_errors(report),
    }
    report["warn_list"], report["fail_list"] = _build_warn_fail_lists(report)
    return report


def _live_report(trade_day_status: dict[str, Any], trigger_context: dict[str, Any]) -> dict[str, Any]:
    before_audit = _audit_snapshot()
    pytdx_pool = _run_pytdx_server_pool()
    default_chain = _run_default_chain_checks()
    smoke_report = _run_official_live_smoke()
    consistency_report = _run_source_consistency()
    akshare_probe = _run_akshare_daily_endpoint_probe()
    adata_boundary = _run_adata_boundary_probe()
    source_sections = _build_source_sections(smoke_report, default_chain, akshare_probe, adata_boundary)
    after_audit = _audit_snapshot()
    audit = {"before": before_audit, "after": after_audit, "delta": _audit_delta(before_audit, after_audit)}
    report = {
        "watch_version": WATCH_VERSION,
        "created_at": _utc_now(),
        "observation_date": _observation_date(),
        "mode": "live",
        "live_enabled": True,
        "trigger_context": trigger_context,
        "schedule_config": _load_schedule_config(),
        "trade_day_status": trade_day_status,
        "python": {"executable": sys.executable, "version": sys.version},
        "operating_system": {
            "platform": platform.platform(),
            "system": platform.system(),
            "release": platform.release(),
            "machine": platform.machine(),
        },
        "dependencies": {
            package: _dependency_status(package)
            for package in ["pytdx", "akshare", "baostock", "easyquotation", "adata"]
        },
        "default_source_policy": DEFAULT_SOURCE_POLICY,
        "observation_scope": {
            "days_required": 5,
            "test_stock_codes": TEST_STOCK_CODES,
            "test_index_codes": TEST_INDEX_CODES,
            "no_s0": True,
            "no_qmt": True,
            "no_broker": True,
            "no_auto_trading": True,
        },
        "pytdx_server_pool": pytdx_pool,
        "default_chain_checks": default_chain,
        "official_live_smoke": smoke_report,
        "source_consistency_raw": consistency_report,
        "source_consistency": _source_consistency_summary(consistency_report),
        "source_sections": source_sections,
        "audit_log": audit,
        "audit_log_written": _audit_written_status(audit),
        "forbidden_output_audit": _forbidden_output_audit(),
    }
    current_network_errors = _find_network_permission_errors(report)
    report["local_network_permission_error"] = {
        "present": bool(current_network_errors),
        "current_run_present": bool(current_network_errors),
        "previous_same_day_present": False,
        "classification": "local_network_permission_error" if current_network_errors else None,
        "action": "提升联网权限或放行防火墙后重跑" if current_network_errors else None,
        "matches": current_network_errors,
    }
    report["daily_acceptance"] = _daily_acceptance(report, audit)
    report["counted_in_5day"] = bool(
        trade_day_status.get("is_trading_day") and report["daily_acceptance"]["status"] == "PASS"
    )
    report["warn_list"], report["fail_list"] = _build_warn_fail_lists(report)
    return report


def _finalize_with_previous_run(report: dict[str, Any], previous: dict[str, Any] | None) -> dict[str, Any]:
    if previous is None:
        return report
    previous_runs = previous.get("same_day_previous_runs") or []
    if not isinstance(previous_runs, list):
        previous_runs = []
    previous_summary = _previous_run_summary(previous)
    report["same_day_previous_runs"] = [*previous_runs, previous_summary][-5:]
    previous_errors = [
        error
        for run in report["same_day_previous_runs"]
        for error in run.get("local_network_permission_errors", [])
    ]
    if previous_errors:
        local = report.setdefault("local_network_permission_error", {})
        local["present"] = True
        local["previous_same_day_present"] = True
        local["classification"] = "local_network_permission_error"
        local["action"] = "提升联网权限或放行防火墙后重跑；若重跑已成功，保留首次失败记录"
        local["previous_matches"] = previous_errors[:20]
        acceptance = report.get("daily_acceptance") or {}
        warnings = acceptance.setdefault("warnings", [])
        warnings.append("同日早前运行出现 local_network_permission_error，本次结果保留该 WARN")
        report["warn_list"], report["fail_list"] = _build_warn_fail_lists(report)
    return report


def main() -> int:
    observation_date = _observation_date()
    json_path = LOGS_DIR / f"stability_daily_{observation_date}.json"
    md_path = REPORTS_DIR / f"STABILITY_DAILY_{observation_date}.md"
    previous = _load_previous_same_day_report(json_path)
    trigger_context = _trigger_context()
    live_enabled = os.environ.get(LIVE_ENV_VAR) == "1"
    if not live_enabled:
        report = _skip_report(
            f"{LIVE_ENV_VAR} is not 1",
            live_enabled=False,
            trigger_context=trigger_context,
        )
        report = _finalize_with_previous_run(report, previous)
        _write_json(json_path, report)
        _write_markdown(report, md_path)
        print(json.dumps(report, ensure_ascii=False, indent=2, default=str))
        return 1

    trade_day = _trade_day_status()
    if not trade_day.get("is_trading_day"):
        reason = (
            "non_trading_day"
            if trade_day.get("status") == "PASS"
            else "trade_calendar_unavailable_skip_observation"
        )
        report = _skip_report(
            reason,
            live_enabled=True,
            trigger_context=trigger_context,
            trade_day_status=trade_day,
        )
        report = _finalize_with_previous_run(report, previous)
        _write_json(json_path, report)
        _write_markdown(report, md_path)
        print(json.dumps(report, ensure_ascii=False, indent=2, default=str))
        return 0

    report = _live_report(trade_day, trigger_context)
    report = _finalize_with_previous_run(report, previous)
    _write_json(json_path, report)
    _write_markdown(report, md_path)
    print(json.dumps(report, ensure_ascii=False, indent=2, default=str))
    return 0 if report["daily_acceptance"]["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
