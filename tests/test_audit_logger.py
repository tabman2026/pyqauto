from __future__ import annotations

import json
import sqlite3

from astock_source_router.adapters.fake_adapter import FakeAdapter
from astock_source_router.core.policy import SourcePolicy
from astock_source_router.core.router import MarketRouter


def test_audit_logs_jsonl_and_sqlite(test_config):
    policy = SourcePolicy({"trade_calendar": ["fake"]})
    router = MarketRouter(config=test_config, source_policy=policy, adapters=[FakeAdapter()], auto_register=False)
    df = router.get_trade_calendar("20260611", "20260611")
    assert len(df) == 1
    assert (test_config.log_dir / "source_router.jsonl").exists()
    assert (test_config.log_dir / "source_router.db").exists()
    with sqlite3.connect(test_config.log_dir / "source_router.db") as conn:
        count = conn.execute("SELECT COUNT(*) FROM source_request_log").fetchone()[0]
        tables = {
            row[0]
            for row in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ).fetchall()
        }
        columns = {
            row[1] for row in conn.execute("PRAGMA table_info(source_request_log)").fetchall()
        }
    assert count >= 1
    assert {
        "source_request_log",
        "source_fallback_trace",
        "source_health_score",
        "source_quality_check",
        "source_failure_event",
        "pytdx_runtime_failover_trace",
    }.issubset(tables)
    assert {
        "request_id",
        "function_name",
        "target",
        "selected_source",
        "attempted_sources",
        "fallback_reason",
        "latency_ms",
        "row_count",
        "field_missing",
        "success",
        "error_type",
        "created_at",
    }.issubset(columns)

    line = (test_config.log_dir / "source_router.jsonl").read_text(encoding="utf-8").splitlines()[0]
    payload = json.loads(line)
    assert payload["function_name"] == "trade_calendar"
