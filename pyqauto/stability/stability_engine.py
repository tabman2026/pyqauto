from __future__ import annotations

from collections.abc import Iterable, Mapping
from datetime import datetime
from typing import Any

from pyqauto.stability.drift_detector import DriftDetector
from pyqauto.stability.health_tracker import HealthTracker
from pyqauto.stability.monitor import StabilityMonitor


class StabilityEngine:
    """Facade for the L8 stability layer.

    The engine coordinates monitor, drift, and health calculations. It does not
    call providers, mutate source selection, or alter governance/meta/autonomy.
    """

    def __init__(
        self,
        *,
        monitor: StabilityMonitor | None = None,
        drift_detector: DriftDetector | None = None,
        health_tracker: HealthTracker | None = None,
    ) -> None:
        self.drift_detector = drift_detector or DriftDetector()
        self.health_tracker = health_tracker or HealthTracker()
        self.monitor = monitor or StabilityMonitor(
            drift_detector=self.drift_detector,
            health_tracker=self.health_tracker,
        )

    def stability_status(
        self,
        *,
        events: Iterable[Mapping[str, Any]] | None = None,
        health_rows: Iterable[Mapping[str, Any]] | None = None,
        current_time: datetime | None = None,
    ) -> dict[str, Any]:
        return self.monitor.stability_status(
            events=events,
            health_rows=health_rows,
            current_time=current_time,
        )

    def drift_report(self, records: Iterable[Mapping[str, Any]] | None = None) -> dict[str, Any]:
        return self.drift_detector.detect(records)

    def health_trend(
        self,
        rows: Iterable[Mapping[str, Any]] | None = None,
    ) -> dict[str, dict[str, Any]]:
        return self.health_tracker.trend(rows)
