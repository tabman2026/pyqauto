from __future__ import annotations

from astock_source_router.autonomy.anomaly_detector import AnomalyDetector
from astock_source_router.core.features import REALTIME_QUOTES


def test_anomaly_detector_observes_before_temporary_instability():
    detector = AnomalyDetector(observation_window=3)

    first = detector.record_attempt(
        source="fake",
        feature=REALTIME_QUOTES,
        success=False,
        status="failed",
    )
    second = detector.record_attempt(
        source="fake",
        feature=REALTIME_QUOTES,
        success=False,
        status="failed",
    )
    third = detector.record_attempt(
        source="fake",
        feature=REALTIME_QUOTES,
        success=True,
        status="success",
    )

    assert first is not None
    assert first.status == "OBSERVING"
    assert second is not None
    assert second.status == "OBSERVING"
    assert third is not None
    assert third.anomaly_type == "temporary_instability"
    assert third.status == "CONFIRMED"


def test_anomaly_detector_reports_sudden_full_failure():
    detector = AnomalyDetector(observation_window=3)

    event = detector.record_request(
        feature=REALTIME_QUOTES,
        trace=[
            {"source": "primary", "status": "failed"},
            {"source": "backup", "status": "quality_failed"},
        ],
        success=False,
    )

    assert event is not None
    assert event.anomaly_type == "sudden_full_failure"
    assert event.severity == "critical"
    assert detector.report(feature=REALTIME_QUOTES)[0]["anomaly_type"] == "sudden_full_failure"
