from __future__ import annotations

import json

from aquote_router.audit import AuditLogger
from aquote_router.models import QuoteRecord
from aquote_router.policy import SourcePolicy
from aquote_router.router import QuoteRouter


class SuccessAdapter:
    source = "pytdx"
    source_level = "primary"

    def realtime_quotes(self, symbols, *, include_raw=False):
        return [QuoteRecord(symbol=symbol, price=1.0) for symbol in symbols]


def test_jsonl_audit_written(tmp_path) -> None:
    audit_path = tmp_path / "audit.jsonl"
    router = QuoteRouter(
        policy=_policy(),
        pytdx_adapters=[SuccessAdapter()],
        audit_logger=AuditLogger(jsonl_path=audit_path),
    )

    records = router.realtime_quotes(["000001"])

    lines = audit_path.read_text(encoding="utf-8").splitlines()
    payload = json.loads(lines[0])
    assert records[0].trace_id == payload["trace_id"]
    assert payload["api_name"] == "realtime_quotes"
    assert payload["selected_source"] == "pytdx"
    assert payload["success"] is True
    assert payload["record_count"] == 1


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
