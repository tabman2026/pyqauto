from __future__ import annotations

import pandas as pd

from astock_source_router.core.adapter_base import BaseMarketDataAdapter
from astock_source_router.core.errors import SourceUnavailableError
from astock_source_router.core.features import DAILY_KLINE, STOCK_BASIC, TRADE_CALENDAR
from astock_source_router.core.schema import date_to_iso, normalize_code


class BaostockAdapter(BaseMarketDataAdapter):
    name = "baostock"
    supported_features = {DAILY_KLINE, TRADE_CALENDAR, STOCK_BASIC}
    default_min_interval_seconds = 1.0

    def _bs(self):
        try:
            import baostock as bs  # type: ignore
        except Exception as exc:  # pragma: no cover
            raise SourceUnavailableError("baostock is not installed. Install astock-source-router[baostock].") from exc
        return bs

    def _to_bs_code(self, code: str) -> str:
        code6 = normalize_code(code)
        prefix = "sh" if code6.startswith(("6", "9")) else "sz"
        return f"{prefix}.{code6}"

    def _login(self):
        bs = self._bs()
        lg = bs.login()
        if getattr(lg, "error_code", "0") != "0":
            raise SourceUnavailableError(f"baostock login failed: {getattr(lg, 'error_msg', '')}")
        return bs

    def fetch_daily_kline(self, code: str, start_date: str, end_date: str, adjust: str = "") -> pd.DataFrame:
        bs = self._login()
        try:
            adjust_flag = {"": "3", "none": "3", "qfq": "2", "hfq": "1"}.get(adjust, "3")
            fields = "date,code,open,high,low,close,preclose,volume,amount,turn,pctChg"
            rs = bs.query_history_k_data_plus(
                self._to_bs_code(code),
                fields,
                start_date=date_to_iso(start_date),
                end_date=date_to_iso(end_date),
                frequency="d",
                adjustflag=adjust_flag,
            )
            data = []
            while rs.error_code == "0" and rs.next():
                data.append(rs.get_row_data())
            df = pd.DataFrame(data, columns=rs.fields)
            if df.empty:
                return df
            df = df.rename(columns={"preclose": "pre_close", "turn": "turnover_rate", "pctChg": "pct_chg"})
            df["code"] = normalize_code(code)
            df["adjust_type"] = adjust or "none"
            return df[
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
        finally:
            bs.logout()

    def fetch_trade_calendar(self, start_date: str, end_date: str) -> pd.DataFrame:
        bs = self._login()
        try:
            rs = bs.query_trade_dates(start_date=date_to_iso(start_date), end_date=date_to_iso(end_date))
            data = []
            while rs.error_code == "0" and rs.next():
                data.append(rs.get_row_data())
            df = pd.DataFrame(data, columns=rs.fields)
            if df.empty:
                return df
            df = df.rename(columns={"calendar_date": "date", "is_trading_day": "is_trading_day"})
            df["is_trading_day"] = df["is_trading_day"].astype(str).isin(["1", "True", "true"])
            return df[["date", "is_trading_day"]]
        finally:
            bs.logout()

    def fetch_stock_basic(self) -> pd.DataFrame:
        bs = self._login()
        try:
            rs = bs.query_all_stock(day=None)
            data = []
            while rs.error_code == "0" and rs.next():
                data.append(rs.get_row_data())
            df = pd.DataFrame(data, columns=rs.fields)
            if df.empty:
                return df
            df["code"] = df["code"].astype(str).str.extract(r"(\d{6})", expand=False)
            df["name"] = df.get("code_name", pd.NA)
            df["exchange"] = df["code"].map(lambda x: "SH" if str(x).startswith(("6", "9")) else "SZ")
            return df[["code", "name", "exchange"]]
        finally:
            bs.logout()
