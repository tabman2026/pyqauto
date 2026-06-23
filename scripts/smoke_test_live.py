from __future__ import annotations

import importlib
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

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from astock_source_router.core.errors import AllSourcesFailedError  # noqa: E402
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
from astock_source_router.core.policy import SourcePolicy  # noqa: E402
from astock_source_router.core.router import MarketRouter  # noqa: E402
from astock_source_router.core.schema import REQUIRED_COLUMNS  # noqa: E402

LIVE_SOURCE_DEFINITIONS: list[dict[str, Any]] = [
    {
        "label": "pytdx",
        "source_name": "pytdx",
        "package": "pytdx",
        "module": "astock_source_router.adapters.pytdx_adapter",
        "class": "PytdxAdapter",
        "batch": "primary",
        "critical_features": [REALTIME_QUOTES, FULL_REALTIME_QUOTES, INDEX_REALTIME, MINUTE_KLINE],
    },
    {
        "label": "AKShare",
        "source_name": "akshare",
        "package": "akshare",
        "module": "astock_source_router.adapters.akshare_adapter",
        "class": "AkShareAdapter",
        "batch": "primary",
        "critical_features": [DAILY_KLINE, TRADE_CALENDAR, INDEX_REALTIME],
    },
    {
        "label": "Baostock",
        "source_name": "baostock",
        "package": "baostock",
        "module": "astock_source_router.adapters.baostock_adapter",
        "class": "BaostockAdapter",
        "batch": "primary",
        "critical_features": [DAILY_KLINE, TRADE_CALENDAR],
    },
    {
        "label": "easyquotation_sina",
        "source_name": "easyquotation_sina",
        "package": "easyquotation",
        "module": "astock_source_router.adapters.easyquotation_adapter",
        "class": "EasyQuotationAdapter",
        "init_kwargs": {"provider": "sina"},
        "batch": "primary",
        "critical_features": [REALTIME_QUOTES, FULL_REALTIME_QUOTES, INDEX_REALTIME],
    },
    {
        "label": "easyquotation_tencent",
        "source_name": "easyquotation_tencent",
        "package": "easyquotation",
        "module": "astock_source_router.adapters.easyquotation_adapter",
        "class": "EasyQuotationAdapter",
        "init_kwargs": {"provider": "tencent"},
        "batch": "primary",
        "critical_features": [REALTIME_QUOTES, FULL_REALTIME_QUOTES, INDEX_REALTIME],
    },
    {
        "label": "adata",
        "source_name": "adata",
        "package": "adata",
        "module": "astock_source_router.adapters.adata_adapter",
        "class": "ADataAdapter",
        "batch": "primary",
        "critical_features": [LITE_REALTIME_QUOTES],
    },
    {
        "label": "efinance",
        "source_name": "efinance",
        "package": "efinance",
        "module": "astock_source_router.adapters.efinance_adapter",
        "class": "EFinanceAdapter",
        "batch": "optional",
        "critical_features": [],
    },
    {
        "label": "mootdx",
        "source_name": "mootdx",
        "package": "mootdx",
        "module": "astock_source_router.adapters.mootdx_adapter",
        "class": "MootdxAdapter",
        "batch": "optional",
        "critical_features": [],
    },
    {
        "label": "Ashare",
        "source_name": "ashare",
        "package": "Ashare",
        "module": None,
        "class": None,
        "batch": "optional",
        "critical_features": [],
    },
]

REQUIRED_INTERFACE_CHECKS = [
    REALTIME_QUOTES,
    FULL_REALTIME_QUOTES,
    LITE_REALTIME_QUOTES,
    DAILY_KLINE,
    TRADE_CALENDAR,
    INDEX_REALTIME,
]
OPTIONAL_INTERFACE_CHECKS = [MINUTE_KLINE]

FEATURE_KWARGS: dict[str, dict[str, Any]] = {
    REALTIME_QUOTES: {"codes": ["000001", "600519"]},
    FULL_REALTIME_QUOTES: {"codes": ["000001", "600519"]},
    LITE_REALTIME_QUOTES: {"codes": ["000001", "600519"]},
    DAILY_KLINE: {"code": "000001", "start_date": "20240102", "end_date": "20240102"},
    TRADE_CALENDAR: {"start_date": "20240102", "end_date": "20240105"},
    INDEX_REALTIME: {"codes": ["000001", "399001", "399006", "000300"]},
    MINUTE_KLINE: {"code": "000001", "period": "5"},
}

POST_MARKET_ACCEPTANCE_RULES: dict[str, int] = {
    DAILY_KLINE: 2,
    TRADE_CALENDAR: 2,
}

REALTIME_GATE_RULES: dict[str, dict[str, list[str]]] = {
    REALTIME_QUOTES: {
        "primary": ["pytdx"],
        "backup": ["easyquotation_sina", "easyquotation_tencent"],
    },
    FULL_REALTIME_QUOTES: {
        "primary": ["pytdx"],
        "backup": ["easyquotation_sina", "easyquotation_tencent"],
    },
    INDEX_REALTIME: {
        "primary": ["pytdx"],
        "backup": ["easyquotation_sina", "easyquotation_tencent", "akshare"],
    },
}

LIVE_MIN_INTERVAL_SECONDS = 1.0
LIVE_REQUEST_TIMEOUT_SECONDS = 20.0
_LAST_SOURCE_CALL_AT: dict[str, float] = {}


def _write_report(report: dict[str, Any]) -> None:
    logs_dir = Path("logs")
    logs_dir.mkdir(parents=True, exist_ok=True)
    (logs_dir / "smoke_test_report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2, default=str),
        encoding="utf-8",
    )


def _dependency_status(package_name: str) -> dict[str, Any]:
    try:
        return {"installed": True, "version": importlib.metadata.version(package_name)}
    except importlib.metadata.PackageNotFoundError:
        return {"installed": False, "version": None}
    except Exception as exc:
        return {"installed": False, "version": None, "error": f"{type(exc).__name__}: {exc}"}


def _installed_dependencies() -> dict[str, dict[str, Any]]:
    packages = ["pytdx", "akshare", "baostock", "easyquotation", "adata", "efinance", "mootdx", "Ashare"]
    return {package: _dependency_status(package) for package in packages}


def _audit_snapshot() -> dict[str, int]:
    logs_dir = Path("logs")
    jsonl_path = logs_dir / "source_router.jsonl"
    sqlite_path = logs_dir / "source_router.db"
    sqlite_rows = 0
    if sqlite_path.exists():
        try:
            with sqlite3.connect(sqlite_path) as conn:
                sqlite_rows = int(conn.execute("SELECT COUNT(*) FROM source_request_log").fetchone()[0])
        except sqlite3.Error:
            sqlite_rows = -1
    return {
        "jsonl_bytes": int(jsonl_path.stat().st_size) if jsonl_path.exists() else 0,
        "sqlite_request_rows": sqlite_rows,
    }


def _audit_delta(before: dict[str, int], after: dict[str, int]) -> dict[str, bool]:
    jsonl_written = after["jsonl_bytes"] > before["jsonl_bytes"]
    sqlite_written = (
        before["sqlite_request_rows"] >= 0
        and after["sqlite_request_rows"] > before["sqlite_request_rows"]
    )
    return {
        "audit_written": bool(jsonl_written or sqlite_written),
        "jsonl_audit_written": bool(jsonl_written),
        "sqlite_audit_written": bool(sqlite_written),
    }


def _fallback_triggered(trace: list[dict[str, Any]]) -> bool:
    attempted = [item for item in trace if item.get("source") not in {None, "<none>", "cache"}]
    if len(attempted) <= 1:
        return False
    return any(item.get("status") not in {"success", "hit", "cache_hit"} for item in attempted[:-1])


def _circuit_breaker_triggered(trace: list[dict[str, Any]]) -> bool:
    return any(item.get("status") == "circuit_open" for item in trace)


def _missing_fields(feature: str, columns: list[str]) -> list[str]:
    expected = REQUIRED_COLUMNS.get(feature, [])
    return [column for column in expected if column not in columns]


def _skip_result(source: dict[str, Any], feature: str, reason: str, *, critical: bool) -> dict[str, Any]:
    return {
        "source": source["label"],
        "source_name": source["source_name"],
        "batch": source["batch"],
        "feature": feature,
        "critical": critical,
        "status": "SKIP",
        "row_count": 0,
        "reason": reason,
        "missing_fields": [],
        "warnings": [],
        "response_time_ms": None,
        "router_latency_ms": None,
        "fallback_triggered": False,
        "circuit_breaker_triggered": False,
        "audit_written": False,
        "jsonl_audit_written": False,
        "sqlite_audit_written": False,
        "fallback_trace": [],
        "params": FEATURE_KWARGS.get(feature, {}),
    }


def _fail_result(
    source: dict[str, Any],
    feature: str,
    reason: str,
    *,
    critical: bool,
    started_at: float,
    trace: list[dict[str, Any]] | None = None,
    audit_delta: dict[str, bool] | None = None,
    missing_fields: list[str] | None = None,
    warnings: list[str] | None = None,
) -> dict[str, Any]:
    trace = trace or []
    audit_delta = audit_delta or {
        "audit_written": False,
        "jsonl_audit_written": False,
        "sqlite_audit_written": False,
    }
    return {
        "source": source["label"],
        "source_name": source["source_name"],
        "batch": source["batch"],
        "feature": feature,
        "critical": critical,
        "status": "FAIL",
        "row_count": 0,
        "reason": reason,
        "missing_fields": missing_fields or [],
        "warnings": warnings or [],
        "response_time_ms": round((time.perf_counter() - started_at) * 1000, 3),
        "router_latency_ms": None,
        "fallback_triggered": _fallback_triggered(trace),
        "circuit_breaker_triggered": _circuit_breaker_triggered(trace),
        **audit_delta,
        "fallback_trace": trace,
        "params": FEATURE_KWARGS.get(feature, {}),
    }


def _wait_for_source(source_name: str) -> None:
    now = time.perf_counter()
    last = _LAST_SOURCE_CALL_AT.get(source_name)
    if last is not None:
        remaining = LIVE_MIN_INTERVAL_SECONDS - (now - last)
        if remaining > 0:
            time.sleep(remaining)
    _LAST_SOURCE_CALL_AT[source_name] = time.perf_counter()


def _load_adapter(source: dict[str, Any]) -> tuple[Any | None, str | None, bool]:
    if source["module"] is None or source["class"] is None:
        return None, "adapter_not_implemented", True
    package = str(source["package"])
    package_status = _dependency_status(package)
    if not package_status["installed"]:
        return None, f"dependency_not_installed: {package}", True
    try:
        module = importlib.import_module(str(source["module"]))
        adapter_cls = getattr(module, str(source["class"]))
        init_kwargs = dict(source.get("init_kwargs") or {})
        return adapter_cls(**init_kwargs), None, False
    except ModuleNotFoundError as exc:
        return None, f"ModuleNotFoundError: {exc}", True
    except Exception as exc:
        return None, f"{type(exc).__name__}: {exc}", False


def _run_router_check(source: dict[str, Any], feature: str, adapter: Any, *, critical: bool) -> dict[str, Any]:
    started_at = time.perf_counter()
    before_audit = _audit_snapshot()
    _wait_for_source(str(source["source_name"]))
    try:
        config = RouterConfig(
            cache_dir=Path(".cache/smoke_live"),
            log_dir=Path("logs"),
            request_timeout_seconds=LIVE_REQUEST_TIMEOUT_SECONDS,
            enable_cache=False,
            enable_sqlite_audit=True,
            min_interval_seconds={str(source["source_name"]): LIVE_MIN_INTERVAL_SECONDS},
        )
        policy = SourcePolicy({feature: [str(source["source_name"])]})
        router = MarketRouter(config=config, source_policy=policy, adapters=[adapter], auto_register=False)
        result = router.fetch_result(feature, **FEATURE_KWARGS[feature])
        after_audit = _audit_snapshot()
        trace = result.fallback_trace
        missing = _missing_fields(feature, list(result.data.columns))
        warnings = []
        for item in trace:
            warnings.extend(item.get("warnings", []) or [])
        return {
            "source": source["label"],
            "source_name": source["source_name"],
            "batch": source["batch"],
            "feature": feature,
            "critical": critical,
            "status": "PASS",
            "row_count": int(len(result.data)),
            "reason": "live_source_ok",
            "missing_fields": missing,
            "warnings": list(dict.fromkeys(warnings)),
            "response_time_ms": round((time.perf_counter() - started_at) * 1000, 3),
            "router_latency_ms": round(float(result.latency_ms), 3),
            "fallback_triggered": _fallback_triggered(trace),
            "circuit_breaker_triggered": _circuit_breaker_triggered(trace),
            **_audit_delta(before_audit, after_audit),
            "fallback_trace": trace,
            "params": FEATURE_KWARGS[feature],
        }
    except AllSourcesFailedError as exc:
        after_audit = _audit_snapshot()
        trace = [dict(item) for item in exc.trace]
        warnings = []
        missing: list[str] = []
        for item in trace:
            warnings.extend(item.get("warnings", []) or [])
            missing.extend(item.get("missing_fields", []) or [])
        error_types = [str(item.get("error_type")) for item in trace if item.get("error_type")]
        if any(error_type == "UnsupportedFeatureError" for error_type in error_types):
            return {
                **_skip_result(
                    source,
                    feature,
                    f"UnsupportedFeatureError: {trace[-1].get('error_message')}",
                    critical=critical,
                ),
                **_audit_delta(before_audit, after_audit),
                "response_time_ms": round((time.perf_counter() - started_at) * 1000, 3),
                "fallback_trace": trace,
            }
        return _fail_result(
            source,
            feature,
            f"AllSourcesFailedError: {exc}",
            critical=critical,
            started_at=started_at,
            trace=trace,
            audit_delta=_audit_delta(before_audit, after_audit),
            missing_fields=list(dict.fromkeys(missing)),
            warnings=list(dict.fromkeys(warnings)),
        )
    except Exception as exc:
        after_audit = _audit_snapshot()
        return _fail_result(
            source,
            feature,
            f"{type(exc).__name__}: {exc}",
            critical=critical,
            started_at=started_at,
            audit_delta=_audit_delta(before_audit, after_audit),
        )


def _run_source_feature(source: dict[str, Any], feature: str) -> dict[str, Any]:
    critical = feature in source.get("critical_features", [])
    adapter, reason, is_skip = _load_adapter(source)
    if adapter is None:
        if is_skip:
            return _skip_result(source, feature, reason or "adapter_unavailable", critical=critical)
        return _fail_result(
            source,
            feature,
            reason or "adapter_load_failed",
            critical=critical,
            started_at=time.perf_counter(),
        )
    if feature not in getattr(adapter, "supported_features", set()):
        return _skip_result(source, feature, "unsupported_feature_by_adapter", critical=critical)
    return _run_router_check(source, feature, adapter, critical=critical)


def _source_summary(results: list[dict[str, Any]]) -> list[dict[str, Any]]:
    summary = []
    for source in LIVE_SOURCE_DEFINITIONS:
        source_results = [item for item in results if item["source_name"] == source["source_name"]]
        critical_results = [item for item in source_results if item.get("critical")]
        decisive = critical_results or [item for item in source_results if item["status"] != "SKIP"] or source_results
        statuses = [item["status"] for item in decisive]
        if any(status == "FAIL" for status in statuses):
            status = "FAIL"
        elif any(status == "PASS" for status in statuses):
            status = "PASS"
        else:
            status = "SKIP"
        summary.append(
            {
                "source": source["label"],
                "source_name": source["source_name"],
                "batch": source["batch"],
                "status": status,
                "critical_features": source["critical_features"],
                "pass_count": sum(item["status"] == "PASS" for item in source_results),
                "fail_count": sum(item["status"] == "FAIL" for item in source_results),
                "skip_count": sum(item["status"] == "SKIP" for item in source_results),
                "reasons": [
                    item["reason"]
                    for item in source_results
                    if item["status"] in {"FAIL", "SKIP"}
                ],
            }
        )
    return summary


def _interface_summary(results: list[dict[str, Any]]) -> list[dict[str, Any]]:
    summary = []
    for feature in REQUIRED_INTERFACE_CHECKS + OPTIONAL_INTERFACE_CHECKS:
        feature_results = [item for item in results if item["feature"] == feature]
        statuses = [item["status"] for item in feature_results]
        if any(status == "PASS" for status in statuses):
            status = "PASS"
        elif any(status == "FAIL" for status in statuses):
            status = "FAIL"
        else:
            status = "SKIP"
        summary.append(
            {
                "feature": feature,
                "status": status,
                "pass_count": sum(item["status"] == "PASS" for item in feature_results),
                "fail_count": sum(item["status"] == "FAIL" for item in feature_results),
                "skip_count": sum(item["status"] == "SKIP" for item in feature_results),
                "total_row_count": sum(int(item.get("row_count") or 0) for item in feature_results),
            }
        )
    return summary


def _passed_sources(results: list[dict[str, Any]], feature: str, candidates: list[str] | None = None) -> list[str]:
    candidate_set = set(candidates) if candidates is not None else None
    passed: list[str] = []
    for item in results:
        source_name = str(item["source_name"])
        if item["feature"] != feature or item["status"] != "PASS":
            continue
        if candidate_set is not None and source_name not in candidate_set:
            continue
        if source_name not in passed:
            passed.append(source_name)
    return passed


def _post_market_acceptance(results: list[dict[str, Any]]) -> dict[str, Any]:
    features: dict[str, Any] = {}
    for feature, minimum_pass_count in POST_MARKET_ACCEPTANCE_RULES.items():
        pass_sources = _passed_sources(results, feature)
        features[feature] = {
            "required_pass_count": minimum_pass_count,
            "pass_count": len(pass_sources),
            "pass_sources": pass_sources,
            "status": "PASS" if len(pass_sources) >= minimum_pass_count else "FAIL",
        }
    return {
        "status": "PASS" if all(item["status"] == "PASS" for item in features.values()) else "FAIL",
        "features": features,
    }


def _primary_backup_gate(
    results: list[dict[str, Any]],
    feature: str,
    *,
    allow_backup_only: bool = False,
    backup_only_min_pass_count: int = 2,
) -> dict[str, Any]:
    rule = REALTIME_GATE_RULES[feature]
    primary_pass_sources = _passed_sources(results, feature, rule["primary"])
    backup_pass_sources = _passed_sources(results, feature, rule["backup"])
    primary_path_pass = bool(primary_pass_sources) and bool(backup_pass_sources)
    backup_only_pass = allow_backup_only and len(backup_pass_sources) >= backup_only_min_pass_count
    feature_pass = primary_path_pass or backup_only_pass
    return {
        "feature": feature,
        "required_primary_pass_count": 1,
        "required_backup_pass_count": 1,
        "backup_only_min_pass_count": backup_only_min_pass_count if allow_backup_only else None,
        "primary_sources": rule["primary"],
        "backup_sources": rule["backup"],
        "primary_pass_count": len(primary_pass_sources),
        "backup_pass_count": len(backup_pass_sources),
        "primary_pass_sources": primary_pass_sources,
        "backup_pass_sources": backup_pass_sources,
        "primary_path_pass": primary_path_pass,
        "backup_only_pass": backup_only_pass,
        "status": "PASS" if feature_pass else "FAIL",
    }


def _realtime_acceptance(results: list[dict[str, Any]]) -> dict[str, Any]:
    feature_gates = [
        _primary_backup_gate(results, REALTIME_QUOTES),
        _primary_backup_gate(results, FULL_REALTIME_QUOTES),
    ]
    return {
        "status": "PASS" if all(item["status"] == "PASS" for item in feature_gates) else "FAIL",
        "features": feature_gates,
    }


def _index_realtime_acceptance(results: list[dict[str, Any]]) -> dict[str, Any]:
    return _primary_backup_gate(
        results,
        INDEX_REALTIME,
        allow_backup_only=True,
        backup_only_min_pass_count=2,
    )


def _minute_acceptance(results: list[dict[str, Any]]) -> dict[str, Any]:
    pass_sources = _passed_sources(results, MINUTE_KLINE, ["pytdx"])
    status = "PASS" if pass_sources else "NON_BLOCKING_WARN"
    return {
        "feature": MINUTE_KLINE,
        "primary_sources": ["pytdx"],
        "primary_pass_sources": pass_sources,
        "status": status,
        "blocking": False,
    }


def _live_acceptance_decision(results: list[dict[str, Any]], gate_results: dict[str, str]) -> dict[str, Any]:
    post_market = _post_market_acceptance(results)
    realtime_gate = _realtime_acceptance(results)
    index_realtime_gate = _index_realtime_acceptance(results)
    minute_gate = _minute_acceptance(results)
    live_enabled_pass = all(status == "PASS" for status in gate_results.values())
    post_close_pass = live_enabled_pass and post_market["status"] == "PASS"
    realtime_pass = live_enabled_pass and realtime_gate["status"] == "PASS"
    index_realtime_pass = live_enabled_pass and index_realtime_gate["status"] == "PASS"
    overall_pass = post_close_pass and realtime_pass and index_realtime_pass
    computed_gate_results = {
        "post_close_gate": "PASS" if post_close_pass else "FAIL",
        "realtime_gate": "PASS" if realtime_pass else "FAIL",
        "index_realtime_gate": "PASS" if index_realtime_pass else "FAIL",
        "minute_gate": minute_gate["status"],
        "overall_live_gate": "PASS" if overall_pass else "FAIL",
    }

    if overall_pass:
        verdict = "PASS"
        verdict_cn = "通过"
        allow_task013 = True
        allow_task013_1 = True
        allow_task012_2 = False
        allow_s0_post_market = "allowed"
        allow_s0_realtime = True
        allow_s0_production = False
        reasons = ["盘后、pytdx 实时主源、easyquotation 备用源和指数实时链路均满足任务013.1验收规则；S0 正式生产仍禁止。"]
    elif post_close_pass:
        verdict = "PARTIAL_PASS"
        verdict_cn = "部分通过"
        allow_task013 = False
        allow_task013_1 = False
        allow_task012_2 = True
        allow_s0_post_market = "conditional"
        allow_s0_realtime = False
        allow_s0_production = False
        reasons = ["盘后链路满足验收规则；pytdx 实时主源或实时备用源不足，不能完成任务013.1实时切换。"]
    elif realtime_pass and index_realtime_pass:
        verdict = "PARTIAL_PASS"
        verdict_cn = "部分通过"
        allow_task013 = False
        allow_task013_1 = False
        allow_task012_2 = True
        allow_s0_post_market = "denied"
        allow_s0_realtime = False
        allow_s0_production = False
        reasons = ["实时股票和指数实时链路满足规则；盘后链路未满足 AKShare + Baostock 双源要求。"]
    else:
        verdict = "FAIL"
        verdict_cn = "未通过"
        allow_task013 = False
        allow_task013_1 = False
        allow_task012_2 = live_enabled_pass
        allow_s0_post_market = "denied"
        allow_s0_realtime = False
        allow_s0_production = False
        reasons = ["盘后、pytdx 实时主源、实时备用源或指数实时链路未满足任务013.1验收规则；禁止任何 S0 正式接入。"]
    return {
        "verdict": verdict,
        "verdict_cn": verdict_cn,
        "post_market": post_market,
        "realtime_gate": realtime_gate,
        "index_realtime_gate": index_realtime_gate,
        "minute_gate": minute_gate,
        "gate_results": computed_gate_results,
        "post_close_gate": computed_gate_results["post_close_gate"],
        "overall_live_gate": computed_gate_results["overall_live_gate"],
        "allow_task013": allow_task013,
        "allow_task013_1": allow_task013_1,
        "allow_task012_2": allow_task012_2,
        "allow_s0_post_market_readonly_sandbox": allow_s0_post_market,
        "allow_s0_realtime_sandbox": allow_s0_realtime,
        "allow_s0_production": allow_s0_production,
        "reasons": reasons,
    }


def main() -> int:
    live_enabled = os.environ.get("ENABLE_LIVE_SMOKE_TEST") == "1"
    results: list[dict[str, Any]] = []
    if live_enabled:
        for source in LIVE_SOURCE_DEFINITIONS:
            checks = list(REQUIRED_INTERFACE_CHECKS)
            if source["source_name"] in {"pytdx", "mootdx"}:
                checks.extend(OPTIONAL_INTERFACE_CHECKS)
            for feature in checks:
                results.append(_run_source_feature(source, feature))
    else:
        for source in LIVE_SOURCE_DEFINITIONS:
            for feature in REQUIRED_INTERFACE_CHECKS:
                results.append(
                    _skip_result(
                        source,
                        feature,
                        "ENABLE_LIVE_SMOKE_TEST is not 1",
                        critical=feature in source.get("critical_features", []),
                    )
                )

    source_summary = _source_summary(results)
    interface_summary = _interface_summary(results)
    gate_results = {"live_enabled": "PASS" if live_enabled else "FAIL"}
    acceptance_decision = _live_acceptance_decision(results, gate_results)
    gate_results = {**gate_results, **acceptance_decision["gate_results"]}
    report = {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "mode": "live",
        "live_enabled": live_enabled,
        "python": {
            "executable": sys.executable,
            "version": sys.version,
        },
        "operating_system": {
            "platform": platform.platform(),
            "system": platform.system(),
            "release": platform.release(),
            "machine": platform.machine(),
        },
        "dependencies": _installed_dependencies(),
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
    _write_report(report)
    print(json.dumps(report, ensure_ascii=False, indent=2, default=str))
    return 0 if live_enabled and acceptance_decision["allow_task013"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
