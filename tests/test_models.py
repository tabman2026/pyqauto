from __future__ import annotations

from aquote_router.models import QuoteRecord


def test_quote_record_omits_raw_by_default() -> None:
    record = QuoteRecord(symbol="000001", price=1.23, raw={"large": "payload"})

    data = record.to_dict()

    assert data["symbol"] == "000001"
    assert "raw" not in data


def test_quote_record_can_include_raw() -> None:
    record = QuoteRecord(symbol="000001", raw={"field": "value"})

    data = record.to_dict(include_raw=True)

    assert data["raw"] == {"field": "value"}
