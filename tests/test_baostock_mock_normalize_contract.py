from __future__ import annotations

import copy
import json
from pathlib import Path

from helpers.adapter_candidate_normalizers import normalize_candidate_payload

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "tests" / "fixtures" / "adapter_candidates" / "baostock_kline_raw_sample.json"


def _load_fixture() -> dict:
    return json.loads(FIXTURE.read_text(encoding="utf-8"))


def test_baostock_kline_mock_normalizes_to_candidate_kline_contract() -> None:
    report = normalize_candidate_payload(
        _load_fixture(),
        candidate="baostock",
        endpoint="kline",
        kind="kline",
    )

    assert report["candidate_source"] == "baostock_candidate"
    assert report["source"] != "baostock"
    record = report["candidate_records"][0]
    assert record["source"] == "baostock_candidate"
    assert record["symbol"] == "600000"
    assert record["datetime"] == "2026-01-02 09:35:00"
    assert record["period"] == "5m"
    assert record["metadata"]["frequency"] == "5"
    assert record["metadata"]["adjustflag"] == "2"
    assert record["raw"]["frequency"] == "5"
    assert record["raw"]["adjustflag"] == "2"


def test_baostock_unknown_units_reject_public_records_without_login_simulation() -> None:
    report = normalize_candidate_payload(
        _load_fixture(),
        candidate="baostock",
        endpoint="kline",
        kind="kline",
    )

    assert report["unit_status"] == "unknown"
    assert report["status"] == "rejected"
    assert report["public_records"] == []
    assert report["rejected_records"][0]["rejected_reason"]
    assert report["candidate_records"][0]["raw"]["request"]["requires_login"] is True
    assert report["candidate_records"][0]["raw"]["request"]["live_request"] is False


def test_baostock_missing_core_field_is_rejected_and_reported_as_drift() -> None:
    payload = copy.deepcopy(_load_fixture())
    fields = payload["result"]["fields"]
    close_index = fields.index("close")
    payload["result"]["fields"] = fields[:close_index] + fields[close_index + 1 :]
    payload["result"]["rows"][0] = (
        payload["result"]["rows"][0][:close_index]
        + payload["result"]["rows"][0][close_index + 1 :]
    )

    report = normalize_candidate_payload(
        payload,
        candidate="baostock",
        endpoint="kline",
        kind="kline",
    )

    assert report["status"] == "rejected"
    assert "close" in report["schema_drift_fields"]
    assert report["public_records"] == []
    assert report["rejected_records"][0]["missing_core_fields"] == ["close"]
