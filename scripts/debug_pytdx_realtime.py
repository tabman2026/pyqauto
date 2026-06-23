from __future__ import annotations

import importlib.metadata
import json
import os
import sys
import time
from contextlib import suppress
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from astock_source_router.adapters.pytdx_adapter import PytdxAdapter  # noqa: E402
from astock_source_router.core.features import (  # noqa: E402
    FULL_REALTIME_QUOTES,
    INDEX_REALTIME,
    MINUTE_KLINE,
    REALTIME_QUOTES,
)
from astock_source_router.core.schema import (  # noqa: E402
    REQUIRED_COLUMNS,
    add_source_columns,
    coerce_standard_types,
    validate_dataframe,
)

JSON_REPORT_PATH = PROJECT_ROOT / "logs" / "pytdx_realtime_primary_report.json"
MD_REPORT_PATH = PROJECT_ROOT / "PYTDX_REALTIME_PRIMARY_REPORT.md"
STOCK_CODES = ["000001", "600519"]
INDEX_CODES = ["000001", "399001", "399006", "000300"]
INDEX_NAMES = {
    "000001": "上证指数",
    "399001": "深证成指",
    "399006": "创业板指",
    "000300": "沪深300",
}

FIELD_DERIVATIONS = {
    "pct_chg": "derived_from_pytdx_price_and_last_close",
    "name": "derived_from_pytdx_get_security_list_or_builtin_index_alias",
    "date": "derived_from_local_date_because_pytdx_quote_has_servertime_only",
    "time": "derived_from_pytdx_servertime",
}

FIELD_WARNINGS = [
    {
        "field": "volume",
        "warning": "pytdx quote volume is kept as raw vol; cross-source consistency may flag unit differences",
    },
    {
        "field": "price",
        "warning": "no price scaling adjustment was applied; live values were checked for plausible A-share/index ranges",
    },
]


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _dependency_status() -> dict[str, Any]:
    try:
        return {"installed": True, "version": importlib.metadata.version("pytdx")}
    except importlib.metadata.PackageNotFoundError:
        return {"installed": False, "version": None}
    except Exception as exc:
        return {"installed": False, "version": None, "error": f"{type(exc).__name__}: {exc}"}


def _write_json(report: dict[str, Any]) -> None:
    JSON_REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    JSON_REPORT_PATH.write_text(
        json.dumps(report, ensure_ascii=False, indent=2, default=str),
        encoding="utf-8",
    )


def _markdown_table_row(values: list[Any]) -> str:
    return "| " + " | ".join("" if value is None else str(value) for value in values) + " |"


def _write_markdown(report: dict[str, Any]) -> None:
    rows = [
        "# PYTDX Realtime Primary Report",
        "",
        "## 结论",
        "",
        f"- 生成时间：`{report['created_at']}`",
        f"- live 启用：`{report['live_enabled']}`",
        f"- pytdx 安装：`{report['dependency']['installed']}`",
        f"- get_security_quotes：`{report['get_security_quotes_status']}`",
        f"- realtime_quotes：`{report['feature_status'].get(REALTIME_QUOTES)}`",
        f"- full_realtime_quotes：`{report['feature_status'].get(FULL_REALTIME_QUOTES)}`",
        f"- index_realtime：`{report['feature_status'].get(INDEX_REALTIME)}`",
        f"- minute_kline：`{report['feature_status'].get(MINUTE_KLINE)}`",
        f"- pytdx 是否允许进入实时默认第一源：`{report['allow_pytdx_realtime_primary']}`",
        "",
        "## 字段派生",
        "",
    ]
    for field, note in report["field_derivations"].items():
        rows.append(f"- `{field}`: {note}")
    rows.extend(
        [
            "",
            "## 字段警告",
            "",
        ]
    )
    for item in report["field_warnings"]:
        rows.append(f"- `{item['field']}`: {item['warning']}")
    rows.extend(
        [
            "",
            "## 功能明细",
            "",
            "| feature | status | row_count | missing_fields | warnings | server |",
            "| --- | --- | ---: | --- | --- | --- |",
        ]
    )
    for item in report["feature_results"]:
        rows.append(
            _markdown_table_row(
                [
                    item.get("feature"),
                    item.get("status"),
                    item.get("row_count"),
                    ", ".join(item.get("missing_fields") or []),
                    ", ".join(item.get("warnings") or []),
                    item.get("server"),
                ]
            )
        )
    rows.extend(
        [
            "",
            "## 测试标的",
            "",
            f"- 股票：`{', '.join(STOCK_CODES)}`",
            f"- 指数：`{', '.join(f'{code}({name})' for code, name in INDEX_NAMES.items())}`",
            "",
            "## 审计结论",
            "",
            "- 本脚本只验证 pytdx 行情读取与字段标准化，不接入 S0、QMT、券商账户或自动交易。",
            "- 未内置 cookie、token、账号或券商登录态。",
            "- 不输出交易建议、仓位建议、收益率承诺或交易计划。",
            "- JSON 报告使用 UTF-8 和 `ensure_ascii=False` 写入。",
        ]
    )
    MD_REPORT_PATH.write_text("\n".join(rows) + "\n", encoding="utf-8")


def _jsonable_sample(df: pd.DataFrame) -> list[dict[str, Any]]:
    if df.empty:
        return []
    return json.loads(df.head(5).to_json(orient="records", force_ascii=False, date_format="iso"))


def _quality_check(feature: str, df: pd.DataFrame, elapsed_ms: float, server: tuple[str, int] | None) -> dict[str, Any]:
    with_source = add_source_columns(df, source="pytdx", latency_ms=elapsed_ms)
    with_source = coerce_standard_types(with_source)
    quality = validate_dataframe(
        feature,
        with_source,
        context={
            "min_expected_rows": (
                len(STOCK_CODES)
                if feature in {REALTIME_QUOTES, FULL_REALTIME_QUOTES}
                else len(INDEX_CODES)
                if feature == INDEX_REALTIME
                else 1
            ),
            "realtime_stale_after_seconds": 15 * 60,
        },
    )
    return {
        "feature": feature,
        "status": "PASS" if quality.is_valid else "FAIL",
        "row_count": quality.row_count,
        "missing_fields": quality.missing_fields,
        "warnings": quality.warnings,
        "columns": list(with_source.columns),
        "required_columns": REQUIRED_COLUMNS.get(feature, []),
        "latency_ms": round(elapsed_ms, 3),
        "server": None if server is None else f"{server[0]}:{server[1]}",
        "sample": _jsonable_sample(with_source),
    }


def _run_feature(adapter: PytdxAdapter, feature: str) -> dict[str, Any]:
    started = time.perf_counter()
    try:
        if feature == REALTIME_QUOTES:
            df = adapter.fetch_realtime_quotes(STOCK_CODES)
        elif feature == FULL_REALTIME_QUOTES:
            df = adapter.fetch_full_realtime_quotes(STOCK_CODES)
        elif feature == INDEX_REALTIME:
            df = adapter.fetch_index_realtime(INDEX_CODES)
        elif feature == MINUTE_KLINE:
            df = adapter.fetch_minute_kline("000001", period="5")
        else:
            raise ValueError(f"unsupported feature: {feature}")
        elapsed_ms = (time.perf_counter() - started) * 1000
        return _quality_check(feature, df, elapsed_ms, adapter.last_server)
    except Exception as exc:
        return {
            "feature": feature,
            "status": "FAIL",
            "row_count": 0,
            "missing_fields": REQUIRED_COLUMNS.get(feature, []),
            "warnings": [],
            "columns": [],
            "required_columns": REQUIRED_COLUMNS.get(feature, []),
            "latency_ms": round((time.perf_counter() - started) * 1000, 3),
            "server": None,
            "error_type": type(exc).__name__,
            "error_message": str(exc),
            "sample": [],
        }


def _raw_quote_check(adapter: PytdxAdapter) -> dict[str, Any]:
    started = time.perf_counter()
    try:
        api, server = adapter._connect_first_available()
        try:
            raw = api.get_security_quotes([(0, "000001"), (1, "600519")])
        finally:
            with suppress(Exception):
                api.disconnect()
        status = "PASS" if raw is not None and len(raw) >= 2 else "FAIL"
        columns = list(raw[0].keys()) if raw else []
        return {
            "status": status,
            "latency_ms": round((time.perf_counter() - started) * 1000, 3),
            "server": f"{server[0]}:{server[1]}",
            "row_count": 0 if raw is None else len(raw),
            "raw_fields": columns,
        }
    except Exception as exc:
        return {
            "status": "FAIL",
            "latency_ms": round((time.perf_counter() - started) * 1000, 3),
            "server": None,
            "row_count": 0,
            "raw_fields": [],
            "error_type": type(exc).__name__,
            "error_message": str(exc),
        }


def _skip_report(reason: str) -> dict[str, Any]:
    return {
        "created_at": _utc_now(),
        "live_enabled": False,
        "reason": reason,
        "dependency": _dependency_status(),
        "get_security_quotes_status": "SKIP",
        "feature_status": {
            REALTIME_QUOTES: "SKIP",
            FULL_REALTIME_QUOTES: "SKIP",
            INDEX_REALTIME: "SKIP",
            MINUTE_KLINE: "SKIP",
        },
        "allow_pytdx_realtime_primary": False,
        "field_derivations": FIELD_DERIVATIONS,
        "field_warnings": FIELD_WARNINGS,
        "feature_results": [],
    }


def main() -> int:
    if os.environ.get("ENABLE_PYTDX_LIVE_TEST") != "1":
        report = _skip_report("ENABLE_PYTDX_LIVE_TEST is not 1")
        _write_json(report)
        _write_markdown(report)
        print(json.dumps(report, ensure_ascii=False, indent=2, default=str))
        return 1

    adapter = PytdxAdapter()
    raw_check = _raw_quote_check(adapter)
    feature_results = [
        _run_feature(adapter, REALTIME_QUOTES),
        _run_feature(adapter, FULL_REALTIME_QUOTES),
        _run_feature(adapter, INDEX_REALTIME),
        _run_feature(adapter, MINUTE_KLINE),
    ]
    feature_status = {item["feature"]: item["status"] for item in feature_results}
    allow_primary = (
        raw_check["status"] == "PASS"
        and feature_status.get(REALTIME_QUOTES) == "PASS"
        and feature_status.get(FULL_REALTIME_QUOTES) == "PASS"
    )
    report = {
        "created_at": _utc_now(),
        "live_enabled": True,
        "dependency": _dependency_status(),
        "test_codes": {"stocks": STOCK_CODES, "indexes": INDEX_NAMES},
        "raw_quote_check": raw_check,
        "get_security_quotes_status": raw_check["status"],
        "feature_status": feature_status,
        "allow_pytdx_realtime_primary": allow_primary,
        "field_derivations": FIELD_DERIVATIONS,
        "field_warnings": FIELD_WARNINGS,
        "feature_results": feature_results,
    }
    _write_json(report)
    _write_markdown(report)
    print(json.dumps(report, ensure_ascii=False, indent=2, default=str))
    return 0 if allow_primary else 1


if __name__ == "__main__":
    raise SystemExit(main())
