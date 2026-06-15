"""pytdx server probe utilities."""

from __future__ import annotations

import argparse
import concurrent.futures
import json
import sys
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Sequence

from aquote_router.adapters.base import code_for_symbol, market_for_symbol
from aquote_router.adapters.pytdx_adapter import PYTDX_KLINE_PERIOD_CATEGORIES

DEFAULT_CONFIG = "config/pytdx_servers.example.json"
DEFAULT_LOCAL_CONFIG = "config/pytdx_servers.local.json"
DEFAULT_OUTPUT = "config/pytdx_servers.active.local.json"
DEFAULT_SYMBOL = "000001"
DEFAULT_MINUTE_PERIOD = "15m"
DEFAULT_COUNT = 10
DEFAULT_TIMEOUT = 3.0
DEFAULT_WORKERS = 8
ROLE_SEQUENCE = ("primary", "hot_backup", "hot_backup")


@dataclass(frozen=True)
class ServerCandidate:
    host: str
    port: int
    source: str
    role: str = "backup"
    configured_latency_ms: int = 999999
    enabled: bool = True
    name: str | None = None

    def key(self) -> tuple[str, int]:
        return (self.host, self.port)


def run_probe(
    *,
    config_path: str | Path = DEFAULT_CONFIG,
    output_path: str | Path = DEFAULT_OUTPUT,
    local_config_path: str | Path | None = DEFAULT_LOCAL_CONFIG,
    timeout: float = DEFAULT_TIMEOUT,
    limit: int = 0,
    workers: int = DEFAULT_WORKERS,
    symbol: str = DEFAULT_SYMBOL,
    minute_period: str = DEFAULT_MINUTE_PERIOD,
    count: int = DEFAULT_COUNT,
    active_count: int = 0,
) -> dict[str, Any]:
    """Probe pytdx servers and write a local active server pool."""

    started_at = datetime.now(timezone.utc)
    config = Path(config_path)
    output = Path(output_path)
    local_config = Path(local_config_path) if local_config_path else None

    official_candidates, official_sources, pytdx_import_error = _load_official_pytdx_servers()
    config_total_count, config_candidates = _load_config_candidates(
        config,
        source=_display_path(config),
        optional=False,
    )
    local_total_count = 0
    local_candidates: list[ServerCandidate] = []
    if local_config is not None:
        local_total_count, local_candidates = _load_config_candidates(
            local_config,
            source=_display_path(local_config),
            optional=True,
        )

    candidates = _dedupe_candidates([*official_candidates, *config_candidates, *local_candidates])
    if limit > 0:
        candidates = candidates[:limit]

    results = _probe_candidates(
        candidates,
        timeout=max(float(timeout), 0.1),
        workers=max(int(workers), 1),
        symbol=symbol,
        minute_period=minute_period,
        count=max(int(count), 1),
    )
    sorted_results = sorted(results, key=_result_sort_key)
    active_entries = _build_active_config(sorted_results, active_count=max(int(active_count), 0))
    _write_json(output, active_entries)

    finished_at = datetime.now(timezone.utc)
    return _build_summary(
        started_at=started_at,
        finished_at=finished_at,
        pytdx_import_error=pytdx_import_error,
        official_sources=official_sources,
        official_candidates=official_candidates,
        config_total_count=config_total_count,
        local_total_count=local_total_count,
        candidates=candidates,
        results=sorted_results,
        output_path=output,
        active_entries=active_entries,
        symbol=symbol,
        minute_period=minute_period,
        count=max(int(count), 1),
        timeout=max(float(timeout), 0.1),
        workers=max(int(workers), 1),
        limit=max(int(limit), 0),
    )


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Probe pytdx servers and generate a local active server pool."
    )
    parser.add_argument("--json", action="store_true", help="Print JSON summary.")
    parser.add_argument(
        "--config",
        "--example-config",
        dest="config",
        default=DEFAULT_CONFIG,
        help="Input pytdx server config.",
    )
    parser.add_argument(
        "--output",
        "--active-config",
        dest="output",
        default=DEFAULT_OUTPUT,
        help="Generated active local pytdx server config.",
    )
    parser.add_argument(
        "--local-config",
        default=DEFAULT_LOCAL_CONFIG,
        help="Optional extra local pytdx server config.",
    )
    parser.add_argument("--symbol", default=DEFAULT_SYMBOL)
    parser.add_argument(
        "--minute-period",
        choices=[period for period in PYTDX_KLINE_PERIOD_CATEGORIES if period != "1d"],
        default=DEFAULT_MINUTE_PERIOD,
    )
    parser.add_argument("--count", default=DEFAULT_COUNT, type=int)
    parser.add_argument("--timeout", default=DEFAULT_TIMEOUT, type=float)
    parser.add_argument("--workers", default=DEFAULT_WORKERS, type=int)
    parser.add_argument(
        "--limit",
        default=0,
        type=int,
        help="Limit candidates after loading and de-duplicating; 0 means no limit.",
    )
    parser.add_argument(
        "--active-count",
        default=0,
        type=int,
        help="Limit written active servers; 0 writes all usable probed servers.",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_arg_parser()
    args = parser.parse_args(argv)
    summary = run_probe(
        config_path=args.config,
        output_path=args.output,
        local_config_path=args.local_config,
        timeout=args.timeout,
        limit=args.limit,
        workers=args.workers,
        symbol=args.symbol,
        minute_period=args.minute_period,
        count=args.count,
        active_count=args.active_count,
    )
    if args.json:
        print(json.dumps(summary, ensure_ascii=False, indent=2))
    else:
        print(
            "Pytdx probe finished: "
            f"{summary['connect_success_count']}/{summary['probe_server_count']} "
            "servers connected. "
            f"Active config: {summary['active_config_path']}"
        )
    return 0


def _load_official_pytdx_servers() -> tuple[
    list[ServerCandidate], list[dict[str, Any]], str | None
]:
    candidates: list[ServerCandidate] = []
    sources: list[dict[str, Any]] = []
    import_error: str | None = None

    try:
        from pytdx.config.hosts import hq_hosts
    except Exception as exc:  # pragma: no cover - depends on user environment
        import_error = _error_text(exc)
        hq_hosts = []

    hq_count = 0
    for item in hq_hosts:
        candidate = _candidate_from_hq_host(item)
        if candidate:
            hq_count += 1
            candidates.append(candidate)
    sources.append(
        {
            "module": "pytdx.config.hosts",
            "object": "hq_hosts",
            "candidate_count": hq_count,
        }
    )

    try:
        from pytdx.util.best_ip import stock_ip
    except Exception:
        stock_ip = []

    stock_count = 0
    for item in stock_ip:
        candidate = _candidate_from_stock_ip(item)
        if candidate:
            stock_count += 1
            candidates.append(candidate)
    sources.append(
        {
            "module": "pytdx.util.best_ip",
            "object": "stock_ip",
            "candidate_count": stock_count,
        }
    )

    return _dedupe_candidates(candidates), sources, import_error


def _candidate_from_hq_host(item: Any) -> ServerCandidate | None:
    if not isinstance(item, (list, tuple)) or len(item) < 3:
        return None
    name, host, port = item[0], item[1], item[2]
    return _candidate_from_values(
        host=host,
        port=port,
        source="pytdx.config.hosts.hq_hosts",
        name=str(name) if name is not None else None,
    )


def _candidate_from_stock_ip(item: Any) -> ServerCandidate | None:
    if not isinstance(item, dict):
        return None
    return _candidate_from_values(
        host=item.get("ip"),
        port=item.get("port"),
        source="pytdx.util.best_ip.stock_ip",
        name=str(item.get("name")) if item.get("name") is not None else None,
    )


def _candidate_from_values(
    *,
    host: Any,
    port: Any,
    source: str,
    role: str = "backup",
    latency_ms: Any = 999999,
    enabled: Any = True,
    name: str | None = None,
) -> ServerCandidate | None:
    try:
        host_text = str(host).strip()
        port_int = int(port)
        latency_int = int(latency_ms)
    except (TypeError, ValueError):
        return None
    if not host_text or port_int <= 0:
        return None
    role_text = str(role)
    if role_text not in {"primary", "hot_backup", "backup"}:
        role_text = "backup"
    return ServerCandidate(
        host=host_text,
        port=port_int,
        source=source,
        role=role_text,
        configured_latency_ms=latency_int,
        enabled=bool(enabled),
        name=name,
    )


def _load_config_candidates(
    path: Path,
    *,
    source: str,
    optional: bool,
) -> tuple[int, list[ServerCandidate]]:
    if not path.exists():
        if optional:
            return 0, []
        raise FileNotFoundError(f"pytdx server config not found: {_display_path(path)}")

    raw = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(raw, list):
        raise ValueError(f"pytdx server config must be a JSON list: {_display_path(path)}")

    candidates: list[ServerCandidate] = []
    for item in raw:
        if not isinstance(item, dict):
            continue
        if not bool(item.get("enabled", True)):
            continue
        candidate = _candidate_from_values(
            host=item.get("host"),
            port=item.get("port", 7709),
            source=source,
            role=item.get("role", "backup"),
            latency_ms=item.get("latency_ms", 999999),
            enabled=item.get("enabled", True),
        )
        if candidate:
            candidates.append(candidate)
    return len(raw), candidates


def _dedupe_candidates(candidates: list[ServerCandidate]) -> list[ServerCandidate]:
    deduped: list[ServerCandidate] = []
    seen: set[tuple[str, int]] = set()
    for candidate in candidates:
        key = candidate.key()
        if key in seen:
            continue
        seen.add(key)
        deduped.append(candidate)
    return deduped


def _probe_candidates(
    candidates: list[ServerCandidate],
    *,
    timeout: float,
    workers: int,
    symbol: str,
    minute_period: str,
    count: int,
) -> list[dict[str, Any]]:
    if not candidates:
        return []
    with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as executor:
        futures = [
            executor.submit(
                _probe_candidate,
                candidate,
                timeout=timeout,
                symbol=symbol,
                minute_period=minute_period,
                count=count,
            )
            for candidate in candidates
        ]
        return [future.result() for future in concurrent.futures.as_completed(futures)]


def _probe_candidate(
    candidate: ServerCandidate,
    *,
    timeout: float,
    symbol: str,
    minute_period: str,
    count: int,
) -> dict[str, Any]:
    result = _empty_result(candidate)
    started = time.perf_counter()
    api = None
    try:
        from pytdx.hq import TdxHq_API
    except Exception as exc:  # pragma: no cover - depends on user environment
        _add_error(result, "import", exc)
        return _finalize_result(result, started)

    try:
        api = TdxHq_API(heartbeat=True, auto_retry=False)
        connect_started = time.perf_counter()
        connected = api.connect(candidate.host, candidate.port, time_out=timeout)
        result["latency_ms"] = round((time.perf_counter() - connect_started) * 1000, 3)
        result["connect_success"] = bool(connected)
        if not connected:
            result["error"] = "connect returned false"
            result["errors"]["connect"] = result["error"]
            return result

        _probe_realtime(api, result, symbol)
        _probe_minute_kline(api, result, symbol, minute_period, count)
        _probe_daily_kline(api, result, symbol, count)
        return result
    except Exception as exc:
        _add_error(result, "connect", exc)
        return result
    finally:
        result["total_latency_ms"] = round((time.perf_counter() - started) * 1000, 3)
        if api is not None:
            try:
                api.disconnect()
            except Exception:
                pass


def _empty_result(candidate: ServerCandidate) -> dict[str, Any]:
    return {
        "host": candidate.host,
        "port": candidate.port,
        "role": candidate.role,
        "source": candidate.source,
        "configured_role": candidate.role,
        "configured_latency_ms": candidate.configured_latency_ms,
        "name": candidate.name,
        "connect_success": False,
        "realtime_success": False,
        "realtime_quote_success": False,
        "minute_kline_success": False,
        "daily_kline_success": False,
        "kline_success": False,
        "latency_ms": None,
        "total_latency_ms": None,
        "realtime_count": 0,
        "realtime_quote_count": 0,
        "minute_kline_count": 0,
        "daily_kline_count": 0,
        "error": None,
        "errors": {},
    }


def _finalize_result(result: dict[str, Any], started: float) -> dict[str, Any]:
    result["total_latency_ms"] = round((time.perf_counter() - started) * 1000, 3)
    return result


def _probe_realtime(api: Any, result: dict[str, Any], symbol: str) -> None:
    try:
        rows = api.get_security_quotes([(market_for_symbol(symbol), code_for_symbol(symbol))])
        row_count = len(rows or [])
        result["realtime_count"] = row_count
        result["realtime_quote_count"] = row_count
        result["realtime_success"] = row_count > 0
        result["realtime_quote_success"] = row_count > 0
        if row_count == 0:
            result["errors"]["realtime"] = "empty response"
            result["error"] = result["error"] or "realtime empty response"
    except Exception as exc:
        _add_error(result, "realtime", exc)


def _probe_minute_kline(
    api: Any,
    result: dict[str, Any],
    symbol: str,
    period: str,
    count: int,
) -> None:
    try:
        rows = api.get_security_bars(
            PYTDX_KLINE_PERIOD_CATEGORIES[period],
            market_for_symbol(symbol),
            code_for_symbol(symbol),
            0,
            count,
        )
        row_count = len(rows or [])
        result["minute_kline_count"] = row_count
        result["minute_kline_success"] = row_count > 0
        result["kline_success"] = bool(
            result["minute_kline_success"] or result["daily_kline_success"]
        )
        if row_count == 0:
            result["errors"]["minute_kline"] = "empty response"
            result["error"] = result["error"] or "minute_kline empty response"
    except Exception as exc:
        _add_error(result, "minute_kline", exc)


def _probe_daily_kline(api: Any, result: dict[str, Any], symbol: str, count: int) -> None:
    try:
        rows = api.get_security_bars(
            PYTDX_KLINE_PERIOD_CATEGORIES["1d"],
            market_for_symbol(symbol),
            code_for_symbol(symbol),
            0,
            count,
        )
        row_count = len(rows or [])
        result["daily_kline_count"] = row_count
        result["daily_kline_success"] = row_count > 0
        result["kline_success"] = bool(
            result["minute_kline_success"] or result["daily_kline_success"]
        )
        if row_count == 0:
            result["errors"]["daily_kline"] = "empty response"
            result["error"] = result["error"] or "daily_kline empty response"
    except Exception as exc:
        _add_error(result, "daily_kline", exc)


def _add_error(result: dict[str, Any], key: str, exc: Exception) -> None:
    text = _error_text(exc)
    result["errors"][key] = text
    result["error"] = result["error"] or text


def _result_sort_key(result: dict[str, Any]) -> tuple[Any, ...]:
    latency = result["latency_ms"] if result["latency_ms"] is not None else 999999999
    minute_success = bool(result["minute_kline_success"])
    daily_success = bool(result["daily_kline_success"])
    return (
        not (minute_success and daily_success),
        not (minute_success or daily_success),
        not bool(result["connect_success"]),
        not bool(result.get("realtime_success") or result.get("realtime_quote_success")),
        latency,
        str(result["host"]),
        int(result["port"]),
    )


def _build_active_config(
    sorted_results: list[dict[str, Any]],
    *,
    active_count: int,
) -> list[dict[str, Any]]:
    useful = [
        result
        for result in sorted_results
        if result["connect_success"]
        and (
            result.get("realtime_success")
            or result.get("realtime_quote_success")
            or result["minute_kline_success"]
            or result["daily_kline_success"]
        )
    ]
    if not useful:
        useful = [result for result in sorted_results if result["connect_success"]]
    if active_count > 0:
        useful = useful[:active_count]

    entries: list[dict[str, Any]] = []
    for index, result in enumerate(useful):
        latency_ms = result["latency_ms"] if result["latency_ms"] is not None else 999999
        entries.append(
            {
                "host": result["host"],
                "port": int(result["port"]),
                "role": _role_for_index(index),
                "latency_ms": int(round(float(latency_ms))),
                "enabled": True,
            }
        )
    return entries


def _role_for_index(index: int) -> str:
    if index < len(ROLE_SEQUENCE):
        return ROLE_SEQUENCE[index]
    return "backup"


def _build_summary(
    *,
    started_at: datetime,
    finished_at: datetime,
    pytdx_import_error: str | None,
    official_sources: list[dict[str, Any]],
    official_candidates: list[ServerCandidate],
    config_total_count: int,
    local_total_count: int,
    candidates: list[ServerCandidate],
    results: list[dict[str, Any]],
    output_path: Path,
    active_entries: list[dict[str, Any]],
    symbol: str,
    minute_period: str,
    count: int,
    timeout: float,
    workers: int,
    limit: int,
) -> dict[str, Any]:
    connect_success_count = _count_success(results, "connect_success")
    realtime_success_count = _count_success(results, "realtime_success")
    minute_success_count = _count_success(results, "minute_kline_success")
    daily_success_count = _count_success(results, "daily_kline_success")
    return {
        "task": "018.2",
        "mode": "pytdx_server_probe",
        "created_at": started_at.isoformat(),
        "finished_at": finished_at.isoformat(),
        "duration_seconds": round((finished_at - started_at).total_seconds(), 3),
        "probe_parameters": {
            "symbol": symbol,
            "minute_period": minute_period,
            "count": count,
            "timeout": timeout,
            "workers": workers,
            "limit": limit,
        },
        "pytdx_package_import_error": pytdx_import_error,
        "official_pytdx_sources": official_sources,
        "official_pool_count": len(official_candidates),
        "config_pool_count": config_total_count,
        "local_pool_count": local_total_count,
        "probe_server_count": len(candidates),
        "connect_success_count": connect_success_count,
        "realtime_success_count": realtime_success_count,
        "minute_kline_success_count": minute_success_count,
        "daily_kline_success_count": daily_success_count,
        "fastest_available_server": _fastest_available_server(results),
        "active_config_generated": output_path.exists(),
        "active_config_path": _display_path(output_path),
        "active_config_server_count": len(active_entries),
        "results": results,
    }


def _count_success(results: list[dict[str, Any]], key: str) -> int:
    return sum(1 for result in results if result.get(key))


def _fastest_available_server(results: list[dict[str, Any]]) -> dict[str, Any] | None:
    useful = [
        result
        for result in results
        if result["connect_success"]
        and (
            result.get("realtime_success")
            or result.get("realtime_quote_success")
            or result["minute_kline_success"]
            or result["daily_kline_success"]
        )
    ]
    if not useful:
        useful = [result for result in results if result["connect_success"]]
    if not useful:
        return None
    fastest = sorted(useful, key=_result_sort_key)[0]
    return {
        "host": fastest["host"],
        "port": fastest["port"],
        "latency_ms": fastest["latency_ms"],
        "realtime_success": fastest.get("realtime_success"),
        "minute_kline_success": fastest["minute_kline_success"],
        "daily_kline_success": fastest["daily_kline_success"],
    }


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _display_path(path: Path) -> str:
    raw_path = Path(path)
    if not raw_path.is_absolute():
        return str(raw_path).replace("\\", "/")
    try:
        relative = raw_path.resolve().relative_to(Path.cwd().resolve())
    except (OSError, ValueError):
        return f"<external-path>/{raw_path.name}"
    return str(relative).replace("\\", "/")


def _error_text(exc: Exception) -> str:
    return f"{type(exc).__name__}: {exc}"


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
