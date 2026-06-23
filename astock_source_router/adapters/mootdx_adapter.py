from __future__ import annotations

import pandas as pd

from astock_source_router.core.adapter_base import BaseMarketDataAdapter
from astock_source_router.core.errors import SourceUnavailableError, UnsupportedFeatureError
from astock_source_router.core.features import MINUTE_KLINE
from astock_source_router.core.schema import normalize_code


class MootdxAdapter(BaseMarketDataAdapter):
    """Optional mootdx adapter for TDX minute data.

    This adapter is intentionally minimal because TDX server behavior and mootdx API may vary by version.
    """

    name = "mootdx"
    supported_features = {MINUTE_KLINE}
    default_min_interval_seconds = 1.0

    def _client(self):
        try:
            from mootdx.quotes import Quotes  # type: ignore
        except Exception as exc:  # pragma: no cover
            raise SourceUnavailableError("mootdx is not installed. Install astock-source-router[tdx].") from exc
        return Quotes.factory(market="std")

    def fetch_minute_kline(self, code: str, period: str = "5", adjust: str = "") -> pd.DataFrame:
        client = self._client()
        code6 = normalize_code(code)
        symbol = f"sh{code6}" if code6.startswith(("6", "9")) else f"sz{code6}"
        if not hasattr(client, "minute"):
            raise UnsupportedFeatureError("mootdx client.minute not available")
        df = client.minute(symbol=symbol)
        if df is None or df.empty:
            return pd.DataFrame()
        out = df.reset_index().rename(
            columns={
                "datetime": "datetime",
                "time": "datetime",
                "open": "open",
                "high": "high",
                "low": "low",
                "close": "close",
                "vol": "volume",
                "volume": "volume",
                "amount": "amount",
            }
        )
        out["code"] = code6
        if "amount" not in out.columns:
            out["amount"] = pd.NA
        return out[["datetime", "code", "open", "high", "low", "close", "volume", "amount"]]
