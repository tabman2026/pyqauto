from __future__ import annotations

import importlib.metadata
import json
import platform
import sys
import time
import traceback
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from astock_source_router.adapters.easyquotation_adapter import EasyQuotationAdapter  # noqa: E402
from astock_source_router.core.errors import AllSourcesFailedError  # noqa: E402
from astock_source_router.core.features import INDEX_REALTIME, REALTIME_QUOTES  # noqa: E402
from astock_source_router.core.models import RouterConfig  # noqa: E402
from astock_source_router.core.policy import SourcePolicy  # noqa: E402
from astock_source_router.core.router import MarketRouter  # noqa: E402

JSON_REPORT_PATH = PROJECT_ROOT / "logs" / "easyquotation_channel_report.json"
MD_REPORT_PATH = PROJECT_ROOT / "EASYQUOTATION_CHANNEL_REPORT.md"

STOCK_CODES = ["000001", "600519"]
INDEX_CODES = ["000001", "399001"]


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


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


def _raw_to_frame(raw: Any) -> pd.DataFrame:
    rows = []
    for code, item in (raw or {}).items():
        row = dict(item)
        row["code"] = row.get("code", code)
        rows.append(row)
    return pd.DataFrame(rows)


def _source_codes_for_raw(provider: str, feature: str) -> list[str]:
    if feature == REALTIME_QUOTES:
        return STOCK_CODES
    return ["sh000001", "sz399001"]


def _run_raw_case(provider: str, feature: str) -> dict[str, Any]:
    import easyquotation  # type: ignore

    source_codes = _source_codes_for_raw(provider, feature)
    started_at = time.perf_counter()
    try:
        quotation = easyquotation.use(provider)
        raw = quotation.stocks(source_codes)
        duration_ms = round((time.perf_counter() - started_at) * 1000, 3)
        df = _raw_to_frame(raw)
        status = "PASS" if not df.empty else "FAIL"
        reason = "raw_non_empty" if status == "PASS" else "raw_empty"
        return {
            "status": status,
            "reason": reason,
            "provider": provider,
            "feature": feature,
            "api": f'easyquotation.use("{provider}").stocks',
            "source_codes": source_codes,
            "duration_ms": duration_ms,
            **_dataframe_payload(df),
        }
    except Exception as exc:
        return {
            "status": "FAIL",
            "reason": "raw_exception",
            "provider": provider,
            "feature": feature,
            "api": f'easyquotation.use("{provider}").stocks',
            "source_codes": source_codes,
            "duration_ms": round((time.perf_counter() - started_at) * 1000, 3),
            "shape": [0, 0],
            "columns": [],
            "head": [],
            "tail": [],
            "head_text": "",
            "tail_text": "",
            "error": _exception_payload(exc),
        }


def _run_router_case(provider: str, feature: str) -> dict[str, Any]:
    adapter = EasyQuotationAdapter(provider=provider)
    params = {"codes": STOCK_CODES if feature == REALTIME_QUOTES else INDEX_CODES}
    config = RouterConfig(
        cache_dir=PROJECT_ROOT / ".cache" / "easyquotation_channels",
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
            "status": "PASS",
            "reason": "router_quality_gate_pass",
            "source_name": adapter.name,
            "provider": provider,
            "feature": feature,
            "params": params,
            "duration_ms": duration_ms,
            "router_latency_ms": round(float(result.latency_ms), 3),
            "missing_fields": list(dict.fromkeys(missing_fields)),
            "warnings": list(dict.fromkeys(warnings)),
            "fallback_trace": result.fallback_trace,
            **_dataframe_payload(result.data),
        }
    except AllSourcesFailedError as exc:
        trace = [dict(item) for item in exc.trace]
        warnings: list[str] = []
        missing_fields: list[str] = []
        for item in trace:
            warnings.extend(item.get("warnings", []) or [])
            missing_fields.extend(item.get("missing_fields", []) or [])
        return {
            "status": "FAIL",
            "reason": "router_quality_gate_fail",
            "source_name": adapter.name,
            "provider": provider,
            "feature": feature,
            "params": params,
            "duration_ms": round((time.perf_counter() - started_at) * 1000, 3),
            "missing_fields": list(dict.fromkeys(missing_fields)),
            "warnings": list(dict.fromkeys(warnings)),
            "fallback_trace": trace,
            "shape": [0, 0],
            "columns": [],
            "head": [],
            "tail": [],
            "head_text": "",
            "tail_text": "",
        }
    except Exception as exc:
        return {
            "status": "FAIL",
            "reason": "router_exception",
            "source_name": adapter.name,
            "provider": provider,
            "feature": feature,
            "params": params,
            "duration_ms": round((time.perf_counter() - started_at) * 1000, 3),
            "missing_fields": [],
            "warnings": [],
            "fallback_trace": [],
            "shape": [0, 0],
            "columns": [],
            "head": [],
            "tail": [],
            "head_text": "",
            "tail_text": "",
            "error": _exception_payload(exc),
        }


def _channel_summary(cases: list[dict[str, Any]]) -> dict[str, Any]:
    summary: dict[str, Any] = {}
    for provider in ["sina", "tencent"]:
        source_name = f"easyquotation_{provider}"
        router_cases = [
            case
            for case in cases
            if case.get("source_name") == source_name and case.get("case_type") == "router"
        ]
        summary[source_name] = {
            "realtime_quotes": next(
                (case.get("status") for case in router_cases if case.get("feature") == REALTIME_QUOTES),
                "SKIP",
            ),
            "index_realtime": next(
                (case.get("status") for case in router_cases if case.get("feature") == INDEX_REALTIME),
                "SKIP",
            ),
        }
    return summary


def _markdown_row(values: list[object]) -> str:
    return "| " + " | ".join(str(value).replace("\n", "<br>") for value in values) + " |"


def _write_markdown(report: dict[str, Any]) -> None:
    lines = [
        "# EASYQUOTATION_CHANNEL_REPORT",
        "",
        f"生成时间：{report['created_at']}",
        "",
        "## 1. 结论",
        "",
        "easyquotation 已拆分为 `easyquotation_sina` 与 `easyquotation_tencent` 两个底层通道。二者若均通过，只表示同一 Python 库下的不同上游通道通过，不等价于完全独立库级双源。",
        "",
        "| 通道 | realtime_quotes | index_realtime |",
        "|---|---:|---:|",
    ]
    for source_name, summary in report["summary"].items():
        lines.append(
            _markdown_row(
                [
                    source_name,
                    summary.get("realtime_quotes"),
                    summary.get("index_realtime"),
                ]
            )
        )
    lines.extend(
        [
            "",
            "## 2. 明细",
            "",
            "| case | provider | feature | status | rows | columns | duration_ms | missing_fields | warnings | reason |",
            "|---|---|---|---:|---:|---|---:|---|---|---|",
        ]
    )
    for case in report.get("cases", []):
        lines.append(
            _markdown_row(
                [
                    case.get("case_type"),
                    case.get("provider"),
                    case.get("feature"),
                    case.get("status"),
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
            "## 3. 抽样",
            "",
        ]
    )
    for case in report.get("cases", []):
        lines.extend(
            [
                f"### {case.get('case_type')} {case.get('provider')} {case.get('feature')}",
                "",
                "```text",
                str(case.get("head_text", "")),
                "```",
                "",
            ]
        )
    lines.extend(
        [
            "## 4. 验收",
            "",
            "- `logs/easyquotation_channel_report.json` 已使用 `ensure_ascii=False` 写入。",
            "- 本脚本未接入 S0，未输出交易建议。",
            "",
        ]
    )
    MD_REPORT_PATH.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    cases: list[dict[str, Any]] = []
    for provider in ["sina", "tencent"]:
        for feature in [REALTIME_QUOTES, INDEX_REALTIME]:
            raw_case = _run_raw_case(provider, feature)
            raw_case["case_type"] = "raw"
            cases.append(raw_case)
            time.sleep(1.0)
            router_case = _run_router_case(provider, feature)
            router_case["case_type"] = "router"
            cases.append(router_case)
            time.sleep(1.0)

    try:
        easyquotation_version = importlib.metadata.version("easyquotation")
    except importlib.metadata.PackageNotFoundError:
        easyquotation_version = None

    report = {
        "created_at": _utc_now(),
        "python": {"executable": sys.executable, "version": sys.version},
        "platform": platform.platform(),
        "dependencies": {"easyquotation": easyquotation_version},
        "stock_codes": STOCK_CODES,
        "index_codes": INDEX_CODES,
        "same_library_different_upstream_channels": True,
        "s0_connected": False,
        "trading_advice_included": False,
        "cases": cases,
        "summary": _channel_summary(cases),
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
