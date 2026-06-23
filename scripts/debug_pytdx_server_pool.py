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

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from astock_source_router.adapters.pytdx_adapter import (  # noqa: E402
    DEFAULT_PYTDX_SERVER_POOL,
    _looks_connected,
    parse_pytdx_server_pool,
)

JSON_REPORT_PATH = PROJECT_ROOT / "logs" / "pytdx_server_pool_report.json"
MD_REPORT_PATH = PROJECT_ROOT / "PYTDX_SERVER_POOL_REPORT.md"
TEST_QUOTES = [(0, "000001"), (1, "600519")]


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
        "# PYTDX Server Pool Report",
        "",
        "## 结论",
        "",
        f"- 生成时间：`{report['created_at']}`",
        f"- live 启用：`{report['live_enabled']}`",
        f"- pytdx 安装：`{report['dependency']['installed']}`",
        f"- 可用服务器数量：`{report['available_server_count']}`",
        f"- server_pool_status：`{report['server_pool_status']}`",
        f"- pytdx 是否允许作为实时主源候选：`{report['allow_pytdx_realtime_primary_candidate']}`",
        "",
        "## 服务器明细",
        "",
        "| ip | port | connect_status | latency_ms | quote_status | error_summary |",
        "| --- | ---: | --- | ---: | --- | --- |",
    ]
    for item in report["servers"]:
        rows.append(
            _markdown_table_row(
                [
                    item.get("ip"),
                    item.get("port"),
                    item.get("connect_status"),
                    item.get("latency_ms"),
                    item.get("quote_status"),
                    item.get("error_summary"),
                ]
            )
        )
    rows.extend(
        [
            "",
            "## 审计结论",
            "",
            "- 本脚本只连接公开 TDX 行情服务器并读取测试代码行情，不接入券商账户、QMT 或 S0。",
            "- 未内置 cookie、token、账号或券商登录态。",
            "- 不输出交易建议、仓位建议、收益率承诺或自动交易逻辑。",
            "- JSON 报告使用 UTF-8 和 `ensure_ascii=False` 写入。",
        ]
    )
    MD_REPORT_PATH.write_text("\n".join(rows) + "\n", encoding="utf-8")


def _server_result(ip: str, port: int) -> dict[str, Any]:
    try:
        from pytdx.hq import TdxHq_API  # type: ignore
    except Exception as exc:
        return {
            "ip": ip,
            "port": port,
            "connect_status": "SKIP",
            "latency_ms": None,
            "quote_status": "SKIP",
            "error_summary": f"pytdx_import_failed: {type(exc).__name__}: {exc}",
        }

    api = TdxHq_API(raise_exception=False)
    started = time.perf_counter()
    connect_status = "FAIL"
    quote_status = "SKIP"
    error_summary = ""
    try:
        connected = api.connect(ip, port, time_out=5.0)
        if not _looks_connected(api, connected):
            error_summary = f"connect_failed: {connected}"
        else:
            connect_status = "PASS"
            raw = api.get_security_quotes(TEST_QUOTES)
            if raw is not None and len(raw) >= len(TEST_QUOTES):
                quote_status = "PASS"
            else:
                quote_status = "FAIL"
                error_summary = f"quote_empty_or_incomplete: {raw}"
    except Exception as exc:
        error_summary = f"{type(exc).__name__}: {exc}"
        if connect_status == "PASS":
            quote_status = "FAIL"
    finally:
        with suppress(Exception):
            api.disconnect()
    return {
        "ip": ip,
        "port": port,
        "connect_status": connect_status,
        "latency_ms": round((time.perf_counter() - started) * 1000, 3),
        "quote_status": quote_status,
        "error_summary": error_summary[:500],
    }


def _decision(available_count: int) -> str:
    if available_count >= 2:
        return "server_pool_ready"
    if available_count == 1:
        return "primary_with_single_server_warning"
    return "optional_pending_server_config"


def _skip_report(reason: str) -> dict[str, Any]:
    servers = parse_pytdx_server_pool()
    return {
        "created_at": _utc_now(),
        "live_enabled": False,
        "reason": reason,
        "dependency": _dependency_status(),
        "default_server_pool": DEFAULT_PYTDX_SERVER_POOL,
        "configured_server_pool": servers,
        "available_server_count": 0,
        "server_pool_status": "SKIP",
        "allow_pytdx_realtime_primary_candidate": False,
        "servers": [
            {
                "ip": ip,
                "port": port,
                "connect_status": "SKIP",
                "latency_ms": None,
                "quote_status": "SKIP",
                "error_summary": reason,
            }
            for ip, port in servers
        ],
    }


def main() -> int:
    if os.environ.get("ENABLE_PYTDX_LIVE_TEST") != "1":
        report = _skip_report("ENABLE_PYTDX_LIVE_TEST is not 1")
        _write_json(report)
        _write_markdown(report)
        print(json.dumps(report, ensure_ascii=False, indent=2, default=str))
        return 1

    dependency = _dependency_status()
    servers = parse_pytdx_server_pool()
    results = [_server_result(ip, port) for ip, port in servers]
    available_count = sum(
        item["connect_status"] == "PASS" and item["quote_status"] == "PASS"
        for item in results
    )
    status = _decision(available_count)
    report = {
        "created_at": _utc_now(),
        "live_enabled": True,
        "dependency": dependency,
        "default_server_pool": DEFAULT_PYTDX_SERVER_POOL,
        "configured_server_pool": servers,
        "available_server_count": available_count,
        "server_pool_status": status,
        "allow_pytdx_realtime_primary_candidate": bool(dependency["installed"] and available_count >= 1),
        "servers": results,
    }
    _write_json(report)
    _write_markdown(report)
    print(json.dumps(report, ensure_ascii=False, indent=2, default=str))
    return 0 if report["allow_pytdx_realtime_primary_candidate"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
