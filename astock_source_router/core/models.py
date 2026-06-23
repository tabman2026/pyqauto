from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import pandas as pd


@dataclass(slots=True)
class RouterConfig:
    """Runtime configuration for MarketRouter.

    Defaults are intentionally conservative because the upstream sources are free public sources.
    """

    cache_dir: Path = Path(".cache/astock_source_router")
    log_dir: Path = Path("logs")
    request_timeout_seconds: float = 8.0
    realtime_cache_seconds: float = 3.0
    daily_cache_seconds: float = 24 * 60 * 60
    calendar_cache_seconds: float = 30 * 24 * 60 * 60
    realtime_stale_seconds: float = 15 * 60
    enable_cache: bool = True
    enable_sqlite_audit: bool = True
    circuit_failure_threshold: int = 3
    circuit_cooldown_seconds: int = 5 * 60
    max_fallback_sources: int = 8
    strict_data_date: bool = False
    min_interval_seconds: dict[str, float] = field(default_factory=dict)


@dataclass(slots=True)
class MarketDataResult:
    """Standard result returned by the router."""

    request_id: str
    feature: str
    data: pd.DataFrame
    source: str
    latency_ms: float
    fallback_trace: list[dict[str, Any]] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    created_at: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def df(self) -> pd.DataFrame:
        """Alias for users who prefer result.df."""

        return self.data


@dataclass(slots=True)
class QualityReport:
    is_valid: bool
    row_count: int
    missing_fields: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


@dataclass(slots=True)
class SourceAttempt:
    source: str
    status: str
    latency_ms: float | None = None
    error_type: str | None = None
    error_message: str | None = None
    row_count: int | None = None
    missing_fields: list[str] = field(default_factory=list)
