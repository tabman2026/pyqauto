from __future__ import annotations

import json

import pandas as pd
import pytest

import astock_source_router.adapters.pytdx_adapter as pytdx_adapter
from astock_source_router.adapters.pytdx_adapter import (
    DEFAULT_PYTDX_SERVER_POOL,
    PytdxAdapter,
    parse_pytdx_server_pool,
)
from astock_source_router.core.errors import PytdxAllServersFailed
from astock_source_router.core.features import FULL_REALTIME_QUOTES, INDEX_REALTIME, MINUTE_KLINE
from astock_source_router.core.schema import (
    add_source_columns,
    coerce_standard_types,
    validate_dataframe,
)


class FakePytdxApi:
    def __init__(self, *, omit_open: bool = False) -> None:
        self.omit_open = omit_open

    def connect(self, ip: str, port: int, time_out: float = 5.0):
        return self

    def disconnect(self) -> None:
        return None

    def get_security_count(self, market: int) -> int:
        return 1000

    def get_security_list(self, market: int, start: int):
        if start != 0:
            return []
        if market == 0:
            return [
                {"code": "000001", "name": "平安银行"},
                {"code": "399001", "name": "深证成指"},
                {"code": "399006", "name": "创业板指"},
            ]
        return [
            {"code": "600519", "name": "贵州茅台"},
            {"code": "000001", "name": "上证指数"},
            {"code": "000300", "name": "沪深300"},
        ]

    def get_security_quotes(self, all_stock):
        rows = []
        for market, code in all_stock:
            base = {
                "market": market,
                "code": code,
                "price": 11.0 if code != "600519" else 1200.0,
                "last_close": 10.0 if code != "600519" else 1000.0,
                "open": 10.5 if code != "600519" else 1100.0,
                "high": 11.2 if code != "600519" else 1210.0,
                "low": 10.4 if code != "600519" else 1090.0,
                "vol": 100,
                "amount": 110000.0,
                "servertime": "10:30:00.000",
            }
            if self.omit_open:
                base.pop("open")
            rows.append(base)
        return rows

    def get_security_bars(self, category: int, market: int, code: str, start: int, count: int):
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


def _validated(feature: str, df: pd.DataFrame):
    with_source = add_source_columns(df, source="pytdx", latency_ms=1.0)
    with_source = coerce_standard_types(with_source)
    return validate_dataframe(feature, with_source, context={"min_expected_rows": len(df) or 1})


def test_pytdx_full_realtime_standardizes_required_fields() -> None:
    adapter = PytdxAdapter(
        server_pool=[("127.0.0.1", 7709)],
        api_factory=FakePytdxApi,
    )

    df = adapter.fetch_full_realtime_quotes(["000001", "600519"])
    quality = _validated(FULL_REALTIME_QUOTES, df)

    assert quality.is_valid
    assert df.loc[df["code"] == "000001", "name"].iloc[0] == "平安银行"
    assert df.loc[df["code"] == "600519", "name"].iloc[0] == "贵州茅台"
    assert round(float(df.loc[df["code"] == "000001", "pct_chg"].iloc[0]), 6) == 10.0


def test_pytdx_index_realtime_standardizes_four_indexes() -> None:
    adapter = PytdxAdapter(
        server_pool=[("127.0.0.1", 7709)],
        api_factory=FakePytdxApi,
    )

    df = adapter.fetch_index_realtime(["000001", "399001", "399006", "000300"])
    quality = _validated(INDEX_REALTIME, df)

    assert quality.is_valid
    assert set(df["code"]) == {"000001", "399001", "399006", "000300"}
    assert df.loc[df["code"] == "000300", "name"].iloc[0] == "沪深300"


def test_pytdx_minute_kline_standardizes_fields() -> None:
    adapter = PytdxAdapter(
        server_pool=[("127.0.0.1", 7709)],
        api_factory=FakePytdxApi,
    )

    df = adapter.fetch_minute_kline("000001", period="5")
    quality = _validated(MINUTE_KLINE, df)

    assert quality.is_valid
    assert list(df.columns) == ["datetime", "code", "open", "high", "low", "close", "volume", "amount"]


def test_pytdx_fails_over_instead_of_fabricating_missing_ohlc() -> None:
    adapter = PytdxAdapter(
        server_pool=[("127.0.0.1", 7709)],
        api_factory=lambda: FakePytdxApi(omit_open=True),
    )

    with pytest.raises(PytdxAllServersFailed) as exc_info:
        adapter.fetch_full_realtime_quotes(["000001"])

    assert exc_info.value.attempts[0]["error_type"] == "quote_schema_missing"


def test_pytdx_server_pool_reads_only_active_pass_servers(tmp_path, monkeypatch) -> None:
    active_path = tmp_path / "pytdx_servers_active.json"
    active_path.write_text(
        json.dumps(
            {
                "servers": [
                    {
                        "ip": "1.1.1.1",
                        "port": 7709,
                        "grade": "primary",
                        "connect_status": "PASS",
                        "quote_status": "PASS",
                    },
                    {
                        "ip": "2.2.2.2",
                        "port": 7709,
                        "grade": "disabled",
                        "connect_status": "FAIL",
                        "quote_status": "FAIL",
                    },
                ]
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(pytdx_adapter, "ACTIVE_SERVER_POOL_PATH", active_path)
    monkeypatch.delenv("PYTDX_SERVER_POOL", raising=False)

    assert parse_pytdx_server_pool() == [("1.1.1.1", 7709)]


def test_pytdx_server_pool_empty_active_config_falls_back_to_default(tmp_path, monkeypatch) -> None:
    active_path = tmp_path / "pytdx_servers_active.json"
    active_path.write_text(
        json.dumps(
            {
                "servers": [
                    {
                        "ip": "2.2.2.2",
                        "port": 7709,
                        "grade": "disabled",
                        "connect_status": "FAIL",
                        "quote_status": "FAIL",
                    }
                ]
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(pytdx_adapter, "ACTIVE_SERVER_POOL_PATH", active_path)
    monkeypatch.delenv("PYTDX_SERVER_POOL", raising=False)

    assert parse_pytdx_server_pool() == DEFAULT_PYTDX_SERVER_POOL
