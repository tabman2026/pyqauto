from __future__ import annotations

import copy
import json
from pathlib import Path

from helpers.adapter_candidate_normalizers import normalize_candidate_payload

ROOT = Path(__file__).resolve().parents[1]
FIXTURE_DIR = ROOT / "tests" / "fixtures" / "adapter_candidates"
CONTRACT_DOC = ROOT / "docs" / "CANDIDATE_NORMALIZE_CONTRACT_V040.md"
SOURCE_POLICY_DRAFT = ROOT / "docs" / "SOURCE_POLICY_DRAFT_V040.md"


def _load_fixture(name: str) -> dict:
    return json.loads((FIXTURE_DIR / name).read_text(encoding="utf-8"))


def test_mootdx_quote_mock_normalizes_to_candidate_quote_contract() -> None:
    report = normalize_candidate_payload(
        _load_fixture("mootdx_quote_raw_sample.json"),
        candidate="mootdx",
        endpoint="quote",
        kind="quote",
    )

    record = report["candidate_records"][0]
    assert report["candidate_source"] == "mootdx_candidate"
    assert record["source"] == "mootdx_candidate"
    assert record["symbol"] == "600000"
    assert record["price"] == 10.12
    assert report["unit_status"] == "unknown"
    assert report["public_records"] == []
    assert report["rejected_records"]


def test_mootdx_kline_mock_normalizes_to_candidate_kline_contract() -> None:
    report = normalize_candidate_payload(
        _load_fixture("mootdx_kline_raw_sample.json"),
        candidate="mootdx",
        endpoint="kline",
        kind="kline",
    )

    record = report["candidate_records"][0]
    assert record["source"] == "mootdx_candidate"
    assert record["symbol"] == "600000"
    assert record["datetime"] == "2026-01-02 15:00:00"
    assert record["period"] == "1d"
    assert record["metadata"]["frequency"] == 9
    assert record["metadata"]["adjust"] == "qfq"
    assert report["public_records"] == []


def test_mootdx_contract_keeps_pytdx_as_default_and_mootdx_as_reference() -> None:
    contract = CONTRACT_DOC.read_text(encoding="utf-8")
    policy = SOURCE_POLICY_DRAFT.read_text(encoding="utf-8")

    assert "mootdx_candidate" in contract
    assert "pytdx server / API wrapper reference" in contract
    assert "must not replace pytdx" in contract
    assert "Candidate adapters do not enter the default fallback chain" in policy


def test_mootdx_missing_core_field_is_rejected_and_reported_as_drift() -> None:
    payload = copy.deepcopy(_load_fixture("mootdx_kline_raw_sample.json"))
    del payload["rows"][0]["close"]

    report = normalize_candidate_payload(
        payload,
        candidate="mootdx",
        endpoint="kline",
        kind="kline",
    )

    assert report["status"] == "rejected"
    assert "close" in report["schema_drift_fields"]
    assert report["public_records"] == []
    assert report["rejected_records"][0]["missing_core_fields"] == ["close"]
