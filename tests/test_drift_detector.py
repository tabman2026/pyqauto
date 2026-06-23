from __future__ import annotations

from pyqauto.stability import detect_drift


def test_detect_drift_flags_schema_fallback_and_latency_increase() -> None:
    records = [
        {"success": True, "latency_ms": 100.0, "missing_fields": [], "attempted_sources": ["pytdx"]},
        {"success": True, "latency_ms": 120.0, "missing_fields": [], "attempted_sources": ["pytdx"]},
        {
            "success": False,
            "latency_ms": 1800.0,
            "missing_fields": ["last_price"],
            "attempted_sources": ["pytdx", "easyquotation_sina"],
        },
        {
            "success": False,
            "latency_ms": 2200.0,
            "schema_drift": True,
            "attempted_sources": ["pytdx", "easyquotation_sina"],
        },
    ]

    report = detect_drift(records)

    assert report["schema_drift_trend"] == "increasing"
    assert report["fallback_frequency_trend"] == "increasing"
    assert report["latency_spike_detected"] is True
    assert report["signals"] == [
        "schema_drift_increase",
        "fallback_frequency_increase",
        "latency_spike",
    ]


def test_detect_drift_reports_stable_when_recent_window_matches_baseline() -> None:
    records = [
        {"success": True, "latency_ms": 100.0, "attempted_sources": ["pytdx"]},
        {"success": True, "latency_ms": 110.0, "attempted_sources": ["pytdx"]},
        {"success": True, "latency_ms": 120.0, "attempted_sources": ["pytdx"]},
        {"success": True, "latency_ms": 115.0, "attempted_sources": ["pytdx"]},
    ]

    report = detect_drift(records)

    assert report["schema_drift_trend"] == "stable"
    assert report["fallback_frequency_trend"] == "stable"
    assert report["latency_trend"] == "stable"
    assert report["signals"] == []
