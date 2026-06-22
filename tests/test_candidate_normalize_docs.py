from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CONTRACT_DOC = ROOT / "docs" / "CANDIDATE_NORMALIZE_CONTRACT_V040.md"
CHECKLIST_DOC = ROOT / "docs" / "V040_ADAPTER_IMPLEMENTATION_CHECKLIST.md"


def test_candidate_normalize_contract_doc_exists_and_defines_flow() -> None:
    text = CONTRACT_DOC.read_text(encoding="utf-8")

    assert "# v0.4.0 Candidate Normalize Contract" in text
    assert "candidate normalizers are test-only contracts, not public adapter APIs" in text
    assert "mock raw -> candidate standard -> validate -> report" in text
    assert "public_records" in text
    assert "rejected_records" in text
    assert "schema_drift_fields" in text
    assert "known / unknown / converted / rejected" in text
    for source in ["efinance_candidate", "baostock_candidate", "mootdx_candidate"]:
        assert source in text


def test_candidate_normalize_contract_doc_keeps_candidates_out_of_runtime() -> None:
    text = CONTRACT_DOC.read_text(encoding="utf-8")

    assert "does not make a formal adapter" in text
    assert "does not update the default fallback chain" in text
    assert "does not publish v0.4.0" in text
    assert "must not enter `public_records`" in text


def test_candidate_normalize_docs_are_linked_from_existing_docs() -> None:
    linked_docs = [
        ROOT / "README.md",
        ROOT / "README.zh-CN.md",
        ROOT / "docs" / "BEGINNER_DEVELOPER_GUIDE.md",
        ROOT / "docs" / "ADAPTER_CANDIDATE_REVIEW_V040.md",
        ROOT / "docs" / "ADAPTER_FIELD_MAPPING_DRAFT_V040.md",
        ROOT / "docs" / "ADAPTER_UNIT_RULES_DRAFT_V040.md",
        ROOT / "docs" / "SOURCE_POLICY_DRAFT_V040.md",
    ]
    for path in linked_docs:
        text = path.read_text(encoding="utf-8")
        assert "CANDIDATE_NORMALIZE_CONTRACT_V040.md" in text
        assert "V040_ADAPTER_IMPLEMENTATION_CHECKLIST.md" in text


def test_v040_checklist_doc_exists() -> None:
    assert CHECKLIST_DOC.is_file()
