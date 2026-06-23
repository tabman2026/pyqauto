from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass, field

from astock_source_router.core.features import (
    DAILY_KLINE,
    FULL_REALTIME_QUOTES,
    INDEX_REALTIME,
    LITE_REALTIME_QUOTES,
    MINUTE_KLINE,
    REALTIME_QUOTES,
    STOCK_BASIC,
    TRADE_CALENDAR,
)

DEFAULT_SOURCE_POLICY: dict[str, list[str]] = {
    REALTIME_QUOTES: ["pytdx", "easyquotation_sina", "easyquotation_tencent"],
    FULL_REALTIME_QUOTES: ["pytdx", "easyquotation_sina", "easyquotation_tencent"],
    LITE_REALTIME_QUOTES: ["adata"],
    INDEX_REALTIME: ["pytdx", "easyquotation_sina", "easyquotation_tencent", "akshare"],
    MINUTE_KLINE: ["pytdx"],
    TRADE_CALENDAR: ["akshare", "baostock"],
    STOCK_BASIC: ["baostock", "akshare"],
    DAILY_KLINE: ["akshare", "baostock"],
}


@dataclass(slots=True)
class SourcePolicy:
    policy: dict[str, list[str]] = field(default_factory=lambda: deepcopy(DEFAULT_SOURCE_POLICY))

    def sources_for(self, feature: str) -> list[str]:
        return list(self.policy.get(feature, []))

    def set_sources(self, feature: str, sources: list[str]) -> None:
        self.policy[feature] = list(dict.fromkeys(sources))
