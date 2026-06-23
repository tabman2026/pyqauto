from __future__ import annotations

from datetime import datetime
from typing import Any

import pandas as pd

from astock_source_router.core.adapter_base import BaseMarketDataAdapter
from astock_source_router.core.errors import SourceUnavailableError
from astock_source_router.core.features import DAILY_KLINE, INDEX_REALTIME, REALTIME_QUOTES
from astock_source_router.core.schema import (
    date_to_yyyymmdd,
    derive_pre_close_from_pct,
    normalize_code,
    normalize_codes,
    safe_pct_chg,
)


class EFinanceAdapter(BaseMarketDataAdapter):
    """Optional efinance adapter.

    efinance upstream has learning/non-commercial usage notes. Keep this adapter optional.
    """

    name = "efinance"
    supported_features = {DAILY_KLINE, REALTIME_QUOTES, INDEX_REALTIME}
    default_min_interval_seconds = 1.0

    def _ef(self) -> Any:
        try:
            import efinance as ef  # type: ignore
        except Exception as exc:  # pragma: no cover
            raise SourceUnavailableError("efinance is not installed. Install astock-source-router[eastmoney].") from exc
        return ef

    def fetch_daily_kline(self, code: str, start_date: str, end_date: str, adjust: str = "") -> pd.DataFrame:
        ef = self._ef()
        quote_id = normalize_code(code)
        df = ef.stock.get_quote_history(
            stock_codes=quote_id,
            beg=date_to_yyyymmdd(start_date),
            end=date_to_yyyymmdd(end_date),
            klt=101,
            fqt=0 if adjust in ("", "none") else 1 if adjust == "qfq" else 2,
        )
        if df is None or df.empty:
            return pd.DataFrame()
        mapping = {
            "日期": "date",
            "股票代码": "code",
            "开盘": "open",
            "最高": "high",
            "最低": "low",
            "收盘": "close",
            "成交量": "volume",
            "成交额": "amount",
            "换手率": "turnover_rate",
            "涨跌幅": "pct_chg",
        }
        out = df.rename(columns={k: v for k, v in mapping.items() if k in df.columns})
        out["code"] = normalize_code(code)
        if "pre_close" not in out.columns:
            if "pct_chg" in out.columns:
                out["pre_close"] = derive_pre_close_from_pct(out["close"], out["pct_chg"])
            else:
                out["pre_close"] = pd.to_numeric(out["close"], errors="coerce").shift(1)
        out["adjust_type"] = adjust or "none"
        return out[
            [
                "date",
                "code",
                "open",
                "high",
                "low",
                "close",
                "pre_close",
                "volume",
                "amount",
                "turnover_rate",
                "pct_chg",
                "adjust_type",
            ]
        ]

    def _standard_realtime_frame(self, df: pd.DataFrame, codes: list[str] | None = None) -> pd.DataFrame:
        if df is None or df.empty:
            return pd.DataFrame()
        mapping = {
            "代码": "code",
            "股票代码": "code",
            "名称": "name",
            "股票名称": "name",
            "最新价": "last_price",
            "昨收": "pre_close",
            "昨日收盘": "pre_close",
            "今开": "open",
            "开盘": "open",
            "最高": "high",
            "最低": "low",
            "成交量": "volume",
            "成交额": "amount",
            "涨跌幅": "pct_chg",
        }
        out = df.rename(columns={k: v for k, v in mapping.items() if k in df.columns})
        if codes and "code" in out.columns:
            target_set = set(codes)
            out = out[out["code"].astype(str).isin(target_set)].copy()
        if out.empty:
            return pd.DataFrame()

        now = datetime.now()
        if "最新交易日" in df.columns:
            out["date"] = df.loc[out.index, "最新交易日"].astype(str).str[:10]
        else:
            out["date"] = now.strftime("%Y-%m-%d")
        if "更新时间" in df.columns:
            out["time"] = pd.to_datetime(df.loc[out.index, "更新时间"], errors="coerce").dt.strftime("%H:%M:%S")
        else:
            out["time"] = now.strftime("%H:%M:%S")
        if "pct_chg" not in out.columns:
            out["pct_chg"] = safe_pct_chg(out["last_price"], out["pre_close"])
        for col in ["name", "last_price", "pre_close", "open", "high", "low", "volume", "amount", "pct_chg"]:
            if col not in out.columns:
                out[col] = pd.NA
        return out[
            [
                "date",
                "time",
                "code",
                "name",
                "last_price",
                "pre_close",
                "open",
                "high",
                "low",
                "volume",
                "amount",
                "pct_chg",
            ]
        ]

    def fetch_realtime_quotes(self, codes: list[str] | tuple[str, ...] | str | None = None) -> pd.DataFrame:
        ef = self._ef()
        target_codes = normalize_codes(codes)
        df = ef.stock.get_latest_quote(target_codes) if target_codes else ef.stock.get_realtime_quotes("沪深A股")
        return self._standard_realtime_frame(df, target_codes or None)

    def fetch_index_realtime(self, codes: list[str] | tuple[str, ...] | str | None = None) -> pd.DataFrame:
        ef = self._ef()
        target_codes = normalize_codes(codes) or ["000001", "399001"]
        df = ef.stock.get_realtime_quotes("沪深系列指数")
        return self._standard_realtime_frame(df, target_codes)
