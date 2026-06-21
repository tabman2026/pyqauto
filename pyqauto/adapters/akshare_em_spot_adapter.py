"""AkShare Eastmoney spot quote adapter."""

from __future__ import annotations

from typing import Any

from pyqauto.adapters.base import BaseQuoteAdapter, code_for_symbol
from pyqauto.exceptions import AdapterError, SourceUnavailableError
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

SOURCE_API = "akshare.stock_zh_a_spot_em"

AKSHARE_EM_SPOT_FIELD_MAPPING = {
    "symbol": ["代码", "code", "symbol"],
    "name": ["名称", "name"],
    "last_price": ["最新价", "last_price", "price"],
    "pre_close": ["昨收", "pre_close", "last_close"],
    "open": ["今开", "开盘", "open"],
    "high": ["最高", "high"],
    "low": ["最低", "low"],
    "change": ["涨跌额", "change"],
    "pct_chg": ["涨跌幅", "pct_chg", "change_pct"],
    "volume_shares": ["成交量"],
    "amount_yuan": ["成交额"],
    "turnover_rate": ["换手率", "turnover_rate"],
}


class AkShareEmSpotAdapter(BaseQuoteAdapter):
    """Adapter for AkShare stock_zh_a_spot_em realtime spot quotes."""

    source = "akshare_em_spot"
    provider = "akshare"

    def realtime_quotes(
        self, symbols: list[str], *, include_raw: bool = False
    ) -> list[QuoteRecord]:
        return self._spot_quotes(symbols, include_raw=include_raw)

    def full_realtime_quotes(
        self, symbols: list[str], *, include_raw: bool = False
    ) -> list[QuoteRecord]:
        return self._spot_quotes(symbols, include_raw=include_raw)

    def _spot_quotes(self, symbols: list[str], *, include_raw: bool) -> list[QuoteRecord]:
        normalized_symbols = [code_for_symbol(symbol) for symbol in symbols]
        fetch_time = utc_now_iso()
        try:
            raw = self.fetch_raw(symbols=normalized_symbols)
            probe = self.inspect_raw_schema(raw=raw, fetch_time=fetch_time)
        except Exception as exc:
            self.inspect_raw_schema(raw=None, fetch_time=fetch_time, error_message=str(exc))
            raise

        rows = self.normalize_to_standard(
            raw,
            symbols=normalized_symbols,
            fetch_time=fetch_time,
            raw_payload_path=probe.get("raw_payload_path"),
        )
        validation = self.validate_standard_output(
            rows,
            field_mapping=AKSHARE_EM_SPOT_FIELD_MAPPING,
        )
        if not validation.is_valid:
            missing = ", ".join(validation.missing_fields)
            raise SourceUnavailableError(
                f"{self.source} standard schema missing fields: {missing}"
            )
        return [
            self._quote_record_from_standard(row, include_raw=include_raw)
            for row in rows
        ]

    def fetch_raw(
        self,
        symbols: list[str] | None = None,
        *,
        source_api: str | None = None,
    ) -> Any:
        """Fetch raw AkShare Eastmoney A-share spot rows."""

        try:
            import akshare as ak
        except Exception as exc:  # pragma: no cover - depends on user env
            raise AdapterError("akshare package is not available") from exc
        return ak.stock_zh_a_spot_em()

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
            source_api=source_api or SOURCE_API,
            raw=raw,
            fetch_time=fetch_time,
            error_message=error_message,
            field_mapping=AKSHARE_EM_SPOT_FIELD_MAPPING,
            unit_rules=[rule for rule in UNIT_RULES if rule.get("source_name") == self.source]
            + [rule for rule in UNIT_RULES if "source_name" not in rule],
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
        """Normalize AkShare spot rows to the standard quote schema."""

        wanted = {code_for_symbol(symbol) for symbol in symbols or []}
        fetch_time = fetch_time or utc_now_iso()
        rows: list[dict[str, Any]] = []
        for item in raw_records(raw):
            symbol_raw = first_present(item, ("代码", "code", "symbol"))
            symbol_code = code_for_symbol(symbol_raw)
            if wanted and symbol_code not in wanted:
                continue
            volume_lots = as_float(first_present(item, ("成交量",)))
            volume_shares = volume_lots * 100 if volume_lots is not None else None
            rows.append(
                build_standard_row(
                    symbol_raw=symbol_code,
                    name=first_present(item, ("名称", "name")),
                    trade_time=fetch_time,
                    last_price=first_present(item, ("最新价", "last_price", "price")),
                    pre_close=first_present(item, ("昨收", "pre_close", "last_close")),
                    open_price=first_present(item, ("今开", "开盘", "open")),
                    high=first_present(item, ("最高", "high")),
                    low=first_present(item, ("最低", "low")),
                    change=first_present(item, ("涨跌额", "change")),
                    pct_chg=first_present(item, ("涨跌幅", "pct_chg", "change_pct")),
                    volume_shares=volume_shares,
                    amount_yuan=first_present(item, ("成交额", "amount", "amount_yuan")),
                    turnover_rate=first_present(item, ("换手率", "turnover_rate")),
                    source_name=self.source,
                    source_api=source_api or SOURCE_API,
                    fetch_time=fetch_time,
                    raw_payload_path=raw_payload_path,
                    raw_row=item,
                )
            )
        return rows

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
