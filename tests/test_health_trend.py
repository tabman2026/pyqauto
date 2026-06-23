from __future__ import annotations

from pyqauto.stability import source_health_trend


def test_source_health_trend_tracks_pytdx_akshare_and_efinance() -> None:
    rows = [
        {"source": "pytdx", "score": 92.0},
        {"source": "akshare", "score": 78.0},
        {"source": "efinance", "score": 66.0},
        {"source": "pytdx", "score": 70.0},
        {"source": "akshare", "score": 86.0},
        {"source": "efinance", "score": 67.0},
    ]

    trend = source_health_trend(rows)

    assert trend["pytdx"]["trend"] == "degrading"
    assert trend["pytdx"]["status"] == "degraded"
    assert trend["akshare"]["trend"] == "improving"
    assert trend["akshare"]["status"] == "healthy"
    assert trend["efinance"]["trend"] == "stable"
    assert trend["efinance"]["latest_score"] == 67.0


def test_source_health_trend_marks_missing_sources_unknown() -> None:
    trend = source_health_trend([{"source": "pytdx", "score": 90.0}])

    assert trend["pytdx"]["trend"] == "insufficient_data"
    assert trend["akshare"]["trend"] == "insufficient_data"
    assert trend["efinance"]["sample_count"] == 0
