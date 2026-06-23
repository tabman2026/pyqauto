from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any

import pandas as pd
import pytest

from astock_source_router.adapters.pytdx_adapter import (
    PytdxAdapter,
    PytdxServer,
    load_pytdx_server_pool_records,
)
from astock_source_router.core.adapter_base import BaseMarketDataAdapter
from astock_source_router.core.errors import PytdxAllServersFailed
from astock_source_router.core.features import (
    FULL_REALTIME_QUOTES,
    INDEX_REALTIME,
    LITE_REALTIME_QUOTES,
    REALTIME_QUOTES,
)
from astock_source_router.core.models import RouterConfig
from astock_source_router.core.policy import DEFAULT_SOURCE_POLICY, SourcePolicy
from astock_source_router.core.router import MarketRouter


class FakeTdxParams:
    MARKET_SZ = 0
    MARKET_SH = 1
    KLINE_TYPE_1MIN = 1
    KLINE_TYPE_5MIN = 5
    KLINE_TYPE_15MIN = 15
    KLINE_TYPE_30MIN = 30
    KLINE_TYPE_1HOUR = 60


class RuntimeFakePytdxApi:
    def __init__(self, behavior: dict[str, str], calls: list[tuple[str, str]]) -> None:
        self.behavior = behavior
        self.calls = calls
        self.ip = ""

    def connect(self, ip: str, port: int, time_out: float = 5.0):
        self.ip = ip
        self.calls.append(("connect", ip))
        action = self.behavior.get(ip, "ok")
        if action == "connect_timeout":
            raise TimeoutError("connect timed out")
        if action == "connect_failed":
            return False
        return self

    def disconnect(self) -> None:
        return None

    def get_security_quotes(self, targets):
        self.calls.append(("quotes", self.ip))
        action = self.behavior.get(self.ip, "ok")
        if action == "quote_timeout":
            raise TimeoutError("quote timed out")
        if action == "quote_empty":
            return []
        rows = []
        for market, code in targets:
            row = {
                "market": market,
                "code": code,
                "price": 11.0,
                "last_close": 10.0,
                "open": 10.5,
                "high": 11.2,
                "low": 10.4,
                "vol": 100,
                "amount": 110000.0,
                "servertime": "10:30:00.000",
            }
            if action == "quote_schema_missing":
                row.pop("open")
            if action == "quote_invalid_value":
                row["price"] = None
            rows.append(row)
        return rows

    def get_security_bars(self, category: int, market: int, code: str, start: int, count: int):
        self.calls.append(("bars", self.ip))
        action = self.behavior.get(self.ip, "ok")
        if action == "quote_empty":
            return []
        return [
            {
                "datetime": "2026-06-12 10:30",
                "open": 10.5,
                "high": 11.0,
                "low": 10.4,
                "close": 10.9,
                "vol": 1000,
                "amount": 109000.0,
            }
        ]


class NamedRealtimeAdapter(BaseMarketDataAdapter):
    supported_features = {REALTIME_QUOTES, FULL_REALTIME_QUOTES, INDEX_REALTIME}
    default_min_interval_seconds = 0.0

    def __init__(self, name: str) -> None:
        self.name = name

    def _frame(self, codes=None) -> pd.DataFrame:
        code = "000001"
        if isinstance(codes, (list, tuple)) and codes:
            code = str(codes[0])
        elif isinstance(codes, str):
            code = codes
        return pd.DataFrame(
            [
                {
                    "date": "2026-06-12",
                    "time": "10:30:00",
                    "code": code,
                    "name": "fallback",
                    "last_price": 10.1,
                    "pre_close": 10.0,
                    "open": 10.0,
                    "high": 10.2,
                    "low": 9.9,
                    "volume": 1000,
                    "amount": 10100.0,
                    "pct_chg": 1.0,
                }
            ]
        )

    def fetch_realtime_quotes(self, codes=None) -> pd.DataFrame:
        return self._frame(codes)

    def fetch_full_realtime_quotes(self, codes=None) -> pd.DataFrame:
        return self._frame(codes)

    def fetch_index_realtime(self, codes=None) -> pd.DataFrame:
        return self._frame(codes)


def _patch_tdx(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(PytdxAdapter, "_tdx", lambda self: (RuntimeFakePytdxApi, FakeTdxParams))


def _api_factory(behavior: dict[str, str], calls: list[tuple[str, str]]):
    return lambda: RuntimeFakePytdxApi(behavior, calls)


def _servers() -> list[PytdxServer]:
    return [
        PytdxServer("primary", 7709, role="primary", latency_ms=10.0),
        PytdxServer("hot", 7709, role="hot_backup", latency_ms=20.0),
        PytdxServer("backup", 7709, role="backup", latency_ms=5.0),
    ]


def _write_active_pool(path: Path, servers: list[dict[str, Any]]) -> None:
    path.write_text(json.dumps({"servers": servers}, ensure_ascii=False), encoding="utf-8")


def test_active_pool_loads_and_sorts_by_role_then_latency(tmp_path: Path) -> None:
    active_path = tmp_path / "pytdx_servers_active.json"
    _write_active_pool(
        active_path,
        [
            {"ip": "backup-fast", "port": 7709, "grade": "backup", "latency_ms": 1, "connect_status": "PASS", "quote_status": "PASS"},
            {"ip": "primary-slow", "port": 7709, "grade": "primary", "latency_ms": 50, "connect_status": "PASS", "quote_status": "PASS"},
            {"ip": "primary-fast", "port": 7709, "grade": "primary", "latency_ms": 20, "connect_status": "PASS", "quote_status": "PASS"},
            {"ip": "hot", "port": 7709, "grade": "hot_backup", "latency_ms": 10, "connect_status": "PASS", "quote_status": "PASS"},
            {"ip": "disabled", "port": 7709, "grade": "disabled", "connect_status": "PASS", "quote_status": "PASS"},
            {"ip": "quote-fail", "port": 7709, "grade": "backup", "connect_status": "PASS", "quote_status": "FAIL"},
        ],
    )

    records, warnings = load_pytdx_server_pool_records(active_config_path=active_path)

    assert warnings == []
    assert [server.ip for server in records] == ["primary-fast", "primary-slow", "hot", "backup-fast"]


def test_disabled_servers_are_skipped_from_active_pool(tmp_path: Path) -> None:
    active_path = tmp_path / "pytdx_servers_active.json"
    _write_active_pool(
        active_path,
        [
            {"ip": "ok", "port": 7709, "grade": "backup", "connect_status": "PASS", "quote_status": "PASS"},
            {"ip": "disabled", "port": 7709, "grade": "disabled", "connect_status": "PASS", "quote_status": "PASS"},
            {"ip": "connect-fail", "port": 7709, "grade": "backup", "connect_status": "FAIL", "quote_status": "PASS"},
        ],
    )

    records, _warnings = load_pytdx_server_pool_records(active_config_path=active_path)

    assert [server.ip for server in records] == ["ok"]


def test_primary_success_does_not_touch_backup(monkeypatch: pytest.MonkeyPatch) -> None:
    _patch_tdx(monkeypatch)
    calls: list[tuple[str, str]] = []
    adapter = PytdxAdapter(
        server_pool=_servers(),
        api_factory=_api_factory({}, calls),
        name_lookup_enabled=False,
    )

    df = adapter.fetch_realtime_quotes(["000001"])

    assert calls == [("connect", "primary"), ("quotes", "primary")]
    metadata = df.attrs["pytdx_runtime_failover"]
    assert metadata["pytdx_server_ip"] == "primary"
    assert metadata["failover_count"] == 0


def test_primary_failure_switches_to_hot_backup(monkeypatch: pytest.MonkeyPatch) -> None:
    _patch_tdx(monkeypatch)
    calls: list[tuple[str, str]] = []
    adapter = PytdxAdapter(
        server_pool=_servers(),
        api_factory=_api_factory({"primary": "connect_failed"}, calls),
        name_lookup_enabled=False,
    )

    df = adapter.fetch_full_realtime_quotes(["000001"])
    metadata = df.attrs["pytdx_runtime_failover"]

    assert [call for call in calls if call[0] == "connect"] == [
        ("connect", "primary"),
        ("connect", "hot"),
    ]
    assert metadata["pytdx_server_ip"] == "hot"
    assert metadata["pytdx_server_role"] == "hot_backup"
    assert metadata["pytdx_failover_attempts"][0]["error_type"] == "connect_failed"


def test_primary_and_hot_failure_switches_to_backup(monkeypatch: pytest.MonkeyPatch) -> None:
    _patch_tdx(monkeypatch)
    calls: list[tuple[str, str]] = []
    adapter = PytdxAdapter(
        server_pool=_servers(),
        api_factory=_api_factory(
            {"primary": "quote_empty", "hot": "quote_schema_missing"},
            calls,
        ),
        name_lookup_enabled=False,
    )

    df = adapter.fetch_index_realtime(["000001"])
    metadata = df.attrs["pytdx_runtime_failover"]

    assert metadata["pytdx_server_ip"] == "backup"
    assert [attempt["error_type"] for attempt in metadata["pytdx_failover_attempts"][:2]] == [
        "quote_empty",
        "quote_schema_missing",
    ]


def test_all_pytdx_servers_failed_raises_fallback_exception(monkeypatch: pytest.MonkeyPatch) -> None:
    _patch_tdx(monkeypatch)
    calls: list[tuple[str, str]] = []
    adapter = PytdxAdapter(
        server_pool=_servers()[:2],
        api_factory=_api_factory({"primary": "connect_timeout", "hot": "quote_invalid_value"}, calls),
        name_lookup_enabled=False,
    )

    with pytest.raises(PytdxAllServersFailed) as exc_info:
        adapter.fetch_realtime_quotes(["000001"])

    assert [attempt["error_type"] for attempt in exc_info.value.attempts] == [
        "connect_timeout",
        "quote_invalid_value",
    ]


def test_router_fallback_trace_and_sqlite_include_pytdx_attempts(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _patch_tdx(monkeypatch)
    calls: list[tuple[str, str]] = []
    pytdx = PytdxAdapter(
        server_pool=_servers()[:2],
        api_factory=_api_factory({"primary": "connect_failed", "hot": "quote_empty"}, calls),
        name_lookup_enabled=False,
    )
    config = RouterConfig(
        cache_dir=tmp_path / "cache",
        log_dir=tmp_path / "logs",
        enable_cache=False,
        min_interval_seconds={"pytdx": 0.0, "easyquotation_sina": 0.0, "easyquotation_tencent": 0.0},
    )
    policy = SourcePolicy({REALTIME_QUOTES: ["pytdx", "easyquotation_sina", "easyquotation_tencent"]})
    router = MarketRouter(
        config=config,
        source_policy=policy,
        adapters=[pytdx, NamedRealtimeAdapter("easyquotation_sina"), NamedRealtimeAdapter("easyquotation_tencent")],
        auto_register=False,
    )

    result = router.fetch_result(REALTIME_QUOTES, codes=["000001"])

    assert result.source == "easyquotation_sina"
    assert result.fallback_trace[0]["source"] == "pytdx"
    assert len(result.fallback_trace[0]["pytdx_failover_attempts"]) == 2
    line = (tmp_path / "logs" / "source_router.jsonl").read_text(encoding="utf-8").splitlines()[-1]
    payload = json.loads(line)
    assert payload["pytdx_runtime_failover"]["fallback_to_source"] == "easyquotation_sina"
    with sqlite3.connect(tmp_path / "logs" / "source_router.db") as conn:
        row = conn.execute(
            "SELECT pytdx_all_failed, fallback_to_source FROM pytdx_runtime_failover_trace"
        ).fetchone()
    assert row == (1, "easyquotation_sina")


def test_source_policy_and_lite_full_boundary_are_preserved() -> None:
    assert DEFAULT_SOURCE_POLICY[REALTIME_QUOTES] == [
        "pytdx",
        "easyquotation_sina",
        "easyquotation_tencent",
    ]
    assert DEFAULT_SOURCE_POLICY[FULL_REALTIME_QUOTES] == [
        "pytdx",
        "easyquotation_sina",
        "easyquotation_tencent",
    ]
    assert DEFAULT_SOURCE_POLICY[LITE_REALTIME_QUOTES] == ["adata"]
    assert "adata" not in DEFAULT_SOURCE_POLICY[FULL_REALTIME_QUOTES]
