from __future__ import annotations

from pyqauto.stability import DriftDetector, detect_drift, source_health_trend, stability_status


def test_stability_trends_report_insufficient_data_for_short_samples() -> None:
    status = stability_status(
        events=[
            {"created_at": "2026-06-23T01:00:00+00:00", "success": True, "latency_ms": 100.0},
            {"created_at": "2026-06-23T02:00:00+00:00", "success": False, "latency_ms": 120.0},
        ],
        health_rows=[{"source": "pytdx", "score": 90.0}],
    )

    assert status["schema_drift_trend"] == "insufficient_data"
    assert status["source_health_trend"]["pytdx"]["trend"] == "insufficient_data"
    assert status["source_health_trend"]["akshare"]["trend"] == "insufficient_data"


def test_drift_and_health_trends_sort_by_observation_time() -> None:
    drift = detect_drift(
        [
            {"created_at": "2026-06-23T04:00:00+00:00", "missing_fields": ["last_price"]},
            {"created_at": "2026-06-23T01:00:00+00:00", "missing_fields": []},
            {"created_at": "2026-06-23T03:00:00+00:00", "missing_fields": ["open"]},
            {"created_at": "2026-06-23T02:00:00+00:00", "missing_fields": []},
        ]
    )
    health = source_health_trend(
        [
            {"created_at": "2026-06-23T02:00:00+00:00", "source": "pytdx", "score": 70.0},
            {"created_at": "2026-06-23T01:00:00+00:00", "source": "pytdx", "score": 90.0},
        ]
    )

    assert drift["schema_drift_trend"] == "increasing"
    assert health["pytdx"]["trend"] == "degrading"


def test_latency_spike_threshold_is_configurable() -> None:
    events = [
        {"created_at": "2026-06-23T01:00:00+00:00", "latency_ms": 100.0},
        {"created_at": "2026-06-23T02:00:00+00:00", "latency_ms": 100.0},
        {"created_at": "2026-06-23T03:00:00+00:00", "latency_ms": 260.0},
        {"created_at": "2026-06-23T04:00:00+00:00", "latency_ms": 260.0},
    ]

    assert detect_drift(events)["latency_spike_detected"] is False
    assert DriftDetector(latency_spike_factor=2.0, latency_min_delta_ms=50.0).detect(events)[
        "latency_spike_detected"
    ] is True
