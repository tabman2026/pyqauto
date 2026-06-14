"""Lightweight dataclass models used by the router and audit trail."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any


def utc_now_iso() -> str:
    """Return an ISO-8601 UTC timestamp."""

    return datetime.now(timezone.utc).isoformat(timespec="milliseconds")


@dataclass
class QuoteRecord:
    """Normalized quote record returned by all adapters."""

    symbol: str
    name: str | None = None
    price: float | None = None
    open: float | None = None
    high: float | None = None
    low: float | None = None
    pre_close: float | None = None
    volume: float | None = None
    amount: float | None = None
    datetime: str | None = None
    source: str | None = None
    source_level: str | None = None
    fallback_from: str | None = None
    is_fallback: bool = False
    raw: dict[str, Any] | None = field(default=None, repr=False)
    error: str | None = None
    trace_id: str | None = None

    def to_dict(self, *, include_raw: bool = False) -> dict[str, Any]:
        """Serialize the quote record.

        Raw source payloads are omitted by default to avoid printing large
        provider responses.
        """

        data = asdict(self)
        if not include_raw:
            data.pop("raw", None)
        return data


@dataclass
class AuditAttempt:
    """One source attempt inside a routed call."""

    source: str
    source_level: str | None
    started_at: str
    finished_at: str
    duration_ms: float
    success: bool
    error_type: str | None = None
    error_message: str | None = None
    record_count: int = 0

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class AuditRecord:
    """Top-level audit record for one router call."""

    trace_id: str
    api_name: str
    symbols: list[str]
    started_at: str
    finished_at: str
    duration_ms: float
    selected_source: str | None
    selected_source_level: str | None
    attempts: list[AuditAttempt]
    fallback_chain: list[str]
    success: bool
    error_type: str | None
    error_message: str | None
    record_count: int

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["attempts"] = [attempt.to_dict() for attempt in self.attempts]
        return data
