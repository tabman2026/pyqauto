from __future__ import annotations

from pyqauto.adapters.base import PytdxServer
from pyqauto.adapters.easyquotation_sina_adapter import EasyQuotationSinaAdapter
from pyqauto.adapters.pytdx_adapter import PytdxAdapter
from pyqauto.source_schema import (
    STANDARD_QUOTE_FIELDS,
    build_standard_row,
    normalize_standard_symbol,
    source_schema_diagnostics,
    validate_standard_rows,
)


def test_standard_quote_schema_fields_validate() -> None:
    row = build_standard_row(
        symbol_raw="600519",
        name="贵州茅台",
        trade_time="2026-06-21 10:00:00",
        fetch_time="2026-06-21T02:00:00Z",
        last_price=1200,
        pre_close=1190,
        open_price=1195,
        high=1210,
        low=1188,
        volume_shares=12300,
        amount_yuan=456789,
        source_name="fake",
        source_api="fake.api",
    )

    validation = validate_standard_rows([row])

    assert validation.is_valid
    assert [field for field in STANDARD_QUOTE_FIELDS if field not in row] == []
    assert row["symbol"] == "600519.SH"
    assert row["change"] == 10
    assert round(row["pct_chg"], 6) == round((1200 / 1190 - 1) * 100, 6)


def test_standard_symbol_supports_bj_suffix() -> None:
    assert normalize_standard_symbol("430017") == "430017.BJ"
    assert normalize_standard_symbol("000001") == "000001.SZ"


def test_pytdx_quote_normalizes_to_standard_without_raw_field_dependency() -> None:
    adapter = PytdxAdapter(PytdxServer("127.0.0.1", 7709, "primary", 1))
    raw = [
        {
            "market": 1,
            "code": "600519",
            "price": 1200,
            "last_close": 1190,
            "open": 1195,
            "high": 1210,
            "low": 1188,
            "vol": 12300,
            "amount": 456789,
            "servertime": "10:00:00",
        }
    ]

    rows = adapter.normalize_to_standard(
        raw,
        source_api="pytdx.get_security_quotes",
        symbols=["600519"],
        fetch_time="2026-06-21T02:00:00Z",
    )
    validation = adapter.validate_standard_output(rows)

    assert validation.is_valid
    assert rows[0]["symbol"] == "600519.SH"
    assert rows[0]["source_api"] == "pytdx.get_security_quotes"


def test_easyquotation_normalizes_to_standard() -> None:
    adapter = EasyQuotationSinaAdapter()
    raw = {
        "000001": {
            "name": "平安银行",
            "now": 10.5,
            "close": 10,
            "open": 10.1,
            "high": 10.8,
            "low": 9.9,
            "turnover": 1000,
            "volume": 10500,
            "date": "2026-06-21",
            "time": "10:00:00",
        }
    }

    rows = adapter.normalize_to_standard(
        raw,
        symbols=["000001"],
        fetch_time="2026-06-21T02:00:00Z",
    )
    validation = adapter.validate_standard_output(rows)

    assert validation.is_valid
    assert rows[0]["symbol"] == "000001.SZ"
    assert rows[0]["volume_shares"] == 1000
    assert rows[0]["amount_yuan"] == 10500


def test_diagnose_schema_payload_contains_mappings_and_units() -> None:
    payload = source_schema_diagnostics()

    assert "standard_fields" in payload
    assert "unit_rules" in payload
    assert "volume_shares" in payload["standard_fields"]
