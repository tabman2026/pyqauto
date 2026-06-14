from __future__ import annotations

import sqlite3

from aquote_router.audit import AuditLogger
from aquote_router.models import QuoteRecord
from aquote_router.policy import SourcePolicy
from aquote_router.router import QuoteRouter


class SuccessAdapter:
    source = "pytdx"
    source_level = "primary"

    def realtime_quotes(self, symbols, *, include_raw=False):
        return [QuoteRecord(symbol=symbol, price=1.0) for symbol in symbols]


def test_sqlite_audit_written(tmp_path) -> None:
    audit_path = tmp_path / "audit.sqlite3"
    router = QuoteRouter(
        policy=_policy(),
        pytdx_adapters=[SuccessAdapter()],
        audit_logger=AuditLogger(sqlite_path=audit_path),
    )

    router.realtime_quotes(["000001"])

    with sqlite3.connect(audit_path) as connection:
        audit_count = connection.execute(
            "SELECT COUNT(*) FROM quote_router_audit"
        ).fetchone()[0]
        attempt_count = connection.execute(
            "SELECT COUNT(*) FROM quote_router_attempts"
        ).fetchone()[0]

    assert audit_count == 1
    assert attempt_count == 1


def _policy() -> SourcePolicy:
    return SourcePolicy.from_dict(
        {
            "apis": {
                "realtime_quotes": {
                    "allow_fallback": True,
                    "fallback_order": ["pytdx"],
                },
                "full_realtime_quotes": {
                    "allow_fallback": True,
                    "fallback_order": ["pytdx"],
                },
                "index_realtime": {
                    "allow_fallback": True,
                    "fallback_order": ["pytdx"],
                },
                "minute_kline": {
                    "allow_fallback": False,
                    "fallback_order": ["pytdx"],
                },
            }
        }
    )
