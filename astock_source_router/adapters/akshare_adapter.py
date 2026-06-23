from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any

import pandas as pd

from astock_source_router.core.adapter_base import BaseMarketDataAdapter
from astock_source_router.core.errors import SourceUnavailableError, UnsupportedFeatureError
from astock_source_router.core.features import (
    DAILY_KLINE,
    FULL_REALTIME_QUOTES,
    INDEX_REALTIME,
    MINUTE_KLINE,
    REALTIME_QUOTES,
    STOCK_BASIC,
    TRADE_CALENDAR,
)
from astock_source_router.core.schema import (
    date_to_iso,
    date_to_yyyymmdd,
    derive_pre_close_from_pct,
    normalize_code,
    normalize_codes,
    safe_pct_chg,
)

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

AKSHARE_DAILY_MAPPING = {
    "日期": "date",
    "date": "date",
    "开盘": "open",
    "open": "open",
    "最高": "high",
    "high": "high",
    "最低": "low",
    "low": "low",
    "收盘": "close",
    "close": "close",
    "昨收": "pre_close",
    "pre_close": "pre_close",
    "成交量": "volume",
    "volume": "volume",
    "成交额": "amount",
    "amount": "amount",
    "turnover": "turnover_rate",
    "换手率": "turnover_rate",
    "turnover_rate": "turnover_rate",
    "涨跌幅": "pct_chg",
    "pct_chg": "pct_chg",
    "change_pct": "pct_chg",
}

AKSHARE_REALTIME_MAPPING = {
    "代码": "code",
    "code": "code",
    "名称": "name",
    "name": "name",
    "最新价": "last_price",
    "last_price": "last_price",
    "price": "last_price",
    "最新": "last_price",
    "昨收": "pre_close",
    "pre_close": "pre_close",
    "previous_close": "pre_close",
    "今开": "open",
    "开盘": "open",
    "open": "open",
    "最高": "high",
    "high": "high",
    "最低": "low",
    "low": "low",
    "成交量": "volume",
    "volume": "volume",
    "成交额": "amount",
    "amount": "amount",
    "涨跌幅": "pct_chg",
    "pct_chg": "pct_chg",
    "change_pct": "pct_chg",
}

AKSHARE_INDEX_SYMBOLS = ("沪深重要指数", "上证系列指数", "深证系列指数")


def _rename_known_columns(df: pd.DataFrame, mapping: dict[str, str]) -> pd.DataFrame:
    return df.rename(columns={key: value for key, value in mapping.items() if key in df.columns}).copy()


def _select_existing_columns(df: pd.DataFrame, columns: list[str]) -> pd.DataFrame:
    return df[[column for column in columns if column in df.columns]]


class AkShareAdapter(BaseMarketDataAdapter):
    name = "akshare"
    supported_features = {
        DAILY_KLINE,
        REALTIME_QUOTES,
        FULL_REALTIME_QUOTES,
        TRADE_CALENDAR,
        MINUTE_KLINE,
        INDEX_REALTIME,
        STOCK_BASIC,
    }
    default_min_interval_seconds = 1.0

    def _ak(self) -> Any:
        try:
            import akshare as ak  # type: ignore
        except Exception as exc:  # pragma: no cover - depends on optional dependency
            raise SourceUnavailableError("akshare is not installed. Install astock-source-router[akshare].") from exc
        return ak

    def _prefixed_symbol(self, code: str) -> str:
        normalized = normalize_code(code)
        prefix = "sh" if normalized.startswith(("6", "9")) else "sz"
        return f"{prefix}{normalized}"

    def _fetch_stock_zh_a_daily(self, ak: Any, code: str, start_date: str, end_date: str, adjust: str) -> pd.DataFrame:
        if not hasattr(ak, "stock_zh_a_daily"):
            return pd.DataFrame()
        buffer_start = datetime.strptime(date_to_yyyymmdd(start_date), "%Y%m%d") - timedelta(days=30)
        return ak.stock_zh_a_daily(
            symbol=self._prefixed_symbol(code),
            start_date=buffer_start.strftime("%Y%m%d"),
            end_date=date_to_yyyymmdd(end_date),
            adjust=adjust or "",
        )

    def fetch_daily_kline(self, code: str, start_date: str, end_date: str, adjust: str = "") -> pd.DataFrame:
        ak = self._ak()
        try:
            df = ak.stock_zh_a_hist(
                symbol=normalize_code(code),
                period="daily",
                start_date=date_to_yyyymmdd(start_date),
                end_date=date_to_yyyymmdd(end_date),
                adjust=adjust or "",
            )
        except Exception:
            df = self._fetch_stock_zh_a_daily(ak, code, start_date, end_date, adjust)
        else:
            if df is None or df.empty:
                df = self._fetch_stock_zh_a_daily(ak, code, start_date, end_date, adjust)
        if df is None or df.empty:
            return pd.DataFrame()
        out = _rename_known_columns(df, AKSHARE_DAILY_MAPPING)
        out["code"] = normalize_code(code)
        if "pre_close" not in out.columns:
            if {"close", "pct_chg"}.issubset(out.columns):
                out["pre_close"] = derive_pre_close_from_pct(out["close"], out["pct_chg"])
            elif "close" in out.columns:
                out["pre_close"] = pd.to_numeric(out["close"], errors="coerce").shift(1)
        if "pct_chg" not in out.columns and {"close", "pre_close"}.issubset(out.columns):
            out["pct_chg"] = safe_pct_chg(out["close"], out["pre_close"])
        if "date" in out.columns:
            start = date_to_iso(start_date)
            end = date_to_iso(end_date)
            out["date"] = pd.to_datetime(out["date"], errors="coerce").dt.strftime("%Y-%m-%d")
            out = out[(out["date"] >= start) & (out["date"] <= end)].copy()
        out["adjust_type"] = adjust or "none"
        return _select_existing_columns(
            out,
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
            ],
        )

    def fetch_realtime_quotes(self, codes: list[str] | tuple[str, ...] | str | None = None) -> pd.DataFrame:
        ak = self._ak()
        df = ak.stock_zh_a_spot_em()
        if df is None or df.empty:
            return pd.DataFrame()
        out = _rename_known_columns(df, AKSHARE_REALTIME_MAPPING)
        target_codes = normalize_codes(codes)
        if target_codes and "code" in out.columns:
            out = out[out["code"].astype(str).str.extract(r"(\d{6})", expand=False).isin(target_codes)]
        now = datetime.now()
        out["date"] = now.strftime("%Y-%m-%d")
        out["time"] = now.strftime("%H:%M:%S")
        if "pre_close" not in out.columns:
            out["pre_close"] = pd.NA
        if "pct_chg" not in out.columns and {"last_price", "pre_close"}.issubset(out.columns):
            out["pct_chg"] = safe_pct_chg(out["last_price"], out["pre_close"])
        return _select_existing_columns(out, REALTIME_COLUMNS)

    def fetch_full_realtime_quotes(self, codes: list[str] | tuple[str, ...] | str | None = None) -> pd.DataFrame:
        return self.fetch_realtime_quotes(codes)

    def fetch_trade_calendar(self, start_date: str, end_date: str) -> pd.DataFrame:
        ak = self._ak()
        df = ak.tool_trade_date_hist_sina()
        if df is None or df.empty:
            return pd.DataFrame()
        col = "trade_date" if "trade_date" in df.columns else df.columns[0]
        out = pd.DataFrame({"date": pd.to_datetime(df[col]).dt.strftime("%Y-%m-%d")})
        start = date_to_iso(start_date)
        end = date_to_iso(end_date)
        out = out[(out["date"] >= start) & (out["date"] <= end)].copy()
        out["is_trading_day"] = True
        return out[["date", "is_trading_day"]]

    def fetch_minute_kline(self, code: str, period: str = "5", adjust: str = "") -> pd.DataFrame:
        ak = self._ak()
        if not hasattr(ak, "stock_zh_a_hist_min_em"):
            raise UnsupportedFeatureError("akshare.stock_zh_a_hist_min_em not available")
        df = ak.stock_zh_a_hist_min_em(symbol=normalize_code(code), period=str(period), adjust=adjust or "")
        if df is None or df.empty:
            return pd.DataFrame()
        mapping = {
            "时间": "datetime",
            "datetime": "datetime",
            "开盘": "open",
            "open": "open",
            "最高": "high",
            "high": "high",
            "最低": "low",
            "low": "low",
            "收盘": "close",
            "close": "close",
            "成交量": "volume",
            "volume": "volume",
            "成交额": "amount",
            "amount": "amount",
        }
        out = _rename_known_columns(df, mapping)
        out["code"] = normalize_code(code)
        return out[["datetime", "code", "open", "high", "low", "close", "volume", "amount"]]

    def fetch_index_realtime(self, codes: list[str] | tuple[str, ...] | str | None = None) -> pd.DataFrame:
        ak = self._ak()
        if not hasattr(ak, "stock_zh_index_spot_em"):
            raise UnsupportedFeatureError("akshare.stock_zh_index_spot_em not available")
        target_codes = normalize_codes(codes)
        frames: list[pd.DataFrame] = []
        last_error: Exception | None = None
        for symbol in AKSHARE_INDEX_SYMBOLS:
            try:
                df = ak.stock_zh_index_spot_em(symbol=symbol)
            except Exception as exc:  # pragma: no cover - live source variability
                last_error = exc
                continue
            if df is None or df.empty:
                continue
            frames.append(df)
            if not target_codes:
                break
            mapped_codes = (
                df.get("代码", pd.Series(dtype="object"))
                .astype(str)
                .str.extract(r"(\d{6})", expand=False)
                .dropna()
                .tolist()
            )
            if set(target_codes).issubset(set(mapped_codes)):
                break
        if not frames and hasattr(ak, "stock_zh_index_spot_sina"):
            try:
                df = ak.stock_zh_index_spot_sina()
            except Exception as exc:  # pragma: no cover - live source variability
                last_error = exc
            else:
                if df is not None and not df.empty:
                    frames.append(df)
        if not frames:
            if last_error is not None:
                raise last_error
            return pd.DataFrame()
        df = pd.concat(frames, ignore_index=True).drop_duplicates()
        out = _rename_known_columns(df, AKSHARE_REALTIME_MAPPING)
        if target_codes and "code" in out.columns:
            out = out[out["code"].astype(str).str.extract(r"(\d{6})", expand=False).isin(target_codes)]
        now = datetime.now()
        out["date"] = now.strftime("%Y-%m-%d")
        out["time"] = now.strftime("%H:%M:%S")
        if "pct_chg" not in out.columns and {"last_price", "pre_close"}.issubset(out.columns):
            out["pct_chg"] = safe_pct_chg(out["last_price"], out["pre_close"])
        return _select_existing_columns(out, REALTIME_COLUMNS)

    def fetch_stock_basic(self) -> pd.DataFrame:
        ak = self._ak()
        if hasattr(ak, "stock_info_a_code_name"):
            df = ak.stock_info_a_code_name()
        elif hasattr(ak, "stock_zh_a_spot_em"):
            df = ak.stock_zh_a_spot_em()[["代码", "名称"]]
        else:
            raise UnsupportedFeatureError("No stock basic function found in akshare")
        mapping = {"代码": "code", "code": "code", "名称": "name", "name": "name"}
        out = _rename_known_columns(df, mapping)
        out["exchange"] = out["code"].astype(str).map(lambda x: "SH" if normalize_code(x).startswith(("6", "9")) else "SZ")
        return out[["code", "name", "exchange"]]
