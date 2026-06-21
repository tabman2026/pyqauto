"""easyquotation Sina adapter."""

from __future__ import annotations

from typing import Any

from pyqauto.adapters.base import BaseQuoteAdapter, code_for_symbol
from pyqauto.exceptions import AdapterError, ErrorCode, SourceUnavailableError
from pyqauto.models import QuoteRecord
from pyqauto.source_schema import (
    UNIT_RULES,
    as_float,
    build_standard_row,
    first_present,
    inspect_raw_schema,
    raw_records,
    utc_now_iso,
)

EASYQUOTATION_FIELD_MAPPING = {
    "symbol": ["code", "symbol", "_raw_key"],
    "name": ["name"],
    "trade_time": ["date + time", "datetime", "time"],
    "last_price": ["now", "price", "close"],
    "pre_close": ["close", "pre_close", "last_close"],
    "open": ["open"],
    "high": ["high"],
    "low": ["low"],
    "volume_shares": ["turnover", "volume", "vol", "成交量", "成交量(手)"],
    "amount_yuan": ["volume", "amount", "turnover", "成交额", "成交额(万)"],
    "pct_chg": ["涨跌幅", "涨跌(%)", "pct_chg"],
}


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

        normalized_symbols = [code_for_symbol(symbol) for symbol in symbols]
        fetch_time = utc_now_iso()
        raw = self.fetch_raw(symbols=normalized_symbols)
        if not raw:
            raise SourceUnavailableError(
                f"{self.source} returned no quote records",
                code=_source_error_code(self.source),
            )

        probe = self.inspect_raw_schema(raw=raw, fetch_time=fetch_time)
        rows = self.normalize_to_standard(
            raw,
            symbols=normalized_symbols,
            fetch_time=fetch_time,
            raw_payload_path=probe.get("raw_payload_path"),
        )
        validation = self.validate_standard_output(
            rows,
            field_mapping=EASYQUOTATION_FIELD_MAPPING,
        )
        if not validation.is_valid:
            missing = ", ".join(validation.missing_fields)
            raise SourceUnavailableError(
                f"{self.source} standard schema missing fields: {missing}",
                code=_source_error_code(self.source),
            )

        records = [
            self._quote_record_from_standard(row, include_raw=include_raw)
            for row in rows
        ]
        if not records:
            raise SourceUnavailableError(
                f"{self.source} returned no requested symbols",
                code=_source_error_code(self.source),
            )
        return records

    def fetch_raw(
        self,
        symbols: list[str] | None = None,
        *,
        source_api: str | None = None,
    ) -> dict[str, Any]:
        """Fetch raw easyquotation stock rows."""

        normalized_symbols = [code_for_symbol(symbol) for symbol in symbols or []]
        quotation = self._quotation()
        return quotation.stocks(normalized_symbols)

    def inspect_raw_schema(
        self,
        raw: Any = None,
        *,
        source_api: str | None = None,
        fetch_time: str | None = None,
        error_message: str | None = None,
    ) -> dict[str, Any]:
        return inspect_raw_schema(
            source_name=self.source,
            source_api=source_api or self._source_api(),
            raw=raw,
            fetch_time=fetch_time,
            error_message=error_message,
            field_mapping=EASYQUOTATION_FIELD_MAPPING,
            unit_rules=UNIT_RULES,
        )

    def normalize_to_standard(
        self,
        raw: Any,
        *,
        symbols: list[str] | None = None,
        fetch_time: str | None = None,
        raw_payload_path: str | None = None,
        source_api: str | None = None,
    ) -> list[dict[str, Any]]:
        """Normalize easyquotation raw rows to the standard quote schema."""

        wanted = {code_for_symbol(symbol) for symbol in symbols or []}
        fetch_time = fetch_time or utc_now_iso()
        rows: list[dict[str, Any]] = []
        for item in raw_records(raw):
            symbol_raw = first_present(item, ("code", "symbol", "_raw_key"))
            symbol_code = code_for_symbol(symbol_raw)
            if wanted and symbol_code not in wanted:
                continue
            rows.append(
                self._normalize_standard_row(
                    symbol_code,
                    item,
                    fetch_time=fetch_time,
                    raw_payload_path=raw_payload_path,
                    source_api=source_api or self._source_api(),
                )
            )
        return rows

    def _quotation(self) -> Any:
        try:
            import easyquotation
        except Exception as exc:  # pragma: no cover - depends on user env
            raise AdapterError("easyquotation package is not available") from exc
        return easyquotation.use(self.provider)

    def _normalize_standard_row(
        self,
        symbol: str,
        row: dict[str, Any],
        *,
        fetch_time: str,
        raw_payload_path: str | None,
        source_api: str,
    ) -> dict[str, Any]:
        date_value = first_present(row, ("date",))
        time_value = first_present(row, ("time",))
        if date_value and time_value:
            dt_value = f"{date_value} {time_value}"
        else:
            dt_value = str(first_present(row, ("datetime", "time")) or "") or None

        volume_shares = first_present(row, ("turnover", "volume", "vol", "成交量", "成交量(手)"))
        amount_yuan = first_present(row, ("volume", "amount", "turnover", "成交额", "成交额(万)"))
        if self.provider == "tencent":
            trade_summary = _parse_tencent_trade_summary(
                first_present(row, ("价格/成交量(手)/成交额",))
            )
            if trade_summary is not None:
                volume_shares = trade_summary["volume_shares"]
                amount_yuan = trade_summary["amount_yuan"]
            else:
                hand_volume = first_present(row, ("成交量(手)",))
                amount_10k = first_present(row, ("成交额(万)",))
                if hand_volume is not None:
                    volume = as_float(hand_volume)
                    volume_shares = volume * 100 if volume is not None else None
                if amount_10k is not None:
                    amount = as_float(amount_10k)
                    amount_yuan = amount * 10000 if amount is not None else None

        return build_standard_row(
            symbol_raw=symbol,
            name=first_present(row, ("name",)),
            trade_time=dt_value,
            last_price=first_present(row, ("now", "price", "close")),
            pre_close=first_present(row, ("close", "pre_close", "last_close")),
            open_price=first_present(row, ("open",)),
            high=first_present(row, ("high",)),
            low=first_present(row, ("low",)),
            pct_chg=first_present(row, ("涨跌幅", "涨跌(%)", "pct_chg")),
            volume_shares=volume_shares,
            amount_yuan=amount_yuan,
            source_name=self.source,
            source_api=source_api,
            fetch_time=fetch_time,
            raw_payload_path=raw_payload_path,
            raw_row=row,
        )

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

    def _source_api(self) -> str:
        return f"easyquotation.{self.provider}.stocks"


def _source_error_code(source: str) -> ErrorCode:
    if source == "easyquotation_tencent":
        return ErrorCode.EASYQUOTATION_TENCENT_FAILED
    return ErrorCode.EASYQUOTATION_SINA_FAILED


def _parse_tencent_trade_summary(value: Any) -> dict[str, float] | None:
    if value in (None, ""):
        return None
    parts = str(value).split("/")
    if len(parts) != 3:
        return None
    volume_hands = as_float(parts[1])
    amount_yuan = as_float(parts[2])
    if volume_hands is None or amount_yuan is None:
        return None
    return {
        "volume_shares": volume_hands * 100,
        "amount_yuan": amount_yuan,
    }
