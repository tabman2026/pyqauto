"""Base adapter contracts and shared helpers."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from pyqauto.exceptions import AdapterError, UnsupportedSymbolError
from pyqauto.models import KlineBar, QuoteRecord
from pyqauto.source_schema import (
    StandardValidationResult,
    inspect_raw_schema,
    validate_standard_rows,
)


@dataclass(frozen=True)
class PytdxServer:
    """One pytdx server configuration entry."""

    host: str
    port: int
    role: str
    latency_ms: int
    enabled: bool = True


@dataclass(frozen=True)
class NormalizedSymbol:
    """Provider-ready symbol code and pytdx market id."""

    code: str
    market: int
    suffix: str | None = None


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
    ) -> list[KlineBar]:
        raise AdapterError(f"{self.source} does not support minute_kline")

    def daily_kline(
        self,
        symbol: str,
        *,
        count: int = 120,
        include_raw: bool = False,
    ) -> list[KlineBar]:
        raise AdapterError(f"{self.source} does not support daily_kline")

    def fetch_raw(self, *args: Any, **kwargs: Any) -> Any:
        """Fetch one raw provider payload without standardizing it."""

        raise AdapterError(f"{self.source} does not support fetch_raw")

    def inspect_raw_schema(self, raw: Any = None, **kwargs: Any) -> dict[str, Any]:
        """Write a raw schema probe for a fetched payload."""

        return inspect_raw_schema(source_name=self.source, raw=raw, **kwargs)

    def normalize_to_standard(self, raw: Any, **kwargs: Any) -> list[dict[str, Any]]:
        """Normalize a raw payload to the standard adapter schema."""

        raise AdapterError(f"{self.source} does not support normalize_to_standard")

    def validate_standard_output(
        self,
        rows: list[dict[str, Any]],
        **kwargs: Any,
    ) -> StandardValidationResult:
        """Validate standard rows before the public router consumes them."""

        return validate_standard_rows(rows, **kwargs)


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

    return normalize_symbol(symbol).market


def code_for_symbol(symbol: str) -> str:
    """Return the six-digit provider code for a documented symbol."""

    return normalize_symbol(symbol).code


def normalize_symbol(symbol: str) -> NormalizedSymbol:
    """Normalize documented A-share symbol forms.

    Supported forms are six digits and six digits followed by .SH, .SZ, or .BJ.
    Bare 6/5/9 prefixes use Shanghai, while bare 0/1/2/3 prefixes use Shenzhen.
    """

    raw = str(symbol or "").strip().upper()
    if "." in raw:
        code, separator, suffix = raw.partition(".")
        if separator != "." or suffix not in {"SH", "SZ", "BJ"}:
            raise UnsupportedSymbolError(f"unsupported symbol suffix: {symbol}")
        if not _is_six_digit_code(code):
            raise UnsupportedSymbolError(f"unsupported symbol code: {symbol}")
        return NormalizedSymbol(code=code, market=1 if suffix == "SH" else 0, suffix=suffix)

    if not _is_six_digit_code(raw):
        raise UnsupportedSymbolError(f"unsupported symbol code: {symbol}")
    if raw.startswith(("5", "6", "9")):
        return NormalizedSymbol(code=raw, market=1)
    if raw.startswith(("0", "1", "2", "3")):
        return NormalizedSymbol(code=raw, market=0)
    if raw.startswith(("4", "8")):
        return NormalizedSymbol(code=raw, market=0, suffix="BJ")
    raise UnsupportedSymbolError(f"unsupported symbol prefix: {symbol}")


def source_id(source: str, source_level: str | None) -> str:
    """Return a compact source identifier for fallback chains."""

    if source_level:
        return f"{source}:{source_level}"
    return source


def _is_six_digit_code(value: str) -> bool:
    return len(value) == 6 and value.isdigit()
