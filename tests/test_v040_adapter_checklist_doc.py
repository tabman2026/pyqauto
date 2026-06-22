from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CHECKLIST = ROOT / "docs" / "V040_ADAPTER_IMPLEMENTATION_CHECKLIST.md"


def test_v040_adapter_implementation_checklist_contains_required_gates() -> None:
    text = CHECKLIST.read_text(encoding="utf-8")
    required_items = [
        "Official documentation has been read",
        "Mock raw schema has been fixed",
        "Field mapping has been confirmed",
        "Unit rules have been confirmed",
        "Normalize mock tests pass",
        "Missing-field rejection tests pass",
        "Schema drift guard passes",
        "Live probe passes",
        "Audit records pass",
        "Source policy draft passes",
        "DATA_SOURCES has been updated",
        "RETURN_FIELDS has been updated",
        "CLI documentation has been updated",
        "Not in the default fallback chain unless explicitly approved",
        "Release checks pass before publishing",
    ]
    for item in required_items:
        assert item in text


def test_v040_adapter_checklist_keeps_release_and_policy_boundaries() -> None:
    text = CHECKLIST.read_text(encoding="utf-8")
    assert "Do not tag or publish from candidate normalize work" in text
    assert "Do not add candidate adapters to default fallback" in text
    assert "pytest / ruff / check_release / smoke_test / build" in text
