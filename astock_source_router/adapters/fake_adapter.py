from __future__ import annotations

import pandas as pd

from astock_source_router.core.adapter_base import BaseMarketDataAdapter
from astock_source_router.core.features import (
    DAILY_KLINE,
    FULL_REALTIME_QUOTES,
    INDEX_REALTIME,
    LITE_REALTIME_QUOTES,
    MINUTE_KLINE,
    REALTIME_QUOTES,
    TRADE_CALENDAR,
)


class FakeAdapter(BaseMarketDataAdapter):
    """Test adapter with deterministic data."""

    name = "fake"
    supported_features = {
        REALTIME_QUOTES,
        FULL_REALTIME_QUOTES,
        LITE_REALTIME_QUOTES,
        INDEX_REALTIME,
        MINUTE_KLINE,
        DAILY_KLINE,
        TRADE_CALENDAR,
    }
    default_min_interval_seconds = 0.0

    def __init__(self, *, fail_features: set[str] | None = None, empty_features: set[str] | None = None) -> None:
        self.fail_features = fail_features or set()
        self.empty_features = empty_features or set()

    def fetch(self, feature: str, **kwargs):
        if feature in self.fail_features:
            raise RuntimeError(f"fake failure for {feature}")
        if feature in self.empty_features:
            return pd.DataFrame()
        return super().fetch(feature, **kwargs)

    def fetch_realtime_quotes(self, codes=None) -> pd.DataFrame:
        return pd.DataFrame(
            [
                {
                    "date": "2026-06-11",
                    "time": "10:00:00",
                    "code": "000001",
                    "name": "平安银行",
                    "last_price": 10.1,
                    "pre_close": 10.0,
                    "open": 10.0,
                    "high": 10.2,
                    "low": 9.9,
                    "volume": 1000000,
                    "amount": 10100000,
                    "pct_chg": 1.0,
                }
            ]
        )

    def fetch_full_realtime_quotes(self, codes=None) -> pd.DataFrame:
        return self.fetch_realtime_quotes(codes)

    def fetch_lite_realtime_quotes(self, codes=None) -> pd.DataFrame:
        return self.fetch_realtime_quotes(codes)

    def fetch_index_realtime(self, codes=None) -> pd.DataFrame:
        return pd.DataFrame(
            [
                {
                    "date": "2026-06-11",
                    "time": "10:00:00",
                    "code": "000001",
                    "name": "SSE Composite",
                    "last_price": 3100.1,
                    "pre_close": 3090.0,
                    "open": 3095.0,
                    "high": 3110.2,
                    "low": 3088.9,
                    "volume": 100000000,
                    "amount": 1010000000,
                    "pct_chg": 0.33,
                }
            ]
        )

    def fetch_minute_kline(self, code: str, period: str = "5", adjust: str = "") -> pd.DataFrame:
        del adjust
        return pd.DataFrame(
            [
                {
                    "datetime": f"2026-06-11 10:{int(str(period).rstrip('m')):02d}:00",
                    "code": code,
                    "open": 10.0,
                    "high": 10.2,
                    "low": 9.9,
                    "close": 10.1,
                    "volume": 100000,
                    "amount": 1010000,
                }
            ]
        )

    def fetch_daily_kline(self, code: str, start_date: str, end_date: str, adjust: str = "") -> pd.DataFrame:
        return pd.DataFrame(
            [
                {
                    "date": "2026-06-11",
                    "code": "000001",
                    "open": 10.0,
                    "high": 10.2,
                    "low": 9.9,
                    "close": 10.1,
                    "pre_close": 10.0,
                    "volume": 1000000,
                    "amount": 10100000,
                    "turnover_rate": 1.2,
                    "pct_chg": 1.0,
                    "adjust_type": adjust or "none",
                }
            ]
        )

    def fetch_trade_calendar(self, start_date: str, end_date: str) -> pd.DataFrame:
        return pd.DataFrame([{"date": "2026-06-11", "is_trading_day": True}])


class BrokenAdapter(FakeAdapter):
    name = "broken"

    def __init__(self) -> None:
        super().__init__(fail_features={REALTIME_QUOTES, DAILY_KLINE, TRADE_CALENDAR})
