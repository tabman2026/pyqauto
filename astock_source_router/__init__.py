"""AStock Source Router.

本包只做本地多源行情路由和字段标准化，不提供投资建议和自动交易能力。
"""

from astock_source_router.core.data_usage_guard import DataUsageDecision, assess_data_usage
from astock_source_router.core.models import MarketDataResult, RouterConfig
from astock_source_router.core.router import MarketRouter

__all__ = [
    "DataUsageDecision",
    "MarketDataResult",
    "MarketRouter",
    "RouterConfig",
    "assess_data_usage",
]
