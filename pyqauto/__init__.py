"""Simple public API for pyqauto."""

from __future__ import annotations

from pathlib import Path

from .governance import SystemState
from .models import KlineBar, QuoteRecord
from .router import QuoteRouter

__version__ = "0.3.1"

_default_router: QuoteRouter | None = None


def configure(
    *,
    pytdx_servers_path: str | Path | None = None,
    source_policy_path: str | Path | None = None,
    audit_jsonl_path: str | Path | None = None,
    audit_sqlite_path: str | Path | None = None,
) -> QuoteRouter:
    """Configure and cache the default router for module-level calls."""

    global _default_router
    _default_router = QuoteRouter.from_config(
        pytdx_servers_path=pytdx_servers_path,
        source_policy_path=source_policy_path,
        audit_jsonl_path=audit_jsonl_path,
        audit_sqlite_path=audit_sqlite_path,
    )
    return _default_router


def get_router() -> QuoteRouter:
    """Return the cached default router, creating it from bundled defaults."""

    global _default_router
    if _default_router is None:
        _default_router = QuoteRouter.from_config()
    return _default_router


def quote(symbol: str, *, include_raw: bool = False) -> QuoteRecord:
    """Fetch one realtime quote."""

    return get_router().realtime_quotes([symbol], include_raw=include_raw)[0]


def quotes(symbols: list[str], *, include_raw: bool = False) -> list[QuoteRecord]:
    """Fetch realtime quotes."""

    return get_router().realtime_quotes(list(symbols), include_raw=include_raw)


def full_quotes(symbols: list[str], *, include_raw: bool = False) -> list[QuoteRecord]:
    """Fetch full realtime quotes."""

    return get_router().full_realtime_quotes(list(symbols), include_raw=include_raw)


def index(symbols: list[str], *, include_raw: bool = False) -> list[QuoteRecord]:
    """Fetch index realtime quotes."""

    return get_router().index_realtime(list(symbols), include_raw=include_raw)


def minute(
    symbol: str,
    *,
    period: str = "1m",
    count: int = 240,
    include_raw: bool = False,
) -> list[KlineBar]:
    """Fetch pytdx-only minute K-line bars."""

    return get_router().minute_kline(
        symbol,
        period=period,
        count=count,
        include_raw=include_raw,
    )


def daily(
    symbol: str,
    *,
    count: int = 120,
    include_raw: bool = False,
) -> list[KlineBar]:
    """Fetch pytdx-only daily K-line bars."""

    return get_router().daily_kline(symbol, count=count, include_raw=include_raw)


def kline(
    symbol: str,
    *,
    period: str = "1m",
    count: int = 120,
    include_raw: bool = False,
) -> list[KlineBar]:
    """Fetch K-line bars through the unified K-line API."""

    return get_router().kline(
        symbol,
        period=period,
        count=count,
        include_raw=include_raw,
    )


def diagnose() -> dict:
    """Return local router configuration without connecting to providers."""

    return get_router().diagnose()


__all__ = [
    "KlineBar",
    "QuoteRecord",
    "QuoteRouter",
    "SystemState",
    "__version__",
    "configure",
    "daily",
    "diagnose",
    "full_quotes",
    "get_router",
    "index",
    "kline",
    "minute",
    "quote",
    "quotes",
]
