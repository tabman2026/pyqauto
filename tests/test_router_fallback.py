from __future__ import annotations

import pytest

from aquote_router.adapters.base import BaseQuoteAdapter
from aquote_router.exceptions import NoAvailableSourceError, SourceUnavailableError
from aquote_router.models import QuoteRecord
from aquote_router.policy import SourcePolicy
from aquote_router.router import QuoteRouter


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
        self.calls: list[str] = []

    def realtime_quotes(self, symbols: list[str], *, include_raw: bool = False):
        self.calls.append("realtime_quotes")
        if self.fail:
            raise SourceUnavailableError(f"{self.source} failed")
        return [QuoteRecord(symbol=symbol, price=1.0) for symbol in symbols]

    def full_realtime_quotes(self, symbols: list[str], *, include_raw: bool = False):
        self.calls.append("full_realtime_quotes")
        if self.fail:
            raise SourceUnavailableError(f"{self.source} failed")
        return [QuoteRecord(symbol=symbol, price=2.0) for symbol in symbols]

    def index_realtime(self, symbols: list[str], *, include_raw: bool = False):
        self.calls.append("index_realtime")
        if self.fail:
            raise SourceUnavailableError(f"{self.source} failed")
        return [QuoteRecord(symbol=symbol, price=3.0) for symbol in symbols]

    def minute_kline(
        self,
        symbol: str,
        *,
        period: str = "1m",
        count: int = 240,
        include_raw: bool = False,
    ):
        self.calls.append("minute_kline")
        if self.fail:
            raise SourceUnavailableError(f"{self.source} failed")
        return [QuoteRecord(symbol=symbol, price=4.0)]


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
                },
            }
        }
    )


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


def test_primary_failure_falls_back_to_hot_backup() -> None:
    router = make_router(
        [
            FakeAdapter("pytdx", "primary", fail=True),
            FakeAdapter("pytdx", "hot_backup"),
            FakeAdapter("pytdx", "backup"),
        ]
    )

    records = router.realtime_quotes(["000001"])

    assert records[0].source == "pytdx"
    assert records[0].source_level == "hot_backup"
    assert records[0].is_fallback is True
    assert records[0].fallback_from == "pytdx:primary"


def test_primary_and_hot_backup_failure_falls_back_to_backup() -> None:
    router = make_router(
        [
            FakeAdapter("pytdx", "primary", fail=True),
            FakeAdapter("pytdx", "hot_backup", fail=True),
            FakeAdapter("pytdx", "backup"),
        ]
    )

    records = router.full_realtime_quotes(["000001"])

    assert records[0].source_level == "backup"
    assert records[0].fallback_from == "pytdx:hot_backup"


def test_all_pytdx_failure_falls_back_to_sina() -> None:
    sina = FakeAdapter("easyquotation_sina")
    router = make_router(
        [
            FakeAdapter("pytdx", "primary", fail=True),
            FakeAdapter("pytdx", "hot_backup", fail=True),
            FakeAdapter("pytdx", "backup", fail=True),
        ],
        sina=sina,
        tencent=FakeAdapter("easyquotation_tencent"),
    )

    records = router.index_realtime(["000001"])

    assert records[0].source == "easyquotation_sina"
    assert records[0].fallback_from == "pytdx:backup"
    assert sina.calls == ["index_realtime"]


def test_sina_failure_falls_back_to_tencent() -> None:
    tencent = FakeAdapter("easyquotation_tencent")
    router = make_router(
        [
            FakeAdapter("pytdx", "primary", fail=True),
            FakeAdapter("pytdx", "hot_backup", fail=True),
            FakeAdapter("pytdx", "backup", fail=True),
        ],
        sina=FakeAdapter("easyquotation_sina", fail=True),
        tencent=tencent,
    )

    records = router.realtime_quotes(["000001"])

    assert records[0].source == "easyquotation_tencent"
    assert records[0].fallback_from == "easyquotation_sina"
    assert tencent.calls == ["realtime_quotes"]


def test_minute_kline_never_uses_easyquotation() -> None:
    sina = FakeAdapter("easyquotation_sina")
    router = make_router(
        [
            FakeAdapter("pytdx", "primary", fail=True),
            FakeAdapter("pytdx", "hot_backup", fail=True),
            FakeAdapter("pytdx", "backup", fail=True),
        ],
        sina=sina,
        tencent=FakeAdapter("easyquotation_tencent"),
    )

    with pytest.raises(NoAvailableSourceError):
        router.minute_kline("000001", period="1m")

    assert sina.calls == []
