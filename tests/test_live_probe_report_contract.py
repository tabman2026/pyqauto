from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from pyqauto.adapters.akshare_em_spot_adapter import AkShareEmSpotAdapter
from pyqauto.adapters.base import PytdxServer, code_for_symbol
from pyqauto.adapters.easyquotation_sina_adapter import EasyQuotationSinaAdapter
from pyqauto.adapters.easyquotation_tencent_adapter import EasyQuotationTencentAdapter
from pyqauto.adapters.pytdx_adapter import PytdxAdapter
from pyqauto.source_schema_live import run_source_schema_probe_live


class FakeAkShareAdapter(AkShareEmSpotAdapter):
    def fetch_raw(
        self,
        symbols: list[str] | None = None,
        *,
        source_api: str | None = None,
    ) -> list[dict[str, Any]]:
        return [
            _akshare_row("600519", "贵州茅台", 123, 456789),
            _akshare_row("000001", "平安银行", 321, 654321),
        ]


class FakeEasyQuotationSinaAdapter(EasyQuotationSinaAdapter):
    def fetch_raw(
        self,
        symbols: list[str] | None = None,
        *,
        source_api: str | None = None,
    ) -> dict[str, dict[str, Any]]:
        return {
            "600519": _easy_row("贵州茅台", 1200),
            "000001": _easy_row("平安银行", 10.5),
        }


class FakeEasyQuotationTencentAdapter(EasyQuotationTencentAdapter):
    def fetch_raw(
        self,
        symbols: list[str] | None = None,
        *,
        source_api: str | None = None,
    ) -> dict[str, dict[str, Any]]:
        return {
            "600519": _easy_row("贵州茅台", 1200),
            "000001": _easy_row("平安银行", 10.5),
        }


class FakePytdxAdapter(PytdxAdapter):
    def __init__(self) -> None:
        super().__init__(PytdxServer("127.0.0.1", 7709, "primary", 1))

    def fetch_raw(
        self,
        *,
        source_api: str,
        symbols: list[str] | None = None,
        symbol: str | None = None,
        period: str = "1m",
        count: int = 240,
        category: int | None = None,
    ) -> list[dict[str, Any]]:
        if source_api == "pytdx.get_security_quotes":
            return [_pytdx_quote_row(code_for_symbol(item)) for item in symbols or []]
        if source_api == "pytdx.get_security_bars" and symbol:
            return [_pytdx_kline_row(symbol)]
        return []


def test_live_probe_report_contract_writes_json_and_jsonl(
    tmp_path: Path,
    monkeypatch,
) -> None:
    monkeypatch.chdir(tmp_path)
    report_path = tmp_path / "reports" / "latest" / "source_schema_probe_live.json"
    log_path = tmp_path / "logs" / "source_schema_probe_live.jsonl"

    payload = run_source_schema_probe_live(
        report_path=report_path,
        log_path=log_path,
        adapters={
            "akshare_em_spot": FakeAkShareAdapter(),
            "pytdx": FakePytdxAdapter(),
            "easyquotation_sina": FakeEasyQuotationSinaAdapter(),
            "easyquotation_tencent": FakeEasyQuotationTencentAdapter(),
        },
    )

    assert report_path.exists()
    assert log_path.exists()
    assert json.loads(report_path.read_text(encoding="utf-8")) == payload
    assert len(log_path.read_text(encoding="utf-8").splitlines()) == 5

    for key in [
        "overall_status",
        "checked_at",
        "sources",
        "source_status",
        "schema_status",
        "missing_fields",
        "schema_drift_fields",
        "rejected_reason",
        "error_message",
        "accepted_record_count",
        "rejected_record_count",
    ]:
        assert key in payload
    assert payload["overall_status"] == "PASS"
    assert payload["accepted_record_count"] > 0
    assert payload["rejected_record_count"] == 0

    for source in payload["sources"]:
        assert source["source_status"] == "ok"
        assert source["schema_status"] == "ok"
        assert source["missing_fields"] == []
        assert source["schema_drift_fields"] == []
        assert source["rejected_reason"] is None
        assert source["accepted_record_count"] > 0

    akshare_probe = _probe(payload, "akshare.stock_zh_a_spot_em")
    assert akshare_probe["raw_to_standard_mapping"]["volume_shares"] == ["成交量"]
    assert akshare_probe["standard_sample"][0]["volume_shares"] == 12300
    assert akshare_probe["standard_sample"][0]["amount_yuan"] == 456789


def _akshare_row(code: str, name: str, volume_lots: int, amount_yuan: int) -> dict[str, Any]:
    return {
        "代码": code,
        "名称": name,
        "最新价": 1200 if code == "600519" else 10.5,
        "昨收": 1190 if code == "600519" else 10,
        "今开": 1195 if code == "600519" else 10.1,
        "最高": 1210 if code == "600519" else 10.8,
        "最低": 1188 if code == "600519" else 9.9,
        "成交量": volume_lots,
        "成交额": amount_yuan,
    }


def _easy_row(name: str, price: float) -> dict[str, Any]:
    return {
        "name": name,
        "now": price,
        "close": price - 1,
        "open": price - 0.5,
        "high": price + 1,
        "low": price - 2,
        "turnover": 1000,
        "volume": 100000,
        "date": "2026-06-21",
        "time": "10:00:00",
    }


def _pytdx_quote_row(code: str) -> dict[str, Any]:
    price = 1200 if code == "600519" else 10.5
    return {
        "market": 1 if code == "600519" else 0,
        "code": code,
        "price": price,
        "last_close": price - 1,
        "open": price - 0.5,
        "high": price + 1,
        "low": price - 2,
        "vol": 1000,
        "amount": 100000,
        "servertime": "10:00:00",
    }


def _pytdx_kline_row(code: str) -> dict[str, Any]:
    price = 1200 if code == "600519" else 10.5
    return {
        "datetime": "2026-06-21",
        "open": price - 0.5,
        "high": price + 1,
        "low": price - 2,
        "close": price,
        "vol": 1000,
        "amount": 100000,
    }


def _probe(report: dict[str, Any], source_api: str) -> dict[str, Any]:
    for probe in report["probes"]:
        if probe["source_api"] == source_api:
            return probe
    raise AssertionError(source_api)
