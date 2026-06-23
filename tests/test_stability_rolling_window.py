from __future__ import annotations

from datetime import datetime, timezone

from pyqauto.stability import stability_status


def test_failure_rate_24h_uses_only_utc_rolling_window() -> None:
    now = datetime(2026, 6, 23, 12, 0, tzinfo=timezone.utc)
    events = [
        {"created_at": "2026-06-22T11:59:59+00:00", "success": False},
        {"created_at": "2026-06-22T12:00:00+00:00", "success": False},
        {"created_at": "2026-06-23T00:00:00+08:00", "success": True},
        {"created_at": "2026-06-23T12:00:01+00:00", "success": False},
        {"success": False},
    ]

    status = stability_status(events=events, current_time=now)

    assert status["failure_rate_24h"] == 0.5
    assert status["system_uptime_score"] == 50.0


def test_naive_current_time_is_treated_as_utc() -> None:
    now = datetime(2026, 6, 23, 12, 0)
    events = [
        {"created_at": "2026-06-22T12:00:00+00:00", "success": True},
        {"created_at": "2026-06-22T11:59:59+00:00", "success": False},
    ]

    status = stability_status(events=events, current_time=now)

    assert status["failure_rate_24h"] == 0.0
