from __future__ import annotations

from datetime import datetime
from typing import Any

import pandas as pd

from astock_source_router.core.adapter_base import BaseMarketDataAdapter
from astock_source_router.core.errors import SourceUnavailableError
from astock_source_router.core.features import FULL_REALTIME_QUOTES, INDEX_REALTIME, REALTIME_QUOTES
from astock_source_router.core.schema import normalize_codes, safe_pct_chg


class EasyQuotationAdapter(BaseMarketDataAdapter):
    name = "easyquotation_sina"
    supported_features = {REALTIME_QUOTES, FULL_REALTIME_QUOTES, INDEX_REALTIME}
    default_min_interval_seconds = 1.0

    def __init__(self, provider: str = "sina", source_name: str | None = None) -> None:
        normalized_provider = "tencent" if provider == "qq" else provider
        self.provider = normalized_provider
        self.name = source_name or f"easyquotation_{normalized_provider}"

    def _quotation(self) -> Any:
        try:
            import easyquotation  # type: ignore
        except Exception as exc:  # pragma: no cover
            raise SourceUnavailableError("easyquotation is not installed. Install astock-source-router[realtime].") from exc
        return easyquotation.use(self.provider)

    def _stock_source_codes(self, codes: list[str] | tuple[str, ...] | str | None) -> list[str]:
        return normalize_codes(codes)

    def _index_source_codes(self, codes: list[str] | tuple[str, ...] | str | None) -> list[str]:
        target_codes = normalize_codes(codes)
        if not target_codes:
            target_codes = ["000001", "399001"]
        source_codes: list[str] = []
        for code in target_codes:
            prefix = "sz" if code.startswith("399") else "sh"
            source_codes.append(f"{prefix}{code}")
        return source_codes

    def _to_standard_frame(self, raw: Any) -> pd.DataFrame:
        rows = []
        now = datetime.now()
        for code, item in (raw or {}).items():
            row = dict(item)
            row["code"] = row.get("code", code)
            rows.append(row)
        df = pd.DataFrame(rows)
        if df.empty:
            return df

        parsed_datetime = pd.to_datetime(df["datetime"], errors="coerce") if "datetime" in df.columns else None
        out = pd.DataFrame()
        if "date" in df.columns:
            out["date"] = df["date"]
        elif parsed_datetime is not None:
            out["date"] = parsed_datetime.dt.strftime("%Y-%m-%d")
        else:
            out["date"] = now.strftime("%Y-%m-%d")

        if "time" in df.columns:
            out["time"] = df["time"]
        elif parsed_datetime is not None:
            out["time"] = parsed_datetime.dt.strftime("%H:%M:%S")
        else:
            out["time"] = now.strftime("%H:%M:%S")

        out["code"] = df["code"]
        out["name"] = df.get("name", pd.NA)
        out["last_price"] = df.get("now", pd.NA)
        out["pre_close"] = df.get("close", df.get("pre_close", pd.NA))
        out["open"] = df.get("open", pd.NA)
        out["high"] = df.get("high", pd.NA)
        out["low"] = df.get("low", pd.NA)

        if self.provider == "sina":
            out["volume"] = df.get("turnover", df.get("volume", pd.NA))
            out["amount"] = df.get("volume", df.get("amount", pd.NA))
        else:
            out["volume"] = df.get("volume", df.get("成交量(手)", pd.NA))
            out["amount"] = df.get("成交额(万)", df.get("amount", pd.NA))

        out["pct_chg"] = df.get("涨跌幅", df.get("涨跌(%)", safe_pct_chg(out["last_price"], out["pre_close"])))
        return out

    def fetch_realtime_quotes(self, codes: list[str] | tuple[str, ...] | str | None = None) -> pd.DataFrame:
        quotation = self._quotation()
        target_codes = self._stock_source_codes(codes)
        if target_codes:
            raw = quotation.stocks(target_codes)
        else:
            all_attr = quotation.all
            raw = all_attr() if callable(all_attr) else all_attr
        return self._to_standard_frame(raw)

    def fetch_full_realtime_quotes(self, codes: list[str] | tuple[str, ...] | str | None = None) -> pd.DataFrame:
        return self.fetch_realtime_quotes(codes)

    def fetch_index_realtime(self, codes: list[str] | tuple[str, ...] | str | None = None) -> pd.DataFrame:
        quotation = self._quotation()
        raw = quotation.stocks(self._index_source_codes(codes))
        return self._to_standard_frame(raw)
