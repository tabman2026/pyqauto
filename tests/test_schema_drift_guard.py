from __future__ import annotations

from pathlib import Path
from typing import Any

from pyqauto.adapters.akshare_em_spot_adapter import (
    AKSHARE_EM_SPOT_FIELD_MAPPING,
    AkShareEmSpotAdapter,
)
from pyqauto.source_schema_live import run_source_schema_probe_live


class MissingPriceAkShareAdapter(AkShareEmSpotAdapter):
    def fetch_raw(
        self,
        symbols: list[str] | None = None,
        *,
        source_api: str | None = None,
    ) -> list[dict[str, Any]]:
        return [
            {
                "代码": "600519",
                "名称": "贵州茅台",
                "昨收": 1190,
                "今开": 1195,
                "最高": 1210,
                "最低": 1188,
                "成交量": 123,
                "成交额": 456789,
            }
        ]


def test_schema_drift_guard_rejects_missing_mapped_core_field() -> None:
    adapter = MissingPriceAkShareAdapter()
    rows = adapter.normalize_to_standard(
        adapter.fetch_raw(),
        symbols=["600519"],
        fetch_time="2026-06-21T02:00:00Z",
    )

    validation = adapter.validate_standard_output(
        rows,
        field_mapping=AKSHARE_EM_SPOT_FIELD_MAPPING,
    )

    assert validation.is_valid is False
    assert validation.adapter_status == "schema_drift"
    assert rows[0]["adapter_status"] == "schema_drift"
    assert "last_price" in validation.missing_fields
    assert "last_price" in validation.diagnose["schema_drift_fields"]
    assert "raw schema did not expose mapped fields" in validation.diagnose["rejection_reason"]


def test_missing_core_field_does_not_enter_public_records(
    tmp_path: Path,
    monkeypatch,
) -> None:
    monkeypatch.chdir(tmp_path)
    payload = run_source_schema_probe_live(
        report_path=tmp_path / "reports" / "latest" / "source_schema_probe_live.json",
        log_path=tmp_path / "logs" / "source_schema_probe_live.jsonl",
        adapters={
            "akshare_em_spot": MissingPriceAkShareAdapter(),
            "pytdx": [],
            "easyquotation_sina": FailingAdapter("easyquotation_sina"),
            "easyquotation_tencent": FailingAdapter("easyquotation_tencent"),
        },
    )

    akshare = next(
        source
        for source in payload["sources"]
        if source["source_api"] == "akshare.stock_zh_a_spot_em"
    )
    probe = next(
        probe
        for probe in payload["probes"]
        if probe["source_api"] == "akshare.stock_zh_a_spot_em"
    )

    assert akshare["schema_status"] == "schema_drift"
    assert akshare["accepted_record_count"] == 0
    assert akshare["rejected_record_count"] == 1
    assert "last_price" in akshare["schema_drift_fields"]
    assert probe["standard_sample"] == []
    assert probe["public_record_count"] == 0


class FailingAdapter:
    source_level = None

    def __init__(self, source: str) -> None:
        self.source = source

    def fetch_raw(self, *args: Any, **kwargs: Any) -> Any:
        raise RuntimeError("mock source unavailable")
