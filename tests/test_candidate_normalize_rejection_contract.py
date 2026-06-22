from __future__ import annotations

import copy
import json
from pathlib import Path

from helpers.adapter_candidate_normalizers import normalize_candidate_payload

ROOT = Path(__file__).resolve().parents[1]
FIXTURE_DIR = ROOT / "tests" / "fixtures" / "adapter_candidates"
POLICY_FILES = [
    ROOT / "config" / "source_policy.example.yaml",
    ROOT / "pyqauto" / "config" / "source_policy.example.yaml",
]
README_FILES = [ROOT / "README.md", ROOT / "README.zh-CN.md"]


def _load_fixture(name: str) -> dict:
    return json.loads((FIXTURE_DIR / name).read_text(encoding="utf-8"))


def test_candidate_sources_have_suffix_and_do_not_enter_default_policy() -> None:
    payloads = [
        ("efinance", "realtime", "quote", "efinance_realtime_raw_sample.json"),
        ("efinance", "kline", "kline", "efinance_kline_raw_sample.json"),
        ("baostock", "kline", "kline", "baostock_kline_raw_sample.json"),
        ("mootdx", "quote", "quote", "mootdx_quote_raw_sample.json"),
        ("mootdx", "kline", "kline", "mootdx_kline_raw_sample.json"),
    ]
    for candidate, endpoint, kind, filename in payloads:
        report = normalize_candidate_payload(
            _load_fixture(filename),
            candidate=candidate,
            endpoint=endpoint,
            kind=kind,
        )
        assert report["candidate_source"] == f"{candidate}_candidate"
        assert report["source"].endswith("_candidate")
        assert report["source"] != candidate

    policy_text = "\n".join(path.read_text(encoding="utf-8") for path in POLICY_FILES)
    for candidate_source in ["efinance_candidate", "baostock_candidate", "mootdx_candidate"]:
        assert candidate_source not in policy_text
    for formal_source in ["efinance", "baostock", "mootdx"]:
        assert f"- {formal_source}" not in policy_text


def test_rejected_candidate_records_never_enter_public_records() -> None:
    report = normalize_candidate_payload(
        _load_fixture("efinance_kline_raw_sample.json"),
        candidate="efinance",
        endpoint="kline",
        kind="kline",
    )

    assert report["unit_status"] == "unknown"
    assert report["rejected_records"]
    assert report["public_records"] == []
    assert all(item["rejected_reason"] for item in report["rejected_records"])


def test_missing_core_field_and_schema_drift_are_reported() -> None:
    payload = copy.deepcopy(_load_fixture("mootdx_quote_raw_sample.json"))
    del payload["rows"][0]["price"]

    report = normalize_candidate_payload(
        payload,
        candidate="mootdx",
        endpoint="quote",
        kind="quote",
    )

    assert report["status"] == "rejected"
    assert "schema_drift_fields" in report
    assert "price" in report["schema_drift_fields"]
    assert report["missing_raw_fields"] == [{"standard_field": "price", "raw_fields": ["price"]}]
    assert report["public_records"] == []


def test_readmes_do_not_present_candidates_as_formal_support() -> None:
    text = "\n".join(path.read_text(encoding="utf-8") for path in README_FILES)
    assert "candidate normalize" in text
    for phrase in [
        "do not mean the current version supports these data sources",
        "not public adapter APIs",
        "do not enter the default fallback chain",
    ]:
        assert phrase in text
    for unsupported_source in ["source = efinance", "source = baostock", "source = mootdx"]:
        assert unsupported_source not in text


def test_candidate_docs_and_fixtures_do_not_leak_private_or_local_material() -> None:
    paths = [
        *FIXTURE_DIR.glob("*.json"),
        ROOT / "docs" / "CANDIDATE_NORMALIZE_CONTRACT_V040.md",
        ROOT / "docs" / "V040_ADAPTER_IMPLEMENTATION_CHECKLIST.md",
        ROOT / "docs" / "ADAPTER_CANDIDATE_REVIEW_V040.md",
        ROOT / "docs" / "ADAPTER_FIELD_MAPPING_DRAFT_V040.md",
        ROOT / "docs" / "ADAPTER_UNIT_RULES_DRAFT_V040.md",
        ROOT / "docs" / "SOURCE_POLICY_DRAFT_V040.md",
    ]
    forbidden_private_terms = ["token", "cookie", "secret", "webhook"]
    forbidden_local_markers = ["C:" + "\\Users", "Desktop" + "/CODEX"]
    forbidden_scope_terms = ["交易执行", "真实账户", "自动交易", "投资建议"]

    for path in paths:
        text = path.read_text(encoding="utf-8")
        lowered = text.lower()
        for term in forbidden_private_terms:
            assert term not in lowered, f"{path.name} contains {term}"
        for marker in forbidden_local_markers:
            assert marker not in text, f"{path.name} contains {marker}"
        for term in forbidden_scope_terms:
            assert term not in text, f"{path.name} contains {term}"
