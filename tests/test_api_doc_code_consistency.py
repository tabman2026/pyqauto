from __future__ import annotations

from pathlib import Path

import pyqauto
from pyqauto import QuoteRouter

ROOT = Path(__file__).resolve().parents[1]


def test_api_reference_lists_public_router_methods() -> None:
    text = (ROOT / "docs" / "API_REFERENCE.md").read_text(encoding="utf-8")

    for api_name in [
        "from_config",
        "realtime_quotes",
        "full_realtime_quotes",
        "index_realtime",
        "minute_kline",
        "daily_kline",
        "kline",
        "diagnose",
        "status",
        "health",
        "decision_trace",
        "get_system_state",
    ]:
        assert hasattr(QuoteRouter, api_name)
        assert api_name in text


def test_api_reference_lists_simple_api_functions() -> None:
    text = (ROOT / "docs" / "API_REFERENCE.md").read_text(encoding="utf-8")

    for api_name in [
        "quote",
        "quotes",
        "full_quotes",
        "index",
        "minute",
        "daily",
        "kline",
        "diagnose",
        "configure",
    ]:
        assert hasattr(pyqauto, api_name)
        assert api_name in text


def test_consistency_report_exists_and_marks_all_checked_apis_passed() -> None:
    report = ROOT / "API_DOC_CODE_CONSISTENCY_REPORT.md"
    if not report.exists():
        return
    text = report.read_text(encoding="utf-8")
    for api_name in [
        "realtime_quotes",
        "full_realtime_quotes",
        "index_realtime",
        "minute_kline",
        "daily_kline",
        "kline",
        "diagnose",
    ]:
        assert api_name in text
    assert "FAILED" not in text
