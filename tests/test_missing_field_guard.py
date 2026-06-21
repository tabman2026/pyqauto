from __future__ import annotations

from pathlib import Path

import pytest

from pyqauto.adapters.akshare_em_spot_adapter import AkShareEmSpotAdapter
from pyqauto.exceptions import SourceUnavailableError


def test_missing_core_field_sets_field_missing_and_diagnose() -> None:
    adapter = AkShareEmSpotAdapter()
    rows = adapter.normalize_to_standard(
        [
            {
                "代码": "000001",
                "名称": "平安银行",
                "昨收": 10.0,
                "今开": 10.1,
                "最高": 10.6,
                "最低": 9.9,
                "成交量": 321,
                "成交额": 654321,
            }
        ],
        symbols=["000001"],
        fetch_time="2026-06-21T02:00:00Z",
    )

    validation = adapter.validate_standard_output(rows)

    assert validation.is_valid is False
    assert validation.adapter_status == "field_missing"
    assert rows[0]["adapter_status"] == "field_missing"
    assert "last_price" in validation.missing_fields
    assert "last_price" in validation.diagnose["missing_fields"]


def test_public_adapter_rejects_unvalidated_standard_rows(
    tmp_path: Path,
    monkeypatch,
) -> None:
    monkeypatch.chdir(tmp_path)
    adapter = AkShareEmSpotAdapter()
    raw_missing_price = [
        {
            "代码": "000001",
            "名称": "平安银行",
            "昨收": 10.0,
            "今开": 10.1,
            "最高": 10.6,
            "最低": 9.9,
            "成交量": 321,
            "成交额": 654321,
        }
    ]
    monkeypatch.setattr(adapter, "fetch_raw", lambda **kwargs: raw_missing_price)

    with pytest.raises(SourceUnavailableError, match="last_price"):
        adapter.realtime_quotes(["000001"])
