from __future__ import annotations

from pyqauto.governance.health_monitor import HealthMonitor


def test_health_scores_start_neutral() -> None:
    monitor = HealthMonitor()

    scores = monitor.scores()

    assert scores["pytdx_health_score"] == 100.0
    assert scores["akshare_health_score"] == 100.0
    assert scores["efinance_health_score"] == 100.0
    assert scores["overall_data_health_score"] == 100.0


def test_health_score_declines_on_timeout_and_fallback() -> None:
    monitor = HealthMonitor()

    monitor.observe_attempts(
        [
            {
                "source": "pytdx",
                "source_level": "primary",
                "success": False,
                "duration_ms": 8000,
                "error_type": "TimeoutError",
                "error_message": "request timeout",
            }
        ],
        fallback_chain=["pytdx:primary"],
        route_success=True,
    )

    health = monitor.snapshot()

    assert health["pytdx_health_score"] < 100.0
    assert health["overall_data_health_score"] < 100.0
    assert health["sources"]["pytdx"]["timeout_rate"] == 1.0
    assert health["sources"]["pytdx"]["fallback_rate"] == 1.0


def test_health_score_declines_on_schema_drift() -> None:
    monitor = HealthMonitor()

    monitor.observe_schema_validation(
        source_name="akshare_em_spot",
        adapter_status="schema_drift",
        schema_drift_fields=["last_price"],
    )

    health = monitor.snapshot()

    assert health["akshare_health_score"] < 100.0
    assert health["sources"]["akshare"]["schema_drift_rate"] == 1.0
