from __future__ import annotations

import math
from collections.abc import Iterable, Mapping, Sequence
from datetime import datetime, timezone
from typing import Any

INCREASING = "increasing"
DECREASING = "decreasing"
STABLE = "stable"
INSUFFICIENT_DATA = "insufficient_data"


def _as_float(value: Any) -> float | None:
    if value is None or isinstance(value, bool):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _as_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "y"}
    return bool(value)


def _has_items(value: Any) -> bool:
    if value is None:
        return False
    if isinstance(value, str):
        return bool(value.strip())
    if isinstance(value, Sequence | set):
        return len(value) > 0
    return bool(value)


def _quality_checks_have_missing_fields(value: Any) -> bool:
    if not isinstance(value, Iterable) or isinstance(value, str):
        return False
    for item in value:
        if isinstance(item, Mapping) and _has_items(item.get("missing_fields")):
            return True
    return False


def _schema_drift_flag(event: Mapping[str, Any]) -> bool:
    for key in ("schema_drift", "schema_drift_detected", "field_missing_detected"):
        if _as_bool(event.get(key)):
            return True
    for key in ("schema_drift_count", "field_missing_count", "missing_field_count"):
        value = _as_float(event.get(key))
        if value is not None and value > 0:
            return True
    if _has_items(event.get("missing_fields")) or _has_items(event.get("field_missing")):
        return True
    return _quality_checks_have_missing_fields(event.get("quality_checks"))


def _fallback_trace_count(value: Any) -> int:
    if not isinstance(value, Iterable) or isinstance(value, str):
        return 0
    sources = []
    for item in value:
        if not isinstance(item, Mapping):
            continue
        source = item.get("source")
        if source and source != "cache":
            sources.append(str(source))
    return len(sources)


def _fallback_flag(event: Mapping[str, Any]) -> bool:
    for key in ("fallback_used", "fallback_triggered"):
        if _as_bool(event.get(key)):
            return True
    fallback_count = _as_float(event.get("fallback_count"))
    if fallback_count is not None and fallback_count > 0:
        return True
    attempted_sources = event.get("attempted_sources")
    if isinstance(attempted_sources, Sequence) and not isinstance(attempted_sources, str):
        return len([source for source in attempted_sources if source != "cache"]) > 1
    return _fallback_trace_count(event.get("fallback_trace")) > 1


def _latency_ms(event: Mapping[str, Any]) -> float | None:
    for key in ("latency_ms", "source_latency_ms", "elapsed_ms"):
        value = _as_float(event.get(key))
        if value is not None:
            return value
    return None


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


def _record_time(event: Mapping[str, Any]) -> datetime | None:
    for key in ("created_at", "timestamp", "event_time", "time"):
        parsed = _parse_datetime(event.get(key))
        if parsed is not None:
            return parsed
    return None


def _sort_records(records: Sequence[Mapping[str, Any]]) -> list[Mapping[str, Any]]:
    indexed = list(enumerate(records))
    if not any(_record_time(row) is not None for _, row in indexed):
        return list(records)
    epoch = datetime.min.replace(tzinfo=timezone.utc)
    return [
        row
        for _, row in sorted(
            indexed,
            key=lambda item: (_record_time(item[1]) or epoch, item[0]),
        )
    ]


def _rate(flags: Sequence[bool]) -> float:
    if not flags:
        return 0.0
    return sum(1 for flag in flags if flag) / len(flags)


def _p95(values: Sequence[float]) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    index = max(0, math.ceil(len(ordered) * 0.95) - 1)
    return ordered[index]


def _split_window(records: Sequence[Mapping[str, Any]]) -> tuple[list[Mapping[str, Any]], list[Mapping[str, Any]]]:
    midpoint = max(1, len(records) // 2)
    return list(records[:midpoint]), list(records[midpoint:])


def _trend(
    baseline_value: float,
    recent_value: float,
    *,
    delta: float,
    minimum_met: bool,
) -> str:
    if not minimum_met:
        return INSUFFICIENT_DATA
    if recent_value > baseline_value + delta:
        return INCREASING
    if recent_value < max(0.0, baseline_value - delta):
        return DECREASING
    return STABLE


class DriftDetector:
    """Detect operational drift from local router/audit observations."""

    def __init__(
        self,
        *,
        minimum_samples: int = 4,
        rate_delta: float = 0.2,
        latency_spike_factor: float = 2.0,
        latency_min_delta_ms: float = 500.0,
    ) -> None:
        self.minimum_samples = minimum_samples
        self.rate_delta = rate_delta
        self.latency_spike_factor = latency_spike_factor
        self.latency_min_delta_ms = latency_min_delta_ms

    def detect(self, records: Iterable[Mapping[str, Any]] | None = None) -> dict[str, Any]:
        rows = _sort_records(list(records or []))
        baseline_rows, recent_rows = _split_window(rows) if rows else ([], [])
        minimum_met = len(rows) >= self.minimum_samples and bool(baseline_rows and recent_rows)

        baseline_schema_rate = _rate([_schema_drift_flag(row) for row in baseline_rows])
        recent_schema_rate = _rate([_schema_drift_flag(row) for row in recent_rows])
        baseline_fallback_rate = _rate([_fallback_flag(row) for row in baseline_rows])
        recent_fallback_rate = _rate([_fallback_flag(row) for row in recent_rows])
        baseline_latency_p95 = _p95(
            [latency for row in baseline_rows if (latency := _latency_ms(row)) is not None]
        )
        recent_latency_p95 = _p95(
            [latency for row in recent_rows if (latency := _latency_ms(row)) is not None]
        )

        schema_trend = _trend(
            baseline_schema_rate,
            recent_schema_rate,
            delta=self.rate_delta,
            minimum_met=minimum_met,
        )
        fallback_trend = _trend(
            baseline_fallback_rate,
            recent_fallback_rate,
            delta=self.rate_delta,
            minimum_met=minimum_met,
        )
        latency_trend = _trend(
            baseline_latency_p95,
            recent_latency_p95,
            delta=self.latency_min_delta_ms,
            minimum_met=minimum_met,
        )

        latency_spike = False
        if minimum_met and recent_latency_p95 > baseline_latency_p95 + self.latency_min_delta_ms:
            if baseline_latency_p95 <= 0:
                latency_spike = recent_latency_p95 >= self.latency_min_delta_ms
            else:
                latency_spike = recent_latency_p95 >= baseline_latency_p95 * self.latency_spike_factor

        schema_increase = schema_trend == INCREASING
        fallback_increase = fallback_trend == INCREASING
        signals = []
        if schema_increase:
            signals.append("schema_drift_increase")
        if fallback_increase:
            signals.append("fallback_frequency_increase")
        if latency_spike:
            signals.append("latency_spike")

        return {
            "sample_count": len(rows),
            "schema_drift_trend": schema_trend,
            "fallback_frequency_trend": fallback_trend,
            "latency_trend": latency_trend,
            "schema_drift_increase": schema_increase,
            "fallback_frequency_increase": fallback_increase,
            "latency_spike_detected": latency_spike,
            "signals": signals,
            "baseline": {
                "schema_drift_rate": round(baseline_schema_rate, 4),
                "fallback_rate": round(baseline_fallback_rate, 4),
                "p95_latency_ms": round(baseline_latency_p95, 3),
            },
            "recent": {
                "schema_drift_rate": round(recent_schema_rate, 4),
                "fallback_rate": round(recent_fallback_rate, 4),
                "p95_latency_ms": round(recent_latency_p95, 3),
            },
        }


def detect_drift(records: Iterable[Mapping[str, Any]] | None = None) -> dict[str, Any]:
    """Return schema, fallback, and latency drift signals."""

    return DriftDetector().detect(records)
