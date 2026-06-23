from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any


@dataclass(slots=True)
class AnomalyEvent:
    source: str | None
    feature: str
    anomaly_type: str
    severity: str
    status: str
    observed_failures: int
    observed_successes: int
    window_size: int
    message: str


class AnomalyDetector:
    """Detect source instability without making trading decisions."""

    def __init__(self, *, observation_window: int = 3, temporary_failure_ratio: float = 0.34) -> None:
        if observation_window < 2:
            raise ValueError("observation_window must be at least 2")
        self.observation_window = observation_window
        self.temporary_failure_ratio = temporary_failure_ratio
        self._attempt_windows: dict[tuple[str, str], list[bool]] = {}
        self._events: dict[tuple[str | None, str, str], AnomalyEvent] = {}

    def _upsert(self, event: AnomalyEvent) -> AnomalyEvent:
        self._events[(event.source, event.feature, event.anomaly_type)] = event
        return event

    def record_attempt(
        self,
        *,
        source: str,
        feature: str,
        success: bool,
        status: str,
    ) -> AnomalyEvent | None:
        key = (source, feature)
        window = self._attempt_windows.setdefault(key, [])
        window.append(bool(success))
        del window[: max(0, len(window) - self.observation_window)]

        failures = sum(1 for ok in window if not ok)
        successes = len(window) - failures
        if len(window) < self.observation_window:
            return self._upsert(
                AnomalyEvent(
                    source=source,
                    feature=feature,
                    anomaly_type="observation_window",
                    severity="info",
                    status="OBSERVING",
                    observed_failures=failures,
                    observed_successes=successes,
                    window_size=len(window),
                    message=f"waiting for observation window after {status}",
                )
            )

        if failures == len(window):
            return self._upsert(
                AnomalyEvent(
                    source=source,
                    feature=feature,
                    anomaly_type="source_failure_streak",
                    severity="high",
                    status="CONFIRMED",
                    observed_failures=failures,
                    observed_successes=successes,
                    window_size=len(window),
                    message="source failed for the full observation window",
                )
            )

        failure_ratio = failures / len(window)
        if failures > 0 and failure_ratio >= self.temporary_failure_ratio:
            return self._upsert(
                AnomalyEvent(
                    source=source,
                    feature=feature,
                    anomaly_type="temporary_instability",
                    severity="medium",
                    status="CONFIRMED",
                    observed_failures=failures,
                    observed_successes=successes,
                    window_size=len(window),
                    message="source alternated between failures and recoveries",
                )
            )

        return self._upsert(
            AnomalyEvent(
                source=source,
                feature=feature,
                anomaly_type="source_recovered",
                severity="info",
                status="CLEARED",
                observed_failures=failures,
                observed_successes=successes,
                window_size=len(window),
                message="source observation window is clean",
            )
        )

    def record_request(
        self,
        *,
        feature: str,
        trace: list[dict[str, Any]],
        success: bool,
    ) -> AnomalyEvent | None:
        attempted = [
            item
            for item in trace
            if item.get("source") not in {None, "", "cache"} and item.get("source") != "<none>"
        ]
        if success or not attempted:
            return None
        failed = [
            item
            for item in attempted
            if item.get("status") not in {"success", "hit", "cache_hit"}
        ]
        if len(failed) != len(attempted):
            return None
        return self._upsert(
            AnomalyEvent(
                source=None,
                feature=feature,
                anomaly_type="sudden_full_failure",
                severity="critical",
                status="CONFIRMED",
                observed_failures=len(failed),
                observed_successes=0,
                window_size=len(attempted),
                message="all attempted sources failed in one router request",
            )
        )

    def report(
        self,
        *,
        source: str | None = None,
        feature: str | None = None,
    ) -> list[dict[str, object]]:
        rows = []
        for event in self._events.values():
            if source is not None and event.source != source:
                continue
            if feature is not None and event.feature != feature:
                continue
            rows.append(asdict(event))
        rows.sort(
            key=lambda row: (
                str(row["feature"]),
                str(row["source"] or ""),
                str(row["anomaly_type"]),
            )
        )
        return rows
