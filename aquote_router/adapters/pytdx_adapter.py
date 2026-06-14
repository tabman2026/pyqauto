"""pytdx quote adapter."""

from __future__ import annotations

from typing import Any

from aquote_router.adapters.base import (
    BaseQuoteAdapter,
    PytdxServer,
    as_float,
    first_value,
    market_for_symbol,
)
from aquote_router.exceptions import AdapterError, SourceUnavailableError
from aquote_router.models import QuoteRecord


class PytdxAdapter(BaseQuoteAdapter):
    """Adapter for one pytdx server entry."""

    source = "pytdx"

    def __init__(self, server: PytdxServer, *, timeout: float = 3.0) -> None:
        self.server = server
        self.source_level = server.role
        self.timeout = timeout

    def realtime_quotes(
        self, symbols: list[str], *, include_raw: bool = False
    ) -> list[QuoteRecord]:
        return self._security_quotes(symbols, include_raw=include_raw)

    def full_realtime_quotes(
        self, symbols: list[str], *, include_raw: bool = False
    ) -> list[QuoteRecord]:
        return self._security_quotes(symbols, include_raw=include_raw)

    def index_realtime(
        self, symbols: list[str], *, include_raw: bool = False
    ) -> list[QuoteRecord]:
        return self._security_quotes(symbols, include_raw=include_raw)

    def minute_kline(
        self,
        symbol: str,
        *,
        period: str = "1m",
        count: int = 240,
        include_raw: bool = False,
    ) -> list[QuoteRecord]:
        category = {
            "1m": 7,
            "5m": 0,
            "15m": 1,
            "30m": 2,
            "60m": 3,
        }.get(period)
        if category is None:
            raise AdapterError(f"unsupported pytdx minute period: {period}")

        api = self._new_api()
        self._connect(api)
        try:
            rows = api.get_security_bars(
                category, market_for_symbol(symbol), symbol, 0, count
            )
        finally:
            self._disconnect(api)

        if not rows:
            raise SourceUnavailableError("pytdx returned no minute_kline records")
        return [
            self._normalize_kline_row(symbol, row, include_raw=include_raw)
            for row in rows
        ]

    def _security_quotes(
        self, symbols: list[str], *, include_raw: bool = False
    ) -> list[QuoteRecord]:
        if not symbols:
            return []

        api = self._new_api()
        self._connect(api)
        try:
            request_symbols = [
                (market_for_symbol(symbol), symbol) for symbol in symbols
            ]
            rows = api.get_security_quotes(request_symbols)
        finally:
            self._disconnect(api)

        if not rows:
            raise SourceUnavailableError("pytdx returned no quote records")
        return [
            self._normalize_quote_row(row, include_raw=include_raw)
            for row in rows
        ]

    def _new_api(self) -> Any:
        try:
            from pytdx.hq import TdxHq_API
        except Exception as exc:  # pragma: no cover - depends on user env
            raise AdapterError("pytdx package is not available") from exc
        return TdxHq_API(heartbeat=True, auto_retry=False)

    def _connect(self, api: Any) -> None:
        connected = api.connect(self.server.host, self.server.port, time_out=self.timeout)
        if not connected:
            raise SourceUnavailableError("pytdx server connection failed")

    def _disconnect(self, api: Any) -> None:
        try:
            api.disconnect()
        except Exception:
            return

    def _normalize_quote_row(
        self, row: dict[str, Any], *, include_raw: bool
    ) -> QuoteRecord:
        symbol = str(first_value(row, ("code", "symbol")) or "")
        return QuoteRecord(
            symbol=symbol,
            name=first_value(row, ("name",)),
            price=as_float(first_value(row, ("price", "now", "close"))),
            open=as_float(first_value(row, ("open",))),
            high=as_float(first_value(row, ("high",))),
            low=as_float(first_value(row, ("low",))),
            pre_close=as_float(first_value(row, ("last_close", "pre_close", "close"))),
            volume=as_float(first_value(row, ("vol", "volume"))),
            amount=as_float(first_value(row, ("amount",))),
            datetime=str(first_value(row, ("datetime", "time")) or "") or None,
            source=self.source,
            source_level=self.source_level,
            raw=dict(row) if include_raw else None,
        )

    def _normalize_kline_row(
        self, symbol: str, row: dict[str, Any], *, include_raw: bool
    ) -> QuoteRecord:
        return QuoteRecord(
            symbol=symbol,
            price=as_float(first_value(row, ("close", "price"))),
            open=as_float(first_value(row, ("open",))),
            high=as_float(first_value(row, ("high",))),
            low=as_float(first_value(row, ("low",))),
            volume=as_float(first_value(row, ("vol", "volume"))),
            amount=as_float(first_value(row, ("amount",))),
            datetime=str(first_value(row, ("datetime", "time")) or "") or None,
            source=self.source,
            source_level=self.source_level,
            raw=dict(row) if include_raw else None,
        )
