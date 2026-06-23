from __future__ import annotations

from collections.abc import Iterable, Mapping
from datetime import datetime, timedelta, timezone
from typing import Any

from pyqauto.stability.drift_detector import DriftDetector
from pyqauto.stability.health_tracker import HealthTracker


def _parse_datetime(value: Any) -> datetime | None:
    if isinstance(value, datetime):
        parsed = value
    elif isinstance(value, str) and value.strip():
        try:
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            return None
    else:
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _normalize_current_time(value: datetime | None) -> datetime:
    if value is None:
        return datetime.now(timezone.utc)
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _event_time(event: Mapping[str, Any]) -> datetime | None:
    for key in ("created_at", "timestamp", "event_time", "time"):
        parsed = _parse_datetime(event.get(key))
        if parsed is not None:
            return parsed
    return None


def _success_flag(event: Mapping[str, Any]) -> bool:
    if "success" in event:
        return bool(event["success"])
    status = str(event.get("status") or "").lower()
    if status in {"success", "hit", "cache_hit"}:
        return True
    return status not in {"failed", "failure", "timeout", "quality_failed", "circuit_open"}


class StabilityMonitor:
    """Summarize long-running stability without changing runtime behavior."""

    def __init__(
        self,
        *,
        drift_detector: DriftDetector | None = None,
        health_tracker: HealthTracker | None = None,
    ) -> None:
        self.drift_detector = drift_detector or DriftDetector()
        self.health_tracker = health_tracker or HealthTracker()

    def _events_24h(
        self,
        events: Iterable[Mapping[str, Any]] | None,
        *,
        current_time: datetime | None = None,
    ) -> list[Mapping[str, Any]]:
        rows = list(events or [])
        if not rows:
            return []
        now = _normalize_current_time(current_time)
        cutoff = now - timedelta(hours=24)
        filtered = []
        for row in rows:
            event_time = _event_time(row)
            if event_time is not None and cutoff <= event_time <= now:
                filtered.append(row)
        return filtered

    def stability_status(
        self,
        *,
        events: Iterable[Mapping[str, Any]] | None = None,
        health_rows: Iterable[Mapping[str, Any]] | None = None,
        current_time: datetime | None = None,
    ) -> dict[str, Any]:
        rows_24h = self._events_24h(events, current_time=current_time)
        total = len(rows_24h)
        failures = sum(1 for row in rows_24h if not _success_flag(row))
        failure_rate = failures / total if total else 0.0
        drift = self.drift_detector.detect(events)

        return {
            "system_uptime_score": round((1.0 - failure_rate) * 100.0, 3),
            "failure_rate_24h": round(failure_rate, 4),
            "schema_drift_trend": drift["schema_drift_trend"],
            "source_health_trend": self.health_tracker.trend(health_rows),
        }


def stability_status(
    *,
    events: Iterable[Mapping[str, Any]] | None = None,
    health_rows: Iterable[Mapping[str, Any]] | None = None,
    current_time: datetime | None = None,
    latency_spike_factor: float = 2.0,
    latency_min_delta_ms: float = 500.0,
) -> dict[str, Any]:
    """Return uptime, 24h failure rate, schema drift, and source health trend."""

    return StabilityMonitor(
        drift_detector=DriftDetector(
            latency_spike_factor=latency_spike_factor,
            latency_min_delta_ms=latency_min_delta_ms,
        )
    ).stability_status(
        events=events,
        health_rows=health_rows,
        current_time=current_time,
    )
