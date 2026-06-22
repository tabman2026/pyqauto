from __future__ import annotations

import copy
import json
from pathlib import Path

from helpers.adapter_candidate_normalizers import normalize_candidate_payload

ROOT = Path(__file__).resolve().parents[1]
FIXTURE_DIR = ROOT / "tests" / "fixtures" / "adapter_candidates"
FIELD_MAPPING_DOC = ROOT / "docs" / "ADAPTER_FIELD_MAPPING_DRAFT_V040.md"
UNIT_RULES_DOC = ROOT / "docs" / "ADAPTER_UNIT_RULES_DRAFT_V040.md"


def _load_fixture(name: str) -> dict:
    return json.loads((FIXTURE_DIR / name).read_text(encoding="utf-8"))


def test_efinance_realtime_mock_normalizes_to_candidate_quote_contract() -> None:
    report = normalize_candidate_payload(
        _load_fixture("efinance_realtime_raw_sample.json"),
        candidate="efinance",
        endpoint="realtime",
        kind="quote",
    )

    assert report["candidate_source"] == "efinance_candidate"
    assert report["source"] != "efinance"
    assert report["field_mapping_doc"] == "docs/ADAPTER_FIELD_MAPPING_DRAFT_V040.md"
    assert report["unit_rules_doc"] == "docs/ADAPTER_UNIT_RULES_DRAFT_V040.md"
    assert "schema_drift_fields" in report

    record = report["candidate_records"][0]
    for field in [
        "symbol",
        "name",
        "price",
        "open",
        "high",
        "low",
        "pre_close",
        "volume",
        "amount",
        "volume_shares",
        "amount_yuan",
        "datetime",
        "source",
        "source_level",
        "trace_id",
        "raw",
    ]:
        assert field in record
    assert record["symbol"] == "600000"
    assert record["source"] == "efinance_candidate"
    assert report["current_model_field_semantics"]["QuoteRecord.volume"] == "volume_shares"
    assert report["current_model_field_semantics"]["QuoteRecord.amount"] == "amount_yuan"

    assert report["unit_status"] == "unknown"
    assert report["status"] == "rejected"
    assert report["public_records"] == []
    assert report["rejected_records"][0]["rejected_reason"]


def test_efinance_kline_mock_normalizes_to_candidate_kline_contract() -> None:
    report = normalize_candidate_payload(
        _load_fixture("efinance_kline_raw_sample.json"),
        candidate="efinance",
        endpoint="kline",
        kind="kline",
    )

    record = report["candidate_records"][0]
    assert record["source"] == "efinance_candidate"
    assert record["symbol"] == "600000"
    assert record["datetime"] == "2026-01-02 09:35"
    assert record["period"] == "5m"
    assert record["metadata"]["klt"] == 5
    assert record["metadata"]["fqt"] == 1
    assert report["unit_status"] == "unknown"
    assert report["public_records"] == []
    assert report["rejected_records"]


def test_efinance_field_mapping_and_unit_docs_drive_contract() -> None:
    field_mapping = FIELD_MAPPING_DOC.read_text(encoding="utf-8")
    unit_rules = UNIT_RULES_DOC.read_text(encoding="utf-8")

    assert "efinance Realtime -> pyqauto QuoteRecord" in field_mapping
    assert "efinance Kline -> pyqauto KlineBar" in field_mapping
    assert "`成交量` | Traded volume | unknown" in field_mapping
    assert "| efinance realtime | `成交量` | unknown | `volume_shares` |" in unit_rules
    assert "| efinance K-line | `成交额` | unknown | `amount_yuan` |" in unit_rules


def test_efinance_missing_core_field_is_rejected_and_reported_as_drift() -> None:
    payload = copy.deepcopy(_load_fixture("efinance_realtime_raw_sample.json"))
    del payload["rows"][0]["最新价"]

    report = normalize_candidate_payload(
        payload,
        candidate="efinance",
        endpoint="realtime",
        kind="quote",
    )

    assert report["status"] == "rejected"
    assert "price" in report["schema_drift_fields"]
    assert report["public_records"] == []
    assert report["rejected_records"][0]["missing_core_fields"] == ["price"]
