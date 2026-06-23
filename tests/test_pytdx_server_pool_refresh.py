from __future__ import annotations

from scripts.pytdx_server_pool_refresh import _grade_results, _merge_candidates


def test_merge_candidates_keeps_unique_servers_and_sources() -> None:
    merged = _merge_candidates(
        [
            [{"ip": "180.153.18.170", "port": 7709, "source": "verified_current"}],
            [{"ip": "180.153.18.170", "port": 7709, "source": "manual_seed"}],
            [{"ip": "119.147.212.81", "port": 7709, "source": "pytdx_hq_hosts"}],
        ]
    )

    assert len(merged) == 2
    assert merged[0]["source"] == "verified_current+manual_seed"
    assert merged[0]["sources"] == ["verified_current", "manual_seed"]


def test_grade_results_marks_only_quote_pass_servers_available() -> None:
    graded, summary = _grade_results(
        [
            {
                "ip": "slow",
                "port": 7709,
                "connect_status": "PASS",
                "quote_status": "PASS",
                "latency_ms": 30,
            },
            {
                "ip": "fast",
                "port": 7709,
                "connect_status": "PASS",
                "quote_status": "PASS",
                "latency_ms": 10,
            },
            {
                "ip": "fail",
                "port": 7709,
                "connect_status": "PASS",
                "quote_status": "FAIL",
                "latency_ms": 1,
            },
        ]
    )

    assert summary["available_server_count"] == 2
    assert summary["server_pool_status"] == "server_pool_ready"
    assert summary["single_server_warning"] is False
    assert graded[0]["ip"] == "fast"
    assert graded[0]["grade"] == "primary"
    assert graded[1]["grade"] == "hot_backup"
    assert graded[2]["grade"] == "disabled"
