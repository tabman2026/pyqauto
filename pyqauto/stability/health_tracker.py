from __future__ import annotations

from collections.abc import Iterable, Mapping
from datetime import datetime, timezone
from typing import Any

TRACKED_SOURCES = ("pytdx", "akshare", "efinance")
INSUFFICIENT_DATA = "insufficient_data"


def _as_float(value: Any) -> float | None:
    if value is None or isinstance(value, bool):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _flatten_rows(rows: Iterable[Mapping[str, Any]] | None) -> list[Mapping[str, Any]]:
    flattened: list[Mapping[str, Any]] = []
    for row in rows or []:
        health_rows = row.get("health")
        if isinstance(health_rows, Iterable) and not isinstance(health_rows, str):
            for health_row in health_rows:
                if isinstance(health_row, Mapping):
                    flattened.append(health_row)
            continue
        flattened.append(row)
    return flattened


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


def _row_time(row: Mapping[str, Any]) -> datetime | None:
    for key in ("created_at", "timestamp", "event_time", "time"):
        parsed = _parse_datetime(row.get(key))
        if parsed is not None:
            return parsed
    return None


def _sort_rows(rows: list[Mapping[str, Any]]) -> list[Mapping[str, Any]]:
    if not any(_row_time(row) is not None for row in rows):
        return rows
    epoch = datetime.min.replace(tzinfo=timezone.utc)
    return [
        row
        for _, row in sorted(
            enumerate(rows),
            key=lambda item: (_row_time(item[1]) or epoch, item[0]),
        )
    ]


def _score(row: Mapping[str, Any]) -> float | None:
    for key in ("score", "health_score", "reliability_score", "source_health_score"):
        value = _as_float(row.get(key))
        if value is not None:
            return value
    return None


def _status(score: float | None) -> str:
    if score is None:
        return "unknown"
    if score >= 80.0:
        return "healthy"
    if score >= 50.0:
        return "degraded"
    return "unhealthy"


class HealthTracker:
    """Track health trends for the primary optional market-data sources."""

    def __init__(
        self,
        *,
        tracked_sources: tuple[str, ...] = TRACKED_SOURCES,
        stable_delta: float = 2.0,
    ) -> None:
        self.tracked_sources = tuple(source.lower() for source in tracked_sources)
        self.stable_delta = stable_delta

    def trend(self, rows: Iterable[Mapping[str, Any]] | None = None) -> dict[str, dict[str, Any]]:
        flattened = _sort_rows(_flatten_rows(rows))
        scores_by_source = {source: [] for source in self.tracked_sources}
        for row in flattened:
            source = str(row.get("source") or row.get("source_name") or "").lower()
            if source not in scores_by_source:
                continue
            score = _score(row)
            if score is not None:
                scores_by_source[source].append(score)

        result: dict[str, dict[str, Any]] = {}
        for source, scores in scores_by_source.items():
            if not scores:
                result[source] = {
                    "trend": INSUFFICIENT_DATA,
                    "latest_score": None,
                    "sample_count": 0,
                    "status": "unknown",
                }
                continue
            if len(scores) < 2:
                result[source] = {
                    "trend": INSUFFICIENT_DATA,
                    "latest_score": round(scores[-1], 3),
                    "sample_count": len(scores),
                    "status": _status(scores[-1]),
                }
                continue
            first_score = scores[0]
            latest_score = scores[-1]
            if latest_score > first_score + self.stable_delta:
                trend = "improving"
            elif latest_score < first_score - self.stable_delta:
                trend = "degrading"
            else:
                trend = "stable"
            result[source] = {
                "trend": trend,
                "latest_score": round(latest_score, 3),
                "sample_count": len(scores),
                "status": _status(latest_score),
            }
        return result


def source_health_trend(
    rows: Iterable[Mapping[str, Any]] | None = None,
) -> dict[str, dict[str, Any]]:
    """Return pytdx, akshare, and efinance health trends."""

    return HealthTracker().trend(rows)
