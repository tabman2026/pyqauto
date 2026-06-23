from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


class AuditLogger:
    """JSONL + SQLite request audit logger."""

    def __init__(self, log_dir: Path, enable_sqlite: bool = True) -> None:
        self.log_dir = log_dir
        self.enable_sqlite = enable_sqlite
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self.jsonl_path = self.log_dir / "source_router.jsonl"
        self.sqlite_path = self.log_dir / "source_router.db"
        if enable_sqlite:
            self._init_sqlite()

    def _init_sqlite(self) -> None:
        with sqlite3.connect(self.sqlite_path) as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS source_request_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    request_id TEXT,
                    feature TEXT,
                    function_name TEXT,
                    target TEXT,
                    selected_source TEXT,
                    attempted_sources TEXT,
                    fallback_reason TEXT,
                    latency_ms REAL,
                    row_count INTEGER,
                    field_missing TEXT,
                    missing_fields TEXT,
                    success INTEGER,
                    error_type TEXT,
                    error_message TEXT,
                    created_at TEXT
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS source_fallback_trace (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    request_id TEXT,
                    feature TEXT,
                    function_name TEXT,
                    source TEXT,
                    status TEXT,
                    fallback_reason TEXT,
                    latency_ms REAL,
                    error_type TEXT,
                    error_message TEXT,
                    row_count INTEGER,
                    missing_fields TEXT,
                    warnings TEXT,
                    created_at TEXT
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS source_health_score (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    request_id TEXT,
                    feature TEXT,
                    function_name TEXT,
                    source TEXT,
                    score REAL,
                    success_rate REAL,
                    avg_latency_ms REAL,
                    p95_latency_ms REAL,
                    empty_rate REAL,
                    field_complete_rate REAL,
                    freshness_rate REAL,
                    recent_failure_count INTEGER,
                    created_at TEXT
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS source_quality_check (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    request_id TEXT,
                    feature TEXT,
                    function_name TEXT,
                    source TEXT,
                    is_valid INTEGER,
                    row_count INTEGER,
                    missing_fields TEXT,
                    warnings TEXT,
                    created_at TEXT
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS source_failure_event (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    request_id TEXT,
                    feature TEXT,
                    function_name TEXT,
                    source TEXT,
                    error_type TEXT,
                    error_message TEXT,
                    fallback_reason TEXT,
                    created_at TEXT
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS pytdx_runtime_failover_trace (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    request_id TEXT,
                    feature TEXT,
                    function_name TEXT,
                    target TEXT,
                    attempted_servers TEXT,
                    selected_server TEXT,
                    selected_server_role TEXT,
                    selected_server_latency_ms REAL,
                    failover_reason TEXT,
                    failover_count INTEGER,
                    pytdx_all_failed INTEGER,
                    fallback_to_source TEXT,
                    success INTEGER,
                    error_type TEXT,
                    created_at TEXT
                )
                """
            )
            self._ensure_request_columns(conn)
            conn.commit()

    def _ensure_request_columns(self, conn: sqlite3.Connection) -> None:
        expected = {
            "source_request_log": {
                "feature": "TEXT",
                "function_name": "TEXT",
                "target": "TEXT",
                "attempted_sources": "TEXT",
                "fallback_reason": "TEXT",
                "field_missing": "TEXT",
                "missing_fields": "TEXT",
                "error_message": "TEXT",
            },
            "source_fallback_trace": {
                "feature": "TEXT",
                "function_name": "TEXT",
                "fallback_reason": "TEXT",
                "warnings": "TEXT",
            },
        }
        for table, columns in expected.items():
            existing = {row[1] for row in conn.execute(f"PRAGMA table_info({table})").fetchall()}
            for column, column_type in columns.items():
                if column not in existing:
                    conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {column_type}")

    def log(self, payload: dict[str, Any]) -> None:
        payload = dict(payload)
        payload.setdefault("created_at", datetime.now(timezone.utc).isoformat())
        with self.jsonl_path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(payload, ensure_ascii=False, default=str) + "\n")
        if self.enable_sqlite:
            self._log_sqlite(payload)

    def _json(self, value: Any) -> str:
        return json.dumps(value, ensure_ascii=False, default=str)

    def _log_sqlite(self, payload: dict[str, Any]) -> None:
        feature = str(payload.get("feature") or payload.get("function_name") or "")
        function_name = str(payload.get("function_name") or feature)
        created_at = str(payload.get("created_at"))
        field_missing = payload.get("field_missing", payload.get("missing_fields", []))
        fallback_trace = payload.get("fallback_trace", []) or []
        attempted_sources = payload.get(
            "attempted_sources",
            [trace.get("source") for trace in fallback_trace if trace.get("source")],
        )
        fallback_reason = payload.get("fallback_reason")

        with sqlite3.connect(self.sqlite_path) as conn:
            conn.execute(
                """
                INSERT INTO source_request_log (
                    request_id, feature, function_name, target, selected_source,
                    attempted_sources, fallback_reason, latency_ms, row_count,
                    field_missing, missing_fields, success, error_type, error_message, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    payload.get("request_id"),
                    feature,
                    function_name,
                    payload.get("target"),
                    payload.get("selected_source"),
                    self._json(attempted_sources),
                    fallback_reason,
                    payload.get("latency_ms"),
                    payload.get("row_count"),
                    self._json(field_missing),
                    self._json(field_missing),
                    1 if payload.get("success") else 0,
                    payload.get("error_type"),
                    payload.get("error_message"),
                    created_at,
                ),
            )

            pytdx_trace = payload.get("pytdx_runtime_failover")
            if isinstance(pytdx_trace, dict):
                conn.execute(
                    """
                    INSERT INTO pytdx_runtime_failover_trace (
                        request_id, feature, function_name, target, attempted_servers,
                        selected_server, selected_server_role, selected_server_latency_ms,
                        failover_reason, failover_count, pytdx_all_failed, fallback_to_source,
                        success, error_type, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        payload.get("request_id"),
                        feature,
                        function_name,
                        payload.get("target"),
                        self._json(
                            pytdx_trace.get("attempted_servers")
                            or pytdx_trace.get("pytdx_failover_attempts", [])
                        ),
                        pytdx_trace.get("selected_server"),
                        pytdx_trace.get("selected_server_role"),
                        pytdx_trace.get("selected_server_latency_ms"),
                        pytdx_trace.get("failover_reason"),
                        pytdx_trace.get("failover_count"),
                        1 if pytdx_trace.get("pytdx_all_failed") else 0,
                        pytdx_trace.get("fallback_to_source"),
                        1 if pytdx_trace.get("success") else 0,
                        pytdx_trace.get("error_type"),
                        created_at,
                    ),
                )

            for trace in fallback_trace:
                conn.execute(
                    """
                    INSERT INTO source_fallback_trace (
                        request_id, feature, function_name, source, status, fallback_reason,
                        latency_ms, error_type, error_message, row_count, missing_fields,
                        warnings, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        payload.get("request_id"),
                        feature,
                        function_name,
                        trace.get("source"),
                        trace.get("status"),
                        trace.get("fallback_reason", fallback_reason),
                        trace.get("latency_ms"),
                        trace.get("error_type"),
                        trace.get("error_message"),
                        trace.get("row_count"),
                        self._json(trace.get("missing_fields", [])),
                        self._json(trace.get("warnings", [])),
                        created_at,
                    ),
                )
                if trace.get("status") not in {"success", "hit", "cache_hit"}:
                    conn.execute(
                        """
                        INSERT INTO source_failure_event (
                            request_id, feature, function_name, source, error_type,
                            error_message, fallback_reason, created_at
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            payload.get("request_id"),
                            feature,
                            function_name,
                            trace.get("source"),
                            trace.get("error_type", payload.get("error_type")),
                            trace.get("error_message", payload.get("error_message")),
                            trace.get("fallback_reason", trace.get("status")),
                            created_at,
                        ),
                    )

            for quality in payload.get("quality_checks", []) or []:
                conn.execute(
                    """
                    INSERT INTO source_quality_check (
                        request_id, feature, function_name, source, is_valid, row_count,
                        missing_fields, warnings, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        payload.get("request_id"),
                        feature,
                        function_name,
                        quality.get("source"),
                        1 if quality.get("is_valid") else 0,
                        quality.get("row_count"),
                        self._json(quality.get("missing_fields", [])),
                        self._json(quality.get("warnings", [])),
                        created_at,
                    ),
                )

            for health in payload.get("health_scores", []) or []:
                conn.execute(
                    """
                    INSERT INTO source_health_score (
                        request_id, feature, function_name, source, score, success_rate,
                        avg_latency_ms, p95_latency_ms, empty_rate, field_complete_rate,
                        freshness_rate, recent_failure_count, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        payload.get("request_id"),
                        health.get("feature", feature),
                        health.get("function_name", health.get("feature", function_name)),
                        health.get("source"),
                        health.get("score"),
                        health.get("success_rate"),
                        health.get("avg_latency_ms"),
                        health.get("p95_latency_ms"),
                        health.get("empty_rate"),
                        health.get("field_complete_rate"),
                        health.get("freshness_rate"),
                        health.get("recent_failure_count"),
                        created_at,
                    ),
                )
            conn.commit()
