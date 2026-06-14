"""easyquotation Sina adapter."""

from __future__ import annotations

from typing import Any

from aquote_router.adapters.base import BaseQuoteAdapter, as_float, first_value
from aquote_router.exceptions import AdapterError, SourceUnavailableError
from aquote_router.models import QuoteRecord


class EasyQuotationSinaAdapter(BaseQuoteAdapter):
    """Adapter for easyquotation's Sina provider."""

    source = "easyquotation_sina"
    provider = "sina"

    def realtime_quotes(
        self, symbols: list[str], *, include_raw: bool = False
    ) -> list[QuoteRecord]:
        return self._stocks(symbols, include_raw=include_raw)

    def full_realtime_quotes(
        self, symbols: list[str], *, include_raw: bool = False
    ) -> list[QuoteRecord]:
        return self._stocks(symbols, include_raw=include_raw)

    def index_realtime(
        self, symbols: list[str], *, include_raw: bool = False
    ) -> list[QuoteRecord]:
        return self._stocks(symbols, include_raw=include_raw)

    def _stocks(self, symbols: list[str], *, include_raw: bool) -> list[QuoteRecord]:
        if not symbols:
            return []

        quotation = self._quotation()
        data = quotation.stocks(symbols)
        if not data:
            raise SourceUnavailableError(f"{self.source} returned no quote records")

        records: list[QuoteRecord] = []
        for symbol in symbols:
            row = data.get(symbol) or data.get(symbol.lower()) or data.get(symbol.upper())
            if row:
                records.append(self._normalize(symbol, row, include_raw=include_raw))
        if not records:
            raise SourceUnavailableError(f"{self.source} returned no requested symbols")
        return records

    def _quotation(self) -> Any:
        try:
            import easyquotation
        except Exception as exc:  # pragma: no cover - depends on user env
            raise AdapterError("easyquotation package is not available") from exc
        return easyquotation.use(self.provider)

    def _normalize(
        self, symbol: str, row: dict[str, Any], *, include_raw: bool
    ) -> QuoteRecord:
        date_value = first_value(row, ("date",))
        time_value = first_value(row, ("time",))
        if date_value and time_value:
            dt_value = f"{date_value} {time_value}"
        else:
            dt_value = str(first_value(row, ("datetime", "time")) or "") or None

        return QuoteRecord(
            symbol=symbol,
            name=first_value(row, ("name",)),
            price=as_float(first_value(row, ("now", "price", "close"))),
            open=as_float(first_value(row, ("open",))),
            high=as_float(first_value(row, ("high",))),
            low=as_float(first_value(row, ("low",))),
            pre_close=as_float(first_value(row, ("close", "pre_close", "last_close"))),
            volume=as_float(first_value(row, ("volume", "vol"))),
            amount=as_float(first_value(row, ("turnover", "amount"))),
            datetime=dt_value,
            source=self.source,
            source_level=self.source_level,
            raw=dict(row) if include_raw else None,
        )
