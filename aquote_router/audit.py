"""JSONL and SQLite audit trail writers."""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path

from aquote_router.models import AuditRecord


class AuditLogger:
    """Write quote router audit records to JSONL and SQLite."""

    def __init__(
        self,
        *,
        jsonl_path: str | Path | None = None,
        sqlite_path: str | Path | None = None,
    ) -> None:
        self.jsonl_path = Path(jsonl_path) if jsonl_path else None
        self.sqlite_path = Path(sqlite_path) if sqlite_path else None

    def log(self, record: AuditRecord) -> None:
        """Persist one audit record to every configured sink."""

        if self.jsonl_path:
            self._write_jsonl(record)
        if self.sqlite_path:
            self._write_sqlite(record)

    def _write_jsonl(self, record: AuditRecord) -> None:
        assert self.jsonl_path is not None
        self.jsonl_path.parent.mkdir(parents=True, exist_ok=True)
        with self.jsonl_path.open("a", encoding="utf-8", newline="\n") as file:
            file.write(json.dumps(record.to_dict(), ensure_ascii=False) + "\n")

    def _write_sqlite(self, record: AuditRecord) -> None:
        assert self.sqlite_path is not None
        self.sqlite_path.parent.mkdir(parents=True, exist_ok=True)
        with sqlite3.connect(self.sqlite_path) as connection:
            self._ensure_schema(connection)
            data = record.to_dict()
            connection.execute(
                """
                INSERT OR REPLACE INTO quote_router_audit (
                    trace_id,
                    api_name,
                    symbols,
                    started_at,
                    finished_at,
                    duration_ms,
                    selected_source,
                    selected_source_level,
                    attempts,
                    fallback_chain,
                    success,
                    error_type,
                    error_message,
                    record_count
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    data["trace_id"],
                    data["api_name"],
                    json.dumps(data["symbols"], ensure_ascii=False),
                    data["started_at"],
                    data["finished_at"],
                    data["duration_ms"],
                    data["selected_source"],
                    data["selected_source_level"],
                    json.dumps(data["attempts"], ensure_ascii=False),
                    json.dumps(data["fallback_chain"], ensure_ascii=False),
                    int(data["success"]),
                    data["error_type"],
                    data["error_message"],
                    data["record_count"],
                ),
            )
            connection.execute(
                "DELETE FROM quote_router_attempts WHERE trace_id = ?",
                (record.trace_id,),
            )
            for index, attempt in enumerate(record.attempts, start=1):
                connection.execute(
                    """
                    INSERT INTO quote_router_attempts (
                        trace_id,
                        attempt_index,
                        source,
                        source_level,
                        started_at,
                        finished_at,
                        duration_ms,
                        success,
                        error_type,
                        error_message,
                        record_count
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        record.trace_id,
                        index,
                        attempt.source,
                        attempt.source_level,
                        attempt.started_at,
                        attempt.finished_at,
                        attempt.duration_ms,
                        int(attempt.success),
                        attempt.error_type,
                        attempt.error_message,
                        attempt.record_count,
                    ),
                )
            connection.commit()

    def _ensure_schema(self, connection: sqlite3.Connection) -> None:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS quote_router_audit (
                trace_id TEXT PRIMARY KEY,
                api_name TEXT NOT NULL,
                symbols TEXT NOT NULL,
                started_at TEXT NOT NULL,
                finished_at TEXT NOT NULL,
                duration_ms REAL NOT NULL,
                selected_source TEXT,
                selected_source_level TEXT,
                attempts TEXT NOT NULL,
                fallback_chain TEXT NOT NULL,
                success INTEGER NOT NULL,
                error_type TEXT,
                error_message TEXT,
                record_count INTEGER NOT NULL
            )
            """
        )
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS quote_router_attempts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                trace_id TEXT NOT NULL,
                attempt_index INTEGER NOT NULL,
                source TEXT NOT NULL,
                source_level TEXT,
                started_at TEXT NOT NULL,
                finished_at TEXT NOT NULL,
                duration_ms REAL NOT NULL,
                success INTEGER NOT NULL,
                error_type TEXT,
                error_message TEXT,
                record_count INTEGER NOT NULL
            )
            """
        )
