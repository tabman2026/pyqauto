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

from astock_source_router.adapters.pytdx_adapter import _looks_connected  # noqa: E402

ENABLE_ENV_VAR = "ENABLE_PYTDX_SERVER_REFRESH"
CONFIG_DIR = PROJECT_ROOT / "config"
LOGS_DIR = PROJECT_ROOT / "logs"
EXTRA_CONFIG_PATH = CONFIG_DIR / "pytdx_servers_extra.json"
ACTIVE_CONFIG_PATH = CONFIG_DIR / "pytdx_servers_active.json"
REFRESH_REPORT_PATH = LOGS_DIR / "pytdx_server_pool_refresh.json"
EXPANSION_REPORT_PATH = PROJECT_ROOT / "PYTDX_SERVER_POOL_EXPANSION_REPORT.md"
CURRENT_VERIFIED_SERVERS = [
    {"ip": "180.153.18.170", "port": 7709, "source": "verified_current"}
]
TEST_STOCK_QUOTES = [(0, "000001"), (1, "600519")]
TEST_INDEX_QUOTES = [(1, "000001"), (0, "399001"), (0, "399006"), (1, "000300")]
NETWORK_PERMISSION_PATTERNS = ("WinError 10013", "PermissionError", "Access is denied")


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, default=str), encoding="utf-8")


def _dependency_status() -> dict[str, Any]:
    try:
        return {"installed": True, "version": importlib.metadata.version("pytdx")}
    except importlib.metadata.PackageNotFoundError:
        return {"installed": False, "version": None}
    except Exception as exc:
        return {"installed": False, "version": None, "error": f"{type(exc).__name__}: {exc}"}


def _probe_timeout_seconds() -> float:
    raw = os.environ.get("PYTDX_SERVER_REFRESH_TIMEOUT_SECONDS", "1.8")
    try:
        value = float(raw)
    except ValueError:
        value = 1.8
    return min(3.0, max(1.5, value))


def _probe_sleep_seconds() -> float:
    raw = os.environ.get("PYTDX_SERVER_REFRESH_SLEEP_SECONDS", "0.5")
    try:
        value = float(raw)
    except ValueError:
        value = 0.5
    return max(0.2, value)


def _local_network_permission_error(text: str) -> bool:
    return any(pattern.lower() in text.lower() for pattern in NETWORK_PERMISSION_PATTERNS)


def _candidate_key(candidate: dict[str, Any]) -> tuple[str, int]:
    return str(candidate["ip"]), int(candidate["port"])


def _candidate(ip: Any, port: Any, source: str, detail: Any | None = None) -> dict[str, Any] | None:
    try:
        ip_text = str(ip).strip()
        port_int = int(port)
    except (TypeError, ValueError):
        return None
    if not ip_text:
        return None
    item: dict[str, Any] = {"ip": ip_text, "port": port_int, "source": source}
    if detail is not None:
        item["source_detail"] = str(detail)
    return item


def _host_entry_to_candidate(entry: Any) -> dict[str, Any] | None:
    if isinstance(entry, dict):
        ip = entry.get("ip") or entry.get("host") or entry.get("hq_host") or entry.get("address")
        port = entry.get("port", 7709)
        detail = entry.get("name") or entry.get("label")
        return _candidate(ip, port, "pytdx_hq_hosts", detail)

    if not isinstance(entry, (list, tuple)):
        return None
    if len(entry) >= 3:
        return _candidate(entry[1], entry[2], "pytdx_hq_hosts", entry[0])
    if len(entry) >= 2:
        return _candidate(entry[0], entry[1], "pytdx_hq_hosts")
    return None


def _load_current_verified_candidates() -> tuple[list[dict[str, Any]], dict[str, Any]]:
    return list(CURRENT_VERIFIED_SERVERS), {"status": "PASS", "count": len(CURRENT_VERIFIED_SERVERS)}


def _load_hq_hosts_candidates() -> tuple[list[dict[str, Any]], dict[str, Any]]:
    try:
        from pytdx.config.hosts import hq_hosts  # type: ignore
    except Exception as exc:
        return [], {
            "status": "SKIP",
            "reason": f"pytdx_hq_hosts_import_failed: {type(exc).__name__}: {exc}",
        }

    candidates = []
    for entry in hq_hosts:
        item = _host_entry_to_candidate(entry)
        if item is not None:
            candidates.append(item)
    return candidates, {"status": "PASS", "count": len(candidates)}


def _load_extra_candidates() -> tuple[list[dict[str, Any]], dict[str, Any]]:
    if not EXTRA_CONFIG_PATH.exists():
        return [], {"status": "SKIP", "reason": f"{EXTRA_CONFIG_PATH} not found"}
    try:
        payload = json.loads(EXTRA_CONFIG_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return [], {"status": "FAIL", "reason": f"{type(exc).__name__}: {exc}"}
    if not isinstance(payload, list):
        return [], {"status": "FAIL", "reason": "extra config must be a JSON list"}

    candidates: list[dict[str, Any]] = []
    skipped = 0
    for entry in payload:
        if not isinstance(entry, dict):
            skipped += 1
            continue
        item = _candidate(entry.get("ip"), entry.get("port", 7709), str(entry.get("source") or "user_extra"))
        if item is None:
            skipped += 1
        else:
            candidates.append(item)
    return candidates, {"status": "PASS", "count": len(candidates), "skipped_count": skipped}


def _merge_candidates(candidate_groups: list[list[dict[str, Any]]]) -> list[dict[str, Any]]:
    by_key: dict[tuple[str, int], dict[str, Any]] = {}
    for group in candidate_groups:
        for item in group:
            key = _candidate_key(item)
            if key not in by_key:
                merged = dict(item)
                merged["sources"] = [str(item.get("source"))]
                by_key[key] = merged
                continue
            sources = by_key[key].setdefault("sources", [])
            source = str(item.get("source"))
            if source not in sources:
                sources.append(source)
            by_key[key]["source"] = "+".join(sources)
    return list(by_key.values())


def _quote_codes(raw: Any) -> set[str]:
    codes: set[str] = set()
    for row in raw or []:
        if isinstance(row, dict) and row.get("code") is not None:
            codes.add(str(row["code"]).zfill(6))
    return codes


def _quote_count(raw: Any) -> int:
    try:
        return int(len(raw or []))
    except TypeError:
        return 0


def _probe_server(
    candidate: dict[str, Any],
    *,
    timeout_seconds: float,
    api_factory: Any | None = None,
) -> dict[str, Any]:
    ip = str(candidate["ip"])
    port = int(candidate["port"])
    tested_at = _utc_now()
    base = {
        "ip": ip,
        "port": port,
        "source": candidate.get("source"),
        "sources": candidate.get("sources") or [candidate.get("source")],
        "connect_status": "FAIL",
        "quote_status": "SKIP",
        "index_quote_status": "SKIP",
        "latency_ms": None,
        "row_count": 0,
        "index_row_count": 0,
        "error_summary": "",
        "error_category": None,
        "tested_at": tested_at,
    }

    if api_factory is None:
        try:
            from pytdx.hq import TdxHq_API  # type: ignore
        except Exception as exc:
            return {
                **base,
                "connect_status": "SKIP",
                "quote_status": "SKIP",
                "error_summary": f"pytdx_import_failed: {type(exc).__name__}: {exc}",
            }
        def api_factory() -> Any:
            return TdxHq_API(raise_exception=False)

    api = api_factory()
    started = time.perf_counter()
    errors: list[str] = []
    try:
        connected = api.connect(ip, port, time_out=timeout_seconds)
        if not _looks_connected(api, connected):
            errors.append(f"connect_failed: {connected}")
            return {
                **base,
                "latency_ms": round((time.perf_counter() - started) * 1000, 3),
                "error_summary": "; ".join(errors)[:500],
            }

        base["connect_status"] = "PASS"
        raw = api.get_security_quotes(TEST_STOCK_QUOTES)
        row_count = _quote_count(raw)
        base["row_count"] = row_count
        required_codes = {code for _, code in TEST_STOCK_QUOTES}
        if row_count >= len(TEST_STOCK_QUOTES) and required_codes.issubset(_quote_codes(raw)):
            base["quote_status"] = "PASS"
        else:
            base["quote_status"] = "FAIL"
            errors.append(f"stock_quote_empty_or_incomplete: row_count={row_count}")

        try:
            index_raw = api.get_security_quotes(TEST_INDEX_QUOTES)
            index_count = _quote_count(index_raw)
            base["index_row_count"] = index_count
            base["index_quote_status"] = "PASS" if index_count > 0 else "FAIL"
            if index_count == 0:
                errors.append("index_quote_empty")
        except Exception as exc:
            base["index_quote_status"] = "SKIP"
            errors.append(f"index_quote_skip: {type(exc).__name__}: {exc}")
    except Exception as exc:
        text = f"{type(exc).__name__}: {exc}"
        errors.append(text)
        if _local_network_permission_error(text):
            base["error_category"] = "local_network_permission_error"
        if base["connect_status"] == "PASS":
            base["quote_status"] = "FAIL"
    finally:
        with suppress(Exception):
            api.disconnect()

    return {
        **base,
        "latency_ms": round((time.perf_counter() - started) * 1000, 3),
        "error_summary": "; ".join(errors)[:500],
    }


def _pool_status(available_count: int) -> str:
    if available_count >= 2:
        return "server_pool_ready"
    if available_count == 1:
        return "primary_with_single_server_warning"
    return "no_available_server_fallback_to_easyquotation"


def _server_ref(item: dict[str, Any] | None) -> dict[str, Any] | None:
    if item is None:
        return None
    return {
        "ip": item.get("ip"),
        "port": item.get("port"),
        "source": item.get("source"),
        "grade": item.get("grade"),
        "latency_ms": item.get("latency_ms"),
        "tested_at": item.get("tested_at"),
    }


def _grade_results(results: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    passed = [
        dict(item)
        for item in results
        if item.get("connect_status") == "PASS" and item.get("quote_status") == "PASS"
    ]
    failed = [
        dict(item)
        for item in results
        if not (item.get("connect_status") == "PASS" and item.get("quote_status") == "PASS")
    ]
    passed.sort(key=lambda item: float(item.get("latency_ms") or 999999999))
    for index, item in enumerate(passed):
        if index == 0:
            item["grade"] = "primary"
        elif index == 1:
            item["grade"] = "hot_backup"
        else:
            item["grade"] = "backup"
    for item in failed:
        item["grade"] = "disabled"
    graded = passed + failed
    available_count = len(passed)
    primary = passed[0] if passed else None
    hot_backup = passed[1] if len(passed) >= 2 else None
    summary = {
        "available_server_count": available_count,
        "server_pool_status": _pool_status(available_count),
        "single_server_warning": available_count == 1,
        "server_pool_ready": available_count >= 2,
        "primary_server": _server_ref(primary),
        "hot_backup_server": _server_ref(hot_backup),
    }
    return graded, summary


def _forbidden_output_audit() -> dict[str, bool]:
    return {
        "s0_connected": False,
        "qmt_connected": False,
        "broker_connected": False,
        "auto_trading_enabled": False,
        "trading_advice_output": False,
        "candidate_pool_output": False,
        "strategy_signal_output": False,
        "buy_point_output": False,
        "sell_point_output": False,
        "position_output": False,
        "return_output": False,
        "winrate_output": False,
        "trading_plan_output": False,
    }


def _active_config(graded_results: list[dict[str, Any]], summary: dict[str, Any]) -> dict[str, Any]:
    active_server_pool = [
        {"ip": item["ip"], "port": item["port"]}
        for item in graded_results
        if item.get("quote_status") == "PASS" and item.get("grade") != "disabled"
    ]
    return {
        "generated_at": _utc_now(),
        "source": "scripts/pytdx_server_pool_refresh.py",
        "refresh_report": str(REFRESH_REPORT_PATH.relative_to(PROJECT_ROOT)),
        **summary,
        "active_server_pool": active_server_pool,
        "servers": graded_results,
        "fallback_policy": {
            "pytdx_zero_pass_action": "pytdx fails fast and router falls back to easyquotation",
            "easyquotation_fallback_preserved": True,
        },
        "forbidden_output_audit": _forbidden_output_audit(),
    }


def load_active_server_pool_config() -> dict[str, Any]:
    if not ACTIVE_CONFIG_PATH.exists():
        return {
            "exists": False,
            "available_server_count": 0,
            "server_pool_status": "missing_active_server_pool_config",
            "single_server_warning": False,
            "server_pool_ready": False,
            "primary_server": None,
            "hot_backup_server": None,
            "servers": [],
        }
    try:
        payload = json.loads(ACTIVE_CONFIG_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return {
            "exists": True,
            "load_status": "FAIL",
            "load_error": f"{type(exc).__name__}: {exc}",
            "available_server_count": 0,
            "server_pool_status": "invalid_active_server_pool_config",
            "single_server_warning": False,
            "server_pool_ready": False,
            "primary_server": None,
            "hot_backup_server": None,
            "servers": [],
        }
    if isinstance(payload, dict):
        payload["exists"] = True
        payload.setdefault("load_status", "PASS")
        return payload
    return {
        "exists": True,
        "load_status": "FAIL",
        "load_error": "active config must be a JSON object",
        "available_server_count": 0,
        "server_pool_status": "invalid_active_server_pool_config",
        "single_server_warning": False,
        "server_pool_ready": False,
        "primary_server": None,
        "hot_backup_server": None,
        "servers": [],
    }


def _markdown_table_row(values: list[Any]) -> str:
    return "| " + " | ".join("" if value is None else str(value) for value in values) + " |"


def _write_markdown(report: dict[str, Any]) -> None:
    summary = report.get("summary", {})
    rows = [
        "# PYTDX SERVER POOL EXPANSION REPORT",
        "",
        "## 结论",
        "",
        f"- 生成时间：`{report.get('created_at')}`",
        f"- live refresh 启用：`{report.get('live_enabled')}`",
        f"- 候选服务器数量：`{report.get('candidate_server_count')}`",
        f"- PASS 服务器数量：`{summary.get('available_server_count')}`",
        f"- server_pool_status：`{summary.get('server_pool_status')}`",
        f"- single_server_warning：`{summary.get('single_server_warning')}`",
        f"- server_pool_ready：`{summary.get('server_pool_ready')}`",
        f"- primary server：`{summary.get('primary_server')}`",
        f"- hot backup server：`{summary.get('hot_backup_server')}`",
        "",
        "## 候选来源",
        "",
        "| 来源 | 状态 | 数量/原因 |",
        "| --- | --- | --- |",
    ]
    for name, status in (report.get("candidate_sources") or {}).items():
        rows.append(_markdown_table_row([name, status.get("status"), status.get("count") or status.get("reason")]))
    rows.extend(
        [
            "",
            "## 服务器明细",
            "",
            "| grade | ip | port | source | connect | quote | index_quote | latency_ms | row_count | error |",
            "| --- | --- | ---: | --- | --- | --- | --- | ---: | ---: | --- |",
        ]
    )
    for item in report.get("servers", []):
        rows.append(
            _markdown_table_row(
                [
                    item.get("grade"),
                    item.get("ip"),
                    item.get("port"),
                    item.get("source"),
                    item.get("connect_status"),
                    item.get("quote_status"),
                    item.get("index_quote_status"),
                    item.get("latency_ms"),
                    item.get("row_count"),
                    item.get("error_summary"),
                ]
            )
        )
    rows.extend(
        [
            "",
            "## 审计结论",
            "",
            "- 所有可用服务器均来自 live probe，未测试服务器不会标记为可用。",
            "- `config/pytdx_servers_active.json` 仅写入本地排序结果；source policy 未改变。",
            "- easyquotation fallback 保留；0 个 PASS 时 pytdx fail-fast，由路由 fallback。",
            "- 未接入 S0、QMT、券商账户或自动交易。",
            "- 未输出候选股池、策略信号、买卖点、仓位、收益率、胜率或交易计划。",
        ]
    )
    EXPANSION_REPORT_PATH.write_text("\n".join(rows) + "\n", encoding="utf-8")


def _skip_report(reason: str) -> dict[str, Any]:
    current, current_status = _load_current_verified_candidates()
    hq_hosts, hq_status = _load_hq_hosts_candidates()
    extra, extra_status = _load_extra_candidates()
    candidates = _merge_candidates([current, hq_hosts, extra])
    return {
        "created_at": _utc_now(),
        "live_enabled": False,
        "status": "SKIP",
        "reason": reason,
        "dependency": _dependency_status(),
        "candidate_sources": {
            "verified_current": current_status,
            "pytdx_hq_hosts": hq_status,
            "config/pytdx_servers_extra.json": extra_status,
        },
        "candidate_server_count": len(candidates),
        "servers": [
            {
                "ip": item["ip"],
                "port": item["port"],
                "source": item["source"],
                "connect_status": "SKIP",
                "quote_status": "SKIP",
                "latency_ms": None,
                "row_count": 0,
                "error_summary": reason,
                "tested_at": None,
                "grade": "disabled",
            }
            for item in candidates
        ],
        "summary": {
            "available_server_count": 0,
            "server_pool_status": "SKIP",
            "single_server_warning": False,
            "server_pool_ready": False,
            "primary_server": None,
            "hot_backup_server": None,
        },
        "forbidden_output_audit": _forbidden_output_audit(),
    }


def build_live_report() -> tuple[dict[str, Any], dict[str, Any]]:
    current, current_status = _load_current_verified_candidates()
    hq_hosts, hq_status = _load_hq_hosts_candidates()
    extra, extra_status = _load_extra_candidates()
    candidates = _merge_candidates([current, hq_hosts, extra])
    timeout_seconds = _probe_timeout_seconds()
    sleep_seconds = _probe_sleep_seconds()
    dependency = _dependency_status()

    results: list[dict[str, Any]] = []
    if not dependency.get("installed"):
        for item in candidates:
            results.append(
                {
                    **item,
                    "connect_status": "SKIP",
                    "quote_status": "SKIP",
                    "index_quote_status": "SKIP",
                    "latency_ms": None,
                    "row_count": 0,
                    "index_row_count": 0,
                    "error_summary": "pytdx dependency not installed",
                    "error_category": None,
                    "tested_at": _utc_now(),
                }
            )
    else:
        for index, item in enumerate(candidates):
            results.append(_probe_server(item, timeout_seconds=timeout_seconds))
            if index < len(candidates) - 1:
                time.sleep(sleep_seconds)

    graded, summary = _grade_results(results)
    active_config = _active_config(graded, summary)
    report = {
        "created_at": _utc_now(),
        "live_enabled": True,
        "status": "PASS" if summary["available_server_count"] >= 1 else "FAIL",
        "dependency": dependency,
        "probe_settings": {
            "timeout_seconds": timeout_seconds,
            "sleep_seconds": sleep_seconds,
            "test_stock_quotes": TEST_STOCK_QUOTES,
            "test_index_quotes": TEST_INDEX_QUOTES,
        },
        "candidate_sources": {
            "verified_current": current_status,
            "pytdx_hq_hosts": hq_status,
            "config/pytdx_servers_extra.json": extra_status,
        },
        "candidate_server_count": len(candidates),
        "servers": graded,
        "summary": summary,
        "active_config_path": str(ACTIVE_CONFIG_PATH.relative_to(PROJECT_ROOT)),
        "forbidden_output_audit": _forbidden_output_audit(),
    }
    return report, active_config


def main() -> int:
    if os.environ.get(ENABLE_ENV_VAR) != "1":
        report = _skip_report(f"{ENABLE_ENV_VAR} is not 1")
        _write_json(REFRESH_REPORT_PATH, report)
        _write_markdown(report)
        print(json.dumps(report, ensure_ascii=False, indent=2, default=str))
        return 1

    report, active_config = build_live_report()
    _write_json(REFRESH_REPORT_PATH, report)
    _write_json(ACTIVE_CONFIG_PATH, active_config)
    _write_markdown(report)
    print(json.dumps(report, ensure_ascii=False, indent=2, default=str))
    return 0 if report["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
