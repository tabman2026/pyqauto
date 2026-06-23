from __future__ import annotations

import importlib
import importlib.metadata
import json
import platform
import sys
import time
import traceback
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from concurrent.futures import TimeoutError as FutureTimeoutError
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from astock_source_router.adapters.efinance_adapter import EFinanceAdapter  # noqa: E402
from astock_source_router.adapters.mootdx_adapter import MootdxAdapter  # noqa: E402
from astock_source_router.core.errors import AllSourcesFailedError  # noqa: E402
from astock_source_router.core.features import (  # noqa: E402
    DAILY_KLINE,
    INDEX_REALTIME,
    MINUTE_KLINE,
    REALTIME_QUOTES,
)
from astock_source_router.core.models import RouterConfig  # noqa: E402
from astock_source_router.core.policy import SourcePolicy  # noqa: E402
from astock_source_router.core.router import MarketRouter  # noqa: E402

JSON_REPORT_PATH = PROJECT_ROOT / "logs" / "optional_sources_live_report.json"
MD_REPORT_PATH = PROJECT_ROOT / "OPTIONAL_BACKUP_SOURCE_REPORT.md"

STOCK_CODES = ["000001", "600519"]
INDEX_CODES = ["000001", "399001"]


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _dependency_status(package_name: str) -> dict[str, Any]:
    try:
        return {"installed": True, "version": importlib.metadata.version(package_name)}
    except importlib.metadata.PackageNotFoundError:
        return {"installed": False, "version": None}
    except Exception as exc:
        return {"installed": False, "version": None, "error": f"{type(exc).__name__}: {exc}"}


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


def _run_router_case(source: str, adapter: Any, feature: str, params: dict[str, Any], api: str) -> dict[str, Any]:
    config = RouterConfig(
        cache_dir=PROJECT_ROOT / ".cache" / "optional_sources_live",
        log_dir=PROJECT_ROOT / "logs",
        request_timeout_seconds=20.0,
        enable_cache=False,
        enable_sqlite_audit=True,
        min_interval_seconds={adapter.name: 1.0},
    )
    router = MarketRouter(
        config=config,
        source_policy=SourcePolicy({feature: [adapter.name]}),
        adapters=[adapter],
        auto_register=False,
    )
    started_at = time.perf_counter()
    try:
        result = router.fetch_result(feature, **params)
        duration_ms = round((time.perf_counter() - started_at) * 1000, 3)
        warnings: list[str] = []
        missing_fields: list[str] = []
        for item in result.fallback_trace:
            warnings.extend(item.get("warnings", []) or [])
            missing_fields.extend(item.get("missing_fields", []) or [])
        return {
            "source": source,
            "source_name": adapter.name,
            "feature": feature,
            "api": api,
            "params": params,
            "status": "PASS",
            "reason": "router_quality_gate_pass",
            "quality_gate_status": "PASS",
            "duration_ms": duration_ms,
            "router_latency_ms": round(float(result.latency_ms), 3),
            "missing_fields": list(dict.fromkeys(missing_fields)),
            "warnings": list(dict.fromkeys(warnings)),
            "fallback_trace": result.fallback_trace,
            "can_be_daily_kline_backup": feature == DAILY_KLINE,
            "can_be_realtime_quotes_backup": feature == REALTIME_QUOTES,
            "can_be_index_realtime_backup": feature == INDEX_REALTIME,
            **_dataframe_payload(result.data),
        }
    except AllSourcesFailedError as exc:
        trace = [dict(item) for item in exc.trace]
        warnings: list[str] = []
        missing_fields: list[str] = []
        error_types: list[str] = []
        for item in trace:
            warnings.extend(item.get("warnings", []) or [])
            missing_fields.extend(item.get("missing_fields", []) or [])
            if item.get("error_type"):
                error_types.append(str(item["error_type"]))
        status = "SKIP" if "UnsupportedFeatureError" in error_types else "FAIL"
        return {
            "source": source,
            "source_name": adapter.name,
            "feature": feature,
            "api": api,
            "params": params,
            "status": status,
            "reason": "unsupported_feature" if status == "SKIP" else "router_quality_gate_fail",
            "quality_gate_status": status,
            "duration_ms": round((time.perf_counter() - started_at) * 1000, 3),
            "missing_fields": list(dict.fromkeys(missing_fields)),
            "warnings": list(dict.fromkeys(warnings)),
            "fallback_trace": trace,
            "can_be_daily_kline_backup": False,
            "can_be_realtime_quotes_backup": False,
            "can_be_index_realtime_backup": False,
            "shape": [0, 0],
            "columns": [],
            "head": [],
            "tail": [],
            "head_text": "",
            "tail_text": "",
        }
    except Exception as exc:
        return {
            "source": source,
            "source_name": getattr(adapter, "name", source),
            "feature": feature,
            "api": api,
            "params": params,
            "status": "FAIL",
            "reason": "router_exception",
            "quality_gate_status": "FAIL",
            "duration_ms": round((time.perf_counter() - started_at) * 1000, 3),
            "missing_fields": [],
            "warnings": [],
            "fallback_trace": [],
            "can_be_daily_kline_backup": False,
            "can_be_realtime_quotes_backup": False,
            "can_be_index_realtime_backup": False,
            "shape": [0, 0],
            "columns": [],
            "head": [],
            "tail": [],
            "head_text": "",
            "tail_text": "",
            "error": _exception_payload(exc),
        }


def _skip_case(source: str, feature: str, api: str, reason: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
    return {
        "source": source,
        "source_name": source,
        "feature": feature,
        "api": api,
        "params": params or {},
        "status": "SKIP",
        "reason": reason,
        "quality_gate_status": "SKIP",
        "duration_ms": None,
        "missing_fields": [],
        "warnings": [],
        "fallback_trace": [],
        "can_be_daily_kline_backup": False,
        "can_be_realtime_quotes_backup": False,
        "can_be_index_realtime_backup": False,
        "shape": [0, 0],
        "columns": [],
        "head": [],
        "tail": [],
        "head_text": "",
        "tail_text": "",
    }


def _run_callable_with_timeout(call: Callable[[], Any], timeout_seconds: float = 20.0) -> tuple[Any | None, BaseException | None]:
    executor = ThreadPoolExecutor(max_workers=1)
    future = executor.submit(call)
    try:
        return future.result(timeout=timeout_seconds), None
    except FutureTimeoutError:
        future.cancel()
        return None, TimeoutError(f"raw call timed out after {timeout_seconds} seconds")
    except Exception as exc:
        return None, exc
    finally:
        executor.shutdown(wait=False, cancel_futures=True)


def _run_raw_case(source: str, feature: str, api: str, params: dict[str, Any], call: Callable[[], Any]) -> dict[str, Any]:
    started_at = time.perf_counter()
    data, error = _run_callable_with_timeout(call)
    duration_ms = round((time.perf_counter() - started_at) * 1000, 3)
    if error is not None:
        return {
            **_skip_case(source, feature, api, f"raw_exception:{type(error).__name__}", params),
            "status": "FAIL",
            "quality_gate_status": "SKIP",
            "duration_ms": duration_ms,
            "error": _exception_payload(error),
        }
    df = data if isinstance(data, pd.DataFrame) else pd.DataFrame(data)
    status = "PASS" if not df.empty else "FAIL"
    return {
        "source": source,
        "source_name": source,
        "feature": feature,
        "api": api,
        "params": params,
        "status": status,
        "reason": "raw_non_empty_no_adapter_gate" if status == "PASS" else "raw_empty_no_adapter_gate",
        "quality_gate_status": "SKIP",
        "duration_ms": duration_ms,
        "missing_fields": [],
        "warnings": [] if status == "PASS" else ["empty_dataframe"],
        "fallback_trace": [],
        "can_be_daily_kline_backup": False,
        "can_be_realtime_quotes_backup": False,
        "can_be_index_realtime_backup": False,
        **_dataframe_payload(df),
    }


def _run_efinance_cases() -> list[dict[str, Any]]:
    adapter = EFinanceAdapter()
    cases = [
        (
            DAILY_KLINE,
            {"code": "000001", "start_date": "20240102", "end_date": "20240105"},
            "efinance.stock.get_quote_history",
        ),
        (
            DAILY_KLINE,
            {"code": "600519", "start_date": "20240102", "end_date": "20240105"},
            "efinance.stock.get_quote_history",
        ),
        (
            REALTIME_QUOTES,
            {"codes": STOCK_CODES},
            "efinance.stock.get_latest_quote",
        ),
        (
            INDEX_REALTIME,
            {"codes": INDEX_CODES},
            "efinance.stock.get_realtime_quotes('沪深系列指数')",
        ),
    ]
    results = []
    for feature, params, api in cases:
        results.append(_run_router_case("efinance", adapter, feature, params, api))
        time.sleep(1.0)
    return results


def _run_ashare_cases() -> list[dict[str, Any]]:
    module = None
    for module_name in ["Ashare", "ashare"]:
        try:
            module = importlib.import_module(module_name)
            break
        except Exception:
            continue
    if module is None:
        reason = "dependency_not_installed_or_unavailable: Ashare/ashare"
        return [
            _skip_case("ashare", DAILY_KLINE, "Ashare import", reason, {"code": "000001"}),
            _skip_case("ashare", DAILY_KLINE, "Ashare import", reason, {"code": "600519"}),
            _skip_case("ashare", REALTIME_QUOTES, "Ashare import", reason, {"codes": STOCK_CODES}),
            _skip_case("ashare", MINUTE_KLINE, "Ashare import", reason, {"code": "000001"}),
            _skip_case("ashare", INDEX_REALTIME, "Ashare import", reason, {"codes": INDEX_CODES}),
        ]

    if not hasattr(module, "get_price"):
        reason = "installed_but_known_get_price_api_missing"
        return [
            _skip_case("ashare", DAILY_KLINE, "Ashare.get_price", reason, {"code": "000001"}),
            _skip_case("ashare", DAILY_KLINE, "Ashare.get_price", reason, {"code": "600519"}),
            _skip_case("ashare", REALTIME_QUOTES, "Ashare realtime", "realtime_api_not_confirmed", {"codes": STOCK_CODES}),
            _skip_case("ashare", MINUTE_KLINE, "Ashare.get_price", reason, {"code": "000001"}),
            _skip_case("ashare", INDEX_REALTIME, "Ashare index realtime", "index_realtime_api_not_confirmed", {"codes": INDEX_CODES}),
        ]

    get_price = module.get_price
    return [
        _run_raw_case(
            "ashare",
            DAILY_KLINE,
            "Ashare.get_price",
            {"code": "000001", "frequency": "1d"},
            lambda: get_price("000001", frequency="1d", count=5),
        ),
        _run_raw_case(
            "ashare",
            DAILY_KLINE,
            "Ashare.get_price",
            {"code": "600519", "frequency": "1d"},
            lambda: get_price("600519", frequency="1d", count=5),
        ),
        _skip_case("ashare", REALTIME_QUOTES, "Ashare realtime", "realtime_api_not_confirmed", {"codes": STOCK_CODES}),
        _run_raw_case(
            "ashare",
            MINUTE_KLINE,
            "Ashare.get_price",
            {"code": "000001", "frequency": "1m"},
            lambda: get_price("000001", frequency="1m", count=5),
        ),
        _skip_case("ashare", INDEX_REALTIME, "Ashare index realtime", "index_realtime_api_not_confirmed", {"codes": INDEX_CODES}),
    ]


def _run_mootdx_cases() -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    try:
        from mootdx.quotes import Quotes  # type: ignore
    except Exception as exc:
        reason = f"dependency_unavailable:{type(exc).__name__}: {exc}"
        return [
            _skip_case("mootdx", REALTIME_QUOTES, "mootdx.quotes.Quotes", reason, {"codes": STOCK_CODES}),
            _skip_case("mootdx", MINUTE_KLINE, "MootdxAdapter.fetch_minute_kline", reason, {"code": "000001"}),
            _skip_case("mootdx", DAILY_KLINE, "mootdx.quotes.Quotes", reason, {"code": "000001"}),
        ]

    adapter = MootdxAdapter()
    results.append(
        _run_router_case(
            "mootdx",
            adapter,
            MINUTE_KLINE,
            {"code": "000001", "period": "5"},
            "MootdxAdapter.fetch_minute_kline",
        )
    )

    def client() -> Any:
        return Quotes.factory(market="std")

    results.append(
        _run_raw_case(
            "mootdx",
            REALTIME_QUOTES,
            "mootdx.Quotes.quotes",
            {"symbols": STOCK_CODES},
            lambda: client().quotes(symbol=STOCK_CODES),
        )
    )
    results.append(
        _run_raw_case(
            "mootdx",
            DAILY_KLINE,
            "mootdx.Quotes.bars",
            {"symbol": "000001", "frequency": 9, "offset": 5},
            lambda: client().bars(symbol="000001", frequency=9, start=0, offset=5),
        )
    )
    return results


def _run_pytdx_cases() -> list[dict[str, Any]]:
    if not _dependency_status("pytdx")["installed"]:
        reason = "dependency_not_installed"
    else:
        reason = "requires_explicit_tdx_server_host_and_market_selection"
    return [
        _skip_case("pytdx", REALTIME_QUOTES, "pytdx.hq.TdxHq_API.get_security_quotes", reason, {"codes": STOCK_CODES}),
        _skip_case("pytdx", MINUTE_KLINE, "pytdx.hq.TdxHq_API.get_security_bars", reason, {"code": "000001"}),
        _skip_case("pytdx", DAILY_KLINE, "pytdx.hq.TdxHq_API.get_security_bars", reason, {"code": "000001"}),
    ]


def _feature_status(results: list[dict[str, Any]], source: str, feature: str) -> str:
    feature_results = [item for item in results if item["source"] == source and item["feature"] == feature]
    if not feature_results:
        return "SKIP"
    if any(item["status"] == "PASS" and item.get("quality_gate_status") == "PASS" for item in feature_results):
        return "PASS"
    if any(item["status"] == "FAIL" for item in feature_results):
        return "FAIL"
    return "SKIP"


def _build_summary(results: list[dict[str, Any]]) -> dict[str, Any]:
    sources = ["efinance", "ashare", "mootdx", "pytdx"]
    summary: dict[str, Any] = {}
    for source in sources:
        summary[source] = {
            "daily_kline": _feature_status(results, source, DAILY_KLINE),
            "realtime_quotes": _feature_status(results, source, REALTIME_QUOTES),
            "index_realtime": _feature_status(results, source, INDEX_REALTIME),
            "minute_kline": _feature_status(results, source, MINUTE_KLINE),
        }
    return summary


def _markdown_row(values: list[object]) -> str:
    return "| " + " | ".join(str(value).replace("\n", "<br>") for value in values) + " |"


def _write_markdown(report: dict[str, Any]) -> None:
    lines = [
        "# OPTIONAL_BACKUP_SOURCE_REPORT",
        "",
        f"生成时间：{report['created_at']}",
        "",
        "## 1. 源能力结论",
        "",
        "| source | daily_kline | realtime_quotes | index_realtime | minute_kline |",
        "|---|---:|---:|---:|---:|",
    ]
    for source, summary in report["summary"].items():
        lines.append(
            _markdown_row(
                [
                    source,
                    summary.get("daily_kline"),
                    summary.get("realtime_quotes"),
                    summary.get("index_realtime"),
                    summary.get("minute_kline"),
                ]
            )
        )
    lines.extend(
        [
            "",
            "## 2. 明细",
            "",
            "| source | feature | api | status | gate | rows | columns | duration_ms | missing_fields | warnings | reason |",
            "|---|---|---|---:|---:|---:|---|---:|---|---|---|",
        ]
    )
    for case in report["cases"]:
        lines.append(
            _markdown_row(
                [
                    case.get("source"),
                    case.get("feature"),
                    case.get("api"),
                    case.get("status"),
                    case.get("quality_gate_status"),
                    (case.get("shape") or [0, 0])[0],
                    ", ".join(case.get("columns", []) or []),
                    case.get("duration_ms"),
                    ", ".join(case.get("missing_fields", []) or []),
                    ", ".join(case.get("warnings", []) or []),
                    case.get("reason"),
                ]
            )
        )
    lines.extend(
        [
            "",
            "## 3. 使用边界",
            "",
            "- efinance 即使通过，也仅按 optional/default backup with notice 处理，不宣传为商用级源。",
            "- Ashare 当前依赖不可用或 API 未确认时仅 SKIP，不进入默认链路。",
            "- mootdx/pytdx 需要通达信服务器连接或额外网络配置时不作为 V0.3 live gate 强阻断项。",
            "- 本报告未接入 S0，未输出任何交易建议。",
            "",
        ]
    )
    MD_REPORT_PATH.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    cases: list[dict[str, Any]] = []
    if _dependency_status("efinance")["installed"]:
        cases.extend(_run_efinance_cases())
    else:
        reason = "dependency_not_installed"
        cases.extend(
            [
                _skip_case("efinance", DAILY_KLINE, "efinance.stock.get_quote_history", reason, {"code": "000001"}),
                _skip_case("efinance", DAILY_KLINE, "efinance.stock.get_quote_history", reason, {"code": "600519"}),
                _skip_case("efinance", REALTIME_QUOTES, "efinance.stock.get_latest_quote", reason, {"codes": STOCK_CODES}),
                _skip_case("efinance", INDEX_REALTIME, "efinance.stock.get_realtime_quotes", reason, {"codes": INDEX_CODES}),
            ]
        )
    cases.extend(_run_ashare_cases())
    cases.extend(_run_mootdx_cases())
    cases.extend(_run_pytdx_cases())

    report = {
        "created_at": _utc_now(),
        "python": {"executable": sys.executable, "version": sys.version},
        "platform": platform.platform(),
        "dependencies": {
            "efinance": _dependency_status("efinance"),
            "Ashare": _dependency_status("Ashare"),
            "ashare": _dependency_status("ashare"),
            "mootdx": _dependency_status("mootdx"),
            "pytdx": _dependency_status("pytdx"),
        },
        "cases": cases,
        "summary": _build_summary(cases),
        "s0_connected": False,
        "trading_advice_included": False,
    }
    JSON_REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    JSON_REPORT_PATH.write_text(
        json.dumps(report, ensure_ascii=False, indent=2, default=str),
        encoding="utf-8",
    )
    _write_markdown(report)
    print(json.dumps(report, ensure_ascii=False, indent=2, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
