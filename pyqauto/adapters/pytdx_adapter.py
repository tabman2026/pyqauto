"""pytdx quote adapter."""

from __future__ import annotations

from typing import Any

from pyqauto.adapters.base import (
    BaseQuoteAdapter,
    PytdxServer,
    code_for_symbol,
    market_for_symbol,
)
from pyqauto.exceptions import (
    AdapterError,
    ErrorCode,
    SourceUnavailableError,
    UnsupportedPeriodError,
)
from pyqauto.models import KlineBar, QuoteRecord
from pyqauto.policy import (
    SUPPORTED_DAILY_KLINE_PERIODS,
    SUPPORTED_MINUTE_KLINE_PERIODS,
)
from pyqauto.source_schema import (
    UNIT_RULES,
    as_float,
    build_standard_row,
    first_present,
    inspect_raw_schema,
    raw_records,
    utc_now_iso,
)

# pytdx get_security_bars category values for supported K-line periods.
PYTDX_KLINE_PERIOD_CATEGORIES = {
    "5m": 0,
    "15m": 1,
    "30m": 2,
    "60m": 3,
    "1d": 4,
    "1m": 7,
}

PYTDX_QUOTE_FIELD_MAPPING = {
    "symbol": ["code", "symbol"],
    "market": ["market"],
    "name": ["name"],
    "trade_time": ["servertime", "datetime", "time"],
    "last_price": ["price", "now", "close"],
    "pre_close": ["last_close", "pre_close", "close"],
    "open": ["open"],
    "high": ["high"],
    "low": ["low"],
    "volume_shares": ["vol", "volume"],
    "amount_yuan": ["amount"],
}

PYTDX_KLINE_FIELD_MAPPING = {
    "symbol": ["request symbol"],
    "trade_time": ["datetime", "time"],
    "last_price": ["close", "price"],
    "open": ["open"],
    "high": ["high"],
    "low": ["low"],
    "volume_shares": ["vol", "volume"],
    "amount_yuan": ["amount"],
}


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
    ) -> list[KlineBar]:
        if period not in SUPPORTED_MINUTE_KLINE_PERIODS:
            supported = ", ".join(SUPPORTED_MINUTE_KLINE_PERIODS)
            raise UnsupportedPeriodError(
                f"unsupported pytdx minute period: {period}; supported: {supported}"
            )
        return self._security_bars(
            symbol,
            period=period,
            count=count,
            include_raw=include_raw,
            empty_message="pytdx returned no minute_kline records",
        )

    def daily_kline(
        self,
        symbol: str,
        *,
        count: int = 120,
        include_raw: bool = False,
    ) -> list[KlineBar]:
        period = SUPPORTED_DAILY_KLINE_PERIODS[0]
        return self._security_bars(
            symbol,
            period=period,
            count=count,
            include_raw=include_raw,
            empty_message="pytdx returned no daily_kline records",
        )

    def _security_bars(
        self,
        symbol: str,
        *,
        period: str,
        count: int,
        include_raw: bool,
        empty_message: str,
    ) -> list[KlineBar]:
        category = PYTDX_KLINE_PERIOD_CATEGORIES.get(period)
        if category is None:
            supported = ", ".join(PYTDX_KLINE_PERIOD_CATEGORIES)
            raise UnsupportedPeriodError(
                f"unsupported pytdx kline period: {period}; supported: {supported}"
            )
        normalized_symbol = code_for_symbol(symbol)
        fetch_time = utc_now_iso()
        raw = self.fetch_raw(
            source_api="pytdx.get_security_bars",
            symbol=normalized_symbol,
            period=period,
            count=count,
            category=category,
        )
        if not raw:
            raise SourceUnavailableError(empty_message)
        probe = self.inspect_raw_schema(
            raw=raw,
            source_api="pytdx.get_security_bars",
            fetch_time=fetch_time,
        )
        standard_rows = self.normalize_to_standard(
            raw,
            source_api="pytdx.get_security_bars",
            symbol=normalized_symbol,
            period=period,
            fetch_time=fetch_time,
            raw_payload_path=probe.get("raw_payload_path"),
        )
        validation = self.validate_standard_output(
            standard_rows,
            kind="kline",
            field_mapping=PYTDX_KLINE_FIELD_MAPPING,
        )
        if not validation.is_valid:
            missing = ", ".join(validation.missing_fields)
            raise SourceUnavailableError(f"pytdx kline standard schema missing fields: {missing}")
        return [
            self._kline_bar_from_standard(
                row,
                period=period,
                include_raw=include_raw,
            )
            for row in standard_rows
        ]

    def _security_quotes(
        self, symbols: list[str], *, include_raw: bool = False
    ) -> list[QuoteRecord]:
        if not symbols:
            return []

        fetch_time = utc_now_iso()
        raw = self.fetch_raw(source_api="pytdx.get_security_quotes", symbols=symbols)
        if not raw:
            raise SourceUnavailableError("pytdx returned no quote records")
        probe = self.inspect_raw_schema(
            raw=raw,
            source_api="pytdx.get_security_quotes",
            fetch_time=fetch_time,
        )
        standard_rows = self.normalize_to_standard(
            raw,
            source_api="pytdx.get_security_quotes",
            symbols=symbols,
            fetch_time=fetch_time,
            raw_payload_path=probe.get("raw_payload_path"),
        )
        validation = self.validate_standard_output(
            standard_rows,
            field_mapping=PYTDX_QUOTE_FIELD_MAPPING,
        )
        if not validation.is_valid:
            missing = ", ".join(validation.missing_fields)
            raise SourceUnavailableError(f"pytdx quote standard schema missing fields: {missing}")
        return [
            self._quote_record_from_standard(row, include_raw=include_raw)
            for row in standard_rows
        ]

    def fetch_raw(
        self,
        *,
        source_api: str,
        symbols: list[str] | None = None,
        symbol: str | None = None,
        period: str = "1m",
        count: int = 240,
        category: int | None = None,
    ) -> Any:
        """Fetch raw pytdx quote or kline rows."""

        api = self._new_api()
        self._connect(api)
        try:
            if source_api == "pytdx.get_security_quotes":
                request_symbols = [
                    (market_for_symbol(item), code_for_symbol(item))
                    for item in symbols or []
                ]
                return api.get_security_quotes(request_symbols)
            if source_api == "pytdx.get_security_bars":
                if symbol is None:
                    raise AdapterError("pytdx kline fetch_raw requires symbol")
                normalized_symbol = code_for_symbol(symbol)
                if category is None:
                    category = PYTDX_KLINE_PERIOD_CATEGORIES.get(period)
                if category is None:
                    raise UnsupportedPeriodError(f"unsupported pytdx kline period: {period}")
                return api.get_security_bars(
                    category,
                    market_for_symbol(normalized_symbol),
                    normalized_symbol,
                    0,
                    count,
                )
            raise AdapterError(f"unsupported pytdx raw source_api: {source_api}")
        finally:
            self._disconnect(api)

    def inspect_raw_schema(
        self,
        raw: Any = None,
        *,
        source_api: str,
        fetch_time: str | None = None,
        error_message: str | None = None,
    ) -> dict[str, Any]:
        field_mapping = (
            PYTDX_KLINE_FIELD_MAPPING
            if source_api == "pytdx.get_security_bars"
            else PYTDX_QUOTE_FIELD_MAPPING
        )
        return inspect_raw_schema(
            source_name=self.source,
            source_api=source_api,
            raw=raw,
            fetch_time=fetch_time,
            error_message=error_message,
            field_mapping=field_mapping,
            unit_rules=UNIT_RULES,
        )

    def normalize_to_standard(
        self,
        raw: Any,
        *,
        source_api: str,
        symbols: list[str] | None = None,
        symbol: str | None = None,
        period: str = "1m",
        fetch_time: str | None = None,
        raw_payload_path: str | None = None,
    ) -> list[dict[str, Any]]:
        """Normalize pytdx raw quote or kline rows to the standard schema."""

        fetch_time = fetch_time or utc_now_iso()
        if source_api == "pytdx.get_security_bars":
            normalized_symbol = code_for_symbol(symbol or "")
            return [
                self._normalize_kline_standard_row(
                    normalized_symbol,
                    row,
                    source_api=source_api,
                    fetch_time=fetch_time,
                    raw_payload_path=raw_payload_path,
                    period=period,
                )
                for row in raw_records(raw)
            ]

        wanted = {code_for_symbol(item) for item in symbols or []}
        rows: list[dict[str, Any]] = []
        for item in raw_records(raw):
            symbol_raw = first_present(item, ("code", "symbol"))
            symbol_code = code_for_symbol(symbol_raw)
            if wanted and symbol_code not in wanted:
                continue
            rows.append(
                self._normalize_quote_standard_row(
                    symbol_code,
                    item,
                    source_api=source_api,
                    fetch_time=fetch_time,
                    raw_payload_path=raw_payload_path,
                )
            )
        return rows

    def _new_api(self) -> Any:
        try:
            from pytdx.hq import TdxHq_API
        except Exception as exc:  # pragma: no cover - depends on user env
            raise AdapterError("pytdx package is not available") from exc
        return TdxHq_API(heartbeat=True, auto_retry=False)

    def _connect(self, api: Any) -> None:
        connected = api.connect(self.server.host, self.server.port, time_out=self.timeout)
        if not connected:
            raise SourceUnavailableError(
                "pytdx server connection failed",
                code=ErrorCode.PYTDX_CONNECT_FAILED,
            )

    def _disconnect(self, api: Any) -> None:
        try:
            api.disconnect()
        except Exception:
            return

    def _normalize_quote_standard_row(
        self,
        symbol: str,
        row: dict[str, Any],
        *,
        source_api: str,
        fetch_time: str,
        raw_payload_path: str | None,
    ) -> dict[str, Any]:
        return build_standard_row(
            symbol_raw=symbol,
            name=first_present(row, ("name",)),
            trade_time=first_present(row, ("servertime", "datetime", "time")),
            last_price=first_present(row, ("price", "now", "close")),
            pre_close=first_present(row, ("last_close", "pre_close", "close")),
            open_price=first_present(row, ("open",)),
            high=first_present(row, ("high",)),
            low=first_present(row, ("low",)),
            volume_shares=first_present(row, ("vol", "volume")),
            amount_yuan=first_present(row, ("amount",)),
            source_name=self.source,
            source_api=source_api,
            fetch_time=fetch_time,
            raw_payload_path=raw_payload_path,
            raw_row=row,
        )

    def _normalize_kline_standard_row(
        self,
        symbol: str,
        row: dict[str, Any],
        *,
        source_api: str,
        fetch_time: str,
        raw_payload_path: str | None,
        period: str,
    ) -> dict[str, Any]:
        standard = build_standard_row(
            symbol_raw=symbol,
            trade_time=first_present(row, ("datetime", "time")),
            last_price=first_present(row, ("close", "price")),
            open_price=first_present(row, ("open",)),
            high=first_present(row, ("high",)),
            low=first_present(row, ("low",)),
            volume_shares=first_present(row, ("vol", "volume")),
            amount_yuan=first_present(row, ("amount",)),
            source_name=self.source,
            source_api=source_api,
            fetch_time=fetch_time,
            raw_payload_path=raw_payload_path,
            raw_row=row,
        )
        standard["period"] = period
        return standard

    def _quote_record_from_standard(
        self,
        row: dict[str, Any],
        *,
        include_raw: bool,
    ) -> QuoteRecord:
        return QuoteRecord(
            symbol=str(row["symbol_raw"]),
            name=row.get("name"),
            price=as_float(row.get("last_price")),
            open=as_float(row.get("open")),
            high=as_float(row.get("high")),
            low=as_float(row.get("low")),
            pre_close=as_float(row.get("pre_close")),
            volume=as_float(row.get("volume_shares")),
            amount=as_float(row.get("amount_yuan")),
            datetime=str(row.get("trade_time") or "") or None,
            source=self.source,
            source_level=self.source_level,
            raw=dict(row.get("_raw") or {}) if include_raw else None,
        )

    def _kline_bar_from_standard(
        self,
        row: dict[str, Any],
        *,
        period: str,
        include_raw: bool,
    ) -> KlineBar:
        return KlineBar(
            symbol=str(row["symbol_raw"]),
            close=as_float(row.get("last_price")),
            open=as_float(row.get("open")),
            high=as_float(row.get("high")),
            low=as_float(row.get("low")),
            volume=as_float(row.get("volume_shares")),
            amount=as_float(row.get("amount_yuan")),
            datetime=str(row.get("trade_time") or "") or None,
            period=period,
            source=self.source,
            source_level=self.source_level,
            raw=dict(row.get("_raw") or {}) if include_raw else None,
        )
