"""Base adapter contracts and shared helpers."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from aquote_router.exceptions import AdapterError
from aquote_router.models import QuoteRecord


@dataclass(frozen=True)
class PytdxServer:
    """One pytdx server configuration entry."""

    host: str
    port: int
    role: str
    latency_ms: int
    enabled: bool = True


class BaseQuoteAdapter:
    """Synchronous quote adapter interface."""

    source: str = "unknown"
    source_level: str | None = None

    def realtime_quotes(
        self, symbols: list[str], *, include_raw: bool = False
    ) -> list[QuoteRecord]:
        raise AdapterError(f"{self.source} does not support realtime_quotes")

    def full_realtime_quotes(
        self, symbols: list[str], *, include_raw: bool = False
    ) -> list[QuoteRecord]:
        return self.realtime_quotes(symbols, include_raw=include_raw)

    def index_realtime(
        self, symbols: list[str], *, include_raw: bool = False
    ) -> list[QuoteRecord]:
        return self.realtime_quotes(symbols, include_raw=include_raw)

    def minute_kline(
        self,
        symbol: str,
        *,
        period: str = "1m",
        count: int = 240,
        include_raw: bool = False,
    ) -> list[QuoteRecord]:
        raise AdapterError(f"{self.source} does not support minute_kline")


def as_float(value: Any) -> float | None:
    """Best-effort conversion to float with empty values mapped to None."""

    if value is None or value == "":
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def first_value(row: dict[str, Any], keys: tuple[str, ...]) -> Any:
    """Return the first present value for a tuple of candidate keys."""

    for key in keys:
        if key in row and row[key] not in (None, ""):
            return row[key]
    return None


def market_for_symbol(symbol: str) -> int:
    """Return pytdx market id for a common A-share symbol."""

    if symbol.startswith(("5", "6", "9")):
        return 1
    return 0


def source_id(source: str, source_level: str | None) -> str:
    """Return a compact source identifier for fallback chains."""

    if source_level:
        return f"{source}:{source_level}"
    return source
