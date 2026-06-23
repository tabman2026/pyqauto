from __future__ import annotations

import inspect
from datetime import datetime
from typing import Any

import pandas as pd

from astock_source_router.core.adapter_base import BaseMarketDataAdapter
from astock_source_router.core.errors import SourceUnavailableError, UnsupportedFeatureError
from astock_source_router.core.features import (
    DAILY_KLINE,
    INDEX_REALTIME,
    LITE_REALTIME_QUOTES,
    MINUTE_KLINE,
    STOCK_BASIC,
    TRADE_CALENDAR,
)
from astock_source_router.core.schema import date_to_iso, normalize_code, normalize_codes

DAILY_COLUMNS = [
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

REALTIME_COLUMNS = [
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

LITE_REALTIME_COLUMNS = [
    "date",
    "time",
    "code",
    "name",
    "last_price",
    "volume",
    "amount",
    "pct_chg",
]

ADATA_DAILY_MAPPING = {
    "trade_date": "date",
    "date": "date",
    "trade_time": "trade_time",
    "stock_code": "code",
    "code": "code",
    "open": "open",
    "high": "high",
    "low": "low",
    "close": "close",
    "pre_close": "pre_close",
    "volume": "volume",
    "amount": "amount",
    "turnover": "turnover_rate",
    "turnover_ratio": "turnover_rate",
    "turnover_rate": "turnover_rate",
    "change_pct": "pct_chg",
    "pct_chg": "pct_chg",
}

ADATA_REALTIME_MAPPING = {
    "trade_date": "date",
    "date": "date",
    "trade_time": "trade_time",
    "time": "time",
    "stock_code": "code",
    "code": "code",
    "short_name": "name",
    "stock_name": "name",
    "name": "name",
    "price": "last_price",
    "current": "last_price",
    "now": "last_price",
    "current_price": "last_price",
    "latest_price": "last_price",
    "last_price": "last_price",
    "最新价": "last_price",
    "现价": "last_price",
    "close": "last_price",
    "pre_close": "pre_close",
    "昨收": "pre_close",
    "open": "open",
    "今开": "open",
    "开盘": "open",
    "high": "high",
    "最高": "high",
    "low": "low",
    "最低": "low",
    "volume": "volume",
    "成交量": "volume",
    "amount": "amount",
    "成交额": "amount",
    "change_pct": "pct_chg",
    "pct_chg": "pct_chg",
    "涨跌幅": "pct_chg",
}


def _rename_known_columns(df: pd.DataFrame, mapping: dict[str, str]) -> pd.DataFrame:
    return df.rename(columns={key: value for key, value in mapping.items() if key in df.columns}).copy()


def _select_existing_columns(df: pd.DataFrame, columns: list[str]) -> pd.DataFrame:
    return df[[column for column in columns if column in df.columns]]


def _derive_pre_close_from_pct(price: pd.Series, pct_chg: pd.Series) -> pd.Series:
    pct = pd.to_numeric(pct_chg, errors="coerce") / 100
    price_num = pd.to_numeric(price, errors="coerce")
    return price_num / (1 + pct.replace(-1, pd.NA))


def _derive_date_time(out: pd.DataFrame) -> pd.DataFrame:
    if "date" not in out.columns and "trade_time" in out.columns:
        parsed = pd.to_datetime(out["trade_time"], errors="coerce")
        out["date"] = parsed.dt.strftime("%Y-%m-%d")
        out["time"] = parsed.dt.strftime("%H:%M:%S")
    elif "date" in out.columns:
        out["date"] = pd.to_datetime(out["date"], errors="coerce").dt.strftime("%Y-%m-%d")
    if "time" not in out.columns and "trade_time" in out.columns:
        parsed = pd.to_datetime(out["trade_time"], errors="coerce")
        out["time"] = parsed.dt.strftime("%H:%M:%S")
    return out


class ADataAdapter(BaseMarketDataAdapter):
    name = "adata"
    supported_features = {
        DAILY_KLINE,
        LITE_REALTIME_QUOTES,
        TRADE_CALENDAR,
        MINUTE_KLINE,
        INDEX_REALTIME,
        STOCK_BASIC,
    }
    default_min_interval_seconds = 1.0

    def _adata(self) -> Any:
        try:
            import adata  # type: ignore
        except Exception as exc:  # pragma: no cover
            raise SourceUnavailableError("adata is not installed. Install astock-source-router[realtime].") from exc
        return adata

    def fetch_daily_kline(self, code: str, start_date: str, end_date: str, adjust: str = "") -> pd.DataFrame:
        adata = self._adata()
        df = adata.stock.market.get_market(
            stock_code=normalize_code(code),
            k_type=1,
            start_date=date_to_iso(start_date),
        )
        if df is None or df.empty:
            return pd.DataFrame()
        out = _rename_known_columns(df, ADATA_DAILY_MAPPING)
        out = _derive_date_time(out)
        out["code"] = normalize_code(code)
        if "date" in out.columns:
            start = date_to_iso(start_date)
            end = date_to_iso(end_date)
            out = out[(out["date"] >= start) & (out["date"] <= end)].copy()
        if "pre_close" not in out.columns and {"close", "pct_chg"}.issubset(out.columns):
            out["pre_close"] = _derive_pre_close_from_pct(out["close"], out["pct_chg"])
        out["adjust_type"] = adjust or "none"
        return _select_existing_columns(out, DAILY_COLUMNS)

    def fetch_realtime_quotes(self, codes: list[str] | tuple[str, ...] | str | None = None) -> pd.DataFrame:
        adata = self._adata()
        target_codes = normalize_codes(codes)
        if not hasattr(adata.stock.market, "list_market_current"):
            raise UnsupportedFeatureError("adata.stock.market.list_market_current not available")
        func = adata.stock.market.list_market_current
        try:
            df = func()
        except TypeError:
            signature = inspect.signature(func)
            params = signature.parameters
            if "code_list" in params:
                df = func(code_list=target_codes if target_codes else None)
            elif "stock_codes" in params:
                df = func(stock_codes=target_codes if target_codes else None)
            elif "stock_code" in params and len(target_codes) == 1:
                df = func(stock_code=target_codes[0])
            elif target_codes:
                df = func(target_codes)
            else:
                raise
        else:
            if (df is None or df.empty) and target_codes:
                signature = inspect.signature(func)
                params = signature.parameters
                if "code_list" in params:
                    df = func(code_list=target_codes)
                elif "stock_codes" in params:
                    df = func(stock_codes=target_codes)
                elif "stock_code" in params and len(target_codes) == 1:
                    df = func(stock_code=target_codes[0])
        if df is None or df.empty:
            return pd.DataFrame()
        out = _rename_known_columns(df, ADATA_REALTIME_MAPPING)
        out = _derive_date_time(out)
        if target_codes and "code" in out.columns:
            out = out[out["code"].astype(str).str.extract(r"(\d{6})", expand=False).isin(target_codes)]
        now = datetime.now()
        if "date" not in out.columns:
            out["date"] = now.strftime("%Y-%m-%d")
        if "time" not in out.columns:
            out["time"] = now.strftime("%H:%M:%S")
        return _select_existing_columns(out, REALTIME_COLUMNS)

    def fetch_full_realtime_quotes(self, codes: list[str] | tuple[str, ...] | str | None = None) -> pd.DataFrame:
        raise UnsupportedFeatureError("adata realtime is lite-only; use lite_realtime_quotes")

    def fetch_lite_realtime_quotes(self, codes: list[str] | tuple[str, ...] | str | None = None) -> pd.DataFrame:
        out = self.fetch_realtime_quotes(codes)
        return _select_existing_columns(out, LITE_REALTIME_COLUMNS)

    def fetch_trade_calendar(self, start_date: str, end_date: str) -> pd.DataFrame:
        adata = self._adata()
        if not hasattr(adata.stock.info, "trade_calendar"):
            raise UnsupportedFeatureError("adata.stock.info.trade_calendar not available")
        df = adata.stock.info.trade_calendar()
        if df is None or df.empty:
            return pd.DataFrame()
        out = df.rename(columns={"trade_date": "date", "calendar_date": "date"}).copy()
        start = date_to_iso(start_date)
        end = date_to_iso(end_date)
        out["date"] = out["date"].astype(str).str[:10]
        out = out[(out["date"] >= start) & (out["date"] <= end)]
        if "is_trading_day" not in out.columns:
            out["is_trading_day"] = True
        return out[["date", "is_trading_day"]]

    def fetch_minute_kline(self, code: str, period: str = "5", adjust: str = "") -> pd.DataFrame:
        adata = self._adata()
        if not hasattr(adata.stock.market, "get_market_min"):
            raise UnsupportedFeatureError("adata.stock.market.get_market_min not available")
        df = adata.stock.market.get_market_min(stock_code=normalize_code(code))
        if df is None or df.empty:
            return pd.DataFrame()
        out = df.rename(columns={"trade_time": "datetime", "stock_code": "code"}).copy()
        out["code"] = normalize_code(code)
        for col in ["amount", "volume"]:
            if col not in out.columns:
                out[col] = pd.NA
        return out[["datetime", "code", "open", "high", "low", "close", "volume", "amount"]]

    def fetch_index_realtime(self, codes: list[str] | tuple[str, ...] | str | None = None) -> pd.DataFrame:
        adata = self._adata()
        if hasattr(adata.stock.market, "list_market_index_current"):
            df = adata.stock.market.list_market_index_current()
        elif hasattr(adata.stock.market, "get_market_index"):
            raise UnsupportedFeatureError("adata index realtime needs explicit API verification")
        else:
            raise UnsupportedFeatureError("adata index realtime function not available")
        if df is None or df.empty:
            return pd.DataFrame()
        out = _rename_known_columns(
            df,
            {
                **ADATA_REALTIME_MAPPING,
                "index_code": "code",
            },
        )
        out = _derive_date_time(out)
        now = datetime.now()
        if "date" not in out.columns:
            out["date"] = now.strftime("%Y-%m-%d")
        if "time" not in out.columns:
            out["time"] = now.strftime("%H:%M:%S")
        if "pre_close" not in out.columns and {"last_price", "pct_chg"}.issubset(out.columns):
            out["pre_close"] = _derive_pre_close_from_pct(out["last_price"], out["pct_chg"])
        return _select_existing_columns(out, REALTIME_COLUMNS)

    def fetch_stock_basic(self) -> pd.DataFrame:
        adata = self._adata()
        df = adata.stock.info.all_code()
        if df is None or df.empty:
            return pd.DataFrame()
        out = df.rename(columns={"stock_code": "code", "short_name": "name"}).copy()
        if "exchange" not in out.columns:
            out["exchange"] = out["code"].astype(str).map(lambda x: "SH" if normalize_code(x).startswith(("6", "9")) else "SZ")
        return out[["code", "name", "exchange"]]
