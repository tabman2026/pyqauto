from __future__ import annotations

import json
from pathlib import Path

import pytest

from pyqauto.adapters.base import BaseQuoteAdapter
from pyqauto.exceptions import NoAvailableSourceError, SourceUnavailableError
from pyqauto.governance.state_machine import SystemState
from pyqauto.models import KlineBar, QuoteRecord
from pyqauto.policy import SourcePolicy
from pyqauto.router import QuoteRouter


class FakeAdapter(BaseQuoteAdapter):
    def __init__(
        self,
        source: str,
        source_level: str | None = None,
        *,
        fail: bool = False,
    ) -> None:
        self.source = source
        self.source_level = source_level
        self.fail = fail

    def realtime_quotes(self, symbols: list[str], *, include_raw: bool = False):
        if self.fail:
            raise SourceUnavailableError(f"{self.source} failed")
        return [QuoteRecord(symbol=symbol, price=1.0) for symbol in symbols]

    def full_realtime_quotes(self, symbols: list[str], *, include_raw: bool = False):
        return self.realtime_quotes(symbols, include_raw=include_raw)

    def index_realtime(self, symbols: list[str], *, include_raw: bool = False):
        return self.realtime_quotes(symbols, include_raw=include_raw)

    def minute_kline(
        self,
        symbol: str,
        *,
        period: str = "1m",
        count: int = 240,
        include_raw: bool = False,
    ):
        if self.fail:
            raise SourceUnavailableError(f"{self.source} failed")
        return [KlineBar(symbol=symbol, close=1.0, period=period)]

    def daily_kline(
        self,
        symbol: str,
        *,
        count: int = 120,
        include_raw: bool = False,
    ):
        if self.fail:
            raise SourceUnavailableError(f"{self.source} failed")
        return [KlineBar(symbol=symbol, close=1.0, period="1d")]


def test_router_fallback_updates_governance_to_degraded(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    router = make_router(
        [FakeAdapter("pytdx", "primary", fail=True)],
        sina=FakeAdapter("easyquotation_sina"),
    )

    records = router.realtime_quotes(["000001"])

    assert records[0].is_fallback is True
    assert router.get_system_state() == SystemState.DEGRADED
    trace = router.decision_trace()
    assert trace["system_state"] == "DEGRADED"
    assert trace["why_this_state"]
    assert trace["failed_sources"] == ["pytdx:primary"]
    assert trace["fallback_chain"] == ["pytdx:primary"]
    assert trace["schema_validation_result"]["status"] == "not_checked"
    assert router.health()["pytdx_health_score"] < 100.0


def test_router_all_sources_fail_updates_governance_to_readonly(
    tmp_path: Path,
    monkeypatch,
) -> None:
    monkeypatch.chdir(tmp_path)
    router = make_router(
        [FakeAdapter("pytdx", "primary", fail=True)],
        sina=FakeAdapter("easyquotation_sina", fail=True),
        tencent=FakeAdapter("easyquotation_tencent", fail=True),
    )

    with pytest.raises(NoAvailableSourceError):
        router.realtime_quotes(["000001"])

    assert router.get_system_state() == SystemState.READONLY
    assert router.decision_trace()["all_sources_failed"] is True


def test_router_status_observes_live_probe_schema_drift(
    tmp_path: Path,
    monkeypatch,
) -> None:
    monkeypatch.chdir(tmp_path)
    report_path = tmp_path / "reports" / "latest" / "source_schema_probe_live.json"
    report_path.parent.mkdir(parents=True)
    payload = {
        "run_id": "probe-1",
        "overall_status": "WARN",
        "source_status": {"akshare_em_spot::akshare.stock_zh_a_spot_em": "schema_drift"},
        "schema_status": {"akshare_em_spot::akshare.stock_zh_a_spot_em": "schema_drift"},
        "sources": [
            {
                "source_name": "akshare_em_spot",
                "source_api": "akshare.stock_zh_a_spot_em",
                "source_status": "schema_drift",
                "schema_status": "schema_drift",
                "schema_drift_fields": ["last_price"],
                "error_message": None,
            }
        ],
    }
    report_path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    router = make_router([FakeAdapter("pytdx", "primary")])

    status = router.status()

    assert router.get_system_state() == SystemState.BLOCKED
    assert status["system_state"] == "BLOCKED"
    assert status["latest_decision_trace"]["schema_validation_result"]["schema_drift_fields"] == [
        "akshare_em_spot:last_price"
    ]
    assert status["health"]["akshare_health_score"] < 100.0


def make_router(
    pytdx_adapters: list[BaseQuoteAdapter],
    sina: BaseQuoteAdapter | None = None,
    tencent: BaseQuoteAdapter | None = None,
) -> QuoteRouter:
    return QuoteRouter(
        policy=make_policy(),
        pytdx_adapters=pytdx_adapters,
        easyquotation_sina_adapter=sina,
        easyquotation_tencent_adapter=tencent,
    )


def make_policy() -> SourcePolicy:
    return SourcePolicy.from_dict(
        {
            "apis": {
                "realtime_quotes": {
                    "allow_fallback": True,
                    "fallback_order": [
                        "pytdx",
                        "easyquotation_sina",
                        "easyquotation_tencent",
                    ],
                },
                "full_realtime_quotes": {
                    "allow_fallback": True,
                    "fallback_order": [
                        "pytdx",
                        "easyquotation_sina",
                        "easyquotation_tencent",
                    ],
                },
                "index_realtime": {
                    "allow_fallback": True,
                    "fallback_order": [
                        "pytdx",
                        "easyquotation_sina",
                        "easyquotation_tencent",
                    ],
                },
                "minute_kline": {
                    "allow_fallback": False,
                    "fallback_order": ["pytdx"],
                    "supported_periods": ["1m", "5m", "15m", "30m", "60m"],
                },
                "daily_kline": {
                    "allow_fallback": False,
                    "fallback_order": ["pytdx"],
                    "supported_periods": ["1d"],
                },
                "kline": {
                    "allow_fallback": False,
                    "fallback_order": ["pytdx"],
                    "supported_periods": ["1m", "5m", "15m", "30m", "60m", "1d"],
                },
            }
        }
    )
