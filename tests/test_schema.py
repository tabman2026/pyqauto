from __future__ import annotations

from astock_source_router.core.schema import date_to_iso, normalize_code, normalize_codes


def test_normalize_code():
    assert normalize_code("sz000001") == "000001"
    assert normalize_code("SH.600519") == "600519"
    assert normalize_codes(["000001", "sh600519"]) == ["000001", "600519"]


def test_date_to_iso():
    assert date_to_iso("20260611") == "2026-06-11"
    assert date_to_iso("2026-06-11") == "2026-06-11"
